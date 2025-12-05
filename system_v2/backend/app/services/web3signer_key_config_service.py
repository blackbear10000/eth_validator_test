"""
Web3Signer 密钥配置管理服务
负责管理 Web3Signer 密钥配置文件，确保配置文件与数据库中的密钥状态同步
"""
import logging
import os
import yaml
import requests
from pathlib import Path
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session

from app.models.database import ValidatorKey
from app.models.enums import ValidatorKeyStatus
from app.config import settings

logger = logging.getLogger(__name__)


class Web3SignerKeyConfigService:
    """
    Web3Signer 密钥配置管理服务
    
    负责：
    1. 为所有非 UNUSED 状态的密钥生成 Web3Signer 配置文件
    2. 删除 UNUSED 状态密钥的配置文件
    3. 同步配置文件与数据库状态
    """
    
    def __init__(self, db: Session, keys_dir: Optional[str] = None):
        """
        初始化服务
        
        Args:
            db: 数据库会话
            keys_dir: 密钥配置文件目录（默认使用配置中的路径）
        """
        self.db = db
        
        # 确定密钥配置文件目录
        if keys_dir:
            self.keys_dir = Path(keys_dir)
        else:
            # 优先检查容器内挂载的 /keys 目录（Docker Compose 挂载）
            import os
            container_keys_dir = Path("/keys")
            if container_keys_dir.exists() and container_keys_dir.is_dir():
                self.keys_dir = container_keys_dir
                logger.info(f"使用容器内挂载的 keys 目录: {self.keys_dir}")
            else:
                # 从环境变量或配置中获取
                keys_path = getattr(settings, 'web3signer_keys_dir', None)
                if keys_path:
                    self.keys_dir = Path(keys_path)
                else:
                    # 默认路径（相对于项目根目录）
                    # 假设服务在 backend 目录运行，需要找到 infra/web3signer/keys
                    current_dir = Path(__file__).parent.parent.parent.parent
                    self.keys_dir = current_dir / "infra" / "web3signer" / "keys"
        
        # 确保目录存在
        self.keys_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"Web3Signer 密钥配置目录: {self.keys_dir}")
        
        # 缓存有效的 Vault token
        self._cached_vault_token: Optional[str] = None
    
    def _get_vault_token(self, force_refresh: bool = False) -> str:
        """
        自动获取有效的 Vault token
        
        优先级：
        1. 从 Consul 读取（初始化脚本保存的 root token）
        2. 通过 Vault API 使用 userpass 认证（admin/admin）获取 token
        3. 从环境变量读取
        4. 使用配置的默认值
        
        注意：Web3Signer 的 HashiCorp Vault 配置只支持 token 认证，不支持 userpass。
        但我们可以通过 userpass 登录获取 token，然后将 token 用于 Web3Signer 配置。
        
        Args:
            force_refresh: 是否强制刷新 token（忽略缓存）
        
        Returns:
            有效的 Vault token
        """
        # 如果已缓存且不强制刷新，直接返回
        if self._cached_vault_token and not force_refresh:
            return self._cached_vault_token
        
        # 1. 尝试从 Consul 读取（初始化脚本保存的 root token）
        try:
            consul_addr = os.getenv("CONSUL_ADDR", "consul:8500")
            consul_url = f"http://{consul_addr}/v1/kv/vault/root_token?raw"
            response = requests.get(consul_url, timeout=2)
            if response.status_code == 200:
                token = response.text.strip()
                if token and len(token) > 10:  # 基本验证
                    logger.info("从 Consul 成功获取 Vault root token")
                    self._cached_vault_token = token
                    return token
        except Exception as e:
            logger.debug(f"从 Consul 读取 token 失败: {e}")
        
        # 2. 尝试通过 Vault API 使用 userpass 认证获取 token
        # 注意：Web3Signer 配置文件不支持 userpass，但我们可以用 userpass 登录获取 token
        try:
            vault_url = settings.vault_url
            # 使用 admin/admin 登录获取 token
            login_url = f"{vault_url}/v1/auth/userpass/login/admin"
            login_data = {"password": "admin"}
            response = requests.post(login_url, json=login_data, timeout=2)
            if response.status_code == 200:
                result = response.json()
                token = result.get("auth", {}).get("client_token")
                if token:
                    logger.info("通过 userpass 认证成功获取 Vault token")
                    self._cached_vault_token = token
                    return token
        except Exception as e:
            logger.debug(f"通过 userpass 获取 token 失败: {e}")
        
        # 3. 尝试从环境变量读取
        env_token = os.getenv("VAULT_TOKEN")
        if env_token and env_token != "dev-root-token":  # 排除无效的默认值
            logger.info("使用环境变量中的 Vault token")
            self._cached_vault_token = env_token
            return env_token
        
        # 4. 使用配置的默认值（但可能无效）
        logger.warning(
            f"无法从 Consul、userpass 或环境变量获取有效的 Vault token，"
            f"使用配置的默认值（可能无效）: {settings.vault_token[:10] if len(settings.vault_token) > 10 else settings.vault_token}..."
        )
        return settings.vault_token
    
    def generate_key_config(self, pubkey: str, force_refresh_token: bool = False) -> Dict[str, Any]:
        """
        为单个密钥生成 Web3Signer 配置文件
        
        Args:
            pubkey: 验证者公钥
            force_refresh_token: 是否强制刷新 Vault token
            
        Returns:
            配置文件内容（字典格式）
        """
        # 清理 pubkey（移除 0x 前缀，转为小写）
        pubkey_clean = pubkey.lower().replace('0x', '')
        
        # Vault 路径（与 VaultClient 中的路径格式一致）
        # Web3Signer 期望完整的 API 路径，包括 /v1 前缀
        vault_path = f"/v1/{settings.vault_mount_point}/data/{settings.vault_key_path_prefix}/{pubkey_clean}"
        
        # 获取有效的 Vault token（每次生成配置时都获取最新的 token）
        vault_token = self._get_vault_token(force_refresh=force_refresh_token)
        
        # Web3Signer HashiCorp Vault 配置格式
        config = {
            "type": "hashicorp",
            "keyType": "BLS",
            "tlsEnabled": "false",
            "keyPath": vault_path,
            "keyName": "value",  # Web3Signer 期望的字段名
            "serverHost": "vault-1",  # Docker 网络中的服务名
            "serverPort": "8200",
            "timeout": "10000",
            "token": vault_token
        }
        
        return config
    
    def save_key_config(self, pubkey: str, force_refresh_token: bool = True) -> bool:
        """
        保存密钥配置文件到磁盘
        
        Args:
            pubkey: 验证者公钥
            
        Returns:
            是否成功
        """
        try:
            # 每次保存配置时都获取最新的 token
            config = self.generate_key_config(pubkey, force_refresh_token=force_refresh_token)
            
            # 文件名：使用 pubkey 的前 16 个字符（去除 0x 前缀）
            pubkey_clean = pubkey.lower().replace('0x', '')
            filename = f"vault-{pubkey_clean[:16]}.yaml"
            config_file = self.keys_dir / filename
            
            # 保存 YAML 文件
            # 使用自定义的 Representer 确保所有字符串值都用双引号（符合 Web3Signer 官方文档格式）
            def quoted_str_presenter(dumper, data):
                """自定义字符串表示器，使用双引号"""
                return dumper.represent_scalar('tag:yaml.org,2002:str', data, style='"')
            
            # 创建自定义 Dumper
            class Web3SignerDumper(yaml.SafeDumper):
                pass
            
            Web3SignerDumper.add_representer(str, quoted_str_presenter)
            
            # 确保所有值都是字符串类型（符合 Web3Signer 要求）
            quoted_config = {}
            for key, value in config.items():
                quoted_config[key] = str(value) if value is not None else ""
            
            with open(config_file, 'w') as f:
                yaml.dump(
                    quoted_config,
                    f,
                    Dumper=Web3SignerDumper,
                    default_flow_style=False,
                    sort_keys=False,
                    allow_unicode=True
                )
            
            logger.debug(f"已保存密钥配置文件: {config_file} (pubkey: {pubkey[:10]}...)")
            
            # 验证配置文件中的 token 是否有效（可选，用于调试）
            try:
                vault_url = settings.vault_url
                vault_token = config.get("token")
                if vault_token:
                    test_url = f"{vault_url}/v1/sys/health"
                    headers = {"X-Vault-Token": vault_token}
                    response = requests.get(test_url, headers=headers, timeout=2)
                    if response.status_code != 200:
                        logger.warning(f"配置文件中的 Vault token 可能无效 (pubkey: {pubkey[:10]}...): HTTP {response.status_code}")
            except Exception as e:
                logger.debug(f"验证 Vault token 失败: {e}")
            
            return True
            
        except Exception as e:
            logger.error(f"保存密钥配置文件失败 ({pubkey[:10]}...): {e}", exc_info=True)
            return False
    
    def remove_key_config(self, pubkey: str) -> bool:
        """
        删除密钥配置文件
        
        Args:
            pubkey: 验证者公钥
            
        Returns:
            是否成功（如果文件不存在也返回 True）
        """
        try:
            pubkey_clean = pubkey.lower().replace('0x', '')
            filename = f"vault-{pubkey_clean[:16]}.yaml"
            config_file = self.keys_dir / filename
            
            if config_file.exists():
                config_file.unlink()
                logger.debug(f"已删除密钥配置文件: {config_file} (pubkey: {pubkey[:10]}...)")
            
            return True
            
        except Exception as e:
            logger.error(f"删除密钥配置文件失败 ({pubkey[:10]}...): {e}", exc_info=True)
            return False
    
    def sync_key_configs(self) -> Dict[str, Any]:
        """
        同步所有密钥的配置文件
        
        确保：
        1. 所有非 UNUSED 状态的密钥都有配置文件
        2. 所有 UNUSED 状态的密钥都没有配置文件
        
        Returns:
            同步结果统计
        """
        result = {
            'created': 0,
            'removed': 0,
            'skipped': 0,
            'errors': 0
        }
        
        try:
            # 获取所有密钥
            all_keys = self.db.query(ValidatorKey).all()
            
            # 获取当前配置文件列表
            existing_configs = set()
            for config_file in self.keys_dir.glob("vault-*.yaml"):
                # 从文件名提取 pubkey（简化处理，只记录文件名）
                existing_configs.add(config_file.name)
            
            logger.info(f"开始同步密钥配置文件，共 {len(all_keys)} 个密钥")
            
            # 处理每个密钥
            for key in all_keys:
                pubkey_clean = key.pubkey.lower().replace('0x', '')
                expected_filename = f"vault-{pubkey_clean[:16]}.yaml"
                
                if key.status == ValidatorKeyStatus.UNUSED.value:
                    # UNUSED 状态：应该删除配置文件
                    if expected_filename in existing_configs:
                        if self.remove_key_config(key.pubkey):
                            result['removed'] += 1
                            existing_configs.discard(expected_filename)
                        else:
                            result['errors'] += 1
                    else:
                        result['skipped'] += 1
                else:
                    # 非 UNUSED 状态：应该存在配置文件
                    if expected_filename not in existing_configs:
                        if self.save_key_config(key.pubkey):
                            result['created'] += 1
                            existing_configs.add(expected_filename)
                        else:
                            result['errors'] += 1
                    else:
                        result['skipped'] += 1
            
            logger.info(
                f"密钥配置文件同步完成: 创建 {result['created']} 个，"
                f"删除 {result['removed']} 个，跳过 {result['skipped']} 个，"
                f"错误 {result['errors']} 个"
            )
            
            return result
            
        except Exception as e:
            logger.error(f"同步密钥配置文件失败: {e}", exc_info=True)
            result['errors'] += 1
            return result
    
    def get_all_key_configs(self) -> List[str]:
        """
        获取所有配置文件对应的公钥列表
        
        Returns:
            公钥列表
        """
        pubkeys = []
        
        try:
            for config_file in self.keys_dir.glob("vault-*.yaml"):
                # 读取配置文件获取 pubkey
                try:
                    with open(config_file, 'r') as f:
                        config = yaml.safe_load(f)
                        key_path = config.get('keyPath', '')
                        # 从 keyPath 中提取 pubkey
                        # 格式：/v1/secret/data/web3signer-keys/{pubkey}
                        if '/web3signer-keys/' in key_path:
                            pubkey = key_path.split('/web3signer-keys/')[-1]
                            pubkeys.append(f"0x{pubkey}")
                except Exception as e:
                    logger.warning(f"读取配置文件失败 {config_file}: {e}")
                    continue
            
            return pubkeys
            
        except Exception as e:
            logger.error(f"获取配置文件列表失败: {e}", exc_info=True)
            return []

