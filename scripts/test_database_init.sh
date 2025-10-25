#!/bin/bash

# 测试数据库初始化脚本
echo "🔍 测试数据库初始化脚本..."

# 检查脚本权限
echo "1. 检查脚本权限..."
if [ -x "/Users/yuanshuai/Documents/Github/eth_validator_test/infra/web3signer/init-db-migrations.sh" ]; then
    echo "✅ 脚本有执行权限"
else
    echo "❌ 脚本没有执行权限"
    chmod +x /Users/yuanshuai/Documents/Github/eth_validator_test/infra/web3signer/init-db-migrations.sh
    echo "✅ 已添加执行权限"
fi

# 检查迁移文件
echo ""
echo "2. 检查迁移文件..."
MIGRATIONS_DIR="/Users/yuanshuai/Documents/Github/eth_validator_test/infra/web3signer/migrations/postgresql"
if [ -d "$MIGRATIONS_DIR" ]; then
    echo "✅ 迁移目录存在: $MIGRATIONS_DIR"
    echo "📋 迁移文件列表:"
    ls -la "$MIGRATIONS_DIR"
else
    echo "❌ 迁移目录不存在: $MIGRATIONS_DIR"
    exit 1
fi

# 检查 docker-compose.yml 配置
echo ""
echo "3. 检查 docker-compose.yml 配置..."
if grep -q "init-db-migrations.sh" /Users/yuanshuai/Documents/Github/eth_validator_test/infra/docker-compose.yml; then
    echo "✅ docker-compose.yml 包含初始化脚本"
else
    echo "❌ docker-compose.yml 缺少初始化脚本配置"
fi

if grep -q "migrations" /Users/yuanshuai/Documents/Github/eth_validator_test/infra/docker-compose.yml; then
    echo "✅ docker-compose.yml 包含迁移文件映射"
else
    echo "❌ docker-compose.yml 缺少迁移文件映射"
fi

echo ""
echo "4. 建议的修复步骤:"
echo "========================"
echo "1. 停止所有服务:"
echo "   docker-compose down"
echo ""
echo "2. 删除 postgres volume:"
echo "   docker volume rm eth_validator_test_postgres_data"
echo ""
echo "3. 重新启动服务:"
echo "   docker-compose up -d"
echo ""
echo "4. 检查 postgres 日志:"
echo "   docker logs postgres"
echo ""
echo "5. 检查 web3signer 日志:"
echo "   docker logs web3signer-1"
echo "   docker logs web3signer-2"

echo ""
echo "✅ 检查完成！"
