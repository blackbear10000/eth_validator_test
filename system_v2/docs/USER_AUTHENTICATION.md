# 用户认证系统

## 概述

系统实现了完整的用户认证和权限控制系统，支持两种登录方式：
- **普通用户**：使用 MetaMask 钱包登录（Web3 签名验证）
- **管理员**：使用用户名密码登录

## 数据库模型

### User 表

```sql
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    wallet_address VARCHAR(42) UNIQUE,  -- 普通用户钱包地址
    username VARCHAR(50) UNIQUE,        -- 管理员用户名
    password_hash VARCHAR(255),         -- 管理员密码哈希
    role VARCHAR(20) DEFAULT 'user',    -- 'admin' 或 'user'
    created_at TIMESTAMP DEFAULT NOW(),
    last_login TIMESTAMP
);
```

### AuditLog 表

```sql
CREATE TABLE audit_logs (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    action VARCHAR(50),                 -- 'create', 'update', 'delete'
    resource_type VARCHAR(50),          -- 'validator_key', 'deposit', 'client'...
    resource_id VARCHAR(100),
    details JSONB,                      -- 变更详情
    ip_address VARCHAR(45),
    created_at TIMESTAMP DEFAULT NOW()
);
```

### ExitRecord 表

```sql
CREATE TABLE exit_records (
    id SERIAL PRIMARY KEY,
    pubkey VARCHAR(98) REFERENCES validator_keys(pubkey),
    validator_index INTEGER,
    exit_epoch INTEGER NOT NULL,
    withdrawable_epoch INTEGER,
    balance_before_exit_eth NUMERIC(20, 9),
    signature TEXT,
    submitted_at TIMESTAMP DEFAULT NOW(),
    confirmed_at TIMESTAMP,
    status VARCHAR(20) DEFAULT 'submitted'  -- 'submitted', 'confirmed', 'withdrawable', 'completed'
);
```

### DepositTransaction 表更新

新增 `user_id` 字段用于绑定存款与用户：

```sql
ALTER TABLE deposit_transactions ADD COLUMN user_id INTEGER REFERENCES users(id);
```

## API 端点

### 认证相关

#### POST `/api/v1/auth/wallet-login`
钱包登录（普通用户）

**请求体**:
```json
{
  "wallet_address": "0x...",
  "signature": "0x...",
  "message": "请签名以登录..."
}
```

**响应**:
```json
{
  "access_token": "eyJ...",
  "token_type": "bearer",
  "user": {
    "id": 1,
    "wallet_address": "0x...",
    "role": "user"
  }
}
```

#### POST `/api/v1/auth/admin-login`
管理员登录

**请求体**:
```json
{
  "username": "admin",
  "password": "password"
}
```

**响应**:
```json
{
  "access_token": "eyJ...",
  "token_type": "bearer",
  "user": {
    "id": 1,
    "username": "admin",
    "role": "admin"
  }
}
```

#### GET `/api/v1/auth/me`
获取当前用户信息

**Headers**: `Authorization: Bearer <token>`

**响应**:
```json
{
  "id": 1,
  "wallet_address": "0x...",
  "username": null,
  "role": "user"
}
```

#### POST `/api/v1/auth/logout`
登出（客户端删除 token 即可）

### 管理员相关

#### GET `/api/v1/admin/export`
导出数据库数据

**查询参数**:
- `format`: `json` 或 `csv`（默认: `json`）
- `tables`: 要导出的表，逗号分隔（可选，留空导出所有表）

**响应**: 文件下载（JSON 或 ZIP 压缩的 CSV）

#### POST `/api/v1/admin/import`
导入数据库数据

**请求**: `multipart/form-data`，文件字段名 `file`（仅支持 JSON 格式）

**响应**:
```json
{
  "message": "导入完成",
  "imported_tables": ["users", "validator_keys"],
  "errors": []
}
```

#### GET `/api/v1/admin/audit-logs`
获取审计日志

**查询参数**:
- `action`: 操作类型（`create`, `update`, `delete`）
- `resource_type`: 资源类型
- `start_date`: 开始日期（`YYYY-MM-DD`）
- `end_date`: 结束日期（`YYYY-MM-DD`）
- `limit`: 返回数量限制（默认: 100）
- `offset`: 偏移量（默认: 0）

**响应**:
```json
{
  "total": 100,
  "items": [
    {
      "id": 1,
      "user_id": 1,
      "action": "create",
      "resource_type": "validator_key",
      "resource_id": "0x...",
      "details": {...},
      "ip_address": "127.0.0.1",
      "created_at": "2025-12-09T10:00:00Z"
    }
  ]
}
```

## 权限控制

### 用户角色

- **admin**: 管理员，可以访问所有页面和功能
- **user**: 普通用户，只能访问以下页面：
  - Overview（仪表板）
  - 存款管理
  - 退出管理
  - 取款管理

### 前端路由保护

使用 `ProtectedRoute` 组件保护需要认证的路由：

```tsx
<ProtectedRoute requireAdmin={true}>
  <AdminPanel />
</ProtectedRoute>
```

### 后端权限验证

使用依赖注入进行权限验证：

```python
from app.api.v1.auth import get_current_user, get_current_admin_user

@router.get("/admin/export")
async def export_data(
    current_user: dict = Depends(get_current_admin_user)
):
    # 只有管理员可以访问
    ...
```

## 使用说明

### 创建管理员账户

首次部署后，需要通过数据库直接创建管理员账户：

```python
from app.services.auth_service import AuthService
from app.dependencies import SessionLocal

db = SessionLocal()
auth_service = AuthService(db)
admin = auth_service.create_admin_user("admin", "your_password")
db.close()
```

或者使用 SQL：

```sql
INSERT INTO users (username, password_hash, role)
VALUES ('admin', '$2b$12$...', 'admin');
```

密码哈希可以使用 Python 生成：

```python
from app.utils.auth import get_password_hash
print(get_password_hash("your_password"))
```

### 前端使用

1. **钱包登录**：
   - 点击"钱包登录"标签
   - 连接 MetaMask
   - 签名登录消息
   - 系统自动创建用户账户（首次登录）

2. **管理员登录**：
   - 点击"管理员登录"标签
   - 输入用户名和密码
   - 登录成功后可以访问所有功能

3. **登出**：
   - 点击右上角用户菜单
   - 选择"登出"

## 安全注意事项

1. **JWT Secret Key**: 生产环境必须修改 `JWT_SECRET_KEY` 环境变量
2. **密码强度**: 管理员密码应使用强密码
3. **HTTPS**: 生产环境必须使用 HTTPS
4. **Token 过期**: Token 默认 7 天过期，可根据需要调整
5. **审计日志**: 所有写操作都会自动记录到审计日志

## 相关文件

- 后端认证服务: `backend/app/services/auth_service.py`
- 认证工具: `backend/app/utils/auth.py`
- 认证 API: `backend/app/api/v1/auth.py`
- 管理员 API: `backend/app/api/v1/admin.py`
- 前端认证 Store: `frontend/src/stores/authStore.ts`
- 前端登录页面: `frontend/src/components/Auth/LoginPage.tsx`
- 路由保护: `frontend/src/components/Auth/ProtectedRoute.tsx`

