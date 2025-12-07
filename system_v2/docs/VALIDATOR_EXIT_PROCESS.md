# 验证者退出流程文档

## 概述

本文档描述了验证者自愿退出（Voluntary Exit）的完整流程，包括退出条件检查、退出签名生成、提交到 Beacon Chain，以及退出后的密钥清理。

## 退出条件

根据 Ethereum 规范，验证者必须满足以下条件才能退出：

1. **验证者必须已激活**：`activation_epoch` 不能是 `FAR_FUTURE_EPOCH`
2. **验证者必须激活至少 256 epochs**：`current_epoch >= activation_epoch + 256`
3. **验证者尚未退出**：`exit_epoch` 必须是 `FAR_FUTURE_EPOCH`（即未设置）

### 退出条件计算公式

```
earliest_exit_epoch = activation_epoch + 256
can_exit = (current_epoch >= earliest_exit_epoch) && (exit_epoch == FAR_FUTURE_EPOCH)
```

### 示例

- **激活 epoch**: 11
- **最早退出 epoch**: 11 + 256 = 267
- **当前 epoch**: 60
- **结果**: 不能退出，需要等待 207 个 epochs (267 - 60 = 207)

## API 端点

### 1. 检查退出资格

**端点**: `GET /api/v1/exits/check-eligibility`

**参数**:
- `pubkey` (query, required): 验证者公钥

**响应示例**:
```json
{
  "can_exit": false,
  "reason": "验证者太年轻，还不能退出。当前 epoch: 60, 最早退出 epoch: 267 (激活于 epoch 11 + 256 epochs 等待期), 还需要等待约 207 个 epochs 才能退出。根据 Ethereum 规范，验证者必须激活至少 256 epochs 后才能退出。",
  "current_epoch": 60,
  "activation_epoch": 11,
  "earliest_exit_epoch": 267,
  "exit_epoch": null
}
```

**使用场景**: 在提交退出前检查验证者是否满足退出条件。

### 2. 生成退出签名

**端点**: `POST /api/v1/exits/generate`

**参数**:
- `pubkey` (query, required): 验证者公钥
- `epoch` (query, optional): 退出 epoch（如果不提供，将自动使用 `earliest_exit_epoch` 或当前 epoch）

**响应示例**:
```json
{
  "message": {
    "epoch": "267",
    "validator_index": "129"
  },
  "signature": "0x1234..."
}
```

**使用场景**: 生成退出签名，但不提交到 Beacon Chain。

### 3. 提交退出

**端点**: `POST /api/v1/exits/submit`

**参数**:
- `pubkey` (query, required): 验证者公钥
- `epoch` (query, optional): 退出 epoch（如果不提供，将自动使用 `earliest_exit_epoch` 或当前 epoch）

**响应示例**:
```json
{
  "pubkey": "0xa13e0be3...",
  "status": "submitted",
  "exit_data": {
    "message": {
      "epoch": "267",
      "validator_index": "129"
    },
    "signature": "0x1234..."
  },
  "eligibility": {
    "can_exit": true,
    "reason": "验证者满足退出条件 (当前 epoch: 267, 最早退出 epoch: 267)",
    "current_epoch": 267,
    "activation_epoch": 11,
    "earliest_exit_epoch": 267,
    "exit_epoch": null
  }
}
```

**使用场景**: 生成退出签名并提交到 Beacon Chain。这是最常用的端点。

**流程**:
1. 检查退出资格
2. 如果满足条件，生成退出签名
3. 提交到 Beacon Chain API (`/eth/v1/beacon/pool/voluntary_exits`)
4. 更新数据库状态为 `pending_exit`

### 4. 批量退出

**端点**: `POST /api/v1/exits/batch`

**参数**:
- `pubkeys` (body, required): 验证者公钥列表
- `epoch` (body, optional): 退出 epoch

**响应示例**:
```json
{
  "total": 2,
  "results": [
    {
      "pubkey": "0xa13e0be3...",
      "status": "success",
      "exit_data": {...}
    },
    {
      "pubkey": "0xab1a95e7...",
      "status": "failed",
      "error": "验证者不满足退出条件: ..."
    }
  ]
}
```

**使用场景**: 批量退出多个验证者。

### 5. 完成退出流程

**端点**: `POST /api/v1/exits/{pubkey}/complete`

**参数**:
- `pubkey` (path, required): 验证者公钥

**响应示例**:
```json
{
  "pubkey": "0xa13e0be3...",
  "status": "exited",
  "removed": {
    "web3signer_removed": true,
    "client_mappings_removed": 1,
    "configs_updated": ["vc-1"]
  }
}
```

**使用场景**: 确认验证者已退出后，清理系统中的密钥和相关配置。

**流程**:
1. 更新数据库状态为 `exited`
2. 从 Web3Signer 删除密钥
3. 从客户端映射表移除密钥
4. 更新客户端配置文件

### 6. 移除已退出的密钥

**端点**: `DELETE /api/v1/exits/{pubkey}/remove-key`

**参数**:
- `pubkey` (path, required): 验证者公钥

**响应示例**:
```json
{
  "pubkey": "0xa13e0be3...",
  "web3signer_removed": true,
  "client_mappings_removed": 1,
  "configs_updated": ["vc-1"]
}
```

**使用场景**: 从系统中移除已退出的密钥，但不更新数据库状态。

## 退出流程详解

### 阶段 1: 退出资格检查

系统会检查以下条件：

1. **验证者是否存在**: 从数据库查询验证者记录
2. **验证者状态**: 检查是否已退出（`status == EXITED`）
3. **获取验证者信息**: 从 Beacon Chain API 查询验证者的 `activation_epoch` 和 `exit_epoch`
4. **计算最早退出 epoch**: `earliest_exit_epoch = activation_epoch + 256`
5. **比较当前 epoch**: `current_epoch >= earliest_exit_epoch`

如果任何条件不满足，将返回详细的错误信息。

### 阶段 2: 退出签名生成

1. **获取验证者索引**: 从数据库或 Beacon Chain 查询 `validator_index`
2. **读取签名私钥**: 从 Vault 读取验证者的签名私钥
3. **确定退出 epoch**: 
   - 如果提供了 `epoch` 参数，使用该值
   - 否则使用 `earliest_exit_epoch` 或当前 epoch
4. **生成签名**: 使用 `ethstaker-deposit-cli` 生成退出签名

### 阶段 3: 提交到 Beacon Chain

1. **提交退出请求**: 发送 POST 请求到 Beacon Chain API (`/eth/v1/beacon/pool/voluntary_exits`)
2. **更新数据库状态**: 如果提交成功，将验证者状态更新为 `pending_exit`
3. **返回结果**: 返回提交结果和退出数据

### 阶段 4: 退出确认和清理

1. **确认退出**: 等待 Beacon Chain 确认验证者已退出
2. **完成退出流程**: 调用 `complete_exit_process` 或 `remove_key_from_system`
3. **清理密钥**: 
   - 从 Web3Signer 删除密钥
   - 从客户端映射表移除密钥
   - 更新客户端配置文件

## 错误处理

### 常见错误

1. **验证者不满足退出条件**
   ```
   错误: 验证者不满足退出条件: 验证者太年轻，还不能退出 (当前 epoch: 60, 最早退出 epoch: 267)
   解决: 等待直到当前 epoch >= earliest_exit_epoch
   ```

2. **验证者已退出或正在退出**
   ```
   错误: 验证者已退出或正在退出 (exit_epoch: 123)
   解决: 验证者已经退出，无需再次提交
   ```

3. **验证者尚未激活**
   ```
   错误: 验证者尚未激活
   解决: 等待验证者激活后再尝试退出
   ```

4. **无法获取验证者信息**
   ```
   错误: 无法获取验证者信息: 0xa13e0be3...
   解决: 检查 Beacon API 连接和验证者公钥是否正确
   ```

5. **Beacon API 返回错误**
   ```
   错误: Beacon API 返回错误: 400, {"code":400,"message":"BAD_REQUEST: Invalid object: gossip verification failed: ExitValidationError(Invalid(TooYoungToExit { current_epoch: Epoch(32), earliest_exit_epoch: Epoch(267) }))"}
   解决: 验证者不满足退出条件，系统会在提交前检查，但 Beacon Chain 也会再次验证
   ```

## 技术实现细节

### 退出签名生成

使用 `ethstaker-deposit-cli` 库生成退出签名：

```python
from ethstaker_deposit.utils.exit_transaction import exit_transaction_generation

signed_exit = exit_transaction_generation(
    chain_setting=self.chain_setting,
    signing_key=signing_private_key_int,
    validator_index=validator_index,
    epoch=epoch
)
```

### FAR_FUTURE_EPOCH 处理

`FAR_FUTURE_EPOCH = 18446744073709551615` 表示 epoch 未设置。系统会正确处理这个值：

- 如果 `activation_epoch == FAR_FUTURE_EPOCH`，表示验证者尚未激活
- 如果 `exit_epoch == FAR_FUTURE_EPOCH`，表示验证者尚未退出

### Epoch 查询

系统会从 Beacon Chain API 查询当前 epoch：

```python
state_data = beacon_api._get("/eth/v1/beacon/states/finalized/finality_checkpoints")
current_epoch = int(state_data['data']['finalized']['epoch'])
```

## 使用示例

### 示例 1: 检查退出资格

```bash
curl -X GET "http://localhost:8000/api/v1/exits/check-eligibility?pubkey=0xa13e0be3431422b3ef2718e695e0fa3e47e81cbfc8096bc73df1fc92dd2c1da1f41ed646a1abe6f794f3d22a9dd28c41"
```

### 示例 2: 提交退出

```bash
curl -X POST "http://localhost:8000/api/v1/exits/submit?pubkey=0xa13e0be3431422b3ef2718e695e0fa3e47e81cbfc8096bc73df1fc92dd2c1da1f41ed646a1abe6f794f3d22a9dd28c41"
```

### 示例 3: 批量退出

```bash
curl -X POST "http://localhost:8000/api/v1/exits/batch" \
  -H "Content-Type: application/json" \
  -d '{
    "pubkeys": [
      "0xa13e0be3431422b3ef2718e695e0fa3e47e81cbfc8096bc73df1fc92dd2c1da1f41ed646a1abe6f794f3d22a9dd28c41",
      "0xab1a95e7871317cd25985c0f3aa46062c4ae43cb172f48e8c6b65afa459565ea6439753a2b462673eec6f881d5ee0fbc"
    ]
  }'
```

### 示例 4: 完成退出流程

```bash
curl -X POST "http://localhost:8000/api/v1/exits/0xa13e0be3431422b3ef2718e695e0fa3e47e81cbfc8096bc73df1fc92dd2c1da1f41ed646a1abe6f794f3d22a9dd28c41/complete"
```

## 参考文档

- [Prysm 验证者退出文档](https://prysm.offchainlabs.com/docs/manage-validator/exiting-a-validator/)
- [Ethereum Beacon Chain 规范 - Voluntary Exit](https://github.com/ethereum/consensus-specs/blob/dev/specs/phase0/beacon-chain.md#voluntary-exits)
- [Ethereum Key Manager APIs](https://ethereum.github.io/keymanager-APIs/)

## 注意事项

1. **退出是不可逆的**: 一旦提交退出，验证者将永久退出验证网络
2. **退出不会自动提取资金**: 验证者必须单独处理资金提取（withdrawal）
3. **退出需要等待**: 验证者必须激活至少 256 epochs 后才能退出
4. **退出签名需要私钥**: 系统会从 Vault 读取签名私钥来生成退出签名
5. **退出提交是异步的**: 提交退出后，需要等待 Beacon Chain 确认

## 状态转换

验证者退出过程中的状态转换：

```
ACTIVE_ON_CHAIN → PENDING_EXIT → EXITED
```

- **ACTIVE_ON_CHAIN**: 验证者正在验证
- **PENDING_EXIT**: 已提交退出请求，等待 Beacon Chain 处理
- **EXITED**: 验证者已退出验证网络

## 故障排查

### 问题 1: 退出提交失败，提示 "TooYoungToExit"

**原因**: 验证者不满足退出条件（当前 epoch < earliest_exit_epoch）

**解决**: 
1. 使用 `GET /api/v1/exits/check-eligibility` 检查退出资格
2. 等待直到当前 epoch >= earliest_exit_epoch
3. 再次尝试提交退出

### 问题 2: 无法获取验证者信息

**原因**: Beacon API 连接问题或验证者公钥错误

**解决**:
1. 检查 Beacon API 连接
2. 验证公钥格式是否正确（带 0x 前缀）
3. 检查验证者是否在 Beacon Chain 上存在

### 问题 3: 退出签名生成失败

**原因**: 无法从 Vault 读取签名私钥

**解决**:
1. 检查 Vault 连接
2. 验证密钥是否在 Vault 中存在
3. 检查 Vault 权限配置

## 相关文件

- `system_v2/backend/app/services/exit_service.py`: 退出服务实现
- `system_v2/backend/app/api/v1/exits.py`: 退出 API 端点
- `system_v2/backend/app/core/exit_generator.py`: 退出签名生成器
- `system_v2/backend/app/core/beacon_api.py`: Beacon API 客户端

