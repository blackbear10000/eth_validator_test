# 修复 Alembic 迁移问题

## 问题描述

数据库表已经存在，但 Alembic 版本表未正确记录，导致运行 `alembic upgrade head` 时尝试重新创建已存在的表。

## 解决方案

### 方法 1: 使用 Python 脚本（推荐）

```bash
cd system_v2/backend
python scripts/check_and_fix_migration.py
```

脚本会检查数据库状态并给出修复建议。

### 方法 2: 手动修复（如果脚本无法运行）

#### 步骤 1: 连接到数据库

```bash
psql -U postgres -d validator_db
```

或者使用你的数据库连接信息。

#### 步骤 2: 检查当前状态

```sql
-- 检查 alembic_version 表是否存在
SELECT * FROM alembic_version;

-- 检查 validator_keys 表的列
SELECT column_name, data_type 
FROM information_schema.columns 
WHERE table_name = 'validator_keys' 
ORDER BY ordinal_position;
```

#### 步骤 3: 创建/修复 alembic_version 表

如果 `alembic_version` 表不存在：

```sql
CREATE TABLE alembic_version (
    version_num VARCHAR(32) PRIMARY KEY
);
```

#### 步骤 4: 标记当前版本

根据你的数据库状态，选择以下之一：

**情况 A: 如果 `slashed_at` 和 `status_history` 字段不存在**

标记为 `fix_tx_hash_unique`（添加 slashed_at 之前的版本）：

```sql
-- 如果表为空
INSERT INTO alembic_version (version_num) VALUES ('fix_tx_hash_unique');

-- 如果已有记录，更新它
UPDATE alembic_version SET version_num = 'fix_tx_hash_unique';
```

**情况 B: 如果所有字段都已存在**

标记为最新版本 `113ec78fdd17`：

```sql
INSERT INTO alembic_version (version_num) VALUES ('113ec78fdd17');
-- 或更新
UPDATE alembic_version SET version_num = '113ec78fdd17';
```

#### 步骤 5: 运行迁移

```bash
cd system_v2/backend
python -m alembic upgrade head
```

这只会添加缺失的字段，不会重新创建表。

### 方法 3: 直接添加缺失字段（如果迁移仍然失败）

如果迁移仍然有问题，可以直接在数据库中添加字段：

```sql
-- 添加 slashed_at 字段
ALTER TABLE validator_keys 
ADD COLUMN IF NOT EXISTS slashed_at TIMESTAMP WITHOUT TIME ZONE;

COMMENT ON COLUMN validator_keys.slashed_at IS '被惩罚时间';

-- 添加 status_history 字段
ALTER TABLE validator_keys 
ADD COLUMN IF NOT EXISTS status_history JSONB;

COMMENT ON COLUMN validator_keys.status_history IS '状态变更历史';

-- 然后标记版本
INSERT INTO alembic_version (version_num) VALUES ('113ec78fdd17')
ON CONFLICT (version_num) DO UPDATE SET version_num = '113ec78fdd17';
```

## 验证

运行以下命令验证修复是否成功：

```bash
python -m alembic current
```

应该显示当前版本为 `113ec78fdd17`。

## 迁移链

正确的迁移顺序：
1. `001` - Initial migration
2. `742b2ef76cff` - Add batch_deposit_contracts table
3. `ab34d9f05edb` - Enhance deposit_transaction status
4. `c74d483d28d5` - Add mnemonic fields
5. `fix_tx_hash_unique` - Fix deposit_transaction tx_hash unique constraint
6. `113ec78fdd17` - Add slashed_at and status_history

