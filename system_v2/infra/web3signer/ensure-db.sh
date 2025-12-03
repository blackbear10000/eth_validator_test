#!/bin/bash

# 确保数据库存在的脚本
# 这个脚本会在 PostgreSQL 启动后运行，检查并创建必要的数据库

set -e

echo "检查数据库是否存在..."

# 等待 PostgreSQL 完全启动
until pg_isready -U postgres >/dev/null 2>&1; do
  echo "等待 PostgreSQL 启动..."
  sleep 1
done

# 检查 web3signer 数据库是否存在
if ! psql -U postgres -lqt | cut -d \| -f 1 | grep -qw web3signer; then
  echo "创建 web3signer 数据库..."
  psql -U postgres <<EOF
CREATE DATABASE web3signer;
GRANT ALL PRIVILEGES ON DATABASE web3signer TO postgres;
EOF
  echo "web3signer 数据库创建完成"
  
  # 执行迁移脚本
  if [ -f /docker-entrypoint-initdb.d/init-db-migrations.sh ]; then
    echo "执行数据库迁移..."
    bash /docker-entrypoint-initdb.d/init-db-migrations.sh
  fi
else
  echo "web3signer 数据库已存在"
fi

# 检查 validator_db 数据库是否存在
if ! psql -U postgres -lqt | cut -d \| -f 1 | grep -qw validator_db; then
  echo "创建 validator_db 数据库..."
  psql -U postgres <<EOF
CREATE DATABASE validator_db;
GRANT ALL PRIVILEGES ON DATABASE validator_db TO postgres;
EOF
  echo "validator_db 数据库创建完成"
else
  echo "validator_db 数据库已存在"
fi

echo "数据库检查完成"

