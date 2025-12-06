#!/bin/bash

# 修复 Web3Signer 数据库版本脚本

set -e

echo "=========================================="
echo "修复 Web3Signer 数据库版本"
echo "=========================================="
echo ""

# 1. 检查 PostgreSQL 容器
if ! docker ps | grep -q "postgres"; then
    echo "❌ PostgreSQL 容器未运行"
    echo "请先启动: cd system_v2/infra && docker-compose up -d postgres"
    exit 1
fi

# 2. 检查 database_version 表是否存在
echo "🔍 检查 database_version 表..."
if ! docker exec postgres psql -U postgres -d web3signer -c "\d database_version" >/dev/null 2>&1; then
    echo "❌ database_version 表不存在，需要先执行数据库迁移"
    echo ""
    echo "请运行数据库迁移脚本："
    echo "  cd system_v2/infra && docker-compose restart postgres"
    echo "  或者手动执行: system_v2/infra/web3signer/init-db-migrations.sh"
    exit 1
fi

# 3. 检查当前版本
echo "🔍 检查当前数据库版本..."
CURRENT_VERSION=$(docker exec postgres psql -U postgres -d web3signer -t -c "SELECT version FROM database_version WHERE id = 1;" 2>/dev/null | xargs)
echo "当前版本: ${CURRENT_VERSION:-未设置}"
echo ""

# 4. 更新数据库版本到 12
echo "🔄 更新数据库版本到 12..."
docker exec postgres psql -U postgres -d web3signer <<EOF
-- 确保 database_version 表存在
CREATE TABLE IF NOT EXISTS database_version (
    id INTEGER PRIMARY KEY,
    version INTEGER NOT NULL
);

-- 更新或插入版本号
INSERT INTO database_version (id, version) VALUES (1, 12)
ON CONFLICT (id) DO UPDATE SET version = 12;

-- 验证版本
SELECT * FROM database_version;
EOF

if [ $? -eq 0 ]; then
    echo "✅ 数据库版本已更新到 12"
else
    echo "❌ 更新数据库版本失败"
    exit 1
fi
echo ""

# 5. 验证版本
echo "🔍 验证数据库版本..."
VERIFIED_VERSION=$(docker exec postgres psql -U postgres -d web3signer -t -c "SELECT version FROM database_version WHERE id = 1;" 2>/dev/null | xargs)
if [ "$VERIFIED_VERSION" = "12" ]; then
    echo "✅ 数据库版本验证成功: $VERIFIED_VERSION"
else
    echo "❌ 数据库版本验证失败，当前版本: ${VERIFIED_VERSION:-未设置}"
    exit 1
fi
echo ""

# 6. 检查是否需要执行迁移
echo "🔍 检查是否需要执行额外的迁移..."
MIGRATION_COUNT=$(docker exec postgres psql -U postgres -d web3signer -t -c "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public';" 2>/dev/null | xargs)
echo "数据库表数量: $MIGRATION_COUNT"

# 检查关键表是否存在
REQUIRED_TABLES=("validators" "signed_blocks" "signed_attestations" "database_version" "metadata" "low_watermarks")
MISSING_TABLES=()

for table in "${REQUIRED_TABLES[@]}"; do
    if ! docker exec postgres psql -U postgres -d web3signer -t -c "SELECT 1 FROM information_schema.tables WHERE table_schema = 'public' AND table_name = '$table';" 2>/dev/null | grep -q 1; then
        MISSING_TABLES+=("$table")
    fi
done

if [ ${#MISSING_TABLES[@]} -gt 0 ]; then
    echo "⚠️  缺少必要的表: ${MISSING_TABLES[*]}"
    echo "建议：执行完整的数据库迁移"
    echo ""
    echo "迁移命令："
    echo "  cd system_v2/infra"
    echo "  docker-compose restart postgres"
    echo "  # 等待迁移完成后再重启 Web3Signer"
else
    echo "✅ 所有必要的表都存在"
fi
echo ""

# 7. 重启 Web3Signer
echo "🔄 重启 Web3Signer 容器..."
if docker ps | grep -q "web3signer-1"; then
    echo "重启 web3signer-1..."
    docker restart web3signer-1 || echo "⚠️  web3signer-1 重启失败（可能未运行）"
fi

if docker ps | grep -q "web3signer-2"; then
    echo "重启 web3signer-2..."
    docker restart web3signer-2 || echo "⚠️  web3signer-2 重启失败（可能未运行）"
fi

echo ""
echo "⏳ 等待 Web3Signer 启动（10秒）..."
sleep 10

# 8. 检查 Web3Signer 状态
echo "🔍 检查 Web3Signer 状态..."
for container in web3signer-1 web3signer-2; do
    if docker ps | grep -q "$container"; then
        echo "检查 $container..."
        if curl -s -f "http://localhost:$([ "$container" = "web3signer-1" ] && echo "9000" || echo "9001")/upcheck" >/dev/null 2>&1; then
            echo "✅ $container 运行正常"
        else
            echo "⚠️  $container 可能还在启动中，请检查日志: docker logs $container"
        fi
    fi
done

echo ""
echo "=========================================="
echo "修复完成！"
echo "=========================================="
echo ""
echo "如果问题仍然存在，请检查："
echo "  1. Web3Signer 日志: docker logs web3signer-1"
echo "  2. PostgreSQL 日志: docker logs postgres"
echo "  3. 网络连接: docker network inspect validator_network"
echo ""

