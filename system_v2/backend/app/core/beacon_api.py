"""
Beacon Chain API 客户端
用于查询验证者状态、同步链上数据
"""
import logging
from typing import List, Dict, Any, Optional
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from app.config import settings
from app.utils.exceptions import BeaconAPIError

logger = logging.getLogger(__name__)


class BeaconAPIClient:
    """
    Beacon Chain API 客户端
    封装标准 Beacon Chain API 调用
    """
    
    def __init__(self, base_url: Optional[str] = None):
        """
        初始化 Beacon API 客户端
        
        Args:
            base_url: Beacon API 基础 URL
        """
        self.base_url = base_url or settings.beacon_api_url.rstrip('/')
        
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
    
    def _get(self, endpoint: str, params: Optional[Dict] = None) -> Dict[str, Any]:
        """
        发送 GET 请求
        
        Args:
            endpoint: API 端点
            params: 查询参数
            
        Returns:
            JSON 响应数据
        """
        url = f"{self.base_url}{endpoint}"
        
        try:
            response = self.session.get(url, params=params, timeout=10)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Beacon API 请求失败: {url}, {e}")
            raise BeaconAPIError(f"Beacon API 请求失败: {e}")
    
    def get_genesis(self) -> Dict[str, Any]:
        """
        获取创世信息
        
        Returns:
            创世信息，包含 fork_version 和 genesis_validators_root
        """
        return self._get("/eth/v1/beacon/genesis")
    
    def get_genesis_validators_root(self) -> Optional[str]:
        """
        获取创世验证者根
        
        Returns:
            Genesis validators root (hex string) 或 None
        """
        try:
            genesis = self.get_genesis()
            genesis_validators_root = genesis.get('data', {}).get('genesis_validators_root')
            if genesis_validators_root:
                return genesis_validators_root
            return None
        except Exception as e:
            logger.warning(f"无法获取 genesis_validators_root: {e}")
            return None
    
    def get_fork_version(self) -> str:
        """
        获取当前 fork version
        
        Returns:
            Fork version (hex string)
        """
        genesis = self.get_genesis()
        fork_version = genesis.get('data', {}).get('genesis_fork_version')
        if fork_version:
            return fork_version
        raise BeaconAPIError("无法获取 fork version")
    
    def get_fork_schedule(self) -> Dict[str, Any]:
        """
        获取 fork 调度信息
        
        Returns:
            Fork schedule 信息
        """
        return self._get("/eth/v1/config/fork_schedule")
    
    def get_validator(self, pubkey: str, state_id: str = "head") -> Optional[Dict[str, Any]]:
        """
        获取验证者信息
        
        Args:
            pubkey: 验证者公钥（带或不带 0x 前缀）
            state_id: 状态 ID (head, finalized, genesis, <slot>, <epoch>)
            
        Returns:
            验证者信息或 None
        """
        try:
            # 规范化 pubkey：确保有 0x 前缀，转为小写
            pubkey_normalized = pubkey.lower().strip()
            if not pubkey_normalized.startswith('0x'):
                pubkey_normalized = f"0x{pubkey_normalized}"
            
            # Beacon API 要求 URL 路径中的 pubkey 需要 0x 前缀
            response = self._get(f"/eth/v1/beacon/states/{state_id}/validators/{pubkey_normalized}")
            data = response.get('data')
            
            if data:
                return data
            return None
            
        except BeaconAPIError:
            # 验证者可能不存在
            return None
    
    def get_validators(
        self,
        pubkeys: List[str],
        state_id: str = "head"
    ) -> Dict[str, Dict[str, Any]]:
        """
        批量获取验证者信息
        
        Args:
            pubkeys: 验证者公钥列表（带或不带 0x 前缀）
            state_id: 状态 ID
            
        Returns:
            验证者信息字典，key 为公钥（小写，带 0x 前缀）
        """
        # 准备查询参数
        # 注意：在查询参数中，某些 Beacon API 实现可能需要不带 0x 前缀
        # 但根据标准，应该支持两种格式，这里先尝试不带 0x 前缀
        pubkey_params = []
        for pubkey in pubkeys:
            pubkey_normalized = pubkey.lower().strip()
            # 移除 0x 前缀用于查询参数（某些实现要求）
            pubkey_clean = pubkey_normalized.replace('0x', '')
            pubkey_params.append(pubkey_clean)
        
        # Beacon API 支持多个 pubkey 查询
        params = {'id': pubkey_params}
        
        try:
            response = self._get(f"/eth/v1/beacon/states/{state_id}/validators", params=params)
            data_list = response.get('data', [])
            
            # 转换为字典，key 使用规范化格式（小写，带 0x 前缀）
            validators = {}
            for validator_data in data_list:
                pubkey = validator_data.get('validator', {}).get('pubkey', '')
                if pubkey:
                    # 确保 pubkey 有 0x 前缀并转为小写
                    pubkey_normalized = pubkey.lower().strip()
                    if not pubkey_normalized.startswith('0x'):
                        pubkey_normalized = f"0x{pubkey_normalized}"
                    validators[pubkey_normalized] = validator_data
            
            return validators
            
        except BeaconAPIError as e:
            logger.error(f"批量获取验证者信息失败: {e}")
            return {}
    
    def get_validator_balance(
        self,
        pubkey: str,
        state_id: str = "head"
    ) -> Optional[int]:
        """
        获取验证者余额（wei）
        
        Args:
            pubkey: 验证者公钥
            state_id: 状态 ID
            
        Returns:
            余额（wei）或 None
        """
        validator = self.get_validator(pubkey, state_id)
        if validator:
            balance = validator.get('balance', '0')
            return int(balance)
        return None
    
    def health_check(self) -> bool:
        """
        检查 Beacon API 健康状态
        
        Returns:
            是否健康
        """
        try:
            # 使用更短的超时时间，避免阻塞
            url = f"{self.base_url}/eth/v1/node/health"
            response = requests.get(url, timeout=3)
            # 200 或 206 都表示健康
            return response.status_code in [200, 206]
        except requests.exceptions.Timeout:
            logger.debug(f"Beacon API 健康检查超时: {self.base_url}")
            return False
        except requests.exceptions.ConnectionError:
            logger.debug(f"Beacon API 连接失败（可能未启动）: {self.base_url}")
            return False
        except Exception as e:
            logger.debug(f"Beacon API 健康检查失败: {e}")
            return False

