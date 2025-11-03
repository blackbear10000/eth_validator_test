#!/bin/bash

# Web3Signer Database Initialization Script
# 按顺序执行所有 PostgreSQL 迁移文件

set -e

echo "=========================================="
echo "初始化 Web3Signer 数据库迁移"
echo "=========================================="

# 获取迁移文件目录
MIGRATIONS_DIR="/docker-entrypoint-initdb.d/migrations/postgresql"

if [ ! -d "$MIGRATIONS_DIR" ]; then
    echo "错误: 迁移文件目录不存在: $MIGRATIONS_DIR"
    exit 1
fi

echo "迁移文件目录: $MIGRATIONS_DIR"
echo "迁移文件列表:"
ls -la "$MIGRATIONS_DIR"

# 等待 PostgreSQL 完全启动
echo "等待 PostgreSQL 完全启动..."
sleep 2

# 按顺序执行所有迁移
echo ""
echo "开始执行迁移..."

echo "执行 V00001__initial.sql..."
psql -U postgres -d web3signer -f "$MIGRATIONS_DIR/V00001__initial.sql"

echo "执行 V00002__removeUniqueConstraints.sql..."
psql -U postgres -d web3signer -f "$MIGRATIONS_DIR/V00002__removeUniqueConstraints.sql"

echo "执行 V00003__addLowWatermark.sql..."
psql -U postgres -d web3signer -f "$MIGRATIONS_DIR/V00003__addLowWatermark.sql"

echo "执行 V00004__addGenesisValidatorsRoot.sql..."
psql -U postgres -d web3signer -f "$MIGRATIONS_DIR/V00004__addGenesisValidatorsRoot.sql"

echo "执行 V00005__xnor_source_target_low_watermark.sql..."
psql -U postgres -d web3signer -f "$MIGRATIONS_DIR/V00005__xnor_source_target_low_watermark.sql"

echo "执行 V00006__signed_data_indexes.sql..."
psql -U postgres -d web3signer -f "$MIGRATIONS_DIR/V00006__signed_data_indexes.sql"

echo "执行 V00007__add_db_version.sql..."
psql -U postgres -d web3signer -f "$MIGRATIONS_DIR/V00007__add_db_version.sql"

echo "执行 V00008__signed_data_unique_constraints.sql..."
psql -U postgres -d web3signer -f "$MIGRATIONS_DIR/V00008__signed_data_unique_constraints.sql"

echo "执行 V00009__upsert_validators.sql..."
psql -U postgres -d web3signer -f "$MIGRATIONS_DIR/V00009__upsert_validators.sql"

echo "执行 V00010__validator_enabled_status.sql..."
psql -U postgres -d web3signer -f "$MIGRATIONS_DIR/V00010__validator_enabled_status.sql"

echo "执行 V00011__bigint_indexes.sql..."
psql -U postgres -d web3signer -f "$MIGRATIONS_DIR/V00011__bigint_indexes.sql"

echo "执行 V00012__add_highwatermark_metadata.sql..."
psql -U postgres -d web3signer -f "$MIGRATIONS_DIR/V00012__add_highwatermark_metadata.sql"

echo ""
echo "=========================================="
echo "验证迁移结果"
echo "=========================================="

# 验证数据库版本
echo "检查数据库版本..."
psql -U postgres -d web3signer -c "SELECT * FROM database_version;"

# 验证表是否存在
echo ""
echo "验证关键表是否存在..."
psql -U postgres -d web3signer -c "\dt"

echo ""
echo "=========================================="
echo "Web3Signer 数据库迁移完成!"
echo "=========================================="

# 创建应用数据库 validator_db
echo ""
echo "创建应用数据库 validator_db..."
psql -U postgres <<EOF
SELECT 'CREATE DATABASE validator_db'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'validator_db')\gexec
GRANT ALL PRIVILEGES ON DATABASE validator_db TO postgres;
EOF

echo "应用数据库创建完成"

