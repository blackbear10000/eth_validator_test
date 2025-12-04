# 端点发现流程文档

本文档描述系统如何从 Kurtosis 开发网络动态发现和访问各种端点（RPC、WebSocket、Beacon API）。

## 概述

系统运行在 Docker 容器中，需要访问运行在 Kurtosis 网络中的服务。由于网络隔离，不能直接使用 `localhost`，需要通过端口映射和动态端点发现机制。

## 网络架构

```
┌─────────────────────────────────────────────────────────┐
│                    Docker Host                            │
│                                                           │
│  ┌──────────────┐         ┌──────────────────────────┐  │
│  │   Backend    │         │   Kurtosis Network       │  │
│  │   Container  │         │   (eth-devnet)          │  │
│  │              │         │                          │  │
│  │  localhost   │         │  ┌────────────────────┐ │  │
│  │  :8001       │         │  │ Execution Layer    │ │  │
│  └──────┬───────┘         │  │ (Geth)             │ │  │
│         │                 │  │ RPC: 8545          │ │  │
│         │                 │  │ WS: 8546           │ │  │
│         │                 │  └────────────────────┘ │  │
│         │                 │                          │  │
│         │                 │  ┌────────────────────┐ │  │
│         │                 │  │ Consensus Layer   │ │  │
│         │                 │  │ (Prysm/Lighthouse)│ │  │
│         │                 │  │ Beacon API: 5052  │ │  │
│         │                 │  └────────────────────┘ │  │
│         │                 └──────────────────────────┘  │
│         │                          │                    │
│         └──────────────────────────┼────────────────────┘
│                                    │
│                          Port Mapping
│                   127.0.0.1:XXXXX -> Container:Port
│
└─────────────────────────────────────────────────────────┘
```

## 端点发现流程

### 1. 启动阶段

```
Backend Container 启动
  ↓
读取配置 (app/config.py)
  ↓
默认端点（硬编码）:
  - RPC: http://localhost:8545
  - Beacon API: http://localhost:5052
  ↓
尝试连接（可能失败）
```

### 2. 动态端点发现

```
API 请求（如 POST /api/v1/deposits/sync）
  ↓
调用 NetworkService.get_rpc_endpoints()
  ↓
调用 Kurtosis Manager API: GET /status
  ↓
获取 enclave 详细信息: kurtosis enclave inspect eth-devnet
  ↓
解析输出文本，查找端口映射
  ↓
提取端点信息
```

### 3. 端点解析逻辑

#### 3.1 RPC 端点解析

```python
# 查找执行层服务（el- 开头）
if re.search(r'el-\d+-\w+', line):
    # 查找 RPC 端口（8545）
    rpc_match = re.search(r'rpc\s*:\s*8545/tcp\s*->\s*([\d.]+):(\d+)', line)
    if rpc_match:
        host_ip = rpc_match.group(1)      # 127.0.0.1
        host_port = rpc_match.group(2)      # 33780
        # 转换为容器可访问的 URL
        rpc_url = f"http://host.docker.internal:{host_port}"
```

#### 3.2 WebSocket 端点解析

```python
# 查找 WS 端口（8546）
ws_match = re.search(r'ws\s*:\s*8546/tcp\s*->\s*([\d.]+):(\d+)', line)
if ws_match:
    host_ip = ws_match.group(1)
    host_port = ws_match.group(2)
    ws_url = f"ws://host.docker.internal:{host_port}"
```

#### 3.3 Beacon API 端点解析

```python
# 查找共识层服务（cl- 开头）
if re.search(r'cl-\d+-\w+', line):
    # 根据实际 Kurtosis enclave 输出：
    # - Prysm: http: 3500/tcp -> http://127.0.0.1:33785
    # - Lighthouse: http: 4000/tcp -> http://127.0.0.1:33790
    # - Teku: rest-api: 5051/tcp -> 127.0.0.1:XXXXX
    beacon_match = re.search(
        r'http\s*:\s*(?:3500|4000)/tcp\s*->\s*(?:http://)?([\d.]+):(\d+)',
        line
    )
    if beacon_match:
        host_ip = beacon_match.group(1)
        host_port = beacon_match.group(2)
        if host_ip == '127.0.0.1' or host_ip == '0.0.0.0':
            beacon_api_url = f"http://host.docker.internal:{host_port}"
        else:
            beacon_api_url = f"http://{host_ip}:{host_port}"
    else:
        # 尝试匹配 Teku 的 rest-api 端口
        teku_match = re.search(
            r'rest-api\s*:\s*5051/tcp\s*->\s*([\d.]+):(\d+)',
            line
        )
        if teku_match:
            host_ip = teku_match.group(1)
            host_port = teku_match.group(2)
            if host_ip == '127.0.0.1' or host_ip == '0.0.0.0':
                beacon_api_url = f"http://host.docker.internal:{host_port}"
            else:
                beacon_api_url = f"http://{host_ip}:{host_port}"
```

## Kurtosis Enclave 输出格式

### 示例输出

```
NAME                          STATUS    PORTS
el-1-geth-prysm               RUNNING   engine-rpc: 8551/tcp -> 127.0.0.1:33699
                                              rpc: 8545/tcp -> 127.0.0.1:33697
                                              ws: 8546/tcp -> 127.0.0.1:33698
cl-1-prysm-geth               RUNNING   http: 3500/tcp -> http://127.0.0.1:33785
                                              rpc: 4000/tcp -> 127.0.0.1:33786
cl-2-lighthouse-reth          RUNNING   http: 4000/tcp -> http://127.0.0.1:33790
```

### 解析规则

1. **服务识别**
   - 执行层：`el-\d+-\w+`（如 `el-1-geth-prysm`）
   - 共识层：`cl-\d+-\w+`（如 `cl-1-prysm`）

2. **端口映射格式**
   ```
   <port_name>: <container_port>/tcp -> <host_ip>:<host_port>
   ```

3. **端口类型**
   - RPC: `rpc: 8545/tcp`
   - WebSocket: `ws: 8546/tcp`
   - Beacon API (Prysm): `http: 3500/tcp` ⚠️ **注意**：Prysm 在 Kurtosis 中使用端口 3500（不是 5052）
   - Beacon API (Lighthouse): `http: 4000/tcp`
   - Beacon API (Teku): `rest-api: 5051/tcp`

## 端点使用流程

### 场景 1：存款状态同步

```
POST /api/v1/deposits/sync
  ↓
DepositManagementService.sync_transaction_status()
  ↓
1. 获取 RPC URL（用于查询交易状态）
   NetworkService.get_rpc_endpoints() → rpc_url
   ↓
2. 获取 Beacon API URL（用于验证验证者状态）
   NetworkService.get_rpc_endpoints() → beacon_api_url  ❌ 当前未实现
   ↓
3. 创建客户端
   ETH1Client(rpc_url)
   BeaconAPIClient(beacon_api_url)  ❌ 当前使用硬编码
   ↓
4. 执行同步
```

### 场景 2：生成 Deposit Data

```
POST /api/v1/deposits/generate
  ↓
DepositManagementService.generate_deposit_data_for_active_keys()
  ↓
需要获取 fork_version
  ↓
BeaconAPIClient().get_fork_version()  ❌ 使用硬编码 URL
  ↓
可能失败（如果 Beacon API 不可访问）
```

## 当前实现状态

### ✅ 已实现

- [x] `NetworkService.get_rpc_endpoints()` - 解析 RPC 端点
- [x] `NetworkService.get_rpc_endpoints()` - 解析 WebSocket 端点
- [x] `NetworkService.get_rpc_endpoints()` - 解析 Beacon API 端点（Prysm: 3500, Lighthouse: 4000, Teku: 5051）
- [x] 在 `deposits/submit` 中使用动态 RPC URL
- [x] 在 `deposits/sync` 中使用动态 RPC URL
- [x] `BeaconAPIClient.get_validator()` - 修复 pubkey 格式，确保有 0x 前缀

### ❌ 待实现

- [ ] 在所有使用 `BeaconAPIClient` 的地方使用动态 URL（从 `get_rpc_endpoints()` 获取）
- [ ] Beacon API 端点健康检查
- [ ] 端点不可用时的降级策略

## 端点访问方式

### 容器内访问

在 Docker 容器中，使用 `host.docker.internal` 访问主机端口：

```python
# 从 Kurtosis 获取的端口映射
127.0.0.1:33780 -> Container:8545

# 容器内访问方式
rpc_url = "http://host.docker.internal:33780"
```

### 主机访问

从宿主机访问，使用 `localhost`：

```python
# 主机访问方式
host_rpc_url = "http://localhost:33780"
```

### 容器间访问（如果 Beacon 节点也在 Docker 中）

如果 Beacon 节点也在 Docker Compose 网络中，可以使用容器名：

```python
# 如果 Beacon 节点容器名为 beacon-node
beacon_api_url = "http://beacon-node:5052"
```

**注意**：当前架构中，Beacon 节点运行在 Kurtosis 网络中，不在 Docker Compose 网络中，所以需要使用端口映射。

## 配置优先级

端点 URL 的获取优先级：

1. **动态发现**（最高优先级）
   - 从 Kurtosis 网络自动解析
   - 通过 `NetworkService.get_rpc_endpoints()` 获取

2. **环境变量**
   - `EXECUTION_RPC_URL`
   - `BEACON_API_URL`（待添加）

3. **配置文件**
   - `settings.execution_rpc_url`
   - `settings.beacon_api_url`（硬编码默认值）

## 错误处理

### 端点不可用

```python
try:
    endpoints = network_service.get_rpc_endpoints()
    rpc_url = endpoints.get("rpc_url")
except Exception as e:
    logger.warning(f"无法从网络服务获取 RPC URL: {e}")
    # 降级到配置
    rpc_url = settings.execution_rpc_url
```

### 连接失败

```python
try:
    beacon_api = BeaconAPIClient(base_url=beacon_api_url)
    validator_data = beacon_api.get_validator(pubkey)
except BeaconAPIError as e:
    logger.error(f"Beacon API 请求失败: {e}")
    # 返回错误或使用缓存数据
    return None
```

## 改进建议

### 短期（立即修复）

1. **扩展端点解析**
   - 在 `get_rpc_endpoints()` 中添加 Beacon API 端口解析
   - 支持 Prysm、Lighthouse、Teku 的常见端口

2. **更新服务调用**
   - 在所有创建 `BeaconAPIClient` 的地方传入动态 URL
   - 优先使用从网络服务获取的 URL

### 中期（优化）

1. **统一端点管理**
   - 创建 `EndpointService` 统一管理所有端点
   - 提供端点缓存和自动刷新机制

2. **健康检查**
   - 在启动时验证所有端点是否可访问
   - 提供端点状态监控 API

3. **降级策略**
   - 端点不可用时的备用方案
   - 支持多个 Beacon API 节点（负载均衡）

### 长期（架构优化）

1. **服务发现集成**
   - 集成 Consul 或其他服务发现工具
   - 自动注册和发现服务端点

2. **配置中心**
   - 将端点配置集中管理
   - 支持动态配置更新

## 相关代码位置

- `app/services/network_service.py` - 网络服务和端点解析
- `app/core/beacon_api.py` - Beacon API 客户端
- `app/services/deposit_management.py` - 存款管理服务
- `app/services/deposit_validation.py` - 存款验证服务
- `app/config.py` - 配置管理

## 相关文档

- [Beacon API 连接问题分析](./BEACON_API_CONNECTION_ISSUE.md)
- [Docker 网络说明](./DOCKER_NETWORK_EXPLAINED.md)
- [架构文档](./ARCHITECTURE.md)

