#!/bin/bash
#
# Kurtosis Enclave 清理脚本
# 用于清理异常状态的 Kurtosis enclave
#
# 使用说明：
#   1. 如果 kurtosis-manager 在 Docker 容器中运行，可以通过容器执行：
#      docker exec kurtosis-manager bash /path/to/cleanup_kurtosis_enclave.sh eth-devnet
#   2. 或者在主机上直接运行（推荐）：
#      ./cleanup_kurtosis_enclave.sh eth-devnet
#

# 不使用 set -e，因为某些命令可能会失败（如停止 EMPTY 状态的 enclave）
# set -e

ENCLAVE_NAME="${1:-eth-devnet}"
USE_DOCKER="${2:-}"

echo "=========================================="
echo "Kurtosis Enclave 清理脚本"
echo "Enclave 名称: $ENCLAVE_NAME"
if [ -n "$USE_DOCKER" ]; then
    echo "执行方式: 通过 Docker 容器 ($USE_DOCKER)"
else
    echo "执行方式: 主机直接执行"
fi
echo "=========================================="
echo ""

# 检查是否在容器内或需要通过容器执行
if [ -n "$USE_DOCKER" ]; then
    KURTOSIS_CMD="docker exec $USE_DOCKER kurtosis"
    DOCKER_CMD="docker"
    echo "使用 Docker 容器执行命令..."
else
    # 检查 kurtosis 命令是否可用
    if ! command -v kurtosis &> /dev/null; then
        echo "⚠ Kurtosis CLI 未在主机上安装"
        echo "尝试通过 kurtosis-manager 容器执行..."
        if docker ps | grep -q kurtosis-manager; then
            echo "找到 kurtosis-manager 容器，使用容器执行..."
            KURTOSIS_CMD="docker exec kurtosis-manager kurtosis"
            DOCKER_CMD="docker"
        else
            echo "❌ 无法找到 kurtosis-manager 容器，请手动指定容器名称"
            echo "用法: $0 $ENCLAVE_NAME <container_name>"
            exit 1
        fi
    else
        KURTOSIS_CMD="kurtosis"
        DOCKER_CMD="docker"
    fi
fi
echo ""

# 1. 检查 enclave 是否存在
echo "1. 检查 enclave 状态..."
if $KURTOSIS_CMD enclave ls | grep -q "$ENCLAVE_NAME"; then
    echo "   ✓ Enclave '$ENCLAVE_NAME' 存在于列表中"
    
    # 显示详细信息并检查状态
    echo ""
    echo "2. Enclave 详细信息:"
    echo "----------------------------------------"
    INSPECT_OUTPUT=$($KURTOSIS_CMD enclave inspect "$ENCLAVE_NAME" 2>&1 || echo "")
    echo "$INSPECT_OUTPUT"
    echo "----------------------------------------"
    echo ""
    
    # 检查 enclave 状态
    ENCLAVE_STATUS=""
    if echo "$INSPECT_OUTPUT" | grep -q "Status:"; then
        ENCLAVE_STATUS=$(echo "$INSPECT_OUTPUT" | grep "Status:" | head -1 | sed 's/.*Status:[[:space:]]*//' | tr -d '[:space:]')
        echo "   检测到状态: $ENCLAVE_STATUS"
    fi
    
    # 2. 根据状态决定操作
    echo ""
    echo "3. 处理 enclave..."
    if [ "$ENCLAVE_STATUS" = "EMPTY" ] || [ "$ENCLAVE_STATUS" = "STOPPED" ]; then
        echo "   ℹ Enclave 状态为 $ENCLAVE_STATUS，跳过停止步骤（无法停止非运行状态的 enclave）"
        echo "   直接尝试移除..."
    else
        echo "   尝试停止 enclave..."
        STOP_OUTPUT=$($KURTOSIS_CMD enclave stop "$ENCLAVE_NAME" 2>&1)
        STOP_EXIT_CODE=$?
        
        if [ $STOP_EXIT_CODE -eq 0 ]; then
            echo "   ✓ Enclave 已停止"
        elif echo "$STOP_OUTPUT" | grep -q "EnclaveContainersStatus_EMPTY\|can't create an enclave context from a non-running enclave"; then
            echo "   ℹ Enclave 状态为 EMPTY，无法停止（这是正常的）"
            echo "   直接尝试移除..."
        else
            echo "   ⚠ 停止失败: $STOP_OUTPUT"
            echo "   尝试继续移除..."
        fi
    fi
    echo ""
    
    # 3. 移除 enclave
    echo "4. 移除 enclave..."
    if $KURTOSIS_CMD enclave rm "$ENCLAVE_NAME" 2>/dev/null; then
        echo "   ✓ Enclave 已移除"
    else
        echo "   ⚠ 移除失败，尝试强制移除..."
        # 尝试强制移除
        $KURTOSIS_CMD enclave rm "$ENCLAVE_NAME" --force 2>/dev/null || echo "   ✗ 强制移除也失败"
    fi
    echo ""
    
    # 4. 验证移除结果
    echo "5. 验证移除结果..."
    if $KURTOSIS_CMD enclave ls | grep -q "$ENCLAVE_NAME"; then
        echo "   ⚠ Enclave 仍在列表中，可能需要手动清理 Docker 容器"
        echo ""
        echo "   尝试查找相关的 Docker 容器:"
        $DOCKER_CMD ps -a | grep -i kurtosis | grep -i "$ENCLAVE_NAME" || echo "   未找到相关容器"
        echo ""
        echo "   提示：如果 enclave 仍然存在，可以尝试："
        echo "   1. 重启 kurtosis-manager 容器: docker restart kurtosis-manager"
        echo "   2. 手动清理相关容器（见文档）"
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

