# Kurtosis Enclave 故障排查指南

## 问题描述

当 Kurtosis enclave 处于异常状态（如非正常关闭）时，可能会出现以下情况：
- `kurtosis enclave ls` 能查到 enclave
- `kurtosis enclave inspect` 无法获取详细信息或返回不完整信息
- 系统误判为网络正在运行中

## 诊断步骤

### 1. 运行诊断脚本

```bash
cd system_v2
./scripts/diagnose_kurtosis.sh eth-devnet
```

这个脚本会：
- 检查 Kurtosis CLI 和 Engine 状态
- 列出所有 enclave
- 检查目标 enclave 的详细信息
- 分析状态字段和服务数量
- 检查相关 Docker 容器
- 提供清理建议

### 2. 手动检查命令

如果脚本无法运行，可以手动执行以下命令：

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

## 清理步骤

### 方法 1: 使用清理脚本（推荐）

```bash
cd system_v2
./scripts/cleanup_kurtosis_enclave.sh eth-devnet
```

### 方法 2: 手动清理

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

### 方法 3: 清理 Docker 容器（如果上述方法失败）

```bash
# 查找相关容器
docker ps -a | grep kurtosis | grep eth-devnet

# 停止并删除相关容器（谨慎操作）
docker stop $(docker ps -a | grep kurtosis | grep eth-devnet | awk '{print $1}')
docker rm $(docker ps -a | grep kurtosis | grep eth-devnet | awk '{print $1}')
```

## 常见状态说明

- **RUNNING**: 正常运行，有服务在运行
- **EMPTY**: Enclave 存在但没有服务运行（应该显示为"已停止"）
- **STOPPED**: 已停止
- **无状态字段**: 可能是异常状态，需要清理

## 验证清理结果

清理完成后，运行以下命令验证：

```bash
# 1. 确认 enclave 不在列表中
kurtosis enclave ls | grep -v eth-devnet

# 2. 检查系统状态（通过 API）
curl http://localhost:8000/api/v1/network/status

# 3. 或者在前端刷新网络管理页面
```

## 预防措施

1. **正常关闭**: 始终使用 `kurtosis enclave stop` 和 `kurtosis enclave rm` 正常关闭
2. **定期检查**: 定期运行诊断脚本检查 enclave 状态
3. **监控日志**: 关注系统日志中的状态判断信息

## 相关文件

- 清理脚本: `system_v2/scripts/cleanup_kurtosis_enclave.sh`
- 诊断脚本: `system_v2/scripts/diagnose_kurtosis.sh`
- Kurtosis 服务代码: `system_v2/infra/kurtosis-manager/kurtosis_service.py`

