# Web3Signer 签名根不匹配错误排查指南

## 错误信息解析

```
java.lang.IllegalArgumentException: Signing root 0xf1456910bde311098abee70d5bf6f0e72d54278037bf0cf453e4429cf32a2913 
must match signing computed signing root 0xa782346bec9f1b591acdd837875105e6cf3644f6b45c73218a26efef1a84fda4 from data
```

### 错误含义

这个错误表示：
1. **请求中的签名根**：`0xf1456910bde311098abee70d5bf6f0e72d54278037bf0cf453e4429cf32a2913`
   - 这是 Validator Client 在签名请求中提供的 `signingRoot` 字段

2. **计算出的签名根**：`0xa782346bec9f1b591acdd837875105e6cf3644f6b45c73218a26efef1a84fda4`
   - 这是 Web3Signer 从请求数据（`type`, `fork_info`, `block` 等）重新计算出的签名根

3. **不匹配**：两个签名根不一致，说明：
   - Validator Client 发送的 `signingRoot` 与请求数据不匹配
   - 或者请求数据本身有问题（fork_info、genesis_validators_root 等参数不正确）

### 可能的原因

1. **网络配置不匹配**
   - Validator Client 和 Web3Signer 使用的网络配置不一致
   - Fork version、genesis_validators_root 等参数不匹配

2. **请求数据格式问题**
   - Validator Client 发送的签名请求格式不正确
   - `signingRoot` 字段计算错误

3. **密钥配置问题**（虽然密钥存在，但可能配置不正确）
   - Vault 中的私钥与公钥不匹配（虽然这种情况较少见）
   - Web3Signer 配置文件中的路径或格式问题

## 手动验证步骤

### 1. 验证 Vault 中的密钥

使用提供的验证脚本：

```bash
# 验证密钥是否正确
python scripts/verify_vault_key.py <pubkey>

# 检查 Vault 路径和内容
python scripts/verify_vault_key.py <pubkey> --check-path
```

脚本会：
- 从 Vault 读取私钥
- 验证私钥与公钥是否匹配
- 检查 Vault 路径和存储格式

### 2. 检查 Web3Signer 配置

```bash
# 查看 Web3Signer 中的密钥列表
curl http://localhost:9002/api/v1/eth2/publicKeys

# 查看特定密钥的配置（如果 Web3Signer 支持）
curl http://localhost:9002/api/v1/eth2/publicKeys/<pubkey>
```

### 3. 检查 Validator Client 配置

检查 Validator Client 的网络配置：
- Fork version
- Genesis validators root
- 网络类型（mainnet/testnet/kurtosis）

### 4. 检查 Web3Signer 配置文件

```bash
# 查看 Web3Signer 密钥配置文件
ls -la infra/web3signer/keys/

# 查看特定密钥的配置
cat infra/web3signer/keys/vault-<pubkey前16字符>.yaml
```

配置文件应该包含：
- `type: "hashicorp"`
- `keyType: "BLS"`
- `keyPath: "/v1/secret/data/web3signer-keys/<pubkey>"`
- `keyName: "value"`
- `token: "<vault_token>"`

### 5. 验证 Vault 中的密钥存储

使用 Vault CLI 或 API：

```bash
# 使用 Vault CLI
vault kv get secret/web3signer-keys/<pubkey>

# 或使用 HTTP API
curl \
  --header "X-Vault-Token: <token>" \
  http://localhost:8200/v1/secret/data/web3signer-keys/<pubkey>
```

应该返回：
```json
{
  "data": {
    "data": {
      "value": "<64字符的私钥十六进制字符串>"
    }
  }
}
```

### 6. 测试签名请求

手动构造一个签名请求来测试：

```bash
curl -X POST http://localhost:9002/api/v1/eth2/sign/<pubkey> \
  -H "Content-Type: application/json" \
  -d '{
    "type": "BLOCK",
    "fork_info": {
      "fork": {
        "previous_version": "0x00000000",
        "current_version": "0x00000000",
        "epoch": "0"
      },
      "genesis_validators_root": "0x0000000000000000000000000000000000000000000000000000000000000000"
    },
    "signingRoot": "0x0000000000000000000000000000000000000000000000000000000000000000"
  }'
```

## 常见问题和解决方案

### 问题1: 私钥与公钥不匹配

**症状**：验证脚本显示私钥与公钥不匹配

**解决方案**：
1. 检查密钥生成过程是否正确
2. 确认 Vault 中存储的是正确的私钥
3. 重新生成密钥配置

### 问题2: Vault 路径不正确

**症状**：无法从 Vault 读取密钥

**解决方案**：
1. 检查 Web3Signer 配置文件中的 `keyPath`
2. 确认 Vault mount point 和 key path prefix 配置正确
3. 验证 Vault token 是否有效

### 问题3: 网络配置不匹配

**症状**：签名根不匹配，但密钥验证正常

**解决方案**：
1. 检查 Validator Client 的网络配置
2. 检查 Web3Signer 的网络配置
3. 确认 fork version 和 genesis_validators_root 一致

### 问题4: Vault Token 过期

**症状**：Web3Signer 无法访问 Vault

**解决方案**：
1. 检查 Vault token 是否过期
2. 重新生成 Web3Signer 配置文件（会自动刷新 token）
3. 重启 Web3Signer 以加载新配置

## 调试命令总结

```bash
# 1. 验证 Vault 密钥
python scripts/verify_vault_key.py <pubkey>

# 2. 检查 Web3Signer 密钥列表
curl http://localhost:9002/api/v1/eth2/publicKeys

# 3. 检查 Vault 存储
vault kv get secret/web3signer-keys/<pubkey>

# 4. 查看 Web3Signer 日志
docker logs web3signer-1
docker logs web3signer-2

# 5. 查看 Validator Client 日志
docker logs <validator-client-container>
```

