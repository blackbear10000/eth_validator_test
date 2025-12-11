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
    is_active: Optional[bool] = Query(None, description="是否只返回激活的客户端（True：激活，False：已删除，None：全部）"),
    client_service: ClientManagementService = Depends(get_client_service)
):
    """列出客户端实例"""
    try:
        from app.models.database import ValidatorClientKey
        from sqlalchemy import func
        
        clients = client_service.list_clients(client_type=client_type, is_active=is_active)
        
        if not clients:
            return []
        
        # 批量查询所有客户端的密钥数量（优化 N+1 查询问题）
        client_ids = [client.id for client in clients]
        key_counts = (
            client_service.db.query(
                ValidatorClientKey.client_id,
                func.count(ValidatorClientKey.pubkey).label('key_count')
            )
            .filter(
                ValidatorClientKey.client_id.in_(client_ids),
                ValidatorClientKey.status == "active"
            )
            .group_by(ValidatorClientKey.client_id)
            .all()
        )
        
        # 创建 client_id -> key_count 的映射
        key_count_map = {client_id: count for client_id, count in key_counts}
        
        # 添加密钥数量
        result = []
        for client in clients:
            client_dict = ClientInstanceResponse.model_validate(client).model_dump()
            client_dict['key_count'] = key_count_map.get(client.id, 0)
            result.append(client_dict)
        
        return result
    except Exception as e:
        logger.error(f"列出客户端失败: {e}", exc_info=True)
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
        
        if not client.is_active:
            raise HTTPException(status_code=400, detail="无法为已删除的客户端分配密钥，请先恢复客户端")
        
        assigned = client_service.assign_keys_to_client(client, request.pubkeys)
        return {
            "client_id": client_id,
            "assigned_count": len(assigned),
            "pubkeys": request.pubkeys
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/clients/{client_id}/keys", response_model=dict)
async def remove_keys(
    client_id: int,
    request: ClientKeyAssignment,
    client_service: ClientManagementService = Depends(get_client_service)
):
    """从客户端移除密钥"""
    try:
        from app.models.database import ClientInstance
        db = client_service.db
        client = db.query(ClientInstance).filter(ClientInstance.id == client_id).first()
        
        if not client:
            raise HTTPException(status_code=404, detail="客户端不存在")
        
        removed_count = client_service.remove_keys_from_client(client, request.pubkeys)
        return {
            "client_id": client_id,
            "removed_count": removed_count,
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


@router.get("/clients/{client_id}/keys/actual", response_model=dict)
async def get_actual_keys(
    client_id: int,
    client_service: ClientManagementService = Depends(get_client_service)
):
    """获取 validator client 实际加载的密钥列表（通过 Remote Validator API）"""
    try:
        from app.models.database import ClientInstance
        db = client_service.db
        client = db.query(ClientInstance).filter(ClientInstance.id == client_id).first()
        
        if not client:
            raise HTTPException(status_code=404, detail="客户端不存在")
        
        # 获取 Remote Validator API URL
        remote_api_url = client_service._get_remote_validator_api_url(client)
        if not remote_api_url:
            raise HTTPException(
                status_code=400,
                detail=f"无法确定 Remote Validator API URL（客户端类型: {client.client_type}）"
            )
        
        try:
            from app.core.remote_validator_client import RemoteValidatorClient
            # 获取 auth token（从容器中读取）
            auth_token = client_service._get_auth_token_from_container(client)
            remote_client = RemoteValidatorClient(remote_api_url, auth_token=auth_token)
            
            # 获取实际加载的密钥列表
            pubkeys = remote_client.get_public_keys()
            keystores = remote_client.get_keystores()
            
            return {
                "client_id": client_id,
                "pubkeys": pubkeys,
                "keystores": keystores,
                "count": len(pubkeys),
                "remote_api_url": remote_api_url
            }
        except Exception as e:
            logger.error(f"获取 validator client 实际密钥列表失败: {e}", exc_info=True)
            raise HTTPException(
                status_code=500,
                detail=f"无法连接到 Remote Validator API: {str(e)}"
            )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取实际密钥列表失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/clients/{client_id}/keys/compare", response_model=dict)
async def compare_keys(
    client_id: int,
    client_service: ClientManagementService = Depends(get_client_service)
):
    """对比数据库中的密钥列表和 validator client 实际加载的密钥列表"""
    try:
        from app.models.database import ClientInstance
        db = client_service.db
        client = db.query(ClientInstance).filter(ClientInstance.id == client_id).first()
        
        if not client:
            raise HTTPException(status_code=404, detail="客户端不存在")
        
        # 获取数据库中的密钥列表
        db_keys = client_service.get_client_keys(client)
        db_pubkeys = set([key.pubkey.lower() for key in db_keys])
        
        # 检查容器是否运行
        is_running = client_service._is_client_running(client)
        remote_api_url = client_service._get_remote_validator_api_url(client)
        actual_pubkeys = set()
        keystores_info = []
        api_error = None
        
        # 只有在容器运行时才尝试获取 validator client 实际密钥列表
        if is_running and remote_api_url:
            try:
                from app.core.remote_validator_client import RemoteValidatorClient
                # 获取 auth token（从容器中读取）
                auth_token = client_service._get_auth_token_from_container(client)
                if not auth_token:
                    logger.warning(f"无法获取 auth token，跳过 Remote Validator API 查询 (客户端: {client.name})")
                    api_error = "无法获取 auth token"
                else:
                    remote_client = RemoteValidatorClient(remote_api_url, auth_token=auth_token)
                    actual_pubkeys_list = remote_client.get_public_keys()
                    actual_pubkeys = set([pubkey.lower() for pubkey in actual_pubkeys_list])
                    keystores_info = remote_client.get_keystores()
                    logger.info(f"成功获取 validator client 实际密钥列表: {len(actual_pubkeys)} 个密钥 (URL: {remote_api_url})")
                    logger.debug(f"Validator client 实际密钥列表: {list(actual_pubkeys)}")
                    logger.debug(f"数据库密钥列表: {list(db_pubkeys)}")
            except Exception as e:
                api_error = str(e)
                logger.warning(f"无法获取 validator client 实际密钥列表: {e}", exc_info=True)
                # 继续执行，actual_pubkeys 保持为空集合
                # 注意：如果 API 调用失败，actual_pubkeys 为空，不会误判为"在 validator 中"
        elif not is_running:
            logger.info(f"客户端容器未运行，跳过 Remote Validator API 查询 (客户端: {client.name})")
        elif not remote_api_url:
            logger.warning(f"无法确定 Remote Validator API URL (客户端类型: {client.client_type})")
        
        # 计算差异
        only_in_db = db_pubkeys - actual_pubkeys
        only_in_validator = actual_pubkeys - db_pubkeys
        in_both = db_pubkeys & actual_pubkeys
        
        # 构建详细的对比结果
        comparison = []
        all_pubkeys = db_pubkeys | actual_pubkeys
        
        for pubkey in all_pubkeys:
            in_db = pubkey in db_pubkeys
            in_validator = pubkey in actual_pubkeys
            
            # 获取数据库中的密钥详细信息
            db_key_info = None
            if in_db:
                db_key = next((k for k in db_keys if k.pubkey.lower() == pubkey), None)
                if db_key:
                    db_key_info = {
                        "status": db_key.status,
                        "activated_at": db_key.activated_at.isoformat() if db_key.activated_at else None,
                        "deposited_at": db_key.deposited_at.isoformat() if db_key.deposited_at else None,
                    }
            
            comparison.append({
                "pubkey": pubkey,
                "in_database": in_db,
                "in_validator_client": in_validator,
                "status": "both" if (in_db and in_validator) else ("database_only" if in_db else "validator_only"),
                "db_key_info": db_key_info
            })
        
        result = {
            "client_id": client_id,
            "database_count": len(db_pubkeys),
            "validator_count": len(actual_pubkeys),
            "only_in_database": list(only_in_db),
            "only_in_validator": list(only_in_validator),
            "in_both": list(in_both),
            "comparison": comparison,
            "remote_api_url": remote_api_url,
            "container_running": is_running
        }
        
        # 如果容器未运行或 API 调用失败，添加警告信息
        if not is_running:
            result["warning"] = "容器未运行，无法获取 validator client 实际密钥列表"
        elif api_error:
            result["warning"] = f"无法连接到 Remote Validator API: {api_error}"
            result["api_error"] = api_error
        
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"对比密钥列表失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/clients/{client_id}/keys/sync-orphaned", response_model=dict)
async def sync_orphaned_keys(
    client_id: int,
    request: Optional[ClientKeyAssignment] = None,
    client_service: ClientManagementService = Depends(get_client_service)
):
    """
    将 Validator Client 中的"孤儿"密钥同步到数据库
    
    这些密钥在 Validator Client 中存在，但在数据库中没有记录。
    通常是由于之前的代码 bug 导致的数据不一致。
    """
    try:
        from app.models.database import ClientInstance
        db = client_service.db
        client = db.query(ClientInstance).filter(ClientInstance.id == client_id).first()
        
        if not client:
            raise HTTPException(status_code=404, detail="客户端不存在")
        
        # 获取要同步的公钥列表（如果提供）
        pubkeys = request.pubkeys if request and request.pubkeys else None
        
        # 同步孤儿密钥到数据库
        result = client_service.sync_orphaned_keys_from_validator_client(client, pubkeys=pubkeys)
        
        return {
            "client_id": client_id,
            "synced_count": len(result['synced']),
            "skipped_count": len(result['skipped']),
            "error_count": len(result['errors']),
            "synced": result['synced'],
            "skipped": result['skipped'],
            "errors": result['errors']
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"同步孤儿密钥失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/clients/{client_id}/keys/remove-orphaned", response_model=dict)
async def remove_orphaned_keys(
    client_id: int,
    request: Optional[ClientKeyAssignment] = None,
    client_service: ClientManagementService = Depends(get_client_service)
):
    """
    从 Validator Client 删除"孤儿"密钥
    
    这些密钥在 Validator Client 中存在，但在数据库中没有记录。
    通常是由于之前的代码 bug 导致的数据不一致。
    """
    try:
        from app.models.database import ClientInstance
        db = client_service.db
        client = db.query(ClientInstance).filter(ClientInstance.id == client_id).first()
        
        if not client:
            raise HTTPException(status_code=404, detail="客户端不存在")
        
        # 获取要删除的公钥列表（如果提供）
        pubkeys = request.pubkeys if request and request.pubkeys else None
        
        # 从 Validator Client 删除孤儿密钥
        result = client_service.remove_orphaned_keys_from_validator_client(client, pubkeys=pubkeys)
        
        return {
            "client_id": client_id,
            "removed_count": len(result['removed']),
            "not_found_count": len(result['not_found']),
            "error_count": len(result['errors']),
            "removed": result['removed'],
            "not_found": result['not_found'],
            "errors": result['errors']
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除孤儿密钥失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/clients/{client_id}/keys/available")
async def get_available_keys(
    client_id: int,
    status: Optional[str] = Query(None, description="密钥状态筛选，如: deposited, pending"),
    limit: int = Query(1000, ge=1, le=10000),
    db: Session = Depends(get_db),
    client_service: ClientManagementService = Depends(get_client_service)
):
    """
    获取可用于分配给该客户端的密钥列表
    只返回已提交的密钥（PENDING, DEPOSITED, ACTIVE_ON_CHAIN）
    排除已被其他激活的客户端选中并使用的密钥（不管客户端是否在运行）
    """
    try:
        from app.models.database import ClientInstance, ValidatorKey, ValidatorClientKey
        from app.models.enums import ValidatorKeyStatus
        
        client = db.query(ClientInstance).filter(ClientInstance.id == client_id).first()
        if not client:
            raise HTTPException(status_code=404, detail="客户端不存在")
        
        # 只获取已提交的密钥：PENDING, DEPOSITED, ACTIVE_ON_CHAIN
        allowed_statuses = [
            ValidatorKeyStatus.PENDING.value,
            ValidatorKeyStatus.DEPOSITED.value,
            ValidatorKeyStatus.ACTIVE_ON_CHAIN.value,
        ]
        
        query = db.query(ValidatorKey).filter(
            ValidatorKey.status.in_(allowed_statuses)
        )
        
        # 如果提供了 status 参数，则在此基础上进一步筛选
        if status:
            query = query.filter(ValidatorKey.status == status)
        
        all_keys = query.limit(limit).all()
        
        # 获取当前客户端已分配的密钥
        current_client_keys = db.query(ValidatorClientKey).filter(
            ValidatorClientKey.client_id == client_id
        ).all()
        current_pubkeys = set([k.pubkey.lower() for k in current_client_keys])
        
        # 获取已被其他激活的客户端使用的密钥（排除已被其他客户端选中并运行的密钥）
        # 只要密钥被其他激活的客户端分配且状态为 active，就不能再被使用
        other_active_client_keys = db.query(ValidatorClientKey).join(ClientInstance).filter(
            ValidatorClientKey.status == "active",
            ValidatorClientKey.client_id != client_id,
            ClientInstance.is_active == True  # 只排除激活的客户端，不管是否在运行
        ).all()
        other_active_pubkeys = set([k.pubkey.lower() for k in other_active_client_keys])
        
        # 过滤可用密钥
        available_keys = []
        for key in all_keys:
            pubkey_lower = key.pubkey.lower()
            # 排除当前客户端已分配的
            if pubkey_lower in current_pubkeys:
                continue
            # 排除已被其他激活的客户端使用的密钥（不管客户端是否在运行）
            if pubkey_lower in other_active_pubkeys:
                continue
            available_keys.append({
                "pubkey": key.pubkey,
                "status": key.status,
                "withdrawal_address": key.withdrawal_address,
                "batch_id": key.batch_id,
            })
        
        return {
            "total": len(available_keys),
            "items": available_keys
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取可用密钥列表失败: {e}", exc_info=True)
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
        # 获取客户端关联的所有密钥（用于首次启动时的配置文件）
        keys = client_service.get_client_keys(client)
        pubkeys = [key.pubkey for key in keys] if keys else []
        
        # 首次启动时生成包含所有密钥的配置文件
        # 注意：首次启动使用配置文件，运行状态下的密钥变更才使用 Remote Validator API
        logger.info(f"首次启动客户端 {client.name}，生成包含 {len(pubkeys)} 个密钥的配置文件")
        if pubkeys:
            config = client_service.generate_config_files(client, pubkeys)
        else:
            # 如果没有密钥，创建一个空配置
            config = client_service.generate_config_files(client, [])
        
        # 获取配置文件路径
        config_file = config.get('config_file')
        config_dir = client.config_path  # 配置文件目录（用于 Docker 挂载）
        
        # 验证配置文件是否存在
        if config_file:
            import os
            if not os.path.exists(config_file):
                error_msg = f"配置文件不存在: {config_file}"
                logger.error(error_msg)
                raise HTTPException(
                    status_code=400,
                    detail={
                        "error": error_msg,
                        "config_file": config_file,
                        "config_dir": config_dir
                    }
                )
            logger.info(f"验证配置文件存在: {config_file}")
        
        # 如果 config_file 是相对路径，提取文件名
        if config_file and config_dir:
            import os
            config_file_name = os.path.basename(config_file)
        else:
            config_file_name = None
        
        # 启动容器
        process_service = ClientProcessService()
        result = process_service.start(
            client_id=client_id,
            client_type=client.client_type,  # client_type 已经是字符串，不需要 .value
            config_file=config_file_name,  # 容器内路径（相对于 /config）
            config_dir=config_dir,  # 宿主机路径（用于挂载）
            web3signer_url=client.web3signer_url,  # Web3Signer URL
            pubkeys=pubkeys,  # 公钥列表
            grpc_endpoint=client.grpc_endpoint  # gRPC 端点（用于调试和可能的命令行参数）
        )
        
        if not result.get("success"):
            # 返回详细的错误信息
            error_detail = {
                "error": result.get("message", "启动失败"),
                "container_name": result.get("container_name"),
                "state": result.get("state"),
                "exit_code": result.get("exit_code"),
                "error_logs": result.get("error_logs"),
                "config_file_path": result.get("config_file_path"),
                "config_dir": result.get("config_dir")
            }
            raise HTTPException(status_code=500, detail=error_detail)
        
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
            client_type=client.client_type  # client_type 已经是字符串，不需要 .value
        )
        
        if not result.get("success"):
            raise HTTPException(status_code=500, detail=result.get("message", "停止失败"))
        
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/clients/{client_id}/pause", response_model=dict)
async def pause_client(
    client_id: int,
    db: Session = Depends(get_db)
):
    """暂停客户端容器"""
    try:
        from app.models.database import ClientInstance
        client = db.query(ClientInstance).filter(ClientInstance.id == client_id).first()
        
        if not client:
            raise HTTPException(status_code=404, detail="客户端不存在")
        
        process_service = ClientProcessService()
        result = process_service.pause(
            client_id=client_id,
            client_type=client.client_type
        )
        
        if not result.get("success"):
            raise HTTPException(status_code=500, detail=result.get("message", "暂停失败"))
        
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/clients/{client_id}/unpause", response_model=dict)
async def unpause_client(
    client_id: int,
    db: Session = Depends(get_db)
):
    """恢复（取消暂停）客户端容器"""
    try:
        from app.models.database import ClientInstance
        client = db.query(ClientInstance).filter(ClientInstance.id == client_id).first()
        
        if not client:
            raise HTTPException(status_code=404, detail="客户端不存在")
        
        process_service = ClientProcessService()
        result = process_service.unpause(
            client_id=client_id,
            client_type=client.client_type
        )
        
        if not result.get("success"):
            raise HTTPException(status_code=500, detail=result.get("message", "恢复失败"))
        
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/clients/{client_id}/destroy", response_model=dict)
async def destroy_client(
    client_id: int,
    db: Session = Depends(get_db)
):
    """销毁（停止并删除）客户端容器"""
    try:
        from app.models.database import ClientInstance
        client = db.query(ClientInstance).filter(ClientInstance.id == client_id).first()
        
        if not client:
            raise HTTPException(status_code=404, detail="客户端不存在")
        
        process_service = ClientProcessService()
        result = process_service.destroy(
            client_id=client_id,
            client_type=client.client_type
        )
        
        if not result.get("success"):
            raise HTTPException(status_code=500, detail=result.get("message", "销毁失败"))
        
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
            client_type=client.client_type  # client_type 已经是字符串，不需要 .value
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
        logs = process_service.get_logs(client_id=client_id, client_type=client.client_type, lines=lines)
        
        return logs
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

