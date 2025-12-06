"""
存款交易验证服务
验证存款交易的有效性，查询 Beacon Chain 状态
"""
import logging
from datetime import datetime
from typing import Dict, Any, Optional, List
from sqlalchemy.orm import Session
from web3 import Web3
from eth_utils import to_bytes

from app.models.database import DepositTransaction, ValidatorKey
from app.models.enums import DepositStatus, ValidatorKeyStatus
from app.core.beacon_api import BeaconAPIClient
from app.services.validator_state_machine import ValidatorStateMachine
from app.utils.exceptions import BeaconAPIError

logger = logging.getLogger(__name__)


class DepositValidationService:
    """
    存款交易验证服务
    负责验证存款交易的有效性和查询 Beacon Chain 状态
    """
    
    def __init__(
        self,
        db: Session,
        beacon_api: Optional[BeaconAPIClient] = None,
        web3: Optional[Web3] = None
    ):
        """
        初始化验证服务
        
        Args:
            db: 数据库会话
            beacon_api: Beacon API 客户端
            web3: Web3 实例
        """
        self.db = db
        self.beacon_api = beacon_api or BeaconAPIClient()
        self.web3 = web3
        self.state_machine = ValidatorStateMachine(db)
    
    def validate_deposit_transaction(
        self,
        tx: DepositTransaction,
        rpc_url: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        验证存款交易
        
        Args:
            tx: 存款交易对象
            rpc_url: RPC URL（可选）
            
        Returns:
            验证结果字典
        """
        result = {
            'is_valid': False,
            'status': tx.status,
            'validator_index': None,
            'activation_epoch': None,
            'exit_epoch': None,
            'effective_balance_gwei': None,
            'error': None,
            'beacon_status': None
        }
        
        try:
            # 1. 检查交易是否已确认
            if tx.status not in [DepositStatus.CONFIRMED.value, DepositStatus.SUBMITTED.value]:
                # 如果状态不是 CONFIRMED 或 SUBMITTED，尝试从链上查询
                if rpc_url and self.web3:
                    try:
                        receipt = self.web3.eth.get_transaction_receipt(tx.tx_hash)
                        if receipt.status == 1:
                            tx.status = DepositStatus.CONFIRMED.value
                            tx.confirmed_at = datetime.utcnow()
                            tx.block_number = receipt.blockNumber
                            self.db.commit()
                        else:
                            result['error'] = '交易失败'
                            result['status'] = DepositStatus.FAILED.value
                            return result
                    except Exception as e:
                        logger.warning(f"无法获取交易 {tx.tx_hash} 的收据: {e}")
                        result['error'] = f"无法获取交易收据: {str(e)}"
                        return result
            
            # 2. 查询 Beacon Chain 验证者状态
            validator_data = self.check_validator_status(tx.pubkey)
            
            if validator_data is None:
                # 验证者在 Beacon Chain 上不存在，可能是参数无效
                result['error'] = '验证者在 Beacon Chain 上不存在，存款参数可能无效'
                result['status'] = DepositStatus.INVALID.value
                return result
            
            # 3. 提取验证者信息
            # Beacon API 返回格式: {'data': {'validator': {...}, 'status': '...', 'index': ..., 'balance': '...'}}
            # 或者直接是 {'validator': {...}, 'status': '...', ...}
            if isinstance(validator_data, dict) and 'data' in validator_data:
                validator_data = validator_data['data']
            
            validator_info = validator_data.get('validator', {})
            status_info = validator_data.get('status', '')
            
            # 如果没有 validator 字段，可能整个对象就是 validator 信息
            if not validator_info and validator_data.get('index') is not None:
                validator_info = validator_data
            
            result['validator_index'] = validator_info.get('index')
            
            # 处理 epoch 值：FAR_FUTURE_EPOCH (2^64 - 1) 表示未设置，应设为 None
            # 同时检查值是否超出 Integer 范围（PostgreSQL Integer 最大值是 2^31 - 1）
            from app.services.validator_state_machine import FAR_FUTURE_EPOCH
            MAX_INTEGER = 2147483647  # PostgreSQL Integer 最大值
            
            activation_epoch = validator_info.get('activation_epoch')
            if activation_epoch is not None:
                # 转换为整数（如果是从字符串转换）
                if isinstance(activation_epoch, str):
                    activation_epoch = int(activation_epoch)
                # 如果是 FAR_FUTURE_EPOCH 或超出 Integer 范围，设为 None
                if activation_epoch == FAR_FUTURE_EPOCH or activation_epoch > MAX_INTEGER:
                    activation_epoch = None
            result['activation_epoch'] = activation_epoch
            
            exit_epoch = validator_info.get('exit_epoch')
            if exit_epoch is not None:
                # 转换为整数（如果是从字符串转换）
                if isinstance(exit_epoch, str):
                    exit_epoch = int(exit_epoch)
                # 如果是 FAR_FUTURE_EPOCH 或超出 Integer 范围，设为 None
                if exit_epoch == FAR_FUTURE_EPOCH or exit_epoch > MAX_INTEGER:
                    exit_epoch = None
            result['exit_epoch'] = exit_epoch
            
            result['effective_balance_gwei'] = validator_info.get('effective_balance')
            result['beacon_status'] = status_info
            
            # 4. 根据 Beacon Chain 状态确定交易状态
            if status_info == 'active_ongoing':
                result['status'] = DepositStatus.ACTIVATED.value
                result['is_valid'] = True
            elif status_info == 'pending_initialized':
                # pending_initialized: 在 deposit queue 中
                result['status'] = DepositStatus.VALIDATED.value
                result['is_valid'] = True
            elif status_info == 'pending_queued':
                # pending_queued: 在激活队列中
                result['status'] = DepositStatus.PENDING_ACTIVATION.value
                result['is_valid'] = True
            elif status_info == 'exited_slashed':
                result['status'] = DepositStatus.EXITED.value
                result['is_valid'] = True
            elif status_info in ['exited_unslashed', 'withdrawal_possible', 'withdrawal_done']:
                result['status'] = DepositStatus.EXITED.value
                result['is_valid'] = True
            elif status_info == 'exiting':
                result['status'] = DepositStatus.EXITING.value
                result['is_valid'] = True
            else:
                # 验证者存在但状态未知，标记为已验证
                result['status'] = DepositStatus.VALIDATED.value
                result['is_valid'] = True
            
            # 5. 更新数据库记录
            self._update_transaction_status(tx, result)
            
            return result
            
        except BeaconAPIError as e:
            logger.error(f"Beacon API 错误: {e}")
            result['error'] = f"Beacon API 错误: {str(e)}"
            return result
        except Exception as e:
            logger.error(f"验证存款交易失败: {e}", exc_info=True)
            result['error'] = f"验证失败: {str(e)}"
            return result
    
    def check_validator_status(self, pubkey: str) -> Optional[Dict[str, Any]]:
        """
        检查验证者状态
        
        Args:
            pubkey: 验证者公钥
            
        Returns:
            验证者数据或 None
        """
        try:
            validator_data = self.beacon_api.get_validator(pubkey)
            return validator_data
        except BeaconAPIError:
            # 验证者可能不存在
            return None
        except Exception as e:
            logger.error(f"查询验证者状态失败: {e}")
            return None
    
    def _update_transaction_status(
        self,
        tx: DepositTransaction,
        result: Dict[str, Any]
    ) -> None:
        """
        更新交易状态（内部方法）
        
        Args:
            tx: 存款交易对象
            result: 验证结果
        """
        old_status = tx.status
        
        # 更新状态
        tx.status = result['status']
        
        # 更新验证时间
        if result['status'] in [DepositStatus.VALIDATED.value, DepositStatus.PENDING_ACTIVATION.value, 
                                DepositStatus.ACTIVATED.value, DepositStatus.EXITING.value, DepositStatus.EXITED.value]:
            if not tx.validated_at:
                tx.validated_at = datetime.utcnow()
        
        # 更新验证者信息
        if result['validator_index'] is not None:
            tx.validator_index = result['validator_index']
        
        # 更新 activation_epoch（已经过处理，FAR_FUTURE_EPOCH 已转为 None）
            tx.activation_epoch = result['activation_epoch']
        
        # 更新 exit_epoch（已经过处理，FAR_FUTURE_EPOCH 已转为 None）
            tx.exit_epoch = result['exit_epoch']
        
        if result['effective_balance_gwei'] is not None:
            tx.effective_balance_gwei = int(result['effective_balance_gwei'])
        
        # 更新验证错误
        if result['error']:
            tx.validation_error = result['error']
        
        # 记录状态历史
        if not tx.status_history:
            tx.status_history = []
        tx.status_history.append({
            'from_status': old_status,
            'to_status': result['status'],
            'timestamp': datetime.utcnow().isoformat(),
            'reason': 'validation'
        })
        
        # 更新关联的验证者密钥状态（使用状态机）
        validator_key = self.db.query(ValidatorKey).filter(
            ValidatorKey.pubkey == tx.pubkey
        ).first()
        
        if validator_key:
            # 根据 Beacon Chain 状态确定验证器状态
            validator_data = self.check_validator_status(tx.pubkey)
            if validator_data:
                # 使用状态机更新状态
                self.state_machine.update_validator_from_beacon_data(validator_key, validator_data)
            else:
                # 如果无法获取 Beacon Chain 状态，根据存款交易状态推断
                if result['status'] == DepositStatus.ACTIVATED.value:
                    self.state_machine.transition(
                        validator_key,
                        ValidatorKeyStatus.ACTIVE_ON_CHAIN,
                        reason='deposit_activated'
                    )
                elif result['status'] == DepositStatus.PENDING_ACTIVATION.value:
                    self.state_machine.transition(
                        validator_key,
                        ValidatorKeyStatus.PENDING,
                        reason='deposit_pending_activation'
                    )
                elif result['status'] == DepositStatus.VALIDATED.value:
                    self.state_machine.transition(
                        validator_key,
                        ValidatorKeyStatus.DEPOSITED,
                        reason='deposit_validated'
                    )
                elif result['status'] == DepositStatus.EXITED.value:
                    # 检查是否是被惩罚
                    if result.get('beacon_status') == 'exited_slashed':
                        self.state_machine.transition(
                            validator_key,
                            ValidatorKeyStatus.SLASHED,
                            reason='deposit_exited_slashed'
                        )
                    else:
                        self.state_machine.transition(
                            validator_key,
                            ValidatorKeyStatus.EXITED,
                            reason='deposit_exited'
                        )
                elif result['status'] == DepositStatus.EXITING.value:
                    self.state_machine.transition(
                        validator_key,
                        ValidatorKeyStatus.PENDING_EXIT,
                        reason='deposit_exiting'
                    )
        
        try:
            self.db.commit()
        except Exception as e:
            logger.error(f"提交事务失败: {e}", exc_info=True)
            self.db.rollback()
            raise
        logger.info(f"存款交易状态已更新: {tx.tx_hash[:10]}... {old_status} -> {result['status']}")
    
    def batch_validate_transactions(
        self,
        transactions: List[DepositTransaction],
        rpc_url: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        批量验证交易
        
        Args:
            transactions: 交易列表
            rpc_url: RPC URL（可选）
            
        Returns:
            批量验证结果统计
        """
        results = {
            'total': len(transactions),
            'validated': 0,
            'invalid': 0,
            'activated': 0,
            'pending_activation': 0,
            'exited': 0,
            'errors': []
        }
        
        for tx in transactions:
            try:
                result = self.validate_deposit_transaction(tx, rpc_url)
                
                if result['is_valid']:
                    results['validated'] += 1
                    if result['status'] == DepositStatus.ACTIVATED.value:
                        results['activated'] += 1
                    elif result['status'] == DepositStatus.PENDING_ACTIVATION.value:
                        results['pending_activation'] += 1
                    elif result['status'] == DepositStatus.EXITED.value:
                        results['exited'] += 1
                else:
                    results['invalid'] += 1
                    if result['error']:
                        results['errors'].append({
                            'tx_hash': tx.tx_hash,
                            'error': result['error']
                        })
            except Exception as e:
                logger.error(f"验证交易 {tx.tx_hash} 失败: {e}")
                results['errors'].append({
                    'tx_hash': tx.tx_hash,
                    'error': str(e)
                })
        
        return results

