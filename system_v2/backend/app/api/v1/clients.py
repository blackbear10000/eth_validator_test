"""
客户端管理 API
"""
import logging
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional

from app.dependencies import get_db

logger = logging.getLogger(__name__)
from app.services.client_management import ClientManagementService
from app.services.client_process_service import ClientProcessService
from app.core.web3signer_client import Web3SignerClient
from app.models.schemas import (
    ClientInstanceCreate,
    ClientInstanceUpdate,
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


@router.get("/clients/{client_id}", response_model=ClientInstanceResponse)
async def get_client(
    client_id: int,
    client_service: ClientManagementService = Depends(get_client_service)
):
    """获取客户端实例详情"""
    try:
        from app.models.database import ClientInstance
        db = client_service.db
        client = db.query(ClientInstance).filter(ClientInstance.id == client_id).first()
        
        if not client:
            raise HTTPException(status_code=404, detail="客户端不存在")
        
        client_dict = ClientInstanceResponse.model_validate(client).model_dump()
        keys = client_service.get_client_keys(client)
        client_dict['key_count'] = len(keys)
        
        return client_dict
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/clients/{client_id}", response_model=ClientInstanceResponse)
async def update_client(
    client_id: int,
    request: ClientInstanceUpdate,
    client_service: ClientManagementService = Depends(get_client_service)
):
    """更新客户端实例"""
    try:
        client = client_service.update_client_instance(
            client_id=client_id,
            name=request.name,
            beacon_api_url=request.beacon_api_url,
            grpc_endpoint=request.grpc_endpoint,
            web3signer_url=request.web3signer_url,
            notes=request.notes,
            is_active=request.is_active
        )
        
        client_dict = ClientInstanceResponse.model_validate(client).model_dump()
        keys = client_service.get_client_keys(client)
        client_dict['key_count'] = len(keys)
        
        return client_dict
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/clients/{client_id}", response_model=dict)
async def delete_client(
    client_id: int,
    hard_delete: bool = Query(default=False, description="是否硬删除（物理删除）"),
    client_service: ClientManagementService = Depends(get_client_service)
):
    """删除客户端实例"""
    try:
        success = client_service.delete_client_instance(client_id, hard_delete=hard_delete)
        
        return {
            "client_id": client_id,
            "deleted": success,
            "hard_delete": hard_delete
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/clients/{client_id}/keys", response_model=List[dict])
async def get_client_keys(
    client_id: int,
    client_service: ClientManagementService = Depends(get_client_service)
):
    """获取客户端已分配的密钥列表"""
    try:
        from app.models.database import ClientInstance
        db = client_service.db
        client = db.query(ClientInstance).filter(ClientInstance.id == client_id).first()
        
        if not client:
            raise HTTPException(status_code=404, detail="客户端不存在")
        
        keys = client_service.get_client_keys(client)
        
        # 转换为字典格式，包含详细信息
        result = []
        for key in keys:
            result.append({
                "pubkey": key.pubkey,
                "status": key.status,
                "activated_at": key.activated_at.isoformat() if key.activated_at else None,
                "deposited_at": key.deposited_at.isoformat() if key.deposited_at else None,
                "withdrawal_pubkey": key.withdrawal_pubkey,
                "batch_id": key.batch_id,
            })
        
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取客户端密钥列表失败: {e}", exc_info=True)
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
    """重新加载客户端密钥（通过 Web3Signer）"""
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


@router.post("/clients/{client_id}/sync-keys", response_model=dict)
async def sync_keys(
    client_id: int,
    client_service: ClientManagementService = Depends(get_client_service)
):
    """同步所有 ACTIVE 状态的密钥到 Validator Client（通过 Remote Validator API）"""
    try:
        from app.models.database import ClientInstance
        db = client_service.db
        client = db.query(ClientInstance).filter(ClientInstance.id == client_id).first()
        
        if not client:
            raise HTTPException(status_code=404, detail="客户端不存在")
        
        # 同步分配给该客户端的密钥
        result = client_service.sync_client_keys_to_validator_client(client)
        
        return {
            "client_id": client_id,
            "sync_result": result
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/clients/{client_id}/start", response_model=dict)
async def start_client(
    client_id: int,
    db: Session = Depends(get_db)
):
    """启动客户端进程"""
    try:
        from app.models.database import ClientInstance
        client = db.query(ClientInstance).filter(ClientInstance.id == client_id).first()
        
        if not client:
            raise HTTPException(status_code=404, detail="客户端不存在")
        
        # 获取客户端配置（使用现有的密钥生成配置）
        client_service = ClientManagementService(db)
        # 获取客户端关联的密钥
        keys = client_service.get_client_keys(client)
        pubkeys = [key.pubkey for key in keys] if keys else []
        
        # 启动前，确保密钥已同步到 Validator Client（如果使用 Remote Validator API）
        if pubkeys:
            try:
                # 同步分配给该客户端的密钥到 Remote Validator API
                sync_result = client_service.sync_keys_to_validator_client(
                    client,
                    add_pubkeys=pubkeys
                )
                logger.info(f"启动前同步密钥到 Validator Client: 添加 {len(sync_result.get('added', []))} 个密钥")
            except Exception as e:
                logger.warning(f"启动前同步密钥失败: {e}，继续启动流程")
        
        # 确保 Web3Signer 已加载所有 ACTIVE 状态的密钥
        try:
            from app.models.enums import ValidatorKeyStatus
            active_keys = [key for key in keys if key.status == ValidatorKeyStatus.ACTIVE.value]
            if active_keys:
                logger.info(f"检查 Web3Signer 是否已加载 {len(active_keys)} 个 ACTIVE 密钥...")
                # Web3Signer 应该已经通过密钥激活流程加载了所有 ACTIVE 密钥
                # 这里只做检查，不强制重新加载
        except Exception as e:
            logger.warning(f"检查 Web3Signer 密钥加载状态失败: {e}")
        
        # 生成配置文件
        if pubkeys:
            config = client_service.generate_config_files(client, pubkeys)
        else:
            # 如果没有密钥，创建一个空配置
            config = client_service.generate_config_files(client, [])
        
        # 启动进程
        process_service = ClientProcessService()
        result = process_service.start(
            client_id=client_id,
            client_type=client.client_type.value,
            config_file=config.get('config_file')
        )
        
        if not result.get("success"):
            raise HTTPException(status_code=500, detail=result.get("message", "启动失败"))
        
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/clients/{client_id}/stop", response_model=dict)
async def stop_client(
    client_id: int,
    db: Session = Depends(get_db)
):
    """停止客户端进程"""
    try:
        from app.models.database import ClientInstance
        client = db.query(ClientInstance).filter(ClientInstance.id == client_id).first()
        
        if not client:
            raise HTTPException(status_code=404, detail="客户端不存在")
        
        # 停止进程
        process_service = ClientProcessService()
        result = process_service.stop(
            client_id=client_id,
            client_type=client.client_type.value
        )
        
        if not result.get("success"):
            raise HTTPException(status_code=500, detail=result.get("message", "停止失败"))
        
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/clients/{client_id}/status", response_model=dict)
async def get_client_status(
    client_id: int,
    db: Session = Depends(get_db)
):
    """获取客户端进程状态"""
    try:
        from app.models.database import ClientInstance
        client = db.query(ClientInstance).filter(ClientInstance.id == client_id).first()
        
        if not client:
            raise HTTPException(status_code=404, detail="客户端不存在")
        
        # 获取进程状态
        process_service = ClientProcessService()
        status = process_service.get_status(
            client_id=client_id,
            client_type=client.client_type.value
        )
        
        return status
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/clients/{client_id}/logs", response_model=dict)
async def get_client_logs(
    client_id: int,
    lines: int = Query(default=100, ge=1, le=1000),
    db: Session = Depends(get_db)
):
    """获取客户端日志"""
    try:
        from app.models.database import ClientInstance
        client = db.query(ClientInstance).filter(ClientInstance.id == client_id).first()
        
        if not client:
            raise HTTPException(status_code=404, detail="客户端不存在")
        
        # 获取日志
        process_service = ClientProcessService()
        logs = process_service.get_logs(client_id=client_id, lines=lines)
        
        return logs
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

