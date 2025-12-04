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
            fork_version: Fork version（可选，如果为空则从 Beacon API 获取）
            
        Returns:
            Deposit Data 列表
        """
        if not withdrawal_address:
            raise ValueError("必须提供 withdrawal_address")
        
        # 如果没有提供 fork_version，尝试从 Beacon API 获取
        if not fork_version:
            try:
                from app.core.beacon_api import BeaconAPIClient
                beacon_api = BeaconAPIClient()
                fork_version = beacon_api.get_fork_version()
                logger.info(f"从 Beacon API 获取 fork_version: {fork_version}")
            except Exception as e:
                logger.warning(f"无法从 Beacon API 获取 fork_version: {e}，使用默认值")
                # 如果获取失败，使用默认值（mainnet）
                fork_version = None
        
        # 更新 fork version（如果有）
        if fork_version:
            # 移除 0x 前缀（如果存在）
            fork_version_clean = fork_version.replace('0x', '') if isinstance(fork_version, str) else fork_version
            # 更新 deposit_generator 的 fork_version 和 network
            self.deposit_generator.fork_version = fork_version_clean
            self.deposit_generator.network = 'kurtosis'  # 对于自定义 fork_version，使用 kurtosis 网络
            self.deposit_generator.chain_setting = self.deposit_generator._get_chain_setting()
            logger.info(f"使用自定义 fork_version: {fork_version_clean}")
        
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
        saved_count = 0
        failed_count = 0
        
        for batch_result in batch_results:
            logger.info(f"处理批次结果: 批次 {batch_result.get('batch_number')}, 状态: {batch_result.get('status')}")
            
            if batch_result['status'] == 'submitted':
                pubkeys = batch_result.get('pubkeys', [])
                logger.info(f"批次包含 {len(pubkeys)} 个验证者")
                
                if not pubkeys:
                    logger.warning(f"批次 {batch_result.get('batch_number')} 没有 pubkeys 数据")
                    submission_results.append({
                        'batch_number': batch_result['batch_number'],
                        'validator_count': batch_result['validator_count'],
                        'tx_hash': batch_result['tx_hash'],
                        'status': 'submitted',
                        'batch_id': batch_id,
                        'warning': '批次没有 pubkeys 数据，无法创建存款记录'
                    })
                else:
                    # 为每个验证者创建存款交易记录
                    for i, pubkey in enumerate(pubkeys):
                        try:
                            # 规范化 pubkey：移除 0x 前缀（如果有），转为小写
                            pubkey_raw = pubkey
                            pubkey_normalized = pubkey_raw.lower().replace('0x', '')
                            # 数据库中的 pubkey 格式是 0x + 96字符，所以需要添加 0x 前缀
                            pubkey_db_format = f"0x{pubkey_normalized}" if not pubkey_normalized.startswith('0x') else pubkey_normalized
                            
                            # 查找对应的验证者密钥（尝试两种格式）
                            validator_key = self.db.query(ValidatorKey).filter(
                                (ValidatorKey.pubkey == pubkey_db_format) | 
                                (ValidatorKey.pubkey == pubkey_normalized)
                            ).first()
                            
                            if not validator_key:
                                # 如果还是找不到，尝试直接匹配原始格式
                                validator_key = self.db.query(ValidatorKey).filter(
                                    ValidatorKey.pubkey == pubkey_raw.lower()
                                ).first()
                            
                            if not validator_key:
                                logger.warning(f"未找到验证者密钥: {pubkey[:20]}... (规范化后: {pubkey_normalized[:20]}...)")
                                failed_count += 1
                                continue
                            
                            deposit_tx = DepositTransaction(
                                pubkey=validator_key.pubkey,
                                tx_hash=batch_result['tx_hash'],
                                batch_id=batch_id,
                                status=DepositStatus.SUBMITTED.value,
                                amount_wei=32 * 10**18,  # 32 ETH
                                amount_eth=32.0,
                                submitted_at=datetime.utcnow()
                            )
                            self.db.add(deposit_tx)
                            
                            # 更新密钥状态
                            validator_key.status = ValidatorKeyStatus.PENDING.value
                            validator_key.deposit_tx_hash = batch_result['tx_hash']
                            saved_count += 1
                            
                        except Exception as e:
                            logger.error(f"保存验证者 {pubkey[:20] if pubkey else 'unknown'}... 的存款记录失败: {e}", exc_info=True)
                            failed_count += 1
                    
                    submission_results.append({
                        'batch_number': batch_result['batch_number'],
                        'validator_count': batch_result['validator_count'],
                        'tx_hash': batch_result['tx_hash'],
                        'status': 'submitted',
                        'batch_id': batch_id,
                        'saved_count': saved_count
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
                logger.warning(f"批次提交失败: {batch_result.get('error')}")
                submission_results.append({
                    'batch_number': batch_result['batch_number'],
                    'validator_count': batch_result['validator_count'],
                    'status': 'failed',
                    'error': batch_result.get('error'),
                    'batch_id': batch_id
                })
                failed_count += batch_result.get('validator_count', 0)
        
        self.db.commit()
        logger.info(f"批量存款提交完成: {len(submission_results)} 个批次，成功保存 {saved_count} 条存款记录，失败 {failed_count} 条")
        
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
    
    def sync_transaction_status(
        self,
        tx_hash: Optional[str] = None,
        rpc_url: Optional[str] = None,
        validate_immediately: bool = True
    ) -> Dict[str, Any]:
        """
        同步交易状态（增强版）
        
        Args:
            tx_hash: 特定交易哈希（可选，如果提供则只同步该交易）
            rpc_url: RPC URL（可选，如果提供则使用该 URL）
            validate_immediately: 是否立即验证已确认的交易
            
        Returns:
            同步结果统计
        """
        from app.config import settings
        from app.services.network_service import NetworkService
        from app.services.deposit_validation import DepositValidationService
        from app.core.beacon_api import BeaconAPIClient
        from web3 import Web3
        
        # 获取 RPC URL
        if not rpc_url:
            try:
                network_service = NetworkService()
                rpc_endpoints = network_service.get_rpc_endpoints()
                rpc_url = rpc_endpoints.get("rpc_url")
            except Exception as e:
                logger.warning(f"无法从网络服务获取 RPC URL: {e}")
        
        if not rpc_url:
            rpc_url = settings.execution_rpc_url
        
        if not rpc_url:
            raise ValueError("无法获取 RPC URL")
        
        # 连接 Web3
        web3 = Web3(Web3.HTTPProvider(rpc_url))
        if not web3.is_connected():
            raise ValueError(f"无法连接到 RPC: {rpc_url}")
        
        # 初始化验证服务
        beacon_api = BeaconAPIClient()
        validation_service = DepositValidationService(
            db=self.db,
            beacon_api=beacon_api,
            web3=web3
        )
        
        # 查询待同步的交易（包括 SUBMITTED 和旧的 PENDING 状态）
        if tx_hash:
            transactions = self.db.query(DepositTransaction).filter(
                DepositTransaction.tx_hash == tx_hash
            ).filter(
                DepositTransaction.status.in_([
                    DepositStatus.SUBMITTED.value,
                    DepositStatus.PENDING.value,  # 向后兼容
                    DepositStatus.CONFIRMED.value  # 已确认但未验证的交易
                ])
            ).all()
        else:
            transactions = self.db.query(DepositTransaction).filter(
                DepositTransaction.status.in_([
                    DepositStatus.SUBMITTED.value,
                    DepositStatus.PENDING.value,  # 向后兼容
                    DepositStatus.CONFIRMED.value  # 已确认但未验证的交易
                ])
            ).all()
        
        synced_count = 0
        confirmed_count = 0
        validated_count = 0
        invalid_count = 0
        failed_count = 0
        
        for tx in transactions:
            try:
                # 跳过失败的交易记录（以 "failed-" 开头）
                if tx.tx_hash.startswith("failed-"):
                    continue
                
                # 迁移旧的 PENDING 状态为 SUBMITTED
                if tx.status == DepositStatus.PENDING.value:
                    tx.status = DepositStatus.SUBMITTED.value
                
                # 检查交易是否已确认
                try:
                    receipt = web3.eth.get_transaction_receipt(tx.tx_hash)
                    
                    if receipt.status == 1:  # 成功
                        # 更新为 CONFIRMED 状态
                        if tx.status != DepositStatus.CONFIRMED.value:
                            tx.status = DepositStatus.CONFIRMED.value
                            tx.confirmed_at = datetime.utcnow()
                            tx.block_number = receipt.blockNumber
                            confirmed_count += 1
                        
                        # 如果 validate_immediately=True，立即验证
                        if validate_immediately:
                            validation_result = validation_service.validate_deposit_transaction(tx, rpc_url)
                            
                            if validation_result['is_valid']:
                                validated_count += 1
                                if validation_result['status'] == DepositStatus.INVALID.value:
                                    invalid_count += 1
                            else:
                                invalid_count += 1
                    else:  # 失败
                        tx.status = DepositStatus.FAILED.value
                        failed_count += 1
                    
                    synced_count += 1
                except Exception as e:
                    # 交易不存在或查询失败
                    logger.warning(f"无法获取交易 {tx.tx_hash} 的状态: {e}")
                    # 如果交易提交时间超过 1 小时仍未确认，标记为失败
                    if (datetime.utcnow() - tx.submitted_at).total_seconds() > 3600:
                        tx.status = DepositStatus.FAILED.value
                        tx.notes = f"交易超时未确认: {str(e)}"
                        failed_count += 1
                        synced_count += 1
                    else:
                        # 交易可能还在 mempool 中，保持 SUBMITTED 状态
                        pass
                        
            except Exception as e:
                logger.error(f"同步交易 {tx.tx_hash} 时出错: {e}", exc_info=True)
        
        self.db.commit()
        
        logger.info(
            f"交易状态同步完成: 同步 {synced_count} 个，确认 {confirmed_count} 个，"
            f"已验证 {validated_count} 个，无效 {invalid_count} 个，失败 {failed_count} 个"
        )
        
        return {
            "synced_count": synced_count,
            "confirmed_count": confirmed_count,
            "validated_count": validated_count,
            "invalid_count": invalid_count,
            "failed_count": failed_count
        }

