# Beacon API Pubkey 格式说明

## 问题描述

在调用 Beacon API 查询验证者信息时，pubkey 的格式要求必须正确，否则会导致请求失败。

## Pubkey 格式要求

### URL 路径中的 Pubkey

在 Beacon API 的 URL 路径中，pubkey **必须包含 `0x` 前缀**：

```
GET /eth/v1/beacon/states/head/validators/{pubkey}
```

**正确格式**：
```
/eth/v1/beacon/states/head/validators/0x805ceabc2ef1413f9f60ed6c464fce64e6069cb32b4c37f8936646750a4191e334dc2dea837b415600e8aeeae95a066a
```

**错误格式**（缺少 0x 前缀）：
```
/eth/v1/beacon/states/head/validators/805ceabc2ef1413f9f60ed6c464fce64e6069cb32b4c37f8936646750a4191e334dc2dea837b415600e8aeeae95a066a
```

### 查询参数中的 Pubkey

在批量查询时，pubkey 作为查询参数传递，格式要求可能因实现而异：

```
GET /eth/v1/beacon/states/head/validators?id={pubkey1}&id={pubkey2}
```

某些 Beacon API 实现可能要求查询参数中的 pubkey **不带 `0x` 前缀**，但标准实现应该支持两种格式。

## 代码实现

### 修复前的问题

```python
def get_validator(self, pubkey: str, state_id: str = "head"):
    # ❌ 错误：移除了 0x 前缀
    pubkey_clean = pubkey.lower().replace('0x', '')
    response = self._get(f"/eth/v1/beacon/states/{state_id}/validators/{pubkey_clean}")
```

### 修复后的实现

```python
def get_validator(self, pubkey: str, state_id: str = "head"):
    # ✅ 正确：确保有 0x 前缀
    pubkey_normalized = pubkey.lower().strip()
    if not pubkey_normalized.startswith('0x'):
        pubkey_normalized = f"0x{pubkey_normalized}"
    response = self._get(f"/eth/v1/beacon/states/{state_id}/validators/{pubkey_normalized}")
```

## 影响范围

以下功能都会受到影响：

1. **存款状态同步** (`DepositManagementService.sync_transaction_status`)
   - 调用 `BeaconAPIClient.get_validator()` 验证验证者状态

2. **验证者状态同步** (`SyncService.sync_validator_status`)
   - 批量查询验证者状态

3. **存款验证** (`DepositValidationService.validate_deposit_transaction`)
   - 验证存款交易后查询验证者状态

4. **监控服务** (`MonitoringService.get_validator_performance`)
   - 获取验证者性能数据

5. **提款服务** (`WithdrawalService.get_validator_withdrawals`)
   - 查询验证者提款信息

## 测试建议

### 单元测试

```python
def test_get_validator_with_0x_prefix():
    """测试带 0x 前缀的 pubkey"""
    client = BeaconAPIClient()
    pubkey = "0x805ceabc2ef1413f9f60ed6c464fce64e6069cb32b4c37f8936646750a4191e334dc2dea837b415600e8aeeae95a066a"
    result = client.get_validator(pubkey)
    assert result is not None

def test_get_validator_without_0x_prefix():
    """测试不带 0x 前缀的 pubkey（应该自动添加）"""
    client = BeaconAPIClient()
    pubkey = "805ceabc2ef1413f9f60ed6c464fce64e6069cb32b4c37f8936646750a4191e334dc2dea837b415600e8aeeae95a066a"
    result = client.get_validator(pubkey)
    assert result is not None
```

### 手动验证

```bash
# 测试带 0x 前缀的请求（应该成功）
curl "http://localhost:33785/eth/v1/beacon/states/head/validators/0x805ceabc2ef1413f9f60ed6c464fce64e6069cb32b4c37f8936646750a4191e334dc2dea837b415600e8aeeae95a066a"

# 测试不带 0x 前缀的请求（可能失败）
curl "http://localhost:33785/eth/v1/beacon/states/head/validators/805ceabc2ef1413f9f60ed6c464fce64e6069cb32b4c37f8936646750a4191e334dc2dea837b415600e8aeeae95a066a"
```

## 相关代码位置

- `app/core/beacon_api.py` - Beacon API 客户端实现
  - `get_validator()` - 单个验证者查询
  - `get_validators()` - 批量验证者查询

## 相关文档

- [Beacon API 连接问题分析](./BEACON_API_CONNECTION_ISSUE.md)
- [端点发现流程](./ENDPOINT_DISCOVERY_FLOW.md)

