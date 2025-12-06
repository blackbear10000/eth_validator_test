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
        # 容器内路径到宿主机路径的映射
        # docker-compose.yml 中：./validator-clients/configs:/app/configs:rw
        self.container_to_host_path_map = {
            "/app/configs": "validator-clients/configs",
            "/app/validator-clients-data": "validator-clients/data"
        }
    
    def _convert_container_path_to_host(self, container_path: str) -> str:
        """
        将容器内路径转换为宿主机路径
        
        Args:
            container_path: 容器内路径（如 /app/configs/prysm/client1）
            
        Returns:
            宿主机路径（如 validator-clients/configs/prysm/client1）
        """
        if not container_path:
            return container_path
        
        # 如果是绝对路径且以 /app/configs 开头，转换为宿主机路径
        if container_path.startswith("/app/configs"):
            # 移除 /app/configs 前缀，添加 validator-clients/configs 前缀
            relative_path = container_path[len("/app/configs"):]
            # 移除开头的斜杠
            if relative_path.startswith("/"):
                relative_path = relative_path[1:]
            host_path = os.path.join("validator-clients", "configs", relative_path)
            logger.debug(f"路径转换: {container_path} -> {host_path}")
            return host_path
        
        # 如果是绝对路径且以 /app/validator-clients-data 开头
        if container_path.startswith("/app/validator-clients-data"):
            relative_path = container_path[len("/app/validator-clients-data"):]
            if relative_path.startswith("/"):
                relative_path = relative_path[1:]
            host_path = os.path.join("validator-clients", "data", relative_path)
            logger.debug(f"路径转换: {container_path} -> {host_path}")
            return host_path
        
        # 如果已经是相对路径或宿主机路径，直接返回
        return container_path
    
    def _find_infra_directory(self) -> Optional[str]:
        """
        查找 infra 目录的路径
        
        Returns:
            infra 目录的绝对路径，如果找不到则返回 None
        """
        # 尝试多个可能的路径
        possible_paths = [
            # 从 backend 容器内运行时
            # backend 在 /app，但 docker-compose.yml 在 system_v2/infra/
            # 所以需要从 /app 向上找到 system_v2，然后进入 infra
            "/app/../infra",  # 如果 backend 在 system_v2/backend，那么 ../infra 是 system_v2/infra
            "/app/../../infra",  # 如果 backend 在 system_v2/backend/app，那么 ../../infra 是 system_v2/infra
            # 从 backend/app/services 向上查找
            os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "infra"),
            # 从当前工作目录查找
            os.path.join(os.getcwd(), "infra"),
            os.path.join(os.getcwd(), "..", "infra"),
            os.path.join(os.getcwd(), "../infra"),
            # 相对路径
            "infra",
            "../infra",
            "../../infra",
        ]
        
        for path in possible_paths:
            try:
                abs_path = os.path.abspath(path)
                # 检查路径是否存在，并且包含 docker-compose.yml
                if os.path.exists(abs_path) and os.path.isdir(abs_path):
                    docker_compose_file = os.path.join(abs_path, "docker-compose.yml")
                    if os.path.exists(docker_compose_file):
                        logger.info(f"找到 infra 目录: {abs_path} (包含 docker-compose.yml)")
                        return abs_path
                    else:
                        logger.debug(f"目录存在但无 docker-compose.yml: {abs_path}")
            except Exception as e:
                logger.debug(f"检查路径失败 {path}: {e}")
                continue
        
        # 特殊处理：在容器内，/app/../infra 会被 os.path.abspath 解析为 /infra（错误）
        # 需要手动构建路径
        if os.path.exists("/app"):
            # 在容器内，backend 挂载在 /app
            # 由于 docker-compose 挂载 ../backend:/app，我们需要找到实际的 infra 目录
            # 但容器内无法直接知道，所以我们需要通过其他方式
            # 检查 /app/configs 是否存在（这是 docker-compose 挂载的）
            if os.path.exists("/app/configs"):
                # 在容器内，配置文件目录已经挂载到 /app/configs
                # 但我们需要找到 infra 目录来构建完整的宿主机路径
                # 由于 docker-compose 挂载 ./validator-clients/configs:/app/configs
                # 我们可以通过检查 /app/configs 的父目录来找到 infra
                # 但实际上，在容器内执行 docker run 时，我们需要的是宿主机路径
                # 所以我们需要从环境变量或配置中获取，或者使用相对路径
                logger.warning("在容器内运行，但无法直接找到 infra 目录")
                # 返回 None，让调用者使用备用逻辑
                return None
        
        logger.warning("未找到 infra 目录（包含 docker-compose.yml）")
        return None
    
    def _find_network_config_file(self) -> Optional[str]:
        """
        查找 network-config.yaml 文件路径
        
        文件应该已经通过 docker-compose.yml 挂载到 backend 容器的 /kurtosis-config/network-config.yaml
        
        Returns:
            network-config.yaml 文件的路径（容器内路径或宿主机路径）
        """
        # 方法1: 检查容器内挂载的文件（最优先）
        # docker-compose.yml 挂载 ../../infra/kurtosis:/kurtosis-config:ro
        container_path = "/kurtosis-config/network-config.yaml"
        if os.path.exists(container_path):
            logger.info(f"✅ 找到 network-config.yaml (容器内挂载): {container_path}")
            return container_path
        
        # 方法2: 如果不在容器内，从 INFRA_DIR 推断项目根目录
        infra_dir_env = os.getenv("INFRA_DIR")
        if infra_dir_env:
            # INFRA_DIR 通常是 system_v2/infra，向上找到项目根目录
            project_root = os.path.dirname(os.path.dirname(os.path.abspath(infra_dir_env)))
            host_path = os.path.join(project_root, "infra", "kurtosis", "network-config.yaml")
            if os.path.exists(host_path):
                logger.info(f"✅ 找到 network-config.yaml (从 INFRA_DIR 推断): {host_path}")
                return host_path
        
        # 方法3: 从 _find_infra_directory() 推断
        infra_dir = self._find_infra_directory()
        if infra_dir:
            project_root = os.path.dirname(os.path.dirname(os.path.abspath(infra_dir)))
            host_path = os.path.join(project_root, "infra", "kurtosis", "network-config.yaml")
            if os.path.exists(host_path):
                logger.info(f"✅ 找到 network-config.yaml (从 infra 目录推断): {host_path}")
                return host_path
        
        logger.error("❌ 未找到 network-config.yaml 文件")
        logger.error("   请确保文件存在于 infra/kurtosis/network-config.yaml")
        logger.error("   或在 docker-compose.yml 中挂载 kurtosis-config 目录")
        return None
    
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
        config_dir: Optional[str] = None,
        web3signer_url: Optional[str] = None,
        pubkeys: Optional[List[str]] = None,
        grpc_endpoint: Optional[str] = None
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
            
            # 添加 host.docker.internal 支持（Linux 系统需要）
            # 在 macOS/Windows 上，Docker Desktop 自动提供 host.docker.internal
            # 在 Linux 上，需要手动添加 --add-host 参数
            cmd.extend(["--add-host", "host.docker.internal:host-gateway"])
            logger.debug("已添加 host.docker.internal 主机映射（Linux 兼容性）")
            
            # 配置文件挂载
            if config_dir:
                # 将容器内路径转换为宿主机路径
                config_dir_host = self._convert_container_path_to_host(config_dir)
                logger.info(f"配置文件路径转换: {config_dir} -> {config_dir_host}")
                
                # 确保使用绝对路径（相对于 docker-compose.yml 所在目录）
                # docker-compose.yml 在 system_v2/infra/ 目录
                # 配置文件应该在 system_v2/infra/validator-clients/configs/...
                if not os.path.isabs(config_dir_host):
                    # 查找 infra 目录
                    infra_dir = self._find_infra_directory()
                    
                    if infra_dir:
                        # 使用 infra 目录作为基准路径
                        # 确保 infra_dir 是绝对路径
                        infra_dir_abs = os.path.abspath(infra_dir)
                        config_dir_abs = os.path.join(infra_dir_abs, config_dir_host)
                        config_dir_abs = os.path.abspath(config_dir_abs)
                        logger.info(f"使用 infra 目录作为基准: {infra_dir_abs}, 配置文件目录: {config_dir_abs}")
                    else:
                        # 如果找不到 infra 目录，需要特殊处理
                        # 在容器内，/app/../infra 会被 os.path.abspath 解析为 /infra（错误）
                        # 我们需要使用不同的方法
                        
                        cwd = os.getcwd()
                        logger.warning(f"未找到 infra 目录，当前工作目录: {cwd}")
                        
                        # 关键问题：在容器内执行 docker run 时
                        # Docker 会从宿主机路径解析挂载路径
                        # 所以我们需要宿主机路径，但我们在容器内
                        
                        # 解决方案：使用 docker inspect 查找 backend 容器的挂载点
                        # 或者，通过检查 /app/configs 的挂载信息
                        # 或者，使用环境变量
                        
                        # 方法1: 检查环境变量
                        infra_path_env = os.getenv("INFRA_DIR")
                        if infra_path_env:
                            config_dir_abs = os.path.join(infra_path_env, config_dir_host)
                            config_dir_abs = os.path.abspath(config_dir_abs)
                            logger.info(f"从环境变量 INFRA_DIR 获取: {infra_path_env}, 配置文件目录: {config_dir_abs}")
                        else:
                            # 方法2: 在容器内，通过 docker inspect 查找挂载点
                            # 查找 backend 容器的挂载信息
                            try:
                                inspect_result = subprocess.run(
                                    ["docker", "inspect", "--format", "{{range .Mounts}}{{.Source}} {{.Destination}}\n{{end}}", "backend"],
                                    capture_output=True,
                                    text=True,
                                    timeout=5
                                )
                                if inspect_result.returncode == 0:
                                    # 解析挂载信息，找到 validator-clients/configs 的挂载点
                                    mounts = inspect_result.stdout.strip().split('\n')
                                    found_mount = False
                                    for mount in mounts:
                                        if mount and 'validator-clients/configs' in mount:
                                            parts = mount.split()
                                            if len(parts) >= 2:
                                                host_path = parts[0]  # 宿主机路径
                                                # 提取 infra 目录（validator-clients/configs 的父目录）
                                                if host_path.endswith('/validator-clients/configs') or host_path.endswith('\\validator-clients\\configs'):
                                                    infra_dir = os.path.dirname(host_path)
                                                    config_dir_abs = os.path.join(infra_dir, config_dir_host)
                                                    config_dir_abs = os.path.abspath(config_dir_abs)
                                                    logger.info(f"从 Docker 挂载信息找到 infra 目录: {infra_dir}, 配置文件目录: {config_dir_abs}")
                                                    found_mount = True
                                                    break
                                    
                                    if not found_mount:
                                        # 如果没找到，使用备用方法
                                        raise ValueError("未找到挂载信息")
                            except Exception as e:
                                logger.warning(f"无法从 Docker 挂载信息获取路径: {e}")
                                # 方法3: 使用相对路径，但需要确保 docker run 在正确的目录执行
                                # 由于我们无法可靠地找到 infra 目录，返回错误
                                error_msg = (
                                    f"无法找到 infra 目录来解析配置文件路径。"
                                    f"请设置 INFRA_DIR 环境变量指向 docker-compose.yml 所在目录。"
                                    f"当前工作目录: {cwd}, 配置文件路径: {config_dir_host}"
                                )
                                logger.error(error_msg)
                                return {
                                    "success": False,
                                    "message": error_msg,
                                    "config_dir": config_dir,
                                    "config_dir_host": config_dir_host,
                                    "suggestion": "设置 INFRA_DIR 环境变量，例如: export INFRA_DIR=/path/to/system_v2/infra"
                                }
                else:
                    config_dir_abs = config_dir_host
                
                # 确保目录存在
                if not os.path.exists(config_dir_abs):
                    logger.warning(f"配置文件目录不存在，将创建: {config_dir_abs}")
                    try:
                        os.makedirs(config_dir_abs, exist_ok=True)
                    except Exception as e:
                        logger.error(f"创建配置文件目录失败: {config_dir_abs}, 错误: {e}")
                        return {
                            "success": False,
                            "message": f"无法创建配置文件目录: {config_dir_abs}",
                            "error": str(e)
                        }
                
                # 验证配置文件是否存在（如果指定了配置文件）
                if config_file:
                    # config_file 是文件名（如 config.yaml）
                    # 在容器内，我们需要检查容器内的路径（/app/configs/...）
                    # 而不是宿主机路径，因为容器内无法直接访问宿主机文件系统
                    config_file_host = os.path.join(config_dir_abs, config_file)
                    
                    # 检查文件是否存在（在容器内或宿主机上）
                    file_exists = False
                    if os.path.exists("/app"):
                        # 在容器内，检查容器内的路径
                        # config_dir 是容器内路径（如 /app/configs/prysm/vc-5）
                        # 转换为容器内路径进行检查
                        if config_dir.startswith("/app/configs"):
                            container_config_file = os.path.join(config_dir, config_file)
                            file_exists = os.path.exists(container_config_file)
                            if file_exists:
                                logger.info(f"在容器内找到配置文件: {container_config_file}")
                            else:
                                logger.warning(f"在容器内未找到配置文件: {container_config_file}")
                        else:
                            # 如果 config_dir 不是容器内路径，尝试检查宿主机路径
                            # 但这在容器内可能失败
                            file_exists = os.path.exists(config_file_host)
                    else:
                        # 在宿主机上，直接检查宿主机路径
                        file_exists = os.path.exists(config_file_host)
                    
                    if not file_exists:
                        # 如果文件不存在，列出目录内容用于调试
                        try:
                            # 尝试检查容器内路径
                            if os.path.exists("/app") and config_dir.startswith("/app/configs"):
                                container_dir = config_dir
                            else:
                                container_dir = config_dir_abs
                            
                            if os.path.exists(container_dir):
                                files = os.listdir(container_dir)
                                logger.error(f"配置文件目录内容 ({container_dir}): {files}")
                            else:
                                logger.error(f"配置文件目录不存在: {container_dir}")
                        except Exception as e:
                            logger.warning(f"无法列出目录内容: {e}")
                        
                        # 在容器内，如果文件在容器内路径存在，我们仍然可以继续
                        # 因为挂载会确保文件在容器内可见
                        if os.path.exists("/app") and config_dir.startswith("/app/configs"):
                            container_config_file = os.path.join(config_dir, config_file)
                            if os.path.exists(container_config_file):
                                logger.info(f"在容器内找到配置文件，继续启动: {container_config_file}")
                                file_exists = True
                        
                        if not file_exists:
                            error_msg = (
                                f"配置文件不存在: {config_file_host} "
                                f"(容器内路径: /config/{config_file}, "
                                f"原始路径: {config_dir})"
                            )
                            logger.error(error_msg)
                            return {
                                "success": False,
                                "message": error_msg,
                                "config_file_path": config_file_host,
                                "config_dir": config_dir_abs,
                                "container_path": f"/config/{config_file}"
                            }
                    
                    logger.info(f"验证配置文件存在: {config_file_host} (容器内: /config/{config_file})")
                
                # 挂载为读写模式，因为 Prysm 等客户端需要写入 pubkey_persistence.txt
                cmd.extend(["-v", f"{config_dir_abs}:/config:rw"])
                logger.info(f"挂载配置目录: {config_dir_abs} -> /config (原始路径: {config_dir}, 读写模式)")
            
            # 挂载网络配置文件（用于 Prysm 等客户端）
            network_config_path = self._find_network_config_file()
            if network_config_path:
                # 如果是容器内路径（/kurtosis-config/network-config.yaml），需要通过 docker inspect 找到宿主机路径
                if network_config_path.startswith("/kurtosis-config"):
                    # 通过 docker inspect 查找 backend 容器的 /kurtosis-config 挂载点对应的宿主机路径
                    try:
                        inspect_result = subprocess.run(
                            ["docker", "inspect", "--format", "{{range .Mounts}}{{if eq .Destination \"/kurtosis-config\"}}{{.Source}}{{end}}{{end}}", "backend"],
                            capture_output=True,
                            text=True,
                            timeout=5
                        )
                        if inspect_result.returncode == 0 and inspect_result.stdout.strip():
                            mount_source = inspect_result.stdout.strip()
                            host_path = os.path.join(mount_source, "network-config.yaml")
                            if os.path.exists(host_path):
                                cmd.extend(["-v", f"{host_path}:/network-config.yaml:ro"])
                                logger.info(f"✅ 挂载网络配置文件: {host_path} -> /network-config.yaml")
                            else:
                                logger.error(f"❌ 宿主机路径不存在: {host_path}")
                                logger.error(f"   挂载源目录: {mount_source}")
                        else:
                            logger.error("❌ 无法从 Docker 挂载信息获取 kurtosis-config 的宿主机路径")
                            # 回退到使用 INFRA_DIR 推断
                            infra_dir = os.getenv("INFRA_DIR")
                            if infra_dir:
                                project_root = os.path.dirname(os.path.dirname(os.path.abspath(infra_dir)))
                                host_path = os.path.join(project_root, "infra", "kurtosis", "network-config.yaml")
                                logger.warning(f"⚠️ 回退到使用 INFRA_DIR 推断路径: {host_path}")
                                if os.path.exists(host_path):
                                    cmd.extend(["-v", f"{host_path}:/network-config.yaml:ro"])
                                    logger.info(f"✅ 挂载网络配置文件: {host_path} -> /network-config.yaml")
                                else:
                                    logger.error(f"❌ 推断的宿主机路径也不存在: {host_path}")
                    except Exception as e:
                        logger.error(f"❌ 无法查找 kurtosis-config 挂载点: {e}")
                        # 回退到使用 INFRA_DIR 推断
                        infra_dir = os.getenv("INFRA_DIR")
                        if infra_dir:
                            project_root = os.path.dirname(os.path.dirname(os.path.abspath(infra_dir)))
                            host_path = os.path.join(project_root, "infra", "kurtosis", "network-config.yaml")
                            logger.warning(f"⚠️ 回退到使用 INFRA_DIR 推断路径: {host_path}")
                            if os.path.exists(host_path):
                                cmd.extend(["-v", f"{host_path}:/network-config.yaml:ro"])
                                logger.info(f"✅ 挂载网络配置文件: {host_path} -> /network-config.yaml")
                            else:
                                logger.error(f"❌ 推断的宿主机路径也不存在: {host_path}")
                else:
                    # 宿主机路径，直接使用
                    cmd.extend(["-v", f"{network_config_path}:/network-config.yaml:ro"])
                    logger.info(f"✅ 挂载网络配置文件: {network_config_path} -> /network-config.yaml")
            else:
                logger.error("❌ 未找到 network-config.yaml 文件，Prysm 将无法正确配置网络参数")
                logger.error("   这可能导致 'start slot is smaller than minimum valid start slot' 错误")
                # 不阻止容器启动，但记录严重警告
            
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
            # 对于 Prysm，如果 grpc_endpoint 未提供，尝试从配置文件读取
            grpc_endpoint_for_cmd = grpc_endpoint
            if not grpc_endpoint_for_cmd and 'prysm' in client_type.lower() and config_file and config_dir:
                try:
                    import yaml
                    config_file_basename = os.path.basename(config_file) if '/' in config_file else config_file
                    config_path = os.path.join(config_dir, config_file_basename)
                    if os.path.exists(config_path):
                        with open(config_path, 'r') as f:
                            config_data = yaml.safe_load(f)
                            if config_data and 'beacon-chain' in config_data:
                                grpc_endpoint_for_cmd = config_data['beacon-chain'].get('rpc-host')
                                logger.info(f"[Prysm 启动] 从配置文件读取 gRPC 端点: {grpc_endpoint_for_cmd}")
                except Exception as e:
                    logger.debug(f"[Prysm 启动] 无法从配置文件读取 gRPC 端点: {e}")
            
            container_cmd = self._build_container_command(
                client_type, 
                config_file,
                web3signer_url=web3signer_url,
                pubkeys=pubkeys or [],
                grpc_endpoint=grpc_endpoint_for_cmd
            )
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
    
    def _force_remove_container(self, container_name: str) -> bool:
        """
        强制删除容器（处理各种异常状态）
        
        Args:
            container_name: 容器名称
            
        Returns:
            是否成功删除
        """
        # 尝试多种方法删除容器
        methods = [
            # 方法1: 标准删除
            ["docker", "rm", "-f", container_name],
            # 方法2: 使用 --force 参数（某些 Docker 版本）
            ["docker", "rm", "--force", container_name],
            # 方法3: 先 kill 再删除
            ["docker", "kill", container_name],
        ]
        
        for method in methods:
            try:
                result = subprocess.run(
                    method,
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                if result.returncode == 0:
                    logger.info(f"容器删除成功: {container_name} (方法: {' '.join(method)})")
                    return True
                # 如果容器不存在，也算成功
                if "No such container" in result.stderr:
                    logger.debug(f"容器不存在: {container_name}")
                    return True
            except subprocess.TimeoutExpired:
                logger.warning(f"删除容器超时: {container_name} (方法: {' '.join(method)})")
                continue
            except Exception as e:
                logger.warning(f"删除容器失败: {e} (方法: {' '.join(method)})")
                continue
        
        return False
    
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
            # 先检查容器状态
            status = self.get_status(client_id, client_type)
            container_state = status.get("state", "unknown")
            
            # 如果容器在运行，先停止
            if status.get("is_running") or container_state in ["running", "restarting"]:
                logger.info(f"停止容器: {container_name} (状态: {container_state})")
                stop_result = subprocess.run(
                    ["docker", "stop", container_name],
                    capture_output=True,
                    text=True,
                    timeout=30
                )
                if stop_result.returncode != 0:
                    logger.warning(f"停止容器失败（可能已停止）: {stop_result.stderr}")
                    # 即使停止失败，也继续尝试删除
            
            # 强制删除容器（处理各种异常状态）
            logger.info(f"删除容器: {container_name} (状态: {container_state})")
            if self._force_remove_container(container_name):
                return {
                    "success": True,
                    "message": f"客户端 {client_id} 容器已销毁"
                }
            else:
                # 最后检查容器是否真的还存在
                final_status = self.get_status(client_id, client_type)
                if "container_name" not in final_status:
                    # 容器不存在，算成功
                    logger.info(f"容器已不存在: {container_name}")
                    return {
                        "success": True,
                        "message": f"客户端 {client_id} 容器已删除或不存在"
                    }
                
                error_msg = f"无法删除容器 {container_name}，当前状态: {final_status.get('state', 'unknown')}"
                logger.error(error_msg)
                return {
                    "success": False,
                    "message": error_msg,
                    "container_state": final_status.get("state"),
                    "suggestion": "请手动检查容器状态: docker ps -a | grep " + container_name
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
        config_file: Optional[str] = None,
        web3signer_url: Optional[str] = None,
        pubkeys: Optional[List[str]] = None,
        grpc_endpoint: Optional[str] = None
    ) -> List[str]:
        """
        构建容器内启动命令
        
        注意：Prysm 官方镜像的 ENTRYPOINT 已经是 ["prysm", "validator"]，
        所以我们只需要传递参数，不需要再添加 "validator" 子命令。
        
        Args:
            client_type: 客户端类型
            config_file: 配置文件路径（容器内路径，如 /config/config.yaml）
            web3signer_url: Web3Signer URL
            pubkeys: 公钥列表（可选，如果不设置则等待通过 Remote Keymanager API 设置）
            
        Returns:
            启动命令参数列表（不包含主命令）
        """
        client_type_lower = client_type.lower()
        pubkeys = pubkeys or []
        
        if 'prysm' in client_type_lower:
            # Prysm 官方镜像 ENTRYPOINT 已经是 ["prysm", "validator"]
            # 我们只需要传递参数
            cmd = []
            
            # 接受使用条款（非交互式环境必需）
            cmd.append('--accept-terms-of-use')
            
            # 网络配置文件（关键！用于配置 fork version、genesis time 等网络参数）
            # 这个文件必须与 dev net 的网络配置匹配，否则会出现 slot 不匹配错误
            # 注意：如果文件未挂载，Prysm 会报错，但我们已经在上面的挂载逻辑中处理了
            cmd.extend(['--chain-config-file', '/network-config.yaml'])
            logger.info(f"[Prysm 启动] 使用网络配置文件: /network-config.yaml")
            
            # gRPC 端点配置（优先通过命令行参数传递，更可靠）
            # 根据 Prysm 文档，--beacon-rpc-provider 参数支持在 validator 命令中使用
            # 默认值是 127.0.0.1:4000，所以必须显式传递正确的值
            if grpc_endpoint:
                # 确保格式正确（host:port，不是 URL）
                grpc_endpoint_clean = grpc_endpoint
                if '://' in grpc_endpoint_clean:
                    grpc_endpoint_clean = grpc_endpoint_clean.replace('http://', '').replace('https://', '')
                cmd.extend(['--beacon-rpc-provider', grpc_endpoint_clean])
                logger.info(f"[Prysm 启动] 通过命令行参数设置 gRPC 端点: {grpc_endpoint_clean}")
            else:
                logger.warning(f"[Prysm 启动] ⚠️  未提供 gRPC 端点，Prysm 将使用默认值 127.0.0.1:4000")
            
            # 配置文件（如果提供）
            if config_file:
                # 如果传入的是相对路径，转换为容器内绝对路径
                if not config_file.startswith('/'):
                    config_file = f"/config/{config_file}"
                cmd.extend(['--config-file', config_file])
                logger.info(f"[Prysm 启动] 使用配置文件: {config_file}")
            
            # Web3Signer 配置
            if web3signer_url:
                cmd.extend(['--validators-external-signer-url', web3signer_url])
                logger.info(f"[Prysm 启动] Web3Signer URL: {web3signer_url}")
            
            # 公钥列表（可选）
            if pubkeys:
                # 格式化公钥列表（逗号分隔）
                pubkeys_clean = []
                for pubkey in pubkeys:
                    pubkey_clean = pubkey.lower().strip()
                    if not pubkey_clean.startswith('0x'):
                        pubkey_clean = f"0x{pubkey_clean}"
                    pubkeys_clean.append(pubkey_clean)
                pubkeys_str = ','.join(pubkeys_clean)
                cmd.extend(['--validators-external-signer-public-keys', pubkeys_str])
                logger.info(f"[Prysm 启动] 公钥数量: {len(pubkeys_clean)}")
            
            # 启用 Remote Keymanager API
            cmd.append('--web')
            
            # Public Key Persistence 文件路径
            cmd.extend(['--validators-external-signer-key-file', '/config/pubkey_persistence.txt'])
            
            # Wallet 目录（用于 auth-token，即使不使用本地钱包）
            cmd.extend(['--wallet-dir', '/wallet'])
            
            logger.info(f"[Prysm 启动] 最终启动命令参数: {' '.join(cmd)}")
            return cmd
        
        elif 'lighthouse' in client_type_lower:
            # Lighthouse 官方镜像可能需要完整命令
            cmd = ['validator']
            
            # 配置文件（如果提供）
            if config_file:
                if not config_file.startswith('/'):
                    config_file = f"/config/{config_file}"
                cmd.extend(['--config-file', config_file])
            
            # Web3Signer 配置
            if web3signer_url:
                cmd.extend(['--validators-external-signer-url', web3signer_url])
            
            # 公钥列表（可选）
            if pubkeys:
                pubkeys_clean = []
                for pubkey in pubkeys:
                    pubkey_clean = pubkey.lower().strip()
                    if not pubkey_clean.startswith('0x'):
                        pubkey_clean = f"0x{pubkey_clean}"
                    pubkeys_clean.append(pubkey_clean)
                pubkeys_str = ','.join(pubkeys_clean)
                cmd.extend(['--validators-external-signer-public-keys', pubkeys_str])
            
            # Lighthouse 的 Remote Keymanager API 通常通过 HTTP API 端口启用
            # 已在配置文件中设置 http.port = 5062
            
            return cmd
        
        elif 'teku' in client_type_lower:
            # Teku 官方镜像的 ENTRYPOINT 可能已经设置
            cmd = []
            
            # 配置文件（如果提供）
            if config_file:
                if not config_file.startswith('/'):
                    config_file = f"/config/{config_file}"
                cmd.extend(['--config-file', config_file])
            
            # Web3Signer 配置
            if web3signer_url:
                cmd.extend(['--validators-external-signer-url', web3signer_url])
            
            # 公钥列表（可选）
            if pubkeys:
                pubkeys_clean = []
                for pubkey in pubkeys:
                    pubkey_clean = pubkey.lower().strip()
                    if not pubkey_clean.startswith('0x'):
                        pubkey_clean = f"0x{pubkey_clean}"
                    pubkeys_clean.append(pubkey_clean)
                pubkeys_str = ','.join(pubkeys_clean)
                cmd.extend(['--validators-external-signer-public-keys', pubkeys_str])
            
            # Teku 的 Remote Keymanager API 通过 REST API 启用
            # 已在配置文件中设置 beacon.beacon-rest-api-enabled = true
            
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

