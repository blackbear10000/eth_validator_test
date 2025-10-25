#!/bin/bash

# Web3Signer 测试运行脚本
# 用于快速诊断和测试 Web3Signer 相关问题

echo "🔍 Web3Signer 测试套件"
echo "========================"

# 检查 Python 环境
if ! command -v python3 &> /dev/null; then
    echo "❌ Python3 未安装"
    exit 1
fi

# 检查必要的 Python 包
echo "📦 检查 Python 依赖..."
python3 -c "import requests, psycopg2" 2>/dev/null || {
    echo "❌ 缺少必要的 Python 包，请安装："
    echo "   pip install requests psycopg2-binary"
    exit 1
}

echo "✅ Python 环境检查通过"

# 检查 Docker 服务状态
echo ""
echo "🐳 检查 Docker 服务状态..."
if ! docker ps &> /dev/null; then
    echo "❌ Docker 未运行或无法访问"
    exit 1
fi

# 检查 Web3Signer 容器状态
echo "检查 Web3Signer 容器..."
WEB3SIGNER_CONTAINERS=$(docker ps --filter "name=web3signer" --format "table {{.Names}}\t{{.Status}}")
if [ -z "$WEB3SIGNER_CONTAINERS" ]; then
    echo "❌ 未找到 Web3Signer 容器，请先启动服务："
    echo "   docker-compose up -d"
    exit 1
else
    echo "✅ Web3Signer 容器状态："
    echo "$WEB3SIGNER_CONTAINERS"
fi

# 检查 PostgreSQL 容器状态
echo ""
echo "🐘 检查 PostgreSQL 容器状态..."
POSTGRES_STATUS=$(docker ps --filter "name=postgres" --format "{{.Status}}")
if [ -z "$POSTGRES_STATUS" ]; then
    echo "❌ PostgreSQL 容器未运行"
    exit 1
else
    echo "✅ PostgreSQL 容器状态: $POSTGRES_STATUS"
fi

echo ""
echo "🧪 开始运行测试..."
echo "========================"

# 运行数据库架构测试
echo ""
echo "1️⃣ 测试数据库架构..."
python3 scripts/test_database_schema.py
DB_TEST_RESULT=$?

# 运行 Web3Signer API 测试
echo ""
echo "2️⃣ 测试 Web3Signer API..."
python3 scripts/test_web3signer_api.py --url http://localhost:9000
API_TEST_RESULT=$?

# 运行问题诊断
echo ""
echo "3️⃣ 运行问题诊断..."
python3 scripts/diagnose_validator_issues.py
DIAGNOSTIC_RESULT=$?

# 总结结果
echo ""
echo "========================"
echo "📊 测试结果总结:"
echo "========================"

if [ $DB_TEST_RESULT -eq 0 ]; then
    echo "✅ 数据库架构测试: 通过"
else
    echo "❌ 数据库架构测试: 失败"
fi

if [ $API_TEST_RESULT -eq 0 ]; then
    echo "✅ Web3Signer API 测试: 通过"
else
    echo "❌ Web3Signer API 测试: 失败"
fi

if [ $DIAGNOSTIC_RESULT -eq 0 ]; then
    echo "✅ 问题诊断: 通过"
else
    echo "❌ 问题诊断: 发现问题"
fi

# 提供下一步建议
echo ""
echo "🛠️  下一步建议:"
echo "========================"

if [ $DB_TEST_RESULT -ne 0 ]; then
    echo "1. 数据库问题 - 建议重新初始化数据库："
    echo "   docker-compose down"
    echo "   docker volume rm eth_validator_test_postgres_data"
    echo "   docker-compose up -d"
fi

if [ $API_TEST_RESULT -ne 0 ]; then
    echo "2. Web3Signer API 问题 - 检查服务状态："
    echo "   docker logs web3signer-1"
    echo "   docker logs web3signer-2"
fi

if [ $DIAGNOSTIC_RESULT -ne 0 ]; then
    echo "3. 发现问题 - 请查看上述诊断结果和解决方案"
fi

if [ $DB_TEST_RESULT -eq 0 ] && [ $API_TEST_RESULT -eq 0 ] && [ $DIAGNOSTIC_RESULT -eq 0 ]; then
    echo "🎉 所有测试都通过了！系统运行正常。"
    exit 0
else
    echo "⚠️  部分测试失败，请根据上述建议进行修复。"
    exit 1
fi
