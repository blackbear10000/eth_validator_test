#!/usr/bin/env python3
"""
数据库迁移脚本
创建应用数据库和表结构
"""
import sys
import os

# 检查依赖
try:
    import psycopg2
except ImportError:
    print("错误: 缺少 psycopg2-binary 模块")
    print("请运行: pip install -r requirements.txt")
    sys.exit(1)

# 添加项目路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

from sqlalchemy import create_engine, text
from app.models.database import Base
from app.config import settings

def create_database():
    """创建应用数据库"""
    # 连接到默认 postgres 数据库
    admin_engine = create_engine(
        settings.database_url.replace('/validator_db', '/postgres'),
        isolation_level="AUTOCOMMIT"
    )
    
    db_name = settings.database_url.split('/')[-1]
    
    with admin_engine.connect() as conn:
        # 检查数据库是否存在
        result = conn.execute(
            text("SELECT 1 FROM pg_database WHERE datname = :db_name"),
            {"db_name": db_name}
        )
        
        if result.fetchone():
            print(f"数据库 {db_name} 已存在")
        else:
            # 创建数据库
            conn.execute(text(f'CREATE DATABASE {db_name}'))
            print(f"数据库 {db_name} 创建成功")

def create_tables():
    """创建表结构"""
    engine = create_engine(settings.database_url)
    
    print("创建表结构...")
    Base.metadata.create_all(engine)
    print("表结构创建成功")

def main():
    """主函数"""
    print("=" * 50)
    print("数据库迁移工具")
    print("=" * 50)
    
    try:
        # 创建数据库
        create_database()
        
        # 创建表
        create_tables()
        
        print("=" * 50)
        print("迁移完成!")
        print("=" * 50)
        
    except Exception as e:
        print(f"错误: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()

