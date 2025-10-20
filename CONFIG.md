# 配置说明

## 📁 配置目录结构

```
config/                    # 配置目录 (git 忽略)
└── config.json          # 运行时配置文件

config.sample.json        # 示例配置文件 (git 跟踪)
```

## 🔧 配置文件说明

### 主配置文件
- **位置**: `config/config.json`
- **用途**: 运行时配置，包含敏感信息
- **Git 状态**: 被忽略，不会提交到版本控制

### 示例配置文件
- **位置**: `config.sample.json`
- **用途**: 提供配置模板，包含所有配置项但不包含敏感信息
- **Git 状态**: 被跟踪，可以提交到版本控制

## 🚀 快速开始

### 1. 复制配置文件
```bash
# 从示例配置创建运行时配置
cp config.sample.json config/config.json
```

### 2. 编辑配置
```bash
# 编辑运行时配置
vim config/config.json
```

### 3. 验证配置
```bash
# 检查配置是否正确
cd code && source venv/bin/activate
python3 core/validator_manager.py check-services
```

## 📋 配置项说明

### 基础配置
```json
{
  "vault_url": "http://localhost:8200",
  "vault_token": "dev-root-token",
  "web3signer_url": "http://localhost:9000",
  "beacon_url": "http://localhost:5052",
  "web3_url": "http://localhost:33205"
}
```

### 验证者配置
```json
{
  "validator_count": 10,
  "withdrawal_address": "0x8943545177806ED17B9F23F0a21ee5948eCaa776",
  "timeout_activation": 1800,
  "timeout_exit": 1800,
  "monitoring_duration": 600
}
```

### 网络参数
```json
{
  "network_params": {
    "slots_per_epoch": 8,
    "seconds_per_slot": 4,
    "genesis_delay": 60,
    "churn_limit_quotient": 32,
    "min_genesis_active_validator_count": 64
  }
}
```

### Kurtosis 测试网配置
```json
{
  "kurtosis_testnet": {
    "enabled": true,
    "web3_url": "http://localhost:33205",
    "deposit_contract_address": "0x4242424242424242424242424242424242424242",
    "from_address": "0x8943545177806ED17B9F23F0a21ee5948eCaa776",
    "private_key": "0xbcdf20249abf0ed6d944c0288fad489e33f66b3960d9e6229c1cd214ed3bbe31",
    "gas_price": "20000000000",
    "gas_limit": "1000000"
  }
}
```

## 🔐 安全注意事项

1. **敏感信息**: `config/test_config.json` 包含私钥等敏感信息，不要提交到版本控制
2. **示例配置**: `config.sample.json` 不包含真实私钥，可以安全提交
3. **备份**: 定期备份配置文件，特别是包含重要私钥的配置

## 🛠️ 故障排除

### 配置文件不存在
```bash
# 错误: 找不到配置文件
cp config.sample.json config/config.json
```

### 配置格式错误
```bash
# 验证 JSON 格式
python3 -m json.tool config/config.json
```

### 权限问题
```bash
# 确保配置文件可读
chmod 644 config/config.json
```
