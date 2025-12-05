"""
客户端管理服务
负责 Validator Client 配置生成、密钥分配、映射表维护
"""
import logging
import json
import os
from datetime import datetime
from typing import List, Dict, Any, Optional
from pathlib import Path
from sqlalchemy.orm import Session

from app.models.database import ClientInstance, ValidatorClientKey, ValidatorKey
from app.models.enums import ValidatorClientType, ValidatorKeyStatus
from app.core.web3signer_client import Web3SignerClient
from app.core.remote_validator_client import RemoteValidatorClient
from app.utils.exceptions import ClientManagementError, DatabaseError

logger = logging.getLogger(__name__)


class ClientManagementService:
    """
    客户端管理服务
    提供 Validator Client 配置生成、密钥分配等功能
    """
    
    def __init__(
        self,
        db: Session,
        web3signer_client: Optional[Web3SignerClient] = None,
        config_base_path: Optional[str] = None
    ):
        """
        初始化客户端管理服务
        
        Args:
            db: 数据库会话
            web3signer_client: Web3Signer 客户端
            config_base_path: 配置文件基础路径
        """
        self.db = db
        self.web3signer_client = web3signer_client or Web3SignerClient()
        self.config_base_path = config_base_path or "configs"
    
    def _get_remote_validator_api_url(self, client_instance: ClientInstance) -> Optional[str]:
        """
        获取 Remote Validator API URL
        
        根据客户端类型和配置推断 Remote Validator API URL：
        - Prysm: 通常使用 Beacon API URL 的同一地址，但端口可能不同（如 7500）
        - Lighthouse: 通常使用 5062 端口（HTTP API）
        - Teku: 通常使用 5051 端口（REST API）
        
        Args:
            client_instance: 客户端实例
            
        Returns:
            Remote Validator API URL 或 None
        """
        if not client_instance.beacon_api_url:
            return None
        
        # 从 beacon_api_url 提取基础 URL（协议 + 主机 + 端口）
        import re
        match = re.match(r'(https?://[^:/]+)(?::(\d+))?', client_instance.beacon_api_url)
        if not match:
            return None
        
        base_url = match.group(1)
        current_port = match.group(2)
        
        # 根据客户端类型确定 Remote Validator API 端口
        if client_instance.client_type == "prysm":
            # Prysm 通常使用 7500 端口（如果 Beacon API 是 3500）
            # 或者使用 Beacon API 的同一端口
            if current_port == "3500":
                return f"{base_url}:7500"
            else:
                # 使用 Beacon API 的同一端口
                return client_instance.beacon_api_url
        elif client_instance.client_type == "lighthouse":
            # Lighthouse 使用 5062 端口（HTTP API）
            return f"{base_url}:5062"
        elif client_instance.client_type == "teku":
            # Teku 使用 5051 端口（REST API）
            return f"{base_url}:5051"
        else:
            # 默认使用 Beacon API URL
            return client_instance.beacon_api_url
    
    def _convert_url_for_container(self, url: Optional[str], url_type: str = "beacon_api") -> Optional[str]:
        """
        将 URL 转换为容器可访问的格式
        
        Args:
            url: 原始 URL
            url_type: URL 类型 ("beacon_api", "web3signer", "grpc")
            
        Returns:
            转换后的 URL
        """
        if not url:
            return None
        
        # 如果已经是容器格式（包含容器名或 host.docker.internal），直接返回
        if 'host.docker.internal' in url or any(container in url for container in ['web3signer-', 'haproxy', 'cl-', 'el-']):
            return url
        
        # 检查是否是 localhost URL
        if 'localhost' in url or '127.0.0.1' in url:
            # 对于 Web3Signer，如果在 Docker 网络中，使用 HAProxy 或容器名
            if url_type == "web3signer":
                # 如果 URL 包含端口 9000-9002，可能是 Web3Signer
                import re
                port_match = re.search(r':(\d+)', url)
                if port_match:
                    port = port_match.group(1)
                    if port in ['9000', '9001']:
                        # 使用容器名
                        instance = 'web3signer-1' if port == '9000' else 'web3signer-2'
                        return url.replace('localhost', instance).replace('127.0.0.1', instance)
                    elif port == '9002':
                        # HAProxy
                        return url.replace('localhost', 'haproxy').replace('127.0.0.1', 'haproxy')
                # 默认使用 HAProxy
                return url.replace('localhost', 'haproxy').replace('127.0.0.1', 'haproxy')
            
            # 对于 Beacon API，尝试从 NetworkService 获取
            elif url_type == "beacon_api":
                try:
                    from app.services.network_service import NetworkService
                    network_service = NetworkService()
                    endpoints = network_service.get_rpc_endpoints()
                    if endpoints.get("beacon_api_url"):
                        logger.info(f"从网络服务获取 Beacon API URL: {endpoints['beacon_api_url']}")
                        return endpoints["beacon_api_url"]
                except Exception as e:
                    logger.warning(f"无法从网络服务获取 Beacon API URL: {e}")
                
                # 如果无法获取，将 localhost 转换为 host.docker.internal
                return url.replace('localhost', 'host.docker.internal').replace('127.0.0.1', 'host.docker.internal')
            
            # 对于其他类型，使用 host.docker.internal
            else:
                return url.replace('localhost', 'host.docker.internal').replace('127.0.0.1', 'host.docker.internal')
        
        # 如果不是 localhost，直接返回
        return url
    
    def create_client_instance(
        self,
        name: str,
        client_type: ValidatorClientType,
        beacon_api_url: Optional[str] = None,
        grpc_endpoint: Optional[str] = None,
        web3signer_url: Optional[str] = None,
        notes: Optional[str] = None
    ) -> ClientInstance:
        """
        创建客户端实例
        
        Args:
            name: 实例名称
            client_type: 客户端类型
            beacon_api_url: Beacon API URL
            grpc_endpoint: gRPC 端点
            web3signer_url: Web3Signer URL
            notes: 备注
            
        Returns:
            ClientInstance 对象
        """
        try:
            # 检查名称是否已存在
            existing = self.db.query(ClientInstance).filter(
                ClientInstance.name == name
            ).first()
            
            if existing:
                raise ValueError(f"客户端实例名称已存在: {name}")
            
            # 转换 URL 为容器可访问的格式
            converted_beacon_api_url = self._convert_url_for_container(beacon_api_url, "beacon_api")
            converted_web3signer_url = self._convert_url_for_container(
                web3signer_url or self.web3signer_client.haproxy_url,
                "web3signer"
            )
            converted_grpc_endpoint = self._convert_url_for_container(grpc_endpoint, "grpc")
            
            # 创建客户端实例
            client_instance = ClientInstance(
                name=name,
                client_type=client_type.value,
                beacon_api_url=converted_beacon_api_url,
                grpc_endpoint=converted_grpc_endpoint,
                web3signer_url=converted_web3signer_url,
                status="stopped",
                is_active=True,
                created_at=datetime.utcnow()
            )
            
            if notes:
                client_instance.notes = notes
            
            self.db.add(client_instance)
            self.db.commit()
            
            logger.info(f"客户端实例已创建: {name} ({client_type.value})")
            return client_instance
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"创建客户端实例失败: {e}")
            raise ClientManagementError(f"创建客户端实例失败: {e}")
    
    def update_client_instance(
        self,
        client_id: int,
        name: Optional[str] = None,
        beacon_api_url: Optional[str] = None,
        grpc_endpoint: Optional[str] = None,
        web3signer_url: Optional[str] = None,
        notes: Optional[str] = None,
        is_active: Optional[bool] = None
    ) -> ClientInstance:
        """
        更新客户端实例
        
        Args:
            client_id: 客户端实例 ID
            name: 实例名称（可选）
            beacon_api_url: Beacon API URL（可选）
            grpc_endpoint: gRPC 端点（可选）
            web3signer_url: Web3Signer URL（可选）
            notes: 备注（可选）
            is_active: 是否活跃（可选）
            
        Returns:
            更新后的 ClientInstance 对象
        """
        try:
            client_instance = self.db.query(ClientInstance).filter(
                ClientInstance.id == client_id
            ).first()
            
            if not client_instance:
                raise ValueError(f"客户端实例不存在: {client_id}")
            
            # 更新名称（如果提供且与现有不同）
            if name is not None and name != client_instance.name:
                # 检查新名称是否已被使用
                existing = self.db.query(ClientInstance).filter(
                    ClientInstance.name == name,
                    ClientInstance.id != client_id
                ).first()
                if existing:
                    raise ValueError(f"客户端实例名称已存在: {name}")
                client_instance.name = name
            
            # 转换并更新 URL
            if beacon_api_url is not None:
                client_instance.beacon_api_url = self._convert_url_for_container(beacon_api_url, "beacon_api")
            if grpc_endpoint is not None:
                client_instance.grpc_endpoint = self._convert_url_for_container(grpc_endpoint, "grpc")
            if web3signer_url is not None:
                client_instance.web3signer_url = self._convert_url_for_container(web3signer_url, "web3signer")
            elif web3signer_url is None and client_instance.web3signer_url is None:
                # 如果没有提供且当前也没有，使用默认值
                client_instance.web3signer_url = self._convert_url_for_container(
                    self.web3signer_client.haproxy_url,
                    "web3signer"
                )
            
            # 更新其他字段
            if notes is not None:
                client_instance.notes = notes
            if is_active is not None:
                client_instance.is_active = is_active
            
            self.db.commit()
            
            logger.info(f"客户端实例已更新: {client_instance.name} (ID: {client_id})")
            return client_instance
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"更新客户端实例失败: {e}")
            raise ClientManagementError(f"更新客户端实例失败: {e}")
    
    def delete_client_instance(self, client_id: int, hard_delete: bool = False) -> bool:
        """
        删除客户端实例
        
        Args:
            client_id: 客户端实例 ID
            hard_delete: 是否硬删除（True：物理删除，False：软删除，设置 is_active=False）
            
        Returns:
            是否成功删除
        """
        try:
            client_instance = self.db.query(ClientInstance).filter(
                ClientInstance.id == client_id
            ).first()
            
            if not client_instance:
                raise ValueError(f"客户端实例不存在: {client_id}")
            
            if hard_delete:
                # 硬删除：物理删除记录（关联的 ValidatorClientKey 会通过 cascade 自动删除）
                self.db.delete(client_instance)
                logger.info(f"客户端实例已硬删除: {client_instance.name} (ID: {client_id})")
            else:
                # 软删除：设置 is_active=False
                client_instance.is_active = False
                client_instance.status = "stopped"
                logger.info(f"客户端实例已软删除: {client_instance.name} (ID: {client_id})")
            
            self.db.commit()
            return True
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"删除客户端实例失败: {e}")
            raise ClientManagementError(f"删除客户端实例失败: {e}")
    
    def generate_config_files(
        self,
        client_instance: ClientInstance,
        pubkeys: List[str]
    ) -> Dict[str, str]:
        """
        生成客户端配置文件
        
        Args:
            client_instance: 客户端实例
            pubkeys: 验证者公钥列表
            
        Returns:
            配置文件路径字典
        """
        configs = {}
        client_dir = Path(self.config_base_path) / client_instance.client_type / client_instance.name
        client_dir.mkdir(parents=True, exist_ok=True)
        
        if client_instance.client_type == "prysm":
            configs.update(self._generate_prysm_config(client_instance, pubkeys, client_dir))
        elif client_instance.client_type == "lighthouse":
            configs.update(self._generate_lighthouse_config(client_instance, pubkeys, client_dir))
        elif client_instance.client_type == "teku":
            configs.update(self._generate_teku_config(client_instance, pubkeys, client_dir))
        
        # 更新配置文件路径
        client_instance.config_path = str(client_dir)
        self.db.commit()
        
        return configs
    
    def _generate_prysm_config(
        self,
        client_instance: ClientInstance,
        pubkeys: List[str],
        config_dir: Path
    ) -> Dict[str, str]:
        """生成 Prysm 配置"""
        # Public Key Persistence 文件
        pubkey_file = config_dir / "pubkey_persistence.json"
        pubkey_data = {
            "pubkeys": pubkeys
        }
        with open(pubkey_file, 'w') as f:
            json.dump(pubkey_data, f, indent=2)
        
        # 主配置文件（YAML 格式，Prysm 使用）
        config_file = config_dir / "config.yaml"
        config = {
            "validator": {
                "wallet-dir": "/wallet",
                "wallet-password-file": "/wallet/password.txt",
                "graffiti": f"prysm-{client_instance.name}"
            },
            "beacon-chain": {
                "rpc-host": client_instance.grpc_endpoint or "localhost:4000",
                "web3-provider": client_instance.beacon_api_url or "http://localhost:5052"
            },
            "slashing-protection-db-url": "postgresql://postgres:password@localhost:5432/web3signer",
            "web3signer-url": client_instance.web3signer_url
        }
        
        import yaml
        with open(config_file, 'w') as f:
            yaml.dump(config, f, default_flow_style=False)
        
        return {
            'config_file': str(config_file),
            'pubkey_persistence_file': str(pubkey_file)
        }
    
    def _generate_lighthouse_config(
        self,
        client_instance: ClientInstance,
        pubkeys: List[str],
        config_dir: Path
    ) -> Dict[str, str]:
        """生成 Lighthouse 配置"""
        # Public Key Persistence 文件
        pubkey_file = config_dir / "pubkey_persistence.json"
        pubkey_data = {
            "pubkeys": pubkeys
        }
        with open(pubkey_file, 'w') as f:
            json.dump(pubkey_data, f, indent=2)
        
        # Lighthouse 使用 TOML 配置
        config_file = config_dir / "config.toml"
        config_content = f"""
[validator_client]
beacon-node = "{client_instance.beacon_api_url or 'http://localhost:5052'}"
wallet = "/wallet"

[http]
address = "0.0.0.0"
port = 5062

[web3signer]
url = "{client_instance.web3signer_url}"
"""
        
        with open(config_file, 'w') as f:
            f.write(config_content)
        
        return {
            'config_file': str(config_file),
            'pubkey_persistence_file': str(pubkey_file)
        }
    
    def _generate_teku_config(
        self,
        client_instance: ClientInstance,
        pubkeys: List[str],
        config_dir: Path
    ) -> Dict[str, str]:
        """生成 Teku 配置"""
        # Public Key Persistence 文件
        pubkey_file = config_dir / "pubkey_persistence.json"
        pubkey_data = {
            "pubkeys": pubkeys
        }
        with open(pubkey_file, 'w') as f:
            json.dump(pubkey_data, f, indent=2)
        
        # Teku 使用 YAML 配置
        config_file = config_dir / "config.yaml"
        config = {
            "beacon": {
                "beacon-rest-api-enabled": True,
                "beacon-rest-api-port": 5051
            },
            "validator-client": {
                "validator-external-signer-url": client_instance.web3signer_url,
                "validator-external-signer-public-keys": pubkeys
            }
        }
        
        import yaml
        with open(config_file, 'w') as f:
            yaml.dump(config, f, default_flow_style=False)
        
        return {
            'config_file': str(config_file),
            'pubkey_persistence_file': str(pubkey_file)
        }
    
    def assign_keys_to_client(
        self,
        client_instance: ClientInstance,
        pubkeys: List[str],
        use_remote_keymanager: bool = True
    ) -> List[ValidatorClientKey]:
        """
        分配密钥到客户端
        
        Args:
            client_instance: 客户端实例
            pubkeys: 验证者公钥列表
            use_remote_keymanager: 是否使用 Remote Keymanager API
            
        Returns:
            创建的映射关系列表
        """
        try:
            assigned_keys = []
            
            for pubkey in pubkeys:
                # 检查密钥是否存在
                validator_key = self.db.query(ValidatorKey).filter(
                    ValidatorKey.pubkey == pubkey.lower()
                ).first()
                
                if not validator_key:
                    logger.warning(f"密钥不存在: {pubkey[:10]}...")
                    continue
                
                # 检查密钥状态：允许已激活、已生成存款数据、已提交到链上的密钥
                allowed_statuses = [
                    ValidatorKeyStatus.ACTIVE.value,
                    ValidatorKeyStatus.DEPOSIT_DATA_GENERATED.value,
                    ValidatorKeyStatus.PENDING.value,  # 已提交存款，等待链上确认
                    ValidatorKeyStatus.DEPOSITED.value,  # 存款已确认，在 deposit queue 中
                    ValidatorKeyStatus.ACTIVE_ON_CHAIN.value  # 链上激活，正在验证
                ]
                if validator_key.status not in allowed_statuses:
                    logger.warning(
                        f"密钥状态不允许加载到客户端: {pubkey[:10]}... "
                        f"(状态: {validator_key.status}, 允许的状态: {allowed_statuses})"
                    )
                    continue
                
                # 检查是否已分配
                existing = self.db.query(ValidatorClientKey).filter(
                    ValidatorClientKey.client_id == client_instance.id,
                    ValidatorClientKey.pubkey == pubkey.lower(),
                    ValidatorClientKey.status == "active"
                ).first()
                
                if existing:
                    logger.debug(f"密钥已分配: {pubkey[:10]}...")
                    continue
                
                # 创建映射关系
                client_key = ValidatorClientKey(
                    client_id=client_instance.id,
                    pubkey=validator_key.pubkey,
                    status="active",
                    added_at=datetime.utcnow()
                )
                self.db.add(client_key)
                assigned_keys.append(client_key)
            
            self.db.commit()
            
            # 生成配置文件
            if assigned_keys:
                pubkey_list = [ck.pubkey for ck in assigned_keys]
                self.generate_config_files(client_instance, pubkey_list)
                
                # 检查是否有 ACTIVE 状态的密钥需要加载到 Web3Signer
                active_pubkeys = [
                    ck.pubkey for ck in assigned_keys
                    if self.db.query(ValidatorKey).filter(
                        ValidatorKey.pubkey == ck.pubkey,
                        ValidatorKey.status == ValidatorKeyStatus.ACTIVE.value
                    ).first()
                ]
                
                # 如果有 ACTIVE 状态的密钥，确保 Web3Signer 已加载
                if active_pubkeys:
                    try:
                        logger.info(f"触发 Web3Signer 重新加载密钥（分配了 {len(active_pubkeys)} 个 ACTIVE 密钥）...")
                        reload_result = self.web3signer_client.zero_downtime_reload(wait_for_health=True)
                        if reload_result.get('success'):
                            logger.info(f"Web3Signer 密钥重新加载成功，已分配的 ACTIVE 密钥已自动加载")
                        else:
                            logger.warning(f"Web3Signer 密钥重新加载可能失败: {reload_result.get('error')}")
                    except Exception as e:
                        logger.warning(f"自动加载密钥到 Web3Signer 失败: {e}，密钥已分配但需要手动触发 Web3Signer 重新加载")
                
                # 如果使用 Remote Validator API，动态添加密钥到 Validator Client
                if use_remote_keymanager:
                    try:
                        self.sync_keys_to_validator_client(
                            client_instance,
                            add_pubkeys=pubkey_list
                        )
                        logger.info(f"密钥已通过 Remote Validator API 添加到客户端: {client_instance.name}")
                    except Exception as e:
                        logger.warning(f"通过 Remote Validator API 添加密钥失败: {e}，但密钥已分配到客户端")
            
            logger.info(f"成功分配 {len(assigned_keys)} 个密钥到客户端: {client_instance.name}")
            return assigned_keys
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"分配密钥失败: {e}")
            raise ClientManagementError(f"分配密钥失败: {e}")
    
    def remove_keys_from_client(
        self,
        client_instance: ClientInstance,
        pubkeys: List[str]
    ) -> int:
        """
        从客户端移除密钥
        
        Args:
            client_instance: 客户端实例
            pubkeys: 验证者公钥列表
            
        Returns:
            移除的密钥数量
        """
        try:
            removed_count = 0
            
            for pubkey in pubkeys:
                client_key = self.db.query(ValidatorClientKey).filter(
                    ValidatorClientKey.client_id == client_instance.id,
                    ValidatorClientKey.pubkey == pubkey.lower(),
                    ValidatorClientKey.status == "active"
                ).first()
                
                if client_key:
                    client_key.status = "removed"
                    client_key.removed_at = datetime.utcnow()
                    removed_count += 1
            
            self.db.commit()
            
            # 重新生成配置文件（排除已移除的密钥）
            active_keys = self.db.query(ValidatorClientKey).filter(
                ValidatorClientKey.client_id == client_instance.id,
                ValidatorClientKey.status == "active"
            ).all()
            
            if active_keys:
                pubkey_list = [ck.pubkey for ck in active_keys]
                self.generate_config_files(client_instance, pubkey_list)
            
            # 通过 Remote Validator API 删除密钥
            if removed_count > 0:
                try:
                    self.sync_keys_to_validator_client(
                        client_instance,
                        remove_pubkeys=pubkeys
                    )
                    logger.info(f"密钥已通过 Remote Validator API 从客户端删除: {client_instance.name}")
                except Exception as e:
                    logger.warning(f"通过 Remote Validator API 删除密钥失败: {e}，但密钥已从客户端移除")
            
            logger.info(f"成功从客户端移除 {removed_count} 个密钥: {client_instance.name}")
            return removed_count
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"移除密钥失败: {e}")
            raise ClientManagementError(f"移除密钥失败: {e}")
    
    def get_client_keys(
        self,
        client_instance: ClientInstance
    ) -> List[ValidatorKey]:
        """
        获取客户端关联的密钥列表
        
        Args:
            client_instance: 客户端实例
            
        Returns:
            密钥列表
        """
        client_keys = self.db.query(ValidatorClientKey).filter(
            ValidatorClientKey.client_id == client_instance.id,
            ValidatorClientKey.status == "active"
        ).all()
        
        pubkeys = [ck.pubkey for ck in client_keys]
        
        if not pubkeys:
            return []
        
        validator_keys = self.db.query(ValidatorKey).filter(
            ValidatorKey.pubkey.in_(pubkeys)
        ).all()
        
        return validator_keys
    
    def list_clients(
        self,
        client_type: Optional[str] = None,
        is_active: Optional[bool] = None
    ) -> List[ClientInstance]:
        """
        列出客户端实例
        
        Args:
            client_type: 客户端类型筛选（可选）
            is_active: 是否活跃筛选（可选）
            
        Returns:
            客户端实例列表
        """
        query = self.db.query(ClientInstance)
        
        if client_type:
            query = query.filter(ClientInstance.client_type == client_type)
        if is_active is not None:
            query = query.filter(ClientInstance.is_active == is_active)
        
            query = query.order_by(ClientInstance.created_at.desc())
        
        return query.all()
    
    def sync_keys_to_validator_client(
        self,
        client_instance: ClientInstance,
        add_pubkeys: Optional[List[str]] = None,
        remove_pubkeys: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        通过 Remote Validator API 同步密钥到 Validator Client
        
        Args:
            client_instance: 客户端实例
            add_pubkeys: 要添加的公钥列表（可选）
            remove_pubkeys: 要删除的公钥列表（可选）
            
        Returns:
            同步结果
        """
        result = {
            'added': [],
            'removed': [],
            'errors': []
        }
        
        try:
            # 获取 Remote Validator API URL
            remote_api_url = self._get_remote_validator_api_url(client_instance)
            if not remote_api_url:
                raise ClientManagementError(
                    f"无法确定 Remote Validator API URL（需要配置 beacon_api_url）"
                )
            
            # 创建 Remote Validator API 客户端
            remote_client = RemoteValidatorClient(remote_api_url)
            
            # 添加密钥
            if add_pubkeys:
                try:
                    add_result = remote_client.add_keystores(
                        pubkeys=add_pubkeys,
                        web3signer_url=client_instance.web3signer_url
                    )
                    result['added'] = add_result.get('imported', [])
                    if add_result.get('error'):
                        result['errors'].extend(add_result['error'])
                    logger.info(f"通过 Remote Validator API 添加了 {len(result['added'])} 个密钥")
                except Exception as e:
                    error_msg = f"添加密钥失败: {e}"
                    logger.error(error_msg)
                    result['errors'].append({'action': 'add', 'error': error_msg})
            
            # 删除密钥
            if remove_pubkeys:
                try:
                    remove_result = remote_client.delete_keystores(pubkeys=remove_pubkeys)
                    result['removed'] = remove_result.get('deleted', [])
                    if remove_result.get('error'):
                        result['errors'].extend(remove_result['error'])
                    logger.info(f"通过 Remote Validator API 删除了 {len(result['removed'])} 个密钥")
                except Exception as e:
                    error_msg = f"删除密钥失败: {e}"
                    logger.error(error_msg)
                    result['errors'].append({'action': 'remove', 'error': error_msg})
            
            return result
            
        except Exception as e:
            logger.error(f"同步密钥到 Validator Client 失败: {e}")
            raise ClientManagementError(f"同步密钥失败: {e}")
    
    def sync_client_keys_to_validator_client(
        self,
        client_instance: ClientInstance
    ) -> Dict[str, Any]:
        """
        将分配给该客户端的密钥同步到 Validator Client（通过 Remote Validator API）
        
        Args:
            client_instance: 客户端实例
            
        Returns:
            同步结果
        """
        try:
            # 获取分配给该客户端的密钥（通过 ValidatorClientKey 表）
            client_keys = self.db.query(ValidatorClientKey).filter(
                ValidatorClientKey.client_id == client_instance.id,
                ValidatorClientKey.status == "active"
            ).all()
            
            if not client_keys:
                logger.info(f"客户端 {client_instance.name} 没有分配的密钥")
                return {
                    'added': [],
                    'removed': [],
                    'errors': []
                }
            
            # 获取这些密钥对应的 ValidatorKey，只包含 ACTIVE 和 DEPOSIT_DATA_GENERATED 状态
            pubkeys = [ck.pubkey for ck in client_keys]
            validator_keys = self.db.query(ValidatorKey).filter(
                ValidatorKey.pubkey.in_(pubkeys),
                ValidatorKey.status.in_([
                    ValidatorKeyStatus.ACTIVE.value,
                    ValidatorKeyStatus.DEPOSIT_DATA_GENERATED.value
                ])
            ).all()
            
            target_pubkeys = [key.pubkey for key in validator_keys]
            
            if not target_pubkeys:
                logger.info(f"客户端 {client_instance.name} 没有需要同步的密钥（ACTIVE 或 DEPOSIT_DATA_GENERATED 状态）")
                return {
                    'added': [],
                    'removed': [],
                    'errors': []
                }
            
            # 获取 Remote Validator API URL
            remote_api_url = self._get_remote_validator_api_url(client_instance)
            if not remote_api_url:
                raise ClientManagementError(
                    f"无法确定 Remote Validator API URL（需要配置 beacon_api_url）"
                )
            
            # 创建 Remote Validator API 客户端
            remote_client = RemoteValidatorClient(remote_api_url)
            
            # 获取当前已加载的密钥
            try:
                current_pubkeys = set(remote_client.get_public_keys())
            except Exception as e:
                logger.warning(f"无法获取当前已加载的密钥: {e}，将尝试添加所有密钥")
                current_pubkeys = set()
            
            # 计算需要添加和删除的密钥
            target_pubkeys_set = set(target_pubkeys)
            to_add = list(target_pubkeys_set - current_pubkeys)
            to_remove = list(current_pubkeys - target_pubkeys_set)
            
            result = {
                'added': [],
                'removed': [],
                'errors': []
            }
            
            # 添加新密钥
            if to_add:
                try:
                    add_result = remote_client.add_keystores(
                        pubkeys=to_add,
                        web3signer_url=client_instance.web3signer_url
                    )
                    result['added'] = add_result.get('imported', [])
                    if add_result.get('error'):
                        result['errors'].extend(add_result['error'])
                except Exception as e:
                    error_msg = f"添加密钥失败: {e}"
                    logger.error(error_msg)
                    result['errors'].append({'action': 'add', 'error': error_msg})
            
            # 删除不需要的密钥
            if to_remove:
                try:
                    remove_result = remote_client.delete_keystores(pubkeys=to_remove)
                    result['removed'] = remove_result.get('deleted', [])
                    if remove_result.get('error'):
                        result['errors'].extend(remove_result['error'])
                except Exception as e:
                    error_msg = f"删除密钥失败: {e}"
                    logger.error(error_msg)
                    result['errors'].append({'action': 'remove', 'error': error_msg})
            
            logger.info(
                f"同步完成: 添加 {len(result['added'])}, 删除 {len(result['removed'])}, "
                f"错误 {len(result['errors'])}"
            )
            
            return result
            
        except Exception as e:
            logger.error(f"同步所有密钥失败: {e}")
            raise ClientManagementError(f"同步所有密钥失败: {e}")
    
    def rolling_update_keys(
        self,
        client_instances: List[ClientInstance],
        add_pubkeys: Optional[List[str]] = None,
        remove_pubkeys: Optional[List[str]] = None,
        wait_for_health: bool = True,
        health_check_timeout: int = 30
    ) -> Dict[str, Any]:
        """
        滚动更新多个 Validator Client 实例的密钥列表（零停机更新）
        
        流程：
        1. 更新第一个实例
        2. 等待健康检查
        3. 更新第二个实例
        4. 继续更新剩余实例
        
        Args:
            client_instances: 客户端实例列表
            add_pubkeys: 要添加的公钥列表（可选）
            remove_pubkeys: 要删除的公钥列表（可选）
            wait_for_health: 是否等待健康检查
            health_check_timeout: 健康检查超时时间（秒）
            
        Returns:
            更新结果
        """
        result = {
            'instances': {},
            'success': True,
            'errors': []
        }
        
        if not client_instances:
            logger.warning("没有需要更新的客户端实例")
            return result
        
        import time
        
        for i, client_instance in enumerate(client_instances):
            instance_key = f"{client_instance.name}_{client_instance.id}"
            instance_result = {
                'added': [],
                'removed': [],
                'errors': []
            }
            
            try:
                logger.info(f"更新客户端实例 {i+1}/{len(client_instances)}: {client_instance.name}")
                
                # 同步密钥
                sync_result = self.sync_keys_to_validator_client(
                    client_instance,
                    add_pubkeys=add_pubkeys,
                    remove_pubkeys=remove_pubkeys
                )
                
                instance_result['added'] = sync_result.get('added', [])
                instance_result['removed'] = sync_result.get('removed', [])
                instance_result['errors'] = sync_result.get('errors', [])
                
                # 等待健康检查（如果不是最后一个实例）
                if wait_for_health and i < len(client_instances) - 1:
                    logger.info(f"等待客户端实例健康检查: {client_instance.name}")
                    remote_api_url = self._get_remote_validator_api_url(client_instance)
                    if remote_api_url:
                        remote_client = RemoteValidatorClient(remote_api_url)
                        start_time = time.time()
                        while time.time() - start_time < health_check_timeout:
                            if remote_client.health_check():
                                logger.info(f"客户端实例 {client_instance.name} 健康检查通过")
                                break
                            time.sleep(1)
                        else:
                            logger.warning(f"客户端实例 {client_instance.name} 健康检查超时")
                
                result['instances'][instance_key] = instance_result
                logger.info(f"客户端实例 {client_instance.name} 更新完成")
                
            except Exception as e:
                error_msg = f"更新客户端实例 {client_instance.name} 失败: {e}"
                logger.error(error_msg)
                instance_result['errors'].append({'error': error_msg})
                result['instances'][instance_key] = instance_result
                result['errors'].append(error_msg)
                result['success'] = False
        
        if result['success']:
            logger.info(f"滚动更新完成: {len(client_instances)} 个实例")
        else:
            logger.warning(f"滚动更新部分失败: {len(result['errors'])} 个错误")
        
        return result

