"""
数据库初始化模块
直接使用 SQLAlchemy 创建所有表，不依赖 Alembic 迁移
用于快速初始化和修复迁移问题
"""
import logging
from sqlalchemy import create_engine, text, inspect
from sqlalchemy.exc import OperationalError

from app.config import settings
from app.models.database import Base

logger = logging.getLogger(__name__)


def init_database(force_recreate: bool = False) -> bool:
    """
    初始化数据库，创建所有表
    
    Args:
        force_recreate: 如果为 True，会先删除所有表再创建（危险操作）
        
    Returns:
        是否成功
    """
    try:
        engine = create_engine(settings.database_url, pool_pre_ping=True)
        
        # 确认数据库连接
        with engine.connect() as conn:
            db_result = conn.execute(text("SELECT current_database()"))
            current_db = db_result.fetchone()[0]
            logger.info(f"初始化数据库: {current_db}")
            
            # 检查表是否存在
            inspector = inspect(engine)
            existing_tables = inspector.get_table_names()
            
            if existing_tables:
                if force_recreate:
                    logger.warning(f"强制重建：删除现有表 {len(existing_tables)} 个")
                    # 删除所有表（按依赖顺序）
                    Base.metadata.drop_all(engine)
                    existing_tables = []
                else:
                    logger.info(f"数据库已有 {len(existing_tables)} 个表: {', '.join(existing_tables)}")
                    # 检查关键表是否存在
                    required_tables = [
                        'validator_keys',
                        'client_instances',
                        'validator_client_keys',
                        'deposit_transactions',
                        'withdrawal_events',
                        'batch_deposit_contracts',
                        'users',  # 用户表
                        'audit_logs',  # 审计日志表
                        'exit_records'  # 退出记录表
                    ]
                    missing_tables = [t for t in required_tables if t not in existing_tables]
                    if not missing_tables:
                        logger.info("所有关键表已存在，检查是否有新表需要创建...")
                        # 即使所有关键表都存在，也调用 create_all 以确保新表被创建
                        # create_all 只会创建不存在的表，不会影响已存在的表
                        Base.metadata.create_all(engine)
                        # 再次检查是否有新表被创建
                        inspector = inspect(engine)
                        updated_tables = inspector.get_table_names()
                        if len(updated_tables) > len(existing_tables):
                            new_tables = [t for t in updated_tables if t not in existing_tables]
                            logger.info(f"创建了新表: {', '.join(new_tables)}")
                        return True
                    else:
                        logger.info(f"缺少表: {', '.join(missing_tables)}，将创建缺失的表")
            
            # 创建所有表
            logger.info("创建数据库表...")
            Base.metadata.create_all(engine)
            
            # 验证表是否创建成功
            inspector = inspect(engine)
            created_tables = inspector.get_table_names()
            logger.info(f"数据库表创建完成，共 {len(created_tables)} 个表: {', '.join(sorted(created_tables))}")
            
            # 检查关键表
            required_tables = [
                'validator_keys',
                'client_instances',
                'validator_client_keys',
                'deposit_transactions',
                'withdrawal_events',
                'batch_deposit_contracts',
                'users',  # 用户表
                'audit_logs',  # 审计日志表
                'exit_records'  # 退出记录表
            ]
            missing_tables = [t for t in required_tables if t not in created_tables]
            if missing_tables:
                logger.error(f"创建失败，缺少表: {', '.join(missing_tables)}")
                return False
            
            logger.info("✓ 数据库初始化成功")
            return True
            
    except Exception as e:
        logger.error(f"数据库初始化失败: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False


def check_database_schema() -> dict:
    """
    检查数据库架构
    
    Returns:
        包含表列表和状态的字典
    """
    try:
        engine = create_engine(settings.database_url, pool_pre_ping=True)
        inspector = inspect(engine)
        
        with engine.connect() as conn:
            db_result = conn.execute(text("SELECT current_database()"))
            current_db = db_result.fetchone()[0]
        
        tables = inspector.get_table_names()
        
        required_tables = [
            'validator_keys',
            'client_instances',
            'validator_client_keys',
            'deposit_transactions',
            'withdrawal_events',
            'batch_deposit_contracts',
            'users',  # 用户表
            'audit_logs',  # 审计日志表
            'exit_records'  # 退出记录表
        ]
        
        return {
            'database': current_db,
            'tables': tables,
            'table_count': len(tables),
            'required_tables': required_tables,
            'missing_tables': [t for t in required_tables if t not in tables],
            'is_complete': all(t in tables for t in required_tables)
        }
    except Exception as e:
        logger.error(f"检查数据库架构失败: {e}")
        return {
            'error': str(e),
            'is_complete': False
        }

