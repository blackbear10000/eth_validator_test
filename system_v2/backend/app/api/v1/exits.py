"""
验证者退出 API
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional

from app.dependencies import get_db
from app.services.exit_service import ExitService
from app.services.key_management import KeyManagementService
from app.services.client_management import ClientManagementService
from app.core.exit_generator import ExitGenerator
from app.core.beacon_api import BeaconAPIClient
from app.core.web3signer_client import Web3SignerClient
from app.core.vault_client import VaultClient

router = APIRouter()


def get_exit_service(db: Session = Depends(get_db)) -> ExitService:
    """获取退出服务"""
    vault_client = VaultClient()
    key_service = KeyManagementService(db, vault_client)
    web3signer_client = Web3SignerClient()
    beacon_api = BeaconAPIClient()
    exit_generator = ExitGenerator(vault_client)
    client_service = ClientManagementService(db, web3signer_client)
    
    return ExitService(
        db,
        exit_generator,
        beacon_api,
        web3signer_client,
        key_service,
        client_service
    )


@router.post("/exits/generate")
async def generate_exit_signature(
    pubkey: str = Query(..., description="验证者公钥"),
    epoch: Optional[int] = Query(None, description="退出 epoch"),
    exit_service: ExitService = Depends(get_exit_service)
):
    """生成验证者退出签名"""
    try:
        exit_data = exit_service.generate_exit_signature(pubkey, epoch=epoch)
        return exit_data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/exits/submit")
async def submit_exit(
    pubkey: str = Query(..., description="验证者公钥"),
    epoch: Optional[int] = Query(None, description="退出 epoch"),
    exit_service: ExitService = Depends(get_exit_service)
):
    """提交验证者退出"""
    try:
        result = exit_service.submit_exit(pubkey, epoch=epoch)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/exits/batch")
async def batch_exit(
    pubkeys: List[str],
    epoch: Optional[int] = None,
    exit_service: ExitService = Depends(get_exit_service)
):
    """批量退出验证者"""
    try:
        results = exit_service.batch_exit_validators(pubkeys, epoch=epoch)
        return {
            'total': len(pubkeys),
            'results': results
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/exits/{pubkey}/complete")
async def complete_exit(
    pubkey: str,
    exit_service: ExitService = Depends(get_exit_service)
):
    """完成退出流程（确认退出后调用）"""
    try:
        result = exit_service.complete_exit_process(pubkey)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/exits/{pubkey}/remove-key")
async def remove_exited_key(
    pubkey: str,
    exit_service: ExitService = Depends(get_exit_service)
):
    """从系统移除已退出的密钥"""
    try:
        result = exit_service.remove_key_from_system(pubkey)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

