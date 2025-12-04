# 系统架构文档

## 整体架构

系统采用前后端分离架构：

- **后端**: FastAPI (Python) - RESTful API
- **前端**: React + TypeScript + Ant Design
- **数据库**: PostgreSQL (元数据) + Hashicorp Vault (私钥)
- **基础设施**: Docker Compose

## 核心组件

### 1. 密钥管理
- **存储架构**: 私钥存储在 Vault，元数据存储在 PostgreSQL
- **密钥生成**: 使用 ethstaker-deposit-cli 官方工具
- **状态管理**: 完整的状态流转机制

### 2. 存款管理
- **Deposit Data 生成**: 支持动态绑定 0x01 类型提款地址
- **批量提交**: 集成 Batch Deposit Contract，自动分批处理

### 3. Web3Signer 集成
- **高可用架构**: 双实例 + HAProxy
- **零停机更新**: 轮转更新机制

### 4. 状态同步
- **定期同步**: 每 1 个 epoch 从 Beacon Chain API 同步
- **实时同步**: 存款提交后立即查询

### 5. 端点发现
- **动态端点发现**: 从 Kurtosis 网络自动解析 RPC、WebSocket 和 Beacon API 端点
- **端口映射**: 通过 `host.docker.internal` 访问主机端口映射
- **降级策略**: 端点不可用时回退到配置的默认值

## 数据流

1. **密钥生成** → Vault (私钥) + PostgreSQL (元数据)
2. **激活密钥** → 更新 PostgreSQL 状态
3. **生成 Deposit Data** → 从 Vault 读取私钥签名
4. **提交存款** → Batch Deposit Contract
5. **状态同步** → Beacon Chain API → PostgreSQL

## 端点发现流程

系统运行在 Docker 容器中，需要访问运行在 Kurtosis 网络中的服务：

1. **动态端点发现**: 通过 `NetworkService` 从 Kurtosis enclave 信息中解析端口映射
2. **端点类型**:
   - **RPC 端点**: 执行层 RPC (端口 8545)
   - **WebSocket 端点**: 执行层 WebSocket (端口 8546)
   - **Beacon API 端点**: 共识层 REST API (端口 5052/4000/5051)
3. **访问方式**: 容器内使用 `host.docker.internal:映射端口` 访问

详细说明请参考 [端点发现流程文档](./ENDPOINT_DISCOVERY_FLOW.md)

