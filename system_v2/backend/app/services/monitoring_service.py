"""
监控服务
收集和聚合系统指标
"""
import logging
from typing import Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.models.database import ValidatorKey, DepositTransaction, WithdrawalEvent
from app.models.enums import ValidatorKeyStatus
from app.core.vault_client import VaultClient
from app.core.web3signer_client import Web3SignerClient
from app.core.beacon_api import BeaconAPIClient

logger = logging.getLogger(__name__)


class MonitoringService:
    """监控服务"""
    
    def __init__(self, db: Session):
        self.db = db
        self.vault_client = VaultClient()
        self.web3signer_client = Web3SignerClient()
        self.beacon_api = BeaconAPIClient()
    
    def get_system_health(self) -> Dict[str, bool]:
        """获取系统健康状态"""
        return {
            'vault': self.vault_client.health_check(),
            'web3signer_primary': self.web3signer_client.health_check("primary"),
            'web3signer_secondary': self.web3signer_client.health_check("secondary"),
            'haproxy': self.web3signer_client.health_check("haproxy"),
            'beacon_api': self.beacon_api.health_check(),
            'postgresql': True  # 简化处理
        }
    
    def get_statistics(self) -> Dict[str, Any]:
        """获取系统统计信息"""
        stats = {
            'total_keys': self.db.query(ValidatorKey).count(),
            'keys_by_status': {},
            'total_deposits': self.db.query(DepositTransaction).count(),
            'total_withdrawals': self.db.query(WithdrawalEvent).count(),
        }
        
        # 按状态统计密钥
        for status in ValidatorKeyStatus:
            count = self.db.query(ValidatorKey).filter(
                ValidatorKey.status == status.value
            ).count()
            stats['keys_by_status'][status.value] = count
        
        return stats

