#!/bin/bash
# 测试后端容器能否访问 Vault

set -e

echo "=========================================="
echo "测试后端容器与 Vault 的连接"
echo "=========================================="

# 1. 检查后端容器是否运行
echo "1. 检查后端容器状态..."
if docker ps | grep -q backend; then
    echo "   ✓ 后端容器正在运行"
else
    echo "   ✗ 后端容器未运行"
    exit 1
fi

# 2. 检查后端环境变量
echo ""
echo "2. 检查后端环境变量..."
echo "   VAULT_URL:"
docker exec backend env | grep VAULT_URL || echo "   ✗ VAULT_URL 未设置"
echo "   VAULT_TOKEN:"
docker exec backend env | grep VAULT_TOKEN || echo "   ✗ VAULT_TOKEN 未设置"

# 3. 测试后端能否访问 Vault
echo ""
echo "3. 测试后端容器能否访问 Vault..."
VAULT_URL=$(docker exec backend env | grep VAULT_URL | cut -d= -f2)
if [ -z "$VAULT_URL" ]; then
    VAULT_URL="http://vault-1:8200"
    echo "   使用默认值: $VAULT_URL"
fi

echo "   尝试从后端容器访问: $VAULT_URL/v1/sys/health"
if docker exec backend curl -s -f "$VAULT_URL/v1/sys/health" > /dev/null 2>&1; then
    echo "   ✓ 后端可以访问 Vault"
    echo "   健康状态:"
    docker exec backend curl -s "$VAULT_URL/v1/sys/health" | python3 -m json.tool 2>/dev/null || docker exec backend curl -s "$VAULT_URL/v1/sys/health"
else
    echo "   ✗ 后端无法访问 Vault"
    echo "   错误详情:"
    docker exec backend curl -v "$VAULT_URL/v1/sys/health" 2>&1 | head -20
fi

# 4. 测试 Python hvac 库连接
echo ""
echo "4. 测试 Python hvac 库连接..."
docker exec backend python3 -c "
import hvac
import os
vault_url = os.getenv('VAULT_URL', 'http://vault-1:8200')
print(f'尝试连接: {vault_url}')
try:
    client = hvac.Client(url=vault_url)
    health = client.sys.read_health_status()
    print(f'✓ 连接成功')
    print(f'  Initialized: {health.get(\"initialized\")}')
    print(f'  Sealed: {health.get(\"sealed\")}')
    print(f'  Healthy: {health.get(\"initialized\") and not health.get(\"sealed\")}')
except Exception as e:
    print(f'✗ 连接失败: {e}')
    import traceback
    traceback.print_exc()
" 2>&1

# 5. 检查后端日志中的 Vault 相关错误
echo ""
echo "5. 检查后端日志中的 Vault 相关错误..."
echo "   最近的 Vault 相关日志:"
docker logs backend --tail 50 2>&1 | grep -i vault | tail -10 || echo "   没有找到 Vault 相关日志"

echo ""
echo "=========================================="
echo "测试完成"

