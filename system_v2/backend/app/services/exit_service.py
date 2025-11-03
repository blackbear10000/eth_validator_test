"""
验证者退出服务
处理验证者自愿退出流程
"""
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session

from app.models.database import ValidatorKey, ValidatorClientKey
from app.models.enums import ValidatorKeyStatus
from app.core.exit_generator import ExitGenerator
from app.core.beacon_api import BeaconAPIClient
from app.core.web3signer_client import Web3SignerClient
from app.services.key_management import KeyManagementService
from app.services.client_management import ClientManagementService
from app.utils.exceptions import DepositGenerationError, DatabaseError

logger = logging.getLogger(__name__)


class ExitService:
    """
    验证者退出服务
    处理退出签名生成、提交、状态更新和密钥移除
    """
    
    def __init__(
        self,
        db: Session,
        exit_generator: Optional[ExitGenerator] = None,
        beacon_api: Optional[BeaconAPIClient] = None,
        web3signer_client: Optional[Web3SignerClient] = None,
        key_service: Optional[KeyManagementService] = None,
        client_service: Optional[ClientManagementService] = None
    ):
        """
        初始化退出服务
        
        Args:
            db: 数据库会话
            exit_generator: 退出签名生成器
            beacon_api: Beacon API 客户端
            web3signer_client: Web3Signer 客户端
            key_service: 密钥管理服务
            client_service: 客户端管理服务
        """
        self.db = db
        self.exit_generator = exit_generator or ExitGenerator()
        self.beacon_api = beacon_api or BeaconAPIClient()
        self.web3signer_client = web3signer_client or Web3SignerClient()
        self.key_service = key_service
        self.client_service = client_service
    
    def get_validator_index(self, pubkey: str) -> Optional[int]:
        """
        从 Beacon Chain 获取验证者索引
        
        Args:
            pubkey: 验证者公钥
            
        Returns:
            验证者索引或 None
        """
        try:
            validator_data = self.beacon_api.get_validator(pubkey)
            if validator_data:
                validator_info = validator_data.get('validator', {})
                index = validator_info.get('index')
                if index:
                    return int(index)
            return None
        except Exception as e:
            logger.error(f"获取验证者索引失败: {e}")
            return None
    
    def generate_exit_signature(
        self,
        pubkey: str,
        epoch: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        生成验证者退出签名
        
        Args:
            pubkey: 验证者公钥
            epoch: 退出 epoch（可选）
            
        Returns:
            退出签名数据
        """
        try:
            # 查询验证者
            validator_key = self.db.query(ValidatorKey).filter(
                ValidatorKey.pubkey == pubkey.lower()
            ).first()
            
            if not validator_key:
                raise ValueError(f"验证者不存在: {pubkey}")
            
            # 检查状态
            if validator_key.status == ValidatorKeyStatus.EXITED.value:
                raise ValueError(f"验证者已退出: {pubkey}")
            
            # 获取验证者索引（从链上查询）
            validator_index = self.get_validator_index(pubkey)
            if validator_index is None:
                raise ValueError(f"无法获取验证者索引: {pubkey}")
            
            # 生成退出签名
            exit_data = self.exit_generator.generate_exit_signature(
                pubkey=pubkey,
                validator_index=validator_index,
                epoch=epoch
            )
            
            logger.info(f"退出签名生成成功: {pubkey[:10]}...")
            return exit_data
            
        except Exception as e:
            logger.error(f"生成退出签名失败: {e}")
            raise DepositGenerationError(f"生成退出签名失败: {e}")
    
    def submit_exit(
        self,
        pubkey: str,
        exit_data: Optional[Dict[str, Any]] = None,
        epoch: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        提交验证者退出
        
        Args:
            pubkey: 验证者公钥
            exit_data: 退出签名数据（可选，如果不提供则生成）
            epoch: 退出 epoch（可选）
            
        Returns:
            提交结果
        """
        try:
            # 生成退出签名（如果未提供）
            if exit_data is None:
                exit_data = self.generate_exit_signature(pubkey, epoch)
            
            # 提交到 Beacon Chain API
            import requests
            response = requests.post(
                f"{self.beacon_api.base_url}/eth/v1/beacon/pool/voluntary_exits",
                json=exit_data,
                timeout=10
            )
            
            if response.status_code in [200, 202]:
                # 更新状态为 pending_exit
                validator_key = self.db.query(ValidatorKey).filter(
                    ValidatorKey.pubkey == pubkey.lower()
                ).first()
                
                if validator_key:
                    validator_key.status = ValidatorKeyStatus.PENDING_EXIT.value
                
                self.db.commit()
                
                logger.info(f"退出提交成功: {pubkey[:10]}...")
                return {
                    'pubkey': pubkey,
                    'status': 'submitted',
                    'exit_data': exit_data
                }
            else:
                raise Exception(f"Beacon API 返回错误: {response.status_code}, {response.text}")
                
        except Exception as e:
            logger.error(f"提交退出失败: {e}")
            raise DepositGenerationError(f"提交退出失败: {e}")
    
    def remove_key_from_system(
        self,
        pubkey: str
    ) -> Dict[str, Any]:
        """
        从系统中移除验证者密钥
        
        包括：
        1. 从 Web3Signer 删除密钥
        2. 从客户端映射表移除
        3. 更新客户端配置文件
        
        Args:
            pubkey: 验证者公钥
            
        Returns:
            移除结果
        """
        result = {
            'pubkey': pubkey,
            'web3signer_removed': False,
            'client_mappings_removed': 0,
            'configs_updated': []
        }
        
        try:
            # 1. 从 Web3Signer 删除密钥（零停机删除）
            try:
                # 先尝试从两个实例删除
                self.web3signer_client.delete_key(pubkey, instance="primary")
                self.web3signer_client.delete_key(pubkey, instance="secondary")
                result['web3signer_removed'] = True
                logger.info(f"密钥已从 Web3Signer 删除: {pubkey[:10]}...")
            except Exception as e:
                logger.warning(f"从 Web3Signer 删除密钥失败: {e}")
            
            # 2. 从客户端映射表移除
            client_keys = self.db.query(ValidatorClientKey).filter(
                ValidatorClientKey.pubkey == pubkey.lower(),
                ValidatorClientKey.status == "active"
            ).all()
            
            if client_keys and self.client_service:
                for client_key in client_keys:
                    client_instance = client_key.client_instance
                    if client_instance:
                        # 从客户端移除密钥
                        self.client_service.remove_keys_from_client(
                            client_instance,
                            [pubkey]
                        )
                        result['client_mappings_removed'] += 1
                        result['configs_updated'].append(client_instance.name)
            
            self.db.commit()
            
            logger.info(f"密钥已从系统移除: {pubkey[:10]}...")
            return result
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"移除密钥失败: {e}")
            raise DatabaseError(f"移除密钥失败: {e}")
    
    def batch_exit_validators(
        self,
        pubkeys: List[str],
        epoch: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        批量退出验证者
        
        Args:
            pubkeys: 验证者公钥列表
            epoch: 退出 epoch（可选）
            
        Returns:
            退出结果列表
        """
        results = []
        
        for pubkey in pubkeys:
            try:
                # 生成并提交退出
                exit_result = self.submit_exit(pubkey, epoch=epoch)
                results.append({
                    'pubkey': pubkey,
                    'status': 'success',
                    **exit_result
                })
            except Exception as e:
                logger.error(f"退出验证者失败 ({pubkey[:10]}...): {e}")
                results.append({
                    'pubkey': pubkey,
                    'status': 'failed',
                    'error': str(e)
                })
        
        logger.info(f"批量退出完成: {len([r for r in results if r['status'] == 'success'])}/{len(pubkeys)} 成功")
        return results
    
    def complete_exit_process(
        self,
        pubkey: str
    ) -> Dict[str, Any]:
        """
        完成退出流程（退出确认后调用）
        
        1. 更新状态为 exited
        2. 从系统中移除密钥
        
        Args:
            pubkey: 验证者公钥
            
        Returns:
            完成结果
        """
        try:
            # 更新状态
            validator_key = self.db.query(ValidatorKey).filter(
                ValidatorKey.pubkey == pubkey.lower()
            ).first()
            
            if not validator_key:
                raise ValueError(f"验证者不存在: {pubkey}")
            
            validator_key.status = ValidatorKeyStatus.EXITED.value
            validator_key.exited_at = datetime.utcnow()
            
            # 移除密钥
            remove_result = self.remove_key_from_system(pubkey)
            
            self.db.commit()
            
            logger.info(f"退出流程完成: {pubkey[:10]}...")
            return {
                'pubkey': pubkey,
                'status': 'exited',
                'removed': remove_result
            }
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"完成退出流程失败: {e}")
            raise DatabaseError(f"完成退出流程失败: {e}")

