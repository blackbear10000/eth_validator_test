#!/bin/bash
# Vault 健康检查脚本
# 用于诊断 Vault 服务状态

set -e

VAULT_ADDR="${VAULT_ADDR:-http://localhost:8200}"
echo "检查 Vault 服务: $VAULT_ADDR"
echo "=========================================="

# 1. 检查 Vault 是否可访问
echo "1. 检查 Vault 是否可访问..."
if curl -s -f "$VAULT_ADDR/v1/sys/health" > /dev/null 2>&1; then
    echo "   ✓ Vault 服务可访问"
else
    echo "   ✗ Vault 服务不可访问"
    echo "   请检查:"
    echo "   - Vault 容器是否运行: docker ps | grep vault"
    echo "   - Vault 端口是否正确: curl $VAULT_ADDR/v1/sys/health"
    exit 1
fi

# 2. 获取健康状态
echo ""
echo "2. 获取 Vault 健康状态..."
HEALTH_RESPONSE=$(curl -s "$VAULT_ADDR/v1/sys/health" 2>&1)
echo "$HEALTH_RESPONSE" | python3 -m json.tool 2>/dev/null || echo "$HEALTH_RESPONSE"

# 3. 检查是否已初始化
echo ""
echo "3. 检查初始化状态..."
INITIALIZED=$(echo "$HEALTH_RESPONSE" | grep -o '"initialized":[^,]*' | cut -d: -f2 | tr -d ' ')
if [ "$INITIALIZED" = "true" ]; then
    echo "   ✓ Vault 已初始化"
else
    echo "   ✗ Vault 未初始化"
    echo "   需要运行: vault operator init"
fi

# 4. 检查是否已解锁
echo ""
echo "4. 检查解锁状态..."
SEALED=$(echo "$HEALTH_RESPONSE" | grep -o '"sealed":[^,]*' | cut -d: -f2 | tr -d ' ')
if [ "$SEALED" = "false" ]; then
    echo "   ✓ Vault 已解锁"
else
    echo "   ✗ Vault 已密封"
    echo "   需要运行: vault operator unseal <unseal-key>"
fi

# 5. 检查 Vault 状态（使用 vault CLI，如果可用）
echo ""
echo "5. 使用 Vault CLI 检查状态..."
if command -v vault >/dev/null 2>&1; then
    export VAULT_ADDR="$VAULT_ADDR"
    vault status 2>&1 || echo "   注意: vault CLI 可能需要认证"
else
    echo "   vault CLI 不可用，跳过"
fi

# 6. 检查后端 API 健康检查端点
echo ""
echo "6. 检查后端 API 健康检查..."
BACKEND_URL="${BACKEND_URL:-http://localhost:8001}"
if curl -s -f "$BACKEND_URL/api/v1/monitoring/health" > /dev/null 2>&1; then
    echo "   ✓ 后端 API 可访问"
    echo "   获取健康检查结果..."
    curl -s "$BACKEND_URL/api/v1/monitoring/health" | python3 -m json.tool 2>/dev/null || curl -s "$BACKEND_URL/api/v1/monitoring/health"
else
    echo "   ✗ 后端 API 不可访问"
    echo "   请检查后端服务是否运行: docker ps | grep backend"
fi

echo ""
echo "=========================================="
echo "诊断完成"

