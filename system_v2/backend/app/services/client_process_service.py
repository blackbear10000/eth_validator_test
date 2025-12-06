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
    
    def _find_network_name(self) -> Optional[str]:
        """
        查找实际的网络名称
        
        Docker Compose 创建的网络可能带有前缀（如 infra_validator_network）
        或者可能使用不同的命名规则
        
        Returns:
            找到的网络名称，如果未找到则返回 None
        """
        # 首先尝试使用配置的网络名称
        try:
            result = subprocess.run(
                ["docker", "network", "inspect", self.network_name],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                logger.debug(f"找到网络: {self.network_name}")
                return self.network_name
        except Exception:
            pass
        
        # 尝试查找包含 "validator_network" 的网络
        try:
            result = subprocess.run(
                ["docker", "network", "ls", "--format", "{{.Name}}"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                networks = result.stdout.strip().split('\n')
                for network in networks:
                    if 'validator_network' in network.lower() or network == self.network_name:
                        logger.info(f"找到匹配的网络: {network}")
                        return network
        except Exception as e:
            logger.warning(f"查找网络失败: {e}")
        
        return None
    
    def _ensure_network_exists(self) -> bool:
        """
        确保 Docker 网络存在，如果不存在则创建
        
        Returns:
            网络是否存在或创建成功
        """
        # 首先尝试查找现有网络
        actual_network_name = self._find_network_name()
        if actual_network_name:
            # 如果找到的网络名称不同，更新 self.network_name
            if actual_network_name != self.network_name:
                logger.info(f"使用找到的网络名称: {actual_network_name} (原配置: {self.network_name})")
                self.network_name = actual_network_name
            return True
        
        # 网络不存在，尝试创建
        logger.info(f"网络 {self.network_name} 不存在，正在创建...")
        try:
            create_result = subprocess.run(
                ["docker", "network", "create", "--driver", "bridge", self.network_name],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if create_result.returncode == 0:
                logger.info(f"网络 {self.network_name} 创建成功")
                return True
            else:
                error_msg = create_result.stderr.strip() or create_result.stdout.strip()
                # 如果网络已存在（可能是并发创建），也算成功
                if "already exists" in error_msg.lower():
                    logger.debug(f"网络 {self.network_name} 已存在（可能是并发创建）")
                    return True
                logger.error(f"创建网络失败: {error_msg}")
                return False
                
        except subprocess.TimeoutExpired:
            logger.error(f"创建网络超时: {self.network_name}")
            return False
        except Exception as e:
            logger.error(f"创建网络失败: {e}")
            return False
    
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
                    
                    # 获取退出代码（如果容器已退出）
                    exit_code = None
                    if not is_running:
                        try:
                            inspect_result = subprocess.run(
                                ["docker", "inspect", "--format", "{{.State.ExitCode}}", container_name],
                                capture_output=True,
                                text=True,
                                timeout=5
                            )
                            if inspect_result.returncode == 0:
                                exit_code_str = inspect_result.stdout.strip()
                                if exit_code_str and exit_code_str != "<no value>":
                                    exit_code = int(exit_code_str)
                        except Exception as e:
                            logger.debug(f"获取退出代码失败: {e}")
                    
                    return {
                        "client_id": client_id,
                        "container_name": container_name,
                        "status": "running" if is_running else "stopped",
                        "state": state,
                        "status_string": status_str,
                        "is_running": is_running,
                        "exit_code": exit_code
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
        
        # 如果容器处于 Created 状态，先删除它
        try:
            inspect_result = subprocess.run(
                ["docker", "inspect", "--format", "{{.State.Status}}", container_name],
                capture_output=True,
                text=True,
                timeout=5
            )
            if inspect_result.returncode == 0:
                container_status = inspect_result.stdout.strip()
                if container_status == "created":
                    logger.info(f"发现处于 Created 状态的容器 {container_name}，正在删除...")
                    rm_result = subprocess.run(
                        ["docker", "rm", container_name],
                        capture_output=True,
                        text=True,
                        timeout=10
                    )
                    if rm_result.returncode != 0:
                        logger.warning(f"删除 Created 状态容器失败: {rm_result.stderr}")
        except Exception as e:
            logger.debug(f"检查容器状态时出错（可能容器不存在）: {e}")
        
        # 确保网络存在
        if not self._ensure_network_exists():
            return {
                "success": False,
                "message": f"无法确保网络 {self.network_name} 存在，请检查 Docker 网络配置"
            }
        
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
                
                # 验证配置文件是否存在（如果指定了配置文件）
                if config_file:
                    # config_file 是容器内路径（如 config.yaml），需要检查宿主机路径
                    config_file_host = os.path.join(config_dir_abs, config_file)
                    if not os.path.exists(config_file_host):
                        error_msg = f"配置文件不存在: {config_file_host} (容器内路径: /config/{config_file})"
                        logger.error(error_msg)
                        return {
                            "success": False,
                            "message": error_msg,
                            "config_file_path": config_file_host,
                            "config_dir": config_dir_abs
                        }
                    logger.info(f"验证配置文件存在: {config_file_host}")
                
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
            
            # 等待容器启动并验证状态
            time.sleep(3)
            
            # 检查容器实际状态
            final_status = self.get_status(client_id, client_type)
            is_running = final_status.get("is_running", False)
            container_state = final_status.get("state", "unknown")
            exit_code = final_status.get("exit_code")
            
            # 如果容器没有运行，获取错误日志
            error_logs = None
            if not is_running:
                try:
                    logs_result = subprocess.run(
                        ["docker", "logs", "--tail", "50", container_name],
                        capture_output=True,
                        text=True,
                        timeout=5
                    )
                    if logs_result.returncode == 0:
                        error_logs = logs_result.stdout.strip() or logs_result.stderr.strip()
                        logger.error(f"容器启动后退出，日志: {error_logs[:500]}")
                except Exception as e:
                    logger.warning(f"获取容器日志失败: {e}")
            
            # 如果容器退出，返回错误
            if not is_running:
                error_msg = f"容器启动后立即退出 (状态: {container_state}"
                if exit_code is not None:
                    error_msg += f", 退出代码: {exit_code}"
                error_msg += ")"
                
                return {
                    "success": False,
                    "message": error_msg,
                    "container_id": container_id,
                    "container_name": container_name,
                    "state": container_state,
                    "exit_code": exit_code,
                    "error_logs": error_logs,
                    "status": final_status
                }
            
            return {
                "success": True,
                "message": f"客户端 {client_id} 容器启动成功",
                "container_id": container_id,
                "container_name": container_name,
                "status": final_status
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
    
    def pause(self, client_id: int, client_type: str) -> Dict[str, any]:
        """
        暂停客户端 Docker 容器
        
        Args:
            client_id: 客户端 ID
            client_type: 客户端类型
            
        Returns:
            暂停结果
        """
        container_name = self._get_container_name(client_id, client_type)
        
        # 检查容器状态
        status = self.get_status(client_id, client_type)
        if not status.get("is_running"):
            return {
                "success": False,
                "message": f"客户端 {client_id} 容器未运行，无法暂停"
            }
        
        try:
            logger.info(f"暂停容器: {container_name}")
            result = subprocess.run(
                ["docker", "pause", container_name],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode != 0:
                error_msg = result.stderr.strip()
                logger.error(f"暂停容器失败: {error_msg}")
                return {
                    "success": False,
                    "message": f"暂停容器失败: {error_msg}"
                }
            
            return {
                "success": True,
                "message": f"客户端 {client_id} 已暂停"
            }
            
        except subprocess.TimeoutExpired:
            logger.error(f"暂停容器超时: {container_name}")
            return {
                "success": False,
                "message": "暂停容器超时"
            }
        except Exception as e:
            logger.error(f"暂停客户端 {client_id} 失败: {e}", exc_info=True)
            return {
                "success": False,
                "message": f"暂停失败: {str(e)}"
            }
    
    def unpause(self, client_id: int, client_type: str) -> Dict[str, any]:
        """
        恢复（取消暂停）客户端 Docker 容器
        
        Args:
            client_id: 客户端 ID
            client_type: 客户端类型
            
        Returns:
            恢复结果
        """
        container_name = self._get_container_name(client_id, client_type)
        
        try:
            logger.info(f"恢复容器: {container_name}")
            result = subprocess.run(
                ["docker", "unpause", container_name],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode != 0:
                error_msg = result.stderr.strip()
                logger.error(f"恢复容器失败: {error_msg}")
                return {
                    "success": False,
                    "message": f"恢复容器失败: {error_msg}"
                }
            
            return {
                "success": True,
                "message": f"客户端 {client_id} 已恢复"
            }
            
        except subprocess.TimeoutExpired:
            logger.error(f"恢复容器超时: {container_name}")
            return {
                "success": False,
                "message": "恢复容器超时"
            }
        except Exception as e:
            logger.error(f"恢复客户端 {client_id} 失败: {e}", exc_info=True)
            return {
                "success": False,
                "message": f"恢复失败: {str(e)}"
            }
    
    def destroy(self, client_id: int, client_type: str) -> Dict[str, any]:
        """
        销毁（停止并删除）客户端 Docker 容器
        
        Args:
            client_id: 客户端 ID
            client_type: 客户端类型
            
        Returns:
            销毁结果
        """
        container_name = self._get_container_name(client_id, client_type)
        
        try:
            # 先停止容器（如果正在运行）
            status = self.get_status(client_id, client_type)
            if status.get("is_running") or status.get("state") in ["running", "restarting"]:
                logger.info(f"停止容器: {container_name}")
                stop_result = subprocess.run(
                    ["docker", "stop", container_name],
                    capture_output=True,
                    text=True,
                    timeout=30
                )
                if stop_result.returncode != 0:
                    logger.warning(f"停止容器失败（可能已停止）: {stop_result.stderr}")
            
            # 删除容器
            logger.info(f"删除容器: {container_name}")
            rm_result = subprocess.run(
                ["docker", "rm", "-f", container_name],  # -f 强制删除，即使容器在运行
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if rm_result.returncode != 0:
                error_msg = rm_result.stderr.strip()
                # 如果容器不存在，也算成功
                if "No such container" in error_msg:
                    logger.debug(f"容器不存在: {container_name}")
                    return {
                        "success": True,
                        "message": f"客户端 {client_id} 容器不存在或已删除"
                    }
                logger.error(f"删除容器失败: {error_msg}")
                return {
                    "success": False,
                    "message": f"删除容器失败: {error_msg}"
                }
            
            return {
                "success": True,
                "message": f"客户端 {client_id} 容器已销毁"
            }
            
        except subprocess.TimeoutExpired:
            logger.error(f"销毁容器超时: {container_name}")
            return {
                "success": False,
                "message": "销毁容器超时"
            }
        except Exception as e:
            logger.error(f"销毁客户端 {client_id} 失败: {e}", exc_info=True)
            return {
                "success": False,
                "message": f"销毁失败: {str(e)}"
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
        
        注意：Prysm 官方镜像的 ENTRYPOINT 已经是 ["prysm", "validator"]，
        所以我们只需要传递参数，不需要再添加 "validator" 子命令。
        
        Args:
            client_type: 客户端类型
            config_file: 配置文件路径（容器内路径，如 /config/config.yaml）
            
        Returns:
            启动命令参数列表（不包含主命令）
        """
        client_type_lower = client_type.lower()
        
        if 'prysm' in client_type_lower:
            # Prysm 官方镜像 ENTRYPOINT 已经是 ["prysm", "validator"]
            # 我们只需要传递参数
            cmd = []
            if config_file:
                # 如果传入的是相对路径，转换为容器内绝对路径
                if not config_file.startswith('/'):
                    config_file = f"/config/{config_file}"
                cmd.extend(['--config-file', config_file])
            return cmd
        
        elif 'lighthouse' in client_type_lower:
            # Lighthouse 官方镜像可能需要完整命令
            cmd = ['validator']
            if config_file:
                if not config_file.startswith('/'):
                    config_file = f"/config/{config_file}"
                cmd.extend(['--config-file', config_file])
            return cmd
        
        elif 'teku' in client_type_lower:
            # Teku 官方镜像的 ENTRYPOINT 可能已经设置
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

