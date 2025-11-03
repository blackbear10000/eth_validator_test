"""
应用配置管理
从环境变量和配置文件加载配置
"""
import os
from typing import Optional
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """应用配置"""
    
    # 应用配置
    app_name: str = "ETH Validator Management System v2"
    app_version: str = "2.0.0"
    debug: bool = False
    
    # API 配置
    api_v1_prefix: str = "/api/v1"
    cors_origins: list[str] = ["http://localhost:3000", "http://localhost:5173"]
    
    # 数据库配置
    database_url: str = "postgresql://postgres:password@localhost:5432/validator_db"
    database_echo: bool = False
    
    # Vault 配置
    vault_url: str = "http://localhost:8200"
    vault_token: str = os.getenv("VAULT_TOKEN", "dev-root-token")
    vault_mount_point: str = "secret"
    vault_key_path_prefix: str = "web3signer-keys"
    
    # Web3Signer 配置
    web3signer_url_primary: str = "http://localhost:9000"
    web3signer_url_secondary: str = "http://localhost:9001"
    web3signer_haproxy_url: str = "http://localhost:9002"
    web3signer_key_store_path: str = "/keys"
    
    # Beacon Chain API 配置
    beacon_api_url: str = "http://localhost:5052"
    beacon_api_sync_interval: int = 12  # 秒（1 epoch）
    
    # Execution Layer RPC 配置
    execution_rpc_url: Optional[str] = None  # 例如: "http://localhost:8545"
    
    # Batch Deposit Contract 配置
    batch_deposit_contract_address: Optional[str] = None
    batch_deposit_max_size: int = 100  # 单次最多 100 个验证者
    batch_deposit_gas_limit: int = 5000000
    
    # 费用配置
    fee_rate: float = 0.1  # 默认 10% 费用比例
    
    # Kurtosis 配置
    kurtosis_enclave: str = "eth-devnet"
    
    # 日志配置
    log_level: str = "INFO"
    log_format: str = "json"
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


# 全局配置实例
settings = Settings()

