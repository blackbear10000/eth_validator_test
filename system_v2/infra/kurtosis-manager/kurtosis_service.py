"""
Kurtosis 服务封装
封装 Kurtosis CLI 调用逻辑
"""
import subprocess
import json
import logging
from typing import Dict, Any, Optional, Tuple
from pathlib import Path

logger = logging.getLogger(__name__)


class KurtosisService:
    """Kurtosis 网络管理服务"""
    
    def __init__(self, config_file: str = "/kurtosis-config/kurtosis-config.yaml", enclave_name: str = "eth-devnet"):
        """
        初始化 Kurtosis 服务
        
        Args:
            config_file: Kurtosis 配置文件路径
            enclave_name: Enclave 名称
        """
        self.config_file = config_file
        self.enclave_name = enclave_name
    
    def _run_kurtosis_command(self, command: list[str], timeout: int = 300) -> Tuple[bool, str, str]:
        """
        执行 Kurtosis CLI 命令
        
        Args:
            command: Kurtosis 命令列表
            timeout: 超时时间（秒）
            
        Returns:
            (成功标志, stdout, stderr)
        """
        try:
            logger.info(f"执行 Kurtosis 命令: kurtosis {' '.join(command)}")
            result = subprocess.run(
                ["kurtosis"] + command,
                capture_output=True,
                text=True,
                timeout=timeout
            )
            
            if result.returncode == 0:
                logger.debug(f"Kurtosis 命令成功: {result.stdout[:200]}")
            else:
                logger.warning(f"Kurtosis 命令失败: {result.stderr[:200]}")
            
            return result.returncode == 0, result.stdout, result.stderr
        except FileNotFoundError:
            logger.error("Kurtosis CLI 未找到")
            return False, "", "Kurtosis CLI not found"
        except subprocess.TimeoutExpired:
            logger.error(f"Kurtosis 命令超时: {' '.join(command)}")
            return False, "", "Command timeout"
        except Exception as e:
            logger.error(f"执行 Kurtosis 命令失败: {e}", exc_info=True)
            return False, "", str(e)
    
    def get_status(self) -> Dict[str, Any]:
        """
        获取网络状态
        
        Returns:
            网络状态信息
        """
        # 检查 enclave 是否存在
        success, stdout, stderr = self._run_kurtosis_command(["enclave", "ls"], timeout=30)
        
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
            ["enclave", "inspect", self.enclave_name, "--json"],
            timeout=30
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
        except json.JSONDecodeError as e:
            logger.warning(f"解析 JSON 失败: {e}, 原始输出: {stdout[:200]}")
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
        
        logger.info(f"启动 Kurtosis enclave: {self.enclave_name}")
        
        # 检查配置文件是否存在
        if not Path(self.config_file).exists():
            return {
                "success": False,
                "message": f"配置文件不存在: {self.config_file}",
                "error": f"Config file not found: {self.config_file}"
            }
        
        # 启动 enclave
        # 注意：kurtosis run 命令可能需要较长时间（几分钟）
        success, stdout, stderr = self._run_kurtosis_command([
            "run",
            "github.com/ethpandaops/ethereum-package",
            "--args-file", self.config_file,
            "--enclave", self.enclave_name
        ], timeout=600)  # 10 分钟超时
        
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
                "error": stderr,
                "output": stdout
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
        ], timeout=120)
        
        if not success:
            return {
                "success": False,
                "message": f"停止失败: {stderr}",
                "error": stderr
            }
        
        # 移除 enclave
        success, stdout, stderr = self._run_kurtosis_command([
            "enclave", "rm", self.enclave_name
        ], timeout=60)
        
        if success:
            return {
                "success": True,
                "message": f"Enclave '{self.enclave_name}' 已停止并移除",
                "output": stdout
            }
        else:
            # 即使移除失败，停止也算成功
            return {
                "success": True,
                "message": f"Enclave '{self.enclave_name}' 已停止（移除可能失败）",
                "warning": stderr,
                "output": stdout
            }

