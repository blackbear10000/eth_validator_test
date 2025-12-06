# Prysm Beacon 端点参数对比

## 参数对比

### `--beacon-rpc-provider` (gRPC)
- **协议**: gRPC
- **默认值**: `127.0.0.1:4000`
- **格式**: `host:port`（不需要 `http://` 前缀）
- **状态**: ⚠️ **已弃用警告** - gRPC API 将在 v8（2026年）后被移除，推荐使用 REST API
- **性能**: 高性能，低延迟
- **用途**: 默认的通信方式，Prysm validator 主要使用 gRPC 与 beacon node 通信

### `--beacon-rest-api-provider` (REST API)
- **协议**: HTTP REST API
- **默认值**: `http://127.0.0.1:3500`
- **格式**: `http://host:port` 或 `https://host:port`（需要协议前缀）
- **状态**: ✅ **推荐** - 未来的标准，Prysm 计划在 v8 后完全迁移到 REST API
- **性能**: 略低于 gRPC（因为 REST API 是基于 gRPC 网关实现的）
- **用途**: 标准化的 HTTP 接口，更容易与其他系统集成

## 关系

1. **两者可以同时使用**：Prysm validator 可以同时配置 gRPC 和 REST API 端点
2. **优先级**：如果同时配置，Prysm 会优先使用 gRPC（如果可用）
3. **互操作性**：REST API 更容易与其他客户端（Lighthouse、Teku）集成
4. **未来趋势**：Prysm 计划在 v8 后移除 gRPC API，完全使用 REST API

## 建议

### 当前推荐（2025年）

**优先使用 `--beacon-rpc-provider`（gRPC）**，原因：
1. ✅ 是 Prysm 的默认通信方式
2. ✅ 性能更好，延迟更低
3. ✅ 目前完全支持，直到 v8（2026年）
4. ✅ 与 Prysm beacon node 的集成最成熟

**示例：**
```bash
--beacon-rpc-provider host.docker.internal:33838
```

### 未来兼容性（2026年后）

如果考虑长期兼容性，可以：
1. **同时配置两者**（推荐）：
   ```bash
   --beacon-rpc-provider host.docker.internal:33838
   --beacon-rest-api-provider http://host.docker.internal:33837
   ```

2. **仅使用 REST API**（如果 gRPC 不可用）：
   ```bash
   --beacon-rest-api-provider http://host.docker.internal:33837
   --enable-beacon-rest-api  # 启用 REST API 查询（实验性）
   ```

### 我们的配置建议

**当前实现（推荐）：**
- 使用 `--beacon-rpc-provider` 配置 gRPC 端点
- 这是 Prysm 的默认方式，性能最好
- 与我们的 Kurtosis 网络配置匹配（Prysm beacon node 的 gRPC 端口是 4000）

**配置示例：**
```bash
prysm validator \
  --accept-terms-of-use \
  --beacon-rpc-provider host.docker.internal:33838 \
  --config-file /config/config.yaml \
  --validators-external-signer-url http://haproxy:9002 \
  --web \
  --validators-external-signer-key-file /config/pubkey_persistence.txt \
  --wallet-dir /wallet
```

## 端口映射说明

根据 Kurtosis 网络配置：
- **gRPC 端口**: `4000` → 映射到宿主机 `33838`
- **REST API 端口**: `3500` → 映射到宿主机 `33837`

所以：
- `--beacon-rpc-provider host.docker.internal:33838` ✅
- `--beacon-rest-api-provider http://host.docker.internal:33837` ✅

## 总结

**当前建议：使用 `--beacon-rpc-provider`**
- 性能更好
- 是 Prysm 的默认方式
- 完全支持到 2026年
- 与我们的配置匹配

**未来考虑：可以同时配置两者**
- 提高兼容性
- 为未来的迁移做准备
- 提供冗余（如果 gRPC 失败，可以回退到 REST API）

