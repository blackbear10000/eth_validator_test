"""
存款交易状态同步调度器
定期同步交易状态和验证者状态
"""
import logging
import threading
import time
from typing import Optional
from sqlalchemy.orm import Session

from app.models.database import DepositTransaction
from app.models.enums import DepositStatus
from app.services.deposit_management import DepositManagementService
from app.services.deposit_validation import DepositValidationService
from app.core.beacon_api import BeaconAPIClient
from app.dependencies import get_db

logger = logging.getLogger(__name__)


class DepositSyncScheduler:
    """
    存款交易状态同步调度器
    定期同步交易状态和验证者状态
    """
    
    def __init__(
        self,
        db: Optional[Session] = None,
        deposit_service: Optional[DepositManagementService] = None,
        validation_service: Optional[DepositValidationService] = None
    ):
        """
        初始化调度器
        
        Args:
            db: 数据库会话（可选）
            deposit_service: 存款管理服务（可选）
            validation_service: 验证服务（可选）
        """
        self.db = db
        self.deposit_service = deposit_service
        self.validation_service = validation_service
        self.running = False
        self.thread: Optional[threading.Thread] = None
        
        # 同步间隔（秒）
        self.pending_check_interval = 30  # 每 30 秒检查一次待确认交易
        self.validation_interval = 300  # 每 5 分钟验证一次已确认但未验证的交易
        self.status_sync_interval = 600  # 每 10 分钟同步一次验证者状态
        
        # 上次执行时间
        self.last_pending_check = 0
        self.last_validation = 0
        self.last_status_sync = 0
    
    def start(self):
        """启动调度器"""
        if self.running:
            logger.warning("调度器已在运行")
            return
        
        self.running = True
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()
        logger.info("存款交易状态同步调度器已启动")
    
    def stop(self):
        """停止调度器"""
        self.running = False
        if self.thread:
            self.thread.join(timeout=5)
        logger.info("存款交易状态同步调度器已停止")
    
    def _run(self):
        """调度器主循环"""
        while self.running:
            try:
                current_time = time.time()
                
                # 1. 同步待确认交易（每 30 秒）
                if current_time - self.last_pending_check >= self.pending_check_interval:
                    self.sync_pending_transactions()
                    self.last_pending_check = current_time
                
                # 2. 验证已确认交易（每 5 分钟）
                if current_time - self.last_validation >= self.validation_interval:
                    self.validate_confirmed_transactions()
                    self.last_validation = current_time
                
                # 3. 同步验证者状态（每 10 分钟）
                if current_time - self.last_status_sync >= self.status_sync_interval:
                    self.sync_validator_statuses()
                    self.last_status_sync = current_time
                
                # 休眠 10 秒
                time.sleep(10)
                
            except Exception as e:
                logger.error(f"调度器执行出错: {e}", exc_info=True)
                time.sleep(30)  # 出错后等待更长时间
    
    def sync_pending_transactions(self):
        """同步待确认交易"""
        try:
            if not self.deposit_service:
                db = self.db or next(get_db())
                from app.services.deposit_management import DepositManagementService
                from app.core.vault_client import VaultClient
                from app.services.key_management import KeyManagementService
                from app.core.deposit_generator import DepositGenerator
                
                vault_client = VaultClient()
                key_service = KeyManagementService(db, vault_client)
                deposit_generator = DepositGenerator(vault_client)
                self.deposit_service = DepositManagementService(
                    db,
                    deposit_generator,
                    None,
                    key_service
                )
            
            result = self.deposit_service.sync_transaction_status(
                validate_immediately=False  # 只同步确认状态，不立即验证
            )
            
            logger.debug(f"同步待确认交易完成: {result}")
            
        except Exception as e:
            logger.error(f"同步待确认交易失败: {e}", exc_info=True)
    
    def validate_confirmed_transactions(self):
        """验证已确认但未验证的交易"""
        try:
            db = self.db or next(get_db())
            
            # 查询已确认但未验证的交易
            transactions = db.query(DepositTransaction).filter(
                DepositTransaction.status == DepositStatus.CONFIRMED.value
            ).all()
            
            if not transactions:
                return
            
            # 获取 RPC URL
            from app.services.network_service import NetworkService
            from app.config import settings
            from web3 import Web3
            
            network_service = NetworkService()
            rpc_endpoints = network_service.get_rpc_endpoints()
            rpc_url = rpc_endpoints.get("rpc_url") or settings.execution_rpc_url
            
            if not rpc_url:
                logger.warning("无法获取 RPC URL，跳过验证")
                return
            
            # 连接 Web3
            web3 = Web3(Web3.HTTPProvider(rpc_url))
            if not web3.is_connected():
                logger.warning(f"无法连接到 RPC: {rpc_url}")
                return
            
            # 初始化验证服务
            if not self.validation_service:
                beacon_api = BeaconAPIClient()
                self.validation_service = DepositValidationService(
                    db=db,
                    beacon_api=beacon_api,
                    web3=web3
                )
            
            # 批量验证
            result = self.validation_service.batch_validate_transactions(
                transactions,
                rpc_url
            )
            
            logger.info(
                f"验证已确认交易完成: 总计 {result['total']} 个，"
                f"已验证 {result['validated']} 个，无效 {result['invalid']} 个，"
                f"激活 {result['activated']} 个，等待激活 {result['pending_activation']} 个，"
                f"已退出 {result['exited']} 个"
            )
            
        except Exception as e:
            logger.error(f"验证已确认交易失败: {e}", exc_info=True)
    
    def sync_validator_statuses(self):
        """同步验证者状态（pending/activated/exiting/exited）"""
        try:
            db = self.db or next(get_db())
            
            # 查询需要同步状态的交易（已验证、等待激活、已激活、退出中）
            transactions = db.query(DepositTransaction).filter(
                DepositTransaction.status.in_([
                    DepositStatus.VALIDATED.value,
                    DepositStatus.PENDING_ACTIVATION.value,
                    DepositStatus.ACTIVATED.value,
                    DepositStatus.EXITING.value
                ])
            ).all()
            
            if not transactions:
                return
            
            # 获取 RPC URL
            from app.services.network_service import NetworkService
            from app.config import settings
            from web3 import Web3
            
            network_service = NetworkService()
            rpc_endpoints = network_service.get_rpc_endpoints()
            rpc_url = rpc_endpoints.get("rpc_url") or settings.execution_rpc_url
            
            if not rpc_url:
                logger.warning("无法获取 RPC URL，跳过状态同步")
                return
            
            # 连接 Web3
            web3 = Web3(Web3.HTTPProvider(rpc_url))
            if not web3.is_connected():
                logger.warning(f"无法连接到 RPC: {rpc_url}")
                return
            
            # 初始化验证服务
            if not self.validation_service:
                beacon_api = BeaconAPIClient()
                self.validation_service = DepositValidationService(
                    db=db,
                    beacon_api=beacon_api,
                    web3=web3
                )
            
            # 批量同步状态
            synced_count = 0
            for tx in transactions:
                try:
                    result = self.validation_service.validate_deposit_transaction(tx, rpc_url)
                    if result.get('is_valid'):
                        synced_count += 1
                except Exception as e:
                    logger.warning(f"同步交易 {tx.tx_hash} 状态失败: {e}")
            
            logger.info(f"同步验证者状态完成: 同步 {synced_count}/{len(transactions)} 个交易")
            
        except Exception as e:
            logger.error(f"同步验证者状态失败: {e}", exc_info=True)


# 全局调度器实例
_scheduler: Optional[DepositSyncScheduler] = None


def get_scheduler() -> DepositSyncScheduler:
    """获取全局调度器实例"""
    global _scheduler
    if _scheduler is None:
        _scheduler = DepositSyncScheduler()
    return _scheduler


def start_scheduler():
    """启动全局调度器"""
    scheduler = get_scheduler()
    scheduler.start()


def stop_scheduler():
    """停止全局调度器"""
    global _scheduler
    if _scheduler:
        _scheduler.stop()
        _scheduler = None

