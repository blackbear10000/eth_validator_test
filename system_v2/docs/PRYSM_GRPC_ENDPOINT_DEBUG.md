# Prysm gRPC 端点配置问题诊断

## 问题描述

Prysm 客户端启动后，日志显示仍然尝试连接 `127.0.0.1:4000`，而不是配置的 gRPC 端点（如 `host.docker.internal:33838`）。

**错误日志：**
```
time="2025-12-06 10:24:21" level=warning msg="Could not determine if beacon chain started" 
error="could not receive ChainStart from stream: could not setup beacon chain ChainStart streaming client: 
rpc error: code = Unavailable desc = connection error: desc = "transport: Error while dialing: 
dial tcp 127.0.0.1:4000: connect: connection refused": could not connect: could not connect" prefix=client
```

## 配置流程检查清单

### 1. 数据库中的 gRPC 端点配置

**检查方法：**
```sql
SELECT id, name, client_type, grpc_endpoint, beacon_api_url 
FROM client_instances 
WHERE id = <client_id>;
```

**期望值：**
- `grpc_endpoint` 应该是 `host.docker.internal:33838` 或类似的值
- 如果为 `NULL` 或 `127.0.0.1:4000`，说明配置未正确保存

### 2. 配置文件生成日志

**检查后端日志：**
```bash
docker logs backend | grep -i "prysm 配置\|grpc 端点\|rpc-host"
```

**期望日志：**
```
[Prysm 配置] 从数据库获取 gRPC 端点: host.docker.internal:33838
[Prysm 配置] gRPC 端点转换: host.docker.internal:33838 -> host.docker.internal:33838
[Prysm 配置] 最终使用的 gRPC 端点: host.docker.internal:33838
[Prysm 配置] 生成配置文件: /path/to/config.yaml
[Prysm 配置] 配置文件内容 - rpc-host: host.docker.internal:33838
[Prysm 配置] ✅ 配置文件中的 rpc-host 已正确设置: host.docker.internal:33838
```

### 3. 实际生成的配置文件

**检查方法：**
```bash
# 在宿主机上
cat /path/to/validator-clients/configs/prysm/vc-<id>/config.yaml

# 或在容器内
docker exec validator-client-<id>-prysm cat /config/config.yaml
```

**期望内容：**
```yaml
validator:
  wallet-dir: /wallet
  wallet-password-file: /wallet/password.txt
  graffiti: prysm-vc-<id>
beacon-chain:
  rpc-host: host.docker.internal:33838  # 应该是正确的值，不是 127.0.0.1:4000
  web3-provider: http://host.docker.internal:33837
slashing-protection-db-url: postgresql://postgres:password@localhost:5432/web3signer
```

### 4. 容器启动命令

**检查后端日志：**
```bash
docker logs backend | grep -i "prysm 启动\|启动客户端容器"
```

**期望日志：**
```
[Prysm 启动] 使用配置文件: /config/config.yaml
[Prysm 启动] 从配置文件读取 gRPC 端点: host.docker.internal:33838
[Prysm 启动] ⚠️  配置文件中的 gRPC 端点应该是: host.docker.internal:33838
启动客户端容器 validator-client-<id>-prysm: docker run -d --name ... --config-file /config/config.yaml ...
```

### 5. Prysm 容器内的配置文件

**检查方法：**
```bash
docker exec validator-client-<id>-prysm cat /config/config.yaml
```

**如果配置文件中的 `rpc-host` 仍然是 `127.0.0.1:4000` 或默认值，说明：**
- 配置文件生成时使用了错误的 gRPC 端点
- 或者配置文件被覆盖了

### 6. Prysm 启动参数

**检查方法：**
```bash
docker inspect validator-client-<id>-prysm | grep -A 20 "Args"
```

**期望参数：**
```json
"Args": [
  "--accept-terms-of-use",
  "--config-file", "/config/config.yaml",
  "--validators-external-signer-url", "http://haproxy:9002",
  "--web",
  "--validators-external-signer-key-file", "/config/pubkey_persistence.txt",
  "--wallet-dir", "/wallet"
]
```

## 可能的问题和解决方案

### 问题 1: 配置文件中的 rpc-host 未正确设置

**症状：** 配置文件中的 `rpc-host` 是 `127.0.0.1:4000` 或默认值

**原因：**
- `client_instance.grpc_endpoint` 为空或未正确转换
- 配置文件生成时使用了默认值

**解决方案：**
1. 检查数据库中的 `grpc_endpoint` 值
2. 重新生成配置文件（删除旧配置，重新启动客户端）
3. 检查后端日志中的 `[Prysm 配置]` 日志

### 问题 2: Prysm 未正确读取配置文件

**症状：** 配置文件中的 `rpc-host` 是正确的，但 Prysm 仍然使用默认值

**原因：**
- Prysm 可能不支持通过配置文件设置 `rpc-host`
- 配置文件格式不正确
- Prysm 版本问题

**解决方案：**
1. 检查 Prysm 版本和文档，确认是否支持 `beacon-chain.rpc-host` 配置
2. 尝试使用命令行参数（如果支持）
3. 检查配置文件格式是否正确（YAML 语法）

### 问题 3: 配置文件路径错误

**症状：** Prysm 无法找到配置文件

**解决方案：**
1. 检查容器内的配置文件路径：`/config/config.yaml`
2. 检查 Docker 挂载是否正确
3. 检查文件权限

## 调试步骤

### 步骤 1: 检查数据库配置
```sql
SELECT * FROM client_instances WHERE id = <client_id>;
```

### 步骤 2: 检查后端日志
```bash
docker logs backend --tail 100 | grep -i "prysm\|grpc\|rpc-host"
```

### 步骤 3: 检查生成的配置文件
```bash
# 找到配置文件路径
docker logs backend | grep "生成配置文件\|config_file"

# 查看配置文件内容
cat <config_file_path>
```

### 步骤 4: 检查容器内的配置文件
```bash
docker exec validator-client-<id>-prysm cat /config/config.yaml
```

### 步骤 5: 检查 Prysm 启动参数
```bash
docker inspect validator-client-<id>-prysm | jq '.[0].Args'
```

### 步骤 6: 检查 Prysm 容器日志
```bash
docker logs validator-client-<id>-prysm --tail 50
```

## 修复后的代码改进

### 1. 添加了详细的调试日志

- `[Prysm 配置]` 前缀的日志，追踪 gRPC 端点配置流程
- `[Prysm 启动]` 前缀的日志，追踪容器启动过程

### 2. 配置文件验证

- 生成配置文件后，验证 `rpc-host` 是否正确写入
- 如果验证失败，记录错误日志

### 3. 配置文件读取验证

- 启动容器前，从配置文件读取 gRPC 端点并记录日志
- 用于验证配置文件是否正确生成

## 下一步行动

1. **重新启动客户端**，查看新的调试日志
2. **检查后端日志**，确认 gRPC 端点配置流程
3. **检查生成的配置文件**，确认 `rpc-host` 值
4. **如果配置文件正确但 Prysm 仍使用默认值**，可能需要：
   - 检查 Prysm 版本和文档
   - 尝试使用命令行参数（如果支持）
   - 检查 Prysm 的配置文件格式要求

