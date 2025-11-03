"""
FastAPI 应用入口
"""
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import logging
import time

from app.config import settings
from app.utils.logger import configure_logging
from app.api.v1 import keys, deposits, clients, monitoring, exits, withdrawals
from app.core.background_tasks import start_background_tasks, stop_background_tasks

# 配置日志
configure_logging()
logger = logging.getLogger(__name__)

# 创建 FastAPI 应用
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="大规模 Ethereum Validator 管理系统 API",
    docs_url="/docs",
    redoc_url="/redoc"
)

# 配置 CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# 中间件：请求日志
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """记录请求日志"""
    start_time = time.time()
    
    logger.info(f"{request.method} {request.url.path}")
    
    response = await call_next(request)
    
    process_time = time.time() - start_time
    logger.info(
        f"{request.method} {request.url.path} - "
        f"Status: {response.status_code} - "
        f"Time: {process_time:.3f}s"
    )
    
    return response


# 异常处理
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """全局异常处理"""
    logger.error(f"未处理的异常: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal Server Error",
            "message": str(exc),
            "path": request.url.path
        }
    )


# 注册路由
app.include_router(keys.router, prefix=settings.api_v1_prefix, tags=["keys"])
app.include_router(deposits.router, prefix=settings.api_v1_prefix, tags=["deposits"])
app.include_router(clients.router, prefix=settings.api_v1_prefix, tags=["clients"])
app.include_router(monitoring.router, prefix=settings.api_v1_prefix, tags=["monitoring"])
app.include_router(exits.router, prefix=settings.api_v1_prefix, tags=["exits"])
app.include_router(withdrawals.router, prefix=settings.api_v1_prefix, tags=["withdrawals"])


# 根路径
@app.get("/")
async def root():
    """根路径"""
    return {
        "name": settings.app_name,
        "version": settings.app_version,
        "docs": "/docs",
        "health": "/api/v1/monitoring/health"
    }


# 应用生命周期事件
@app.on_event("startup")
async def startup_event():
    """应用启动时执行"""
    logger.info("应用启动，初始化后台任务...")
    try:
        await start_background_tasks()
        logger.info("后台任务已启动")
    except Exception as e:
        logger.error(f"启动后台任务失败: {e}")


@app.on_event("shutdown")
async def shutdown_event():
    """应用关闭时执行"""
    logger.info("应用关闭，停止后台任务...")
    try:
        await stop_background_tasks()
        logger.info("后台任务已停止")
    except Exception as e:
        logger.error(f"停止后台任务失败: {e}")


# 健康检查
@app.get("/health")
async def health():
    """健康检查"""
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.debug
    )

