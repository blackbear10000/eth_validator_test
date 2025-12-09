#!/bin/bash
#
# Kurtosis Enclave 清理脚本
# 用于清理异常状态的 Kurtosis enclave
#

set -e

ENCLAVE_NAME="${1:-eth-devnet}"

echo "=========================================="
echo "Kurtosis Enclave 清理脚本"
echo "Enclave 名称: $ENCLAVE_NAME"
echo "=========================================="
echo ""

# 1. 检查 enclave 是否存在
echo "1. 检查 enclave 状态..."
if kurtosis enclave ls | grep -q "$ENCLAVE_NAME"; then
    echo "   ✓ Enclave '$ENCLAVE_NAME' 存在于列表中"
    
    # 显示详细信息
    echo ""
    echo "2. Enclave 详细信息:"
    echo "----------------------------------------"
    kurtosis enclave inspect "$ENCLAVE_NAME" || echo "   ⚠ 无法获取详细信息（可能是异常状态）"
    echo "----------------------------------------"
    echo ""
    
    # 2. 尝试停止 enclave
    echo "3. 尝试停止 enclave..."
    if kurtosis enclave stop "$ENCLAVE_NAME" 2>/dev/null; then
        echo "   ✓ Enclave 已停止"
    else
        echo "   ⚠ 停止失败或 enclave 已经停止"
    fi
    echo ""
    
    # 3. 移除 enclave
    echo "4. 移除 enclave..."
    if kurtosis enclave rm "$ENCLAVE_NAME" 2>/dev/null; then
        echo "   ✓ Enclave 已移除"
    else
        echo "   ⚠ 移除失败，尝试强制移除..."
        # 尝试强制移除
        kurtosis enclave rm "$ENCLAVE_NAME" --force 2>/dev/null || echo "   ✗ 强制移除也失败"
    fi
    echo ""
    
    # 4. 验证移除结果
    echo "5. 验证移除结果..."
    if kurtosis enclave ls | grep -q "$ENCLAVE_NAME"; then
        echo "   ⚠ Enclave 仍在列表中，可能需要手动清理 Docker 容器"
        echo ""
        echo "   尝试查找相关的 Docker 容器:"
        docker ps -a | grep -i kurtosis | grep -i "$ENCLAVE_NAME" || echo "   未找到相关容器"
    else
        echo "   ✓ Enclave 已成功移除"
    fi
else
    echo "   ℹ Enclave '$ENCLAVE_NAME' 不存在于列表中"
fi

echo ""
echo "=========================================="
echo "清理完成"
echo "=========================================="

