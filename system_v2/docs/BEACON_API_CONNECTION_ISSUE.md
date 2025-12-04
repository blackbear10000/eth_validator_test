# Beacon API 连接问题分析

## 问题描述

在调用 `POST /api/v1/deposits/sync` 端点时，系统尝试连接 Beacon API (`http://localhost:5052`)，但连接被拒绝。

### 错误日志

```
Beacon API 请求失败: http://localhost:5052/eth/v1/beacon/states/head/validators/805ceabc2ef1413f9f60ed6c464fce64e6069cb32b4c37f8936646750a4191e334dc2dea837b415600e8aeeae95a066a
HTTPConnectionPool(host='localhost', port=5052): Max retries exceeded with url: /eth/v1/beacon/states/head/validators/...
(Caused by NewConnectionError: Failed to establish a new connection: [Errno 111] Connection refused)
```

### 系统行为

从日志中可以看到：
1. ✅ 成功从 Consul 读取 Vault token
2. ✅ 成功找到 RPC 端口映射：`127.0.0.1:33780 -> http://host.docker.internal:33780`
3. ✅ 成功找到 WS 端口映射：`127.0.0.1:33781 -> ws://host.docker.internal:33781`
4. ❌ **Beacon API 连接失败**：使用硬编码的 `http://localhost:5052`，连接被拒绝

## 问题根源

### 1. 硬编码的 Beacon API URL

在 `app/config.py` 中，Beacon API URL 被硬编码为：

```python
beacon_api_url: str = "http://localhost:5052"
```

**注意**：根据实际的 Kurtosis enclave 输出，Prysm 的 Beacon API 端口是 **3500**（不是 5052），Lighthouse 的端口是 **4000**。

### 2. Docker 容器网络问题

当后端服务运行在 Docker 容器中时：
- `localhost:5052` 指向**容器自己**，而不是 Beacon 节点
- Beacon 节点运行在 Kurtosis 网络中，需要通过端口映射访问
- 系统已经能够从 Kurtosis 网络获取 RPC 端点，但没有类似机制获取 Beacon API 端点

### 3. 缺少动态端点发现

与 RPC 端点不同，系统没有从 Kurtosis 网络动态获取 Beacon API 端点的机制：

- ✅ `NetworkService.get_rpc_endpoints()` - 能够从 Kurtosis enclave 输出中解析 RPC 端口
- ❌ **缺少** `NetworkService.get_beacon_api_endpoint()` - 无法动态获取 Beacon API 端口

## 架构分析

### 当前端点获取流程

```
POST /api/v1/deposits/sync
  ↓
DepositManagementService.sync_transaction_status()
  ↓
NetworkService.get_rpc_endpoints()  ✅ 动态获取 RPC URL
  ↓
BeaconAPIClient()  ❌ 使用硬编码的 settings.beacon_api_url
  ↓
http://localhost:5052  ❌ 连接失败
```

### 相关代码位置

1. **Beacon API 客户端初始化**
   - `app/core/beacon_api.py:23-30`
   - 使用 `settings.beacon_api_url` 或传入的 `base_url`

2. **同步服务调用**
   - `app/services/deposit_management.py:444-602`
   - `sync_transaction_status()` 方法中创建 `BeaconAPIClient()` 时没有传入动态 URL

3. **网络服务**
   - `app/services/network_service.py:165-284`
   - `get_rpc_endpoints()` 只解析 RPC 和 WS 端口，不解析 Beacon API 端口

## 解决方案

### 方案 1：扩展 NetworkService 支持 Beacon API 端点（推荐）

#### 1.1 扩展 `get_rpc_endpoints()` 方法

修改 `NetworkService.get_rpc_endpoints()` 以同时解析 Beacon API 端口：

```python
def get_rpc_endpoints(self) -> Dict[str, Any]:
    """
    从 Kurtosis enclave 信息中提取 RPC 和 Beacon API 端点
    
    Returns:
        包含 rpc_url、ws_url 和 beacon_api_url 的字典
    """
    # ... 现有 RPC/WS 解析逻辑 ...
    
    # 查找 Beacon API 端口（在 cl- 开头的共识层服务中）
    # 根据实际 enclave 输出：
    # - Prysm: http: 3500/tcp -> http://127.0.0.1:33785
    # - Lighthouse: http: 4000/tcp -> http://127.0.0.1:33790
    # - Teku: rest-api: 5051/tcp -> 127.0.0.1:XXXXX
    beacon_api_url = None
    in_cl_service = False
    
    for line in lines:
        # 检查是否是共识层服务（cl- 开头，如 cl-1-prysm-geth, cl-2-lighthouse-reth）
        if re.search(r'cl-\d+-\w+', line):
            in_cl_service = True
            continue
        
        if in_cl_service:
            # 查找 HTTP API 端口（Prysm: 3500, Lighthouse: 4000）
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
                logger.info(f"找到 Beacon API 端口映射: {host_ip}:{host_port} -> {beacon_api_url}")
                break
    
    return {
        "rpc_url": rpc_url,
        "host_rpc_url": host_rpc_url,
        "ws_url": ws_url,
        "host_ws_url": host_ws_url,
        "beacon_api_url": beacon_api_url,  # 新增
        "host_beacon_api_url": beacon_api_url.replace('host.docker.internal', 'localhost') if beacon_api_url else None,
        "service": current_service
    }
```

#### 1.2 修改 `sync_transaction_status()` 使用动态 Beacon API URL

在 `app/services/deposit_management.py` 中：

```python
def sync_transaction_status(self, ...):
    # ... 现有 RPC URL 获取逻辑 ...
    
    # 获取 Beacon API URL
    beacon_api_url = None
    try:
        network_service = NetworkService()
        endpoints = network_service.get_rpc_endpoints()
        beacon_api_url = endpoints.get("beacon_api_url")
    except Exception as e:
        logger.warning(f"无法从网络服务获取 Beacon API URL: {e}")
    
    if not beacon_api_url:
        from app.config import settings
        beacon_api_url = settings.beacon_api_url
    
    # 使用动态 URL 创建 Beacon API 客户端
    beacon_api = BeaconAPIClient(base_url=beacon_api_url)
    validation_service = DepositValidationService(
        db=self.db,
        beacon_api=beacon_api,
        web3=eth1_client.web3
    )
```

### 方案 2：环境变量配置（临时方案）

如果无法从 Kurtosis 网络自动发现，可以通过环境变量配置：

```bash
# docker-compose.yml
backend:
  environment:
    - BEACON_API_URL=http://host.docker.internal:XXXXX  # 从 Kurtosis 获取的实际端口
```

然后在 `app/config.py` 中：

```python
beacon_api_url: str = os.getenv("BEACON_API_URL", "http://localhost:5052")
```

## 实施建议

### 优先级 1：立即修复

1. **扩展 NetworkService**
   - 在 `get_rpc_endpoints()` 中添加 Beacon API 端口解析
   - 支持常见的 Beacon 客户端端口（Prysm: 3500, Lighthouse: 4000, Teku: 5051）
   - **注意**：根据实际 Kurtosis 输出，Prysm 使用端口 3500（不是 5052）

2. **修复 Beacon API pubkey 格式问题**
   - Beacon API 请求 `/eth/v1/beacon/states/head/validators/{pubkey}` 中，pubkey **必须**包含 `0x` 前缀
   - 修复 `BeaconAPIClient.get_validator()` 方法，确保 pubkey 有 0x 前缀

2. **修改同步服务**
   - 在 `sync_transaction_status()` 中动态获取 Beacon API URL
   - 在 `DepositValidationService` 初始化时传入动态 URL

### 优先级 2：其他使用 Beacon API 的地方

检查并更新所有创建 `BeaconAPIClient` 的地方：

- `app/services/deposit_management.py:80, 96` - 生成 Deposit Data 时
- `app/services/deposit_validation.py:42` - 验证服务初始化
- `app/services/sync_service.py` - 状态同步服务
- `app/services/network_service.py:319` - 网络信息获取
- `app/services/deposit_sync_scheduler.py` - 定时同步
- `app/services/withdrawal_service.py` - 提款服务
- `app/services/withdrawal_listener.py` - 提款监听
- `app/services/exit_service.py` - 退出服务
- `app/services/monitoring_service.py` - 监控服务

### 优先级 3：配置管理优化

1. **创建统一的端点获取服务**
   ```python
   class EndpointService:
       def get_all_endpoints(self) -> Dict[str, str]:
           """获取所有端点（RPC, WS, Beacon API）"""
           # ...
   ```

2. **添加端点健康检查**
   - 在启动时验证所有端点是否可访问
   - 提供端点状态监控

## 测试建议

1. **单元测试**
   - 测试 `NetworkService.get_rpc_endpoints()` 的 Beacon API 端口解析
   - 测试不同 Beacon 客户端（Prysm, Lighthouse, Teku）的端口识别

2. **集成测试**
   - 测试在 Docker 容器中从 Kurtosis 网络获取端点
   - 测试端点不可用时的降级策略

3. **手动验证**
   ```bash
   # 在容器内测试 Beacon API 连接
   docker exec backend curl http://host.docker.internal:XXXXX/eth/v1/node/health
   ```

## 相关文档

- [Docker 网络说明](./DOCKER_NETWORK_EXPLAINED.md)
- [架构文档](./ARCHITECTURE.md)
- [状态检测分析](./STATUS_DETECTION_ANALYSIS.md)

## 总结

**问题**：Beacon API 使用硬编码的 `localhost:5052`，在 Docker 容器中无法访问 Kurtosis 网络中的 Beacon 节点。

**根本原因**：缺少从 Kurtosis 网络动态获取 Beacon API 端点的机制。

**解决方案**：扩展 `NetworkService` 以解析 Beacon API 端口，并在所有使用 `BeaconAPIClient` 的地方传入动态 URL。

**影响范围**：所有需要查询 Beacon Chain 状态的功能都会受到影响，包括：
- 存款状态同步
- 验证者状态验证
- 网络信息获取
- 监控和告警

