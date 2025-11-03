"""
监控 API
"""
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

router = APIRouter()


@router.get("/monitoring/health", response_model=SystemHealthResponse)
async def system_health():
    """系统健康检查"""
    try:
        vault_client = VaultClient()
        web3signer_client = Web3SignerClient()
        beacon_api = BeaconAPIClient()
        
        vault_health = vault_client.health_check()
        web3signer_primary = web3signer_client.health_check("primary")
        web3signer_secondary = web3signer_client.health_check("secondary")
        haproxy = web3signer_client.health_check("haproxy")
        beacon_api_health = beacon_api.health_check()
        
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
        
        # 系统健康
        vault_client = VaultClient()
        web3signer_client = Web3SignerClient()
        beacon_api = BeaconAPIClient()
        
        vault_health = vault_client.health_check()
        web3signer_primary = web3signer_client.health_check("primary")
        web3signer_secondary = web3signer_client.health_check("secondary")
        haproxy = web3signer_client.health_check("haproxy")
        beacon_api_health = beacon_api.health_check()
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

