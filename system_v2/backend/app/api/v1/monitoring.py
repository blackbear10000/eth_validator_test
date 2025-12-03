"""
监控 API
"""
import logging
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.dependencies import get_db
from app.models.database import ValidatorKey, DepositTransaction
from app.models.enums import ValidatorKeyStatus
from app.core.vault_client import VaultClient
from app.core.web3signer_client import Web3SignerClient
from app.core.beacon_api import BeaconAPIClient
from app.models.schemas import SystemHealthResponse, SystemOverviewResponse

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/monitoring/health", response_model=SystemHealthResponse)
async def system_health():
    """系统健康检查"""
    try:
        # Vault 健康检查（不需要认证）
        vault_health = False
        try:
            # 直接使用不需要认证的健康检查方法
            import hvac
            from app.config import settings
            vault_url = settings.vault_url
            logger.debug(f"尝试连接 Vault: {vault_url}")
            unauthenticated_client = hvac.Client(url=vault_url)
            health = unauthenticated_client.sys.read_health_status()
            initialized = health.get('initialized', False)
            sealed = health.get('sealed', True)
            vault_health = initialized and not sealed
            logger.info(f"Vault 健康检查成功: url={vault_url}, initialized={initialized}, sealed={sealed}, healthy={vault_health}")
        except Exception as health_error:
            logger.error(f"Vault 健康检查失败 (url={settings.vault_url}): {health_error}", exc_info=True)
            # 如果直接健康检查也失败，尝试使用 VaultClient（可能需要认证）
            try:
                logger.info("尝试使用 VaultClient 进行健康检查...")
                vault_client = VaultClient()
                vault_health = vault_client.health_check()
                logger.info(f"VaultClient 健康检查成功: {vault_health}")
            except Exception as e:
                logger.error(f"VaultClient 健康检查也失败: {e}", exc_info=True)
        
        # Web3Signer 健康检查
        web3signer_primary = False
        web3signer_secondary = False
        haproxy = False
        try:
            web3signer_client = Web3SignerClient()
            web3signer_primary = web3signer_client.health_check("primary")
            web3signer_secondary = web3signer_client.health_check("secondary")
            haproxy = web3signer_client.health_check("haproxy")
        except Exception as e:
            logger.error(f"Web3Signer 健康检查失败: {e}")
        
        # Beacon API 健康检查
        beacon_api_health = False
        try:
            beacon_api = BeaconAPIClient()
            beacon_api_health = beacon_api.health_check()
        except Exception as e:
            logger.error(f"Beacon API 健康检查失败: {e}")
        
        # PostgreSQL 健康检查（简化）
        postgresql_health = True  # 实际应该检查数据库连接
        
        overall = all([
            vault_health,
            postgresql_health,
            web3signer_primary,
            web3signer_secondary,
            haproxy,
            beacon_api_health
        ])
        
        return SystemHealthResponse(
            vault=vault_health,
            postgresql=postgresql_health,
            web3signer_primary=web3signer_primary,
            web3signer_secondary=web3signer_secondary,
            haproxy=haproxy,
            beacon_api=beacon_api_health,
            overall=overall
        )
    except Exception as e:
        logger.error(f"系统健康检查失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/monitoring/overview", response_model=SystemOverviewResponse)
async def system_overview(db: Session = Depends(get_db)):
    """系统概览"""
    try:
        # 密钥统计
        total_keys = db.query(ValidatorKey).count()
        
        keys_by_status = {}
        for status in ValidatorKeyStatus:
            count = db.query(ValidatorKey).filter(
                ValidatorKey.status == status.value
            ).count()
            keys_by_status[status.value] = count
        
        # 存款统计
        total_deposits = db.query(DepositTransaction).count()
        
        # 活跃验证者
        active_validators = keys_by_status.get(ValidatorKeyStatus.ACTIVE_ON_CHAIN.value, 0)
        
        # 总收益（简化，实际应该从链上查询）
        total_rewards_eth = 0.0
        
        # 系统健康（使用与 system_health 相同的逻辑）
        vault_health = False
        try:
            # 直接使用不需要认证的健康检查方法
            import hvac
            from app.config import settings
            vault_url = settings.vault_url
            logger.debug(f"尝试连接 Vault: {vault_url}")
            unauthenticated_client = hvac.Client(url=vault_url)
            health = unauthenticated_client.sys.read_health_status()
            initialized = health.get('initialized', False)
            sealed = health.get('sealed', True)
            vault_health = initialized and not sealed
            logger.info(f"Vault 健康检查成功: url={vault_url}, initialized={initialized}, sealed={sealed}, healthy={vault_health}")
        except Exception as health_error:
            logger.error(f"Vault 健康检查失败 (url={settings.vault_url}): {health_error}", exc_info=True)
            # 如果直接健康检查也失败，尝试使用 VaultClient（可能需要认证）
            try:
                logger.info("尝试使用 VaultClient 进行健康检查...")
                vault_client = VaultClient()
                vault_health = vault_client.health_check()
                logger.info(f"VaultClient 健康检查成功: {vault_health}")
            except Exception as e:
                logger.error(f"VaultClient 健康检查也失败: {e}", exc_info=True)
        
        web3signer_primary = False
        web3signer_secondary = False
        haproxy = False
        try:
            web3signer_client = Web3SignerClient()
            web3signer_primary = web3signer_client.health_check("primary")
            web3signer_secondary = web3signer_client.health_check("secondary")
            haproxy = web3signer_client.health_check("haproxy")
        except Exception as e:
            logger.error(f"Web3Signer 健康检查失败: {e}")
        
        beacon_api_health = False
        try:
            beacon_api = BeaconAPIClient()
            beacon_api_health = beacon_api.health_check()
        except Exception as e:
            logger.error(f"Beacon API 健康检查失败: {e}")
        
        postgresql_health = True
        
        overall = all([
            vault_health,
            postgresql_health,
            web3signer_primary,
            web3signer_secondary,
            haproxy,
            beacon_api_health
        ])
        
        health = SystemHealthResponse(
            vault=vault_health,
            postgresql=postgresql_health,
            web3signer_primary=web3signer_primary,
            web3signer_secondary=web3signer_secondary,
            haproxy=haproxy,
            beacon_api=beacon_api_health,
            overall=overall
        )
        
        return SystemOverviewResponse(
            total_keys=total_keys,
            keys_by_status=keys_by_status,
            total_deposits=total_deposits,
            active_validators=active_validators,
            total_rewards_eth=total_rewards_eth,
            system_health=health
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/monitoring/validators/{pubkey}", response_model=dict)
async def get_validator_performance(
    pubkey: str,
    db: Session = Depends(get_db)
):
    """获取验证者性能数据"""
    try:
        validator_key = db.query(ValidatorKey).filter(
            ValidatorKey.pubkey == pubkey.lower()
        ).first()
        
        if not validator_key:
            raise HTTPException(status_code=404, detail="验证者不存在")
        
        # 查询链上数据
        beacon_api = BeaconAPIClient()
        validator_data = beacon_api.get_validator(pubkey)
        
        if not validator_data:
            return {
                "pubkey": pubkey,
                "status": validator_key.status,
                "message": "验证者在链上不存在"
            }
        
        validator_info = validator_data.get('validator', {})
        balance = validator_data.get('balance', '0')
        effective_balance = validator_info.get('effective_balance', '0')
        
        return {
            "pubkey": pubkey,
            "status": validator_key.status,
            "balance_eth": float(balance) / 1e18,
            "effective_balance_eth": float(effective_balance) / 1e9,
            "activation_epoch": validator_info.get('activation_epoch'),
            "exit_epoch": validator_info.get('exit_epoch')
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

