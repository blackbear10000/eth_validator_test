#!/bin/bash
#
# Kurtosis 诊断脚本
# 用于诊断 Kurtosis enclave 的状态问题
#

set -e

ENCLAVE_NAME="${1:-eth-devnet}"

echo "=========================================="
echo "Kurtosis 诊断脚本"
echo "Enclave 名称: $ENCLAVE_NAME"
echo "=========================================="
echo ""

# 1. 检查 Kurtosis CLI
echo "1. 检查 Kurtosis CLI..."
if command -v kurtosis &> /dev/null; then
    echo "   ✓ Kurtosis CLI 已安装"
    kurtosis --version
else
    echo "   ✗ Kurtosis CLI 未安装"
    exit 1
fi
echo ""

# 2. 检查 Kurtosis Engine
echo "2. 检查 Kurtosis Engine..."
if kurtosis engine status &>/dev/null; then
    echo "   ✓ Kurtosis Engine 正在运行"
    kurtosis engine status
else
    echo "   ⚠ Kurtosis Engine 未运行或无法访问"
fi
echo ""

# 3. 列出所有 enclave
echo "3. 列出所有 enclave:"
echo "----------------------------------------"
kurtosis enclave ls
echo "----------------------------------------"
echo ""

# 4. 检查目标 enclave
echo "4. 检查目标 enclave '$ENCLAVE_NAME'..."
if kurtosis enclave ls | grep -q "$ENCLAVE_NAME"; then
    echo "   ✓ Enclave '$ENCLAVE_NAME' 存在于列表中"
    echo ""
    echo "   详细信息:"
    echo "   ----------------------------------------"
    kurtosis enclave inspect "$ENCLAVE_NAME" || echo "   ⚠ 无法获取详细信息"
    echo "   ----------------------------------------"
    echo ""
    
    # 检查状态字段
    echo "   状态分析:"
    STATUS_OUTPUT=$(kurtosis enclave inspect "$ENCLAVE_NAME" 2>/dev/null || echo "")
    if echo "$STATUS_OUTPUT" | grep -q "Status:"; then
        STATUS=$(echo "$STATUS_OUTPUT" | grep "Status:" | head -1 | sed 's/.*Status:[[:space:]]*//' | tr -d '[:space:]')
        echo "     - Status 字段: $STATUS"
        
        case "$STATUS" in
            RUNNING)
                echo "     - 状态: 运行中"
                ;;
            EMPTY)
                echo "     - 状态: 空（未运行）"
                ;;
            STOPPED)
                echo "     - 状态: 已停止"
                ;;
            *)
                echo "     - 状态: 未知 ($STATUS)"
                ;;
        esac
    else
        echo "     - ⚠ 无法解析 Status 字段"
    fi
    
    # 检查服务
    if echo "$STATUS_OUTPUT" | grep -q "User Services"; then
        SERVICE_COUNT=$(echo "$STATUS_OUTPUT" | sed -n '/User Services/,/^===/p' | grep -E '^[a-f0-9]{12}' | wc -l)
        echo "     - 服务数量: $SERVICE_COUNT"
        if [ "$SERVICE_COUNT" -eq 0 ]; then
            echo "     - ⚠ 没有运行的服务"
        fi
    else
        echo "     - ⚠ 无法找到 User Services 部分"
    fi
    
else
    echo "   ℹ Enclave '$ENCLAVE_NAME' 不存在于列表中"
fi
echo ""

# 5. 检查相关 Docker 容器
echo "5. 检查相关 Docker 容器:"
echo "----------------------------------------"
docker ps -a --filter "name=kurtosis" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" | head -20
echo "----------------------------------------"
echo ""

# 6. 提供清理建议
echo "6. 清理建议:"
if kurtosis enclave ls | grep -q "$ENCLAVE_NAME"; then
    echo "   Enclave 存在，建议执行以下命令清理:"
    echo ""
    echo "   # 停止 enclave"
    echo "   kurtosis enclave stop $ENCLAVE_NAME"
    echo ""
    echo "   # 移除 enclave"
    echo "   kurtosis enclave rm $ENCLAVE_NAME"
    echo ""
    echo "   或者使用清理脚本:"
    echo "   ./scripts/cleanup_kurtosis_enclave.sh $ENCLAVE_NAME"
else
    echo "   Enclave 不存在，无需清理"
fi
echo ""

echo "=========================================="
echo "诊断完成"
echo "=========================================="

