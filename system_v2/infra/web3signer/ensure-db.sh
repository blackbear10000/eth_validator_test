#!/bin/bash

# 确保数据库存在的脚本
# 这个脚本会在 PostgreSQL 启动后运行，检查并创建必要的数据库
# 可以安全地多次执行（幂等性）
# 注意：此脚本在 healthcheck 中执行，需要快速完成（< 10s timeout）

set -e  # 遇到错误立即退出（但在 healthcheck 中会被捕获）

# 等待 PostgreSQL 完全启动（最多等待 5 秒）
timeout=5
elapsed=0
while ! pg_isready -U postgres >/dev/null 2>&1; do
  if [ $elapsed -ge $timeout ]; then
    echo "PostgreSQL 未在 ${timeout}s 内启动"
    exit 1
  fi
  sleep 0.5
  elapsed=$((elapsed + 1))
done

# 检查 web3signer 数据库是否存在
if ! psql -U postgres -lqt 2>/dev/null | cut -d \| -f 1 | grep -qw web3signer; then
  echo "创建 web3signer 数据库..."
  psql -U postgres -c "CREATE DATABASE web3signer;" 2>/dev/null || true
  psql -U postgres -c "GRANT ALL PRIVILEGES ON DATABASE web3signer TO postgres;" 2>/dev/null || true
  
  # 执行迁移脚本（如果数据库是新创建的）
  # 注意：迁移脚本可能很慢，在 healthcheck 中不执行，由后端启动时执行
  # if [ -f /docker-entrypoint-initdb.d/init-db-migrations.sh ]; then
  #   echo "执行数据库迁移..."
  #   bash /docker-entrypoint-initdb.d/init-db-migrations.sh 2>&1
  # fi
fi

# 检查 validator_db 数据库是否存在（这是关键！）
if ! psql -U postgres -lqt 2>/dev/null | cut -d \| -f 1 | grep -qw validator_db; then
  echo "创建 validator_db 数据库..."
  psql -U postgres -c "CREATE DATABASE validator_db;" 2>/dev/null || true
  psql -U postgres -c "GRANT ALL PRIVILEGES ON DATABASE validator_db TO postgres;" 2>/dev/null || true
fi

# 验证数据库可以访问（快速检查）
psql -U postgres -d web3signer -c "SELECT 1;" >/dev/null 2>&1 || exit 1
psql -U postgres -d validator_db -c "SELECT 1;" >/dev/null 2>&1 || exit 1

exit 0

