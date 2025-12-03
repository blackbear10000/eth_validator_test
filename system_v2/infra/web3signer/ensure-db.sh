#!/bin/bash

# 确保数据库存在的脚本
# 这个脚本会在 PostgreSQL 启动后运行，检查并创建必要的数据库
# 可以安全地多次执行（幂等性）

set +e  # 允许某些命令失败

# 等待 PostgreSQL 完全启动
until pg_isready -U postgres >/dev/null 2>&1; do
  sleep 1
done

# 检查 web3signer 数据库是否存在
if ! psql -U postgres -lqt 2>/dev/null | cut -d \| -f 1 | grep -qw web3signer; then
  echo "创建 web3signer 数据库..."
  psql -U postgres -c "CREATE DATABASE web3signer;" 2>/dev/null
  psql -U postgres -c "GRANT ALL PRIVILEGES ON DATABASE web3signer TO postgres;" 2>/dev/null
  
  # 执行迁移脚本（如果数据库是新创建的）
  if [ -f /docker-entrypoint-initdb.d/init-db-migrations.sh ]; then
    echo "执行数据库迁移..."
    bash /docker-entrypoint-initdb.d/init-db-migrations.sh 2>&1
  fi
fi

# 检查 validator_db 数据库是否存在
if ! psql -U postgres -lqt 2>/dev/null | cut -d \| -f 1 | grep -qw validator_db; then
  echo "创建 validator_db 数据库..."
  psql -U postgres -c "CREATE DATABASE validator_db;" 2>/dev/null
  psql -U postgres -c "GRANT ALL PRIVILEGES ON DATABASE validator_db TO postgres;" 2>/dev/null
fi

# 验证数据库可以访问
psql -U postgres -d web3signer -c "SELECT 1;" >/dev/null 2>&1
exit $?

