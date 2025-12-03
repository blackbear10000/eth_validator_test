"""
客户端进程管理服务
管理 Validator Client 进程的启动、停止和状态查询
"""
import subprocess
import logging
import os
import signal
import time
import psutil
from typing import Dict, Optional, List, Any
from pathlib import Path
from app.config import settings

logger = logging.getLogger(__name__)


class ClientProcessService:
    """Validator Client 进程管理服务"""
    
    def __init__(self):
        """初始化进程管理服务"""
        self.processes: Dict[int, subprocess.Popen] = {}  # client_id -> process
        self.process_info: Dict[int, Dict] = {}  # client_id -> process info
    
    def _find_process_by_name(self, name_pattern: str) -> List[psutil.Process]:
        """
        根据进程名称模式查找进程
        
        Args:
            name_pattern: 进程名称模式（如 "prysm", "lighthouse", "teku"）
            
        Returns:
            匹配的进程列表
        """
        processes = []
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            try:
                cmdline = ' '.join(proc.info['cmdline'] or [])
                if name_pattern.lower() in cmdline.lower():
                    processes.append(proc)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        return processes
    
    def _get_client_process_name(self, client_type: str) -> str:
        """
        获取客户端进程名称
        
        Args:
            client_type: 客户端类型
            
        Returns:
            进程名称
        """
        client_type_lower = client_type.lower()
        if 'prysm' in client_type_lower:
            return 'prysm'
        elif 'lighthouse' in client_type_lower:
            return 'lighthouse'
        elif 'teku' in client_type_lower:
            return 'teku'
        return client_type_lower
    
    def get_status(self, client_id: int, client_type: str) -> Dict[str, any]:
        """
        获取客户端进程状态
        
        Args:
            client_id: 客户端 ID
            client_type: 客户端类型
            
        Returns:
            进程状态信息
        """
        # 检查内存中的进程
        if client_id in self.processes:
            proc = self.processes[client_id]
            if proc.poll() is None:  # 进程仍在运行
                return {
                    "client_id": client_id,
                    "status": "running",
                    "pid": proc.pid,
                    "is_running": True
                }
            else:
                # 进程已退出
                del self.processes[client_id]
                return {
                    "client_id": client_id,
                    "status": "stopped",
                    "exit_code": proc.returncode,
                    "is_running": False
                }
        
        # 尝试通过进程名称查找
        process_name = self._get_client_process_name(client_type)
        matching_processes = self._find_process_by_name(process_name)
        
        if matching_processes:
            # 找到匹配的进程，但不确定是否是我们的客户端
            return {
                "client_id": client_id,
                "status": "running",
                "pid": matching_processes[0].pid,
                "is_running": True,
                "note": "Found process by name, may not be this client instance"
            }
        
        return {
            "client_id": client_id,
            "status": "stopped",
            "is_running": False
        }
    
    def start(
        self,
        client_id: int,
        client_type: str,
        config_file: Optional[str] = None,
        command: Optional[List[str]] = None
    ) -> Dict[str, any]:
        """
        启动客户端进程
        
        Args:
            client_id: 客户端 ID
            client_type: 客户端类型
            config_file: 配置文件路径
            command: 自定义启动命令
            
        Returns:
            启动结果
        """
        # 检查是否已经在运行
        status = self.get_status(client_id, client_type)
        if status.get("is_running"):
            return {
                "success": True,
                "message": f"客户端 {client_id} 已经在运行",
                "status": status
            }
        
        # 构建启动命令
        if command:
            cmd = command
        else:
            cmd = self._build_start_command(client_type, config_file)
        
        if not cmd:
            return {
                "success": False,
                "message": f"无法构建 {client_type} 的启动命令"
            }
        
        try:
            # 启动进程
            logger.info(f"启动客户端 {client_id} ({client_type}): {' '.join(cmd)}")
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=os.getcwd()
            )
            
            self.processes[client_id] = process
            self.process_info[client_id] = {
                "client_type": client_type,
                "config_file": config_file,
                "command": cmd,
                "started_at": time.time()
            }
            
            return {
                "success": True,
                "message": f"客户端 {client_id} 启动成功",
                "pid": process.pid,
                "status": self.get_status(client_id, client_type)
            }
        except Exception as e:
            logger.error(f"启动客户端 {client_id} 失败: {e}")
            return {
                "success": False,
                "message": f"启动失败: {str(e)}"
            }
    
    def stop(self, client_id: int, client_type: str) -> Dict[str, any]:
        """
        停止客户端进程
        
        Args:
            client_id: 客户端 ID
            client_type: 客户端类型
            
        Returns:
            停止结果
        """
        # 检查内存中的进程
        if client_id in self.processes:
            proc = self.processes[client_id]
            try:
                proc.terminate()
                proc.wait(timeout=10)
                del self.processes[client_id]
                if client_id in self.process_info:
                    del self.process_info[client_id]
                return {
                    "success": True,
                    "message": f"客户端 {client_id} 已停止"
                }
            except subprocess.TimeoutExpired:
                # 强制杀死
                proc.kill()
                proc.wait()
                del self.processes[client_id]
                if client_id in self.process_info:
                    del self.process_info[client_id]
                return {
                    "success": True,
                    "message": f"客户端 {client_id} 已强制停止"
                }
            except Exception as e:
                logger.error(f"停止客户端 {client_id} 失败: {e}")
                return {
                    "success": False,
                    "message": f"停止失败: {str(e)}"
                }
        
        # 尝试通过进程名称查找并停止
        status = self.get_status(client_id, client_type)
        if status.get("is_running") and "pid" in status:
            try:
                pid = status["pid"]
                proc = psutil.Process(pid)
                proc.terminate()
                proc.wait(timeout=10)
                return {
                    "success": True,
                    "message": f"客户端 {client_id} 已停止 (PID: {pid})"
                }
            except psutil.NoSuchProcess:
                return {
                    "success": True,
                    "message": f"客户端 {client_id} 进程不存在"
                }
            except psutil.TimeoutExpired:
                try:
                    proc.kill()
                    return {
                        "success": True,
                        "message": f"客户端 {client_id} 已强制停止 (PID: {pid})"
                    }
                except Exception as e:
                    return {
                        "success": False,
                        "message": f"强制停止失败: {str(e)}"
                    }
            except Exception as e:
                return {
                    "success": False,
                    "message": f"停止失败: {str(e)}"
                }
        
        return {
            "success": True,
            "message": f"客户端 {client_id} 未运行"
        }
    
    def _build_start_command(
        self,
        client_type: str,
        config_file: Optional[str] = None
    ) -> Optional[List[str]]:
        """
        构建启动命令
        
        Args:
            client_type: 客户端类型
            config_file: 配置文件路径
            
        Returns:
            启动命令列表
        """
        client_type_lower = client_type.lower()
        
        if 'prysm' in client_type_lower:
            cmd = ['prysm', 'validator']
            if config_file:
                cmd.extend(['--config-file', config_file])
            return cmd
        
        elif 'lighthouse' in client_type_lower:
            cmd = ['lighthouse', 'validator']
            if config_file:
                cmd.extend(['--config-file', config_file])
            return cmd
        
        elif 'teku' in client_type_lower:
            cmd = ['teku']
            if config_file:
                cmd.extend(['--config-file', config_file])
            return cmd
        
        return None
    
    def get_logs(self, client_id: int, lines: int = 100) -> Dict[str, any]:
        """
        获取客户端日志（简化实现）
        
        Args:
            client_id: 客户端 ID
            lines: 返回的行数
            
        Returns:
            日志信息
        """
        # 这是一个简化实现，实际应该从日志文件读取
        if client_id in self.process_info:
            return {
                "client_id": client_id,
                "logs": [],
                "message": "日志功能需要配置日志文件路径"
            }
        
        return {
            "client_id": client_id,
            "logs": [],
            "message": "客户端未运行或未找到日志"
        }

