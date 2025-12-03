"""
网络管理服务
管理 Kurtosis 开发网络的启动、停止和状态查询
"""
import subprocess
import json
import logging
from typing import Dict, Optional, Any
from app.config import settings

logger = logging.getLogger(__name__)


class NetworkService:
    """Kurtosis 网络管理服务"""
    
    def __init__(self, enclave_name: Optional[str] = None):
        """
        初始化网络服务
        
        Args:
            enclave_name: Kurtosis enclave 名称，默认使用配置中的值
        """
        self.enclave_name = enclave_name or settings.kurtosis_enclave
    
    def _run_kurtosis_command(self, command: list[str]) -> tuple[bool, str, str]:
        """
        执行 Kurtosis CLI 命令
        
        Args:
            command: Kurtosis 命令列表
            
        Returns:
            (成功标志, stdout, stderr)
        """
        try:
            result = subprocess.run(
                ["kurtosis"] + command,
                capture_output=True,
                text=True,
                timeout=30
            )
            return result.returncode == 0, result.stdout, result.stderr
        except FileNotFoundError:
            logger.error("Kurtosis CLI 未找到，请确保已安装 Kurtosis")
            return False, "", "Kurtosis CLI not found"
        except subprocess.TimeoutExpired:
            logger.error(f"Kurtosis 命令超时: {' '.join(command)}")
            return False, "", "Command timeout"
        except Exception as e:
            logger.error(f"执行 Kurtosis 命令失败: {e}")
            return False, "", str(e)
    
    def get_status(self) -> Dict[str, Any]:
        """
        获取网络状态
        
        Returns:
            网络状态信息
        """
        # 检查 enclave 是否存在
        success, stdout, stderr = self._run_kurtosis_command(["enclave", "ls"])
        
        if not success:
            return {
                "enclave_name": self.enclave_name,
                "status": "error",
                "error": stderr or "无法查询 enclave 列表",
                "is_running": False
            }
        
        # 检查 enclave 是否在运行
        is_running = self.enclave_name in stdout
        
        if not is_running:
            return {
                "enclave_name": self.enclave_name,
                "status": "stopped",
                "is_running": False
            }
        
        # 获取 enclave 详细信息
        success, stdout, stderr = self._run_kurtosis_command(
            ["enclave", "inspect", self.enclave_name]
        )
        
        if not success:
            return {
                "enclave_name": self.enclave_name,
                "status": "running",
                "is_running": True,
                "error": stderr or "无法获取 enclave 详细信息"
            }
        
        # 解析 enclave 信息
        try:
            enclave_info = json.loads(stdout)
            return {
                "enclave_name": self.enclave_name,
                "status": "running",
                "is_running": True,
                "enclave_info": enclave_info
            }
        except json.JSONDecodeError:
            # 如果无法解析 JSON，返回原始输出
            return {
                "enclave_name": self.enclave_name,
                "status": "running",
                "is_running": True,
                "raw_output": stdout
            }
    
    def start(self) -> Dict[str, Any]:
        """
        启动 Kurtosis 网络
        
        Returns:
            启动结果
        """
        # 检查是否已经运行
        status = self.get_status()
        if status.get("is_running"):
            return {
                "success": True,
                "message": f"Enclave '{self.enclave_name}' 已经在运行",
                "status": status
            }
        
        # 启动 enclave
        # 注意：这里需要根据实际的 Kurtosis 启动命令调整
        # 通常需要指定配置文件或包
        logger.info(f"启动 Kurtosis enclave: {self.enclave_name}")
        
        # 尝试使用默认的启动命令
        # 实际命令可能需要根据项目配置调整
        success, stdout, stderr = self._run_kurtosis_command([
            "run",
            "github.com/ethpandaops/ethereum-package",
            "--enclave", self.enclave_name
        ])
        
        if success:
            return {
                "success": True,
                "message": f"Enclave '{self.enclave_name}' 启动成功",
                "output": stdout
            }
        else:
            return {
                "success": False,
                "message": f"启动失败: {stderr}",
                "error": stderr
            }
    
    def stop(self) -> Dict[str, Any]:
        """
        停止 Kurtosis 网络
        
        Returns:
            停止结果
        """
        # 检查是否在运行
        status = self.get_status()
        if not status.get("is_running"):
            return {
                "success": True,
                "message": f"Enclave '{self.enclave_name}' 未运行",
                "status": status
            }
        
        logger.info(f"停止 Kurtosis enclave: {self.enclave_name}")
        
        # 停止 enclave
        success, stdout, stderr = self._run_kurtosis_command([
            "enclave", "stop", self.enclave_name
        ])
        
        if success:
            return {
                "success": True,
                "message": f"Enclave '{self.enclave_name}' 已停止",
                "output": stdout
            }
        else:
            return {
                "success": False,
                "message": f"停止失败: {stderr}",
                "error": stderr
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

