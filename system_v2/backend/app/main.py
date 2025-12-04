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
from app.api.v1 import keys, deposits, clients, monitoring, exits, withdrawals, network, web3signer
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
app.include_router(web3signer.router, prefix=settings.api_v1_prefix, tags=["web3signer"])


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
        # 1. 首先确保数据库连接可用，并等待数据库准备就绪
        from sqlalchemy import create_engine, text
        import time
        
        logger.info("等待数据库准备就绪...")
        max_retries = 30
        retry_count = 0
        db_ready = False
        
        while retry_count < max_retries:
            try:
                engine = create_engine(settings.database_url, pool_pre_ping=True)
                with engine.connect() as conn:
                    # 测试连接并检查数据库是否存在
                    result = conn.execute(text("SELECT 1"))
                    result.fetchone()
                    
                    # 额外验证：检查数据库名称是否正确
                    db_result = conn.execute(text("SELECT current_database()"))
                    current_db = db_result.fetchone()[0]
                    expected_db = settings.database_url.split('/')[-1]
                    if current_db != expected_db:
                        raise RuntimeError(f"连接到了错误的数据库: {current_db}，期望: {expected_db}")
                    
                    db_ready = True
                    logger.info(f"数据库连接成功，当前数据库: {current_db}")
                    break
            except Exception as e:
                retry_count += 1
                if retry_count < max_retries:
                    logger.warning(f"数据库连接失败 (尝试 {retry_count}/{max_retries}): {e}")
                    time.sleep(2)
                else:
                    logger.error(f"数据库连接失败，已达到最大重试次数: {e}")
                    raise
        
        if not db_ready:
            raise RuntimeError("数据库未准备就绪")
        
        # 2. 确保数据库存在（如果不存在则创建）
        try:
            # 连接到 postgres 数据库来创建 validator_db（如果需要）
            db_name = settings.database_url.split('/')[-1]
            admin_url = settings.database_url.replace(f'/{db_name}', '/postgres')
            admin_engine = create_engine(admin_url, isolation_level="AUTOCOMMIT")
            
            with admin_engine.connect() as conn:
                result = conn.execute(
                    text("SELECT 1 FROM pg_database WHERE datname = :db_name"),
                    {"db_name": db_name}
                )
                if not result.fetchone():
                    logger.info(f"数据库 {db_name} 不存在，正在创建...")
                    conn.execute(text(f'CREATE DATABASE {db_name}'))
                    logger.info(f"数据库 {db_name} 创建成功")
                else:
                    logger.info(f"数据库 {db_name} 已存在")
        except Exception as e:
            logger.warning(f"检查/创建数据库时出错（可能已存在）: {e}")
        
        # 3. 直接使用 SQLAlchemy 创建表（不依赖 Alembic）
        # 这样可以避免 Alembic 迁移的复杂性和潜在问题
        logger.info("使用 SQLAlchemy 直接创建数据库表...")
        from app.core.db_init import init_database, check_database_schema
        
        # 检查当前数据库状态
        schema_info = check_database_schema()
        logger.info(f"数据库状态检查: {schema_info.get('database')}, 表数量: {schema_info.get('table_count', 0)}")
        
        if schema_info.get('is_complete'):
            logger.info("✓ 所有表已存在，无需初始化")
        else:
            missing = schema_info.get('missing_tables', [])
            if missing:
                logger.info(f"缺少表: {', '.join(missing)}，开始创建...")
            
            # 初始化数据库（创建缺失的表）
            success = init_database(force_recreate=False)
            if not success:
                logger.error("数据库初始化失败")
                raise RuntimeError("数据库初始化失败")
            
            # 再次验证
            schema_info = check_database_schema()
            if not schema_info.get('is_complete'):
                missing = schema_info.get('missing_tables', [])
                logger.error(f"初始化后仍然缺少表: {', '.join(missing)}")
                raise RuntimeError(f"数据库初始化不完整，缺少表: {', '.join(missing)}")
            
            logger.info("✓ 数据库初始化成功，所有表已创建")
            
    except Exception as e:
        logger.error(f"数据库初始化失败: {e}")
        import traceback
        logger.error(traceback.format_exc())
        raise
    
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

