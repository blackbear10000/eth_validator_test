"""
验证者取款 API
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional

from app.dependencies import get_db
from app.services.withdrawal_service import WithdrawalService
from app.core.beacon_api import BeaconAPIClient
from app.models.enums import WithdrawalType

router = APIRouter()


def get_withdrawal_service(db: Session = Depends(get_db)) -> WithdrawalService:
    """获取取款服务"""
    beacon_api = BeaconAPIClient()
    return WithdrawalService(db, beacon_api)


@router.get("/withdrawals/{pubkey}")
async def get_validator_withdrawals(
    pubkey: str,
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    withdrawal_service: WithdrawalService = Depends(get_withdrawal_service)
):
    """获取验证者的取款历史"""
    try:
        withdrawals, total = withdrawal_service.get_validator_withdrawals(
            pubkey,
            limit=limit,
            offset=offset
        )
        
        return {
            'total': total,
            'items': [
                {
                    'id': w.id,
                    'withdrawal_type': w.withdrawal_type,
                    'amount_eth': float(w.amount_eth),
                    'fee_eth': float(w.fee_eth),
                    'net_amount_eth': float(w.amount_eth - w.fee_eth),
                    'withdrawn_at': w.withdrawn_at.isoformat(),
                    'slot': int(w.slot) if w.slot else None,
                    'epoch': int(w.epoch) if w.epoch else None,
                }
                for w in withdrawals
            ]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/withdrawals/{pubkey}/statistics")
async def get_withdrawal_statistics(
    pubkey: str,
    withdrawal_service: WithdrawalService = Depends(get_withdrawal_service)
):
    """获取验证者取款统计"""
    try:
        stats = withdrawal_service.get_total_withdrawals(pubkey)
        return stats
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/withdrawals/sync")
async def sync_withdrawals(
    pubkey: Optional[str] = None,
    withdrawal_service: WithdrawalService = Depends(get_withdrawal_service)
):
    """手动触发取款事件同步"""
    try:
        if pubkey:
            events = withdrawal_service.sync_withdrawals_from_beacon(pubkey)
            return {
                'pubkey': pubkey,
                'synced_count': len(events),
                'message': '取款同步功能需要实际实现（监听链上事件）'
            }
        else:
            return {
                'message': '需要提供 pubkey 参数'
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/withdrawals/calculate-fee")
async def calculate_withdrawal_fee(
    amount_eth: float,
    withdrawal_service: WithdrawalService = Depends(get_withdrawal_service)
):
    """计算取款费用"""
    try:
        from app.core.eth_tools import eth_to_wei
        amount_wei = eth_to_wei(amount_eth)
        fee_info = withdrawal_service.calculate_fee(amount_wei)
        return fee_info
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

