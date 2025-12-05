"""
Vault 客户端封装
负责与 Hashicorp Vault 的交互，存储和读取验证者私钥
私钥存储格式兼容 Web3Signer
"""
import logging
import os
from typing import Optional
import hvac
from hvac.exceptions import VaultError
import requests

from app.config import settings

logger = logging.getLogger(__name__)


class VaultClient:
    """
    Vault 客户端封装类
    提供私钥存储和读取功能，使用 Web3Signer 兼容格式
    """
    
    def __init__(
        self,
        vault_url: Optional[str] = None,
        vault_token: Optional[str] = None,
        mount_point: Optional[str] = None
    ):
        """
        初始化 Vault 客户端
        
        Args:
            vault_url: Vault 服务 URL
            vault_token: Vault 认证 Token
            mount_point: KV Secret Engine 挂载点
        """
        self.vault_url = vault_url or settings.vault_url
        self.vault_token = vault_token or settings.vault_token
        self.mount_point = mount_point or settings.vault_mount_point
        self.key_path_prefix = settings.vault_key_path_prefix
        
        # 初始化 Vault 客户端
        self.client = hvac.Client(url=self.vault_url, token=self.vault_token)
        
        # 验证连接和认证，如果失败则尝试从 Consul 读取 token
        try:
            self._ensure_authenticated()
        except ConnectionError:
            # 尝试从 Consul 读取 token
            consul_token = self._get_token_from_consul()
            if consul_token:
                logger.info("从 Consul 读取到新的 Vault token，更新客户端")
                self.vault_token = consul_token
                self.client = hvac.Client(url=self.vault_url, token=self.vault_token)
                self._ensure_authenticated()
            else:
                raise
        
        # 确保 KV v2 引擎已启用
        self._ensure_kv_engine()
    
    def _get_token_from_consul(self) -> Optional[str]:
        """
        从 Consul KV store 读取 Vault root token
        
        Returns:
            Vault token 或 None
        """
        try:
            # Consul 地址（从环境变量或默认值）
            consul_addr = os.getenv("CONSUL_ADDR", "consul:8500")
            consul_url = f"http://{consul_addr}/v1/kv/vault/root_token"
            
            response = requests.get(consul_url, timeout=5)
            if response.status_code == 200:
                import base64
                import json
                data = response.json()
                if data and len(data) > 0:
                    # Consul KV API 返回 base64 编码的值
                    token_b64 = data[0].get('Value', '')
                    if token_b64:
                        token = base64.b64decode(token_b64).decode('utf-8')
                        logger.info("成功从 Consul 读取 Vault token")
                        return token.strip()
        except Exception as e:
            logger.debug(f"从 Consul 读取 token 失败（这是正常的，如果 Consul 不可用）: {e}")
        
        return None
    
    def _ensure_authenticated(self) -> None:
        """确保 Vault 客户端已认证"""
        if not self.client.is_authenticated():
            raise ConnectionError(
                f"Vault 认证失败。请检查 VAULT_TOKEN 或启动 Vault 服务: {self.vault_url}"
            )
        logger.debug(f"Vault 认证成功: {self.vault_url}")
    
    def _ensure_kv_engine(self) -> None:
        """确保 KV v2 引擎已启用"""
        try:
            mounts = self.client.sys.list_mounted_secrets_engines()
            mount_path = f"{self.mount_point}/"
            
            if mount_path not in mounts:
                logger.info(f"启用 KV v2 引擎: {self.mount_point}")
                self.client.sys.enable_secrets_engine(
                    backend_type='kv',
                    path=self.mount_point,
                    options={'version': '2'}
                )
                logger.info(f"KV v2 引擎已启用: {self.mount_point}")
            else:
                logger.debug(f"KV v2 引擎已存在: {self.mount_point}")
        except VaultError as e:
            logger.warning(f"KV v2 引擎检查失败，可能已存在: {e}")
            # 继续执行，引擎可能已经存在
    
    def _get_key_path(self, pubkey: str) -> str:
        """
        获取密钥在 Vault 中的存储路径
        
        Args:
            pubkey: 验证者公钥（带或不带 0x 前缀）
            
        Returns:
            相对于 mount_point 的路径（不包含 mount_point 和 data/ 前缀）
            
        注意：
            - 对于 KV v2，create_or_update_secret 的 path 参数应该是相对于 mount_point 的路径
            - KV v2 会自动添加 data/ 前缀，所以 path 不应该包含 data/
            - 实际存储路径会是：{mount_point}/data/{path}
            - Web3Signer 访问路径应该是：/v1/{mount_point}/data/{path}
        """
        # 移除 0x 前缀（如果存在）
        pubkey_clean = pubkey.lower().replace('0x', '')
        
        # 返回相对于 mount_point 的路径（不包含 mount_point 和 data/）
        # 实际存储路径：secret/data/web3signer-keys/{pubkey}
        # Web3Signer 访问路径：/v1/secret/data/web3signer-keys/{pubkey}
        return f"{self.key_path_prefix}/{pubkey_clean}"
    
    def store_signing_key(
        self,
        pubkey: str,
        signing_private_key: str,
        metadata: Optional[dict] = None
    ) -> bool:
        """
        存储验证者签名私钥到 Vault
        
        存储格式（Web3Signer 兼容）：
        {
            "value": "<signing_private_key_hex>"  // 不含 0x 前缀
        }
        
        Args:
            pubkey: 验证者公钥（用于路径标识）
            signing_private_key: 签名私钥（十六进制字符串，可带或不带 0x 前缀）
            metadata: 可选元数据
            
        Returns:
            是否成功
        """
        try:
            # 清理私钥格式（移除 0x 前缀，转为小写）
            signing_key_clean = signing_private_key.lower().replace('0x', '')
            
            # 准备存储数据（Web3Signer 兼容格式）
            secret_data = {
                "value": signing_key_clean
            }
            
            # 添加元数据（如果有）
            if metadata:
                secret_data.update(metadata)
            
            # 存储到 Vault
            key_path = self._get_key_path(pubkey)
            self.client.secrets.kv.v2.create_or_update_secret(
                path=key_path,
                secret=secret_data,
                mount_point=self.mount_point
            )
            
            logger.info(f"私钥已存储到 Vault: {pubkey[:10]}...")
            return True
            
        except VaultError as e:
            logger.error(f"存储私钥失败 ({pubkey[:10]}...): {e}")
            raise
    
    def get_signing_key(self, pubkey: str) -> Optional[str]:
        """
        从 Vault 读取验证者签名私钥
        
        Args:
            pubkey: 验证者公钥
            
        Returns:
            签名私钥（十六进制字符串，不含 0x 前缀），如果不存在则返回 None
        """
        try:
            key_path = self._get_key_path(pubkey)
            response = self.client.secrets.kv.v2.read_secret_version(
                path=key_path,
                mount_point=self.mount_point
            )
            
            if response and 'data' in response and 'data' in response['data']:
                secret_data = response['data']['data']
                signing_key = secret_data.get('value')
                
                if signing_key:
                    logger.debug(f"私钥已读取: {pubkey[:10]}...")
                    return signing_key
            
            logger.warning(f"私钥不存在: {pubkey[:10]}...")
            return None
            
        except VaultError as e:
            # 如果是 404 错误，说明密钥不存在
            if 'not found' in str(e).lower() or '404' in str(e):
                logger.debug(f"私钥不存在: {pubkey[:10]}...")
                return None
            logger.error(f"读取私钥失败 ({pubkey[:10]}...): {e}")
            raise
    
    def delete_signing_key(self, pubkey: str) -> bool:
        """
        从 Vault 删除验证者私钥
        
        Args:
            pubkey: 验证者公钥
            
        Returns:
            是否成功
        """
        try:
            key_path = self._get_key_path(pubkey)
            self.client.secrets.kv.v2.delete_metadata_and_all_versions(
                path=key_path,
                mount_point=self.mount_point
            )
            
            logger.info(f"私钥已删除: {pubkey[:10]}...")
            return True
            
        except VaultError as e:
            # 如果是 404 错误，说明密钥已不存在
            if 'not found' in str(e).lower() or '404' in str(e):
                logger.debug(f"私钥已不存在: {pubkey[:10]}...")
                return True
            logger.error(f"删除私钥失败 ({pubkey[:10]}...): {e}")
            raise
    
    def key_exists(self, pubkey: str) -> bool:
        """
        检查密钥是否存在于 Vault 中
        
        Args:
            pubkey: 验证者公钥
            
        Returns:
            是否存在
        """
        signing_key = self.get_signing_key(pubkey)
        return signing_key is not None
    
    def health_check(self) -> bool:
        """
        检查 Vault 服务健康状态
        
        注意：这个方法不需要认证，直接调用 Vault 的健康检查端点
        
        Returns:
            是否健康
        """
        try:
            # 直接使用 requests 调用健康检查端点（更可靠）
            # /v1/sys/health 是一个不需要认证的端点
            health_url = f"{self.vault_url.rstrip('/')}/v1/sys/health"
            response = requests.get(health_url, timeout=5)
            response.raise_for_status()
            
            # 解析 JSON 响应
            health = response.json()
            
            initialized = health.get('initialized', False)
            sealed = health.get('sealed', True)
            
            # Vault 必须已初始化且未密封
            is_healthy = initialized and not sealed
            
            if not is_healthy:
                logger.warning(f"Vault 健康检查失败: initialized={initialized}, sealed={sealed}")
            else:
                logger.debug(f"Vault 健康检查成功: initialized={initialized}, sealed={sealed}")
            
            return is_healthy
        except requests.exceptions.RequestException as e:
            logger.error(f"Vault 健康检查请求失败: {e}")
            return False
        except Exception as e:
            logger.error(f"Vault 健康检查失败: {e}", exc_info=True)
            return False

