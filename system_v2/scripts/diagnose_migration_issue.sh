#!/bin/bash
# 诊断迁移问题脚本

set -e

echo "=========================================="
echo "数据库迁移问题诊断"
echo "=========================================="

# 检查 PostgreSQL 容器是否运行
if ! docker ps | grep -q postgres; then
    echo "✗ PostgreSQL 容器未运行"
    exit 1
fi

echo "✓ PostgreSQL 容器正在运行"
echo ""

# 检查数据库列表
echo "1. 检查数据库列表:"
docker exec postgres psql -U postgres -c "\l" | grep -E "web3signer|validator_db" || echo "  未找到相关数据库"
echo ""

# 检查 validator_db 数据库中的表
echo "2. 检查 validator_db 数据库中的表:"
if docker exec postgres psql -U postgres -d validator_db -c "\dt" 2>/dev/null; then
    echo ""
    echo "3. 检查关键表是否存在:"
    for table in validator_keys client_instances deposit_transactions alembic_version; do
        if docker exec postgres psql -U postgres -d validator_db -c "\d $table" >/dev/null 2>&1; then
            echo "  ✓ $table 存在"
        else
            echo "  ✗ $table 不存在"
        fi
    done
else
    echo "  ✗ 无法连接到 validator_db 数据库"
fi
echo ""

# 检查 web3signer 数据库中的表（可能迁移执行在了这里）
echo "4. 检查 web3signer 数据库中的表（可能迁移执行在了这里）:"
if docker exec postgres psql -U postgres -d web3signer -c "\dt" 2>/dev/null | grep -E "validator_keys|client_instances|alembic_version"; then
    echo "  ⚠️  警告: 在 web3signer 数据库中发现了应用表！"
    echo "  这说明迁移可能执行在了错误的数据库上"
fi
echo ""

# 检查 alembic_version 表
echo "5. 检查迁移版本:"
echo "  validator_db:"
docker exec postgres psql -U postgres -d validator_db -c "SELECT * FROM alembic_version;" 2>/dev/null || echo "    alembic_version 表不存在"
echo ""
echo "  web3signer:"
docker exec postgres psql -U postgres -d web3signer -c "SELECT * FROM alembic_version;" 2>/dev/null || echo "    alembic_version 表不存在"
echo ""

# 检查后端容器的环境变量
echo "6. 检查后端容器的数据库配置:"
if docker ps | grep -q backend; then
    echo "  DATABASE_URL:"
    docker exec backend env | grep DATABASE_URL || echo "    未设置"
else
    echo "  ✗ 后端容器未运行"
fi
echo ""

echo "=========================================="
echo "诊断完成"
echo "=========================================="

