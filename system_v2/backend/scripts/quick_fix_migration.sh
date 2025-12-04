#!/bin/bash
# 快速修复 Alembic 迁移问题的脚本

set -e

echo "=========================================="
echo "Alembic 迁移修复脚本"
echo "=========================================="

# 获取数据库连接信息
DB_URL="${DATABASE_URL:-postgresql://postgres:password@localhost:5432/validator_db}"

echo "使用数据库: $DB_URL"

# 提取数据库连接信息
DB_HOST=$(echo $DB_URL | sed -n 's/.*@\([^:]*\):.*/\1/p')
DB_PORT=$(echo $DB_URL | sed -n 's/.*:\([0-9]*\)\/.*/\1/p')
DB_NAME=$(echo $DB_URL | sed -n 's/.*\/\([^?]*\).*/\1/p')
DB_USER=$(echo $DB_URL | sed -n 's/.*:\/\/\([^:]*\):.*/\1/p')

echo "连接信息:"
echo "  主机: $DB_HOST"
echo "  端口: $DB_PORT"
echo "  数据库: $DB_NAME"
echo "  用户: $DB_USER"
echo ""

# 检查 alembic_version 表
echo "检查 alembic_version 表..."
psql "$DB_URL" -c "SELECT version_num FROM alembic_version;" 2>/dev/null || {
    echo "⚠️  alembic_version 表不存在或为空"
    echo "创建 alembic_version 表..."
    psql "$DB_URL" -c "CREATE TABLE IF NOT EXISTS alembic_version (version_num VARCHAR(32) PRIMARY KEY);"
}

# 检查 validator_keys 表的字段
echo ""
echo "检查 validator_keys 表字段..."
HAS_SLASHED_AT=$(psql "$DB_URL" -t -c "SELECT COUNT(*) FROM information_schema.columns WHERE table_name='validator_keys' AND column_name='slashed_at';" | tr -d ' ')
HAS_STATUS_HISTORY=$(psql "$DB_URL" -t -c "SELECT COUNT(*) FROM information_schema.columns WHERE table_name='validator_keys' AND column_name='status_history';" | tr -d ' ')

echo "  slashed_at: $([ "$HAS_SLASHED_AT" = "1" ] && echo "✅ 存在" || echo "❌ 缺失")"
echo "  status_history: $([ "$HAS_STATUS_HISTORY" = "1" ] && echo "✅ 存在" || echo "❌ 缺失")"

# 确定目标版本
if [ "$HAS_SLASHED_AT" = "1" ] && [ "$HAS_STATUS_HISTORY" = "1" ]; then
    TARGET_VERSION="113ec78fdd17"
    echo ""
    echo "✅ 所有字段都存在，标记为最新版本: $TARGET_VERSION"
else
    TARGET_VERSION="fix_tx_hash_unique"
    echo ""
    echo "⚠️  缺失字段，标记为: $TARGET_VERSION（添加字段之前的版本）"
fi

# 标记版本
echo ""
echo "标记 Alembic 版本为: $TARGET_VERSION"
psql "$DB_URL" -c "INSERT INTO alembic_version (version_num) VALUES ('$TARGET_VERSION') ON CONFLICT (version_num) DO UPDATE SET version_num = '$TARGET_VERSION';"

echo ""
echo "✅ 版本标记完成！"
echo ""
echo "现在可以运行迁移:"
echo "  python -m alembic upgrade head"

