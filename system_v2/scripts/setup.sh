#!/bin/bash

# 系统初始化脚本

set -e

echo "=========================================="
echo "ETH Validator Management System v2 初始化"
echo "=========================================="

# 检查必要工具
command -v docker >/dev/null 2>&1 || { echo "错误: 需要安装 Docker"; exit 1; }
command -v docker-compose >/dev/null 2>&1 || { echo "错误: 需要安装 Docker Compose"; exit 1; }

# 创建必要目录
echo "创建必要目录..."
mkdir -p ../configs
mkdir -p ../data/logs
mkdir -p infra/web3signer/keys

# 复制迁移文件（如果还没有）
if [ ! -d "infra/web3signer/migrations/postgresql" ]; then
    echo "复制 Web3Signer 数据库迁移文件..."
    mkdir -p infra/web3signer/migrations/postgresql
    # 迁移文件应该已经从现有系统复制
fi

# 设置权限
echo "设置脚本执行权限..."
chmod +x ../backend/scripts/*.sh 2>/dev/null || true
chmod +x infra/web3signer/init-db-migrations.sh

# 初始化环境变量
if [ ! -f "../backend/.env" ]; then
    echo "创建环境变量文件..."
    cat > ../backend/.env << EOF
DATABASE_URL=postgresql://postgres:password@localhost:5432/validator_db
VAULT_URL=http://localhost:8200
VAULT_TOKEN=dev-root-token
WEB3SIGNER_URL_PRIMARY=http://localhost:9000
WEB3SIGNER_URL_SECONDARY=http://localhost:9001
WEB3SIGNER_HAPROXY_URL=http://localhost:9002
BEACON_API_URL=http://localhost:5052
DEBUG=false
EOF
fi

echo ""
echo "=========================================="
echo "初始化完成!"
echo "=========================================="
echo ""
echo "下一步:"
echo "1. cd infra && docker-compose up -d"
echo "2. cd ../scripts && python3 migrate_db.py"
echo "3. 启动后端: cd ../backend && uvicorn app.main:app --reload"
echo "4. 启动前端: cd ../frontend && npm run dev"

