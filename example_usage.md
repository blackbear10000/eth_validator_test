# 新系统使用示例

## 🎯 完整工作流程示例

### 1. 启动基础设施
```bash
# 启动 Vault, Web3Signer, Kurtosis 等
./start.sh quick-start
```

### 2. 生成密钥并存储到 Vault
```bash
# 使用现有的密钥生成器
python3 scripts/external_validator_manager.py generate-keys --count 5
```

### 3. 查询和管理密钥
```bash
# 列出所有密钥
python3 scripts/vault_key_manager.py list

# 按状态过滤
python3 scripts/vault_key_manager.py list --status unused

# 按批次过滤
python3 scripts/vault_key_manager.py list --batch-id batch-001

# 获取未使用的密钥
python3 scripts/vault_key_manager.py unused --count 3
```

### 4. 生成存款数据
```bash
# 从 Vault 读取未使用密钥，生成存款
python3 scripts/deposit_generator.py generate 3 0xf39Fd6e51aad88F6F4ce6aB8827279cffFb92266

# 指定批次和客户端类型
python3 scripts/deposit_generator.py generate 2 0xf39Fd6e51aad88F6F4ce6aB8827279cffFb92266 --batch-id batch-001 --client-type prysm
```

### 5. 生成验证者客户端配置
```bash
# 获取活跃密钥的公钥
python3 scripts/validator_client_config.py list-active

# 生成 Prysm 配置
python3 scripts/validator_client_config.py prysm --pubkeys 0x1234... 0x5678... --beacon-node http://localhost:3500

# 生成所有客户端配置
python3 scripts/validator_client_config.py all --pubkeys 0x1234... 0x5678...
```

### 6. 备份密钥
```bash
# 创建 keystore 备份
python3 scripts/backup_system.py keystore 0x1234... 0x5678... --password mypassword

# 创建 mnemonic 备份
python3 scripts/backup_system.py mnemonic 0x1234... 0x5678...

# 创建批次备份
python3 scripts/backup_system.py batch batch-001 --format both --password mypassword
```

### 7. 监控和管理
```bash
# 获取存款摘要
python3 scripts/deposit_generator.py summary 0xf39Fd6e51aad88F6F4ce6aB8827279cffFb92266

# 列出所有备份
python3 scripts/backup_system.py list

# 更新密钥状态
python3 scripts/vault_key_manager.py status 0x1234... active --client-type prysm --notes "已激活"
```

## 🔄 典型使用场景

### 场景1：批量生成验证者
```bash
# 1. 生成 10 个密钥
python3 scripts/external_validator_manager.py generate-keys --count 10

# 2. 查看生成的密钥
python3 scripts/vault_key_manager.py list --status unused

# 3. 生成存款数据
python3 scripts/deposit_generator.py generate 10 0xf39Fd6e51aad88F6F4ce6aB8827279cffFb92266

# 4. 生成 Prysm 配置
python3 scripts/validator_client_config.py prysm --pubkeys $(python3 scripts/vault_key_manager.py unused --count 10 | grep -o '0x[0-9a-fA-F]*')
```

### 场景2：按批次管理
```bash
# 1. 查看特定批次的密钥
python3 scripts/vault_key_manager.py list --batch-id batch-001

# 2. 为该批次生成存款
python3 scripts/deposit_generator.py generate 5 0xf39Fd6e51aad88F6F4ce6aB8827279cffFb92266 --batch-id batch-001

# 3. 备份该批次
python3 scripts/backup_system.py batch batch-001 --format both --password mypassword
```

### 场景3：多客户端支持
```bash
# 1. 获取活跃密钥
python3 scripts/validator_client_config.py list-active

# 2. 为不同客户端生成配置
python3 scripts/validator_client_config.py prysm --pubkeys 0x1234... 0x5678...
python3 scripts/validator_client_config.py lighthouse --pubkeys 0x9abc... 0xdef0...
python3 scripts/validator_client_config.py teku --pubkeys 0x1111... 0x2222...

# 3. 或者一次性生成所有配置
python3 scripts/validator_client_config.py all --pubkeys 0x1234... 0x5678... 0x9abc... 0xdef0...
```

## 🛡️ 安全最佳实践

### 密钥备份
```bash
# 定期备份所有密钥
python3 scripts/backup_system.py batch all --format encrypted --password strong_password

# 备份特定批次的助记词
python3 scripts/backup_system.py batch batch-001 --format mnemonic
```

### 密钥状态管理
```bash
# 标记密钥为使用中
python3 scripts/vault_key_manager.py status 0x1234... active --client-type prysm --notes "Prysm 验证者"

# 标记密钥为已注销
python3 scripts/vault_key_manager.py status 0x1234... retired --notes "已退出网络"
```

### 恢复测试
```bash
# 试运行恢复
python3 scripts/backup_system.py restore backup-file.json --dry-run

# 实际恢复
python3 scripts/backup_system.py restore backup-file.json --password mypassword
```

## 📊 监控和调试

### 查看系统状态
```bash
# 查看服务状态
./start.sh status

# 查看密钥统计
python3 scripts/deposit_generator.py summary 0xf39Fd6e51aad88F6F4ce6aB8827279cffFb92266

# 查看活跃密钥分布
python3 scripts/validator_client_config.py list-active
```

### 故障排除
```bash
# 检查 Vault 连接
python3 scripts/vault_key_manager.py list

# 检查可用密钥
python3 scripts/deposit_generator.py list-keys

# 查看备份文件
python3 scripts/backup_system.py list
```

这个新系统提供了完整的验证者密钥管理解决方案，支持您提到的所有需求：
- ✅ 按公钥、批次、生成日期查询
- ✅ 支持 Prysm、Lighthouse、Teku 三种客户端
- ✅ 密钥状态管理（未使用/使用中/已注销）
- ✅ 支持 keystore 和 mnemonic 备份形式
