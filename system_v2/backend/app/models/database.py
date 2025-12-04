"""
数据库模型定义
使用 SQLAlchemy ORM 定义所有数据库表结构
"""
from datetime import datetime
from typing import Optional
from sqlalchemy import (
    Column, Integer, String, Text, DateTime, ForeignKey, 
    Numeric, Boolean, Index, UniqueConstraint, JSON
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

from .enums import ValidatorKeyStatus, ValidatorClientType, DepositStatus, WithdrawalType

Base = declarative_base()


class ValidatorKey(Base):
    """
    验证者密钥元数据表
    存储验证者密钥的所有元数据信息，私钥存储在 Vault 中
    """
    __tablename__ = "validator_keys"

    # 主键
    pubkey = Column(String(98), primary_key=True, comment="验证者公钥 (BLS12-381, 0x开头, 96字符)")

    # 密钥信息
    withdrawal_pubkey = Column(String(98), nullable=False, comment="提款公钥 (BLS12-381)")
    signing_key_path = Column(String(64), nullable=False, comment="签名密钥派生路径 (m/12381/3600/{index}/0/0)")
    index = Column(Integer, nullable=False, comment="密钥派生索引")
    batch_id = Column(String(64), nullable=True, index=True, comment="批次ID，用于批量操作")

    # 状态信息
    status = Column(
        String(32),
        nullable=False,
        default=ValidatorKeyStatus.UNUSED.value,
        index=True,
        comment="密钥状态: unused/active/pending/deposited/active_on_chain/exited"
    )

    # 时间戳
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True, comment="创建时间")
    activated_at = Column(DateTime, nullable=True, comment="激活时间")
    deposited_at = Column(DateTime, nullable=True, comment="存款时间")
    exited_at = Column(DateTime, nullable=True, comment="退出时间")

    # 提款地址
    withdrawal_address = Column(String(42), nullable=True, comment="0x01 类型提款地址 (Execution Address)")

    # 客户端关联
    client_type = Column(String(32), nullable=True, index=True, comment="关联的客户端类型: prysm/lighthouse/teku")

    # 存款信息
    deposit_tx_hash = Column(String(66), nullable=True, comment="存款交易哈希")

    # 备注
    notes = Column(Text, nullable=True, comment="备注信息")

    # 助记词（加密存储）
    mnemonic_encrypted = Column(Text, nullable=True, comment="加密后的助记词（同一批次共享）")
    mnemonic_salt = Column(String(64), nullable=True, comment="加密盐值")

    # 关系
    client_keys = relationship("ValidatorClientKey", back_populates="validator_key", cascade="all, delete-orphan")
    deposits = relationship("DepositTransaction", back_populates="validator_key")
    withdrawals = relationship("WithdrawalEvent", back_populates="validator_key")

    def __repr__(self):
        return f"<ValidatorKey(pubkey={self.pubkey[:10]}..., status={self.status})>"


class ValidatorClientKey(Base):
    """
    客户端-密钥映射表
    追踪哪些密钥关联到哪个 Validator Client
    """
    __tablename__ = "validator_client_keys"

    id = Column(Integer, primary_key=True, autoincrement=True)
    client_id = Column(Integer, ForeignKey("client_instances.id"), nullable=False, index=True, comment="客户端实例ID")
    pubkey = Column(String(98), ForeignKey("validator_keys.pubkey"), nullable=False, index=True, comment="验证者公钥")
    
    status = Column(String(32), nullable=False, default="active", comment="关联状态: active/removed")
    added_at = Column(DateTime, nullable=False, default=datetime.utcnow, comment="添加时间")
    removed_at = Column(DateTime, nullable=True, comment="移除时间")

    # 关系
    client_instance = relationship("ClientInstance", back_populates="client_keys")
    validator_key = relationship("ValidatorKey", back_populates="client_keys")

    # 唯一约束：同一个客户端不能重复添加同一个密钥
    __table_args__ = (
        UniqueConstraint('client_id', 'pubkey', name='uq_client_pubkey'),
        Index('idx_client_pubkey', 'client_id', 'pubkey'),
    )

    def __repr__(self):
        return f"<ValidatorClientKey(client_id={self.client_id}, pubkey={self.pubkey[:10]}...)>"


class DepositTransaction(Base):
    """
    存款交易记录表
    记录每个验证者的存款交易信息
    """
    __tablename__ = "deposit_transactions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    pubkey = Column(String(98), ForeignKey("validator_keys.pubkey"), nullable=False, index=True, comment="验证者公钥")
    
    # 交易信息
    tx_hash = Column(String(66), nullable=False, unique=True, index=True, comment="交易哈希")
    batch_id = Column(String(64), nullable=True, index=True, comment="批次ID（如果使用 Batch Deposit）")
    status = Column(
        String(32),
        nullable=False,
        default=DepositStatus.SUBMITTED.value,
        index=True,
        comment="存款状态: submitted/confirmed/validated/invalid/pending_activation/activated/exiting/exited/failed/rejected"
    )
    
    # 存款金额
    amount_wei = Column(Numeric(78, 0), nullable=False, comment="存款金额（wei）")
    amount_eth = Column(Numeric(20, 8), nullable=False, comment="存款金额（ETH）")

    # 时间戳
    submitted_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True, comment="提交时间")
    confirmed_at = Column(DateTime, nullable=True, comment="确认时间")
    validated_at = Column(DateTime, nullable=True, comment="验证时间")
    block_number = Column(Integer, nullable=True, comment="确认区块号")

    # Beacon Chain 信息
    validator_index = Column(Integer, nullable=True, index=True, comment="验证者索引（beacon chain）")
    activation_epoch = Column(Integer, nullable=True, comment="激活 epoch")
    exit_epoch = Column(Integer, nullable=True, comment="退出 epoch")
    effective_balance_gwei = Column(Numeric(20, 0), nullable=True, comment="有效余额（gwei）")
    
    # 验证错误信息
    validation_error = Column(Text, nullable=True, comment="验证错误信息（如果无效）")
    
    # 状态历史（用于审计）
    status_history = Column(JSON, nullable=True, comment="状态变更历史")

    # 备注
    notes = Column(Text, nullable=True, comment="备注信息")

    # 关系
    validator_key = relationship("ValidatorKey", back_populates="deposits")

    def __repr__(self):
        return f"<DepositTransaction(tx_hash={self.tx_hash[:10]}..., status={self.status})>"


class WithdrawalEvent(Base):
    """
    提款事件记录表
    记录验证者的提款事件（部分提款和全额提款）
    """
    __tablename__ = "withdrawal_events"

    id = Column(Integer, primary_key=True, autoincrement=True)
    pubkey = Column(String(98), ForeignKey("validator_keys.pubkey"), nullable=False, index=True, comment="验证者公钥")
    
    # 提款信息
    withdrawal_type = Column(
        String(32),
        nullable=False,
        comment="提款类型: partial/full"
    )
    amount_wei = Column(Numeric(78, 0), nullable=False, comment="提款金额（wei）")
    amount_eth = Column(Numeric(20, 8), nullable=False, comment="提款金额（ETH）")
    
    # 费用扣除
    fee_wei = Column(Numeric(78, 0), nullable=False, default=0, comment="扣除的费用（wei）")
    fee_eth = Column(Numeric(20, 8), nullable=False, default=0, comment="扣除的费用（ETH）")
    fee_rate = Column(Numeric(5, 4), nullable=False, default=0.1, comment="费用比例（默认10%）")
    
    # 链上信息
    withdrawal_index = Column(Integer, nullable=True, comment="提款索引（链上）")
    slot = Column(Numeric(20, 0), nullable=True, comment="提款发生的 slot")
    epoch = Column(Numeric(20, 0), nullable=True, comment="提款发生的 epoch")
    block_number = Column(Integer, nullable=True, comment="确认区块号")
    
    # 时间戳
    withdrawn_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True, comment="提款时间")
    confirmed_at = Column(DateTime, nullable=True, comment="确认时间")
    
    # 关系
    validator_key = relationship("ValidatorKey", back_populates="withdrawals")

    def __repr__(self):
        return f"<WithdrawalEvent(pubkey={self.pubkey[:10]}..., amount_eth={self.amount_eth})>"


class ClientInstance(Base):
    """
    Validator Client 实例表
    记录所有部署的 Validator Client 实例信息
    """
    __tablename__ = "client_instances"

    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # 客户端信息
    name = Column(String(128), nullable=False, unique=True, comment="客户端实例名称")
    client_type = Column(
        String(32),
        nullable=False,
        index=True,
        comment="客户端类型: prysm/lighthouse/teku"
    )
    
    # 配置信息
    beacon_api_url = Column(String(256), nullable=True, comment="Beacon API URL")
    grpc_endpoint = Column(String(256), nullable=True, comment="gRPC 端点")
    web3signer_url = Column(String(256), nullable=False, comment="Web3Signer URL (通过 HAProxy)")
    
    # 状态信息
    is_active = Column(Boolean, nullable=False, default=True, index=True, comment="是否活跃")
    status = Column(String(32), nullable=False, default="stopped", comment="运行状态: running/stopped/error")
    
    # 时间戳
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True, comment="创建时间")
    started_at = Column(DateTime, nullable=True, comment="启动时间")
    last_seen_at = Column(DateTime, nullable=True, comment="最后活跃时间")
    
    # 配置路径
    config_path = Column(String(512), nullable=True, comment="配置文件路径")
    pubkey_persistence_path = Column(String(512), nullable=True, comment="Public Key Persistence 文件路径")
    
    # 备注
    notes = Column(Text, nullable=True, comment="备注信息")

    # 关系
    client_keys = relationship("ValidatorClientKey", back_populates="client_instance", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<ClientInstance(name={self.name}, type={self.client_type}, status={self.status})>"


class BatchDepositContract(Base):
    """
    Batch Deposit 合约记录表
    记录已部署的 Batch Deposit 合约信息
    """
    __tablename__ = "batch_deposit_contracts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # 合约信息
    contract_address = Column(String(42), nullable=False, unique=True, index=True, comment="合约地址")
    network_name = Column(String(64), nullable=False, index=True, comment="网络名称（如 kurtosis-devnet, mainnet）")
    rpc_url = Column(String(256), nullable=False, comment="关联的 RPC URL")
    
    # 部署信息
    deployer_address = Column(String(42), nullable=False, comment="部署者地址")
    deployment_tx_hash = Column(String(66), nullable=False, unique=True, index=True, comment="部署交易哈希")
    block_number = Column(Integer, nullable=True, comment="部署区块号")
    gas_used = Column(Numeric(20, 0), nullable=True, comment="部署使用的 Gas")
    
    # 时间戳
    deployed_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True, comment="部署时间")
    
    # 备注
    notes = Column(Text, nullable=True, comment="备注信息")
    
    # 唯一约束：同一网络不应该有多个活跃合约（可选）
    __table_args__ = (
        Index('idx_network_contract', 'network_name', 'contract_address'),
    )

    def __repr__(self):
        return f"<BatchDepositContract(address={self.contract_address[:10]}..., network={self.network_name})>"

