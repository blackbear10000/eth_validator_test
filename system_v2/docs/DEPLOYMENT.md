# 部署文档

## 系统要求

- Docker & Docker Compose
- Python 3.11+
- Node.js 18+
- PostgreSQL 12+ (如果单独部署)

## 部署步骤

### 1. 环境准备

```bash
cd system_v2
./scripts/setup.sh
```

### 2. 启动基础设施

```bash
cd infra
docker-compose up -d
```

### 3. 初始化数据库

等待 PostgreSQL 迁移完成后：

```bash
cd ../scripts
python3 migrate_db.py
python3 init_vault.py
```

### 4. 启动服务

**开发模式**:

```bash
# 后端
cd backend
uvicorn app.main:app --reload

# 前端
cd frontend
npm run dev
```

**生产模式** (使用 Docker):

```bash
cd infra
docker-compose up -d
```

## 验证部署

- 后端 API: http://localhost:8000/docs
- 前端界面: http://localhost:3000
- Vault UI: http://localhost:8200
- Consul UI: http://localhost:8500

