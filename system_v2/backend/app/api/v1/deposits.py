"""
存款管理 API
"""
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
    DepositTransactionResponse
)
from web3 import Web3

router = APIRouter()


def get_deposit_service(db: Session = Depends(get_db)) -> DepositManagementService:
    """获取存款管理服务"""
    vault_client = VaultClient()
    key_service = KeyManagementService(db, vault_client)
    deposit_generator = DepositGenerator(vault_client)
    
    # Batch Deposit Client（需要配置）
    batch_client = None
    if hasattr(db, 'get_batch_deposit_config'):
        # 从配置获取
        pass
    
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
    deposit_service: DepositManagementService = Depends(get_deposit_service)
):
    """提交批量存款"""
    try:
        # 这里需要配置 Batch Deposit Client
        # 暂时返回错误
        raise HTTPException(
            status_code=501,
            detail="Batch Deposit Client 需要配置 Web3 连接和合约地址"
        )
    except Exception as e:
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

