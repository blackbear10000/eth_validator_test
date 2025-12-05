"""
客户端进程管理服务
管理 Validator Client Docker 容器的启动、停止和状态查询
"""
import subprocess
import logging
import os
import json
import time
from typing import Dict, Optional, List, Any
from pathlib import Path
from app.config import settings

logger = logging.getLogger(__name__)


class ClientProcessService:
    """Validator Client Docker 容器管理服务"""
    
    def __init__(self):
        """初始化容器管理服务"""
        self.network_name = "validator_network"  # Docker 网络名称
        self.image_map = {
            "prysm": "gcr.io/prysmaticlabs/prysm/validator:latest",
            "lighthouse": "sigp/lighthouse:latest",
            "teku": "consensys/teku:latest"
        }
    
    def _get_container_name(self, client_id: int, client_type: str) -> str:
        """
        获取容器名称
        
        Args:
            client_id: 客户端 ID
            client_type: 客户端类型
            
        Returns:
            容器名称
        """
        client_type_clean = client_type.lower().replace(' ', '-')
        return f"validator-client-{client_id}-{client_type_clean}"
    
    def _get_docker_image(self, client_type: str) -> str:
        """
        获取 Docker 镜像名称
        
        Args:
            client_type: 客户端类型
            
        Returns:
            Docker 镜像名称
        """
        client_type_lower = client_type.lower()
        if 'prysm' in client_type_lower:
            return self.image_map.get("prysm", "gcr.io/prysmaticlabs/prysm/validator:latest")
        elif 'lighthouse' in client_type_lower:
            return self.image_map.get("lighthouse", "sigp/lighthouse:latest")
        elif 'teku' in client_type_lower:
            return self.image_map.get("teku", "consensys/teku:latest")
        raise ValueError(f"不支持的客户端类型: {client_type}")
    
    def _check_docker_available(self) -> bool:
        """
        检查 Docker 是否可用
        
        检查项：
        1. Docker CLI 可执行文件是否存在
        2. Docker CLI 是否可以执行
        3. Docker socket 是否存在且可访问
        4. 是否可以执行基本的 Docker 命令
        
        Returns:
            Docker 是否可用
        """
        # 检查 Docker CLI 是否存在
        try:
            result = subprocess.run(
                ["docker", "--version"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode != 0:
                logger.error(f"Docker CLI 返回错误: {result.stderr}")
                return False
            logger.debug(f"Docker CLI 版本: {result.stdout.strip()}")
        except FileNotFoundError:
            logger.error("Docker CLI 未安装或不在 PATH 中")
            return False
        except subprocess.TimeoutExpired:
            logger.error("Docker CLI 检查超时")
            return False
        except Exception as e:
            logger.error(f"Docker CLI 检查失败: {e}")
            return False
        
        # 检查 Docker socket 是否可访问
        docker_sock = "/var/run/docker.sock"
        if not os.path.exists(docker_sock):
            logger.error(f"Docker socket 不存在: {docker_sock}")
            return False
        
        if not os.access(docker_sock, os.R_OK):
            logger.error(f"Docker socket 不可读: {docker_sock}")
            return False
        
        # 尝试执行一个简单的 Docker 命令验证连接
        try:
            result = subprocess.run(
                ["docker", "ps", "--format", "{{.Names}}"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode != 0:
                logger.warning(f"Docker 命令执行失败: {result.stderr}")
                # 不返回 False，因为可能是权限问题，但 CLI 可用
                # 实际使用时可能会失败，但至少 CLI 已安装
            else:
                logger.debug("Docker 连接验证成功")
        except Exception as e:
            logger.warning(f"Docker 命令测试失败: {e}")
            # 不返回 False，因为可能是临时问题
        
        return True
    
    def get_status(self, client_id: int, client_type: str) -> Dict[str, any]:
        """
        获取客户端容器状态
        
        Args:
            client_id: 客户端 ID
            client_type: 客户端类型
            
        Returns:
            容器状态信息
        """
        container_name = self._get_container_name(client_id, client_type)
        
        try:
            # 查询容器状态
            result = subprocess.run(
                ["docker", "ps", "-a", "--filter", f"name={container_name}", "--format", "{{.Names}}\t{{.Status}}\t{{.State}}"],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode != 0:
                logger.warning(f"查询容器状态失败: {result.stderr}")
                return {
                    "client_id": client_id,
                    "status": "unknown",
                    "is_running": False,
                    "error": "无法查询容器状态"
                }
            
            # 解析输出
            if result.stdout.strip():
                # 容器存在
                parts = result.stdout.strip().split('\t')
                if len(parts) >= 3:
                    status_str = parts[1]
                    state = parts[2]
                    
                    is_running = state == "running"
                    return {
                        "client_id": client_id,
                        "container_name": container_name,
                        "status": "running" if is_running else "stopped",
                        "state": state,
                        "status_string": status_str,
                        "is_running": is_running
                    }
            
            # 容器不存在
            return {
                "client_id": client_id,
                "container_name": container_name,
                "status": "stopped",
                "is_running": False
            }
            
        except subprocess.TimeoutExpired:
            logger.error(f"查询容器状态超时: {container_name}")
            return {
                "client_id": client_id,
                "status": "unknown",
                "is_running": False,
                "error": "查询超时"
            }
        except Exception as e:
            logger.error(f"查询容器状态失败: {e}")
            return {
                "client_id": client_id,
                "status": "unknown",
                "is_running": False,
                "error": str(e)
            }
    
    def start(
        self,
        client_id: int,
        client_type: str,
        config_file: Optional[str] = None,
        config_dir: Optional[str] = None
    ) -> Dict[str, any]:
        """
        启动客户端 Docker 容器
        
        Args:
            client_id: 客户端 ID
            client_type: 客户端类型
            config_file: 配置文件路径（容器内路径）
            config_dir: 配置文件目录（宿主机路径，用于挂载）
            
        Returns:
            启动结果
        """
        # 检查 Docker 是否可用
        if not self._check_docker_available():
            return {
                "success": False,
                "message": "Docker 不可用，无法启动容器"
            }
        
        # 检查是否已经在运行
        status = self.get_status(client_id, client_type)
        if status.get("is_running"):
            return {
                "success": True,
                "message": f"客户端 {client_id} 已经在运行",
                "status": status
            }
        
        container_name = self._get_container_name(client_id, client_type)
        docker_image = self._get_docker_image(client_type)
        
        try:
            # 构建 docker run 命令
            cmd = ["docker", "run", "-d"]
            
            # 容器名称
            cmd.extend(["--name", container_name])
            
            # 网络配置
            cmd.extend(["--network", self.network_name])
            
            # 配置文件挂载
            if config_dir:
                # 确保使用绝对路径
                # 如果 config_dir 是相对路径，需要转换为绝对路径
                if not os.path.isabs(config_dir):
                    # 相对于 backend 容器的工作目录
                    config_dir_abs = os.path.abspath(config_dir)
                else:
                    config_dir_abs = config_dir
                
                # 确保目录存在
                if not os.path.exists(config_dir_abs):
                    logger.warning(f"配置文件目录不存在，将创建: {config_dir_abs}")
                    os.makedirs(config_dir_abs, exist_ok=True)
                
                cmd.extend(["-v", f"{config_dir_abs}:/config:ro"])
                logger.debug(f"挂载配置目录: {config_dir_abs} -> /config")
            
            # 数据目录挂载（持久化）
            # 在容器内使用 /app/validator-clients-data（挂载到宿主机）
            if os.path.exists("/app"):
                # 在容器内
                data_dir = f"/app/validator-clients-data/{client_id}"
            else:
                # 在宿主机上
                data_dir = f"validator-clients-data/{client_id}"
            data_dir_abs = os.path.abspath(data_dir)
            os.makedirs(data_dir_abs, exist_ok=True)
            cmd.extend(["-v", f"{data_dir_abs}:/data:rw"])
            logger.debug(f"挂载数据目录: {data_dir_abs} -> /data")
            
            # 镜像
            cmd.append(docker_image)
            
            # 构建容器内启动命令
            container_cmd = self._build_container_command(client_type, config_file)
            cmd.extend(container_cmd)
            
            # 执行 docker run
            logger.info(f"启动客户端容器 {container_name}: {' '.join(cmd)}")
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=60
            )
            
            if result.returncode != 0:
                error_msg = result.stderr.strip() or result.stdout.strip()
                logger.error(f"启动容器失败: {error_msg}")
                return {
                    "success": False,
                    "message": f"启动容器失败: {error_msg}"
                }
            
            container_id = result.stdout.strip()
            logger.info(f"容器启动成功: {container_name} (ID: {container_id[:12]})")
            
            # 等待容器启动
            time.sleep(2)
            
            return {
                "success": True,
                "message": f"客户端 {client_id} 容器启动成功",
                "container_id": container_id,
                "container_name": container_name,
                "status": self.get_status(client_id, client_type)
            }
            
        except subprocess.TimeoutExpired:
            logger.error(f"启动容器超时: {container_name}")
            return {
                "success": False,
                "message": "启动容器超时"
            }
        except Exception as e:
            logger.error(f"启动客户端 {client_id} 失败: {e}", exc_info=True)
            return {
                "success": False,
                "message": f"启动失败: {str(e)}"
            }
    
    def stop(self, client_id: int, client_type: str, remove: bool = False) -> Dict[str, any]:
        """
        停止客户端 Docker 容器
        
        Args:
            client_id: 客户端 ID
            client_type: 客户端类型
            remove: 是否删除容器（默认：False，保留容器用于调试）
            
        Returns:
            停止结果
        """
        container_name = self._get_container_name(client_id, client_type)
        
        # 检查容器是否存在
        status = self.get_status(client_id, client_type)
        if not status.get("is_running") and "container_name" not in status:
            return {
                "success": True,
                "message": f"客户端 {client_id} 容器不存在"
            }
        
        try:
            # 停止容器
            logger.info(f"停止容器: {container_name}")
            stop_result = subprocess.run(
                ["docker", "stop", container_name],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if stop_result.returncode != 0:
                # 容器可能已经停止
                if "No such container" in stop_result.stderr or "is not running" in stop_result.stderr:
                    logger.debug(f"容器已停止或不存在: {container_name}")
                else:
                    logger.warning(f"停止容器失败: {stop_result.stderr}")
                    return {
                        "success": False,
                        "message": f"停止容器失败: {stop_result.stderr.strip()}"
                    }
            
            # 如果需要，删除容器
            if remove:
                logger.info(f"删除容器: {container_name}")
                rm_result = subprocess.run(
                    ["docker", "rm", container_name],
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                if rm_result.returncode != 0:
                    logger.warning(f"删除容器失败: {rm_result.stderr}")
            
            return {
                "success": True,
                "message": f"客户端 {client_id} 已停止" + ("并删除" if remove else "")
            }
            
        except subprocess.TimeoutExpired:
            logger.error(f"停止容器超时: {container_name}")
            return {
                "success": False,
                "message": "停止容器超时"
            }
        except Exception as e:
            logger.error(f"停止客户端 {client_id} 失败: {e}", exc_info=True)
            return {
                "success": False,
                "message": f"停止失败: {str(e)}"
            }
    
    def _build_container_command(
        self,
        client_type: str,
        config_file: Optional[str] = None
    ) -> List[str]:
        """
        构建容器内启动命令
        
        Args:
            client_type: 客户端类型
            config_file: 配置文件路径（容器内路径，如 /config/config.yaml）
            
        Returns:
            启动命令列表
        """
        client_type_lower = client_type.lower()
        
        if 'prysm' in client_type_lower:
            cmd = ['validator']
            if config_file:
                # 如果传入的是相对路径，转换为容器内绝对路径
                if not config_file.startswith('/'):
                    config_file = f"/config/{config_file}"
                cmd.extend(['--config-file', config_file])
            return cmd
        
        elif 'lighthouse' in client_type_lower:
            cmd = ['validator']
            if config_file:
                if not config_file.startswith('/'):
                    config_file = f"/config/{config_file}"
                cmd.extend(['--config-file', config_file])
            return cmd
        
        elif 'teku' in client_type_lower:
            cmd = []
            if config_file:
                if not config_file.startswith('/'):
                    config_file = f"/config/{config_file}"
                cmd.extend(['--config-file', config_file])
            return cmd
        
        raise ValueError(f"不支持的客户端类型: {client_type}")
    
    def get_logs(self, client_id: int, client_type: str, lines: int = 100) -> Dict[str, any]:
        """
        获取客户端容器日志
        
        Args:
            client_id: 客户端 ID
            client_type: 客户端类型
            lines: 返回的行数
            
        Returns:
            日志信息
        """
        container_name = self._get_container_name(client_id, client_type)
        
        try:
            # 获取容器日志
            result = subprocess.run(
                ["docker", "logs", "--tail", str(lines), container_name],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode != 0:
                if "No such container" in result.stderr:
                    return {
                        "client_id": client_id,
                        "logs": [],
                        "message": "容器不存在"
                    }
                return {
                    "client_id": client_id,
                    "logs": [],
                    "error": result.stderr.strip()
                }
            
            logs = result.stdout.strip().split('\n') if result.stdout.strip() else []
            return {
                "client_id": client_id,
                "container_name": container_name,
                "logs": logs,
                "lines": len(logs)
            }
            
        except subprocess.TimeoutExpired:
            return {
                "client_id": client_id,
                "logs": [],
                "error": "获取日志超时"
            }
        except Exception as e:
            logger.error(f"获取日志失败: {e}")
            return {
                "client_id": client_id,
                "logs": [],
                "error": str(e)
            }

