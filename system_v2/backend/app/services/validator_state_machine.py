"""
验证器状态机管理服务
统一管理验证器状态转换逻辑，确保状态转换的合法性和一致性
"""
import logging
from datetime import datetime
from typing import Dict, Any, Optional, List
from sqlalchemy.orm import Session

from app.models.database import ValidatorKey
from app.models.enums import ValidatorKeyStatus

logger = logging.getLogger(__name__)

# Beacon Chain 中的 FAR_FUTURE_EPOCH 常量
FAR_FUTURE_EPOCH = 18446744073709551615


class ValidatorStateMachine:
    """
    验证器状态机
    管理验证器状态的转换规则和逻辑
    """
    
    # 定义合法的状态转换规则
    VALID_TRANSITIONS: Dict[str, List[str]] = {
        ValidatorKeyStatus.UNUSED.value: [ValidatorKeyStatus.ACTIVE.value],
        ValidatorKeyStatus.ACTIVE.value: [ValidatorKeyStatus.DEPOSIT_DATA_GENERATED.value, ValidatorKeyStatus.UNKNOWN.value, ValidatorKeyStatus.PENDING.value],
        ValidatorKeyStatus.DEPOSIT_DATA_GENERATED.value: [ValidatorKeyStatus.ACTIVE.value, ValidatorKeyStatus.PENDING.value, ValidatorKeyStatus.UNKNOWN.value],
        ValidatorKeyStatus.UNKNOWN.value: [ValidatorKeyStatus.PENDING.value, ValidatorKeyStatus.ACTIVE.value, ValidatorKeyStatus.DEPOSIT_DATA_GENERATED.value],
        ValidatorKeyStatus.PENDING.value: [ValidatorKeyStatus.DEPOSITED.value, ValidatorKeyStatus.ACTIVE.value],
        ValidatorKeyStatus.DEPOSITED.value: [ValidatorKeyStatus.PENDING.value, ValidatorKeyStatus.ACTIVE_ON_CHAIN.value],
        ValidatorKeyStatus.ACTIVE_ON_CHAIN.value: [ValidatorKeyStatus.PENDING_EXIT.value, ValidatorKeyStatus.SLASHED.value, ValidatorKeyStatus.EXITED.value],
        ValidatorKeyStatus.PENDING_EXIT.value: [ValidatorKeyStatus.EXITED.value],
        ValidatorKeyStatus.SLASHED.value: [ValidatorKeyStatus.EXITED.value],
        ValidatorKeyStatus.EXITED.value: [],  # 终态，不能再转换
    }
    
    def __init__(self, db: Session):
        """
        初始化状态机
        
        Args:
            db: 数据库会话
        """
        self.db = db
    
    def can_transition(self, from_status: str, to_status: str) -> bool:
        """
        检查是否可以进行状态转换
        
        Args:
            from_status: 当前状态
            to_status: 目标状态
            
        Returns:
            是否可以转换
        """
        allowed_transitions = self.VALID_TRANSITIONS.get(from_status, [])
        return to_status in allowed_transitions
    
    def transition(
        self,
        validator_key: ValidatorKey,
        new_status: ValidatorKeyStatus,
        reason: str = "",
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        执行状态转换
        
        Args:
            validator_key: 验证器密钥对象
            new_status: 新状态
            reason: 转换原因
            metadata: 额外的元数据（如 epoch、时间戳等）
            
        Returns:
            是否成功转换
        """
        old_status = validator_key.status
        new_status_value = new_status.value if isinstance(new_status, ValidatorKeyStatus) else new_status
        
        # 检查是否可以转换
        if not self.can_transition(old_status, new_status_value):
            logger.warning(
                f"无效的状态转换: {validator_key.pubkey[:10]}... "
                f"{old_status} -> {new_status_value} (原因: {reason})"
            )
            return False
        
        # 执行转换
        validator_key.status = new_status_value
        
        # 更新时间戳
        now = datetime.utcnow()
        if new_status_value == ValidatorKeyStatus.ACTIVE_ON_CHAIN.value and not validator_key.activated_at:
            validator_key.activated_at = now
        elif new_status_value == ValidatorKeyStatus.DEPOSITED.value and not validator_key.deposited_at:
            validator_key.deposited_at = now
        elif new_status_value == ValidatorKeyStatus.EXITED.value and not validator_key.exited_at:
            validator_key.exited_at = now
        elif new_status_value == ValidatorKeyStatus.SLASHED.value and not validator_key.slashed_at:
            validator_key.slashed_at = now
        
        # 记录状态历史
        if not validator_key.status_history:
            validator_key.status_history = []
        
        history_entry = {
            'from_status': old_status,
            'to_status': new_status_value,
            'timestamp': now.isoformat(),
            'reason': reason,
        }
        if metadata:
            history_entry['metadata'] = metadata
        
        validator_key.status_history.append(history_entry)
        
        logger.info(
            f"验证器状态已转换: {validator_key.pubkey[:10]}... "
            f"{old_status} -> {new_status_value} (原因: {reason})"
        )
        
        return True
    
    def get_status_from_beacon_data(
        self,
        validator_data: Dict[str, Any],
        current_local_status: Optional[str] = None
    ) -> ValidatorKeyStatus:
        """
        从 Beacon API 数据确定验证器状态
        
        Args:
            validator_data: Beacon API 返回的验证器数据
            current_local_status: 当前本地状态（用于辅助判断）
            
        Returns:
            对应的 ValidatorKeyStatus
        """
        validator_info = validator_data.get('validator', {})
        status_info = validator_data.get('status', '')
        
        # 如果没有 validator 字段，可能整个对象就是 validator 信息
        if not validator_info and validator_data.get('index') is not None:
            validator_info = validator_data
        
        # 根据 Beacon Chain 状态映射到本地状态
        if status_info == 'active_ongoing':
            return ValidatorKeyStatus.ACTIVE_ON_CHAIN
        
        elif status_info == 'exiting':
            return ValidatorKeyStatus.PENDING_EXIT
        
        elif status_info == 'exited_slashed':
            return ValidatorKeyStatus.SLASHED
        
        elif status_info in ['exited_unslashed', 'withdrawal_possible', 'withdrawal_done']:
            return ValidatorKeyStatus.EXITED
        
        elif status_info == 'pending_initialized':
            # pending_initialized: 存款已确认，在 deposit queue 中
            # 检查 activation_epoch 来判断是否在激活队列中
            activation_epoch = validator_info.get('activation_epoch')
            if activation_epoch and activation_epoch != FAR_FUTURE_EPOCH:
                # activation_epoch 已设置，说明在激活队列中（pending queue）
                return ValidatorKeyStatus.PENDING
            else:
                # activation_epoch 未设置，说明在 deposit queue 中
                return ValidatorKeyStatus.DEPOSITED
        
        elif status_info == 'pending_queued':
            # pending_queued: 在激活队列中，等待激活
            return ValidatorKeyStatus.PENDING
        
        else:
            # 未知状态，根据当前本地状态判断
            if current_local_status == ValidatorKeyStatus.PENDING.value:
                # 如果本地是 PENDING，但 Beacon Chain 没有返回状态，可能是刚提交还未处理
                return ValidatorKeyStatus.DEPOSITED
            elif current_local_status == ValidatorKeyStatus.DEPOSITED.value:
                # 保持 DEPOSITED 状态
                return ValidatorKeyStatus.DEPOSITED
            else:
                # 其他情况，保持原状态或返回 UNUSED
                return ValidatorKeyStatus.UNUSED
    
    def update_validator_from_beacon_data(
        self,
        validator_key: ValidatorKey,
        validator_data: Dict[str, Any]
    ) -> bool:
        """
        从 Beacon API 数据更新验证器状态（使用状态机）
        
        Args:
            validator_key: 验证器密钥对象
            validator_data: Beacon API 返回的验证器数据
            
        Returns:
            是否成功更新
        """
        try:
            # 确定新状态
            new_status = self.get_status_from_beacon_data(
                validator_data,
                current_local_status=validator_key.status
            )
            
            # 如果状态没有变化，不需要更新
            if validator_key.status == new_status.value:
                return True
            
            # 提取元数据
            validator_info = validator_data.get('validator', {})
            if not validator_info and validator_data.get('index') is not None:
                validator_info = validator_data
            
            metadata = {
                'validator_index': validator_info.get('index'),
                'activation_epoch': validator_info.get('activation_epoch'),
                'exit_epoch': validator_info.get('exit_epoch'),
                'effective_balance': validator_info.get('effective_balance'),
                'beacon_status': validator_data.get('status', ''),
            }
            
            # 执行状态转换
            return self.transition(
                validator_key,
                new_status,
                reason='beacon_sync',
                metadata=metadata
            )
            
        except Exception as e:
            logger.error(f"从 Beacon 数据更新验证器状态失败: {e}", exc_info=True)
            return False

