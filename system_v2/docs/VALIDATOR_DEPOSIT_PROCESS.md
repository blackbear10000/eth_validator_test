# Validator Deposit Process and Timeline

本文档详细说明基于当前网络配置（`infra/kurtosis/network-config.yaml`），从提交 deposit data 到验证器节点激活的完整流程和时间线。

## 参考文档

本文档基于 [Beaconcha.in Deposit Process Guide](https://docs.beaconcha.in/faqs/deposit-process) 编写。

## 网络配置参数

当前测试网的关键时间参数：

- **每个 Slot = 4 秒**（主网为 12 秒）
- **每个 Epoch = 32 slots**（以太坊标准）= 32 × 4 = **128 秒 ≈ 2.13 分钟**
- **ETH1 区块时间 = 12 秒**
- **ETH1_FOLLOW_DISTANCE = 16 个区块**

## 完整流程和时间线

### 1. Unknown（交易在内存池中）

**状态描述：**
- Deposit 交易已提交，但仍在内存池（Mempool）中等待打包
- 验证器在 Beaconcha.in 上显示为 "Unknown" 状态

**时间：**
- **不确定**，取决于以下因素：
  - 网络拥堵程度
  - Gas 价格（Base Fee + Priority Fee）
  - 区块构建者的优先级设置

**说明：**
- 内存池是交易的"等待室"
- 交易需要支付 Base Fee（算法设定，会被销毁）和可选的 Priority Fee（给区块构建者）
- 区块构建者通常优先处理 Priority Fee 最高的交易
- 当网络拥堵时，Base Fee 会动态上升
- Base Fee 或 Priority Fee 较低的交易可能面临不可预测的延迟
- **可以通过提高网络费用来加速交易**

### 2. Deposited（存款已确认，等待处理）

**状态描述：**
- Deposit 交易已被包含在区块中
- Beaconcha.in 显示验证器状态为 "Deposited"
- 等待 deposit queue 完全处理该存款

**时间：**
- 至少需要等待 **ETH1_FOLLOW_DISTANCE = 16 个区块**
- 16 个区块 × 12 秒 = **192 秒 ≈ 3.2 分钟**

**重要说明：**
- 验证器必须至少有 32 ETH 的有效余额（effective balance）才能有资格激活
- **注意：余额（balance）和有效余额（effective balance）可能不同**
  - 有效余额只有在余额比当前有效余额高至少 1.25 ETH 时才会增加
  - 例如：如果验证器的有效余额是 31 ETH，收到额外的 1 ETH 存款
    - 验证器的余额变为 32 ETH
    - 但有效余额仍然保持为 31 ETH
    - 需要再存入至少 1.25 ETH 才能使有效余额增加到 32 ETH

**Deposit Queue（存款队列）：**
- 验证器在 deposit queue 中等待处理
- 队列长度取决于同时提交的存款数量
- **队列处理速度**：
  - 每个 epoch 最多处理 **MAX_PER_EPOCH_ACTIVATION_CHURN_LIMIT = 64** 个验证器
  - 每个 epoch = 128 秒 ≈ 2.13 分钟
  - **理论最快处理速度**：64 个验证器/epoch ≈ 2 秒/验证器
- **实际等待时间计算**：
  - 如果队列中有 N 个验证器等待处理
  - 等待时间 = (N / 64) × 128 秒
  - 例如：队列中有 128 个验证器 → 需要等待 2 epochs ≈ 4.27 分钟
  - 例如：队列中有 320 个验证器 → 需要等待 5 epochs ≈ 10.67 分钟
- **注意**：Deposit Queue 的处理发生在 Deposited 阶段之后，验证器需要先等待 ETH1_FOLLOW_DISTANCE（16 个区块），然后才能进入队列处理

### 3. Pending（等待激活队列）

**状态描述：**
- 验证器的有效余额已达到至少 32 ETH
- 进入 Pending 状态，等待激活

**时间：**
- 固定等待 **5 epochs**
- 5 epochs × 128 秒 = **640 秒 ≈ 10.67 分钟**

**说明：**
- 这是协议规定的等待期（见 `process_registry_updates`）
- 验证器在激活队列中等待
- 如果队列中有很多验证器等待激活，可能需要更长时间

**Pending Queue（激活队列）：**
- 验证器在 pending queue 中等待激活
- 队列长度取决于同时等待激活的验证器数量
- **队列处理速度**：
  - 每个 epoch 最多激活 **MAX_PER_EPOCH_ACTIVATION_CHURN_LIMIT = 64** 个验证器
  - 每个 epoch = 128 秒 ≈ 2.13 分钟
  - **理论最快处理速度**：64 个验证器/epoch ≈ 2 秒/验证器
- **实际等待时间计算**：
  - 如果队列中有 N 个验证器等待激活
  - 等待时间 = (N / 64) × 128 秒
  - 例如：队列中有 64 个验证器 → 需要等待 1 epoch ≈ 2.13 分钟
  - 例如：队列中有 320 个验证器 → 需要等待 5 epochs ≈ 10.67 分钟
- **固定等待期**：无论队列长度如何，每个验证器在进入 Pending 状态后，必须等待至少 **5 epochs**（协议规定）
- **总等待时间**：固定 5 epochs + 队列等待时间（如果有）

### 4. Active（激活）

**状态描述：**
- 验证器已激活，开始执行职责
- 开始获得质押奖励

**时间：**
- 从 Pending 状态结束后立即激活

**职责：**
- 每个 epoch 至少有一个 attestation 职责
- 可能被随机选中提议区块（propose blocks）
- 可能被选中参与同步委员会（sync committee）职责

**说明：**
- 激活后，验证器开始帮助保护网络并获得奖励
- 验证器状态会显示为 "Online" 或 "Offline"
  - **Online**：验证器正常执行职责
  - **Offline**：如果验证器错过了最近 3 个已确认的 attestations，会被标记为离线
  - 错过职责会导致错过奖励，并可能受到惩罚

## 时间总结表

| 阶段 | 最短时间 | 队列等待时间 | 说明 |
|------|---------|------------|------|
| **Unknown** | 不确定 | - | 取决于网络拥堵和 gas 费 |
| **Deposited** | **~3.2 分钟** | **+ (N/64) × 2.13 分钟** | 等待 16 个 ETH1 区块确认 + Deposit Queue 处理 |
| **Pending** | **~10.67 分钟** | **+ (N/64) × 2.13 分钟** | 固定等待 5 epochs + Pending Queue 等待 |
| **总计（最短）** | **~14 分钟** | **取决于队列长度** | 假设交易立即被打包，队列为空 |

**说明**：
- N = 队列中等待的验证器数量
- 队列等待时间仅在队列不为空时计算
- 实际总时间 = 最短时间 + 队列等待时间

## 注意事项

### 1. 队列延迟
- 如果同时有很多验证器进入队列，可能需要等待更长时间
- Deposit Queue 和 Pending Queue 都有动态的每 epoch 限制

### 2. 有效余额要求
- 确保存款后有效余额达到 32 ETH
- 可能需要存入超过 32 ETH 才能满足有效余额要求（如果之前有效余额较低）

### 3. 网络速度
- 您的测试网 slot 时间为 4 秒（主网为 12 秒），因此整体流程更快
- 这使得测试和开发更加高效

### 4. 交易确认
- 确保 deposit 交易被正确签名（BLS 签名）
- 如果签名错误（例如为错误的网络签名），会导致 "Invalid Deposit" 状态

## 与主网对比

| 参数 | 当前测试网 | 主网 |
|------|-----------|------|
| Slot 时间 | 4 秒 | 12 秒 |
| Epoch 时间 | ~2.13 分钟 | ~6.4 分钟 |
| Pending 阶段 | ~10.67 分钟 | ~32 分钟 |
| Deposited 阶段 | ~3.2 分钟 | ~3.2 分钟 |
| **总激活时间（最短）** | **~14 分钟** | **~35 分钟** |

## 验证器生命周期（Post-Pectra）

完整的验证器状态包括：

1. **Unknown** - 交易在内存池中
2. **Deposited** - 存款已确认，等待处理
3. **Pending** - 等待激活（5 epochs）
4. **Active** - 激活状态，执行职责
5. **Exiting** - 退出中（至少 5 epochs，可能有队列）
6. **Exited** - 已退出网络
7. **Slashed** - 因违规被强制退出
8. **Invalid Deposit** - 无效存款（通常是签名错误）

## 相关配置参数

从 `network-config.yaml` 中相关的关键参数：

```yaml
# 时间参数
SECONDS_PER_SLOT: 4                    # 每个 slot 4 秒
SLOT_DURATION_MS: 4000                  # Slot 持续时间（毫秒）
SECONDS_PER_ETH1_BLOCK: 12             # ETH1 区块时间
ETH1_FOLLOW_DISTANCE: 16                # ETH1 跟随距离（区块数）

# 验证器周期
MIN_PER_EPOCH_CHURN_LIMIT: 4           # 每个 epoch 最小变动限制
CHURN_LIMIT_QUOTIENT: 32                # 变动限制商数
MAX_PER_EPOCH_ACTIVATION_CHURN_LIMIT: 64  # 每个 epoch 最大激活变动限制

# 存款合约
DEPOSIT_CHAIN_ID: 3151908
DEPOSIT_NETWORK_ID: 3151908
DEPOSIT_CONTRACT_ADDRESS: 0x4242424242424242424242424242424242424242
```

## Deposit Queue 和 Pending Queue 详细说明

### Deposit Queue（存款队列）

**作用**：处理已确认的存款交易，将验证器从 Deposited 状态推进到 Pending 状态

**处理速度**：
- 每个 epoch 最多处理 **64 个验证器**（`MAX_PER_EPOCH_ACTIVATION_CHURN_LIMIT`）
- 每个 epoch = 128 秒 ≈ 2.13 分钟
- 理论处理速度：**约 2 秒/验证器**

**等待时间计算**：
```
等待时间 = (队列位置 / 64) × 128 秒
```

**示例**：
- 队列位置 1-64：等待 0-1 epoch（0-2.13 分钟）
- 队列位置 65-128：等待 1-2 epochs（2.13-4.27 分钟）
- 队列位置 129-192：等待 2-3 epochs（4.27-6.4 分钟）

**注意**：Deposit Queue 的处理发生在 ETH1_FOLLOW_DISTANCE（16 个区块）之后，所以总等待时间 = ETH1 确认时间 + 队列等待时间

### Pending Queue（激活队列）

**作用**：处理已进入 Pending 状态的验证器，等待激活

**处理速度**：
- 每个 epoch 最多激活 **64 个验证器**（`MAX_PER_EPOCH_ACTIVATION_CHURN_LIMIT`）
- 每个 epoch = 128 秒 ≈ 2.13 分钟
- 理论处理速度：**约 2 秒/验证器**

**固定等待期**：
- 每个验证器在进入 Pending 状态后，必须等待至少 **5 epochs**（协议规定）
- 这是固定的等待期，无论队列是否为空

**等待时间计算**：
```
总等待时间 = 5 epochs（固定） + (队列位置 / 64) × 128 秒
```

**示例**：
- 队列位置 1-64：等待 5-6 epochs（10.67-12.8 分钟）
- 队列位置 65-128：等待 6-7 epochs（12.8-14.93 分钟）
- 队列位置 129-192：等待 7-8 epochs（14.93-17.07 分钟）

### 队列查询方法

可以通过 Beacon Chain API 查询队列状态：

```bash
# 查询 deposit queue
curl http://beacon-api:3500/eth/v1/beacon/deposit_snapshot

# 查询 pending validators
curl http://beacon-api:3500/eth/v1/beacon/states/head/validators?status=pending_queued
```

## 总结

在理想情况下（交易立即被打包，队列为空），从提交 deposit 到验证器激活大约需要 **14 分钟**，其中：

- **~3.2 分钟**：等待 ETH1 区块确认（Deposited 阶段）
- **~10.67 分钟**：固定等待 5 epochs（Pending 阶段）

**实际时间**取决于队列长度：
- 如果 Deposit Queue 中有 N 个验证器：额外等待 `(N/64) × 2.13 分钟`
- 如果 Pending Queue 中有 M 个验证器：额外等待 `(M/64) × 2.13 分钟`

**总时间公式**：
```
总时间 = 3.2 分钟（ETH1 确认）
       + (N/64) × 2.13 分钟（Deposit Queue）
       + 10.67 分钟（固定 5 epochs）
       + (M/64) × 2.13 分钟（Pending Queue）
```

这个时间比主网快得多（主网约需 35 分钟），非常适合测试和开发环境。

## 参考资料

- [Beaconcha.in Deposit Process Guide](https://docs.beaconcha.in/faqs/deposit-process)
- [Ethereum Validator Lifecycle](https://docs.beaconcha.in/faqs/deposit-process#ethereum-validator-lifecycle-and-status-post-pectra)
- [How Ethereum validator withdrawals work](https://docs.beaconcha.in/faqs/how-ethereum-validator-withdrawals-work)

