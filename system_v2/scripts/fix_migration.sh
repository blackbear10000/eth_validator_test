#!/bin/bash
# 修复迁移问题的脚本
# 在容器内运行此脚本来手动执行迁移

set -e

echo "=========================================="
echo "修复数据库迁移"
echo "=========================================="

# 检查是否在容器内
if [ ! -f /.dockerenv ] && [ -z "$DOCKER_CONTAINER" ]; then
    echo "此脚本需要在容器内运行"
    echo "使用方法:"
    echo "  docker exec -it backend bash -c 'cd /app && bash /path/to/fix_migration.sh'"
    echo "或者:"
    echo "  docker exec -it backend bash"
    echo "  cd /app"
    echo "  alembic upgrade head"
    exit 1
fi

cd /app || cd "$(dirname "$0")/../backend" || exit 1

echo "当前目录: $(pwd)"
echo ""

# 检查环境变量
if [ -z "$DATABASE_URL" ]; then
    echo "警告: DATABASE_URL 未设置"
    export DATABASE_URL="postgresql://postgres:password@postgres:5432/validator_db"
    echo "使用默认值: $DATABASE_URL"
fi

echo "数据库 URL: ${DATABASE_URL/@*/@***}"
echo ""

# 检查 alembic.ini
if [ ! -f "alembic.ini" ]; then
    echo "错误: alembic.ini 不存在"
    exit 1
fi

# 检查当前迁移版本
echo "1. 检查当前迁移版本..."
alembic current || echo "  未找到迁移版本记录"
echo ""

# 执行迁移
echo "2. 执行迁移..."
alembic upgrade head
echo ""

# 验证迁移结果
echo "3. 验证迁移结果..."
alembic current
echo ""

# 使用 Python 检查表
echo "4. 检查数据库表..."
python3 << 'EOF'
import os
import sys
sys.path.insert(0, '/app')

from sqlalchemy import create_engine, text
from app.config import settings

try:
    engine = create_engine(settings.database_url)
    with engine.connect() as conn:
        # 检查当前数据库
        db_result = conn.execute(text("SELECT current_database()"))
        current_db = db_result.fetchone()[0]
        print(f"   当前数据库: {current_db}")
        
        # 获取所有表
        tables_result = conn.execute(text("""
            SELECT tablename 
            FROM pg_tables 
            WHERE schemaname = 'public'
            ORDER BY tablename
        """))
        tables = [row[0] for row in tables_result]
        print(f"   表数量: {len(tables)}")
        
        # 检查关键表
        required_tables = [
            'validator_keys',
            'client_instances',
            'validator_client_keys',
            'deposit_transactions',
            'withdrawal_events',
            'batch_deposit_contracts',
            'alembic_version'
        ]
        
        print("   关键表状态:")
        for table in required_tables:
            if table in tables:
                print(f"     ✓ {table}")
            else:
                print(f"     ✗ {table} (缺失)")
        
        # 检查 alembic_version
        try:
            version_result = conn.execute(text("SELECT version_num FROM alembic_version"))
            version = version_result.fetchone()
            if version:
                print(f"   迁移版本: {version[0]}")
        except Exception as e:
            print(f"   ⚠️  无法读取迁移版本: {e}")
            
except Exception as e:
    print(f"   ✗ 错误: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
EOF

echo ""
echo "=========================================="
echo "修复完成"
echo "=========================================="

