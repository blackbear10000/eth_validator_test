# 客户端管理文档

## 概述

客户端管理功能负责管理 Validator Client 实例（Prysm、Lighthouse、Teku），包括创建、编辑、删除客户端，分配密钥，以及通过 Remote Validator API 动态更新密钥列表。

## 核心功能

### 1. 客户端实例管理

#### 创建客户端
- **端点**: `POST /api/v1/clients`
- **功能**: 创建新的 Validator Client 实例
- **自动处理**:
  - URL 自动转换（localhost -> 容器可访问的 URL）
  - Beacon API URL 自动从 Kurtosis 网络获取（如果未提供）

#### 编辑客户端
- **端点**: `PUT /api/v1/clients/{client_id}`
- **功能**: 更新客户端配置（名称、URL、备注等）
- **支持字段**: name, beacon_api_url, grpc_endpoint, web3signer_url, notes, is_active

#### 删除客户端
- **端点**: `DELETE /api/v1/clients/{client_id}`
- **功能**: 删除客户端实例（支持软删除和硬删除）
- **参数**: `hard_delete` (bool) - 是否硬删除

#### 查询客户端
- **端点**: `GET /api/v1/clients` - 列出所有客户端
- **端点**: `GET /api/v1/clients/{client_id}` - 获取客户端详情

### 2. 密钥分配与管理

#### 分配密钥到客户端
- **端点**: `PUT /api/v1/clients/{client_id}/keys`
- **功能**: 将密钥分配到客户端
- **状态要求**: 只允许 `ACTIVE` 和 `DEPOSIT_DATA_GENERATED` 状态的密钥
- **自动处理**:
  - 生成客户端配置文件
  - 通过 Remote Validator API 动态添加密钥（如果启用）

#### 移除密钥
- **功能**: 从客户端移除密钥
- **自动处理**:
  - 重新生成配置文件
  - 通过 Remote Validator API 动态删除密钥

### 3. Remote Validator API 集成

#### 动态密钥同步
- **端点**: `POST /api/v1/clients/{client_id}/sync-keys`
- **功能**: 同步所有 ACTIVE 状态的密钥到 Validator Client
- **机制**: 
  - 获取当前已加载的密钥列表
  - 计算需要添加和删除的密钥
  - 增量更新（只添加/删除变化的密钥）

#### Remote Validator API URL 推断

系统会根据客户端类型和 Beacon API URL 自动推断 Remote Validator API URL：

- **Prysm**: 
  - 如果 Beacon API 端口是 3500，使用 7500 端口
  - 否则使用 Beacon API 的同一端口
- **Lighthouse**: 使用 5062 端口（HTTP API）
- **Teku**: 使用 5051 端口（REST API）

### 4. Web3Signer 自动加载

#### 自动加载机制
- **触发时机**: 密钥激活时（`activate_keys`）
- **流程**:
  1. 密钥状态更新为 ACTIVE
  2. 自动触发 Web3Signer 零停机重新加载
  3. Web3Signer 从 Vault 读取所有密钥（包括新激活的）
  4. 两个 Web3Signer 实例滚动更新

#### 零停机更新
- **方法**: `Web3SignerClient.zero_downtime_reload()`
- **流程**:
  1. Web3Signer-2 执行 reload-new-keys
  2. 等待健康检查
  3. HAProxy 自动切换到 Web3Signer-2
  4. Web3Signer-1 执行 reload-new-keys
  5. 完成轮转

## 密钥状态管理

### 状态流转

```
UNUSED -> ACTIVE -> DEPOSIT_DATA_GENERATED -> PENDING -> DEPOSITED -> ACTIVE_ON_CHAIN
```

### 关键状态说明

- **ACTIVE**: 已激活，准备用于存款，可以加载到客户端
- **DEPOSIT_DATA_GENERATED**: 已生成 Deposit Data，等待提交存款，**可以加载到客户端**
- **PENDING**: 已提交存款，等待链上确认，**不应加载到客户端**

### 状态转换规则

- 生成 Deposit Data 时：`ACTIVE -> DEPOSIT_DATA_GENERATED`
- 提交存款时：`DEPOSIT_DATA_GENERATED -> PENDING` 或 `ACTIVE -> PENDING`
- 只有 `ACTIVE` 和 `DEPOSIT_DATA_GENERATED` 状态的密钥可以加载到客户端

## 跨容器 URL 处理

### 自动转换规则

系统会自动将 localhost URL 转换为容器可访问的 URL：

1. **Beacon API URL**:
   - 优先从 Kurtosis 网络获取（`NetworkService.get_rpc_endpoints()`）
   - 如果无法获取，将 `localhost` 转换为 `host.docker.internal`

2. **Web3Signer URL**:
   - `localhost:9000` -> `web3signer-1:9000`
   - `localhost:9001` -> `web3signer-2:9000`
   - `localhost:9002` -> `haproxy:9002`

3. **gRPC Endpoint**:
   - `localhost` -> `host.docker.internal`

### URL 转换方法

`ClientManagementService._convert_url_for_container()` 方法负责 URL 转换：
- 检查 URL 是否包含 localhost 或 127.0.0.1
- 根据 URL 类型（beacon_api, web3signer, grpc）应用不同的转换规则
- 保留非 localhost URL 不变

## Remote Validator API 使用

### API 端点

Remote Validator API 遵循以太坊标准：

- `GET /eth/v1/keystores` - 获取密钥列表
- `POST /eth/v1/keystores` - 添加密钥
- `DELETE /eth/v1/keystores` - 删除密钥

### 添加密钥请求格式

```json
{
  "keystores": [
    {
      "validating_pubkey": "0x...",
      "derivation_path": "",
      "readonly": false
    }
  ],
  "passwords": [""],
  "slashing_protection": null
}
```

### 删除密钥请求格式

```json
{
  "pubkeys": ["0x...", "0x..."]
}
```

### 响应格式

```json
{
  "data": {
    "statuses": [
      {
        "status": "imported" | "duplicate" | "error",
        "message": "..."
      }
    ],
    "slashing_protection": {...}
  }
}
```

## 滚动升级机制

### 多实例滚动更新

`ClientManagementService.rolling_update_keys()` 方法支持多个客户端实例的滚动更新：

1. 按顺序更新每个实例
2. 每次更新后等待健康检查
3. 继续更新下一个实例
4. 确保至少有一个实例始终可用

### 使用场景

- 更新多个 Validator Client 实例的密钥列表
- 确保验证服务不中断
- 支持高可用部署

## 工作流程示例

### 场景 1：激活密钥并自动加载到 Web3Signer

```
1. 用户调用 POST /api/v1/keys/activate
2. 密钥状态更新为 ACTIVE
3. 自动触发 Web3Signer.zero_downtime_reload()
4. Web3Signer 从 Vault 读取所有密钥（包括新激活的）
5. 两个 Web3Signer 实例滚动更新
6. 完成
```

### 场景 2：分配密钥到客户端

```
1. 用户调用 PUT /api/v1/clients/{client_id}/keys
2. 检查密钥状态（只允许 ACTIVE 和 DEPOSIT_DATA_GENERATED）
3. 创建 ValidatorClientKey 映射关系
4. 生成客户端配置文件
5. 通过 Remote Validator API 添加密钥到 Validator Client
6. 完成
```

### 场景 3：生成 Deposit Data

```
1. 用户调用 POST /api/v1/deposits/generate
2. 查询 ACTIVE 状态的密钥
3. 生成 Deposit Data
4. 密钥状态更新为 DEPOSIT_DATA_GENERATED（使用状态机）
5. 密钥仍然可以加载到客户端
6. 返回 Deposit Data
```

### 场景 4：提交存款

```
1. 用户调用 POST /api/v1/deposits/submit
2. 提交存款交易到链上
3. 密钥状态从 DEPOSIT_DATA_GENERATED 或 ACTIVE 更新为 PENDING（使用状态机）
4. 创建 DepositTransaction 记录
5. 完成
```

### 场景 5：同步所有密钥到客户端

```
1. 用户调用 POST /api/v1/clients/{client_id}/sync-keys
2. 查询所有 ACTIVE 和 DEPOSIT_DATA_GENERATED 状态的密钥
3. 获取 Validator Client 当前已加载的密钥列表
4. 计算差异（需要添加和删除的密钥）
5. 通过 Remote Validator API 增量更新
6. 完成
```

## 配置要求

### Validator Client 配置

Validator Client 需要启用 Remote Validator API：

- **Prysm**: 配置 `--validator-web` 和 `--web-port`
- **Lighthouse**: 配置 `[http]` 部分的 `address` 和 `port`
- **Teku**: 配置 `beacon-rest-api-enabled` 和 `beacon-rest-api-port`

### Web3Signer 配置

Web3Signer 需要配置 Vault 作为密钥存储：

- `VAULT_ADDR`: Vault 地址
- `VAULT_TOKEN`: Vault 认证 Token
- `key-store-path`: 密钥存储路径（如果使用文件系统）

## 错误处理

### Remote Validator API 失败

如果 Remote Validator API 调用失败：
- 记录错误日志
- 密钥分配仍然成功（配置文件已生成）
- 用户可以手动触发同步或重启客户端

### Web3Signer 重新加载失败

如果 Web3Signer 重新加载失败：
- 记录警告日志
- 密钥激活仍然成功
- 用户可以手动触发 Web3Signer 重新加载

## 最佳实践

1. **密钥状态管理**:
   - 生成 Deposit Data 后，密钥状态为 `DEPOSIT_DATA_GENERATED`，仍可加载到客户端
   - 提交存款后，密钥状态为 `PENDING`，不应加载到客户端

2. **URL 配置**:
   - 优先使用容器名（如 `web3signer-1:9000`）
   - 系统会自动转换 localhost URL

3. **密钥同步**:
   - 定期调用 `sync-keys` 端点确保密钥列表同步
   - 或者在分配/移除密钥时自动同步

4. **滚动升级**:
   - 更新多个实例时使用 `rolling_update_keys()` 方法
   - 确保至少有一个实例始终可用

## 相关文档

- [API 文档](./API.md)
- [架构文档](./ARCHITECTURE.md)
- [端点发现流程](./ENDPOINT_DISCOVERY_FLOW.md)
- [Beacon API 连接问题](./BEACON_API_CONNECTION_ISSUE.md)

