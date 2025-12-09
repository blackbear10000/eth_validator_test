# Kurtosis Enclave 故障排查指南

## 常见问题

### 问题 1: CLI 和 Engine 版本不匹配

**错误信息**：
```
ERRO[xxx] The engine server API version that the CLI expects, '1.11', doesn't match 
the running engine server API version, '1.13'
```

**原因**：Kurtosis CLI 版本与 Engine 版本不匹配

**解决方案**：

#### 方案 A: 重启 Engine（推荐，如果 CLI 版本较新）

```bash
# 重启 Engine 以匹配 CLI 版本
kurtosis engine restart

# 验证版本匹配
kurtosis version
kurtosis engine status
```

#### 方案 B: 更新 CLI 版本（如果 Engine 版本较新）

```bash
# 检查当前 CLI 版本
kurtosis version

# 更新 Kurtosis CLI（根据你的安装方式）
# macOS (Homebrew)
brew upgrade kurtosis-tech/kurtosis/kurtosis-cli

# Linux (APT)
sudo apt-get update && sudo apt-get install kurtosis-cli

# 或者重新安装最新版本
curl -fsSL https://docs.kurtosis.com/install.sh | bash
```

#### 方案 C: 使用 Docker 容器内的 CLI（推荐，适用于 Docker 环境）

如果宿主机版本不匹配，直接使用 kurtosis-manager 容器内的 CLI：

```bash
# 通过容器执行命令（容器内的版本是匹配的）
docker exec kurtosis-manager kurtosis enclave ls
docker exec kurtosis-manager kurtosis enclave inspect eth-devnet
```

### 问题 2: Enclave 异常状态

当 Kurtosis enclave 处于异常状态（如非正常关闭）时，可能会出现以下情况：
- `kurtosis enclave ls` 能查到 enclave
- `kurtosis enclave inspect` 无法获取详细信息或返回不完整信息
- 系统误判为网络正在运行中

## 快速修复版本不匹配

如果遇到版本不匹配错误，可以使用修复脚本：

```bash
cd system_v2
./scripts/fix_kurtosis_version.sh
```

或者手动修复：

```bash
# 方案 1: 重启 Engine（推荐）
kurtosis engine restart

# 方案 2: 使用 Docker 容器内的 CLI（如果宿主机版本不匹配）
docker exec kurtosis-manager kurtosis enclave ls
```

## 诊断步骤

### 1. 运行诊断脚本

#### 方式 A: 在主机上运行（如果主机安装了 Kurtosis CLI）

```bash
cd system_v2
./scripts/diagnose_kurtosis.sh eth-devnet
```

#### 方式 B: 通过 Docker 容器运行（推荐，适用于 Docker 环境）

```bash
# 确保 kurtosis-manager 容器正在运行
docker ps | grep kurtosis-manager

# 通过容器执行诊断脚本
docker exec kurtosis-manager bash -c "
  cd /app && \
  kurtosis --version && \
  kurtosis enclave ls && \
  kurtosis enclave inspect eth-devnet
"
```

或者将脚本复制到容器中执行：

```bash
# 复制脚本到容器
docker cp system_v2/scripts/diagnose_kurtosis.sh kurtosis-manager:/tmp/

# 在容器内执行
docker exec kurtosis-manager bash /tmp/diagnose_kurtosis.sh eth-devnet
```

这个脚本会：
- 检查 Kurtosis CLI 和 Engine 状态
- 列出所有 enclave
- 检查目标 enclave 的详细信息
- 分析状态字段和服务数量
- 检查相关 Docker 容器
- 提供清理建议

### 2. 手动检查命令

#### 在主机上执行（如果安装了 Kurtosis CLI）

```bash
# 1. 检查 enclave 列表
kurtosis enclave ls

# 2. 查看 enclave 详细信息
kurtosis enclave inspect eth-devnet

# 3. 检查状态字段（重点）
kurtosis enclave inspect eth-devnet | grep -i "Status:"

# 4. 检查是否有服务运行
kurtosis enclave inspect eth-devnet | grep -A 20 "User Services"
```

#### 通过 Docker 容器执行（推荐）

```bash
# 1. 检查 enclave 列表
docker exec kurtosis-manager kurtosis enclave ls

# 2. 查看 enclave 详细信息
docker exec kurtosis-manager kurtosis enclave inspect eth-devnet

# 3. 检查状态字段（重点）
docker exec kurtosis-manager kurtosis enclave inspect eth-devnet | grep -i "Status:"

# 4. 检查是否有服务运行
docker exec kurtosis-manager kurtosis enclave inspect eth-devnet | grep -A 20 "User Services"
```

## 清理步骤

### 方法 1: 使用清理脚本（推荐）

#### 在主机上运行（如果主机安装了 Kurtosis CLI）

```bash
cd system_v2
./scripts/cleanup_kurtosis_enclave.sh eth-devnet
```

#### 通过 Docker 容器运行（推荐，适用于 Docker 环境）

```bash
# 方式 A: 直接在容器内执行命令
docker exec kurtosis-manager kurtosis enclave stop eth-devnet
docker exec kurtosis-manager kurtosis enclave rm eth-devnet

# 方式 B: 复制脚本到容器并执行
docker cp system_v2/scripts/cleanup_kurtosis_enclave.sh kurtosis-manager:/tmp/
docker exec kurtosis-manager bash /tmp/cleanup_kurtosis_enclave.sh eth-devnet
```

### 方法 2: 手动清理

#### 在主机上执行（如果安装了 Kurtosis CLI）

```bash
# 1. 停止 enclave
kurtosis enclave stop eth-devnet

# 2. 移除 enclave
kurtosis enclave rm eth-devnet

# 3. 如果移除失败，尝试强制移除
kurtosis enclave rm eth-devnet --force

# 4. 验证移除结果
kurtosis enclave ls
```

#### 通过 Docker 容器执行（推荐）

```bash
# 1. 停止 enclave
docker exec kurtosis-manager kurtosis enclave stop eth-devnet

# 2. 移除 enclave
docker exec kurtosis-manager kurtosis enclave rm eth-devnet

# 3. 如果移除失败，尝试强制移除
docker exec kurtosis-manager kurtosis enclave rm eth-devnet --force

# 4. 验证移除结果
docker exec kurtosis-manager kurtosis enclave ls
```

### 方法 3: 清理 Docker 容器（如果上述方法失败）

```bash
# 查找相关容器（Kurtosis 创建的容器）
docker ps -a | grep kurtosis | grep eth-devnet

# 停止并删除相关容器（谨慎操作）
# 注意：这些是 Kurtosis 创建的容器，不是 kurtosis-manager 容器本身
docker stop $(docker ps -a --filter "name=kurtosis" --format "{{.Names}}" | grep eth-devnet)
docker rm $(docker ps -a --filter "name=kurtosis" --format "{{.Names}}" | grep eth-devnet)

# 如果 enclave 仍然存在，可以尝试重启 kurtosis-manager 容器
docker restart kurtosis-manager
```

## 常见状态说明

- **RUNNING**: 正常运行，有服务在运行
- **EMPTY**: Enclave 存在但没有服务运行（应该显示为"已停止"）
- **STOPPED**: 已停止
- **无状态字段**: 可能是异常状态，需要清理

## 验证清理结果

清理完成后，运行以下命令验证：

#### 在主机上验证（如果安装了 Kurtosis CLI）

```bash
# 1. 确认 enclave 不在列表中
kurtosis enclave ls | grep -v eth-devnet
```

#### 通过 Docker 容器验证（推荐）

```bash
# 1. 确认 enclave 不在列表中
docker exec kurtosis-manager kurtosis enclave ls | grep -v eth-devnet
```

#### 通过 API 验证

```bash
# 2. 检查系统状态（通过 API）
curl http://localhost:8001/api/v1/network/status

# 应该返回：
# {
#   "enclave_name": "eth-devnet",
#   "status": "stopped",
#   "is_running": false
# }
```

#### 通过前端验证

```bash
# 3. 或者在前端刷新网络管理页面
# 访问 http://localhost:3000
# 网络管理页面应该显示"已停止"状态
```

## Docker 环境特殊说明

### kurtosis-manager 容器配置

- **网络模式**: `host` - 使用主机网络，可以直接访问主机的 Docker daemon
- **Docker Socket**: 挂载 `/var/run/docker.sock`，允许容器内的 Kurtosis CLI 管理主机上的 Docker
- **创建的容器**: Kurtosis 创建的容器（Geth、Prysm 等）运行在**主机上**，不是嵌套容器

### 为什么推荐通过容器执行命令？

1. **一致性**: kurtosis-manager 容器内已经安装了 Kurtosis CLI，版本和配置都是正确的
2. **权限**: 容器已经配置好访问 Docker socket 的权限
3. **环境**: 容器内的环境变量和配置都是正确的

### 如果容器无法访问 Docker socket

如果遇到权限问题，可以检查：

```bash
# 检查容器是否有权限访问 Docker socket
docker exec kurtosis-manager ls -la /var/run/docker.sock

# 检查容器内的用户
docker exec kurtosis-manager whoami

# 如果权限不足，可能需要调整 docker-compose.yml 中的配置
```

## 预防措施

1. **正常关闭**: 始终使用 `kurtosis enclave stop` 和 `kurtosis enclave rm` 正常关闭
2. **定期检查**: 定期运行诊断脚本检查 enclave 状态
3. **监控日志**: 关注系统日志中的状态判断信息

## 相关文件

- 清理脚本: `system_v2/scripts/cleanup_kurtosis_enclave.sh`
- 诊断脚本: `system_v2/scripts/diagnose_kurtosis.sh`
- Kurtosis 服务代码: `system_v2/infra/kurtosis-manager/kurtosis_service.py`

