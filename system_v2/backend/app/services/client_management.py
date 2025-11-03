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
            
            # 创建客户端实例
            client_instance = ClientInstance(
                name=name,
                client_type=client_type.value,
                beacon_api_url=beacon_api_url,
                grpc_endpoint=grpc_endpoint,
                web3signer_url=web3signer_url or self.web3signer_client.haproxy_url,
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
                
                # 如果使用 Remote Keymanager API，通过 Web3Signer 加载
                if use_remote_keymanager:
                    # 注意：Remote Keymanager API 需要客户端主动调用，这里只是准备配置
                    logger.info(f"密钥已分配到客户端，配置文件已生成: {client_instance.name}")
            
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

