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
from app.api.v1 import keys, deposits, clients, monitoring, exits, withdrawals, network
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
app.include_router(network.router, prefix=settings.api_v1_prefix, tags=["network"])


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
    logger.info("应用启动，执行数据库迁移...")
    try:
        # 使用 Alembic API 执行迁移（而不是 subprocess）
        from alembic.config import Config
        from alembic import command
        import os
        import traceback
        
        # 获取 alembic.ini 路径
        backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        alembic_ini_path = os.path.join(backend_dir, "alembic.ini")
        
        logger.info(f"使用 Alembic 配置文件: {alembic_ini_path}")
        
        if not os.path.exists(alembic_ini_path):
            logger.error(f"Alembic 配置文件不存在: {alembic_ini_path}")
            raise FileNotFoundError(f"Alembic 配置文件不存在: {alembic_ini_path}")
        
        alembic_cfg = Config(alembic_ini_path)
        
        # 确保使用环境变量中的数据库 URL（而不是 alembic.ini 中的硬编码值）
        alembic_cfg.set_main_option("sqlalchemy.url", settings.database_url)
        logger.info(f"使用数据库 URL: {settings.database_url.split('@')[-1]}")  # 只显示主机部分，隐藏密码
        
        # 执行迁移
        logger.info("开始执行数据库迁移...")
        try:
            command.upgrade(alembic_cfg, "head")
            logger.info("数据库迁移完成")
        except Exception as migration_error:
            logger.error(f"迁移执行过程中出错: {migration_error}")
            logger.error(traceback.format_exc())
            raise
        
        # 验证表是否创建成功
        from app.dependencies import SessionLocal
        db = SessionLocal()
        try:
            from sqlalchemy import inspect
            inspector = inspect(db.bind)
            tables = inspector.get_table_names()
            logger.info(f"数据库中的表: {tables}")
            
            # 检查所有关键表
            required_tables = [
                'validator_keys',
                'client_instances',
                'validator_client_keys',
                'deposit_transactions',
                'withdrawal_events',
                'batch_deposit_contracts',
                'alembic_version'
            ]
            
            missing_tables = [t for t in required_tables if t not in tables]
            if missing_tables:
                logger.error(f"缺少以下关键表: {', '.join(missing_tables)}")
                logger.error("数据库迁移可能未完全执行，请手动运行: alembic upgrade head")
                raise RuntimeError(f"数据库迁移不完整，缺少表: {', '.join(missing_tables)}")
            else:
                logger.info("所有关键表已存在，迁移验证通过")
        except Exception as e:
            logger.error(f"验证数据库表时出错: {e}")
            raise
        finally:
            db.close()
            
    except Exception as e:
        logger.error(f"数据库迁移失败: {e}")
        logger.error(traceback.format_exc())
        # 迁移失败不应该阻止应用启动，但会记录错误
    
    logger.info("初始化后台任务...")
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

