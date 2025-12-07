"""
Remote Validator API 客户端
用于与 Validator Client（Prysm、Lighthouse、Teku）的 Remote Validator API 交互
支持动态增减 validator keys，实现不停机更新
"""
import logging
from typing import List, Dict, Any, Optional
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from app.utils.exceptions import RemoteValidatorAPIError

logger = logging.getLogger(__name__)


class RemoteValidatorClient:
    """
    Remote Validator API 客户端
    封装标准 Remote Validator API 调用，支持动态密钥管理
    """
    
    def __init__(self, base_url: str, auth_token: Optional[str] = None):
        """
        初始化 Remote Validator API 客户端
        
        Args:
            base_url: Validator Client 的 Remote Validator API 基础 URL
                      例如: http://localhost:7500 (Prysm), http://localhost:5062 (Lighthouse)
            auth_token: 认证 token（Bearer token），如果提供则添加到请求头
                       根据 Prysm 文档，JWT token 在 auth-token 文件的第二行
        """
        self.base_url = base_url.rstrip('/')
        
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
        
        # 如果提供了 auth_token，添加到请求头（根据 Prysm 文档格式）
        if auth_token:
            self.session.headers.update({
                'Authorization': f'Bearer {auth_token}'
            })
            logger.debug("已添加 Authorization Bearer token 到请求头")
    
    def _request(
        self,
        method: str,
        endpoint: str,
        **kwargs
    ) -> Dict[str, Any]:
        """
        发送 HTTP 请求
        
        Args:
            method: HTTP 方法
            endpoint: API 端点
            **kwargs: 其他请求参数
            
        Returns:
            JSON 响应数据
        """
        url = f"{self.base_url}{endpoint}"
        
        try:
            response = self.session.request(method, url, timeout=10, **kwargs)
            response.raise_for_status()
            
            # 空响应返回空字典
            if not response.text:
                return {}
            
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Remote Validator API 请求失败: {url}, {e}")
            raise RemoteValidatorAPIError(f"Remote Validator API 请求失败: {e}")
    
    def get_keystores(self) -> List[Dict[str, Any]]:
        """
        获取所有已加载的密钥列表（使用 Remote Key Manager API）
        
        根据 Ethereum Remote Key Manager API 规范：
        https://ethereum.github.io/keymanager-APIs/#/Remote%20Key%20Manager/listRemoteKeys
        
        使用 Web3Signer 时，应使用 /eth/v1/remotekeys 端点，而不是 /eth/v1/keystores
        
        Returns:
            密钥列表，每个密钥包含 pubkey 等信息
        """
        try:
            # 使用 Remote Key Manager API 端点（符合标准规范）
            response = self._request("GET", "/eth/v1/remotekeys")
            
            # 处理不同的响应格式
            # Remote Key Manager API 标准格式: {"data": {"remote_keys": [...]}}
            # 每个 remote_key 包含: {"pubkey": "0x...", "url": "http://..."}
            # 某些实现可能直接返回列表: [...]
            if isinstance(response, list):
                # 如果响应直接是列表，直接返回
                logger.debug(f"API 响应是列表格式，包含 {len(response)} 个密钥")
                return response
            elif isinstance(response, dict):
                # 标准格式，从 data.remote_keys 获取（Remote Key Manager API）
                data = response.get('data', {})
                if isinstance(data, list):
                    # 某些实现可能 data 直接是列表
                    logger.debug(f"API 响应 data 是列表格式，包含 {len(data)} 个密钥")
                    return data
                else:
                    # 优先尝试 Remote Key Manager API 格式
                    remote_keys = data.get('remote_keys', [])
                    if remote_keys:
                        logger.debug(f"API 响应包含 {len(remote_keys)} 个远程密钥")
                        return remote_keys
                    # 回退到标准 keystores 格式（兼容性）
                    keystores = data.get('keystores', [])
                    logger.debug(f"API 响应包含 {len(keystores)} 个密钥")
                    return keystores
            else:
                logger.warning(f"意外的响应格式: {type(response)}")
                return []
        except RemoteValidatorAPIError:
            raise
        except Exception as e:
            logger.error(f"获取密钥列表失败: {e}", exc_info=True)
            raise RemoteValidatorAPIError(f"获取密钥列表失败: {e}")
    
    def get_public_keys(self) -> List[str]:
        """
        获取所有已加载的公钥列表
        
        Returns:
            公钥列表（带 0x 前缀）
        """
        keystores = self.get_keystores()
        pubkeys = []
        
        for keystore in keystores:
            # 处理不同的 keystore 格式
            # Remote Key Manager API 格式: {"pubkey": "0x...", "url": "http://..."}
            # 标准格式: {"validating_pubkey": "0x..."}
            # 某些实现可能直接返回字符串列表: ["0x...", ...]
            if isinstance(keystore, dict):
                # 优先使用 Remote Key Manager API 格式
                pubkey = keystore.get('pubkey', '') or keystore.get('validating_pubkey', '')
            elif isinstance(keystore, str):
                # 如果 keystore 直接是字符串（公钥），直接使用
                pubkey = keystore
            else:
                logger.warning(f"意外的 keystore 格式: {type(keystore)}, 值: {keystore}")
                continue
            
            if pubkey:
                # 确保有 0x 前缀
                if not pubkey.startswith('0x'):
                    pubkey = f"0x{pubkey}"
                pubkeys.append(pubkey.lower())
        
        return pubkeys
    
    def add_keystores(
        self,
        pubkeys: List[str],
        web3signer_url: str
    ) -> Dict[str, Any]:
        """
        添加密钥到 Validator Client（使用 Remote Key Manager API）
        
        根据 Ethereum Remote Key Manager API 规范：
        https://ethereum.github.io/keymanager-APIs/#/Remote%20Key%20Manager/importRemoteKeys
        
        使用 Web3Signer 时，应使用 /eth/v1/remotekeys 端点，而不是 /eth/v1/keystores
        
        Args:
            pubkeys: 要添加的公钥列表
            web3signer_url: Web3Signer URL（用于签名）
            
        Returns:
            添加结果，包含成功和失败的密钥
        """
        try:
            # 规范化 Web3Signer URL
            # 在容器间通信时，应该使用容器名称（haproxy），而不是 host.docker.internal
            web3signer_url_normalized = web3signer_url
            if 'host.docker.internal:9002' in web3signer_url:
                # 将 host.docker.internal:9002 转换为 haproxy:9002（容器间通信）
                web3signer_url_normalized = web3signer_url.replace('host.docker.internal:9002', 'haproxy:9002')
                logger.debug(f"Web3Signer URL 已转换: {web3signer_url} -> {web3signer_url_normalized}")
            
            # 准备请求数据（符合 Remote Key Manager API 规范）
            remote_keys = []
            for pubkey in pubkeys:
                # 规范化 pubkey
                pubkey_normalized = pubkey.lower().strip()
                if not pubkey_normalized.startswith('0x'):
                    pubkey_normalized = f"0x{pubkey_normalized}"
                
                remote_keys.append({
                    "pubkey": pubkey_normalized,
                    "url": web3signer_url_normalized  # Web3Signer URL（已规范化）
                })
            
            request_data = {
                "remote_keys": remote_keys
            }
            
            # 使用 Remote Key Manager API 端点（符合标准规范）
            response = self._request("POST", "/eth/v1/remotekeys", json=request_data)
            
            # 解析响应（Remote Key Manager API 响应格式）
            data = response.get('data', {})
            statuses = data.get('statuses', [])
            
            # 统计结果
            result = {
                'imported': [],
                'duplicate': [],
                'error': []
            }
            
            for i, status in enumerate(statuses):
                pubkey = pubkeys[i] if i < len(pubkeys) else None
                status_value = status.get('status', '')
                
                if status_value == 'imported':
                    result['imported'].append(pubkey)
                elif status_value == 'duplicate':
                    result['duplicate'].append(pubkey)
                else:
                    error_msg = status.get('message', 'Unknown error')
                    result['error'].append({
                        'pubkey': pubkey,
                        'error': error_msg
                    })
            
            logger.info(
                f"添加密钥结果: 成功 {len(result['imported'])}, "
                f"重复 {len(result['duplicate'])}, 失败 {len(result['error'])}"
            )
            
            return result
            
        except RemoteValidatorAPIError:
            raise
        except Exception as e:
            logger.error(f"添加密钥失败: {e}")
            raise RemoteValidatorAPIError(f"添加密钥失败: {e}")
    
    def delete_keystores(
        self,
        pubkeys: List[str]
    ) -> Dict[str, Any]:
        """
        从 Validator Client 删除密钥（使用 Remote Key Manager API）
        
        根据 Ethereum Remote Key Manager API 规范：
        https://ethereum.github.io/keymanager-APIs/#/Remote%20Key%20Manager/deleteRemoteKeys
        
        使用 Web3Signer 时，应使用 /eth/v1/remotekeys 端点，而不是 /eth/v1/keystores
        
        Args:
            pubkeys: 要删除的公钥列表
            
        Returns:
            删除结果，包含成功和失败的密钥
        """
        try:
            # 规范化 pubkeys
            pubkeys_normalized = []
            for pubkey in pubkeys:
                pubkey_normalized = pubkey.lower().strip()
                if not pubkey_normalized.startswith('0x'):
                    pubkey_normalized = f"0x{pubkey_normalized}"
                pubkeys_normalized.append(pubkey_normalized)
            
            request_data = {
                "pubkeys": pubkeys_normalized
            }
            
            # 使用 Remote Key Manager API 端点（符合标准规范）
            response = self._request("DELETE", "/eth/v1/remotekeys", json=request_data)
            
            # 解析响应
            data = response.get('data', {})
            statuses = data.get('statuses', [])
            slashing_protection = data.get('slashing_protection', {})
            
            # 统计结果
            result = {
                'deleted': [],
                'not_found': [],
                'error': [],
                'slashing_protection': slashing_protection
            }
            
            for i, status in enumerate(statuses):
                pubkey = pubkeys_normalized[i] if i < len(pubkeys_normalized) else None
                status_value = status.get('status', '')
                
                if status_value == 'deleted':
                    result['deleted'].append(pubkey)
                elif status_value == 'not_found':
                    result['not_found'].append(pubkey)
                else:
                    error_msg = status.get('message', 'Unknown error')
                    result['error'].append({
                        'pubkey': pubkey,
                        'error': error_msg
                    })
            
            logger.info(
                f"删除密钥结果: 成功 {len(result['deleted'])}, "
                f"未找到 {len(result['not_found'])}, 失败 {len(result['error'])}"
            )
            
            return result
            
        except RemoteValidatorAPIError:
            raise
        except Exception as e:
            logger.error(f"删除密钥失败: {e}")
            raise RemoteValidatorAPIError(f"删除密钥失败: {e}")
    
    def health_check(self) -> bool:
        """
        检查 Remote Validator API 健康状态
        
        Returns:
            是否健康
        """
        try:
            # 尝试获取密钥列表作为健康检查
            self.get_keystores()
            return True
        except Exception as e:
            logger.debug(f"Remote Validator API 健康检查失败: {e}")
            return False

