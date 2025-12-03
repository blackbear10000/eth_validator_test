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
        
        # 验证 Kurtosis CLI 是否可用
        self._verify_kurtosis_cli()
        
        # 禁用 analytics/metrics（避免网络连接问题）
        self._disable_analytics()
        
        # 检查并启动 Kurtosis engine（如果需要）
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
    
    def _ensure_engine_running(self) -> bool:
        """
        确保 Kurtosis engine 正在运行
        
        处理以下情况：
        1. Engine 未运行 -> 启动 engine
        2. Engine 容器存在但无响应 -> 重启 engine
        
        Returns:
            是否成功
        """
        try:
            # 检查 engine 状态
            success, stdout, stderr = self._run_kurtosis_command(["engine", "status"], timeout=10)
            if success:
                logger.info("Kurtosis engine 正在运行")
                return True
            
            # Engine 状态检查失败，可能的原因：
            # 1. Engine 未运行
            # 2. Engine 容器存在但服务器无响应（需要重启）
            
            # 检查错误信息中是否包含 "server isn't responding"
            error_msg = (stdout + stderr).lower()
            if "server isn't responding" in error_msg or "isn't responding" in error_msg:
                logger.warning("检测到 Kurtosis engine 容器存在但服务器无响应，尝试重启...")
                # 尝试重启 engine
                restart_success, restart_stdout, restart_stderr = self._run_kurtosis_command(
                    ["engine", "restart"], 
                    timeout=60
                )
                if restart_success:
                    logger.info("Kurtosis engine 重启成功")
                    return True
                else:
                    logger.warning(f"Kurtosis engine 重启失败: {restart_stderr[:300]}")
                    # 尝试停止并重新启动
                    logger.info("尝试停止并重新启动 engine...")
                    self._run_kurtosis_command(["engine", "stop"], timeout=30)
                    start_success, start_stdout, start_stderr = self._run_kurtosis_command(
                        ["engine", "start"], 
                        timeout=60
                    )
                    if start_success:
                        logger.info("Kurtosis engine 重新启动成功")
                        return True
                    else:
                        logger.warning(f"Kurtosis engine 重新启动失败: {start_stderr[:300]}")
                        return False
            else:
                # Engine 未运行，尝试启动
                logger.info("Kurtosis engine 未运行，尝试启动...")
                success, stdout, stderr = self._run_kurtosis_command(["engine", "start"], timeout=60)
                if success:
                    logger.info("Kurtosis engine 启动成功")
                    return True
                else:
                    logger.warning(f"Kurtosis engine 启动失败: {stderr[:300]}")
                    # 不阻止服务启动，某些操作可能不需要 engine
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
                    logger.warning(f"检测到 engine 无响应，错误信息: {error_output[:300]}")
                    # 尝试自动修复：重启 engine（直接调用 subprocess 避免递归）
                    logger.info("尝试自动重启 engine...")
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
                            time.sleep(3)  # 等待 engine 完全启动
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

