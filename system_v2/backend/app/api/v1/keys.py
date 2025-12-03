"""
密钥管理 API
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional

from app.dependencies import get_db
from app.services.key_management import KeyManagementService
from app.core.vault_client import VaultClient
from app.models.schemas import (
    ValidatorKeyResponse,
    ValidatorKeyListResponse,
    ValidatorKeyCreate,
    BatchActivateKeys,
    ValidatorKeyStatusUpdate
)
from app.models.enums import ValidatorKeyStatus

router = APIRouter()


def get_key_service(db: Session = Depends(get_db)) -> KeyManagementService:
    """获取密钥管理服务"""
    vault_client = VaultClient()
    return KeyManagementService(db, vault_client)


@router.post("/keys/batch-generate", response_model=dict)
async def batch_generate_keys(
    request: ValidatorKeyCreate,
    key_service: KeyManagementService = Depends(get_key_service)
):
    """批量生成验证者密钥"""
    try:
        result = key_service.batch_generate_keys(
            count=request.count,
            batch_id=request.batch_id,
            network='mainnet'
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/keys/activate", response_model=List[ValidatorKeyResponse])
async def activate_keys(
    request: BatchActivateKeys,
    key_service: KeyManagementService = Depends(get_key_service)
):
    """激活密钥"""
    try:
        keys = key_service.activate_keys(
            count=request.count,
            batch_id=request.batch_id
        )
        return [ValidatorKeyResponse.model_validate(k) for k in keys]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/keys", response_model=ValidatorKeyListResponse)
async def list_keys(
    status: Optional[ValidatorKeyStatus] = Query(None),
    batch_id: Optional[str] = Query(None),
    search: Optional[str] = Query(None, description="搜索关键词（公钥、提款公钥、批次ID）"),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    key_service: KeyManagementService = Depends(get_key_service)
):
    """列出密钥"""
    try:
        keys, total = key_service.list_keys(
            status=status,
            batch_id=batch_id,
            search=search,
            limit=limit,
            offset=offset
        )
        return ValidatorKeyListResponse(
            total=total,
            items=[ValidatorKeyResponse.model_validate(k) for k in keys]
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/keys/{pubkey}", response_model=ValidatorKeyResponse)
async def get_key(
    pubkey: str,
    key_service: KeyManagementService = Depends(get_key_service)
):
    """获取密钥详情"""
    key = key_service.get_key(pubkey)
    if not key:
        raise HTTPException(status_code=404, detail="密钥不存在")
    return ValidatorKeyResponse.model_validate(key)


@router.put("/keys/{pubkey}/status", response_model=ValidatorKeyResponse)
async def update_key_status(
    pubkey: str,
    request: ValidatorKeyStatusUpdate,
    key_service: KeyManagementService = Depends(get_key_service)
):
    """更新密钥状态"""
    try:
        key = key_service.update_key_status(pubkey, request.status)
        return ValidatorKeyResponse.model_validate(key)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/keys/pool/status", response_model=dict)
async def get_pool_status(
    key_service: KeyManagementService = Depends(get_key_service)
):
    """获取密钥池状态"""
    try:
        return key_service.get_pool_status()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

