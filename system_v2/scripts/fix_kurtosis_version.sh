#!/bin/bash
#
# Kurtosis 版本修复脚本
# 用于修复 CLI 和 Engine 版本不匹配的问题
#

set -e

echo "=========================================="
echo "Kurtosis 版本修复脚本"
echo "=========================================="
echo ""

# 检查是否在 Docker 环境中
USE_DOCKER=""
if docker ps | grep -q kurtosis-manager; then
    USE_DOCKER="kurtosis-manager"
    echo "检测到 kurtosis-manager 容器，将使用容器内的 CLI"
    KURTOSIS_CMD="docker exec $USE_DOCKER kurtosis"
else
    if ! command -v kurtosis &> /dev/null; then
        echo "❌ Kurtosis CLI 未安装"
        echo "请先安装 Kurtosis CLI 或启动 kurtosis-manager 容器"
        exit 1
    fi
    KURTOSIS_CMD="kurtosis"
fi

echo "使用命令: $KURTOSIS_CMD"
echo ""

# 1. 检查当前版本
echo "1. 检查当前版本..."
VERSION_OUTPUT=$($KURTOSIS_CMD version 2>&1 || echo "")
if [ -n "$VERSION_OUTPUT" ]; then
    # 提取 CLI 版本（格式：CLI Version:   1.13.2）
    CLI_VERSION=$(echo "$VERSION_OUTPUT" | grep -i "CLI Version" | sed 's/.*CLI Version:[[:space:]]*//' | head -1)
    if [ -z "$CLI_VERSION" ]; then
        CLI_VERSION=$(echo "$VERSION_OUTPUT" | head -1)
    fi
    echo "   CLI 版本: $CLI_VERSION"
else
    echo "   CLI 版本: 未知（无法获取）"
    CLI_VERSION="未知"
fi

ENGINE_STATUS=$($KURTOSIS_CMD engine status 2>&1 || echo "")
if echo "$ENGINE_STATUS" | grep -q "API version mismatch\|version.*doesn't match"; then
    echo "   ⚠ 检测到版本不匹配错误"
    echo ""
    echo "   错误详情:"
    echo "$ENGINE_STATUS" | grep -i "version\|mismatch" | head -3
    echo ""
    
    # 提取版本信息
    EXPECTED_VERSION=$(echo "$ENGINE_STATUS" | grep -oP "expects, '[^']+'" | grep -oP "'[^']+'" | tr -d "'" || echo "")
    ACTUAL_VERSION=$(echo "$ENGINE_STATUS" | grep -oP "version '[^']+'" | grep -oP "'[^']+'" | tr -d "'" | head -1 || echo "")
    
    if [ -n "$EXPECTED_VERSION" ] && [ -n "$ACTUAL_VERSION" ]; then
        echo "   CLI 期望版本: $EXPECTED_VERSION"
        echo "   Engine 实际版本: $ACTUAL_VERSION"
    fi
    echo ""
    
    # 2. 提供解决方案
    echo "2. 解决方案选择:"
    echo ""
    echo "   方案 A: 重启 Engine（推荐，如果 CLI 版本较新）"
    echo "   方案 B: 使用 Docker 容器内的 CLI（如果宿主机版本不匹配）"
    echo ""
    
    read -p "   选择方案 (A/B，默认 A): " choice
    choice=${choice:-A}
    
    case "$choice" in
        A|a)
            echo ""
            echo "3. 执行方案 A: 重启 Engine..."
            if [ -n "$USE_DOCKER" ]; then
                echo "   通过容器重启 Engine..."
                docker exec $USE_DOCKER kurtosis engine restart
            else
                echo "   在主机上重启 Engine..."
                kurtosis engine restart
            fi
            
            echo ""
            echo "   等待 Engine 启动..."
            sleep 5
            
            # 验证
            echo ""
            echo "4. 验证修复结果..."
            if $KURTOSIS_CMD engine status &>/dev/null; then
                echo "   ✓ Engine 已重启"
                NEW_STATUS=$($KURTOSIS_CMD engine status 2>&1)
                if echo "$NEW_STATUS" | grep -q "API version mismatch"; then
                    echo "   ⚠ 版本仍然不匹配，可能需要更新 CLI"
                    echo "   建议使用方案 B（通过容器执行）"
                else
                    echo "   ✓ 版本匹配成功！"
                    $KURTOSIS_CMD engine status | head -5
                fi
            else
                echo "   ⚠ Engine 重启后无法访问，请检查日志"
            fi
            ;;
        B|b)
            echo ""
            echo "3. 执行方案 B: 使用 Docker 容器内的 CLI"
            echo ""
            echo "   推荐使用以下命令通过容器执行:"
            echo ""
            echo "   # 诊断"
            echo "   docker exec kurtosis-manager kurtosis enclave ls"
            echo ""
            echo "   # 清理"
            echo "   docker exec kurtosis-manager kurtosis enclave stop eth-devnet"
            echo "   docker exec kurtosis-manager kurtosis enclave rm eth-devnet"
            echo ""
            echo "   或者使用脚本:"
            echo "   docker exec kurtosis-manager bash /path/to/cleanup_kurtosis_enclave.sh eth-devnet"
            ;;
        *)
            echo "   无效选择，退出"
            exit 1
            ;;
    esac
else
    echo "   ✓ 未检测到版本不匹配问题"
    echo ""
    echo "   Engine 状态:"
    echo "$ENGINE_STATUS" | head -5
fi

echo ""
echo "=========================================="
echo "完成"
echo "=========================================="

