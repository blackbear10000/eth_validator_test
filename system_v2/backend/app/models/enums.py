"""
枚举类型定义
"""
from enum import Enum


class ValidatorKeyStatus(str, Enum):
    """验证者密钥状态"""
    UNUSED = "unused"  # 已生成但未激活
    ACTIVE = "active"  # 已激活，准备用于存款
    DEPOSIT_DATA_GENERATED = "deposit_data_generated"  # 已生成 Deposit Data，等待提交存款
    UNKNOWN = "unknown"  # 交易在内存池中，等待确认
    PENDING = "pending"  # 已提交存款，等待链上确认（或在激活队列中）
    DEPOSITED = "deposited"  # 存款已确认，在 deposit queue 中等待处理
    ACTIVE_ON_CHAIN = "active_on_chain"  # 链上激活，正在验证
    EXITED = "exited"  # 已退出验证
    SLASHED = "slashed"  # 被惩罚（特殊情况）
    PENDING_EXIT = "pending_exit"  # 退出中


class ValidatorClientType(str, Enum):
    """Validator Client 类型"""
    PRYSM = "prysm"
    LIGHTHOUSE = "lighthouse"
    TEKU = "teku"


class DepositStatus(str, Enum):
    """存款交易状态"""
    # 交易阶段
    SUBMITTED = "submitted"  # 交易已提交到 mempool，等待确认
    CONFIRMED = "confirmed"  # 交易已在链上确认（但参数可能无效）
    
    # 验证阶段
    VALIDATED = "validated"  # 存款参数已验证有效，等待处理
    INVALID = "invalid"  # 存款参数无效（交易成功但参数错误）
    
    # 验证者生命周期
    PENDING_ACTIVATION = "pending_activation"  # 验证者在 beacon chain 上 pending，等待激活
    ACTIVATED = "activated"  # 验证者已激活，正在验证
    EXITING = "exiting"  # 验证者正在退出
    EXITED = "exited"  # 验证者已退出
    
    # 失败状态
    FAILED = "failed"  # 交易失败（revert 或超时）
    REJECTED = "rejected"  # 交易被拒绝（gas 不足等）
    
    # 向后兼容（已废弃，保留用于迁移）
    PENDING = "pending"  # 已废弃，等同于 SUBMITTED


class WithdrawalType(str, Enum):
    """提款类型"""
    PARTIAL = "partial"  # 部分提款（余额超过 32 ETH 的奖励部分）
    FULL = "full"  # 全额提款（验证者退出后的本金和奖励）

