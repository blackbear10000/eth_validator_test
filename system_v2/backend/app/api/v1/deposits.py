"""
存款管理 API
"""
import logging
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List

from app.dependencies import get_db
from app.services.deposit_management import DepositManagementService
from app.services.key_management import KeyManagementService
from app.core.deposit_generator import DepositGenerator
from app.core.batch_deposit import BatchDepositClient
from app.core.vault_client import VaultClient
from app.models.schemas import (
    DepositDataGenerate,
    DepositDataResponse,
    BatchDepositSubmit,
    DepositTransactionResponse,
    BatchDepositDeployRequest,
    BatchDepositContractResponse,
    BatchContractStatistics
)
from app.models.database import BatchDepositContract, DepositTransaction
from web3 import Web3
from typing import Optional

logger = logging.getLogger(__name__)
router = APIRouter()


def get_deposit_service(db: Session = Depends(get_db)) -> DepositManagementService:
    """获取存款管理服务"""
    vault_client = VaultClient()
    key_service = KeyManagementService(db, vault_client)
    deposit_generator = DepositGenerator(vault_client)
    
    # Batch Deposit Client（需要配置 Web3 和合约地址）
    # 注意：Batch Deposit Client 需要在提交时动态创建，因为需要 from_address 和 private_key
    batch_client = None
    
    return DepositManagementService(
        db,
        deposit_generator,
        batch_client,
        key_service
    )


@router.post("/deposits/generate", response_model=List[DepositDataResponse])
async def generate_deposit_data(
    request: DepositDataGenerate,
    deposit_service: DepositManagementService = Depends(get_deposit_service)
):
    """生成 Deposit Data"""
    try:
        deposit_data_list = deposit_service.generate_deposit_data_for_active_keys(
            count=len(request.pubkeys) if request.pubkeys and len(request.pubkeys) > 0 else None,
            pubkeys=request.pubkeys if request.pubkeys and len(request.pubkeys) > 0 else None,
            withdrawal_address=request.withdrawal_address,
            amount_eth=request.amount_eth or 32.0,
            fork_version=request.fork_version if request.fork_version else None
        )
        
        return [DepositDataResponse(**dd) for dd in deposit_data_list]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/deposits/submit", response_model=List[dict])
async def submit_deposits(
    request: BatchDepositSubmit,
    deposit_service: DepositManagementService = Depends(get_deposit_service),
    db: Session = Depends(get_db)
):
    """提交批量存款"""
    try:
        from app.config import settings
        from app.services.network_service import NetworkService
        
        # 优先从 Kurtosis 网络获取 RPC URL
        rpc_url = None
        try:
            network_service = NetworkService()
            rpc_endpoints = network_service.get_rpc_endpoints()
            if rpc_endpoints.get("rpc_url") and not rpc_endpoints.get("error"):
                rpc_url = rpc_endpoints["rpc_url"]
                logger.info(f"从 Kurtosis 网络获取 RPC URL: {rpc_url}")
        except Exception as e:
            logger.warning(f"无法从 Kurtosis 网络获取 RPC URL: {e}")
        
        # 如果无法从网络获取，回退到配置
        if not rpc_url:
            rpc_url = settings.execution_rpc_url
            if rpc_url:
                logger.info(f"使用配置的 RPC URL: {rpc_url}")
        
        # 如果仍然没有 RPC URL，返回错误
        if not rpc_url:
            raise HTTPException(
                status_code=501,
                detail="无法获取 RPC URL。请确保 Kurtosis 网络正在运行，或配置 EXECUTION_RPC_URL 环境变量"
            )
        
        if not request.private_key:
            raise HTTPException(
                status_code=400,
                detail="需要提供 private_key 用于签名交易"
            )
        
        # 初始化 Web3 连接
        web3 = Web3(Web3.HTTPProvider(rpc_url))
        
        # 验证 Web3 连接
        if not web3.is_connected():
            raise HTTPException(
                status_code=503,
                detail=f"无法连接到 Web3 RPC: {rpc_url}"
            )
        
        # 转换 Deposit Data 格式
        deposit_data_list = [dd.model_dump() for dd in request.deposit_data_list]
        
        # 根据存款类型选择客户端
        deposit_type = request.deposit_type or "batch"
        
        if deposit_type == "official":
            # 使用官方 Deposit 合约
            from app.core.official_deposit import OfficialDepositClient
            
            # 获取官方合约地址
            official_contract_address = request.official_deposit_contract_address
            
            # 如果未提供，尝试从网络信息获取
            if not official_contract_address:
                try:
                    network_info = NetworkService().get_info()
                    # 尝试从网络信息中提取合约地址（从 Kurtosis 配置文件读取）
                    official_contract_address = network_info.get("deposit_contract_address")
                    if official_contract_address:
                        logger.info(f"从 Kurtosis 网络信息获取到 deposit_contract_address: {official_contract_address}")
                except Exception as e:
                    logger.warning(f"无法从网络信息获取合约地址: {e}")
            
            # 如果仍然没有，尝试使用标准地址（根据网络名称）
            if not official_contract_address:
                # 对于 Kurtosis devnet，使用配置中的地址
                official_contract_address = settings.official_deposit_contract_address
                if official_contract_address:
                    logger.info(f"使用配置的官方合约地址: {official_contract_address}")
            
            # 如果还是没有，返回错误
            if not official_contract_address:
                raise HTTPException(
                    status_code=400,
                    detail="需要提供 official_deposit_contract_address 或配置官方合约地址"
                )
            
            # 创建官方 Deposit Client
            official_client = OfficialDepositClient(
                web3=web3,
                contract_address=official_contract_address,
                from_address=request.from_address,
                private_key=request.private_key
            )
            
            # 提交存款（官方合约不支持批量，需要循环调用）
            results = official_client.submit_multiple_deposits(deposit_data_list)
            
            # 保存到数据库
            from app.models.database import DepositTransaction, ValidatorKey
            from app.models.enums import DepositStatus, ValidatorKeyStatus
            from datetime import datetime
            
            for result in results:
                if result['status'] == 'submitted':
                    # 规范化 pubkey：移除 0x 前缀（如果有），转为小写
                    pubkey_raw = result['pubkey']
                    pubkey_normalized = pubkey_raw.lower().replace('0x', '')
                    # 数据库中的 pubkey 格式是 0x + 96字符，所以需要添加 0x 前缀
                    pubkey_db_format = f"0x{pubkey_normalized}" if not pubkey_normalized.startswith('0x') else pubkey_normalized
                    
                    # 查找对应的验证者密钥（尝试两种格式）
                    validator_key = db.query(ValidatorKey).filter(
                        (ValidatorKey.pubkey == pubkey_db_format) | 
                        (ValidatorKey.pubkey == pubkey_normalized)
                    ).first()
                    
                    if not validator_key:
                        # 如果还是找不到，尝试直接匹配原始格式
                        validator_key = db.query(ValidatorKey).filter(
                            ValidatorKey.pubkey == pubkey_raw.lower()
                        ).first()
                    
                    if validator_key:
                        # 创建存款交易记录
                        deposit_tx = DepositTransaction(
                            pubkey=validator_key.pubkey,
                            tx_hash=result['tx_hash'],
                            batch_id=None,  # 官方存款没有批次ID
                            status=DepositStatus.SUBMITTED.value,
                            amount_wei=32 * 10**18,
                            amount_eth=32.0,
                            submitted_at=datetime.utcnow()
                        )
                        db.add(deposit_tx)
                        
                        # 更新密钥状态
                        validator_key.status = ValidatorKeyStatus.PENDING.value
                        validator_key.deposit_tx_hash = result['tx_hash']
                elif result['status'] == 'failed':
                    # 记录失败的交易
                    validator_key = db.query(ValidatorKey).filter(
                        ValidatorKey.pubkey == result.get('pubkey', '').lower()
                    ).first()
                    
                    if validator_key:
                        # 创建失败记录（使用临时 tx_hash）
                        deposit_tx = DepositTransaction(
                            pubkey=validator_key.pubkey,
                            tx_hash=f"failed-{datetime.utcnow().timestamp()}",
                            status=DepositStatus.FAILED.value,
                            amount_wei=32 * 10**18,
                            amount_eth=32.0,
                            submitted_at=datetime.utcnow(),
                            notes=f"提交失败: {result.get('error', 'Unknown error')}"
                        )
                        db.add(deposit_tx)
            
            # 提交数据库事务
            db.commit()
            
            # 转换为与 Batch Deposit 相同的格式
            formatted_results = []
            for result in results:
                if result['status'] == 'submitted':
                    formatted_results.append({
                        'batch_number': 1,
                        'validator_count': 1,
                        'tx_hash': result['tx_hash'],
                        'status': 'submitted',
                        'pubkeys': [result['pubkey']]
                    })
                else:
                    formatted_results.append({
                        'batch_number': result['index'] + 1,
                        'validator_count': 1,
                        'status': 'failed',
                        'error': result.get('error'),
                        'pubkeys': [result['pubkey']]
                    })
            
            return formatted_results
            
        else:
            # 使用 Batch Deposit 合约
            # 获取合约地址（如果请求中没有指定，使用配置或从数据库查询）
            contract_address = request.batch_contract_address
            
            if not contract_address:
                # 尝试从数据库查询当前网络的合约
                try:
                    from app.models.database import BatchDepositContract
                    # 尝试从网络名称推断（这里简化处理，实际应该从网络信息获取）
                    network_name = "kurtosis-devnet"  # 默认值
                    contract = db.query(BatchDepositContract).filter(
                        BatchDepositContract.network_name == network_name
                    ).order_by(BatchDepositContract.deployed_at.desc()).first()
                    
                    if contract:
                        contract_address = contract.contract_address
                        logger.info(f"从数据库获取 Batch Deposit 合约地址: {contract_address}")
                except Exception as e:
                    logger.warning(f"从数据库查询合约地址失败: {e}")
            
            if not contract_address:
                contract_address = settings.batch_deposit_contract_address
            
            if not contract_address:
                raise HTTPException(
                    status_code=400,
                    detail="需要提供 batch_contract_address、部署 Batch Deposit 合约，或配置 BATCH_DEPOSIT_CONTRACT_ADDRESS"
                )
            
            # 创建 Batch Deposit Client
            batch_client = BatchDepositClient(
                web3=web3,
                contract_address=contract_address,
                from_address=request.from_address,
                private_key=request.private_key
            )
            
            # 临时设置 batch_deposit_client 到服务
            deposit_service.batch_deposit_client = batch_client
            
            # 提交批量存款
            results = deposit_service.submit_batch_deposits(
                deposit_data_list=deposit_data_list,
                wait_for_confirmation=False  # 不等待确认，异步处理
            )
            
            return results
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"提交批量存款失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/deposits", response_model=List[DepositTransactionResponse])
async def list_deposits(
    deposit_service: DepositManagementService = Depends(get_deposit_service)
):
    """列出存款交易"""
    try:
        transactions, total = deposit_service.get_deposit_transactions()
        return [DepositTransactionResponse.model_validate(t) for t in transactions]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/deposits/sync")
async def sync_deposits(
    tx_hash: Optional[str] = Query(None, description="特定交易哈希（可选，如果提供则只同步该交易）"),
    validate_immediately: bool = Query(True, description="是否立即验证已确认的交易"),
    deposit_service: DepositManagementService = Depends(get_deposit_service)
):
    """手动触发状态同步"""
    try:
        # 获取 RPC URL（用于同步）
        rpc_url = None
        try:
            from app.services.network_service import NetworkService
            network_service = NetworkService()
            rpc_endpoints = network_service.get_rpc_endpoints()
            if rpc_endpoints.get("rpc_url") and not rpc_endpoints.get("error"):
                rpc_url = rpc_endpoints["rpc_url"]
        except Exception as e:
            logger.warning(f"无法从网络服务获取 RPC URL: {e}")
        
        if not rpc_url:
            from app.config import settings
            rpc_url = settings.execution_rpc_url
        
        # 调用同步服务
        result = deposit_service.sync_transaction_status(
            tx_hash=tx_hash,
            rpc_url=rpc_url,
            validate_immediately=validate_immediately
        )
        return result
    except Exception as e:
        logger.error(f"同步存款状态失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/deposits/{tx_hash}/validate")
async def validate_deposit(
    tx_hash: str,
    deposit_service: DepositManagementService = Depends(get_deposit_service),
    db: Session = Depends(get_db)
):
    """手动验证存款交易"""
    try:
        from app.services.deposit_validation import DepositValidationService
        from app.core.beacon_api import BeaconAPIClient
        from app.services.network_service import NetworkService
        from web3 import Web3
        
        # 获取交易
        transaction = db.query(DepositTransaction).filter(
            DepositTransaction.tx_hash == tx_hash
        ).first()
        
        if not transaction:
            raise HTTPException(status_code=404, detail=f"交易不存在: {tx_hash}")
        
        # 获取 RPC URL
        network_service = NetworkService()
        rpc_endpoints = network_service.get_rpc_endpoints()
        rpc_url = rpc_endpoints.get("rpc_url")
        
        if not rpc_url:
            from app.config import settings
            rpc_url = settings.execution_rpc_url
        
        if not rpc_url:
            raise HTTPException(status_code=500, detail="无法获取 RPC URL")
        
        # 连接 Web3
        web3 = Web3(Web3.HTTPProvider(rpc_url))
        if not web3.is_connected():
            raise HTTPException(status_code=500, detail=f"无法连接到 RPC: {rpc_url}")
        
        # 初始化验证服务
        beacon_api = BeaconAPIClient()
        validation_service = DepositValidationService(
            db=db,
            beacon_api=beacon_api,
            web3=web3
        )
        
        # 验证交易
        result = validation_service.validate_deposit_transaction(transaction, rpc_url)
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"验证存款交易失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/deposits/{tx_hash}/status")
async def get_deposit_status(
    tx_hash: str,
    db: Session = Depends(get_db)
):
    """获取存款交易详细状态"""
    try:
        transaction = db.query(DepositTransaction).filter(
            DepositTransaction.tx_hash == tx_hash
        ).first()
        
        if not transaction:
            raise HTTPException(status_code=404, detail=f"交易不存在: {tx_hash}")
        
        # 返回详细信息
        return {
            "tx_hash": transaction.tx_hash,
            "pubkey": transaction.pubkey,
            "status": transaction.status,
            "amount_eth": float(transaction.amount_eth),
            "amount_wei": int(transaction.amount_wei),
            "submitted_at": transaction.submitted_at.isoformat() if transaction.submitted_at else None,
            "confirmed_at": transaction.confirmed_at.isoformat() if transaction.confirmed_at else None,
            "validated_at": transaction.validated_at.isoformat() if transaction.validated_at else None,
            "block_number": transaction.block_number,
            "validator_index": transaction.validator_index,
            "activation_epoch": transaction.activation_epoch,
            "exit_epoch": transaction.exit_epoch,
            "effective_balance_gwei": int(transaction.effective_balance_gwei) if transaction.effective_balance_gwei else None,
            "validation_error": transaction.validation_error,
            "status_history": transaction.status_history,
            "notes": transaction.notes
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取存款交易状态失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/deposits/batch-contract/deploy", response_model=BatchDepositContractResponse)
async def deploy_batch_contract(
    request: BatchDepositDeployRequest,
    db: Session = Depends(get_db)
):
    """部署 Batch Deposit 合约"""
    try:
        from app.core.batch_deposit_deployer import BatchDepositDeployer
        from app.services.network_service import NetworkService
        from app.config import settings
        
        # 优先从 Kurtosis 网络获取 RPC URL（如果请求中的 RPC URL 为空）
        rpc_url = request.rpc_url
        if not rpc_url:
            try:
                network_service = NetworkService()
                rpc_endpoints = network_service.get_rpc_endpoints()
                if rpc_endpoints.get("rpc_url") and not rpc_endpoints.get("error"):
                    rpc_url = rpc_endpoints["rpc_url"]
                    logger.info(f"从 Kurtosis 网络获取 RPC URL: {rpc_url}")
                else:
                    error_msg = rpc_endpoints.get("error", "未知错误")
                    logger.warning(f"无法从 Kurtosis 网络获取 RPC URL: {error_msg}")
            except Exception as e:
                logger.warning(f"无法从 Kurtosis 网络获取 RPC URL: {e}")
        
        if not rpc_url:
            rpc_url = settings.execution_rpc_url
        
        if not rpc_url:
            raise HTTPException(
                status_code=400,
                detail="无法获取 RPC URL。请确保：1) Kurtosis 网络正在运行，或 2) 提供 rpc_url 参数，或 3) 配置 EXECUTION_RPC_URL 环境变量"
            )
        
        # 初始化 Web3 连接
        web3 = Web3(Web3.HTTPProvider(rpc_url))
        
        if not web3.is_connected():
            raise HTTPException(
                status_code=503,
                detail=f"无法连接到 Web3 RPC: {rpc_url}"
            )
        
        # 获取官方 Deposit 合约地址
        deposit_contract_address = request.deposit_contract_address
        if not deposit_contract_address:
            try:
                network_service = NetworkService()
                network_info = network_service.get_info()
                deposit_contract_address = network_info.get("deposit_contract_address")
                if deposit_contract_address:
                    logger.info(f"从 Kurtosis 网络配置获取 Deposit 合约地址: {deposit_contract_address}")
            except Exception as e:
                logger.warning(f"无法从 Kurtosis 网络配置获取 Deposit 合约地址: {e}")
        
        if not deposit_contract_address:
            raise HTTPException(
                status_code=400,
                detail="无法获取官方 Deposit 合约地址。请提供 deposit_contract_address 参数，或确保 Kurtosis 网络配置中包含该地址"
            )
        
        # 验证 deposit_contract_address 格式
        if not web3.is_address(deposit_contract_address):
            raise HTTPException(
                status_code=400,
                detail=f"无效的 Deposit 合约地址格式: {deposit_contract_address}"
            )
        
        # 创建部署器
        deployer = BatchDepositDeployer(
            web3=web3,
            deployer_private_key=request.deployer_private_key
        )
        
        # 部署合约
        # initial_fee 默认 0，必须是 gwei 的倍数
        initial_fee = request.initial_fee or 0
        deployment_result = deployer.deploy(
            rpc_url=rpc_url,
            network_name=request.network_name,
            deposit_contract_address=deposit_contract_address,
            initial_fee=initial_fee,
            gas_price=request.gas_price,
            gas_limit=request.gas_limit
        )
        
        # 保存到数据库
        batch_contract = BatchDepositContract(
            contract_address=deployment_result['contract_address'],
            network_name=request.network_name,
            rpc_url=rpc_url,
            deployer_address=deployment_result['deployer_address'],
            deployment_tx_hash=deployment_result['deployment_tx_hash'],
            block_number=deployment_result.get('block_number'),
            gas_used=deployment_result.get('gas_used')
        )
        
        db.add(batch_contract)
        db.commit()
        db.refresh(batch_contract)
        
        logger.info(f"Batch Deposit 合约已部署并保存: {batch_contract.contract_address}")
        
        return BatchDepositContractResponse.model_validate(batch_contract)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"部署 Batch Deposit 合约失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/deposits/batch-contract/list", response_model=List[BatchDepositContractResponse])
async def list_batch_contracts(
    network_name: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """列出已部署的 Batch Deposit 合约"""
    try:
        query = db.query(BatchDepositContract)
        
        if network_name:
            query = query.filter(BatchDepositContract.network_name == network_name)
        
        contracts = query.order_by(BatchDepositContract.deployed_at.desc()).all()
        
        return [BatchDepositContractResponse.model_validate(c) for c in contracts]
        
    except Exception as e:
        logger.error(f"列出 Batch Deposit 合约失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/deposits/batch-contract/{contract_id}", response_model=BatchDepositContractResponse)
async def get_batch_contract(
    contract_id: int,
    db: Session = Depends(get_db)
):
    """获取单个 Batch Deposit 合约详情"""
    try:
        contract = db.query(BatchDepositContract).filter(
            BatchDepositContract.id == contract_id
        ).first()
        
        if not contract:
            raise HTTPException(status_code=404, detail=f"合约不存在: {contract_id}")
        
        return BatchDepositContractResponse.model_validate(contract)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取 Batch Deposit 合约详情失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/deposits/batch-contract/{contract_id}/statistics", response_model=BatchContractStatistics)
async def get_batch_contract_statistics(
    contract_id: int,
    db: Session = Depends(get_db)
):
    """获取 Batch Deposit 合约统计数据"""
    try:
        from sqlalchemy import func, distinct
        from decimal import Decimal
        
        # 获取合约信息
        contract = db.query(BatchDepositContract).filter(
            BatchDepositContract.id == contract_id
        ).first()
        
        if not contract:
            raise HTTPException(status_code=404, detail=f"合约不存在: {contract_id}")
        
        contract_address = contract.contract_address.lower()
        
        # 统计存款交易：通过查询交易收据获取 to 地址匹配合约地址
        # 由于 DepositTransaction 表中没有直接存储合约地址，我们需要通过 Web3 查询
        # 但为了性能，我们先统计所有有 batch_id 的交易（这些通常是批量存款）
        # 然后通过 Web3 验证哪些交易确实是发送到该合约的
        
        # 方法1：通过 Web3 查询所有相关交易（较慢但准确）
        # 方法2：先统计所有 batch_id 不为空的交易，然后通过 Web3 过滤（折中方案）
        # 方法3：假设所有 batch_id 不为空的交易都是通过 Batch Deposit 合约提交的（快速但不完全准确）
        
        # 为了性能，我们使用方法3，但添加一个可选的 Web3 验证
        # 首先，统计所有有 batch_id 的交易（这些通常是批量存款）
        deposit_query = db.query(DepositTransaction).filter(
            DepositTransaction.batch_id.isnot(None)
        )
        
        # 通过 Web3 验证哪些交易确实是发送到该合约的
        try:
            from app.services.network_service import NetworkService
            from app.config import settings
            from web3 import Web3
            
            # 获取 RPC URL
            rpc_url = contract.rpc_url
            if not rpc_url:
                try:
                    network_service = NetworkService()
                    rpc_endpoints = network_service.get_rpc_endpoints()
                    if rpc_endpoints.get("rpc_url") and not rpc_endpoints.get("error"):
                        rpc_url = rpc_endpoints["rpc_url"]
                except Exception:
                    pass
            
            if not rpc_url:
                rpc_url = settings.execution_rpc_url
            
            if rpc_url:
                web3 = Web3(Web3.HTTPProvider(rpc_url))
                if web3.is_connected():
                    # 获取所有唯一的 tx_hash
                    all_tx_hashes = db.query(DepositTransaction.tx_hash).filter(
                        DepositTransaction.batch_id.isnot(None)
                    ).distinct().all()
                    
                    # 验证哪些交易是发送到该合约的
                    valid_tx_hashes = []
                    for (tx_hash,) in all_tx_hashes:
                        try:
                            tx = web3.eth.get_transaction(tx_hash)
                            if tx and tx.to and tx.to.lower() == contract_address:
                                valid_tx_hashes.append(tx_hash)
                        except Exception as e:
                            logger.warning(f"无法获取交易 {tx_hash} 的信息: {e}")
                    
                    # 过滤出有效的交易
                    if valid_tx_hashes:
                        deposit_query = deposit_query.filter(
                            DepositTransaction.tx_hash.in_(valid_tx_hashes)
                        )
                    else:
                        # 如果没有找到有效交易，返回空统计
                        deposit_query = deposit_query.filter(False)
        except Exception as e:
            logger.warning(f"无法通过 Web3 验证交易，使用简化统计: {e}")
            # 如果 Web3 查询失败，我们仍然可以返回基于 batch_id 的统计
            # 但这可能不够准确
        
        # 统计存款数量
        deposit_count = deposit_query.count()
        
        # 统计总金额和验证者数量
        if deposit_count > 0:
            total_amount_result = deposit_query.with_entities(
                func.sum(DepositTransaction.amount_eth)
            ).scalar()
            total_amount_eth = float(total_amount_result) if total_amount_result else 0.0
            
            validator_count_result = deposit_query.with_entities(
                func.count(distinct(DepositTransaction.pubkey))
            ).scalar()
            validator_count = validator_count_result or 0
        else:
            total_amount_eth = 0.0
            validator_count = 0
        
        # 获取合约链上信息（费用、余额等）
        contract_fee_wei = None
        contract_fee_gwei = None
        contract_balance_wei = None
        contract_balance_eth = None
        is_paused = None
        owner_address = None
        
        try:
            from app.core.batch_deposit import BatchDepositClient
            
            # 获取 RPC URL
            rpc_url = contract.rpc_url
            if not rpc_url:
                try:
                    network_service = NetworkService()
                    rpc_endpoints = network_service.get_rpc_endpoints()
                    if rpc_endpoints.get("rpc_url") and not rpc_endpoints.get("error"):
                        rpc_url = rpc_endpoints["rpc_url"]
                except Exception:
                    pass
            
            if not rpc_url:
                rpc_url = settings.execution_rpc_url
            
            if rpc_url:
                web3 = Web3(Web3.HTTPProvider(rpc_url))
                if web3.is_connected():
                    # 获取合约余额
                    try:
                        balance = web3.eth.get_balance(Web3.to_checksum_address(contract_address))
                        contract_balance_wei = balance
                        contract_balance_eth = float(Decimal(balance) / Decimal(10**18))
                    except Exception as e:
                        logger.warning(f"无法获取合约余额: {e}")
                    
                    # 获取合约费用和状态
                    try:
                        batch_client = BatchDepositClient(
                            web3=web3,
                            contract_address=contract_address,
                            from_address=contract.deployer_address
                        )
                        fee = batch_client.get_contract_fee()
                        contract_fee_wei = fee
                        contract_fee_gwei = float(Decimal(fee) / Decimal(10**9))
                        
                        # 尝试获取合约所有者（如果合约支持）
                        try:
                            owner = batch_client.contract.functions.owner().call()
                            owner_address = owner
                        except Exception:
                            pass
                        
                        # 尝试获取暂停状态（如果合约支持）
                        try:
                            paused = batch_client.contract.functions.paused().call()
                            is_paused = paused
                        except Exception:
                            pass
                    except Exception as e:
                        logger.warning(f"无法获取合约费用和状态: {e}")
        except Exception as e:
            logger.warning(f"无法获取合约链上信息: {e}")
        
        return BatchContractStatistics(
            contract_id=contract.id,
            contract_address=contract.contract_address,
            deposit_count=deposit_count,
            total_amount_eth=total_amount_eth,
            validator_count=validator_count,
            contract_fee_wei=contract_fee_wei,
            contract_fee_gwei=contract_fee_gwei,
            contract_balance_wei=contract_balance_wei,
            contract_balance_eth=contract_balance_eth,
            is_paused=is_paused,
            owner_address=owner_address
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取 Batch Deposit 合约统计数据失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

