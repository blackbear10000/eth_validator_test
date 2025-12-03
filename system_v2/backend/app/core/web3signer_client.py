"""
Web3Signer 客户端
封装 Web3Signer API 调用，支持零停机密钥更新
"""
import logging
from typing import List, Dict, Any, Optional
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from app.config import settings
from app.utils.exceptions import Web3SignerError

logger = logging.getLogger(__name__)


class Web3SignerClient:
    """
    Web3Signer API 客户端
    提供密钥加载、查询、零停机更新等功能
    """
    
    def __init__(
        self,
        primary_url: Optional[str] = None,
        secondary_url: Optional[str] = None,
        haproxy_url: Optional[str] = None
    ):
        """
        初始化 Web3Signer 客户端
        
        Args:
            primary_url: Web3Signer-1 URL
            secondary_url: Web3Signer-2 URL
            haproxy_url: HAProxy URL（用于统一访问）
        """
        self.primary_url = (primary_url or settings.web3signer_url_primary).rstrip('/')
        self.secondary_url = (secondary_url or settings.web3signer_url_secondary).rstrip('/')
        self.haproxy_url = (haproxy_url or settings.web3signer_haproxy_url).rstrip('/')
        
        # 配置重试策略
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        
        self.session = requests.Session()
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)
        self.session.headers.update({
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        })
    
    def _request(
        self,
        method: str,
        endpoint: str,
        url: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        发送 HTTP 请求
        
        Args:
            method: HTTP 方法
            endpoint: API 端点
            url: 目标 URL（如果不提供则使用 haproxy_url）
            **kwargs: 其他请求参数
            
        Returns:
            JSON 响应数据
        """
        base_url = url or self.haproxy_url
        full_url = f"{base_url}{endpoint}"
        
        try:
            response = self.session.request(method, full_url, **kwargs)
            response.raise_for_status()
            
            # 空响应返回空字典
            if not response.text:
                return {}
            
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Web3Signer API 请求失败: {full_url}, {e}")
            raise Web3SignerError(f"Web3Signer API 请求失败: {e}")
    
    def health_check(self, instance: str = "haproxy") -> bool:
        """
        检查 Web3Signer 健康状态
        
        Args:
            instance: 实例名称 (haproxy/primary/secondary)
            
        Returns:
            是否健康
        """
        url_map = {
            "haproxy": self.haproxy_url,
            "primary": self.primary_url,
            "secondary": self.secondary_url
        }
        
        url = url_map.get(instance, self.haproxy_url)
        
        if not url:
            logger.warning(f"Web3Signer {instance} URL 未配置")
            return False
        
        try:
            # 使用独立的 session，不包含额外的 headers，避免干扰健康检查
            # /upcheck 端点是一个简单的健康检查端点，不需要 JSON headers
            health_url = f"{url}/upcheck"
            logger.debug(f"检查 Web3Signer {instance} 健康状态: {health_url}")
            
            # 创建一个简单的请求，不包含额外的 headers
            response = requests.get(health_url, timeout=5)
            
            # Web3Signer 的 /upcheck 端点可能返回 200 或 403
            # 403 通常表示服务在运行但可能有权限限制，我们也认为它是健康的
            # 这与 HAProxy 配置一致：http-check expect status 200,403
            is_healthy = response.status_code in [200, 403]
            
            if not is_healthy:
                logger.warning(f"Web3Signer {instance} 健康检查失败: HTTP {response.status_code}, URL: {health_url}, Response: {response.text[:100]}")
            else:
                logger.info(f"Web3Signer {instance} 健康检查成功: HTTP {response.status_code}, URL: {health_url}")
            
            return is_healthy
        except requests.exceptions.Timeout:
            logger.warning(f"Web3Signer {instance} 健康检查超时: {url}")
            return False
        except requests.exceptions.ConnectionError as e:
            logger.warning(f"Web3Signer {instance} 连接失败: {url}, {e}")
            return False
        except Exception as e:
            logger.error(f"Web3Signer {instance} 健康检查失败: {url}, {e}", exc_info=True)
            return False
    
    def get_public_keys(self, instance: str = "haproxy") -> List[str]:
        """
        获取已加载的公钥列表
        
        Args:
            instance: 实例名称
            
        Returns:
            公钥列表
        """
        url_map = {
            "haproxy": None,  # 使用默认 haproxy_url
            "primary": self.primary_url,
            "secondary": self.secondary_url
        }
        
        url = url_map.get(instance)
        
        try:
            response = self._request("GET", "/api/v1/eth2/publicKeys", url=url)
            data = response.get('data', [])
            
            # 返回公钥列表
            if isinstance(data, list):
                return [item.get('publicKey', '') if isinstance(item, dict) else item for item in data]
            return []
        except Exception as e:
            logger.error(f"获取公钥列表失败: {e}")
            return []
    
    def reload_keys(self, instance: str = "primary") -> bool:
        """
        重新加载密钥（通过 reload-new-keys API）
        
        Args:
            instance: 实例名称 (primary/secondary)
            
        Returns:
            是否成功
        """
        url_map = {
            "primary": self.primary_url,
            "secondary": self.secondary_url
        }
        
        url = url_map.get(instance)
        if not url:
            raise ValueError(f"无效的实例名称: {instance}")
        
        try:
            # Web3Signer reload-new-keys API
            response = self._request("POST", "/reload", url=url)
            logger.info(f"Web3Signer {instance} 密钥重新加载成功")
            return True
        except Exception as e:
            logger.error(f"Web3Signer {instance} 密钥重新加载失败: {e}")
            raise Web3SignerError(f"密钥重新加载失败: {e}")
    
    def zero_downtime_reload(
        self,
        wait_for_health: bool = True,
        health_check_timeout: int = 30
    ) -> Dict[str, Any]:
        """
        零停机密钥更新流程
        
        流程：
        1. Web3Signer-1 继续服务
        2. Web3Signer-2 执行 reload-new-keys，加载新密钥
        3. 检查 Web3Signer-2 健康状态
        4. HAProxy 将流量切换到 Web3Signer-2
        5. Web3Signer-1 执行 reload-new-keys，加载新密钥
        6. 完成轮转
        
        Args:
            wait_for_health: 是否等待健康检查
            health_check_timeout: 健康检查超时时间（秒）
            
        Returns:
            更新结果
        """
        result = {
            'primary': False,
            'secondary': False,
            'success': False
        }
        
        try:
            # 1. 检查初始状态
            if not self.health_check("primary"):
                raise Web3SignerError("Web3Signer-1 不可用")
            
            logger.info("开始零停机密钥更新流程...")
            
            # 2. Web3Signer-2 执行 reload-new-keys
            logger.info("步骤 1: 在 Web3Signer-2 上重新加载密钥...")
            self.reload_keys("secondary")
            
            # 3. 等待 Web3Signer-2 就绪
            if wait_for_health:
                logger.info(f"步骤 2: 等待 Web3Signer-2 健康检查（最多 {health_check_timeout} 秒）...")
                import time
                start_time = time.time()
                while time.time() - start_time < health_check_timeout:
                    if self.health_check("secondary"):
                        logger.info("Web3Signer-2 已就绪")
                        result['secondary'] = True
                        break
                    time.sleep(1)
                else:
                    logger.warning("Web3Signer-2 健康检查超时，但继续流程")
            
            # 4. HAProxy 会自动切换（如果配置了健康检查）
            logger.info("步骤 3: HAProxy 将自动切换到 Web3Signer-2")
            
            # 5. Web3Signer-1 执行 reload-new-keys
            logger.info("步骤 4: 在 Web3Signer-1 上重新加载密钥...")
            self.reload_keys("primary")
            
            if wait_for_health:
                import time
                start_time = time.time()
                while time.time() - start_time < health_check_timeout:
                    if self.health_check("primary"):
                        logger.info("Web3Signer-1 已就绪")
                        result['primary'] = True
                        break
                    time.sleep(1)
            
            result['success'] = True
            logger.info("零停机密钥更新流程完成")
            
            return result
            
        except Exception as e:
            logger.error(f"零停机密钥更新失败: {e}")
            result['error'] = str(e)
            return result
    
    def delete_key(self, pubkey: str, instance: str = "haproxy") -> bool:
        """
        删除密钥（通过 Web3Signer API）
        
        Args:
            pubkey: 验证者公钥
            instance: 实例名称
            
        Returns:
            是否成功
        """
        url_map = {
            "haproxy": None,
            "primary": self.primary_url,
            "secondary": self.secondary_url
        }
        
        url = url_map.get(instance)
        
        try:
            # Web3Signer delete key API
            response = self._request(
                "DELETE",
                f"/api/v1/eth2/publicKeys/{pubkey}",
                url=url
            )
            logger.info(f"密钥已从 Web3Signer 删除: {pubkey[:10]}...")
            return True
        except Exception as e:
            logger.error(f"删除密钥失败: {e}")
            return False

