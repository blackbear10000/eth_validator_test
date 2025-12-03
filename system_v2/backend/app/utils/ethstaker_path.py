"""
ethstaker-deposit-cli 路径解析工具
统一处理本地开发和 Docker 容器环境下的路径问题
"""
import os
import sys
import logging

logger = logging.getLogger(__name__)

# 全局变量存储解析后的路径
_ethstaker_path: str | None = None


def get_ethstaker_path() -> str | None:
    """
    获取 ethstaker-deposit-cli 路径（带缓存）
    
    优先级：
    1. 环境变量 ETHSTAKER_DEPOSIT_CLI_PATH
    2. Docker 容器内挂载路径：/app/external/ethstaker-deposit-cli
    3. 项目根目录：code/external/ethstaker-deposit-cli（从 system_v2/backend/app 向上5层）
    4. 项目根目录：code/external/ethstaker-deposit-cli（从 system_v2/backend/app 向上4层，兼容旧代码）
    
    Returns:
        ethstaker-deposit-cli 路径，如果不存在则返回 None
    """
    global _ethstaker_path
    
    if _ethstaker_path is None:
        _ethstaker_path = _find_ethstaker_path()
    
    return _ethstaker_path


def _find_ethstaker_path() -> str | None:
    """
    内部函数：查找 ethstaker-deposit-cli 路径
    """
    # 1. 检查环境变量
    env_path = os.getenv("ETHSTAKER_DEPOSIT_CLI_PATH")
    if env_path and os.path.exists(env_path):
        logger.debug(f"使用环境变量路径: {env_path}")
        return env_path
    
    # 2. 检查 Docker 容器内挂载路径
    docker_path = "/app/external/ethstaker-deposit-cli"
    if os.path.exists(docker_path):
        logger.debug(f"使用 Docker 挂载路径: {docker_path}")
        return docker_path
    
    # 3. 从当前文件位置计算项目根目录
    # 假设这个文件在 system_v2/backend/app/utils/ethstaker_path.py
    # 向上5层：utils -> app -> backend -> system_v2 -> eth_validator_test (项目根目录)
    current_file = os.path.abspath(__file__)
    project_root_5 = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(current_file)))))
    path_5 = os.path.join(project_root_5, "code", "external", "ethstaker-deposit-cli")
    if os.path.exists(path_5):
        logger.debug(f"使用计算路径（5层）: {path_5}")
        return path_5
    
    # 4. 向上4层（兼容旧代码）
    project_root_4 = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(current_file))))
    path_4 = os.path.join(project_root_4, "code", "external", "ethstaker-deposit-cli")
    if os.path.exists(path_4):
        logger.debug(f"使用计算路径（4层）: {path_4}")
        return path_4
    
    # 5. 尝试从 backend 目录向上查找
    backend_dir = os.path.dirname(os.path.dirname(os.path.dirname(current_file)))
    # backend_dir 应该是 system_v2/backend
    # 向上2层到项目根目录
    project_root_from_backend = os.path.dirname(os.path.dirname(backend_dir))
    path_from_backend = os.path.join(project_root_from_backend, "code", "external", "ethstaker-deposit-cli")
    if os.path.exists(path_from_backend):
        logger.debug(f"使用从 backend 计算的路径: {path_from_backend}")
        return path_from_backend
    
    logger.warning(f"未找到 ethstaker-deposit-cli，尝试的路径：")
    logger.warning(f"  - 环境变量: {env_path}")
    logger.warning(f"  - Docker 路径: {docker_path}")
    logger.warning(f"  - 5层路径: {path_5}")
    logger.warning(f"  - 4层路径: {path_4}")
    logger.warning(f"  - 从 backend 计算: {path_from_backend}")
    
    return None


def setup_ethstaker_import():
    """
    设置 ethstaker-deposit-cli 导入路径
    
    Returns:
        (成功标志, 路径)
    """
    global _ethstaker_path
    
    if _ethstaker_path is None:
        _ethstaker_path = _find_ethstaker_path()
    
    ethstaker_path = _ethstaker_path
    
    if ethstaker_path and os.path.exists(ethstaker_path):
        if ethstaker_path not in sys.path:
            sys.path.insert(0, ethstaker_path)
            logger.info(f"已添加 ethstaker-deposit-cli 到 Python 路径: {ethstaker_path}")
        return True, ethstaker_path
    else:
        logger.warning("ethstaker-deposit-cli 路径不存在，导入可能失败")
        return False, ethstaker_path

