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
# 运行初始化脚本
cd scripts
./setup.sh
```

### 2. 启动基础设施

```bash
cd ../infra
docker-compose up -d
```

### 3. 初始化数据库

```bash
# 等待 PostgreSQL 和迁移完成
docker logs postgres | grep "迁移完成"

# 运行应用数据库迁移
cd ../scripts
python3 migrate_db.py
```

### 4. 初始化 Vault

```bash
python3 init_vault.py
```

### 5. 启动后端服务

```bash
cd ../backend
pip install -r requirements.txt
uvicorn app.main:app --reload
```

### 6. 启动前端服务

```bash
cd ../frontend
npm install
npm run dev
```

## API 文档

启动后端后，访问：
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## 主要功能

- ✅ 密钥管理：批量生成、状态管理、密钥池
- ✅ 存款管理：Deposit Data 生成、批量提交
- ✅ 客户端管理：Prysm/Lighthouse 配置生成
- ✅ 监控系统：系统健康、验证者性能
- ✅ Web3Signer 集成：零停机密钥更新
- ✅ 状态同步：Beacon Chain API 集成

## 详细文档

参见项目根目录下的 `requirements/1_requirement_document.md`

