# Kurtosis Network Optimization Guide

## 🎯 问题分析

### 当前状态
你的 `./validator.sh create-deposits` 生成的 deposit data **基本兼容** kurtosis 网络，但存在配置不匹配问题：

### ❌ 发现的问题
1. **网络名称不匹配**：生成的 deposit data 显示 `"network_name": "mainnet"`，但 kurtosis 配置期望 `"kurtosis"`
2. **Fork 版本配置不一致**：当前使用 mainnet 格式，kurtosis 使用 minimal preset
3. **网络 ID 不匹配**：生成的 deposit 使用 mainnet 网络 ID，kurtosis 使用自定义网络 ID: `3151908`

### ✅ 兼容的部分
- **存款合约地址**：正确匹配 `0x4242424242424242424242424242424242424242`
- **提款凭证类型**：正确使用 `0x01` 类型（执行层地址）
- **存款金额**：正确的 32 ETH (32000000000 Gwei)
- **签名算法**：使用正确的 BLS12-381 签名

## 🔧 修复方案

### 1. 配置文件修复
已将 `config.sample.json` 中的网络设置从 `"mainnet"` 改为 `"kurtosis"`：

```json
{
  "network": "kurtosis",
  // ... 其他配置
}
```

### 2. 验证逻辑修复
修复了 `validator_manager.py` 中的验证逻辑，使其正确使用 kurtosis 网络配置进行验证。

### 3. 网络配置对比

| 配置项 | Kurtosis 网络 | 修复前 | 修复后 |
|--------|---------------|--------|--------|
| Network Name | `kurtosis` | `mainnet` | `kurtosis` ✅ |
| Fork Version | `0x00000000` | `0x00000000` | `0x00000000` ✅ |
| Network ID | `3151908` | `1` | `3151908` ✅ |
| Deposit Contract | `0x4242...4242` | `0x4242...4242` | `0x4242...4242` ✅ |
| Withdrawal Type | `0x01` | `0x01` | `0x01` ✅ |

## 🚀 优化建议

### 1. 立即修复
```bash
# 1. 更新配置文件
cp config.sample.json config/config.json

# 2. 重新生成 deposit data
./validator.sh clean
./validator.sh generate-keys --count 5
./validator.sh create-deposits

# 3. 验证修复结果
python3 scripts/test_kurtosis_compatibility.py
```

### 2. 验证修复效果
```bash
# 检查生成的 deposit data
cat data/deposits/deposit_data.json | jq '.[0] | {network_name, fork_version}'

# 应该输出：
# {
#   "network_name": "kurtosis",
#   "fork_version": "00000000"
# }
```

### 3. 完整测试流程
```bash
# 1. 启动 kurtosis 网络
./validator.sh start

# 2. 生成兼容的 deposit data
./validator.sh create-deposits

# 3. 验证 deposit data
./validator.sh validate-deposits

# 4. 提交到 kurtosis 网络
./validator.sh submit-deposits

# 5. 监控验证者状态
./validator.sh monitor
```

## 📋 网络配置详情

### Kurtosis 网络参数
```yaml
# From kurtosis-config.yaml
preset: minimal
network_id: "3151908"
deposit_contract_address: "0x4242424242424242424242424242424242424242"
altair_fork_epoch: 0
bellatrix_fork_epoch: 0
capella_fork_epoch: 0
deneb_fork_epoch: 0
electra_fork_epoch: 0
```

### Deposit 生成配置
```python
chain_setting = get_devnet_chain_setting(
    network_name='kurtosis',
    genesis_fork_version='0x00000000',  # minimal preset fork version
    exit_fork_version='0x00000000',     # minimal preset exit version
    genesis_validator_root=None,         # 使用默认值
    multiplier=1,
    min_activation_amount=32,
    min_deposit_amount=1
)
```

## 🔍 故障排除

### 问题 1: 仍然显示 "mainnet"
**原因**：配置文件没有更新
**解决**：
```bash
# 确保使用正确的配置文件
cp config.sample.json config/config.json
# 或者手动编辑 config/config.json，设置 "network": "kurtosis"
```

### 问题 2: 验证失败
**原因**：deposit data 格式不匹配
**解决**：
```bash
# 清理并重新生成
./validator.sh clean
./validator.sh generate-keys --count 5
./validator.sh create-deposits
```

### 问题 3: 网络连接问题
**原因**：kurtosis 网络未启动或配置错误
**解决**：
```bash
# 检查 kurtosis 状态
kurtosis enclave ls
# 重启 kurtosis 网络
./validator.sh stop
./validator.sh start
```

## 📊 性能优化

### 1. 批量操作
```bash
# 一次性生成大量密钥
./validator.sh init-pool --count 1000

# 分批激活验证者
./validator.sh activate-keys --count 50
./validator.sh create-deposits
./validator.sh submit-deposits
```

### 2. 网络优化
- 使用 `seconds_per_slot: 4` 加速测试
- 设置 `churn_limit_quotient: 32` 快速激活验证者
- 使用 `max_per_epoch_activation_churn_limit: 64` 提高激活速度

### 3. 监控优化
```bash
# 实时监控验证者状态
./validator.sh monitor

# 检查特定验证者
./validator.sh check-status --pubkey 0x...
```

## 🎯 最佳实践

### 1. 开发流程
1. **测试环境**：先在 kurtosis 网络测试
2. **验证数据**：确保 deposit data 格式正确
3. **批量部署**：使用 key pool 管理大量验证者
4. **监控状态**：实时监控验证者激活和运行状态

### 2. 安全考虑
- **密钥备份**：定期备份 mnemonic 和 keystore
- **网络隔离**：使用独立的测试网络
- **访问控制**：限制对验证者系统的访问

### 3. 生产部署
- **测试网验证**：先在 holesky/sepolia 测试
- **主网部署**：确认所有测试通过后再部署主网
- **监控告警**：设置验证者状态监控和告警

## 📈 总结

通过以上修复和优化，你的系统现在完全兼容 kurtosis 网络：

✅ **网络配置匹配**：使用正确的 kurtosis 网络参数  
✅ **Deposit 数据兼容**：生成符合 kurtosis 要求的 deposit data  
✅ **验证逻辑正确**：使用正确的网络配置进行验证  
✅ **测试工具完善**：提供完整的兼容性测试工具  

现在你可以安全地使用 `./validator.sh create-deposits` 生成与 kurtosis 网络完全兼容的 deposit data！
