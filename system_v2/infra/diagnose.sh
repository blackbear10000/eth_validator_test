#!/bin/bash
# 诊断脚本：检查容器状态和网络连接

echo "=== 容器状态检查 ==="
docker ps -a | grep -E "(backend|frontend|kurtosis-manager|kurtosis-engine)"

echo ""
echo "=== 后端容器健康检查 ==="
docker inspect backend --format='{{.State.Status}} - Health: {{.State.Health.Status}}' 2>/dev/null || echo "后端容器不存在"

echo ""
echo "=== 后端容器日志（最后20行）==="
docker logs backend --tail=20 2>/dev/null || echo "无法获取后端日志"

echo ""
echo "=== 网络连接测试 ==="
echo "从 frontend 容器测试后端连接："
docker exec frontend curl -s -o /dev/null -w "HTTP Status: %{http_code}\n" http://backend:8000/health 2>/dev/null || echo "无法连接后端"

echo ""
echo "从 backend 容器测试 kurtosis-manager 连接："
docker exec backend curl -s -o /dev/null -w "HTTP Status: %{http_code}\n" http://host.docker.internal:8002/health 2>/dev/null || echo "无法连接 kurtosis-manager"

echo ""
echo "=== Kurtosis Engine 容器状态 ==="
docker ps -a | grep kurtosis-engine || echo "未找到 engine 容器"

echo ""
echo "=== Kurtosis Engine 日志（最后30行）==="
ENGINE_CONTAINER=$(docker ps -a --filter "name=kurtosis-engine" --format "{{.Names}}" | head -1)
if [ -n "$ENGINE_CONTAINER" ]; then
    docker logs "$ENGINE_CONTAINER" --tail=30 2>/dev/null || echo "无法获取 engine 日志"
else
    echo "未找到 engine 容器"
fi

echo ""
echo "=== 网络信息 ==="
docker network inspect validator_network --format='{{range .Containers}}{{.Name}} {{.IPv4Address}}{{"\n"}}{{end}}' 2>/dev/null | grep -E "(backend|frontend)" || echo "无法获取网络信息"

