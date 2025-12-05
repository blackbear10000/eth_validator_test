"""
Web3Signer 监控 API
提供 Web3Signer 实例状态、密钥列表和同步状态查询
"""
import logging
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.web3signer_client import Web3SignerClient
from app.models.database import ValidatorKey
from app.models.enums import ValidatorKeyStatus
from app.dependencies import get_db

logger = logging.getLogger(__name__)

router = APIRouter()


def get_web3signer_client() -> Web3SignerClient:
    """获取 Web3Signer 客户端"""
    return Web3SignerClient()


@router.get("/web3signer/status")
async def get_web3signer_status(
    web3signer_client: Web3SignerClient = Depends(get_web3signer_client)
):
    """
    获取 Web3Signer 实例的健康状态
    
    Returns:
        包含 primary 和 secondary 实例健康状态的字典
    """
    try:
        primary_health = web3signer_client.health_check("primary")
        secondary_health = web3signer_client.health_check("secondary")
        haproxy_health = web3signer_client.health_check("haproxy")
        
        return {
            "primary": {
                "healthy": primary_health,
                "url": web3signer_client.primary_url
            },
            "secondary": {
                "healthy": secondary_health,
                "url": web3signer_client.secondary_url
            },
            "haproxy": {
                "healthy": haproxy_health,
                "url": web3signer_client.haproxy_url
            }
        }
    except Exception as e:
        logger.error(f"获取 Web3Signer 状态失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/web3signer/keys")
async def get_web3signer_keys(
    instance: str = Query("both", description="实例名称: primary, secondary, 或 both"),
    web3signer_client: Web3SignerClient = Depends(get_web3signer_client),
    db: Session = Depends(get_db)
):
    """
    获取 Web3Signer 实例加载的密钥列表
    
    Args:
        instance: 实例名称 (primary/secondary/both)
        
    Returns:
        密钥列表，包含公钥和数据库中的状态信息
    """
    try:
        result = {}
        
        if instance in ["primary", "both"]:
            try:
                primary_keys = web3signer_client.get_public_keys("primary")
                result["primary"] = {
                    "keys": primary_keys,
                    "count": len(primary_keys)
                }
            except Exception as e:
                logger.error(f"获取 Web3Signer primary 密钥列表失败: {e}")
                result["primary"] = {
                    "keys": [],
                    "count": 0,
                    "error": str(e)
                }
        
        if instance in ["secondary", "both"]:
            try:
                secondary_keys = web3signer_client.get_public_keys("secondary")
                result["secondary"] = {
                    "keys": secondary_keys,
                    "count": len(secondary_keys)
                }
            except Exception as e:
                logger.error(f"获取 Web3Signer secondary 密钥列表失败: {e}")
                result["secondary"] = {
                    "keys": [],
                    "count": 0,
                    "error": str(e)
                }
        
        # 如果查询了密钥，同时获取数据库中的密钥信息
        if instance in ["primary", "secondary", "both"]:
            all_keys = set()
            if "primary" in result:
                all_keys.update(result["primary"].get("keys", []))
            if "secondary" in result:
                all_keys.update(result["secondary"].get("keys", []))
            
            # 查询数据库中的密钥信息
            if all_keys:
                # 规范化 pubkey（确保有 0x 前缀，小写）
                normalized_keys = []
                for key in all_keys:
                    key_lower = key.lower().strip()
                    if not key_lower.startswith('0x'):
                        key_lower = f"0x{key_lower}"
                    normalized_keys.append(key_lower)
                
                db_keys = db.query(ValidatorKey).filter(
                    ValidatorKey.pubkey.in_(normalized_keys)
                ).all()
                
                # 创建 pubkey -> ValidatorKey 的映射
                key_map = {key.pubkey.lower(): key for key in db_keys}
                
                # 为每个密钥添加数据库信息
                for instance_name in ["primary", "secondary"]:
                    if instance_name in result:
                        keys_with_info = []
                        for pubkey in result[instance_name].get("keys", []):
                            pubkey_normalized = pubkey.lower().strip()
                            if not pubkey_normalized.startswith('0x'):
                                pubkey_normalized = f"0x{pubkey_normalized}"
                            
                            key_info = {
                                "pubkey": pubkey,
                                "in_database": pubkey_normalized in key_map
                            }
                            
                            if pubkey_normalized in key_map:
                                db_key = key_map[pubkey_normalized]
                                key_info["status"] = db_key.status
                                key_info["activated_at"] = db_key.activated_at.isoformat() if db_key.activated_at else None
                            else:
                                key_info["status"] = None
                                key_info["activated_at"] = None
                            
                            keys_with_info.append(key_info)
                        
                        result[instance_name]["keys"] = keys_with_info
        
        return result
    except Exception as e:
        logger.error(f"获取 Web3Signer 密钥列表失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/web3signer/sync-status")
async def get_web3signer_sync_status(
    instance: str = Query("both", description="实例名称: primary, secondary, 或 both"),
    web3signer_client: Web3SignerClient = Depends(get_web3signer_client),
    db: Session = Depends(get_db)
):
    """
    获取 Web3Signer 与数据库的同步状态对比
    
    Args:
        instance: 实例名称 (primary/secondary/both)
        
    Returns:
        同步状态对比，包括：
        - 在数据库中但未加载的密钥
        - 已加载但不在数据库中的密钥
        - 已同步的密钥
    """
    try:
        result = {}
        
        # 获取数据库中所有非 UNUSED 状态的密钥（这些密钥应该被加载到 Web3Signer）
        db_non_unused_keys = db.query(ValidatorKey).filter(
            ValidatorKey.status != ValidatorKeyStatus.UNUSED.value
        ).all()
        db_pubkeys = {key.pubkey.lower() for key in db_non_unused_keys}
        
        if instance in ["primary", "both"]:
            try:
                primary_keys = web3signer_client.get_public_keys("primary")
                primary_pubkeys = {
                    (key.lower().strip() if not key.lower().strip().startswith('0x') else f"0x{key.lower().strip()}")
                    for key in primary_keys
                }
                # 确保所有都有 0x 前缀
                primary_pubkeys = {
                    key if key.startswith('0x') else f"0x{key}"
                    for key in primary_pubkeys
                }
                
                missing_in_web3signer = db_pubkeys - primary_pubkeys
                extra_in_web3signer = primary_pubkeys - db_pubkeys
                synced = db_pubkeys & primary_pubkeys
                
                result["primary"] = {
                    "missing_in_web3signer": list(missing_in_web3signer),
                    "extra_in_web3signer": list(extra_in_web3signer),
                    "synced": list(synced),
                    "stats": {
                        "db_active_count": len(db_pubkeys),
                        "web3signer_count": len(primary_pubkeys),
                        "missing_count": len(missing_in_web3signer),
                        "extra_count": len(extra_in_web3signer),
                        "synced_count": len(synced)
                    }
                }
            except Exception as e:
                logger.error(f"获取 Web3Signer primary 同步状态失败: {e}")
                result["primary"] = {
                    "error": str(e)
                }
        
        if instance in ["secondary", "both"]:
            try:
                secondary_keys = web3signer_client.get_public_keys("secondary")
                secondary_pubkeys = {
                    (key.lower().strip() if not key.lower().strip().startswith('0x') else f"0x{key.lower().strip()}")
                    for key in secondary_keys
                }
                # 确保所有都有 0x 前缀
                secondary_pubkeys = {
                    key if key.startswith('0x') else f"0x{key}"
                    for key in secondary_pubkeys
                }
                
                missing_in_web3signer = db_pubkeys - secondary_pubkeys
                extra_in_web3signer = secondary_pubkeys - db_pubkeys
                synced = db_pubkeys & secondary_pubkeys
                
                result["secondary"] = {
                    "missing_in_web3signer": list(missing_in_web3signer),
                    "extra_in_web3signer": list(extra_in_web3signer),
                    "synced": list(synced),
                    "stats": {
                        "db_active_count": len(db_pubkeys),
                        "web3signer_count": len(secondary_pubkeys),
                        "missing_count": len(missing_in_web3signer),
                        "extra_count": len(extra_in_web3signer),
                        "synced_count": len(synced)
                    }
                }
            except Exception as e:
                logger.error(f"获取 Web3Signer secondary 同步状态失败: {e}")
                result["secondary"] = {
                    "error": str(e)
                }
        
        return result
    except Exception as e:
        logger.error(f"获取 Web3Signer 同步状态失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/web3signer/sync-configs")
async def sync_web3signer_configs(
    cleanup_orphaned: bool = Query(True, description="是否清理孤立的配置文件"),
    db: Session = Depends(get_db),
    web3signer_client: Web3SignerClient = Depends(get_web3signer_client)
):
    """
    同步 Web3Signer 密钥配置文件并触发轮转加载
    
    功能：
    1. 为所有非 UNUSED 状态的密钥生成配置文件
    2. 删除 UNUSED 状态密钥的配置文件
    3. 清理孤立的配置文件（数据库中不存在的密钥对应的配置文件）
    4. 触发 Web3Signer 轮转加载（先加载 Web3Signer-2，再加载 Web3Signer-1）
    
    注意：Web3Signer 使用 key-store-path 配置时，可能不支持运行时重新扫描。
    如果 reload 失败，需要重启 Web3Signer 容器才能加载新配置文件。
    
    Args:
        cleanup_orphaned: 是否清理孤立的配置文件（默认：True）
    
    Returns:
        同步结果和加载结果
    """
    try:
        from app.services.web3signer_key_config_service import Web3SignerKeyConfigService
        
        # 同步配置文件
        config_service = Web3SignerKeyConfigService(db)
        sync_result = config_service.sync_key_configs(cleanup_orphaned=cleanup_orphaned)
        
        # 触发轮转加载
        reload_result = web3signer_client.zero_downtime_reload(wait_for_health=True)
        
        # 检查是否真的加载了密钥
        needs_restart = False
        if reload_result.get('success'):
            # 验证是否真的加载了密钥
            try:
                primary_keys = web3signer_client.get_public_keys("primary")
                secondary_keys = web3signer_client.get_public_keys("secondary")
                total_keys = len(primary_keys) + len(secondary_keys)
                
                if total_keys == 0 and (sync_result.get('created', 0) > 0 or sync_result.get('removed', 0) > 0):
                    needs_restart = True
                    logger.warning("Web3Signer reload 完成，但没有加载密钥，可能需要重启容器")
            except Exception as e:
                logger.warning(f"无法验证密钥加载状态: {e}")
        
        return {
            "sync_result": sync_result,
            "reload_result": reload_result,
            "success": reload_result.get('success', False),
            "needs_restart": needs_restart,
            "message": "配置文件已同步。如果 Web3Signer 没有加载密钥，请重启 Web3Signer 容器。" if needs_restart else "配置文件已同步并重新加载"
        }
    except Exception as e:
        logger.error(f"同步 Web3Signer 配置失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/web3signer/restart")
async def restart_web3signer():
    """
    重启 Web3Signer 容器以加载新的配置文件
    
    注意：这会短暂中断 Web3Signer 服务，但 HAProxy 会处理故障转移
    
    Returns:
        重启结果
    """
    try:
        import subprocess
        import time
        
        result = {
            "primary": False,
            "secondary": False,
            "success": False
        }
        
        # 检查是否有权限执行 docker 命令
        # 在 Docker 容器内，需要挂载 Docker socket 才能执行 docker 命令
        try:
            # 尝试重启 web3signer-1
            logger.info("重启 Web3Signer-1 容器...")
            restart_1 = subprocess.run(
                ["docker", "restart", "web3signer-1"],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if restart_1.returncode == 0:
                logger.info("Web3Signer-1 重启成功")
                result["primary"] = True
                # 等待启动
                time.sleep(10)
            else:
                logger.error(f"Web3Signer-1 重启失败: {restart_1.stderr}")
                raise HTTPException(
                    status_code=500,
                    detail=f"无法重启 Web3Signer-1: {restart_1.stderr}"
                )
            
            # 尝试重启 web3signer-2
            logger.info("重启 Web3Signer-2 容器...")
            restart_2 = subprocess.run(
                ["docker", "restart", "web3signer-2"],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if restart_2.returncode == 0:
                logger.info("Web3Signer-2 重启成功")
                result["secondary"] = True
                # 等待启动
                time.sleep(10)
            else:
                logger.error(f"Web3Signer-2 重启失败: {restart_2.stderr}")
                raise HTTPException(
                    status_code=500,
                    detail=f"无法重启 Web3Signer-2: {restart_2.stderr}"
                )
            
            # 验证服务是否启动
            web3signer_client = Web3SignerClient()
            if web3signer_client.health_check("primary") and web3signer_client.health_check("secondary"):
                result["success"] = True
                logger.info("Web3Signer 容器重启成功，服务已恢复")
            else:
                logger.warning("Web3Signer 容器已重启，但健康检查未通过，请稍后重试")
            
            return result
            
        except FileNotFoundError:
            raise HTTPException(
                status_code=503,
                detail="无法执行 docker 命令。后端容器可能没有访问 Docker socket 的权限。请手动重启 Web3Signer 容器：docker restart web3signer-1 web3signer-2"
            )
        except subprocess.TimeoutExpired:
            raise HTTPException(
                status_code=500,
                detail="重启 Web3Signer 容器超时"
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"重启 Web3Signer 失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"重启 Web3Signer 失败: {str(e)}。请手动重启：docker restart web3signer-1 web3signer-2"
        )


@router.post("/web3signer/cleanup-configs")
async def cleanup_web3signer_configs(
    db: Session = Depends(get_db)
):
    """
    清理所有孤立的 Web3Signer 配置文件
    
    功能：
    删除所有数据库中不存在的密钥对应的配置文件
    
    Returns:
        清理结果
    """
    try:
        from app.services.web3signer_key_config_service import Web3SignerKeyConfigService
        
        config_service = Web3SignerKeyConfigService(db)
        cleanup_result = config_service.cleanup_orphaned_configs()
        
        return {
            "success": cleanup_result['errors'] == 0,
            "removed": cleanup_result['removed'],
            "errors": cleanup_result['errors'],
            "files": cleanup_result['files'],
            "message": f"已清理 {cleanup_result['removed']} 个孤立配置文件"
        }
    except Exception as e:
        logger.error(f"清理 Web3Signer 配置文件失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

