# API 文档

## 基础信息

- Base URL: `http://localhost:8001/api/v1`
- 文档: http://localhost:8001/docs
- 认证方式: JWT Token (Bearer Token)

## 认证

所有 API 端点（除登录端点外）都需要在请求头中包含认证令牌：

```
Authorization: Bearer <token>
```

Token 通过登录接口获取，存储在 HTTP-only Cookie 中，前端会自动发送。

### 认证端点

- `POST /auth/wallet-login` - 钱包登录（MetaMask 签名）
- `POST /auth/admin-login` - 管理员登录（用户名密码）
- `GET /auth/me` - 获取当前用户信息
- `POST /auth/logout` - 登出

## 主要端点

### 密钥管理

- `POST /keys/batch-generate` - 批量生成密钥（需要管理员权限）
- `POST /keys/activate` - 激活密钥
- `GET /keys` - 列出密钥
- `GET /keys/{pubkey}` - 获取密钥详情
- `PUT /keys/{pubkey}/status` - 更新密钥状态
- `GET /keys/pool/status` - 获取密钥池状态

### 存款管理

- `POST /deposits/generate` - 生成 Deposit Data
- `POST /deposits/submit` - 提交批量存款
- `GET /deposits` - 列出存款交易（包含 withdrawal_address 和 earnings_eth）
- `POST /deposits/sync` - 手动触发状态同步
- `GET /deposits/batch-contract/{contract_id}/deposits` - 获取合约存款记录

### 客户端管理

- `POST /clients` - 创建客户端实例（需要管理员权限）
- `GET /clients` - 列出客户端
- `GET /clients/{client_id}` - 获取客户端详情
- `PUT /clients/{client_id}` - 更新客户端实例（需要管理员权限）
- `DELETE /clients/{client_id}` - 删除客户端实例（需要管理员权限）
- `PUT /clients/{client_id}/keys` - 分配密钥到客户端（需要管理员权限）
- `GET /clients/{client_id}/keys/available` - 获取可用密钥列表（过滤已被其他客户端使用的密钥）
- `POST /clients/{client_id}/reload-keys` - 重新加载密钥（Web3Signer）（需要管理员权限）
- `POST /clients/{client_id}/sync-keys` - 同步所有 ACTIVE 状态的密钥到 Validator Client（Remote Validator API）（需要管理员权限）

### 退出管理

- `POST /exits/generate` - 生成退出数据
- `POST /exits/submit` - 提交退出请求
- `GET /exits/records` - 获取退出记录列表

### 管理员功能

- `GET /admin/export` - 导出数据库数据（JSON/CSV）（需要管理员权限）
- `POST /admin/import` - 导入数据库数据（JSON）（需要管理员权限）
- `GET /admin/audit-logs` - 获取审计日志（需要管理员权限）

### 监控

- `GET /monitoring/health` - 系统健康检查
- `GET /monitoring/overview` - 系统概览
- `GET /monitoring/validators/{pubkey}` - 验证者性能

详细文档请访问 Swagger UI: http://localhost:8001/docs

## 密钥状态说明

### ValidatorKeyStatus 枚举

- `unused` - 已生成但未激活
- `active` - 已激活，准备用于存款，**可以加载到客户端**
- `deposit_data_generated` - 已生成 Deposit Data，等待提交存款，**可以加载到客户端**
- `pending` - 已提交存款，等待链上确认，**不应加载到客户端**
- `deposited` - 存款已确认，在 deposit queue 中等待处理
- `active_on_chain` - 链上激活，正在验证
- `exited` - 已退出验证
- `slashed` - 被惩罚
- `pending_exit` - 退出中

### 状态转换规则

- `ACTIVE -> DEPOSIT_DATA_GENERATED` - 生成 Deposit Data 时
- `DEPOSIT_DATA_GENERATED -> PENDING` - 提交存款时
- `ACTIVE -> PENDING` - 直接提交存款时（跳过生成 Deposit Data）

