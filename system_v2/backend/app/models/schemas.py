"""
Pydantic Schemas
用于 API 请求和响应的数据验证
"""
from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, validator

from .enums import ValidatorKeyStatus, ValidatorClientType, DepositStatus, WithdrawalType


# ==================== 密钥相关 Schemas ====================

class ValidatorKeyBase(BaseModel):
    """验证者密钥基础 Schema"""
    withdrawal_address: Optional[str] = None
    client_type: Optional[ValidatorClientType] = None
    notes: Optional[str] = None


class ValidatorKeyCreate(ValidatorKeyBase):
    """创建验证者密钥（批量生成时使用）"""
    count: int = Field(gt=0, le=10000, description="生成密钥数量")
    batch_id: Optional[str] = None


class ValidatorKeyResponse(ValidatorKeyBase):
    """验证者密钥响应 Schema"""
    pubkey: str
    withdrawal_pubkey: str
    status: ValidatorKeyStatus
    index: int
    signing_key_path: str
    batch_id: Optional[str] = None
    created_at: datetime
    activated_at: Optional[datetime] = None
    deposited_at: Optional[datetime] = None
    exited_at: Optional[datetime] = None
    deposit_tx_hash: Optional[str] = None

    model_config = {"from_attributes": True}


class ValidatorKeyListResponse(BaseModel):
    """密钥列表响应"""
    total: int
    items: List[ValidatorKeyResponse]


class ValidatorKeyStatusUpdate(BaseModel):
    """更新密钥状态"""
    status: ValidatorKeyStatus


class BatchActivateKeys(BaseModel):
    """批量激活密钥"""
    count: int = Field(gt=0, description="激活密钥数量")
    batch_id: Optional[str] = None


# ==================== 存款相关 Schemas ====================

class DepositDataGenerate(BaseModel):
    """生成 Deposit Data 请求"""
    pubkeys: List[str] = Field(..., description="验证者公钥列表")
    withdrawal_address: str = Field(..., description="0x01 类型提款地址")
    fork_version: Optional[str] = None  # 如果为空则自动检测
    amount_eth: float = Field(default=32.0, ge=32.0, description="存款金额（ETH）")


class DepositDataResponse(BaseModel):
    """Deposit Data 响应"""
    pubkey: str
    withdrawal_credentials: str
    amount: int
    signature: str
    deposit_data_root: str
    fork_version: str


class BatchDepositSubmit(BaseModel):
    """批量存款提交请求"""
    deposit_data_list: List[DepositDataResponse]
    from_address: str = Field(..., description="发送交易的钱包地址")
    private_key: Optional[str] = Field(None, description="私钥（用于签名交易）")


class DepositTransactionResponse(BaseModel):
    """存款交易响应"""
    id: int
    pubkey: str
    tx_hash: str
    batch_id: Optional[str] = None
    status: DepositStatus
    amount_eth: float
    submitted_at: datetime
    confirmed_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


# ==================== 客户端相关 Schemas ====================

class ClientInstanceCreate(BaseModel):
    """创建客户端实例"""
    name: str = Field(..., min_length=1, max_length=128)
    client_type: ValidatorClientType
    beacon_api_url: Optional[str] = None
    grpc_endpoint: Optional[str] = None
    web3signer_url: str = Field(default="http://localhost:9002")
    notes: Optional[str] = None


class ClientInstanceResponse(BaseModel):
    """客户端实例响应"""
    id: int
    name: str
    client_type: ValidatorClientType
    beacon_api_url: Optional[str] = None
    grpc_endpoint: Optional[str] = None
    web3signer_url: str
    is_active: bool
    status: str
    created_at: datetime
    key_count: int = 0

    model_config = {"from_attributes": True}


class ClientKeyAssignment(BaseModel):
    """客户端密钥分配"""
    pubkeys: List[str] = Field(..., description="要分配的验证者公钥列表")


# ==================== 监控相关 Schemas ====================

class SystemHealthResponse(BaseModel):
    """系统健康状态响应"""
    vault: bool
    postgresql: bool
    web3signer_primary: bool
    web3signer_secondary: bool
    haproxy: bool
    beacon_api: bool
    overall: bool


class ValidatorPerformanceResponse(BaseModel):
    """验证者性能响应"""
    pubkey: str
    status: str
    balance_eth: float
    effective_balance_eth: float
    total_rewards_eth: float
    total_withdrawals_eth: float
    activation_epoch: Optional[int] = None
    exit_epoch: Optional[int] = None


class SystemOverviewResponse(BaseModel):
    """系统概览响应"""
    total_keys: int
    keys_by_status: dict[str, int]
    total_deposits: int
    active_validators: int
    total_rewards_eth: float
    system_health: SystemHealthResponse


# ==================== 退出相关 Schemas ====================

class ExitRequest(BaseModel):
    """退出请求"""
    pubkey: str
    epoch: Optional[int] = None


class ExitResponse(BaseModel):
    """退出响应"""
    pubkey: str
    status: str
    exit_data: Optional[dict] = None


# ==================== 取款相关 Schemas ====================

class WithdrawalEventResponse(BaseModel):
    """取款事件响应"""
    id: int
    pubkey: str
    withdrawal_type: str
    amount_eth: float
    fee_eth: float
    net_amount_eth: float
    withdrawn_at: datetime
    slot: Optional[int] = None
    epoch: Optional[int] = None

    model_config = {"from_attributes": True}


# ==================== 网络管理相关 Schemas ====================

class NetworkStatusResponse(BaseModel):
    """网络状态响应"""
    enclave_name: str
    status: str
    is_running: bool
    error: Optional[str] = None
    enclave_info: Optional[Dict[str, Any]] = None
    raw_output: Optional[str] = None


class NetworkInfoResponse(BaseModel):
    """网络信息响应"""
    enclave_name: str
    genesis: Optional[Dict[str, Any]] = None
    fork_schedule: Optional[Dict[str, Any]] = None
    beacon_api_url: Optional[str] = None
    error: Optional[str] = None
    status: Optional[Dict[str, Any]] = None

