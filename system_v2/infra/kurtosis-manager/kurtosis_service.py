"""
Kurtosis 服务封装
封装 Kurtosis CLI 调用逻辑
"""
import os
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
        self._engine_restart_attempted = False  # 标记是否已尝试重启 engine
        
        # 验证 Kurtosis CLI 是否可用
        self._verify_kurtosis_cli()
        
        # 禁用 analytics/metrics（避免网络连接问题）
        self._disable_analytics()
        
        # 检查并启动 Kurtosis engine（如果需要）
        # 注意：不强制要求 engine 运行，因为某些操作可能不需要 engine
        self._ensure_engine_running()
    
    def _verify_kurtosis_cli(self) -> bool:
        """
        验证 Kurtosis CLI 是否可用
        
        Returns:
            是否可用
        """
        try:
            import shutil
            kurtosis_path = shutil.which("kurtosis")
            if kurtosis_path:
                logger.info(f"找到 Kurtosis CLI: {kurtosis_path}")
                # 尝试运行 version 命令验证（设置环境变量禁用 telemetry）
                env = os.environ.copy()
                env['KURTOSIS_DISABLE_TELEMETRY'] = 'true'
                env['KURTOSIS_DISABLE_ANALYTICS'] = 'true'
                env['KURTOSIS_DISABLE_METRICS'] = 'true'
                
                result = subprocess.run(
                    ["kurtosis", "version"],
                    capture_output=True,
                    text=True,
                    timeout=10,
                    env=env
                )
                if result.returncode == 0:
                    logger.info(f"Kurtosis CLI 版本: {result.stdout.strip()}")
                    return True
                else:
                    logger.warning(f"Kurtosis CLI 版本检查失败: {result.stderr}")
                    return False
            else:
                logger.error("Kurtosis CLI 未在 PATH 中找到")
                # 尝试检查常见安装位置（apt 安装通常在 /usr/bin/kurtosis）
                common_paths = [
                    "/usr/bin/kurtosis",  # apt 安装位置
                    "/usr/local/bin/kurtosis",
                    "/root/.kurtosis/bin/kurtosis",  # 脚本安装位置
                ]
                for path in common_paths:
                    if Path(path).exists():
                        logger.warning(f"Kurtosis CLI 在 {path} 但不在 PATH 中，请检查环境变量")
                        return False
                return False
        except Exception as e:
            logger.error(f"验证 Kurtosis CLI 时出错: {e}", exc_info=True)
            return False
    
    def _disable_analytics(self) -> bool:
        """
        禁用 Kurtosis analytics/metrics
        
        Returns:
            是否成功
        """
        try:
            logger.info("禁用 Kurtosis analytics...")
            kurtosis_path = self._get_kurtosis_path()
            
            # 直接调用 subprocess，不通过 _run_kurtosis_command（避免循环）
            # 使用环境变量禁用 telemetry/metrics
            env = os.environ.copy()
            env['KURTOSIS_DISABLE_TELEMETRY'] = 'true'
            env['KURTOSIS_DISABLE_ANALYTICS'] = 'true'
            env['KURTOSIS_DISABLE_METRICS'] = 'true'
            
            # 尝试使用 kurtosis analytics disable 命令
            result = subprocess.run(
                [kurtosis_path, "analytics", "disable"],
                capture_output=True,
                text=True,
                timeout=10,
                env=env
            )
            
            if result.returncode == 0:
                logger.info("Kurtosis analytics 已禁用")
                return True
            else:
                # 如果命令不存在或失败，记录警告但继续（环境变量应该足够）
                logger.warning(f"禁用 analytics 命令失败（可能不支持）: {result.stderr[:200]}")
                logger.info("将使用环境变量禁用 metrics")
                return False
        except Exception as e:
            logger.warning(f"禁用 analytics 时出错: {e}，将使用环境变量")
            return False
    
    def _check_engine_container_status(self) -> Dict[str, Any]:
        """
        检查 engine 容器的实际状态（通过 Docker）
        
        Returns:
            容器状态信息
        """
        try:
            import docker
            client = docker.from_env()
            
            # 查找 kurtosis engine 容器
            containers = client.containers.list(all=True, filters={"name": "kurtosis-engine"})
            
            if not containers:
                return {"found": False, "message": "未找到 engine 容器"}
            
            container = containers[0]
            status = {
                "found": True,
                "id": container.id[:12],
                "status": container.status,
                "name": container.name,
            }
            
            # 检查容器健康状态
            if hasattr(container, 'attrs') and 'State' in container.attrs:
                state = container.attrs['State']
                status["running"] = state.get('Running', False)
                status["restarting"] = state.get('Restarting', False)
                status["exit_code"] = state.get('ExitCode', 0)
                status["error"] = state.get('Error', '')
            
            # 检查端口映射
            if hasattr(container, 'attrs') and 'NetworkSettings' in container.attrs:
                ports = container.attrs.get('NetworkSettings', {}).get('Ports', {})
                status["ports"] = ports
            
            return status
        except ImportError:
            logger.debug("docker Python 库未安装，跳过容器状态检查")
            return {"found": None, "message": "无法检查容器状态（docker 库未安装）"}
        except Exception as e:
            logger.debug(f"检查容器状态时出错: {e}")
            return {"found": None, "message": f"检查失败: {str(e)}"}
    
    def _ensure_engine_running(self) -> bool:
        """
        确保 Kurtosis engine 正在运行
        
        注意：不强制要求 engine 运行，因为某些操作可能不需要 engine。
        如果 engine 无法启动，服务仍然可以启动，只是某些功能可能不可用。
        
        改进：
        1. 使用实际命令测试 engine 可用性
        2. 检查 engine 容器的实际状态
        3. 如果容器在运行但无法连接，提供诊断信息
        
        Returns:
            是否成功
        """
        try:
            # 首先检查 engine 容器的实际状态
            container_status = self._check_engine_container_status()
            if container_status.get("found") is True:
                logger.info(f"Engine 容器状态: {container_status.get('status')}, 运行中: {container_status.get('running')}")
                if container_status.get("restarting"):
                    logger.warning("Engine 容器正在重启中，可能存在问题")
            
            # 尝试执行一个简单的测试命令来验证 engine 是否真的可用
            logger.info("验证 Kurtosis engine 是否可用...")
            test_success, test_stdout, test_stderr = self._run_kurtosis_command(
                ["enclave", "ls"], 
                timeout=15
            )
            
            if test_success:
                logger.info("Kurtosis engine 可用且响应正常")
                return True
            
            # 测试命令失败
            error_msg = (test_stdout + test_stderr).lower()
            full_error = test_stderr[:500] if test_stderr else test_stdout[:500]
            
            logger.warning(f"Engine 测试失败: {full_error}")
            
            # 如果容器在运行但无法连接，提供诊断信息
            if container_status.get("found") is True and container_status.get("running"):
                logger.warning("Engine 容器在运行，但 CLI 无法连接。可能的原因：")
                logger.warning("  1. Engine 服务器进程未正常启动")
                logger.warning("  2. 端口映射问题")
                logger.warning("  3. 网络连接问题")
                logger.warning(f"  容器状态: {container_status}")
                
                # 尝试检查 engine 容器的日志
                try:
                    import docker
                    client = docker.from_env()
                    containers = client.containers.list(all=True, filters={"name": "kurtosis-engine"})
                    if containers:
                        container = containers[0]
                        logs = container.logs(tail=20).decode('utf-8', errors='ignore')
                        logger.info(f"Engine 容器最近日志:\n{logs}")
                except Exception as e:
                    logger.debug(f"无法获取 engine 容器日志: {e}")
            
            # 检查是否是 engine 相关错误
            if "engine" in error_msg or "server isn't responding" in error_msg or "creating a new" in error_msg:
                logger.warning("检测到 Kurtosis engine 连接问题")
                
                # 只尝试一次重启，避免无限循环
                if not self._engine_restart_attempted:
                    self._engine_restart_attempted = True
                    logger.info("尝试重启 engine...")
                    
                    # 尝试重启
                    kurtosis_path = self._get_kurtosis_path()
                    env = os.environ.copy()
                    env['KURTOSIS_DISABLE_TELEMETRY'] = 'true'
                    env['KURTOSIS_DISABLE_ANALYTICS'] = 'true'
                    env['KURTOSIS_DISABLE_METRICS'] = 'true'
                    
                    try:
                        restart_result = subprocess.run(
                            [kurtosis_path, "engine", "restart"],
                            capture_output=True,
                            text=True,
                            timeout=60,
                            env=env
                        )
                        
                        if restart_result.returncode == 0:
                            logger.info("Engine 重启命令执行成功，等待几秒后验证...")
                            import time
                            time.sleep(10)  # 等待 engine 完全启动（增加等待时间）
                            
                            # 再次检查容器状态
                            container_status_after = self._check_engine_container_status()
                            logger.info(f"重启后容器状态: {container_status_after}")
                            
                            # 再次验证
                            verify_success, _, _ = self._run_kurtosis_command(
                                ["enclave", "ls"], 
                                timeout=15
                            )
                            if verify_success:
                                logger.info("Engine 重启后验证成功")
                                return True
                            else:
                                logger.warning("Engine 重启后仍然无法响应")
                        else:
                            logger.warning(f"Engine 重启失败: {restart_result.stderr[:300]}")
                    except Exception as restart_error:
                        logger.warning(f"尝试重启 engine 时出错: {restart_error}")
                else:
                    logger.info("已尝试过重启 engine，跳过以避免循环")
            
            # Engine 无法启动或不可用，但不阻止服务启动
            # 注意：即使 engine 不可用，CLI 仍然可以通过 Docker socket 管理容器
            # 只是某些需要 engine API 的功能可能不可用
            logger.info("Kurtosis engine 当前不可用，服务将继续运行（某些功能可能受限）")
            logger.info("提示：如果 engine 容器在运行但无响应，可以尝试手动重启：")
            logger.info("  docker restart <engine-container-name>")
            logger.info("或者检查 engine 容器日志：")
            logger.info("  docker logs <engine-container-name> --tail=50")
            return False
            
        except Exception as e:
            logger.warning(f"检查 Kurtosis engine 状态时出错: {e}")
            # 不阻止服务启动
            return False
    
    def _get_kurtosis_path(self) -> str:
        """
        获取 Kurtosis CLI 路径
        
        Returns:
            Kurtosis CLI 路径
        """
        import shutil
        kurtosis_path = shutil.which("kurtosis")
        if kurtosis_path:
            return kurtosis_path
        
        # 尝试常见安装位置（apt 安装通常在 /usr/bin/kurtosis）
        common_paths = [
            "/usr/bin/kurtosis",  # apt 安装位置
            "/usr/local/bin/kurtosis",
            "/root/.kurtosis/bin/kurtosis",  # 脚本安装位置
        ]
        for path in common_paths:
            if Path(path).exists():
                return path
        
        return "kurtosis"  # 默认值，如果找不到会抛出 FileNotFoundError
    
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
            kurtosis_path = self._get_kurtosis_path()
            logger.info(f"执行 Kurtosis 命令: {kurtosis_path} {' '.join(command)}")
            
            # 设置环境变量以禁用 telemetry/metrics（避免网络连接问题）
            env = os.environ.copy()
            env['KURTOSIS_DISABLE_TELEMETRY'] = 'true'
            # 保留其他可能的变量名作为后备
            env['KURTOSIS_DISABLE_ANALYTICS'] = 'true'
            env['KURTOSIS_DISABLE_METRICS'] = 'true'
            
            result = subprocess.run(
                [kurtosis_path] + command,
                capture_output=True,
                text=True,
                timeout=timeout,
                env=env
            )
            
            if result.returncode == 0:
                logger.debug(f"Kurtosis 命令成功: {result.stdout[:200]}")
            else:
                # 检查是否是 engine 无响应的问题
                error_output = result.stderr + result.stdout
                if "server isn't responding" in error_output.lower() or "isn't responding" in error_output.lower():
                    # 如果已经尝试过重启，不再重复尝试（避免循环）
                    if self._engine_restart_attempted:
                        logger.debug("Engine 无响应，但已尝试过重启，跳过自动修复")
                    else:
                        logger.warning(f"检测到 engine 无响应，错误信息: {error_output[:300]}")
                        # 尝试自动修复：重启 engine（直接调用 subprocess 避免递归）
                        logger.info("尝试自动重启 engine...")
                        self._engine_restart_attempted = True
                        try:
                            restart_result = subprocess.run(
                                [kurtosis_path, "engine", "restart"],
                                capture_output=True,
                                text=True,
                                timeout=60,
                                env=env
                            )
                            if restart_result.returncode == 0:
                                logger.info("Engine 重启成功，等待几秒后重试原命令...")
                                import time
                                time.sleep(5)  # 等待 engine 完全启动
                                # 重试原命令
                                retry_result = subprocess.run(
                                    [kurtosis_path] + command,
                                    capture_output=True,
                                    text=True,
                                    timeout=timeout,
                                    env=env
                                )
                                if retry_result.returncode == 0:
                                    logger.info("重试命令成功")
                                    return True, retry_result.stdout, retry_result.stderr
                                else:
                                    logger.warning(f"重试命令仍然失败: {retry_result.stderr[:200]}")
                            else:
                                logger.warning(f"Engine 重启失败: {restart_result.stderr[:200]}")
                        except Exception as restart_error:
                            logger.warning(f"尝试重启 engine 时出错: {restart_error}")
                else:
                    logger.warning(f"Kurtosis 命令失败: {result.stderr[:200]}")
            
            return result.returncode == 0, result.stdout, result.stderr
        except FileNotFoundError:
            logger.error(f"Kurtosis CLI 未找到，尝试的路径: {self._get_kurtosis_path()}")
            logger.error("请确保 Kurtosis CLI 已正确安装并在 PATH 中")
            return False, "", "Kurtosis CLI not found. Please ensure Kurtosis CLI is installed and in PATH."
        except subprocess.TimeoutExpired:
            logger.error(f"Kurtosis 命令超时: {' '.join(command)}")
            return False, "", "Command timeout"
        except Exception as e:
            logger.error(f"执行 Kurtosis 命令失败: {e}", exc_info=True)
            return False, "", str(e)
    
    def get_status(self) -> Dict[str, Any]:
        """
        获取网络状态
        
        即使 dev net 未启动，也应该返回一个合理的状态（stopped），而不是错误。
        
        Returns:
            网络状态信息
        """
        # 检查 enclave 是否存在
        success, stdout, stderr = self._run_kurtosis_command(["enclave", "ls"], timeout=30)
        
        if not success:
            # 检查是否是 engine 问题（这种情况下应该返回 stopped 而不是 error）
            error_msg = (stderr + stdout).lower()
            
            # 如果是 engine 相关错误，返回 stopped 状态（用户可能只是还没启动 dev net）
            if "engine" in error_msg or "server isn't responding" in error_msg:
                logger.info(f"Engine 问题或 dev net 未启动，返回 stopped 状态: {stderr[:200]}")
                return {
                    "enclave_name": self.enclave_name,
                    "status": "stopped",
                    "is_running": False,
                    "message": "Dev net 未启动或 engine 未就绪"
                }
            
            # 其他错误（如 CLI 未找到等）才返回 error 状态
            logger.warning(f"查询 enclave 列表失败: {stderr[:200]}")
            return {
                "enclave_name": self.enclave_name,
                "status": "error",
                "error": stderr[:500] if stderr else "无法查询 enclave 列表",
                "is_running": False
            }
        
        # 检查 enclave 是否在运行
        is_running = self.enclave_name in stdout
        
        if not is_running:
            # Dev net 未启动，这是正常状态，返回 stopped
            return {
                "enclave_name": self.enclave_name,
                "status": "stopped",
                "is_running": False,
                "message": "Dev net 未启动"
            }
        
        # 获取 enclave 详细信息
        # 注意：Kurtosis CLI 不支持 --json 标志，使用普通输出
        success, stdout, stderr = self._run_kurtosis_command(
            ["enclave", "inspect", self.enclave_name],
            timeout=30
        )
        
        if not success:
            # 如果无法获取详细信息，但 enclave 存在于列表中，可能是状态异常
            # 保守起见，返回 stopped 状态
            logger.warning(f"无法获取 enclave 详细信息: {stderr}")
            return {
                "enclave_name": self.enclave_name,
                "status": "stopped",
                "is_running": False,
                "error": stderr or "无法获取 enclave 详细信息"
            }
        
        # 解析 enclave inspect 输出，检查实际状态
        # Kurtosis enclave 状态可能是：RUNNING, EMPTY, STOPPED 等
        enclave_status = None
        lines = stdout.split('\n')
        for line in lines:
            # 查找 Status: 行
            if 'Status:' in line or 'status:' in line.lower():
                # 提取状态值（去除前后空格）
                parts = line.split(':', 1)
                if len(parts) > 1:
                    enclave_status = parts[1].strip()
                    break
        
        # 检查是否有服务在运行（通过检查 User Services 部分是否有内容）
        has_services = False
        in_user_services = False
        for line in lines:
            if 'User Services' in line or 'user services' in line.lower():
                in_user_services = True
                continue
            if in_user_services:
                # 跳过表头行（包含 UUID, Name, Ports, Status）
                if 'UUID' in line and ('Name' in line or 'Ports' in line):
                    continue
                # 检查是否有服务行（包含 UUID 和 Name）
                if line.strip() and not line.strip().startswith('='):
                    # 如果有非空行且不是分隔符，检查是否是有效的服务行
                    # 服务行通常以 UUID（12个十六进制字符）开头
                    parts = line.split()
                    if len(parts) >= 2:
                        # 检查第一个部分是否是 UUID 格式（12个十六进制字符）
                        first_part = parts[0].strip()
                        if len(first_part) == 12 and all(c in '0123456789abcdef' for c in first_part.lower()):
                            has_services = True
                            break
                # 如果遇到新的部分（以 = 开头），停止检查
                if line.strip().startswith('=') and in_user_services:
                    break
        
        # 判断 enclave 是否真正在运行
        # 只有当状态是 RUNNING 且有服务在运行时，才认为是在运行
        is_actually_running = False
        if enclave_status:
            enclave_status_upper = enclave_status.upper()
            # 状态为 RUNNING 且有服务，才认为真正在运行
            if enclave_status_upper == 'RUNNING' and has_services:
                is_actually_running = True
            elif enclave_status_upper in ['EMPTY', 'STOPPED']:
                is_actually_running = False
            else:
                # 其他状态（如未知状态），如果没有服务，认为未运行
                is_actually_running = has_services
        
        # 如果没有解析到状态，但有服务在运行，认为是在运行
        if enclave_status is None and has_services:
            is_actually_running = True
        
        # 根据实际运行状态返回结果
        if is_actually_running:
            return {
                "enclave_name": self.enclave_name,
                "status": "running",
                "is_running": True,
                "enclave_info": {
                    "raw_output": stdout,
                    "enclave_status": enclave_status
                },
                "raw_output": stdout
            }
        else:
            # Enclave 存在但未运行（EMPTY 状态）
            return {
                "enclave_name": self.enclave_name,
                "status": "stopped",
                "is_running": False,
                "message": f"Enclave 存在但未运行 (Status: {enclave_status or 'Unknown'})",
                "enclave_info": {
                    "raw_output": stdout,
                    "enclave_status": enclave_status
                },
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

