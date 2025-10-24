# Prysm Validator 启动问题修复

## 问题分析

从错误日志可以看出，主要问题包括：

1. **`--config-file` 参数不支持**: Prysm 不支持 `--config-file` 参数，应该使用直接的命令行参数
2. **Web3Signer 连接配置错误**: 需要使用正确的远程签名器参数
3. **签名请求失败**: `failed to sign the request: http: ContentLength=439 with Body length 0`

## 修复内容

### 1. 移除不支持的 `--config-file` 参数

**之前的问题代码:**
```bash
prysm validator --config-file=configs/prysm/validator-config.yaml
```

**修复后:**
```bash
prysm validator --beacon-rpc-provider=127.0.0.1:4000 --keymanager-kind=remote --keymanager-url=http://localhost:9000
```

### 2. 正确配置 Web3Signer 连接

**关键参数:**
- `--validators-external-signer-url=http://localhost:9000`: Web3Signer 服务地址
- `--validators-external-signer-public-keys`: 验证者公钥列表

**注意:** 根据 [Prysm 官方文档](https://prysm.offchainlabs.com/docs/manage-wallet/web3signer/)，`--keymanager-kind` 和 `--keymanager-url` 参数不存在，应该使用 `--validators-external-signer-url` 和 `--validators-external-signer-public-keys`。

### 3. 完整的启动命令

```bash
prysm validator \
    --beacon-rpc-provider=127.0.0.1:4000 \
    --validators-external-signer-url=http://localhost:9000 \
    --validators-external-signer-public-keys=0x1234...,0x5678... \
    --suggested-fee-recipient=0x8943545177806ED17B9F23F0a21ee5948eCaa776 \
    --chain-config-file=/path/to/network-config.yaml \
    --enable-external-slashing-protection \
    --slashing-protection-db-url=postgres://user:password@localhost:5432/slashing_protection \
    --graffiti=Prysm-20251024 \
    --log-format=json \
    --log-level=info \
    --monitoring-port=8082 \
    --web \
    --http-port=7500 \
    --accept-terms-of-use
```

## 修改的文件

1. **`code/utils/validator_client_config.py`**
   - 修复了 `_generate_prysm_start_script` 方法
   - 移除了不支持的 `--config-file` 参数
   - 添加了正确的 Web3Signer 连接参数
   - 使用动态检测的 beacon-rpc-provider 地址
   - **新增**: 支持 Public Key Persistence 功能

2. **`scripts/start_validator_client.py`**
   - 添加了 `--enable-key-persistence` 和 `--disable-key-persistence` 参数
   - 默认启用公钥持久化功能

## 新增功能：Public Key Persistence

### 功能说明
根据 [Prysm Web3Signer 官方文档](https://prysm.offchainlabs.com/docs/manage-wallet/web3signer/)，Public Key Persistence 功能可以让通过 Remote Keymanager API 设置的公钥在验证器重启后仍然保持。

### 使用方法

**启用公钥持久化（默认）:**
```bash
./validator.sh start-validator prysm
```

**禁用公钥持久化:**
```bash
python3 scripts/start_validator_client.py prysm --disable-key-persistence
```

**手动指定公钥持久化文件:**
```bash
python3 scripts/start_validator_client.py prysm --enable-key-persistence
```

### 生成的文件
- `configs/prysm/validator-keys.txt`: 公钥持久化文件，每行一个公钥
- 启动脚本会自动添加 `--validators-external-signer-key-file` 参数


## 验证步骤

1. 确保 Web3Signer 服务正在运行
2. 确保网络配置文件存在
3. 运行 `./validator.sh start-validator prysm`
4. 检查日志中是否还有签名错误
5. 验证公钥持久化文件是否生成

## 预期结果

修复后，Prysm 验证器应该能够：
- 正确连接到 Web3Signer 进行签名
- 使用指定的网络配置文件
- 设置正确的费用接收者
- 支持公钥持久化功能
- 不再出现 "failed to sign the request" 错误
