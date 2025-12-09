# 功能更新文档

本文档记录了系统 v2 的最新功能更新和优化。

## 更新日期

2025-12-09

## 主要更新内容

### 1. 用户认证与权限系统

#### 1.1 用户认证
- ✅ 支持 MetaMask 钱包登录（普通用户）
- ✅ 支持用户名密码登录（管理员）
- ✅ JWT Token 认证
- ✅ 自动创建用户账户（首次钱包登录）

#### 1.2 权限控制
- ✅ 基于角色的访问控制（RBAC）
- ✅ 前端路由保护
- ✅ 后端 API 权限验证
- ✅ 菜单权限动态显示

**普通用户可访问页面**:
- Overview（仪表板）
- 存款管理
- 退出管理
- 取款管理

**管理员可访问页面**:
- 所有普通用户页面
- 密钥管理
- 合约管理
- 客户端管理
- 网络管理
- Web3Signer 监控
- 管理员面板

### 2. 管理员功能

#### 2.1 数据导出/导入
- ✅ 支持 JSON 格式导出
- ✅ 支持 CSV 格式导出（ZIP 压缩）
- ✅ 选择性导出表
- ✅ JSON 格式导入

**使用方式**:
1. 访问"管理员面板" → "数据导出"
2. 选择导出格式（JSON/CSV）
3. 选择要导出的表（可选，留空导出所有表）
4. 点击"导出数据"下载文件

#### 2.2 审计日志
- ✅ 自动记录所有写操作（POST/PUT/DELETE）
- ✅ 记录用户 ID、操作类型、资源类型、IP 地址
- ✅ 支持按操作类型、资源类型、时间范围筛选
- ✅ 分页显示

**审计日志记录的操作**:
- 创建资源（create）
- 更新资源（update）
- 删除资源（delete）

**记录的资源类型**:
- `validator_key`: 验证者密钥
- `deposit`: 存款交易
- `client`: 客户端实例
- `exit`: 退出操作
- 等等...

### 3. 合约管理页面优化

#### 3.1 统计数据修复
- ✅ 合约余额：从链上读取 Batch 合约 ETH 余额
- ✅ 总存款金额：统计通过该合约的存款总额
- ✅ 合约费用：从链上读取合约 fee 设置
- ✅ 合约状态：从链上读取 paused 状态

#### 3.2 存款记录列表
- ✅ 新增"存款记录"Tab
- ✅ 显示通过该合约的所有存款交易
- ✅ 显示字段：交易哈希、批次ID、验证者数量、总金额、状态、提交时间、确认时间、区块号

**API 端点**: `GET /api/v1/deposits/batch-contract/{contract_id}/deposits`

### 4. 存款管理页面优化

#### 4.1 字段修复和优化
- ✅ 修复"金额(ETH)"字段显示（显示存款金额，通常是 32 ETH）
- ✅ 增加"提款地址"列（withdrawal_address，截断显示）
- ✅ 优化"收益(ETH)"计算：`当前余额 - 32 ETH + 已取款金额累计`
- ✅ 收益字段添加 Tooltip 显示计算明细

#### 4.2 按钮优化
- ✅ "同步状态" → "同步链上数据"（更明确的命名）
- ✅ "刷新" → "刷新列表"（更明确的命名）
- ✅ 两个按钮功能明确区分：
  - **同步链上数据**：从 Beacon Chain 同步最新状态到数据库
  - **刷新列表**：仅刷新页面数据（从数据库读取）

#### 4.3 批量选择功能
- ✅ 输入数量自动选择激活状态的验证者
- ✅ 支持表格行选择
- ✅ 显示已选择数量

**使用方式**:
1. 在表格下方输入数量
2. 点击"批量选择激活验证者"
3. 系统自动选择指定数量的 `activated` 或 `active_on_chain` 状态的验证者

### 5. 客户端管理页面优化

#### 5.1 批量导入密钥
- ✅ 输入数量自动选择已提交存款的密钥
- ✅ 自动过滤已被其他运行中客户端使用的密钥
- ✅ 显示可用密钥数量

**使用方式**:
1. 打开客户端密钥管理模态框
2. 在"批量导入"区域输入数量
3. 点击"批量导入已提交存款的密钥"
4. 系统自动选择指定数量的 `deposited` 或 `pending` 状态的密钥

#### 5.2 密钥过滤优化
- ✅ 新增 API: `GET /api/v1/clients/{client_id}/keys/available`
- ✅ 自动排除已被其他运行中客户端使用的密钥
- ✅ 显示可用密钥数量提示

#### 5.3 日志显示优化
- ✅ 增加日志行数（从 100 行增加到 500 行）
- ✅ 自动刷新（每 5 秒）
- ✅ 自动滚动到底部
- ✅ 改进样式（word-break、更好的换行）
- ✅ 过滤空行

**使用方式**:
1. 点击客户端列表中的"查看日志"按钮
2. 日志自动刷新并滚动到底部
3. 可以手动点击"刷新"按钮

### 6. 退出管理页面优化

#### 6.1 退出记录列表
- ✅ 新增"退出记录"Tab
- ✅ 显示所有退出操作的详细历史
- ✅ 显示字段：
  - ID
  - 公钥
  - 验证者索引
  - 退出 Epoch
  - 预计可取款 Epoch
  - 退出前余额（ETH）
  - 状态（submitted/confirmed/withdrawable/completed）
  - 提交时间
  - 确认时间

**API 端点**: `GET /api/v1/exits/records`

**查询参数**:
- `pubkey`: 验证者公钥（可选）
- `status`: 状态筛选（可选）
- `limit`: 返回数量限制（默认: 100）
- `offset`: 偏移量（默认: 0）

## API 变更

### 新增端点

1. **认证相关**:
   - `POST /api/v1/auth/wallet-login`
   - `POST /api/v1/auth/admin-login`
   - `GET /api/v1/auth/me`
   - `POST /api/v1/auth/logout`

2. **管理员相关**:
   - `GET /api/v1/admin/export`
   - `POST /api/v1/admin/import`
   - `GET /api/v1/admin/audit-logs`

3. **合约相关**:
   - `GET /api/v1/deposits/batch-contract/{contract_id}/deposits`

4. **退出相关**:
   - `GET /api/v1/exits/records`

5. **客户端相关**:
   - `GET /api/v1/clients/{client_id}/keys/available`

### 修改的端点

1. **存款列表** (`GET /api/v1/deposits`):
   - 新增 `withdrawal_address` 字段（从 ValidatorKey 关联获取）
   - 收益计算优化：`earnings_eth = balance_eth - 32 + total_withdrawn_eth`
   - 新增 `total_withdrawn_eth` 字段

2. **退出提交** (`POST /api/v1/exits/submit`):
   - 自动创建 `ExitRecord` 记录
   - 返回 `exit_record_id`

## 数据库变更

### 新增表

1. **users**: 用户表
2. **audit_logs**: 审计日志表
3. **exit_records**: 退出记录表

### 修改的表

1. **deposit_transactions**: 新增 `user_id` 字段

### 迁移说明

系统启动时会自动执行数据库迁移，创建新表和字段。无需手动操作。

## 前端变更

### 新增组件

1. **Auth/LoginPage.tsx**: 登录页面
2. **Auth/ProtectedRoute.tsx**: 路由保护组件
3. **Admin/AdminPanel.tsx**: 管理员面板

### 修改的组件

1. **App.tsx**: 添加认证路由和权限控制
2. **Layout/MainLayout.tsx**: 根据用户角色显示菜单，添加登出功能
3. **Contracts/BatchContractManager.tsx**: 添加存款记录 Tab
4. **Deposits/DepositList.tsx**: 优化字段显示、添加批量选择
5. **Clients/ClientKeyManagementModal.tsx**: 添加批量导入功能
6. **Clients/ClientList.tsx**: 优化日志显示
7. **Exits/ExitList.tsx**: 添加退出记录 Tab

### 新增 Store

1. **stores/authStore.ts**: 认证状态管理

## 依赖更新

### 后端依赖

新增：
- `passlib[bcrypt]>=1.7.4`: 密码哈希
- `python-jose[cryptography]>=3.3.0`: JWT token
- `python-multipart>=0.0.6`: 文件上传支持

### 前端依赖

无需新增依赖（使用现有的 Ant Design 和 React Router）

## 配置说明

### 环境变量

新增后端环境变量（可选）:
```bash
JWT_SECRET_KEY=your-secret-key-change-in-production  # JWT 密钥（生产环境必须修改）
```

### 默认配置

- Token 过期时间: 7 天
- 审计日志: 自动记录所有写操作
- 日志自动刷新间隔: 5 秒

## 使用示例

### 创建管理员账户

```python
from app.services.auth_service import AuthService
from app.dependencies import SessionLocal

db = SessionLocal()
auth_service = AuthService(db)
admin = auth_service.create_admin_user("admin", "secure_password")
print(f"管理员账户创建成功: {admin.username}")
db.close()
```

### 前端认证流程

```typescript
// 钱包登录
const { loginWithWallet } = useAuthStore()
await loginWithWallet()

// 管理员登录
const { loginWithPassword } = useAuthStore()
await loginWithPassword("admin", "password")

// 检查认证状态
const { checkAuth } = useAuthStore()
await checkAuth()

// 登出
const { logout } = useAuthStore()
logout()
```

## 注意事项

1. **首次部署**: 需要手动创建管理员账户（见使用示例）
2. **JWT Secret**: 生产环境必须修改 `JWT_SECRET_KEY`
3. **HTTPS**: 生产环境必须使用 HTTPS
4. **数据库迁移**: 系统启动时自动执行，无需手动操作
5. **审计日志**: 会自动记录所有写操作，注意数据库空间

## 相关文档

- [用户认证系统](./USER_AUTHENTICATION.md)
- [API 文档](./API.md)
- [架构文档](./ARCHITECTURE.md)

