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
kurtosis_service = KurtosisService(config_file=config_file, enclave_name=enclave_name)


@app.get("/health")
async def health():
    """健康检查"""
    return {"status": "healthy"}


@app.get("/status")
async def get_status():
    """获取网络状态"""
    try:
        status = kurtosis_service.get_status()
        return status
    except Exception as e:
        logger.error(f"获取状态失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/start")
async def start_network():
    """启动 Kurtosis 网络"""
    try:
        result = kurtosis_service.start()
        if not result.get("success"):
            raise HTTPException(status_code=500, detail=result.get("message", "启动失败"))
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"启动网络失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/stop")
async def stop_network():
    """停止 Kurtosis 网络"""
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

