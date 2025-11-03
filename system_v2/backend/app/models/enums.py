"""
枚举类型定义
"""
from enum import Enum


class ValidatorKeyStatus(str, Enum):
    """验证者密钥状态"""
    UNUSED = "unused"  # 已生成但未激活
    ACTIVE = "active"  # 已激活，准备用于存款
    PENDING = "pending"  # 已提交存款，等待链上确认
    DEPOSITED = "deposited"  # 存款已确认，等待激活
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
    """存款状态"""
    PENDING = "pending"  # 交易已提交，等待确认
    CONFIRMED = "confirmed"  # 交易已确认
    FAILED = "failed"  # 交易失败


class WithdrawalType(str, Enum):
    """提款类型"""
    PARTIAL = "partial"  # 部分提款（余额超过 32 ETH 的奖励部分）
    FULL = "full"  # 全额提款（验证者退出后的本金和奖励）

