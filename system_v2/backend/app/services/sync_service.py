"""
状态同步服务
定期从 Beacon Chain API 同步验证者状态
"""
import logging
import asyncio
from datetime import datetime
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import and_

from app.models.database import ValidatorKey
from app.models.enums import ValidatorKeyStatus
from app.core.beacon_api import BeaconAPIClient
from app.services.validator_state_machine import ValidatorStateMachine
from app.utils.exceptions import BeaconAPIError, DatabaseError

logger = logging.getLogger(__name__)


class SyncService:
    """
    状态同步服务
    从 Beacon Chain API 同步验证者状态到本地数据库
    """
    
    def __init__(
        self,
        db: Session,
        beacon_api_client: Optional[BeaconAPIClient] = None
    ):
        """
        初始化同步服务
        
        Args:
            db: 数据库会话
            beacon_api_client: Beacon API 客户端
        """
        self.db = db
        self.beacon_api = beacon_api_client or BeaconAPIClient()
        self.state_machine = ValidatorStateMachine(db)
    
    def sync_validator_status(
        self,
        pubkey: str
    ) -> Optional[ValidatorKey]:
        """
        同步单个验证者状态
        
        Args:
            pubkey: 验证者公钥
            
        Returns:
            更新后的 ValidatorKey 对象或 None
        """
        try:
            # 规范化 pubkey（确保有 0x 前缀，小写）
            pubkey_normalized = pubkey.lower().strip()
            if not pubkey_normalized.startswith('0x'):
                pubkey_normalized = f"0x{pubkey_normalized}"
            
            # 查询本地密钥（支持两种格式匹配）
            validator_key = self.db.query(ValidatorKey).filter(
                (ValidatorKey.pubkey == pubkey_normalized) |
                (ValidatorKey.pubkey == pubkey.lower())
            ).first()
            
            if not validator_key:
                logger.warning(f"密钥不存在: {pubkey[:10]}...")
                return None
            
            # 查询链上状态（get_validator 会自动处理 0x 前缀）
            validator_data = self.beacon_api.get_validator(pubkey)
            
            if not validator_data:
                # 验证者在链上不存在（可能是 pending 状态）
                if validator_key.status == ValidatorKeyStatus.PENDING.value:
                    # 保持 pending 状态
                    logger.debug(f"验证者仍在 pending: {pubkey[:10]}...")
                    return validator_key
                elif validator_key.status == ValidatorKeyStatus.ACTIVE.value:
                    # 可能是刚激活但还未上链
                    logger.debug(f"验证者已激活但未上链: {pubkey[:10]}...")
                    return validator_key
                else:
                    logger.warning(f"验证者在链上不存在: {pubkey[:10]}...")
                    return validator_key
            
            # 使用状态机更新状态
            self.state_machine.update_validator_from_beacon_data(validator_key, validator_data)
            
            return validator_key
            
        except BeaconAPIError as e:
            logger.error(f"同步验证者状态失败 ({pubkey[:10]}...): {e}")
            return None
        except Exception as e:
            logger.error(f"同步验证者状态时出错 ({pubkey[:10]}...): {e}")
            return None
    
    def sync_multiple_validators(
        self,
        pubkeys: List[str]
    ) -> Dict[str, Any]:
        """
        批量同步多个验证者状态
        
        Args:
            pubkeys: 验证者公钥列表
            
        Returns:
            同步结果统计
        """
        # 分批查询（Beacon API 可能有数量限制）
        batch_size = 100
        synced_count = 0
        failed_count = 0
        
        for i in range(0, len(pubkeys), batch_size):
            batch_pubkeys = pubkeys[i:i + batch_size]
            
            try:
                # 批量查询验证者信息
                validators = self.beacon_api.get_validators(batch_pubkeys)
                
                # 更新每个验证者状态
                for pubkey in batch_pubkeys:
                    # 规范化 pubkey（确保有 0x 前缀，小写）
                    pubkey_normalized = pubkey.lower().strip()
                    if not pubkey_normalized.startswith('0x'):
                        pubkey_normalized = f"0x{pubkey_normalized}"
                    
                    validator_key = self.db.query(ValidatorKey).filter(
                        (ValidatorKey.pubkey == pubkey_normalized) |
                        (ValidatorKey.pubkey == pubkey.lower())
                    ).first()
                    
                    if not validator_key:
                        failed_count += 1
                        continue
                    
                    # get_validators 返回的字典 key 是带 0x 前缀的规范化格式
                    validator_data = validators.get(pubkey_normalized)
                    if validator_data:
                        # 使用已有逻辑更新状态
                        self._update_validator_from_beacon_data(validator_key, validator_data)
                        synced_count += 1
                    else:
                        # 验证者在链上不存在，保持当前状态或标记为 pending
                        if validator_key.status == ValidatorKeyStatus.PENDING.value:
                            synced_count += 1  # 保持状态也算同步成功
                        else:
                            failed_count += 1
                
            except Exception as e:
                logger.error(f"批量同步失败 (批次 {i//batch_size + 1}): {e}")
                failed_count += len(batch_pubkeys)
        
        self.db.commit()
        
        logger.info(f"批量同步完成: 成功 {synced_count}, 失败 {failed_count}")
        
        return {
            'synced': synced_count,
            'failed': failed_count,
            'total': len(pubkeys)
        }
    
    def _update_validator_from_beacon_data(
        self,
        validator_key: ValidatorKey,
        validator_data: Dict[str, Any]
    ) -> None:
        """
        从 Beacon API 数据更新验证者状态（内部方法）
        
        Args:
            validator_key: ValidatorKey 对象
            validator_data: Beacon API 返回的验证者数据
        """
        # 使用状态机更新状态
        self.state_machine.update_validator_from_beacon_data(validator_key, validator_data)
    
    def sync_all_pending_validators(self) -> Dict[str, Any]:
        """
        同步所有需要同步的验证者（pending/deposited/active_on_chain 状态）
        
        Returns:
            同步结果统计
        """
        # 查询需要同步的验证者
        validators_to_sync = self.db.query(ValidatorKey).filter(
            ValidatorKey.status.in_([
                ValidatorKeyStatus.PENDING.value,
                ValidatorKeyStatus.DEPOSITED.value,
                ValidatorKeyStatus.ACTIVE_ON_CHAIN.value
            ])
        ).all()
        
        if not validators_to_sync:
            logger.info("没有需要同步的验证者")
            return {'synced': 0, 'failed': 0, 'total': 0}
        
        pubkeys = [v.pubkey for v in validators_to_sync]
        result = self.sync_multiple_validators(pubkeys)
        return result
    
    def health_check(self) -> bool:
        """
        检查同步服务健康状态
        
        Returns:
            是否健康
        """
        return self.beacon_api.health_check()

