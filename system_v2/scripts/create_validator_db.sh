#!/bin/bash
# 创建应用数据库（validator_db）
# 这个脚本在 PostgreSQL 容器启动后执行

psql -U postgres <<EOF
-- 创建应用数据库
SELECT 'CREATE DATABASE validator_db'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'validator_db')\gexec

-- 授予权限
GRANT ALL PRIVILEGES ON DATABASE validator_db TO postgres;
EOF

echo "应用数据库 validator_db 创建完成"

