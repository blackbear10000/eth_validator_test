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
        从数据库或 Beacon Chain 获取验证者索引
        
        优先从数据库的 DepositTransaction 表中获取（如果已激活），
        否则从 Beacon Chain 查询。
        
        Args:
            pubkey: 验证者公钥
            
        Returns:
            验证者索引或 None
        """
        try:
            # 方法1：优先从数据库获取（如果验证者已激活）
            from app.models.database import DepositTransaction
            deposit_tx = self.db.query(DepositTransaction).filter(
                DepositTransaction.pubkey == pubkey.lower()
            ).order_by(DepositTransaction.submitted_at.desc()).first()
            
            if deposit_tx and deposit_tx.validator_index is not None:
                logger.debug(f"从数据库获取验证者索引: {pubkey[:10]}... -> {deposit_tx.validator_index}")
                return int(deposit_tx.validator_index)
            
            # 方法2：从 Beacon Chain 查询
            validator_data = self.beacon_api.get_validator(pubkey)
            if validator_data:
                # Beacon API 返回格式: {'index': ..., 'status': '...', 'validator': {...}, 'balance': '...'}
                # 或者 {'data': {'index': ..., ...}}
                # 验证者索引在顶层，不在 validator 对象中
                if isinstance(validator_data, dict) and 'data' in validator_data:
                    validator_data = validator_data['data']
                
                # 从顶层获取 index（根据 validator_state_machine.py 的逻辑）
                index = validator_data.get('index')
                if index is not None:
                    logger.debug(f"从 Beacon API 获取验证者索引: {pubkey[:10]}... -> {index}")
                    return int(index)
                
                # 如果顶层没有，尝试从 validator 对象中获取（非标准格式，兼容处理）
                validator_info = validator_data.get('validator', {})
                if not validator_info and validator_data.get('index') is not None:
                    validator_info = validator_data
                
                index = validator_info.get('index')
                if index is not None:
                    logger.debug(f"从 validator 对象获取验证者索引: {pubkey[:10]}... -> {index}")
                    return int(index)
            
            logger.warning(f"无法获取验证者索引: {pubkey[:10]}...")
            return None
        except Exception as e:
            logger.error(f"获取验证者索引失败: {e}", exc_info=True)
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
    
    def check_exit_eligibility(self, pubkey: str) -> Dict[str, Any]:
        """
        检查验证者是否满足退出条件
        
        Args:
            pubkey: 验证者公钥
            
        Returns:
            包含退出资格信息的字典
        """
        try:
            # 获取验证者信息
            validator_data = self.beacon_api.get_validator(pubkey)
            if not validator_data:
                raise ValueError(f"无法获取验证者信息: {pubkey}")
            
            # 处理不同的响应格式
            if isinstance(validator_data, dict) and 'data' in validator_data:
                validator_data = validator_data['data']
            
            validator_info = validator_data.get('validator', {})
            if not validator_info:
                validator_info = validator_data
            
            # 获取当前 epoch（从 finalized checkpoint）
            try:
                state_data = self.beacon_api._get("/eth/v1/beacon/states/finalized/finality_checkpoints")
                if isinstance(state_data, dict) and 'data' in state_data:
                    state_data = state_data['data']
                current_epoch = state_data.get('finalized', {}).get('epoch')
                if current_epoch:
                    current_epoch = int(current_epoch)
                else:
                    current_epoch = None
            except Exception as e:
                logger.warning(f"无法获取当前 epoch: {e}")
                current_epoch = None
            
            # 获取验证者的 activation_epoch 和 exit_epoch
            activation_epoch_raw = validator_info.get('activation_epoch')
            exit_epoch_raw = validator_info.get('exit_epoch')
            
            # 计算 earliest_exit_epoch
            # 根据 Ethereum 规范，验证者必须激活至少 256 epochs 后才能退出
            # earliest_exit_epoch = activation_epoch + 256 (如果已激活)
            # 如果还未激活，则不能退出
            FAR_FUTURE_EPOCH = 18446744073709551615
            
            # 处理 activation_epoch
            activation_epoch = None
            if activation_epoch_raw is not None:
                try:
                    activation_epoch_int = int(activation_epoch_raw)
                    if activation_epoch_int != FAR_FUTURE_EPOCH:
                        activation_epoch = activation_epoch_int
                except (ValueError, TypeError):
                    pass
            
            # 处理 exit_epoch
            exit_epoch = None
            if exit_epoch_raw is not None:
                try:
                    exit_epoch_int = int(exit_epoch_raw)
                    if exit_epoch_int != FAR_FUTURE_EPOCH:
                        exit_epoch = exit_epoch_int
                except (ValueError, TypeError):
                    pass
            
            # 计算 earliest_exit_epoch
            if activation_epoch is not None:
                earliest_exit_epoch = activation_epoch + 256
            else:
                earliest_exit_epoch = None
            
            # 检查是否可以退出
            can_exit = False
            reason = None
            
            # 首先检查是否已退出或正在退出
            if exit_epoch is not None:
                can_exit = False
                reason = f"验证者已退出或正在退出 (exit_epoch: {exit_epoch})"
            elif activation_epoch is None:
                can_exit = False
                reason = "验证者尚未激活"
            elif current_epoch is None:
                can_exit = True  # 无法确定当前 epoch，允许尝试
                reason = "无法确定当前 epoch，将尝试提交"
            elif current_epoch < earliest_exit_epoch:
                can_exit = False
                epochs_remaining = earliest_exit_epoch - current_epoch
                reason = (
                    f"验证者太年轻，还不能退出。"
                    f"当前 epoch: {current_epoch}, "
                    f"最早退出 epoch: {earliest_exit_epoch} (激活于 epoch {activation_epoch} + 256 epochs 等待期), "
                    f"还需要等待约 {epochs_remaining} 个 epochs 才能退出。"
                    f"根据 Ethereum 规范，验证者必须激活至少 256 epochs 后才能退出。"
                )
            else:
                can_exit = True
                reason = f"验证者满足退出条件 (当前 epoch: {current_epoch}, 最早退出 epoch: {earliest_exit_epoch})"
            
            return {
                'can_exit': can_exit,
                'reason': reason,
                'current_epoch': current_epoch,
                'activation_epoch': activation_epoch,
                'earliest_exit_epoch': earliest_exit_epoch,
                'exit_epoch': exit_epoch
            }
            
        except Exception as e:
            logger.error(f"检查退出资格失败: {e}", exc_info=True)
            raise DepositGenerationError(f"检查退出资格失败: {e}")
    
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
            # 检查验证者是否满足退出条件
            eligibility = self.check_exit_eligibility(pubkey)
            if not eligibility['can_exit']:
                error_msg = f"验证者不满足退出条件: {eligibility['reason']}"
                logger.warning(f"{error_msg} (pubkey: {pubkey[:10]}...)")
                raise ValueError(error_msg)
            
            logger.info(f"验证者满足退出条件: {eligibility['reason']} (pubkey: {pubkey[:10]}...)")
            
            # 如果未提供 epoch，使用 earliest_exit_epoch 或当前 epoch
            if epoch is None:
                if eligibility['earliest_exit_epoch']:
                    epoch = eligibility['earliest_exit_epoch']
                elif eligibility['current_epoch']:
                    epoch = eligibility['current_epoch']
                else:
                    # 如果无法确定，使用当前 epoch（从 Beacon API 查询）
                    try:
                        state_data = self.beacon_api._get("/eth/v1/beacon/states/finalized/finality_checkpoints")
                        if isinstance(state_data, dict) and 'data' in state_data:
                            state_data = state_data['data']
                        epoch = int(state_data.get('finalized', {}).get('epoch', 0))
                        logger.info(f"从 Beacon API 获取当前 epoch: {epoch}")
                    except Exception as e:
                        logger.warning(f"无法从 Beacon API 获取当前 epoch: {e}，使用 earliest_exit_epoch")
                        epoch = eligibility['earliest_exit_epoch'] or 0
            
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
                    'exit_data': exit_data,
                    'eligibility': eligibility
                }
            else:
                error_text = response.text
                # 尝试解析错误信息
                try:
                    import json
                    error_json = json.loads(error_text)
                    error_message = error_json.get('message', error_text)
                except:
                    error_message = error_text
                
                raise Exception(f"Beacon API 返回错误: {response.status_code}, {error_message}")
                
        except ValueError:
            # 重新抛出验证错误
            raise
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

