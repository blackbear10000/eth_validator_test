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
        
        # 获取数据库中所有 ACTIVE 状态的密钥
        db_active_keys = db.query(ValidatorKey).filter(
            ValidatorKey.status == ValidatorKeyStatus.ACTIVE.value
        ).all()
        db_pubkeys = {key.pubkey.lower() for key in db_active_keys}
        
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

