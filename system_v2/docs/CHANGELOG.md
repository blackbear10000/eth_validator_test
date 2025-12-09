# 更新日志

## [2.1.0] - 2025-12-09

### 新增功能

#### 用户认证系统
- ✅ 支持 MetaMask 钱包登录（普通用户）
- ✅ 支持用户名密码登录（管理员）
- ✅ JWT Token 认证
- ✅ 自动创建用户账户（首次钱包登录）
- ✅ 用户角色管理（admin/user）

#### 权限控制系统
- ✅ 基于角色的访问控制（RBAC）
- ✅ 前端路由保护
- ✅ 后端 API 权限验证
- ✅ 菜单权限动态显示

#### 管理员功能
- ✅ 数据导出（JSON/CSV 格式）
- ✅ 数据导入（JSON 格式）
- ✅ 审计日志系统（自动记录所有写操作）
- ✅ 审计日志查询和筛选

#### 合约管理页面
- ✅ 修复统计数据（合约余额、总存款金额、合约费用、合约状态）
- ✅ 新增存款记录列表（显示通过该合约的所有存款交易）

#### 存款管理页面
- ✅ 修复"金额(ETH)"字段显示
- ✅ 新增"提款地址"列
- ✅ 优化收益计算（综合计算：当前余额 - 32 + 已取款金额）
- ✅ 按钮重命名（"同步链上数据"、"刷新列表"）
- ✅ 批量选择功能（输入数量自动选择激活验证者）

#### 客户端管理页面
- ✅ 批量导入密钥功能（输入数量自动选择已提交存款的密钥）
- ✅ 过滤已被其他运行中客户端使用的密钥
- ✅ 日志显示优化（增加行数、自动刷新、自动滚动）

#### 退出管理页面
- ✅ 新增退出记录列表（显示所有退出操作的详细历史）

### 数据库变更

#### 新增表
- `users`: 用户表
- `audit_logs`: 审计日志表
- `exit_records`: 退出记录表

#### 修改的表
- `deposit_transactions`: 新增 `user_id` 字段

### API 变更

#### 新增端点
- `POST /api/v1/auth/wallet-login`: 钱包登录
- `POST /api/v1/auth/admin-login`: 管理员登录
- `GET /api/v1/auth/me`: 获取当前用户信息
- `POST /api/v1/auth/logout`: 登出
- `GET /api/v1/admin/export`: 导出数据
- `POST /api/v1/admin/import`: 导入数据
- `GET /api/v1/admin/audit-logs`: 获取审计日志
- `GET /api/v1/deposits/batch-contract/{contract_id}/deposits`: 获取合约存款记录
- `GET /api/v1/exits/records`: 获取退出记录列表
- `GET /api/v1/clients/{client_id}/keys/available`: 获取可用密钥列表

#### 修改的端点
- `GET /api/v1/deposits`: 新增 `withdrawal_address` 和 `total_withdrawn_eth` 字段，优化收益计算
- `POST /api/v1/exits/submit`: 自动创建退出记录

### 前端变更

#### 新增组件
- `components/Auth/LoginPage.tsx`: 登录页面
- `components/Auth/ProtectedRoute.tsx`: 路由保护组件
- `components/Admin/AdminPanel.tsx`: 管理员面板

#### 新增 Store
- `stores/authStore.ts`: 认证状态管理

#### 修改的组件
- `App.tsx`: 添加认证路由和权限控制
- `components/Layout/MainLayout.tsx`: 根据用户角色显示菜单
- `components/Contracts/BatchContractManager.tsx`: 添加存款记录 Tab
- `components/Deposits/DepositList.tsx`: 优化字段显示、添加批量选择
- `components/Clients/ClientKeyManagementModal.tsx`: 添加批量导入功能
- `components/Clients/ClientList.tsx`: 优化日志显示
- `components/Exits/ExitList.tsx`: 添加退出记录 Tab

### 依赖更新

#### 后端
- `passlib[bcrypt]>=1.7.4`: 密码哈希
- `python-jose[cryptography]>=3.3.0`: JWT token
- `python-multipart>=0.0.6`: 文件上传支持

### 配置变更

#### 环境变量
- `JWT_SECRET_KEY`: JWT 密钥（生产环境必须修改）

### 已知问题

无

### 升级说明

1. **数据库迁移**: 系统启动时会自动执行，无需手动操作
2. **创建管理员账户**: 首次部署后需要手动创建管理员账户（见 USER_AUTHENTICATION.md）
3. **JWT Secret**: 生产环境必须修改 `JWT_SECRET_KEY` 环境变量

### 向后兼容性

- ✅ 所有现有 API 端点保持兼容
- ✅ 数据库迁移向后兼容（不会删除现有数据）
- ✅ 未登录用户会被重定向到登录页面

---

## [2.0.0] - 2025-12-04

### 初始版本
- 密钥管理
- 存款管理
- 客户端管理
- 监控系统
- Web3Signer 集成
- 状态同步

