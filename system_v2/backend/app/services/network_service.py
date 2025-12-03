"""
网络管理服务
管理 Kurtosis 开发网络的启动、停止和状态查询
通过 HTTP API 调用 kurtosis-manager 服务
"""
import logging
import requests
from typing import Dict, Optional, Any
from app.config import settings

logger = logging.getLogger(__name__)


class NetworkService:
    """Kurtosis 网络管理服务"""
    
    def __init__(self, enclave_name: Optional[str] = None, manager_url: Optional[str] = None):
        """
        初始化网络服务
        
        Args:
            enclave_name: Kurtosis enclave 名称，默认使用配置中的值
            manager_url: Kurtosis 管理服务 URL，默认使用配置中的值
        """
        self.enclave_name = enclave_name or settings.kurtosis_enclave
        self.manager_url = (manager_url or settings.kurtosis_manager_url).rstrip('/')
    
    def _call_api(self, endpoint: str, method: str = "GET", **kwargs) -> Dict[str, Any]:
        """
        调用 Kurtosis 管理服务 API
        
        Args:
            endpoint: API 端点
            method: HTTP 方法
            **kwargs: 其他请求参数
            
        Returns:
            API 响应数据
        """
        url = f"{self.manager_url}{endpoint}"
        try:
            logger.debug(f"调用 Kurtosis 管理服务: {method} {url}")
            response = requests.request(method, url, timeout=30, **kwargs)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.ConnectionError as e:
            logger.error(f"无法连接到 Kurtosis 管理服务: {url}, {e}")
            return {
                "error": f"无法连接到 Kurtosis 管理服务: {e}",
                "is_running": False
            }
        except requests.exceptions.Timeout:
            logger.error(f"Kurtosis 管理服务请求超时: {url}")
            return {
                "error": "请求超时",
                "is_running": False
            }
        except requests.exceptions.HTTPError as e:
            logger.error(f"Kurtosis 管理服务 HTTP 错误: {e}, 响应: {response.text[:200]}")
            try:
                return response.json()
            except:
                return {
                    "error": f"HTTP 错误: {e}",
                    "is_running": False
                }
        except Exception as e:
            logger.error(f"调用 Kurtosis 管理服务失败: {e}", exc_info=True)
            return {
                "error": str(e),
                "is_running": False
            }
    
    def get_status(self) -> Dict[str, Any]:
        """
        获取网络状态
        
        Returns:
            网络状态信息
        """
        result = self._call_api("/status")
        
        # 确保包含 enclave_name
        if "enclave_name" not in result:
            result["enclave_name"] = self.enclave_name
        
        return result
    
    def start(self) -> Dict[str, Any]:
        """
        启动 Kurtosis 网络
        
        Returns:
            启动结果
        """
        logger.info(f"启动 Kurtosis 网络: {self.enclave_name}")
        result = self._call_api("/start", method="POST")
        
        # 确保包含 success 字段
        if "success" not in result:
            result["success"] = "error" not in result
        
        return result
    
    def stop(self) -> Dict[str, Any]:
        """
        停止 Kurtosis 网络
        
        Returns:
            停止结果
        """
        logger.info(f"停止 Kurtosis 网络: {self.enclave_name}")
        result = self._call_api("/stop", method="POST")
        
        # 确保包含 success 字段
        if "success" not in result:
            result["success"] = "error" not in result
        
        return result
    
    def get_info(self) -> Dict[str, Any]:
        """
        获取网络详细信息（genesis、fork version、deposit contract 等）
        
        Returns:
            网络详细信息
        """
        status = self.get_status()
        
        if not status.get("is_running"):
            return {
                "error": "网络未运行",
                "status": status
            }
        
        # 尝试从 Beacon API 获取网络信息
        try:
            from app.core.beacon_api import BeaconAPIClient
            beacon_api = BeaconAPIClient()
            
            # 获取 genesis 信息
            genesis_info = beacon_api.get_genesis()
            
            # 获取 fork schedule（如果可用）
            try:
                fork_schedule = beacon_api.get_fork_schedule()
            except Exception:
                fork_schedule = None
            
            return {
                "enclave_name": self.enclave_name,
                "genesis": genesis_info,
                "fork_schedule": fork_schedule,
                "beacon_api_url": settings.beacon_api_url
            }
        except Exception as e:
            logger.error(f"获取网络信息失败: {e}")
            return {
                "enclave_name": self.enclave_name,
                "error": str(e),
                "status": status
            }

