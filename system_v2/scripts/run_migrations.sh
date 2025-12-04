#!/bin/bash
# 手动运行数据库迁移脚本

set -e

echo "=========================================="
echo "运行数据库迁移"
echo "=========================================="

# 获取脚本所在目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$SCRIPT_DIR/../backend"

# 检查后端目录
if [ ! -d "$BACKEND_DIR" ]; then
    echo "错误: 后端目录不存在: $BACKEND_DIR"
    exit 1
fi

cd "$BACKEND_DIR"

# 检查环境变量
if [ -z "$DATABASE_URL" ]; then
    echo "警告: DATABASE_URL 未设置，使用默认值"
    export DATABASE_URL="postgresql://postgres:password@localhost:5432/validator_db"
fi

echo "数据库 URL: ${DATABASE_URL/@*/@***}"  # 隐藏密码

# 检查 alembic.ini
if [ ! -f "alembic.ini" ]; then
    echo "错误: alembic.ini 不存在"
    exit 1
fi

echo ""
echo "检查当前迁移状态..."
alembic current

echo ""
echo "执行迁移到最新版本..."
alembic upgrade head

echo ""
echo "验证迁移结果..."
alembic current

echo ""
echo "=========================================="
echo "迁移完成！"
echo "=========================================="

