#!/usr/bin/env python3
"""
自动修复 Alembic 迁移问题
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine, text, inspect
from app.config import settings

def main():
    print("=" * 60)
    print("自动修复 Alembic 迁移问题")
    print("=" * 60)
    
    engine = create_engine(settings.database_url, pool_pre_ping=True)
    inspector = inspect(engine)
    
    with engine.connect() as conn:
        # 1. 检查并创建 alembic_version 表
        tables = inspector.get_table_names()
        if 'alembic_version' not in tables:
            print("\n1. 创建 alembic_version 表...")
            conn.execute(text("""
                CREATE TABLE alembic_version (
                    version_num VARCHAR(32) PRIMARY KEY
                )
            """))
            conn.commit()
            print("   ✅ alembic_version 表已创建")
        else:
            print("\n1. ✅ alembic_version 表已存在")
        
        # 2. 检查 validator_keys 表的字段
        if 'validator_keys' not in tables:
            print("\n❌ 错误: validator_keys 表不存在！")
            print("   请先运行初始迁移或使用 db_init.py 创建表")
            return
        
        columns = inspector.get_columns('validator_keys')
        column_names = {col['name'] for col in columns}
        
        print(f"\n2. 检查 validator_keys 表字段...")
        print(f"   当前有 {len(column_names)} 个字段")
        
        has_slashed_at = 'slashed_at' in column_names
        has_status_history = 'status_history' in column_names
        
        print(f"   slashed_at: {'✅' if has_slashed_at else '❌'}")
        print(f"   status_history: {'✅' if has_status_history else '❌'}")
        
        # 3. 确定目标版本
        if has_slashed_at and has_status_history:
            target_version = '113ec78fdd17'
            print(f"\n3. ✅ 所有字段都存在，标记为最新版本: {target_version}")
        else:
            target_version = 'fix_tx_hash_unique'
            print(f"\n3. ⚠️  缺失字段，标记为: {target_version}")
            print("   运行迁移后将添加缺失字段")
        
        # 4. 标记版本
        print(f"\n4. 标记 Alembic 版本为: {target_version}")
        
        # 检查是否已有版本记录
        result = conn.execute(text("SELECT version_num FROM alembic_version"))
        existing = result.fetchone()
        
        if existing:
            current_version = existing[0]
            if current_version == target_version:
                print(f"   ✅ 版本已经是 {target_version}，无需更新")
            else:
                print(f"   ⚠️  当前版本: {current_version}")
                print(f"   📝 更新为: {target_version}")
                conn.execute(
                    text("UPDATE alembic_version SET version_num = :version"),
                    {"version": target_version}
                )
                conn.commit()
                print(f"   ✅ 版本已更新")
        else:
            print(f"   📝 插入版本记录: {target_version}")
            conn.execute(
                text("INSERT INTO alembic_version (version_num) VALUES (:version)"),
                {"version": target_version}
            )
            conn.commit()
            print(f"   ✅ 版本已插入")
        
        # 5. 验证
        result = conn.execute(text("SELECT version_num FROM alembic_version"))
        final_version = result.fetchone()[0]
        print(f"\n5. ✅ 最终版本: {final_version}")
        
        print("\n" + "=" * 60)
        print("修复完成！")
        print("=" * 60)
        
        if not (has_slashed_at and has_status_history):
            print("\n下一步: 运行迁移添加缺失字段")
            print("  python -m alembic upgrade head")
        else:
            print("\n✅ 数据库已是最新状态，无需运行迁移")

if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        print(f"\n❌ 错误: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

