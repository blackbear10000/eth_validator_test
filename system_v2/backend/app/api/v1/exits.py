"""
验证者退出 API
"""
import logging
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional

from app.dependencies import get_db
from app.services.exit_service import ExitService
from app.models.database import ExitRecord
from app.services.key_management import KeyManagementService
from app.services.client_management import ClientManagementService
from app.core.exit_generator import ExitGenerator
from app.core.beacon_api import BeaconAPIClient
from app.core.web3signer_client import Web3SignerClient
from app.core.vault_client import VaultClient

logger = logging.getLogger(__name__)
router = APIRouter()


def get_exit_service(db: Session = Depends(get_db)) -> ExitService:
    """获取退出服务"""
    vault_client = VaultClient()
    key_service = KeyManagementService(db, vault_client)
    web3signer_client = Web3SignerClient()
    beacon_api = BeaconAPIClient()
    
    # 从 Beacon API 获取 fork_version 和 network 信息，用于初始化 ExitGenerator
    fork_version = None
    network = 'mainnet'
    try:
        fork_version = beacon_api.get_fork_version()
        if fork_version:
            # 如果成功获取到 fork_version，说明是自定义网络（如 kurtosis）
            network = 'kurtosis'
            logger.info(f"从 Beacon API 获取 fork_version: {fork_version}，使用 kurtosis 网络")
    except Exception as e:
        logger.warning(f"无法从 Beacon API 获取 fork_version: {e}，使用默认 mainnet 网络")
    
    exit_generator = ExitGenerator(
        vault_client=vault_client,
        network=network,
        fork_version=fork_version
    )
    client_service = ClientManagementService(db, web3signer_client)
    
    return ExitService(
        db,
        exit_generator,
        beacon_api,
        web3signer_client,
        key_service,
        client_service
    )


@router.get("/exits/check-eligibility")
async def check_exit_eligibility(
    pubkey: str = Query(..., description="验证者公钥"),
    exit_service: ExitService = Depends(get_exit_service)
):
    """检查验证者是否满足退出条件"""
    try:
        eligibility = exit_service.check_exit_eligibility(pubkey)
        return eligibility
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


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


@router.get("/exits/records")
async def get_exit_records(
    pubkey: Optional[str] = Query(None, description="验证者公钥（可选）"),
    status: Optional[str] = Query(None, description="状态筛选"),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db)
):
    """获取退出记录列表"""
    try:
        query = db.query(ExitRecord)
        
        if pubkey:
            query = query.filter(ExitRecord.pubkey == pubkey.lower())
        if status:
            query = query.filter(ExitRecord.status == status)
        
        total = query.count()
        records = query.order_by(ExitRecord.submitted_at.desc()).offset(offset).limit(limit).all()
        
        return {
            "total": total,
            "items": [
                {
                    "id": record.id,
                    "pubkey": record.pubkey,
                    "validator_index": record.validator_index,
                    "exit_epoch": record.exit_epoch,
                    "withdrawable_epoch": record.withdrawable_epoch,
                    "balance_before_exit_eth": float(record.balance_before_exit_eth) if record.balance_before_exit_eth else None,
                    "status": record.status,
                    "submitted_at": record.submitted_at.isoformat() if record.submitted_at else None,
                    "confirmed_at": record.confirmed_at.isoformat() if record.confirmed_at else None,
                }
                for record in records
            ]
        }
    except Exception as e:
        logger.error(f"获取退出记录失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取退出记录失败: {str(e)}")

