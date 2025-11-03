# API 文档

## 基础信息

- Base URL: `http://localhost:8000/api/v1`
- 文档: http://localhost:8000/docs

## 主要端点

### 密钥管理

- `POST /keys/batch-generate` - 批量生成密钥
- `POST /keys/activate` - 激活密钥
- `GET /keys` - 列出密钥
- `GET /keys/{pubkey}` - 获取密钥详情
- `PUT /keys/{pubkey}/status` - 更新密钥状态
- `GET /keys/pool/status` - 获取密钥池状态

### 存款管理

- `POST /deposits/generate` - 生成 Deposit Data
- `POST /deposits/submit` - 提交批量存款
- `GET /deposits` - 列出存款交易
- `POST /deposits/sync` - 手动触发状态同步

### 客户端管理

- `POST /clients` - 创建客户端实例
- `GET /clients` - 列出客户端
- `PUT /clients/{client_id}/keys` - 分配密钥
- `POST /clients/{client_id}/reload-keys` - 重新加载密钥

### 监控

- `GET /monitoring/health` - 系统健康检查
- `GET /monitoring/overview` - 系统概览
- `GET /monitoring/validators/{pubkey}` - 验证者性能

详细文档请访问 Swagger UI: http://localhost:8000/docs

