"""
取款事件监听服务
监听 Execution Layer 的 Withdrawal 事件
"""
import logging
import asyncio
from typing import List, Dict, Any, Optional
from datetime import datetime
from decimal import Decimal

from web3 import Web3
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

# 兼容不同版本的 web3.py
# web3.py 6.0+ 中 geth_poa_middleware 的导入方式已改变
geth_poa_middleware = None
try:
    # 尝试旧版本导入 (web3.py < 6.0)
    from web3.middleware import geth_poa_middleware
except ImportError:
    try:
        # 尝试新版本导入 (web3.py >= 6.0)
        from web3.middleware import ExtraDataToPOAMiddleware
        geth_poa_middleware = ExtraDataToPOAMiddleware
    except ImportError:
        # PoA 中间件在新版本中可能已移除或改名
        # 这不会影响主网等非 PoA 网络的使用
        pass

from app.models.database import ValidatorKey, WithdrawalEvent
from app.models.enums import WithdrawalType
from app.config import settings
from app.core.beacon_api import BeaconAPIClient
from app.utils.exceptions import DatabaseError


class WithdrawalListener:
    """
    取款事件监听器
    监听 Execution Layer 的 Withdrawal 事件
    """
    
    # Withdrawal 事件签名（Ethereum 主网）
    # 在 Capella 升级后，验证者奖励会自动提取
    # Withdrawal 事件在 Execution Layer 记录在区块中
    
    def __init__(
        self,
        db: Session,
        execution_rpc_url: Optional[str] = None,
        beacon_api: Optional[BeaconAPIClient] = None
    ):
        """
        初始化监听器
        
        Args:
            db: 数据库会话
            execution_rpc_url: Execution Layer RPC URL
            beacon_api: Beacon API 客户端
        """
        self.db = db
        self.execution_rpc_url = execution_rpc_url or settings.execution_rpc_url
        self.beacon_api = beacon_api or BeaconAPIClient()
        
        # 初始化 Web3 连接
        if self.execution_rpc_url:
            self.w3 = Web3(Web3.HTTPProvider(self.execution_rpc_url))
            # 如果使用 PoA 网络，添加中间件
            if geth_poa_middleware is not None:
                try:
                    self.w3.middleware_onion.inject(geth_poa_middleware, layer=0)
                except Exception as e:
                    logger.debug(f"无法注入 PoA 中间件: {e}")
        else:
            self.w3 = None
            logger.warning("Execution Layer RPC URL 未配置，将使用 Beacon API 同步")
    
    def get_validator_pubkeys(self) -> List[str]:
        """
        获取所有活跃验证者公钥列表
        
        Returns:
            公钥列表
        """
        validators = self.db.query(ValidatorKey).filter(
            ValidatorKey.status.in_([
                'active_on_chain',
                'pending_exit',
                'exited'
            ])
        ).all()
        
        return [v.pubkey for v in validators]
    
    def record_withdrawal_event(
        self,
        pubkey: str,
        withdrawal_type: WithdrawalType,
        amount_wei: int,
        withdrawal_index: Optional[int] = None,
        slot: Optional[int] = None,
        epoch: Optional[int] = None
    ) -> WithdrawalEvent:
        """
        记录取款事件到数据库
        
        Args:
            pubkey: 验证者公钥
            withdrawal_type: 取款类型
            amount_wei: 取款金额（wei）
            withdrawal_index: 取款索引
            slot: Slot
            epoch: Epoch
            
        Returns:
            WithdrawalEvent 对象
        """
        from app.services.withdrawal_service import WithdrawalService
        
        withdrawal_service = WithdrawalService(self.db)
        return withdrawal_service.record_withdrawal(
            pubkey=pubkey,
            withdrawal_type=withdrawal_type,
            amount_wei=amount_wei,
            withdrawal_index=withdrawal_index,
            slot=slot,
            epoch=epoch
        )
    
    def sync_withdrawals_from_beacon_api(
        self,
        pubkey: str,
        from_epoch: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        从 Beacon API 同步取款事件
        
        通过查询验证者余额变化来推断取款事件
        这是一个替代方案，因为 Beacon API 可能不直接提供取款事件
        
        Args:
            pubkey: 验证者公钥
            from_epoch: 起始 epoch
            
        Returns:
            取款事件列表
        """
        withdrawals = []
        
        try:
            # 获取验证者信息
            validator_info = self.beacon_api.get_validator(pubkey)
            if not validator_info:
                return withdrawals
            
            validator_data = validator_info.get('validator', {})
            if not validator_data:
                return withdrawals
            
            # 获取验证者余额
            balance_gwei = int(validator_data.get('balance', '0'))
            balance_wei = balance_gwei * 10**9
            balance_eth = float(Decimal(balance_wei) / Decimal(10**18))
            
            # 获取有效余额
            effective_balance_gwei = int(validator_data.get('effective_balance', '0'))
            effective_balance_eth = float(Decimal(effective_balance_gwei) / Decimal(10**9))
            
            # 如果余额超过有效余额，说明有部分取款
            # 注意：这是一个简化的实现，实际应该记录历史余额变化
            
            # 获取验证者索引
            validator_index = validator_data.get('index')
            
            # 获取退出 epoch
            exit_epoch = validator_data.get('exit_epoch')
            if exit_epoch and exit_epoch != '18446744073709551615':  # 未退出
                # 验证者已退出，可能发生全额取款
                exit_epoch_int = int(exit_epoch)
                
                # 检查是否已记录过退出后的取款
                existing = self.db.query(WithdrawalEvent).filter(
                    WithdrawalEvent.pubkey == pubkey.lower(),
                    WithdrawalEvent.withdrawal_type == WithdrawalType.FULL.value
                ).first()
                
                if not existing and balance_eth < 32:
                    # 退出后余额减少，可能发生了全额取款
                    # 注意：这是一个简化实现，实际应该监听链上事件
                    logger.info(f"检测到可能的全额取款: {pubkey[:10]}... (余额: {balance_eth:.6f} ETH)")
            
            # 检查部分取款（余额超过 32 ETH）
            if balance_eth > 32.1:  # 考虑阈值
                # 检查最近是否已有部分取款记录
                recent_partial = self.db.query(WithdrawalEvent).filter(
                    WithdrawalEvent.pubkey == pubkey.lower(),
                    WithdrawalEvent.withdrawal_type == WithdrawalType.PARTIAL.value
                ).order_by(WithdrawalEvent.withdrawn_at.desc()).first()
                
                # 这是一个简化的实现，实际应该：
                # 1. 记录历史余额快照
                # 2. 检测余额变化
                # 3. 计算取款金额
                logger.debug(f"验证者余额超过 32 ETH: {pubkey[:10]}... (余额: {balance_eth:.6f} ETH)")
        
        except Exception as e:
            logger.error(f"从 Beacon API 同步取款事件失败 ({pubkey[:10]}...): {e}")
        
        return withdrawals
    
    def listen_withdrawal_events(
        self,
        start_block: Optional[int] = None,
        pubkeys: Optional[List[str]] = None
    ):
        """
        监听链上 Withdrawal 事件
        
        注意：Ethereum 的 Withdrawal 是通过系统级别的操作完成的，
        不是通过智能合约事件。需要使用其他方法：
        1. 监听 Execution Layer 的区块，查找 Withdrawal 操作
        2. 或定期查询 Beacon API 验证者余额变化
        
        Args:
            start_block: 起始区块号
            pubkeys: 要监听的验证者公钥列表（如果为 None，监听所有）
        """
        if not self.w3:
            logger.warning("Web3 未初始化，无法监听链上事件")
            return
        
        if pubkeys is None:
            pubkeys = self.get_validator_pubkeys()
        
        if start_block is None:
            start_block = self.w3.eth.block_number
        
        logger.info(f"开始监听 Withdrawal 事件 (起始区块: {start_block})")
        
        # 注意：实际实现需要：
        # 1. 定期查询最新区块
        # 2. 检查区块中的 Withdrawal 操作
        # 3. 匹配验证者公钥
        # 4. 记录取款事件
        
        # 这是一个占位实现
        current_block = start_block
        
        while True:
            try:
                latest_block = self.w3.eth.block_number
                
                # 处理新区块
                for block_num in range(current_block, latest_block + 1):
                    block = self.w3.eth.get_block(block_num, full_transactions=True)
                    
                    # 检查 Withdrawal 操作（Capella 升级后）
                    # 注意：Withdrawal 不是交易，而是区块结构的一部分
                    # 需要检查区块的 withdrawals 字段
                    if hasattr(block, 'withdrawals') and block.withdrawals:
                        for withdrawal in block.withdrawals:
                            # withdrawal 包含 validator_index 和 amount
                            # 需要通过 validator_index 查询对应的公钥
                            # 这是一个复杂的映射过程
                            pass
                
                current_block = latest_block + 1
                
                # 等待新区块
                asyncio.sleep(12)  # 约 12 秒一个区块
                
            except Exception as e:
                logger.error(f"监听 Withdrawal 事件时出错: {e}")
                asyncio.sleep(60)  # 出错后等待 1 分钟再试
    
    def sync_all_validators(self) -> Dict[str, Any]:
        """
        同步所有验证者的取款事件
        
        Returns:
            同步结果统计
        """
        pubkeys = self.get_validator_pubkeys()
        
        results = {
            'total': len(pubkeys),
            'synced': 0,
            'errors': 0,
            'withdrawals_found': 0,
        }
        
        for pubkey in pubkeys:
            try:
                withdrawals = self.sync_withdrawals_from_beacon_api(pubkey)
                results['synced'] += 1
                results['withdrawals_found'] += len(withdrawals)
            except Exception as e:
                logger.error(f"同步验证者取款事件失败 ({pubkey[:10]}...): {e}")
                results['errors'] += 1
        
        logger.info(
            f"同步完成: {results['synced']}/{results['total']} 成功, "
            f"发现 {results['withdrawals_found']} 个取款事件"
        )
        
        return results

