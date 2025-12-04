#!/usr/bin/env python3
"""
修复 Alembic 版本表
当数据库表已经存在但 Alembic 版本表未正确记录时使用此脚本
"""
import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine, text, inspect
from app.config import settings

def check_alembic_version():
    """检查 Alembic 版本表状态"""
    engine = create_engine(settings.database_url, pool_pre_ping=True)
    
    with engine.connect() as conn:
        # 检查 alembic_version 表是否存在
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        
        if 'alembic_version' not in tables:
            print("❌ alembic_version 表不存在")
            return None
        
        # 查询当前版本
        result = conn.execute(text("SELECT version_num FROM alembic_version"))
        row = result.fetchone()
        
        if row:
            version = row[0]
            print(f"✅ 当前 Alembic 版本: {version}")
            return version
        else:
            print("⚠️  alembic_version 表存在但为空")
            return None

def check_table_columns():
    """检查 validator_keys 表的列"""
    engine = create_engine(settings.database_url, pool_pre_ping=True)
    inspector = inspect(engine)
    
    if 'validator_keys' not in inspector.get_table_names():
        print("❌ validator_keys 表不存在")
        return {}
    
    columns = inspector.get_columns('validator_keys')
    column_names = {col['name'] for col in columns}
    
    print("\n📋 validator_keys 表列:")
    for col in columns:
        print(f"  - {col['name']}: {col['type']}")
    
    return column_names

def stamp_alembic_version(version: str):
    """标记 Alembic 版本"""
    engine = create_engine(settings.database_url, pool_pre_ping=True)
    
    with engine.connect() as conn:
        # 检查表是否存在
        inspector = inspect(engine)
        if 'alembic_version' not in inspector.get_table_names():
            print("创建 alembic_version 表...")
            conn.execute(text("""
                CREATE TABLE alembic_version (
                    version_num VARCHAR(32) NOT NULL,
                    CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num)
                )
            """))
            conn.commit()
        
        # 检查是否已有版本记录
        result = conn.execute(text("SELECT version_num FROM alembic_version"))
        existing = result.fetchone()
        
        if existing:
            print(f"⚠️  已有版本记录: {existing[0]}")
            response = input(f"是否更新为 {version}? (y/N): ")
            if response.lower() != 'y':
                print("取消操作")
                return False
            conn.execute(text("UPDATE alembic_version SET version_num = :version"), {"version": version})
        else:
            print(f"插入版本记录: {version}")
            conn.execute(text("INSERT INTO alembic_version (version_num) VALUES (:version)"), {"version": version})
        
        conn.commit()
        print(f"✅ 成功标记版本: {version}")
        return True

def main():
    print("=" * 60)
    print("Alembic 版本检查和修复工具")
    print("=" * 60)
    
    # 检查当前版本
    current_version = check_alembic_version()
    
    # 检查表结构
    columns = check_table_columns()
    
    # 检查缺失的字段
    required_columns = {'slashed_at', 'status_history'}
    missing_columns = required_columns - columns
    
    print(f"\n📊 分析结果:")
    print(f"  - Alembic 版本: {current_version or '未设置'}")
    print(f"  - 缺失字段: {missing_columns if missing_columns else '无'}")
    
    # 确定应该标记的版本
    # 根据迁移链：001 -> 742b2ef76cff -> ab34d9f05edb -> c74d483d28d5 -> fix_tx_hash_unique -> 113ec78fdd17
    # 如果表已经存在，可能已经应用了部分迁移
    
    if not current_version:
        print("\n💡 建议操作:")
        if missing_columns:
            print("  数据库表已存在，但缺少新字段。")
            print("  建议标记为最新迁移版本，然后运行迁移添加缺失字段。")
            
            # 根据缺失字段判断应该标记的版本
            if 'slashed_at' in missing_columns or 'status_history' in missing_columns:
                target_version = 'fix_tx_hash_unique'  # 标记到添加 slashed_at 之前的版本
                print(f"\n  将标记版本为: {target_version}")
                print("  然后运行迁移添加 slashed_at 和 status_history 字段")
            else:
                target_version = '113ec78fdd17'  # 最新版本
                print(f"\n  将标记版本为: {target_version}")
        else:
            target_version = '113ec78fdd17'  # 所有字段都存在，标记为最新版本
            print(f"\n  所有字段都存在，将标记为最新版本: {target_version}")
        
        response = input("\n是否执行标记操作? (y/N): ")
        if response.lower() == 'y':
            stamp_alembic_version(target_version)
            print("\n✅ 完成！现在可以运行: python -m alembic upgrade head")
        else:
            print("取消操作")
    elif missing_columns:
        print(f"\n⚠️  当前版本: {current_version}")
        print(f"   缺失字段: {missing_columns}")
        print("\n💡 建议: 直接运行迁移添加缺失字段")
        print("   python -m alembic upgrade head")
    else:
        print("\n✅ 一切正常！数据库版本和表结构都正确。")

if __name__ == '__main__':
    main()

