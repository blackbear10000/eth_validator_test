"""
存款管理服务
负责存款批次管理、状态追踪、交易记录
"""
import logging
from datetime import datetime
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session

from app.models.database import DepositTransaction, ValidatorKey
from app.models.enums import DepositStatus, ValidatorKeyStatus
from app.core.deposit_generator import DepositGenerator
from app.core.batch_deposit import BatchDepositClient
from app.core.vault_client import VaultClient
from app.services.key_management import KeyManagementService
from app.utils.exceptions import DepositGenerationError, DatabaseError

logger = logging.getLogger(__name__)


class DepositManagementService:
    """
    存款管理服务
    提供存款数据生成、批量提交、状态追踪等功能
    """
    
    def __init__(
        self,
        db: Session,
        deposit_generator: Optional[DepositGenerator] = None,
        batch_deposit_client: Optional[BatchDepositClient] = None,
        key_service: Optional[KeyManagementService] = None
    ):
        """
        初始化存款管理服务
        
        Args:
            db: 数据库会话
            deposit_generator: Deposit Data 生成器
            batch_deposit_client: Batch Deposit 客户端
            key_service: 密钥管理服务
        """
        self.db = db
        self.deposit_generator = deposit_generator or DepositGenerator()
        self.batch_deposit_client = batch_deposit_client
        self.key_service = key_service
    
    def generate_deposit_data_for_active_keys(
        self,
        count: Optional[int] = None,
        pubkeys: Optional[List[str]] = None,
        withdrawal_address: str = None,
        amount_eth: float = 32.0,
        fork_version: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        为激活的密钥生成 Deposit Data
        
        Args:
            count: 生成数量（如果不提供 pubkeys）
            pubkeys: 要生成的公钥列表（如果提供则忽略 count）
            withdrawal_address: 0x01 类型提款地址（必需）
            amount_eth: 存款金额（ETH）
            fork_version: Fork version（可选，用于自定义网络）
            
        Returns:
            Deposit Data 列表
        """
        if not withdrawal_address:
            raise ValueError("必须提供 withdrawal_address")
        
        # 更新 fork version（如果有）
        if fork_version:
            self.deposit_generator.fork_version = fork_version
            self.deposit_generator.chain_setting = self.deposit_generator._get_chain_setting()
        
        # 获取要生成 Deposit Data 的密钥
        if pubkeys:
            # 查询指定的密钥
            validator_keys = self.db.query(ValidatorKey).filter(
                ValidatorKey.pubkey.in_([pk.lower() for pk in pubkeys]),
                ValidatorKey.status == ValidatorKeyStatus.ACTIVE.value
            ).all()
            
            if len(validator_keys) != len(pubkeys):
                raise ValueError(f"部分密钥不存在或未激活")
        elif count:
            # 查询激活的密钥
            validator_keys = self.db.query(ValidatorKey).filter(
                ValidatorKey.status == ValidatorKeyStatus.ACTIVE.value
            ).order_by(ValidatorKey.created_at).limit(count).all()
            
            if len(validator_keys) < count:
                raise ValueError(f"激活的密钥不足: 需要 {count} 个，只有 {len(validator_keys)} 个")
        else:
            raise ValueError("必须提供 count 或 pubkeys 参数")
        
        # 生成 Deposit Data
        deposit_data_list = []
        for validator_key in validator_keys:
            try:
                deposit_data = self.deposit_generator.generate_deposit_data(
                    validator_key=validator_key,
                    withdrawal_address=withdrawal_address,
                    amount_eth=amount_eth
                )
                
                # 验证 Deposit Data
                if self.deposit_generator.validate_deposit_data(deposit_data):
                    deposit_data_list.append(deposit_data)
                    logger.debug(f"Deposit Data 生成成功: {validator_key.pubkey[:10]}...")
                else:
                    logger.warning(f"Deposit Data 验证失败: {validator_key.pubkey[:10]}...")
                    
            except Exception as e:
                logger.error(f"生成 Deposit Data 失败 ({validator_key.pubkey[:10]}...): {e}")
                continue
        
        logger.info(f"成功生成 {len(deposit_data_list)}/{len(validator_keys)} 个 Deposit Data")
        return deposit_data_list
    
    def submit_batch_deposits(
        self,
        deposit_data_list: List[Dict[str, Any]],
        batch_id: Optional[str] = None,
        gas_price: Optional[int] = None,
        gas_limit: Optional[int] = None,
        wait_for_confirmation: bool = False
    ) -> List[Dict[str, Any]]:
        """
        提交批量存款
        
        Args:
            deposit_data_list: Deposit Data 列表
            batch_id: 批次ID（可选）
            gas_price: Gas 价格（可选）
            gas_limit: Gas 限制（可选）
            wait_for_confirmation: 是否等待确认
            
        Returns:
            提交结果列表
        """
        if not self.batch_deposit_client:
            raise ValueError("Batch Deposit Client 未配置")
        
        # 生成批次ID（如果没有提供）
        if batch_id is None:
            batch_id = f"batch-{datetime.utcnow().strftime('%Y%m%d-%H%M%S')}"
        
        # 提交批量存款（自动分批）
        batch_results = self.batch_deposit_client.submit_multiple_batches(
            deposit_data_list,
            gas_price=gas_price,
            gas_limit=gas_limit
        )
        
        # 记录交易到数据库
        submission_results = []
        for batch_result in batch_results:
            if batch_result['status'] == 'submitted':
                # 为每个验证者创建存款交易记录
                for i, pubkey in enumerate(batch_result['pubkeys']):
                    validator_key = self.db.query(ValidatorKey).filter(
                        ValidatorKey.pubkey == pubkey.lower()
                    ).first()
                    
                    if validator_key:
                        deposit_tx = DepositTransaction(
                            pubkey=validator_key.pubkey,
                            tx_hash=batch_result['tx_hash'],
                            batch_id=batch_id,
                            status=DepositStatus.PENDING.value,
                            amount_wei=32 * 10**18,  # 32 ETH
                            amount_eth=32.0,
                            submitted_at=datetime.utcnow()
                        )
                        self.db.add(deposit_tx)
                        
                        # 更新密钥状态
                        validator_key.status = ValidatorKeyStatus.PENDING.value
                        validator_key.deposit_tx_hash = batch_result['tx_hash']
                
                submission_results.append({
                    'batch_number': batch_result['batch_number'],
                    'validator_count': batch_result['validator_count'],
                    'tx_hash': batch_result['tx_hash'],
                    'status': 'submitted',
                    'batch_id': batch_id
                })
                
                # 等待确认（如果需要）
                if wait_for_confirmation:
                    try:
                        confirmation = self.batch_deposit_client.wait_for_confirmation(
                            batch_result['tx_hash']
                        )
                        if confirmation['status'] == 'confirmed':
                            # 更新交易状态
                            self.db.query(DepositTransaction).filter(
                                DepositTransaction.tx_hash == batch_result['tx_hash']
                            ).update({
                                'status': DepositStatus.CONFIRMED.value,
                                'confirmed_at': datetime.utcnow(),
                                'block_number': confirmation['block_number']
                            })
                            
                            # 更新密钥状态
                            self.db.query(ValidatorKey).filter(
                                ValidatorKey.deposit_tx_hash == batch_result['tx_hash']
                            ).update({
                                'status': ValidatorKeyStatus.DEPOSITED.value
                            })
                    except Exception as e:
                        logger.error(f"等待交易确认失败: {e}")
            else:
                submission_results.append({
                    'batch_number': batch_result['batch_number'],
                    'validator_count': batch_result['validator_count'],
                    'status': 'failed',
                    'error': batch_result.get('error'),
                    'batch_id': batch_id
                })
        
        self.db.commit()
        logger.info(f"批量存款提交完成: {len(submission_results)} 个批次")
        
        return submission_results
    
    def get_deposit_transactions(
        self,
        pubkey: Optional[str] = None,
        batch_id: Optional[str] = None,
        status: Optional[DepositStatus] = None,
        limit: Optional[int] = None,
        offset: int = 0
    ) -> tuple[List[DepositTransaction], int]:
        """
        查询存款交易记录
        
        Args:
            pubkey: 验证者公钥（可选）
            batch_id: 批次ID（可选）
            status: 状态（可选）
            limit: 限制数量
            offset: 偏移量
            
        Returns:
            (交易列表, 总数) 元组
        """
        query = self.db.query(DepositTransaction)
        
        if pubkey:
            query = query.filter(DepositTransaction.pubkey == pubkey.lower())
        if batch_id:
            query = query.filter(DepositTransaction.batch_id == batch_id)
        if status:
            query = query.filter(DepositTransaction.status == status.value)
        
        # 获取总数
        total = query.count()
        
        # 按提交时间倒序（必须在 limit/offset 之前）
        query = query.order_by(DepositTransaction.submitted_at.desc())
        
        # 应用分页
        if limit:
            query = query.limit(limit).offset(offset)
        
        transactions = query.all()
        return transactions, total
    
    def update_deposit_status(
        self,
        tx_hash: str,
        status: DepositStatus,
        block_number: Optional[int] = None
    ) -> DepositTransaction:
        """
        更新存款交易状态
        
        Args:
            tx_hash: 交易哈希
            status: 新状态
            block_number: 确认区块号（可选）
            
        Returns:
            更新后的交易对象
        """
        transaction = self.db.query(DepositTransaction).filter(
            DepositTransaction.tx_hash == tx_hash
        ).first()
        
        if not transaction:
            raise ValueError(f"交易不存在: {tx_hash}")
        
        transaction.status = status.value
        if status == DepositStatus.CONFIRMED:
            transaction.confirmed_at = datetime.utcnow()
            if block_number:
                transaction.block_number = block_number
            
            # 更新密钥状态
            validator_key = self.db.query(ValidatorKey).filter(
                ValidatorKey.pubkey == transaction.pubkey
            ).first()
            
            if validator_key and validator_key.status == ValidatorKeyStatus.PENDING.value:
                validator_key.status = ValidatorKeyStatus.DEPOSITED.value
        
        self.db.commit()
        
        logger.info(f"存款交易状态已更新: {tx_hash} -> {status.value}")
        return transaction

