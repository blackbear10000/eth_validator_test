# ETH Validator Management System v2

大规模 Ethereum Validator 管理系统 v2.0

## 项目结构

```
system_v2/
├── backend/           # Python 后端服务 (FastAPI)
├── frontend/          # React 前端应用
├── infra/            # 基础设施配置 (Docker Compose)
└── scripts/          # 部署和工具脚本
```

## 快速开始

### 1. 环境准备

```bash
# 运行初始化脚本（可选，用于创建目录和设置权限）
cd scripts
./setup.sh
```

### 2. 启动所有服务

```bash
cd infra
docker-compose up -d
```

这会启动所有服务，包括：
- **基础设施**：Consul、Vault、PostgreSQL、Web3Signer、HAProxy
- **后端服务**：FastAPI 后端（端口 8001）
- **前端服务**：React 前端（端口 3000）
- **Kurtosis 管理服务**：Kurtosis 网络管理（端口 8002）

### 3. 等待服务就绪

```bash
# 查看服务状态
docker-compose ps

# 查看后端日志（确认数据库迁移完成）
docker logs backend -f

# 查看 Vault 初始化状态
docker logs vault-1 -f
```

**重要说明**：
- **数据库迁移**：后端服务启动时会自动执行 Alembic 迁移，无需手动运行 `migrate_db.py`
- **数据库创建**：PostgreSQL healthcheck 会自动创建 `validator_db` 数据库
- **Vault 初始化**：Vault 容器启动时会自动初始化并解锁，KV v2 引擎会在后端首次连接时自动启用

### 4. 验证服务（可选）

```bash
# 检查后端健康状态
curl http://localhost:8001/api/v1/monitoring/health

# 检查前端（浏览器访问）
open http://localhost:3000

# 验证 Vault（可选，主要用于调试）
cd scripts
# 需要先设置 VAULT_TOKEN 环境变量
export VAULT_TOKEN=$(docker exec vault-1 cat /vault/data/root_token.txt 2>/dev/null || echo "dev-root-token")
python3 init_vault.py
```

## 开发模式

如果需要本地开发（不使用 Docker）：

### 启动基础设施（Docker）

```bash
cd infra
docker-compose up -d consul vault-1 postgres web3signer-1 web3signer-2 haproxy
```

### 启动后端（本地）

```bash
cd backend
pip install -r requirements.txt
# 设置环境变量
export DATABASE_URL=postgresql://postgres:password@localhost:5432/validator_db
export VAULT_URL=http://localhost:8200
export VAULT_TOKEN=dev-root-token  # 或从 Consul 读取
uvicorn app.main:app --reload
```

### 启动前端（本地）

```bash
cd frontend
npm install
npm run dev
```

## 访问地址

启动所有服务后：

- **前端界面**: http://localhost:3000
- **后端 API**: http://localhost:8001
- **API 文档**:
  - Swagger UI: http://localhost:8001/docs
  - ReDoc: http://localhost:8001/redoc
- **Vault UI**: http://localhost:8200
- **Consul UI**: http://localhost:8500
- **Kurtosis 管理 API**: http://localhost:8002

## 主要功能

- ✅ 密钥管理：批量生成、状态管理、密钥池
- ✅ 存款管理：Deposit Data 生成、批量提交
- ✅ 客户端管理：Prysm/Lighthouse 配置生成
- ✅ 监控系统：系统健康、验证者性能
- ✅ Web3Signer 集成：零停机密钥更新
- ✅ 状态同步：Beacon Chain API 集成

## 脚本工具说明

`scripts/` 目录下的工具脚本：

### `migrate_db.py` - 数据库迁移脚本（已废弃）

**注意**：这个脚本已经**不再需要**，因为：
1. **数据库创建**：`ensure-db.sh` 在 PostgreSQL healthcheck 中自动创建 `validator_db` 数据库
2. **表结构迁移**：后端服务启动时会自动执行 Alembic 迁移（`app/main.py` 的 `startup_event`）

如果需要在容器外手动运行迁移，可以使用：
```bash
cd backend
alembic upgrade head
```

### `init_vault.py` - Vault 初始化验证（可选）

用于验证 Vault 配置是否正确。**不是必需的**，因为：
- Vault 容器启动时会自动初始化
- KV v2 引擎会在后端首次连接时自动启用（`VaultClient._ensure_kv_engine()`）

主要用于调试和验证。

### `get_vault_token.py` - 获取 Vault Token

从 Consul KV store 读取 Vault root token，用于设置环境变量。

## 详细文档

参见项目根目录下的 `requirements/1_requirement_document.md`

