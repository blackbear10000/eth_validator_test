#!/bin/bash
# HAProxy 健康检查诊断脚本

set -e

echo "=========================================="
echo "HAProxy 健康检查诊断"
echo "=========================================="

# 1. 检查 HAProxy 容器状态
echo ""
echo "1. 检查 HAProxy 容器状态..."
if docker ps | grep -q haproxy; then
    docker ps | grep haproxy
    echo ""
    echo "   健康状态检查："
    docker inspect haproxy --format='{{.State.Health.Status}}' 2>/dev/null || echo "   无法获取健康状态"
else
    echo "   ❌ HAProxy 容器未运行"
    exit 1
fi

# 2. 检查 HAProxy 容器内是否有 curl
echo ""
echo "2. 检查 HAProxy 容器内是否有 curl..."
if docker exec haproxy which curl >/dev/null 2>&1; then
    echo "   ✅ curl 已安装"
    CURL_VERSION=$(docker exec haproxy curl --version 2>/dev/null | head -1)
    echo "   版本: $CURL_VERSION"
else
    echo "   ❌ curl 未安装"
    echo "   解决方案：使用自定义 Dockerfile 构建 HAProxy 镜像"
    echo "   运行: cd infra && docker-compose build haproxy"
fi

# 3. 手动测试健康检查端点（从容器内）
echo ""
echo "3. 从容器内测试健康检查端点..."
echo "   测试 http://localhost:9002/upcheck..."
if docker exec haproxy curl -f http://localhost:9002/upcheck >/dev/null 2>&1; then
    echo "   ✅ 健康检查端点响应正常"
    docker exec haproxy curl -s http://localhost:9002/upcheck
else
    echo "   ❌ 健康检查端点无响应或返回错误"
    docker exec haproxy curl -v http://localhost:9002/upcheck 2>&1 | head -10 || echo "   curl 命令执行失败"
fi

# 4. 从外部测试 HAProxy
echo ""
echo "4. 从外部测试 HAProxy..."
echo "   测试 http://localhost:9002/upcheck..."
if curl -f http://localhost:9002/upcheck >/dev/null 2>&1; then
    echo "   ✅ 外部访问正常"
    curl -s http://localhost:9002/upcheck
else
    echo "   ⚠️  外部访问失败（可能是网络配置问题）"
    curl -v http://localhost:9002/upcheck 2>&1 | head -10 || echo "   curl 命令执行失败"
fi

# 5. 检查 HAProxy 日志
echo ""
echo "5. 检查 HAProxy 最近日志..."
docker logs haproxy --tail 30 2>&1 | tail -20

# 6. 检查 HAProxy 配置
echo ""
echo "6. 检查 HAProxy 配置..."
if docker exec haproxy cat /usr/local/etc/haproxy/haproxy.cfg >/dev/null 2>&1; then
    echo "   ✅ 配置文件存在"
    echo "   检查 upcheck 端点配置..."
    docker exec haproxy grep -A 2 "upcheck" /usr/local/etc/haproxy/haproxy.cfg || echo "   未找到 upcheck 配置"
else
    echo "   ❌ 配置文件不存在或无法读取"
fi

# 7. 检查后端服务状态
echo ""
echo "7. 检查后端 Web3Signer 服务状态..."
WEB3SIGNER_COUNT=$(docker ps | grep -c web3signer || echo "0")
if [ "$WEB3SIGNER_COUNT" -gt 0 ]; then
    echo "   ✅ 发现 $WEB3SIGNER_COUNT 个 Web3Signer 容器"
    docker ps | grep web3signer
else
    echo "   ❌ Web3Signer 容器未运行"
fi

# 8. 检查健康检查历史
echo ""
echo "8. 检查健康检查历史..."
docker inspect haproxy --format='{{range .State.Health.Log}}{{.Output}}{{end}}' 2>/dev/null | tail -5 || echo "   无法获取健康检查历史"

echo ""
echo "=========================================="
echo "诊断完成"
echo ""
echo "如果健康检查仍然失败，请："
echo "1. 重新构建 HAProxy 镜像: cd infra && docker-compose build haproxy"
echo "2. 重启 HAProxy: docker-compose restart haproxy"
echo "3. 查看详细日志: docker logs haproxy -f"

