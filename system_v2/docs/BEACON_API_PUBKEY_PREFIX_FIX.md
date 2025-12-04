# Beacon API Pubkey 前缀修复

## 问题描述

后端日志显示 Beacon API 请求失败，错误为 400 Bad Request：

```
Beacon API 请求失败: http://host.docker.internal:33790/eth/v1/beacon/states/head/validators?id=8901f16b5ba803748b640eb6c873cf2482e73bf55162adbda9a22b663fba3330b8e2c5e2eb12fcfdddcd4c180b57c6e7
```

**问题**：查询参数中的 pubkey 缺少 `0x` 前缀。

## 根本原因

在 `BeaconAPIClient.get_validators()` 方法中，代码错误地移除了 pubkey 的 0x 前缀：

```python
# 错误的代码
pubkey_clean = pubkey_normalized.replace('0x', '')
pubkey_params.append(pubkey_clean)  # ❌ 没有 0x 前缀
```

根据 Beacon API 标准（Ethereum Beacon API Specification），查询参数中的 pubkey **必须**带 `0x` 前缀。

## 修复方案

修改 `get_validators()` 方法，确保查询参数中的 pubkey 带 0x 前缀：

```python
# 修复后的代码
pubkey_normalized = pubkey.lower().strip()
# 确保有 0x 前缀（Beacon API 标准要求）
if not pubkey_normalized.startswith('0x'):
    pubkey_normalized = f"0x{pubkey_normalized}"
pubkey_params.append(pubkey_normalized)  # ✅ 带 0x 前缀
```

## 修复后的行为

修复后，查询参数格式为：
```
?id=0x8901f16b5ba803748b640eb6c873cf2482e73bf55162adbda9a22b663fba3330b8e2c5e2eb12fcfdddcd4c180b57c6e7
```

符合 Beacon API 标准要求。

## 其他相关检查

### 已正确处理的场景

1. **`get_validator()` 方法**：
   - URL 路径中的 pubkey 已正确添加 0x 前缀 ✅
   - 代码：`f"/eth/v1/beacon/states/{state_id}/validators/{pubkey_normalized}"`

2. **`sync_service.py`**：
   - 调用 `get_validator()` 和 `get_validators()` 前已规范化 pubkey ✅
   - 支持数据库中的两种格式（带/不带 0x 前缀）

3. **`deposit_validation.py`**：
   - 通过 `check_validator_status()` 调用 `get_validator()` ✅
   - `get_validator()` 会自动处理 0x 前缀

4. **`remote_validator_client.py`**：
   - 所有 pubkey 都已规范化（添加 0x 前缀）✅

### 注意事项

1. **数据库中的 pubkey 格式**：
   - 数据库可能存储为带或不带 0x 前缀的格式
   - 查询时使用两种格式匹配：`(ValidatorKey.pubkey == pubkey_normalized) | (ValidatorKey.pubkey == pubkey.lower())`

2. **Beacon API 标准**：
   - URL 路径中的 pubkey：**必须**带 0x 前缀
   - 查询参数中的 pubkey：**必须**带 0x 前缀
   - 返回的 pubkey：通常带 0x 前缀

3. **不同 Beacon Client 实现**：
   - Prysm、Lighthouse、Teku 都遵循 Beacon API 标准
   - 所有实现都要求 pubkey 带 0x 前缀

## 相关文件

- `system_v2/backend/app/core/beacon_api.py` - 修复了 `get_validators()` 方法中的 pubkey 前缀问题

## 验证

修复后，Beacon API 请求应该成功：

```
Beacon API 请求成功: http://host.docker.internal:33790/eth/v1/beacon/states/head/validators?id=0x8901f16b5ba803748b640eb6c873cf2482e73bf55162adbda9a22b663fba3330b8e2c5e2eb12fcfdddcd4c180b57c6e7&id=0x94e4fcd64ca1be4dd9274beca0b3ffeebb9ef12a89720805f2413ac3b1341c34df23c37e3d27a7b0a9bdde6fe340a704
```

