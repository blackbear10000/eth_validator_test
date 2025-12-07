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


def get_beacon_api_url() -> str:
    """
    获取 Beacon API URL（优先从 NetworkService 获取，否则使用配置的默认值）
    
    Returns:
        Beacon API URL
    """
    try:
        from app.services.network_service import NetworkService
        network_service = NetworkService()
        endpoints = network_service.get_rpc_endpoints()
        if endpoints.get("beacon_api_url"):
            logger.debug(f"从网络服务获取 Beacon API URL: {endpoints['beacon_api_url']}")
            return endpoints["beacon_api_url"]
    except Exception as e:
        logger.debug(f"无法从网络服务获取 Beacon API URL: {e}，使用默认配置")
    
    # 使用默认配置
    return settings.beacon_api_url


class BeaconAPIClient:
    """
    Beacon Chain API 客户端
    封装标准 Beacon Chain API 调用
    """
    
    # Ethereum 2.0 常量
    SLOTS_PER_EPOCH = 32  # 大多数网络的默认值
    
    @staticmethod
    def slot_to_epoch(slot: int) -> int:
        """
        将 slot 转换为 epoch
        
        Args:
            slot: Slot 编号
            
        Returns:
            Epoch 编号
        """
        return slot // BeaconAPIClient.SLOTS_PER_EPOCH
    
    def __init__(self, base_url: Optional[str] = None):
        """
        初始化 Beacon API 客户端
        
        Args:
            base_url: Beacon API 基础 URL（如果不提供，则自动从 NetworkService 获取）
        """
        if base_url:
            self.base_url = base_url.rstrip('/')
        else:
            # 自动获取 Beacon API URL（优先从 NetworkService）
            self.base_url = get_beacon_api_url().rstrip('/')
        
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
    
    def get_spec(self) -> Optional[Dict[str, Any]]:
        """
        获取网络规范参数
        
        Returns:
            网络规范参数字典，如果端点不支持则返回 None
        """
        try:
            return self._get("/eth/v1/config/spec")
        except BeaconAPIError:
            # 某些 Beacon API 实现可能不支持此端点
            logger.debug("Beacon API 不支持 /eth/v1/config/spec 端点")
            return None
    
    def get_min_validator_withdrawability_delay(self) -> int:
        """
        获取 MIN_VALIDATOR_WITHDRAWABILITY_DELAY 参数
        
        注意：虽然某些网络配置可能设置了较小的值（如 2），但 Beacon Chain 节点
        在验证退出时可能仍使用 Ethereum 规范的默认值 256。为了确保退出验证
        的一致性，这里固定返回 256。
        
        Returns:
            MIN_VALIDATOR_WITHDRAWABILITY_DELAY 值（epochs），固定为 256
        """
        # 固定返回 256，因为 Beacon Chain 节点在验证退出时使用此值
        # 即使配置文件或 Beacon API 返回了其他值，链上验证仍会使用 256
        return 256
    
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
        # 根据 Beacon API 标准，查询参数中的 pubkey 应该带 0x 前缀
        pubkey_params = []
        for pubkey in pubkeys:
            pubkey_normalized = pubkey.lower().strip()
            # 确保有 0x 前缀（Beacon API 标准要求）
            if not pubkey_normalized.startswith('0x'):
                pubkey_normalized = f"0x{pubkey_normalized}"
            pubkey_params.append(pubkey_normalized)
        
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

