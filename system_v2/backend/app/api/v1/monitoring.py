"""
监控 API
"""
import logging
import concurrent.futures
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
            # 使用 VaultClient 的健康检查方法（内部使用 requests，更可靠）
            vault_client = VaultClient()
            vault_health = vault_client.health_check()
            logger.info(f"Vault 健康检查成功: healthy={vault_health}")
        except Exception as health_error:
            logger.error(f"Vault 健康检查失败: {health_error}", exc_info=True)
            # 如果 VaultClient 初始化失败（可能是认证问题），尝试直接调用健康检查端点
            try:
                import requests
                from app.config import settings
                vault_url = settings.vault_url
                logger.info(f"尝试直接调用健康检查端点: {vault_url}")
                health_url = f"{vault_url.rstrip('/')}/v1/sys/health"
                response = requests.get(health_url, timeout=5)
                response.raise_for_status()
                health = response.json()
                initialized = health.get('initialized', False)
                sealed = health.get('sealed', True)
                vault_health = initialized and not sealed
                logger.info(f"直接健康检查成功: initialized={initialized}, sealed={sealed}, healthy={vault_health}")
            except Exception as e:
                logger.error(f"直接健康检查也失败: {e}", exc_info=True)
        
        # Web3Signer 健康检查
        web3signer_primary = False
        web3signer_secondary = False
        haproxy = False
        try:
            web3signer_client = Web3SignerClient()
            logger.debug(f"Web3Signer URLs: primary={web3signer_client.primary_url}, secondary={web3signer_client.secondary_url}, haproxy={web3signer_client.haproxy_url}")
            web3signer_primary = web3signer_client.health_check("primary")
            web3signer_secondary = web3signer_client.health_check("secondary")
            haproxy = web3signer_client.health_check("haproxy")
            logger.info(f"Web3Signer 健康检查结果: primary={web3signer_primary}, secondary={web3signer_secondary}, haproxy={haproxy}")
        except Exception as e:
            logger.error(f"Web3Signer 健康检查异常: {e}", exc_info=True)
        
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
        # 密钥统计（快速查询）
        total_keys = db.query(ValidatorKey).count()
        
        keys_by_status = {}
        for status in ValidatorKeyStatus:
            count = db.query(ValidatorKey).filter(
                ValidatorKey.status == status.value
            ).count()
            keys_by_status[status.value] = count
        
        # 存款统计（快速查询）
        total_deposits = db.query(DepositTransaction).count()
        
        # 活跃验证者
        active_validators = keys_by_status.get(ValidatorKeyStatus.ACTIVE_ON_CHAIN.value, 0)
        
        # 总收益（简化，实际应该从链上查询）
        total_rewards_eth = 0.0
        
        # 系统健康检查（使用较短的超时时间，避免阻塞）
        # 使用并发检查以提高响应速度
        
        def check_vault_health():
            try:
                vault_client = VaultClient()
                return vault_client.health_check()
            except Exception as e:
                logger.debug(f"Vault 健康检查失败: {e}")
                return False
        
        def check_web3signer_health():
            try:
                web3signer_client = Web3SignerClient()
                primary = web3signer_client.health_check("primary")
                secondary = web3signer_client.health_check("secondary")
                haproxy = web3signer_client.health_check("haproxy")
                return primary, secondary, haproxy
            except Exception as e:
                logger.debug(f"Web3Signer 健康检查失败: {e}")
                return False, False, False
        
        def check_beacon_api_health():
            try:
                beacon_api = BeaconAPIClient()
                return beacon_api.health_check()
            except Exception as e:
                logger.debug(f"Beacon API 健康检查失败: {e}")
                return False
        
        # 并发执行健康检查（最多等待 10 秒）
        vault_health = False
        web3signer_primary = False
        web3signer_secondary = False
        haproxy = False
        beacon_api_health = False
        
        try:
            with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
                vault_future = executor.submit(check_vault_health)
                web3signer_future = executor.submit(check_web3signer_health)
                beacon_future = executor.submit(check_beacon_api_health)
                
                # 等待所有检查完成，最多等待 10 秒
                try:
                    vault_health = vault_future.result(timeout=10)
                    web3signer_result = web3signer_future.result(timeout=10)
                    if isinstance(web3signer_result, tuple):
                        web3signer_primary, web3signer_secondary, haproxy = web3signer_result
                    beacon_api_health = beacon_future.result(timeout=10)
                except concurrent.futures.TimeoutError:
                    logger.warning("健康检查超时，使用默认值")
        except Exception as e:
            logger.error(f"健康检查执行失败: {e}", exc_info=True)
        
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
        logger.error(f"获取系统概览失败: {e}", exc_info=True)
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

