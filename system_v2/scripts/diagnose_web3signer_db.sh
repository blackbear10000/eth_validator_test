#!/bin/bash

# Web3Signer 数据库诊断和修复脚本

set -e

echo "=========================================="
echo "Web3Signer 数据库诊断工具"
echo "=========================================="
echo ""

# 1. 检查 PostgreSQL 容器状态
echo "🔍 1. 检查 PostgreSQL 容器状态..."
if docker ps | grep -q "postgres"; then
    echo "✅ PostgreSQL 容器正在运行"
    docker ps | grep postgres
else
    echo "❌ PostgreSQL 容器未运行"
    echo "请先启动 PostgreSQL: docker-compose up -d postgres"
    exit 1
fi
echo ""

# 2. 检查 PostgreSQL 版本
echo "🔍 2. 检查 PostgreSQL 服务器版本..."
PG_VERSION=$(docker exec postgres psql -U postgres -t -c "SELECT version();" | head -1)
echo "PostgreSQL 版本: $PG_VERSION"
echo ""

# 3. 检查数据库是否存在
echo "🔍 3. 检查 web3signer 数据库..."
if docker exec postgres psql -U postgres -lqt | cut -d \| -f 1 | grep -qw web3signer; then
    echo "✅ web3signer 数据库存在"
else
    echo "❌ web3signer 数据库不存在"
    echo "创建数据库..."
    docker exec postgres psql -U postgres -c "CREATE DATABASE web3signer;"
fi
echo ""

# 4. 检查 database_version 表
echo "🔍 4. 检查 database_version 表..."
if docker exec postgres psql -U postgres -d web3signer -c "\d database_version" >/dev/null 2>&1; then
    echo "✅ database_version 表存在"
    CURRENT_VERSION=$(docker exec postgres psql -U postgres -d web3signer -t -c "SELECT version FROM database_version WHERE id = 1;" 2>/dev/null | xargs)
    if [ -z "$CURRENT_VERSION" ]; then
        echo "⚠️  数据库版本为空，需要初始化"
        CURRENT_VERSION="未设置"
    else
        echo "当前数据库版本: $CURRENT_VERSION"
        if [ "$CURRENT_VERSION" != "12" ]; then
            echo "⚠️  数据库版本应该是 12，实际是 $CURRENT_VERSION"
        else
            echo "✅ 数据库版本正确 (12)"
        fi
    fi
else
    echo "❌ database_version 表不存在"
    echo "需要执行数据库迁移"
fi
echo ""

# 5. 检查所有必要的表
echo "🔍 5. 检查数据库表结构..."
TABLES=$(docker exec postgres psql -U postgres -d web3signer -t -c "SELECT table_name FROM information_schema.tables WHERE table_schema = 'public' ORDER BY table_name;" 2>/dev/null | xargs)
if [ -z "$TABLES" ]; then
    echo "❌ 数据库中没有表，需要执行迁移"
else
    echo "✅ 数据库表列表:"
    echo "$TABLES" | tr ' ' '\n' | sed 's/^/  - /'
fi
echo ""

# 6. 检查数据库连接
echo "🔍 6. 测试数据库连接..."
if docker exec postgres psql -U postgres -d web3signer -c "SELECT 1;" >/dev/null 2>&1; then
    echo "✅ 数据库连接正常"
else
    echo "❌ 数据库连接失败"
    exit 1
fi
echo ""

# 7. 诊断结果和建议
echo "=========================================="
echo "诊断结果和建议"
echo "=========================================="

if [ "$CURRENT_VERSION" != "12" ] && [ "$CURRENT_VERSION" != "未设置" ]; then
    echo ""
    echo "⚠️  问题：数据库版本不匹配"
    echo "建议：运行修复脚本更新数据库版本"
    echo ""
    echo "修复命令："
    echo "  docker exec postgres psql -U postgres -d web3signer -c \"UPDATE database_version SET version = 12 WHERE id = 1;\""
    echo ""
elif [ "$CURRENT_VERSION" = "未设置" ]; then
    echo ""
    echo "⚠️  问题：数据库版本未设置"
    echo "建议：需要执行完整的数据库迁移"
    echo ""
    echo "修复命令："
    echo "  cd system_v2/infra && docker-compose restart postgres"
    echo "  或者手动执行迁移脚本"
    echo ""
else
    echo ""
    echo "✅ 数据库状态正常"
    echo ""
    echo "如果 Web3Signer 仍然无法启动，请检查："
    echo "  1. Web3Signer 容器日志: docker logs web3signer-1"
    echo "  2. PostgreSQL 容器日志: docker logs postgres"
    echo "  3. 网络连接: docker network inspect validator_network"
    echo ""
fi

