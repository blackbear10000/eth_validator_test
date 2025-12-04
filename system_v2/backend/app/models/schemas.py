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
    deposit_message_root: str
    deposit_data_root: str
    fork_version: str
    network_name: str
    deposit_cli_version: str


class BatchDepositDeployRequest(BaseModel):
    """Batch Deposit 合约部署请求"""
    rpc_url: Optional[str] = Field(None, description="RPC URL（可选，优先从 Kurtosis 网络获取）")
    deployer_private_key: str = Field(..., description="部署者私钥")
    network_name: str = Field(..., description="网络名称")
    deposit_contract_address: Optional[str] = Field(None, description="官方 Deposit 合约地址（可选，优先从网络配置获取）")
    initial_fee: Optional[int] = Field(0, description="初始费用（wei，必须是 gwei 的倍数，默认 0）")
    gas_price: Optional[int] = Field(None, description="Gas 价格（可选）")
    gas_limit: Optional[int] = Field(None, description="Gas 限制（可选）")


class BatchDepositContractResponse(BaseModel):
    """Batch Deposit 合约响应"""
    id: int
    contract_address: str
    network_name: str
    rpc_url: str
    deployer_address: str
    deployment_tx_hash: str
    block_number: Optional[int] = None
    gas_used: Optional[int] = None
    deployed_at: datetime
    notes: Optional[str] = None

    model_config = {"from_attributes": True}


class BatchContractStatistics(BaseModel):
    """Batch Deposit 合约统计数据"""
    contract_id: int
    contract_address: str
    deposit_count: int = Field(0, description="存款交易数量")
    total_amount_eth: float = Field(0.0, description="总存款金额（ETH）")
    validator_count: int = Field(0, description="验证者数量（去重）")
    contract_fee_wei: Optional[int] = Field(None, description="合约当前费用（wei）")
    contract_fee_gwei: Optional[float] = Field(None, description="合约当前费用（gwei）")
    contract_balance_wei: Optional[int] = Field(None, description="合约余额（wei）")
    contract_balance_eth: Optional[float] = Field(None, description="合约余额（ETH）")
    is_paused: Optional[bool] = Field(None, description="合约是否暂停")
    owner_address: Optional[str] = Field(None, description="合约所有者地址")


class BatchDepositSubmit(BaseModel):
    """批量存款提交请求"""
    deposit_data_list: List[DepositDataResponse]
    from_address: str = Field(..., description="发送交易的钱包地址")
    private_key: Optional[str] = Field(None, description="私钥（用于签名交易）")
    deposit_type: str = Field("batch", description="存款类型: official 或 batch")
    batch_contract_address: Optional[str] = Field(None, description="Batch Deposit 合约地址（deposit_type 为 batch 时必需）")
    official_deposit_contract_address: Optional[str] = Field(None, description="官方 Deposit 合约地址（deposit_type 为 official 时可选）")


class DepositTransactionResponse(BaseModel):
    """存款交易响应"""
    id: int
    pubkey: str
    tx_hash: str
    batch_id: Optional[str] = None
    status: DepositStatus
    amount_eth: float
    amount_wei: Optional[int] = None
    submitted_at: datetime
    confirmed_at: Optional[datetime] = None
    validated_at: Optional[datetime] = None
    block_number: Optional[int] = None
    validator_index: Optional[int] = None
    activation_epoch: Optional[int] = None
    exit_epoch: Optional[int] = None
    effective_balance_gwei: Optional[int] = None
    validation_error: Optional[str] = None
    status_history: Optional[List[dict]] = None
    notes: Optional[str] = None

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
    deposit_contract_address: Optional[str] = None
    fork_version: Optional[str] = None
    network_name: Optional[str] = None
    error: Optional[str] = None
    status: Optional[Dict[str, Any]] = None

