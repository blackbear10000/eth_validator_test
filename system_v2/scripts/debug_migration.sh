#!/bin/bash
# 调试迁移问题的脚本
# 在服务器上运行此脚本来诊断迁移问题

set -e

echo "=========================================="
echo "迁移问题诊断脚本"
echo "=========================================="

# 检查是否在容器内
if [ -f /.dockerenv ] || [ -n "$DOCKER_CONTAINER" ]; then
    CONTAINER_MODE=true
    echo "在容器内运行"
else
    CONTAINER_MODE=false
    echo "在主机上运行，将使用 docker exec"
fi

echo ""

# 1. 检查数据库列表
echo "1. 检查数据库列表:"
if [ "$CONTAINER_MODE" = true ]; then
    psql -U postgres -c "\l" | grep -E "web3signer|validator_db"
else
    docker exec postgres psql -U postgres -c "\l" | grep -E "web3signer|validator_db"
fi
echo ""

# 2. 检查 validator_db 中的表
echo "2. 检查 validator_db 中的表:"
if [ "$CONTAINER_MODE" = true ]; then
    psql -U postgres -d validator_db -c "\dt"
else
    docker exec postgres psql -U postgres -d validator_db -c "\dt"
fi
echo ""

# 3. 检查 alembic_version 表
echo "3. 检查 alembic_version 表:"
if [ "$CONTAINER_MODE" = true ]; then
    psql -U postgres -d validator_db -c "SELECT * FROM alembic_version;" 2>&1 || echo "  alembic_version 表不存在"
else
    docker exec postgres psql -U postgres -d validator_db -c "SELECT * FROM alembic_version;" 2>&1 || echo "  alembic_version 表不存在"
fi
echo ""

# 4. 检查 web3signer 数据库中的表（可能迁移执行在了这里）
echo "4. 检查 web3signer 数据库中的表:"
if [ "$CONTAINER_MODE" = true ]; then
    psql -U postgres -d web3signer -c "\dt" | head -20
else
    docker exec postgres psql -U postgres -d web3signer -c "\dt" | head -20
fi
echo ""

# 5. 检查 web3signer 中的 alembic_version
echo "5. 检查 web3signer 中的 alembic_version:"
if [ "$CONTAINER_MODE" = true ]; then
    psql -U postgres -d web3signer -c "SELECT * FROM alembic_version;" 2>&1 || echo "  alembic_version 表不存在"
else
    docker exec postgres psql -U postgres -d web3signer -c "SELECT * FROM alembic_version;" 2>&1 || echo "  alembic_version 表不存在"
fi
echo ""

# 6. 检查后端环境变量
echo "6. 检查后端环境变量:"
if [ "$CONTAINER_MODE" = true ]; then
    echo "  DATABASE_URL: $DATABASE_URL"
else
    docker exec backend env | grep DATABASE_URL || echo "  未找到 DATABASE_URL"
fi
echo ""

# 7. 尝试手动运行迁移
echo "7. 尝试手动运行迁移:"
if [ "$CONTAINER_MODE" = true ]; then
    cd /app
    alembic current
    echo ""
    echo "运行迁移..."
    alembic upgrade head
else
    echo "  请在容器内运行: docker exec -it backend bash -c 'cd /app && alembic upgrade head'"
fi
echo ""

# 8. 再次检查表
echo "8. 迁移后再次检查表:"
if [ "$CONTAINER_MODE" = true ]; then
    psql -U postgres -d validator_db -c "\dt"
else
    docker exec postgres psql -U postgres -d validator_db -c "\dt"
fi
echo ""

echo "=========================================="
echo "诊断完成"
echo "=========================================="

