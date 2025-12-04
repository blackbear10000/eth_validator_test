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
        
        # 3. 使用 Alembic API 执行迁移
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
        # 重要：必须在调用 command.upgrade 之前设置，否则 Alembic 会使用 alembic.ini 中的 URL
        alembic_cfg.set_main_option("sqlalchemy.url", settings.database_url)
        
        # 验证 URL 设置是否成功
        configured_url = alembic_cfg.get_main_option("sqlalchemy.url")
        db_url_display = configured_url.split('@')[-1] if '@' in configured_url else configured_url
        logger.info(f"使用数据库 URL: postgresql://***@{db_url_display}")
        
        # 双重验证：确保 URL 正确
        if configured_url != settings.database_url:
            logger.error(f"⚠️  URL 设置失败！")
            logger.error(f"期望: {settings.database_url}")
            logger.error(f"实际: {configured_url}")
            raise RuntimeError(f"Alembic URL 配置失败，可能导致迁移执行在错误的数据库")
        
        # 执行迁移
        logger.info("开始执行数据库迁移...")
        try:
            # 在执行迁移前，再次确认数据库连接
            test_engine = create_engine(settings.database_url, pool_pre_ping=True)
            with test_engine.connect() as test_conn:
                # 检查当前连接的数据库
                db_result = test_conn.execute(text("SELECT current_database()"))
                current_db = db_result.fetchone()[0]
                logger.info(f"迁移将执行在数据库: {current_db}")
                
                # 检查 alembic_version 表是否存在
                try:
                    version_result = test_conn.execute(text("SELECT version_num FROM alembic_version"))
                    current_version = version_result.fetchone()
                    if current_version:
                        logger.info(f"当前迁移版本: {current_version[0]}")
                    else:
                        logger.info("alembic_version 表存在但为空，将执行初始迁移")
                except Exception:
                    logger.info("alembic_version 表不存在，将执行初始迁移")
            
            command.upgrade(alembic_cfg, "head")
            logger.info("数据库迁移完成")
            
            # 立即验证迁移是否成功（在同一个连接中，确保事务已提交）
            logger.info("立即验证迁移结果（迁移后）...")
            with test_engine.connect() as immediate_verify:
                # 确认当前数据库
                db_result = immediate_verify.execute(text("SELECT current_database()"))
                current_db_immediate = db_result.fetchone()[0]
                logger.info(f"立即验证数据库: {current_db_immediate}")
                
                # 检查 alembic_version 表
                try:
                    version_result = immediate_verify.execute(text("SELECT version_num FROM alembic_version"))
                    version = version_result.fetchone()
                    if version:
                        logger.info(f"迁移版本记录: {version[0]}")
                    else:
                        logger.warning("alembic_version 表存在但为空")
                except Exception as e:
                    logger.error(f"⚠️  无法读取 alembic_version 表: {e}")
                
                # 获取所有表
                tables_result = immediate_verify.execute(text("""
                    SELECT tablename 
                    FROM pg_tables 
                    WHERE schemaname = 'public'
                    ORDER BY tablename
                """))
                tables_immediate = [row[0] for row in tables_result]
                logger.info(f"立即验证 - 数据库中的表 ({len(tables_immediate)} 个): {', '.join(tables_immediate) if tables_immediate else '(无)'}")
                
                if not tables_immediate:
                    logger.error("⚠️  严重警告: 迁移执行后没有找到任何表！")
                    logger.error("这可能是因为:")
                    logger.error("1. 迁移执行在了错误的数据库")
                    logger.error("2. 迁移事务被回滚")
                    logger.error("3. 数据库连接问题")
                    logger.error("4. Alembic 配置问题")
                    raise RuntimeError("迁移执行后表不存在，迁移可能失败")
                    
        except Exception as migration_error:
            logger.error(f"迁移执行过程中出错: {migration_error}")
            logger.error(traceback.format_exc())
            raise
        
        # 再次验证表是否创建成功（使用新的连接，确保事务已提交）
        logger.info("最终验证迁移结果（新连接）...")
        verification_engine = create_engine(settings.database_url, pool_pre_ping=True)
        with verification_engine.connect() as verify_conn:
            # 确认当前数据库
            db_result = verify_conn.execute(text("SELECT current_database()"))
            current_db = db_result.fetchone()[0]
            logger.info(f"验证数据库: {current_db}")
            
            # 获取所有表
            tables_result = verify_conn.execute(text("""
                SELECT tablename 
                FROM pg_tables 
                WHERE schemaname = 'public'
                ORDER BY tablename
            """))
            tables = [row[0] for row in tables_result]
            logger.info(f"最终验证 - 数据库中的表 ({len(tables)} 个): {', '.join(tables) if tables else '(无)'}")
            
            if not tables:
                logger.error("⚠️  严重错误: 最终验证时仍然没有找到任何表！")
                logger.error("迁移可能执行在了错误的数据库，或者事务被回滚")
                logger.error("请检查:")
                logger.error("1. Alembic 配置的数据库 URL")
                logger.error("2. 迁移是否执行在了 web3signer 数据库")
                logger.error("3. 数据库事务是否已提交")
                raise RuntimeError("迁移验证失败：表不存在")
            
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
                logger.error(f"当前数据库: {current_db}")
                logger.error(f"数据库 URL: {settings.database_url.split('@')[-1]}")
                logger.error("数据库迁移可能未完全执行，请手动运行: alembic upgrade head")
                raise RuntimeError(f"数据库迁移不完整，缺少表: {', '.join(missing_tables)}")
            else:
                logger.info("✓ 所有关键表已存在，迁移验证通过")
                
            # 检查 alembic_version 表的内容
            try:
                version_result = verify_conn.execute(text("SELECT version_num FROM alembic_version"))
                final_version = version_result.fetchone()
                if final_version:
                    logger.info(f"✓ 最终迁移版本: {final_version[0]}")
            except Exception as e:
                logger.warning(f"无法读取迁移版本: {e}")
            
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

