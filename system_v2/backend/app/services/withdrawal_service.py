"""
验证者取款服务
监听和处理验证者取款事件，包括费用扣除
"""
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional
from decimal import Decimal
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.models.database import ValidatorKey, WithdrawalEvent
from app.models.enums import WithdrawalType, ValidatorKeyStatus
from app.core.beacon_api import BeaconAPIClient
from app.config import settings
from app.utils.exceptions import BeaconAPIError, DatabaseError

logger = logging.getLogger(__name__)


class WithdrawalService:
    """
    验证者取款服务
    监听取款事件，记录取款历史，计算和扣除费用
    """
    
    def __init__(
        self,
        db: Session,
        beacon_api: Optional[BeaconAPIClient] = None,
        fee_rate: Optional[float] = None
    ):
        """
        初始化取款服务
        
        Args:
            db: 数据库会话
            beacon_api: Beacon API 客户端
            fee_rate: 费用比例（默认从配置读取）
        """
        self.db = db
        self.beacon_api = beacon_api or BeaconAPIClient()
        self.fee_rate = fee_rate or settings.fee_rate
    
    def record_withdrawal(
        self,
        pubkey: str,
        withdrawal_type: WithdrawalType,
        amount_wei: int,
        withdrawal_index: Optional[int] = None,
        slot: Optional[int] = None,
        epoch: Optional[int] = None,
        block_number: Optional[int] = None
    ) -> WithdrawalEvent:
        """
        记录取款事件
        
        Args:
            pubkey: 验证者公钥
            withdrawal_type: 取款类型（partial/full）
            amount_wei: 取款金额（wei）
            withdrawal_index: 取款索引（链上）
            slot: Slot
            epoch: Epoch
            block_number: 区块号
            
        Returns:
            WithdrawalEvent 对象
        """
        try:
            # 计算费用
            amount_eth = float(Decimal(amount_wei) / Decimal(10**18))
            fee_wei = int(amount_wei * self.fee_rate)
            fee_eth = amount_eth * self.fee_rate
            
            # 创建取款事件记录
            withdrawal_event = WithdrawalEvent(
                pubkey=pubkey.lower(),
                withdrawal_type=withdrawal_type.value,
                amount_wei=amount_wei,
                amount_eth=amount_eth,
                fee_wei=fee_wei,
                fee_eth=fee_eth,
                fee_rate=Decimal(str(self.fee_rate)),
                withdrawal_index=withdrawal_index,
                slot=slot,
                epoch=epoch,
                block_number=block_number,
                withdrawn_at=datetime.utcnow()
            )
            
            self.db.add(withdrawal_event)
            self.db.commit()
            
            logger.info(
                f"取款事件已记录: {pubkey[:10]}... "
                f"类型: {withdrawal_type.value}, 金额: {amount_eth:.6f} ETH, 费用: {fee_eth:.6f} ETH"
            )
            
            return withdrawal_event
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"记录取款事件失败: {e}")
            raise DatabaseError(f"记录取款事件失败: {e}")
    
    def get_validator_withdrawals(
        self,
        pubkey: str,
        limit: Optional[int] = None,
        offset: int = 0
    ) -> tuple[List[WithdrawalEvent], int]:
        """
        获取验证者的取款历史
        
        Args:
            pubkey: 验证者公钥
            limit: 限制数量
            offset: 偏移量
            
        Returns:
            (取款事件列表, 总数) 元组
        """
        query = self.db.query(WithdrawalEvent).filter(
            WithdrawalEvent.pubkey == pubkey.lower()
        )
        
        total = query.count()
        
        if limit:
            query = query.limit(limit).offset(offset)
        
        query = query.order_by(WithdrawalEvent.withdrawn_at.desc())
        
        withdrawals = query.all()
        return withdrawals, total
    
    def get_total_withdrawals(
        self,
        pubkey: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        获取取款统计信息
        
        Args:
            pubkey: 验证者公钥（可选，如果不提供则统计所有）
            
        Returns:
            统计信息字典
        """
        query = self.db.query(WithdrawalEvent)
        
        if pubkey:
            query = query.filter(WithdrawalEvent.pubkey == pubkey.lower())
        
        total_count = query.count()
        total_amount_wei = query.with_entities(
            func.sum(WithdrawalEvent.amount_wei)
        ).scalar() or 0
        total_fee_wei = query.with_entities(
            func.sum(WithdrawalEvent.fee_wei)
        ).scalar() or 0
        
        # 按类型统计
        partial_count = query.filter(
            WithdrawalEvent.withdrawal_type == WithdrawalType.PARTIAL.value
        ).count()
        full_count = query.filter(
            WithdrawalEvent.withdrawal_type == WithdrawalType.FULL.value
        ).count()
        
        return {
            'total_count': total_count,
            'total_amount_eth': float(Decimal(total_amount_wei) / Decimal(10**18)),
            'total_fee_eth': float(Decimal(total_fee_wei) / Decimal(10**18)),
            'partial_count': partial_count,
            'full_count': full_count
        }
    
    def sync_withdrawals_from_beacon(
        self,
        pubkey: str,
        from_epoch: Optional[int] = None
    ) -> List[WithdrawalEvent]:
        """
        从 Beacon Chain API 同步取款事件
        
        注意：Beacon API 可能不直接提供取款事件查询，
        这里是一个简化实现，实际应该监听链上事件或使用专门的索引服务
        
        Args:
            pubkey: 验证者公钥
            from_epoch: 起始 epoch（可选）
            
        Returns:
            同步的取款事件列表
        """
        # 这是一个占位实现
        # 实际实现需要：
        # 1. 监听 Execution Layer 的 Withdrawal 事件
        # 2. 或使用专门的索引服务（如 Etherscan API）
        # 3. 或定期查询验证者余额变化
        
        logger.warning("从 Beacon Chain 同步取款事件功能需要实际实现")
        return []
    
    def calculate_fee(
        self,
        withdrawal_amount_wei: int
    ) -> Dict[str, Any]:
        """
        计算取款费用
        
        Args:
            withdrawal_amount_wei: 取款金额（wei）
            
        Returns:
            费用信息字典
        """
        fee_wei = int(withdrawal_amount_wei * self.fee_rate)
        fee_eth = float(Decimal(fee_wei) / Decimal(10**18))
        net_amount_wei = withdrawal_amount_wei - fee_wei
        net_amount_eth = float(Decimal(net_amount_wei) / Decimal(10**18))
        
        return {
            'withdrawal_amount_wei': withdrawal_amount_wei,
            'withdrawal_amount_eth': float(Decimal(withdrawal_amount_wei) / Decimal(10**18)),
            'fee_rate': self.fee_rate,
            'fee_wei': fee_wei,
            'fee_eth': fee_eth,
            'net_amount_wei': net_amount_wei,
            'net_amount_eth': net_amount_eth
        }

