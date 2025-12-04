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
            result = response.json()
            
            # 确保返回的数据包含必要字段（对于 /status 端点）
            if endpoint == "/status":
                if "enclave_name" not in result:
                    result["enclave_name"] = self.enclave_name
                if "status" not in result:
                    result["status"] = "stopped" if not result.get("is_running") else "running"
                if "is_running" not in result:
                    result["is_running"] = False
            
            return result
        except requests.exceptions.ConnectionError as e:
            logger.error(f"无法连接到 Kurtosis 管理服务: {url}, {e}")
            return {
                "enclave_name": self.enclave_name,
                "status": "error",
                "is_running": False,
                "error": f"无法连接到 Kurtosis 管理服务: {e}"
            }
        except requests.exceptions.Timeout:
            logger.error(f"Kurtosis 管理服务请求超时: {url}")
            return {
                "enclave_name": self.enclave_name,
                "status": "error",
                "is_running": False,
                "error": "请求超时"
            }
        except requests.exceptions.HTTPError as e:
            logger.error(f"Kurtosis 管理服务 HTTP 错误: {e}, 响应: {response.text[:200]}")
            try:
                result = response.json()
                # 确保包含必要字段
                if "enclave_name" not in result:
                    result["enclave_name"] = self.enclave_name
                if "status" not in result:
                    result["status"] = "error" if result.get("error") else "stopped"
                if "is_running" not in result:
                    result["is_running"] = False
                return result
            except:
                return {
                    "enclave_name": self.enclave_name,
                    "status": "error",
                    "is_running": False,
                    "error": f"HTTP 错误: {e}"
                }
        except Exception as e:
            logger.error(f"调用 Kurtosis 管理服务失败: {e}", exc_info=True)
            return {
                "enclave_name": self.enclave_name,
                "status": "error",
                "is_running": False,
                "error": str(e)
            }
    
    def get_status(self) -> Dict[str, Any]:
        """
        获取网络状态
        
        Returns:
            网络状态信息
        """
        result = self._call_api("/status")
        
        # 确保包含必要字段
        if "enclave_name" not in result:
            result["enclave_name"] = self.enclave_name
        if "status" not in result:
            result["status"] = "stopped" if not result.get("is_running") else "running"
        if "is_running" not in result:
            result["is_running"] = False
        
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
            # 检查是否有错误，或者检查 status 字段
            if "error" in result:
                result["success"] = False
            elif result.get("status") == "running" or result.get("is_running"):
                result["success"] = True
            else:
                result["success"] = False
        
        # 确保包含 message 字段
        if "message" not in result:
            if result.get("success"):
                result["message"] = "网络启动成功"
            else:
                result["message"] = result.get("error", "启动失败")
        
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
    
    def get_rpc_endpoints(self) -> Dict[str, Any]:
        """
        从 Kurtosis enclave 信息中提取 RPC 端点
        
        Returns:
            包含 rpc_url 和 ws_url 的字典，如果无法获取则返回错误信息
        """
        status = self.get_status()
        
        if not status.get("is_running"):
            return {
                "error": "网络未运行",
                "rpc_url": None,
                "ws_url": None
            }
        
        # 获取 enclave 详细信息
        raw_output = status.get("raw_output") or status.get("enclave_info", {}).get("raw_output")
        
        if not raw_output:
            return {
                "error": "无法获取 enclave 详细信息",
                "rpc_url": None,
                "ws_url": None
            }
        
        # 解析输出，查找执行层服务的 RPC 端口
        # 格式示例（Kurtosis enclave inspect 输出）：
        # NAME                          STATUS    PORTS
        # el-1-geth-prysm               RUNNING   engine-rpc: 8551/tcp -> 127.0.0.1:33699
        #                                              rpc: 8545/tcp -> 127.0.0.1:33697
        #                                              ws: 8546/tcp -> 127.0.0.1:33698
        
        import re
        
        rpc_url = None
        ws_url = None
        current_service = None
        
        # 记录原始输出用于调试
        logger.debug(f"解析 enclave 输出，长度: {len(raw_output)} 字符")
        logger.debug(f"输出前 500 字符: {raw_output[:500]}")
        
        # 查找执行层服务（el- 开头的服务）
        lines = raw_output.split('\n')
        in_el_service = False
        
        for i, line in enumerate(lines):
            # 检查是否是执行层服务行（可能包含容器ID或服务名）
            # 格式可能是：容器ID + 服务名，或者直接是服务名
            if re.search(r'el-\d+-\w+', line):
                in_el_service = True
                # 提取服务名称
                match = re.search(r'(el-\d+-\w+)', line)
                if match:
                    current_service = match.group(1)
                    logger.debug(f"找到执行层服务: {current_service}, 行 {i+1}: {line[:100]}")
                continue
            
            # 如果在执行层服务块中，查找端口映射
            if in_el_service:
                # 查找 rpc 端口（8545）
                # 匹配格式：rpc: 8545/tcp -> 127.0.0.1:33697 或 rpc:8545/tcp->127.0.0.1:33697
                rpc_match = re.search(r'rpc\s*:\s*8545/tcp\s*->\s*([\d.]+):(\d+)', line)
                if rpc_match:
                    host_ip = rpc_match.group(1)
                    host_port = rpc_match.group(2)
                    # 默认使用 host.docker.internal（因为后端在容器中运行）
                    # 如果映射到 localhost，使用 host.docker.internal；否则使用实际 IP
                    if host_ip == '127.0.0.1' or host_ip == '0.0.0.0':
                        rpc_url = f"http://host.docker.internal:{host_port}"
                    else:
                        rpc_url = f"http://{host_ip}:{host_port}"
                    logger.info(f"找到 RPC 端口映射: {host_ip}:{host_port} -> {rpc_url}")
                
                # 查找 ws 端口（8546）
                ws_match = re.search(r'ws\s*:\s*8546/tcp\s*->\s*([\d.]+):(\d+)', line)
                if ws_match:
                    host_ip = ws_match.group(1)
                    host_port = ws_match.group(2)
                    if host_ip == '127.0.0.1' or host_ip == '0.0.0.0':
                        ws_url = f"ws://host.docker.internal:{host_port}"
                    else:
                        ws_url = f"ws://{host_ip}:{host_port}"
                    logger.info(f"找到 WS 端口映射: {host_ip}:{host_port} -> {ws_url}")
                
                # 如果找到了 RPC URL，可以继续查找 WS，但通常一个服务块就包含了
                if rpc_url:
                    # 继续查找 WS，但不要跳出循环，因为可能有多个执行层服务
                    pass
            
            # 如果遇到新的服务块（非执行层），重置状态
            # 检查是否是新的容器/服务行（通常以容器ID开头，或者包含其他服务名）
            if in_el_service and re.match(r'^[a-f0-9]{12}\s+', line) and not re.search(r'el-\d+-', line):
                in_el_service = False
                current_service = None
        
        if rpc_url:
            # 生成主机可访问的 URL（用于前端显示）
            # 将 host.docker.internal 替换回 localhost
            host_rpc_url = rpc_url.replace('host.docker.internal', 'localhost')
            host_ws_url = ws_url.replace('host.docker.internal', 'localhost') if ws_url else None
            
            logger.info(f"成功提取 RPC 端点: 容器内={rpc_url}, 主机={host_rpc_url}, 服务={current_service}")
            return {
                "rpc_url": rpc_url,  # 返回容器可访问的 URL（默认使用 host.docker.internal）
                "host_rpc_url": host_rpc_url,  # 返回主机可访问的 URL（用于前端显示）
                "ws_url": ws_url,
                "host_ws_url": host_ws_url,
                "service": current_service
            }
        else:
            logger.warning(f"无法从 enclave 信息中提取 RPC 端点。原始输出前 1000 字符:\n{raw_output[:1000]}")
            return {
                "error": f"无法从 enclave 信息中提取 RPC 端点。请检查网络是否正常运行，或手动提供 RPC URL。",
                "rpc_url": None,
                "host_rpc_url": None,
                "ws_url": None,
                "debug_info": raw_output[:500]  # 返回部分原始输出用于调试
            }
    
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
        
        # 尝试从 Kurtosis 配置文件读取 deposit_contract_address
        deposit_contract_address = None
        try:
            import yaml
            import os
            config_file = os.getenv("KURTOSIS_CONFIG_FILE", "/kurtosis-config/kurtosis-config.yaml")
            if os.path.exists(config_file):
                with open(config_file, 'r') as f:
                    config = yaml.safe_load(f)
                    if config and 'network_params' in config:
                        deposit_contract_address = config['network_params'].get('deposit_contract_address')
                        if deposit_contract_address:
                            logger.info(f"从 Kurtosis 配置文件读取到 deposit_contract_address: {deposit_contract_address}")
        except Exception as e:
            logger.warning(f"无法从 Kurtosis 配置文件读取 deposit_contract_address: {e}")
        
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
            
            # 获取 fork_version
            fork_version = None
            try:
                fork_version = beacon_api.get_fork_version()
                logger.info(f"从 Beacon API 获取到 fork_version: {fork_version}")
            except Exception as e:
                logger.warning(f"无法从 Beacon API 获取 fork_version: {e}")
            
            result = {
                "enclave_name": self.enclave_name,
                "genesis": genesis_info,
                "fork_schedule": fork_schedule,
                "beacon_api_url": settings.beacon_api_url,
                "fork_version": fork_version,
                "network_name": "mainnet"  # 对于 dev net，使用 mainnet 作为 network_name
            }
            
            # 添加 deposit_contract_address（如果从配置文件读取到）
            if deposit_contract_address:
                result["deposit_contract_address"] = deposit_contract_address
            
            return result
        except Exception as e:
            logger.error(f"获取网络信息失败: {e}")
            result = {
                "enclave_name": self.enclave_name,
                "error": str(e),
                "status": status,
                "network_name": "mainnet"  # 对于 dev net，使用 mainnet 作为 network_name
            }
            # 即使 Beacon API 失败，也返回 deposit_contract_address（如果从配置文件读取到）
            if deposit_contract_address:
                result["deposit_contract_address"] = deposit_contract_address
            return result

