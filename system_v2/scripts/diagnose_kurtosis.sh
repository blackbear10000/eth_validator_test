#!/bin/bash
#
# Kurtosis 诊断脚本
# 用于诊断 Kurtosis enclave 的状态问题
#
# 使用说明：
#   1. 如果 kurtosis-manager 在 Docker 容器中运行，可以通过容器执行：
#      docker exec kurtosis-manager bash /path/to/diagnose_kurtosis.sh eth-devnet
#   2. 或者在主机上直接运行（推荐）：
#      ./diagnose_kurtosis.sh eth-devnet
#

set -e

ENCLAVE_NAME="${1:-eth-devnet}"
USE_DOCKER="${2:-}"

echo "=========================================="
echo "Kurtosis 诊断脚本"
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

# 1. 检查 Kurtosis CLI
echo "1. 检查 Kurtosis CLI..."
VERSION_OUTPUT=$($KURTOSIS_CMD version 2>&1 || echo "")
if [ -n "$VERSION_OUTPUT" ]; then
    echo "   ✓ Kurtosis CLI 可用"
    # 提取 CLI 版本（格式：CLI Version:   1.13.2）
    CLI_VERSION=$(echo "$VERSION_OUTPUT" | grep -i "CLI Version" | sed 's/.*CLI Version:[[:space:]]*//' | head -1)
    if [ -z "$CLI_VERSION" ]; then
        # 如果没有找到，使用第一行
        CLI_VERSION=$(echo "$VERSION_OUTPUT" | head -1)
    fi
    echo "   CLI 版本: $CLI_VERSION"
else
    echo "   ✗ Kurtosis CLI 不可用"
    exit 1
fi
echo ""

# 2. 检查 Kurtosis Engine 和版本匹配
echo "2. 检查 Kurtosis Engine..."
ENGINE_STATUS_OUTPUT=$($KURTOSIS_CMD engine status 2>&1)
if echo "$ENGINE_STATUS_OUTPUT" | grep -q "API version mismatch\|version.*doesn't match"; then
    echo "   ⚠ 版本不匹配错误检测到！"
    echo "   错误信息:"
    echo "$ENGINE_STATUS_OUTPUT" | grep -i "version\|mismatch" | head -3
    echo ""
    echo "   建议解决方案:"
    echo "   1. 重启 Engine: $KURTOSIS_CMD engine restart"
    echo "   2. 或使用 Docker 容器内的 CLI: docker exec kurtosis-manager kurtosis ..."
    echo ""
    echo "   尝试继续执行（可能会失败）..."
elif echo "$ENGINE_STATUS_OUTPUT" | grep -q "running\|started"; then
    echo "   ✓ Kurtosis Engine 正在运行"
    echo "$ENGINE_STATUS_OUTPUT" | head -5
    # 尝试提取 Engine 版本
    ENGINE_VERSION=$(echo "$ENGINE_STATUS_OUTPUT" | grep -i "version\|1\.[0-9]" | head -1)
    if [ -n "$ENGINE_VERSION" ]; then
        echo "   Engine 版本信息: $ENGINE_VERSION"
    fi
else
    echo "   ⚠ Kurtosis Engine 未运行或无法访问"
    echo "   输出: $ENGINE_STATUS_OUTPUT"
fi
echo ""

# 3. 列出所有 enclave
echo "3. 列出所有 enclave:"
echo "----------------------------------------"
$KURTOSIS_CMD enclave ls
echo "----------------------------------------"
echo ""

# 4. 检查目标 enclave
echo "4. 检查目标 enclave '$ENCLAVE_NAME'..."
if $KURTOSIS_CMD enclave ls | grep -q "$ENCLAVE_NAME"; then
    echo "   ✓ Enclave '$ENCLAVE_NAME' 存在于列表中"
    echo ""
    echo "   详细信息:"
    echo "   ----------------------------------------"
    $KURTOSIS_CMD enclave inspect "$ENCLAVE_NAME" || echo "   ⚠ 无法获取详细信息"
    echo "   ----------------------------------------"
    echo ""
    
    # 检查状态字段
    echo "   状态分析:"
    STATUS_OUTPUT=$($KURTOSIS_CMD enclave inspect "$ENCLAVE_NAME" 2>/dev/null || echo "")
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
$DOCKER_CMD ps -a --filter "name=kurtosis" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" | head -20
echo "----------------------------------------"
echo ""

# 6. 提供清理建议
echo "6. 清理建议:"
if $KURTOSIS_CMD enclave ls | grep -q "$ENCLAVE_NAME"; then
    echo "   Enclave 存在，建议执行以下命令清理:"
    echo ""
    if [ -n "$USE_DOCKER" ]; then
        echo "   # 通过容器执行"
        echo "   docker exec $USE_DOCKER kurtosis enclave stop $ENCLAVE_NAME"
        echo "   docker exec $USE_DOCKER kurtosis enclave rm $ENCLAVE_NAME"
    else
        echo "   # 停止 enclave"
        echo "   $KURTOSIS_CMD enclave stop $ENCLAVE_NAME"
        echo ""
        echo "   # 移除 enclave"
        echo "   $KURTOSIS_CMD enclave rm $ENCLAVE_NAME"
    fi
    echo ""
    echo "   或者使用清理脚本:"
    if [ -n "$USE_DOCKER" ]; then
        echo "   docker exec $USE_DOCKER bash /path/to/cleanup_kurtosis_enclave.sh $ENCLAVE_NAME"
    else
        echo "   ./scripts/cleanup_kurtosis_enclave.sh $ENCLAVE_NAME"
    fi
else
    echo "   Enclave 不存在，无需清理"
fi
echo ""

echo "=========================================="
echo "诊断完成"
echo "=========================================="

