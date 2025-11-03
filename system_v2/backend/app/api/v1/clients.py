"""
客户端管理 API
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional

from app.dependencies import get_db
from app.services.client_management import ClientManagementService
from app.core.web3signer_client import Web3SignerClient
from app.models.schemas import (
    ClientInstanceCreate,
    ClientInstanceResponse,
    ClientKeyAssignment
)
from app.models.enums import ValidatorClientType

router = APIRouter()


def get_client_service(db: Session = Depends(get_db)) -> ClientManagementService:
    """获取客户端管理服务"""
    web3signer_client = Web3SignerClient()
    return ClientManagementService(db, web3signer_client)


@router.post("/clients", response_model=ClientInstanceResponse)
async def create_client(
    request: ClientInstanceCreate,
    client_service: ClientManagementService = Depends(get_client_service)
):
    """创建客户端实例"""
    try:
        client = client_service.create_client_instance(
            name=request.name,
            client_type=request.client_type,
            beacon_api_url=request.beacon_api_url,
            grpc_endpoint=request.grpc_endpoint,
            web3signer_url=request.web3signer_url,
            notes=request.notes
        )
        return ClientInstanceResponse.model_validate(client)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/clients", response_model=List[ClientInstanceResponse])
async def list_clients(
    client_type: Optional[str] = None,
    client_service: ClientManagementService = Depends(get_client_service)
):
    """列出客户端实例"""
    try:
        clients = client_service.list_clients(client_type=client_type)
        
        # 添加密钥数量
        result = []
        for client in clients:
            client_dict = ClientInstanceResponse.model_validate(client).model_dump()
            keys = client_service.get_client_keys(client)
            client_dict['key_count'] = len(keys)
            result.append(client_dict)
        
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/clients/{client_id}/keys", response_model=dict)
async def assign_keys(
    client_id: int,
    request: ClientKeyAssignment,
    client_service: ClientManagementService = Depends(get_client_service)
):
    """分配密钥到客户端"""
    try:
        from app.models.database import ClientInstance
        db = client_service.db
        client = db.query(ClientInstance).filter(ClientInstance.id == client_id).first()
        
        if not client:
            raise HTTPException(status_code=404, detail="客户端不存在")
        
        assigned = client_service.assign_keys_to_client(client, request.pubkeys)
        return {
            "client_id": client_id,
            "assigned_count": len(assigned),
            "pubkeys": request.pubkeys
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/clients/{client_id}/reload-keys", response_model=dict)
async def reload_keys(
    client_id: int,
    client_service: ClientManagementService = Depends(get_client_service)
):
    """重新加载客户端密钥"""
    try:
        from app.models.database import ClientInstance
        db = client_service.db
        client = db.query(ClientInstance).filter(ClientInstance.id == client_id).first()
        
        if not client:
            raise HTTPException(status_code=404, detail="客户端不存在")
        
        # 触发 Web3Signer 重新加载
        result = client_service.web3signer_client.zero_downtime_reload()
        
        return {
            "client_id": client_id,
            "reload_result": result
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

