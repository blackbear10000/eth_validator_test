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

1. **网络配置不匹配** ⚠️ **最可能的原因**
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

### 2. 检查 Validator Client 网络配置

使用网络配置检查脚本：

```bash
# 检查所有 Validator Client 的网络配置
python scripts/check_validator_network_config.py

# 检查特定容器
python scripts/check_validator_network_config.py --container <container-name>
```

脚本会检查：
- `network-config.yaml` 文件是否存在和内容
- 容器是否正确挂载了网络配置文件
- 启动命令是否包含 `--chain-config-file` 参数
- Fork version 是否与 Beacon API 一致

### 3. 手动检查容器配置

```bash
# 1. 查找 Validator Client 容器
docker ps | grep -E "validator|prysm|lighthouse|teku"

# 2. 检查容器内的网络配置文件
docker exec <container-name> ls -la /network-config.yaml

# 3. 查看文件内容
docker exec <container-name> cat /network-config.yaml | head -50

# 4. 检查启动命令
docker exec <container-name> ps aux | grep -E "chain-config|network-config"

# 5. 检查挂载点
docker inspect <container-name> | grep -A 10 "Mounts"
```

### 4. 检查 Beacon API 网络信息

```bash
# 检查 fork 信息
curl http://localhost:5052/eth/v1/beacon/states/head/fork

# 检查 genesis 信息
curl http://localhost:5052/eth/v1/beacon/genesis

# 检查网络配置
curl http://localhost:5052/eth/v1/config/spec
```

### 5. 检查 Web3Signer 配置

```bash
# 查看 Web3Signer 中的密钥列表
curl http://localhost:9002/api/v1/eth2/publicKeys

# 查看 Web3Signer 日志
docker logs web3signer-1 | tail -50
docker logs web3signer-2 | tail -50
```

### 6. 检查 network-config.yaml 文件

```bash
# 查看文件内容
cat infra/kurtosis/network-config.yaml | head -60

# 检查关键参数
grep -E "GENESIS_FORK_VERSION|CONFIG_NAME|PRESET_BASE" infra/kurtosis/network-config.yaml
```

## 常见问题和解决方案

### 问题1: network-config.yaml 未挂载

**症状**：容器内 `/network-config.yaml` 文件不存在

**解决方案**：
1. 检查 `client_process_service.py` 中的挂载逻辑
2. 确认 `infra/kurtosis/network-config.yaml` 文件存在
3. 重新启动 Validator Client 容器

### 问题2: Fork Version 不匹配

**症状**：`network-config.yaml` 中的 fork version 与 Beacon API 不一致

**解决方案**：
1. 从 Beacon API 获取实际的 fork version
2. 更新 `network-config.yaml` 文件
3. 重启 Validator Client

### 问题3: Genesis Validators Root 不匹配

**症状**：签名根不匹配，但 fork version 正确

**解决方案**：
1. `genesis_validators_root` 在创世时确定，无法修改
2. 确认 Validator Client 和 Web3Signer 使用相同的网络
3. 如果网络已启动，可能需要重新启动网络以获取正确的 genesis_validators_root

### 问题4: Validator Client 未使用网络配置文件

**症状**：启动命令中没有 `--chain-config-file` 参数

**解决方案**：
1. 检查 `client_process_service.py` 中的 `_build_container_command` 方法
2. 确认 Prysm 启动命令包含 `--chain-config-file /network-config.yaml`
3. 重新生成客户端配置并重启

## 调试命令总结

```bash
# 1. 验证 Vault 密钥
python scripts/verify_vault_key.py <pubkey>

# 2. 检查网络配置
python scripts/check_validator_network_config.py

# 3. 检查 Web3Signer 密钥列表
curl http://localhost:9002/api/v1/eth2/publicKeys

# 4. 检查 Beacon API 网络信息
curl http://localhost:5052/eth/v1/beacon/states/head/fork
curl http://localhost:5052/eth/v1/beacon/genesis

# 5. 检查容器配置
docker exec <container-name> cat /network-config.yaml | head -30
docker exec <container-name> ps aux | grep chain-config

# 6. 查看日志
docker logs <validator-container> | tail -100
docker logs web3signer-1 | tail -100
```

## 重点排查项

根据你的情况（Web3Signer 和 Vault 都正常），**最可能的问题是网络配置不匹配**：

1. ✅ **检查 Validator Client 是否加载了 network-config.yaml**
   ```bash
   docker exec <container-name> cat /network-config.yaml
   docker exec <container-name> ps aux | grep chain-config-file
   ```

2. ✅ **检查 network-config.yaml 中的 fork version**
   ```bash
   grep GENESIS_FORK_VERSION infra/kurtosis/network-config.yaml
   ```

3. ✅ **从 Beacon API 获取实际的网络参数**
   ```bash
   curl http://localhost:5052/eth/v1/beacon/states/head/fork
   curl http://localhost:5052/eth/v1/beacon/genesis
   ```

4. ✅ **比较两者是否一致**

如果 fork version 或 genesis_validators_root 不匹配，Validator Client 计算出的签名根就会与 Web3Signer 期望的不一致。
