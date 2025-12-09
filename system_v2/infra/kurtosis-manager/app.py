"""
Kurtosis 管理服务 API
提供 HTTP API 接口供后端调用
"""
import os
import logging
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, Dict, Any

from kurtosis_service import KurtosisService

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 创建 FastAPI 应用
app = FastAPI(title="Kurtosis Manager API", version="1.0.0")

# 配置 CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 在生产环境中应该限制来源
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 初始化 Kurtosis 服务
config_file = os.getenv("KURTOSIS_CONFIG_FILE", "/kurtosis-config/kurtosis-config.yaml")
enclave_name = os.getenv("KURTOSIS_ENCLAVE", "eth-devnet")

try:
    kurtosis_service = KurtosisService(config_file=config_file, enclave_name=enclave_name)
    logger.info("Kurtosis 服务初始化成功")
except Exception as e:
    logger.error(f"Kurtosis 服务初始化失败: {e}", exc_info=True)
    logger.error("请确保 Kurtosis CLI 已正确安装")
    kurtosis_service = None


@app.get("/health")
async def health():
    """健康检查"""
    return {"status": "healthy"}


@app.get("/status")
async def get_status():
    """
    获取网络状态
    
    即使 dev net 未启动，也会返回一个合理的状态（stopped），不会抛出异常。
    """
    if kurtosis_service is None:
        raise HTTPException(
            status_code=503,
            detail="Kurtosis CLI 未安装或不可用。请检查容器日志并重新构建镜像。"
        )
    try:
        status = kurtosis_service.get_status()
        # 确保返回的状态包含必要字段
        if "is_running" not in status:
            status["is_running"] = False
        if "status" not in status:
            status["status"] = "stopped"
        return status
    except Exception as e:
        logger.error(f"获取状态失败: {e}", exc_info=True)
        # 即使出现异常，也返回一个合理的默认状态，而不是抛出 HTTP 异常
        # 这样前端可以正常显示"未启动"状态
        return {
            "enclave_name": os.getenv("KURTOSIS_ENCLAVE", "eth-devnet"),
            "status": "stopped",
            "is_running": False,
            "error": f"查询状态时出错: {str(e)}"
        }


@app.post("/start")
async def start_network():
    """启动 Kurtosis 网络"""
    if kurtosis_service is None:
        raise HTTPException(
            status_code=503,
            detail="Kurtosis CLI 未安装或不可用。请检查容器日志并重新构建镜像。"
        )
    try:
        result = kurtosis_service.start()
        if not result.get("success"):
            # 改进错误信息，包含更多详细信息
            error_detail = result.get("message", "启动失败")
            if result.get("error"):
                error_detail += f"\n错误详情: {result.get('error')[:500]}"
            if result.get("full_stderr"):
                error_detail += f"\n完整错误输出: {result.get('full_stderr')[-1000:]}"
            logger.error(f"启动失败: {error_detail}")
            raise HTTPException(status_code=500, detail=error_detail)
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"启动网络失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/stop")
async def stop_network():
    """停止 Kurtosis 网络"""
    if kurtosis_service is None:
        raise HTTPException(
            status_code=503,
            detail="Kurtosis CLI 未安装或不可用。请检查容器日志并重新构建镜像。"
        )
    try:
        result = kurtosis_service.stop()
        if not result.get("success"):
            raise HTTPException(status_code=500, detail=result.get("message", "停止失败"))
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"停止网络失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8002)

