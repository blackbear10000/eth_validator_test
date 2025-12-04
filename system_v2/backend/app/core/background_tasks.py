"""
后台任务调度
定期执行同步和监听任务
"""
import logging
import asyncio
from datetime import datetime
from typing import Optional

from sqlalchemy.orm import Session
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.config import settings
from app.services.sync_service import SyncService
from app.services.withdrawal_listener import WithdrawalListener
from app.services.deposit_sync_scheduler import start_scheduler as start_deposit_sync_scheduler, stop_scheduler as stop_deposit_sync_scheduler
from app.dependencies import get_db

logger = logging.getLogger(__name__)


class BackgroundTaskScheduler:
    """
    后台任务调度器
    定期执行同步和监听任务
    """
    
    def __init__(self):
        """初始化调度器"""
        self.running = False
        self.tasks = []
        
        # 创建数据库连接和会话工厂
        engine = create_engine(
            settings.database_url,
            pool_pre_ping=True,
            pool_size=5,
            max_overflow=10
        )
        self.SessionLocal = sessionmaker(bind=engine)
    
    def get_db_session(self) -> Session:
        """获取新的数据库会话"""
        return self.SessionLocal()
    
    async def sync_validator_states(self):
        """
        定期同步验证者状态
        """
        logger.info("开始定期同步验证者状态")
        
        while self.running:
            db = None
            try:
                db = self.get_db_session()
                sync_service = SyncService(db)
                # 使用正确的方法名
                result = sync_service.sync_all_pending_validators()
                db.commit()
                
                logger.info("验证者状态同步完成")
                
                # 等待下一个同步周期（1 epoch = 12 秒，实际可以更长）
                await asyncio.sleep(settings.beacon_api_sync_interval)
                
            except Exception as e:
                logger.error(f"同步验证者状态失败: {e}")
                if db:
                    try:
                        db.rollback()
                    except Exception:
                        pass
                await asyncio.sleep(60)  # 出错后等待 1 分钟再试
            finally:
                if db:
                    try:
                        db.close()
                    except Exception:
                        pass
    
    async def sync_withdrawal_events(self):
        """
        定期同步取款事件
        """
        logger.info("开始定期同步取款事件")
        
        while self.running:
            db = None
            try:
                db = self.get_db_session()
                listener = WithdrawalListener(db)
                results = listener.sync_all_validators()
                db.commit()
                
                logger.info(
                    f"取款事件同步完成: {results['synced']}/{results['total']} 成功, "
                    f"发现 {results['withdrawals_found']} 个取款事件"
                )
                
                # 每 5 分钟同步一次
                await asyncio.sleep(300)
                
            except Exception as e:
                logger.error(f"同步取款事件失败: {e}")
                if db:
                    try:
                        db.rollback()
                    except Exception:
                        pass
                await asyncio.sleep(60)  # 出错后等待 1 分钟再试
            finally:
                if db:
                    try:
                        db.close()
                    except Exception:
                        pass
    
    async def start(self):
        """启动所有后台任务"""
        if self.running:
            logger.warning("后台任务已在运行")
            return
        
        self.running = True
        logger.info("启动后台任务调度器")
        
        # 启动同步任务
        task1 = asyncio.create_task(self.sync_validator_states())
        self.tasks.append(task1)
        
        # 启动取款事件同步任务
        task2 = asyncio.create_task(self.sync_withdrawal_events())
        self.tasks.append(task2)
        
        logger.info(f"已启动 {len(self.tasks)} 个后台任务")
    
    async def stop(self):
        """停止所有后台任务"""
        if not self.running:
            return
        
        logger.info("停止后台任务调度器")
        self.running = False
        
        # 取消所有任务
        for task in self.tasks:
            task.cancel()
        
        # 等待任务完成
        await asyncio.gather(*self.tasks, return_exceptions=True)
        
        self.tasks = []
        
        logger.info("后台任务调度器已停止")


# 全局调度器实例
_scheduler: Optional[BackgroundTaskScheduler] = None


def get_scheduler() -> BackgroundTaskScheduler:
    """获取全局调度器实例"""
    global _scheduler
    if _scheduler is None:
        _scheduler = BackgroundTaskScheduler()
    return _scheduler


async def start_background_tasks():
    """启动后台任务（在应用启动时调用）"""
    scheduler = get_scheduler()
    await scheduler.start()
    
    # 启动存款同步调度器（同步方法，在后台线程中运行）
    start_deposit_sync_scheduler()


async def stop_background_tasks():
    """停止后台任务（在应用关闭时调用）"""
    scheduler = get_scheduler()
    await scheduler.stop()
    
    # 停止存款同步调度器（同步方法）
    stop_deposit_sync_scheduler()

