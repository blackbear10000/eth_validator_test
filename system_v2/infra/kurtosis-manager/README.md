# Kurtosis 管理服务

独立的 Kurtosis 网络管理服务，通过 HTTP API 提供网络启动、停止和状态查询功能。

## 工作原理

### Docker Socket 挂载（不是 Docker-in-Docker）

- **挂载 Docker socket** (`/var/run/docker.sock:/var/run/docker.sock`)
- Kurtosis CLI 在容器内运行，但通过 socket **连接到主机的 Docker daemon**
- Kurtosis 创建的容器（Geth、Prysm 等）运行在**主机上**，不是嵌套容器
- 这些容器与 kurtosis-manager 容器**平级**，都在主机 Docker 网络中

### 架构

```
┌─────────────────────────────────────────┐
│           主机 Docker                   │
│                                         │
│  ┌──────────────────────────────────┐  │
│  │  kurtosis-manager 容器           │  │
│  │  - Kurtosis CLI                  │  │
│  │  - HTTP API                      │  │
│  └───────────┬──────────────────────┘  │
│              │ Docker Socket            │
│              │ (/var/run/docker.sock)   │
│              ▼                          │
│  ┌──────────────────────────────────┐  │
│  │  Kurtosis 创建的容器（主机上）   │  │
│  │  - Geth                          │  │
│  │  - Prysm                         │  │
│  │  - Lighthouse                    │  │
│  │  - ...                           │  │
│  └──────────────────────────────────┘  │
└─────────────────────────────────────────┘
```

## API 端点

### GET /health
健康检查

### GET /status
获取网络状态

响应示例：
```json
{
  "enclave_name": "eth-devnet",
  "is_running": true,
  "status": "running",
  "enclave_info": {...}
}
```

### POST /start
启动 Kurtosis 网络

响应示例：
```json
{
  "success": true,
  "message": "Enclave 'eth-devnet' 启动成功",
  "output": "..."
}
```

### POST /stop
停止 Kurtosis 网络

响应示例：
```json
{
  "success": true,
  "message": "Enclave 'eth-devnet' 已停止并移除"
}
```

## 环境变量

- `KURTOSIS_CONFIG_FILE`: Kurtosis 配置文件路径（默认：`/kurtosis-config/kurtosis-config.yaml`）
- `KURTOSIS_ENCLAVE`: Enclave 名称（默认：`eth-devnet`）

## 注意事项

1. **Docker Socket 权限**：容器需要访问 Docker socket 的权限
2. **配置文件路径**：确保配置文件路径正确挂载
3. **超时设置**：Kurtosis 启动可能需要较长时间（几分钟），API 超时设置为 10 分钟
4. **网络隔离**：Kurtosis 创建的容器可以正常访问其他 Docker Compose 服务

