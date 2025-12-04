# Beacon API 解析问题修复

## 问题分析

### 问题描述

后端日志显示：
```
成功提取端点: RPC=http://host.docker.internal:33780, WS=ws://host.docker.internal:33781, Beacon API=None, 执行层服务=None, 共识层服务=None
```

说明 `NetworkService` 没有成功解析出 Beacon API URL，导致回退到默认的 `http://localhost:5052`。

### 根本原因

从 `enclave_output.txt` 可以看到，Kurtosis 的输出格式是：

```
4692a1818c6f   cl-1-prysm-geth                                  http: 3500/tcp -> http://127.0.0.1:33785      RUNNING
```

**关键问题**：服务名和端口信息在同一行！

但是原来的代码逻辑是：
1. 检测到 `cl-1-prysm-geth` 后，设置 `in_cl_service = True`
2. 然后 `continue`，**跳过了同一行的端口信息**
3. 下一行是空行或下一个服务，所以端口信息被完全跳过了

### 代码问题

```python
# 原来的错误代码
if re.search(r'cl-\d+-\w+', line):
    in_cl_service = True
    # ...
    continue  # ❌ 这里跳过了同一行的端口信息！
```

## 修复方案

### 1. 移除 continue 语句

让代码在检测到服务名后，继续检查同一行的端口信息：

```python
# 修复后的代码
cl_match = re.search(r'cl-\d+-\w+', line)
if cl_match:
    in_cl_service = True
    in_el_service = False
    beacon_service = cl_match.group(0)
    logger.debug(f"找到共识层服务: {beacon_service}, 行 {i+1}: {line[:100]}")
    # ✅ 不 continue，继续检查同一行是否有端口信息
```

### 2. 改进状态重置逻辑

原来的状态重置逻辑可能过于严格，导致在某些情况下提前重置状态。改进为：

```python
# 修复后的状态重置逻辑
if (in_el_service or in_cl_service):
    uuid_match = re.match(r'^[a-f0-9]{12}\s+', line)
    if uuid_match:
        # 只有当新行不包含当前服务标识时才重置
        if in_el_service and not re.search(r'el-\d+-', line):
            in_el_service = False
            current_service = None
        if in_cl_service and not re.search(r'cl-\d+-', line):
            in_cl_service = False
            beacon_service = None
```

## 修复后的工作流程

1. **检测服务名**：
   - 检测到 `cl-1-prysm-geth` 或 `el-1-geth-prysm`
   - 设置 `in_cl_service = True` 或 `in_el_service = True`
   - **不 continue，继续处理同一行**

2. **检查端口信息**：
   - 如果 `in_cl_service = True`，检查同一行是否有 `http: 3500/tcp` 或 `http: 4000/tcp`
   - 如果 `in_el_service = True`，检查同一行是否有 `rpc: 8545/tcp` 或 `ws: 8546/tcp`

3. **状态重置**：
   - 遇到新的 UUID 行时，检查是否包含当前服务标识
   - 如果不包含，说明是新服务，重置状态

## 验证

修复后，日志应该显示：

```
找到共识层服务: cl-1-prysm-geth, 行 27: 4692a1818c6f   cl-1-prysm-geth...
找到 Beacon API 端口映射: 127.0.0.1:33785 -> http://host.docker.internal:33785
成功提取端点: RPC=http://host.docker.internal:33780, WS=ws://host.docker.internal:33781, Beacon API=http://host.docker.internal:33785, 执行层服务=el-2-reth-lighthouse, 共识层服务=cl-1-prysm-geth
```

## 相关文件

- `system_v2/backend/app/services/network_service.py` - 修复了服务名和端口信息的解析逻辑

