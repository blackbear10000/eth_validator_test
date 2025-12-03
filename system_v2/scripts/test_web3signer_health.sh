#!/bin/bash
# Web3Signer 健康检查诊断脚本

set -e

echo "=========================================="
echo "Web3Signer 健康检查诊断"
echo "=========================================="

# 1. 检查 Web3Signer 容器状态
echo "1. 检查 Web3Signer 容器状态..."
docker ps | grep web3signer || echo "   Web3Signer 容器未运行"

# 2. 从后端容器测试 Web3Signer
echo ""
echo "2. 从后端容器测试 Web3Signer..."
echo "   测试 web3signer-1:9000..."
docker exec backend curl -v http://web3signer-1:9000/upcheck 2>&1 | head -20
echo ""
echo "   测试 web3signer-2:9000..."
docker exec backend curl -v http://web3signer-2:9000/upcheck 2>&1 | head -20

# 3. 测试 Python requests 库
echo ""
echo "3. 测试 Python requests 库（模拟后端代码）..."
docker exec backend python3 -c "
import requests
import sys

urls = {
    'primary': 'http://web3signer-1:9000',
    'secondary': 'http://web3signer-2:9000',
    'haproxy': 'http://haproxy:9002'
}

for name, url in urls.items():
    try:
        print(f'测试 {name}: {url}/upcheck')
        response = requests.get(f'{url}/upcheck', timeout=5)
        print(f'  状态码: {response.status_code}')
        print(f'  响应: {response.text[:100]}')
        is_healthy = response.status_code in [200, 403]
        print(f'  健康: {is_healthy}')
        print()
    except Exception as e:
        print(f'  错误: {e}')
        print()
" 2>&1

# 4. 检查后端日志
echo ""
echo "4. 检查后端日志中的 Web3Signer 相关错误..."
docker logs backend --tail 100 2>&1 | grep -i "web3signer\|health" | tail -20 || echo "   没有找到相关日志"

# 5. 检查后端健康检查 API
echo ""
echo "5. 检查后端健康检查 API..."
curl -s http://localhost:8001/api/v1/monitoring/health | python3 -m json.tool || echo "   API 调用失败"

echo ""
echo "=========================================="
echo "诊断完成"

