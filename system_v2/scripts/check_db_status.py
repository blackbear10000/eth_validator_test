#!/usr/bin/env python3
"""
检查数据库状态和迁移情况
"""
import sys
import os

# 添加项目路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

from sqlalchemy import create_engine, text, inspect
from app.config import settings

def check_database():
    """检查数据库状态"""
    print("=" * 50)
    print("数据库状态检查")
    print("=" * 50)
    
    # 显示数据库 URL（隐藏密码）
    db_url_display = settings.database_url.split('@')[-1] if '@' in settings.database_url else settings.database_url
    print(f"\n数据库 URL: postgresql://***@{db_url_display}")
    
    try:
        # 创建引擎
        engine = create_engine(settings.database_url)
        
        # 测试连接
        print("\n1. 测试数据库连接...")
        with engine.connect() as conn:
            result = conn.execute(text("SELECT version()"))
            version = result.fetchone()[0]
            print(f"   ✓ 连接成功")
            print(f"   PostgreSQL 版本: {version.split(',')[0]}")
        
        # 检查数据库是否存在
        print("\n2. 检查数据库...")
        db_name = settings.database_url.split('/')[-1]
        admin_url = settings.database_url.replace(f'/{db_name}', '/postgres')
        admin_engine = create_engine(admin_url, isolation_level="AUTOCOMMIT")
        
        with admin_engine.connect() as conn:
            result = conn.execute(
                text("SELECT 1 FROM pg_database WHERE datname = :db_name"),
                {"db_name": db_name}
            )
            if result.fetchone():
                print(f"   ✓ 数据库 '{db_name}' 存在")
            else:
                print(f"   ✗ 数据库 '{db_name}' 不存在")
                return False
        
        # 检查表
        print("\n3. 检查表结构...")
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        
        expected_tables = [
            'validator_keys',
            'client_instances',
            'validator_client_keys',
            'deposit_transactions',
            'withdrawal_events',
            'batch_deposit_contracts',
            'alembic_version'
        ]
        
        print(f"   找到 {len(tables)} 个表:")
        for table in sorted(tables):
            marker = "✓" if table in expected_tables else "?"
            print(f"   {marker} {table}")
        
        missing_tables = [t for t in expected_tables if t not in tables]
        if missing_tables:
            print(f"\n   ✗ 缺少以下表: {', '.join(missing_tables)}")
            return False
        else:
            print(f"\n   ✓ 所有必需的表都存在")
        
        # 检查 Alembic 版本
        print("\n4. 检查 Alembic 迁移版本...")
        try:
            with engine.connect() as conn:
                result = conn.execute(text("SELECT version_num FROM alembic_version"))
                version = result.fetchone()
                if version:
                    print(f"   当前迁移版本: {version[0]}")
                else:
                    print("   ✗ 未找到迁移版本记录")
                    return False
        except Exception as e:
            print(f"   ✗ 无法读取迁移版本: {e}")
            return False
        
        # 检查 client_instances 表结构
        print("\n5. 检查 client_instances 表结构...")
        if 'client_instances' in tables:
            columns = inspector.get_columns('client_instances')
            print(f"   表有 {len(columns)} 个列:")
            for col in columns:
                print(f"     - {col['name']} ({col['type']})")
        else:
            print("   ✗ client_instances 表不存在")
            return False
        
        print("\n" + "=" * 50)
        print("✓ 数据库状态正常")
        print("=" * 50)
        return True
        
    except Exception as e:
        print(f"\n✗ 错误: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = check_database()
    sys.exit(0 if success else 1)

