"""
存款管理 API
"""
import logging
from fastapi import APIRouter, Depends, HTTPException
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
    BatchDepositContractResponse
)
from app.models.database import BatchDepositContract
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
            count=len(request.pubkeys) if request.pubkeys else None,
            pubkeys=request.pubkeys,
            withdrawal_address=request.withdrawal_address,
            amount_eth=request.amount_eth,
            fork_version=request.fork_version
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
    deposit_service: DepositManagementService = Depends(get_deposit_service)
):
    """手动触发状态同步"""
    try:
        # 这里需要调用同步服务
        return {"message": "同步功能需要集成 SyncService"}
    except Exception as e:
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

