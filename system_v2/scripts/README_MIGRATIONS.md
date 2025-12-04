# 数据库迁移问题排查指南

## 问题症状

前端报错：
```
relation "client_instances" does not exist
```

## 原因分析

数据库迁移可能没有正确执行。可能的原因：
1. 后端启动时迁移执行失败但没有阻止服务启动
2. 数据库连接问题
3. 迁移脚本执行顺序问题

## 解决方案

### 方案 1: 手动运行迁移（推荐）

#### 在容器内运行（如果使用 Docker）

```bash
# 进入后端容器
docker exec -it backend bash

# 运行迁移
cd /app
alembic upgrade head
```

#### 在本地运行（如果后端在本地运行）

```bash
cd system_v2/backend

# 确保设置了正确的环境变量
export DATABASE_URL="postgresql://postgres:password@localhost:5432/validator_db"

# 运行迁移
alembic upgrade head
```

#### 使用提供的脚本

```bash
cd system_v2/scripts
./run_migrations.sh
```

### 方案 2: 检查数据库状态

使用诊断脚本检查数据库状态：

```bash
cd system_v2/scripts
python3 check_db_status.py
```

这个脚本会：
- 检查数据库连接
- 列出所有表
- 检查关键表是否存在
- 显示当前迁移版本

### 方案 3: 重新启动后端服务

如果迁移在启动时自动执行，可以尝试重新启动后端：

```bash
# Docker Compose
cd system_v2/infra
docker-compose restart backend

# 或查看日志
docker-compose logs -f backend
```

查看日志中是否有迁移相关的错误信息。

## 验证迁移是否成功

运行以下命令检查迁移状态：

```bash
cd system_v2/backend
alembic current
```

应该看到类似输出：
```
fix_tx_hash_unique (head)
```

检查所有表是否存在：

```bash
# 使用 psql
psql -U postgres -d validator_db -c "\dt"

# 或使用诊断脚本
cd system_v2/scripts
python3 check_db_status.py
```

## 迁移脚本顺序

正确的迁移顺序应该是：
1. `001` - Initial migration（创建所有基础表）
2. `742b2ef76cff` - add_batch_deposit_contracts_table
3. `ab34d9f05edb` - enhance_deposit_transaction_status_fields
4. `c74d483d28d5` - add mnemonic fields to validator_keys
5. `fix_tx_hash_unique` - fix deposit_transaction tx_hash unique constraint

## 常见问题

### Q: 迁移执行失败，提示表已存在

A: 可能是迁移状态不一致。检查 `alembic_version` 表：

```sql
SELECT * FROM alembic_version;
```

如果版本号不正确，可能需要手动修复。

### Q: 迁移执行成功但表仍然不存在

A: 检查是否连接到了正确的数据库：

```bash
# 检查环境变量
echo $DATABASE_URL

# 检查数据库是否存在
psql -U postgres -l | grep validator_db
```

### Q: 迁移执行时出现外键约束错误

A: 确保迁移按正确顺序执行。如果 `client_instances` 表不存在，其他依赖它的表无法创建。

## 预防措施

后端启动时会自动验证所有关键表是否存在。如果缺少表，服务会启动失败并显示错误信息。

## 联系支持

如果以上方法都无法解决问题，请：
1. 收集后端日志：`docker-compose logs backend > backend.log`
2. 运行诊断脚本：`python3 check_db_status.py > db_status.txt`
3. 检查迁移状态：`alembic current > migration_status.txt`

