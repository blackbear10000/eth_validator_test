#!/usr/bin/env python3
"""
快速检查和修复 Alembic 迁移状态
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine, text, inspect
from app.config import settings

def main():
    engine = create_engine(settings.database_url, pool_pre_ping=True)
    inspector = inspect(engine)
    
    print("=" * 60)
    print("检查数据库状态...")
    print("=" * 60)
    
    # 检查表是否存在
    tables = inspector.get_table_names()
    print(f"\n✅ 数据库表: {', '.join(tables)}")
    
    # 检查 validator_keys 表的列
    if 'validator_keys' in tables:
        columns = inspector.get_columns('validator_keys')
        column_names = {col['name'] for col in columns}
        print(f"\n📋 validator_keys 表列 ({len(column_names)} 个):")
        for col in sorted(column_names):
            print(f"  - {col}")
        
        # 检查缺失的字段
        required = {'slashed_at', 'status_history'}
        missing = required - column_names
        
        if missing:
            print(f"\n⚠️  缺失字段: {missing}")
        else:
            print(f"\n✅ 所有必需字段都存在")
    
    # 检查 alembic_version 表
    if 'alembic_version' in tables:
        with engine.connect() as conn:
            result = conn.execute(text("SELECT version_num FROM alembic_version"))
            row = result.fetchone()
            if row:
                print(f"\n✅ Alembic 版本: {row[0]}")
            else:
                print(f"\n⚠️  alembic_version 表为空")
    else:
        print(f"\n⚠️  alembic_version 表不存在")
    
    print("\n" + "=" * 60)
    print("修复建议:")
    print("=" * 60)
    
    # 如果表存在但版本表为空或不存在
    if 'validator_keys' in tables:
        if 'alembic_version' not in tables:
            print("\n1. 创建 alembic_version 表:")
            print("   CREATE TABLE alembic_version (version_num VARCHAR(32) PRIMARY KEY);")
        
        # 检查缺失字段
        if 'validator_keys' in tables:
            columns = inspector.get_columns('validator_keys')
            column_names = {col['name'] for col in columns}
            missing = {'slashed_at', 'status_history'} - column_names
            
            if missing:
                print("\n2. 标记版本为 fix_tx_hash_unique（添加 slashed_at 之前的版本）:")
                print("   INSERT INTO alembic_version (version_num) VALUES ('fix_tx_hash_unique');")
                print("   或者如果已存在:")
                print("   UPDATE alembic_version SET version_num = 'fix_tx_hash_unique';")
                print("\n3. 然后运行迁移:")
                print("   python -m alembic upgrade head")
            else:
                print("\n2. 标记版本为最新版本:")
                print("   INSERT INTO alembic_version (version_num) VALUES ('113ec78fdd17');")
                print("   或者如果已存在:")
                print("   UPDATE alembic_version SET version_num = '113ec78fdd17';")

if __name__ == '__main__':
    main()

