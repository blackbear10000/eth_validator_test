# 修复迁移问题指南

## 问题症状

前端报错：`relation "client_instances" does not exist`

迁移日志显示执行成功，但表不存在。

## 快速修复

### 方法 1: 在容器内手动运行迁移（最简单）

```bash
# 进入后端容器
docker exec -it backend bash

# 运行迁移
cd /app
alembic upgrade head

# 验证表是否存在
python3 << 'EOF'
from sqlalchemy import create_engine, text
from app.config import settings
engine = create_engine(settings.database_url)
with engine.connect() as conn:
    result = conn.execute(text("SELECT tablename FROM pg_tables WHERE schemaname = 'public'"))
    tables = [r[0] for r in result]
    print("Tables:", tables)
    print("client_instances exists:", "client_instances" in tables)
EOF
```

### 方法 2: 使用修复脚本

```bash
# 将脚本复制到容器内
docker cp system_v2/scripts/fix_migration.sh backend:/tmp/

# 在容器内运行
docker exec -it backend bash /tmp/fix_migration.sh
```

### 方法 3: 检查后端日志

```bash
# 查看后端启动日志
docker-compose logs backend | grep -E "迁移|migration|database|表|table|client_instances|validator_db" -i

# 查看完整日志
docker-compose logs backend | tail -100
```

## 诊断步骤

### 1. 检查数据库是否存在

```bash
docker exec postgres psql -U postgres -c "\l" | grep validator_db
```

### 2. 检查表是否在正确的数据库中

```bash
# 检查 validator_db
docker exec postgres psql -U postgres -d validator_db -c "\dt"

# 检查 web3signer（可能迁移执行在了这里）
docker exec postgres psql -U postgres -d web3signer -c "\dt" | grep client_instances
```

### 3. 检查迁移版本

```bash
# validator_db
docker exec postgres psql -U postgres -d validator_db -c "SELECT * FROM alembic_version;"

# web3signer
docker exec postgres psql -U postgres -d web3signer -c "SELECT * FROM alembic_version;" 2>/dev/null || echo "No alembic_version in web3signer"
```

### 4. 检查后端环境变量

```bash
docker exec backend env | grep DATABASE_URL
```

应该显示：`DATABASE_URL=postgresql://postgres:password@postgres:5432/validator_db`

## 常见问题

### Q: 迁移执行成功但表不存在

**可能原因：**
1. 迁移执行在了错误的数据库（web3signer 而不是 validator_db）
2. 迁移执行时数据库还没有创建
3. 迁移后数据库被重置

**解决方案：**
1. 确认 `DATABASE_URL` 环境变量正确
2. 手动运行迁移：`docker exec backend alembic upgrade head`
3. 检查迁移日志，确认执行在正确的数据库

### Q: 迁移执行失败

**检查日志：**
```bash
docker-compose logs backend | grep -A 20 "迁移执行过程中出错"
```

**常见错误：**
- 数据库连接失败 → 检查 PostgreSQL 是否运行
- 表已存在 → 检查迁移版本，可能需要降级后重新升级
- 权限问题 → 检查数据库用户权限

### Q: 迁移执行在错误的数据库

**症状：** 迁移日志显示成功，但表在 web3signer 数据库中

**解决方案：**
1. 确认 `DATABASE_URL` 环境变量
2. 删除错误的迁移记录：
   ```sql
   -- 在 web3signer 数据库中
   DROP TABLE IF EXISTS alembic_version CASCADE;
   ```
3. 在正确的数据库中运行迁移

## 预防措施

后端启动时会：
1. 等待数据库准备就绪（最多 30 次重试）
2. 确保数据库存在（不存在则创建）
3. 确认迁移执行在正确的数据库
4. 验证所有关键表是否存在

如果验证失败，后端会启动失败并显示错误信息。

## 完全重置（如果其他方法都失败）

```bash
# 停止所有容器
docker-compose down -v

# 删除所有卷
docker volume rm system_v2_infra_postgres_data system_v2_infra_vault_data_1 system_v2_infra_consul_data

# 重新启动
docker-compose up -d

# 等待后端启动完成
docker-compose logs -f backend
```

## 联系支持

如果以上方法都无法解决问题，请提供：
1. 后端完整日志：`docker-compose logs backend > backend.log`
2. 数据库状态：`docker exec postgres psql -U postgres -c "\l" > databases.txt`
3. 迁移版本：`docker exec backend alembic current > migration_version.txt`

