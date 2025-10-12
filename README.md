# ETH Validator Workflow Testing System

A comprehensive testing framework for Ethereum validator lifecycle management using Kurtosis, Web3Signer, Vault, and Consul.

## 🎯 Overview

This system provides a comprehensive Ethereum validator key management solution with:
- **Key Management**: HashiCorp Vault for secure key storage with advanced query capabilities
- **Multi-Client Support**: Supports Prysm, Lighthouse, and Teku validator clients
- **Advanced Backup**: Supports keystore and mnemonic backup formats
- **Official Implementation**: Uses `ethstaker-deposit-cli` for BLS12-381 key generation
- **Lifecycle Testing**: Complete validator onboarding/exit workflows

## 🏗️ Architecture

### Infrastructure Stack
- **Vault** (port 8200): Secure key storage with KV v2 engine
- **PostgreSQL** (port 5432): Slashing protection database for Web3Signer
- **Web3Signer** (port 9000): Remote signing service for external validators
- **Kurtosis Devnet**: Accelerated testnet with 4s slots for fast testing

### Enhanced Workflow
```
1. 密钥管理 → 2. 存款生成 → 3. 客户端配置 → 4. 验证者运行
```

#### 详细流程
```
1. 密钥管理 (Vault Key Manager)
   ├── 生成密钥 → 存储到 Vault
   ├── 查询密钥 (按公钥/批次/日期)
   ├── 状态管理 (未使用/使用中/已注销)
   └── 备份支持 (keystore/mnemonic)

2. 存款生成 (Dynamic Deposit Generator)
   ├── 从 Vault 读取未使用密钥
   ├── 支持动态提款地址
   ├── 生成存款数据
   └── 自动标记密钥为使用中

3. 客户端配置 (Validator Client Config)
   ├── 支持 Prysm/Lighthouse/Teku
   ├── 生成 Web3Signer 配置
   ├── 生成客户端配置文件
   └── 生成启动脚本

4. 验证者运行
   ├── 启动 Web3Signer
   ├── 启动验证者客户端
   ├── 监控性能
   └── 测试退出流程
```

## 🚀 Quick Start

### Prerequisites
- Docker & Docker Compose
- [Kurtosis CLI](https://docs.kurtosis.com/install)
- Python 3.8+
- Git (for ethstaker-deposit-cli integration)

### 🔑 Vault Token 获取指南

在这个项目中，Vault 使用开发模式运行，默认的 root token 是 `dev-root-token`。

#### 获取 Vault Token 的方法

**方法1：使用默认 token（推荐）**
```bash
# 直接使用默认 token
python3 scripts/vault_key_manager.py --vault-token dev-root-token list
```

**方法2：设置环境变量**
```bash
# 设置环境变量
export VAULT_TOKEN=dev-root-token

# 然后正常使用命令
python3 scripts/vault_key_manager.py list
```

**方法3：启动基础设施后获取**
```bash
# 1. 启动基础设施
./start.sh quick-start

# 2. 等待服务启动完成
# 3. 使用默认 token
python3 scripts/vault_key_manager.py --vault-token dev-root-token list
```

#### 故障排除

**问题1：Vault 服务未运行**
```bash
# 检查 Vault 状态
curl http://localhost:8200/v1/sys/health

# 如果返回 "Vault not accessible"，需要启动服务
./start.sh quick-start
```

**问题2：Token 认证失败**
```bash
# 确保使用正确的 token
python3 scripts/vault_key_manager.py --vault-token dev-root-token list
```

**问题3：Docker 未运行**
```bash
# 启动 Docker
sudo systemctl start docker  # Linux
# 或启动 Docker Desktop  # macOS/Windows

# 然后启动基础设施
./start.sh quick-start
```



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
python3 scripts/vault_key_manager.py --vault-token dev-root-token list

# 按状态过滤
python3 scripts/vault_key_manager.py --vault-token dev-root-token list --status unused

# 按批次过滤
python3 scripts/vault_key_manager.py --vault-token dev-root-token list --batch-id batch-001

# 获取未使用的密钥
python3 scripts/vault_key_manager.py --vault-token dev-root-token unused --count 3
```

### 4. 生成存款数据
```bash
# 从 Vault 读取未使用密钥，生成存款
python3 scripts/deposit_generator.py --vault-token dev-root-token generate 3 0xf39Fd6e51aad88F6F4ce6aB8827279cffFb92266

# 指定批次和客户端类型
python3 scripts/deposit_generator.py --vault-token dev-root-token generate 2 0xf39Fd6e51aad88F6F4ce6aB8827279cffFb92266 --batch-id batch-001 --client-type prysm
```

### 5. 生成验证者客户端配置
```bash
# 获取活跃密钥的公钥
python3 scripts/validator_client_config.py --vault-token dev-root-token list-active

# 生成 Prysm 配置
python3 scripts/validator_client_config.py --vault-token dev-root-token prysm --pubkeys 0x1234... 0x5678... --beacon-node http://localhost:3500

# 生成所有客户端配置
python3 scripts/validator_client_config.py --vault-token dev-root-token all --pubkeys 0x1234... 0x5678...
```

### 6. 备份密钥
```bash
# 创建 keystore 备份
python3 scripts/backup_system.py --vault-token dev-root-token keystore 0x1234... 0x5678... --password mypassword

# 创建 mnemonic 备份
python3 scripts/backup_system.py --vault-token dev-root-token mnemonic 0x1234... 0x5678...

# 创建批次备份
python3 scripts/backup_system.py --vault-token dev-root-token batch batch-001 --format both --password mypassword
```

### 7. 监控和管理
```bash
# 获取存款摘要
python3 scripts/deposit_generator.py --vault-token dev-root-token summary 0xf39Fd6e51aad88F6F4ce6aB8827279cffFb92266

# 列出所有备份
python3 scripts/backup_system.py list

# 更新密钥状态
python3 scripts/vault_key_manager.py --vault-token dev-root-token status 0x1234... active --client-type prysm --notes "已激活"
```

## 🔄 典型使用场景

### 场景1：批量生成验证者
```bash
# 1. 生成 10 个密钥
python3 scripts/external_validator_manager.py generate-keys --count 10

# 2. 查看生成的密钥
python3 scripts/vault_key_manager.py --vault-token dev-root-token list --status unused

# 3. 生成存款数据
python3 scripts/deposit_generator.py generate 10 0xf39Fd6e51aad88F6F4ce6aB8827279cffFb92266 --vault-token dev-root-token

# 4. 生成 Prysm 配置
python3 scripts/validator_client_config.py --vault-token dev-root-token prysm --pubkeys $(python3 scripts/vault_key_manager.py --vault-token dev-root-token unused --count 10 | grep -o '0x[0-9a-fA-F]*')
```

### 场景2：按批次管理
```bash
# 1. 查看特定批次的密钥
python3 scripts/vault_key_manager.py --vault-token dev-root-token list --batch-id batch-001

# 2. 为该批次生成存款
python3 scripts/deposit_generator.py generate 5 0xf39Fd6e51aad88F6F4ce6aB8827279cffFb92266 --batch-id batch-001 --vault-token dev-root-token

# 3. 备份该批次
python3 scripts/backup_system.py --vault-token dev-root-token batch batch-001 --format both --password mypassword
```

### 场景3：多客户端支持
```bash
# 1. 获取活跃密钥
python3 scripts/validator_client_config.py --vault-token dev-root-token list-active

# 2. 为不同客户端生成配置
python3 scripts/validator_client_config.py --vault-token dev-root-token prysm --pubkeys 0x1234... 0x5678...
python3 scripts/validator_client_config.py --vault-token dev-root-token lighthouse --pubkeys 0x9abc... 0xdef0...
python3 scripts/validator_client_config.py --vault-token dev-root-token teku --pubkeys 0x1111... 0x2222...

# 3. 或者一次性生成所有配置
python3 scripts/validator_client_config.py --vault-token dev-root-token all --pubkeys 0x1234... 0x5678... 0x9abc... 0xdef0...
```

## 🛡️ 安全最佳实践

### 密钥备份
```bash
# 定期备份所有密钥
python3 scripts/backup_system.py --vault-token dev-root-token batch all --format encrypted --password strong_password

# 备份特定批次的助记词
python3 scripts/backup_system.py --vault-token dev-root-token batch batch-001 --format mnemonic
```

### 密钥状态管理
```bash
# 标记密钥为使用中
python3 scripts/vault_key_manager.py --vault-token dev-root-token status 0x1234... active --client-type prysm --notes "Prysm 验证者"

# 标记密钥为已注销
python3 scripts/vault_key_manager.py --vault-token dev-root-token status 0x1234... retired --notes "已退出网络"
```

### 恢复测试
```bash
# 试运行恢复
python3 scripts/backup_system.py --vault-token dev-root-token restore backup-file.json --dry-run

# 实际恢复
python3 scripts/backup_system.py --vault-token dev-root-token restore backup-file.json --password mypassword
```

## 📋 Commands Reference

### Main Script
```bash
./start.sh [command]
```

Commands:
- `quick-start` - Start infrastructure (Vault, Web3Signer, Kurtosis)
- `external-test` - Run external validator lifecycle test
- `full-test` - Alias for external-test
- `status` - Show service status
- `logs` - Show service logs
- `cleanup` - Stop all services
- `help` - Show help

### 🆕 New Enhanced Scripts

#### Vault Key Manager
```bash
# 列出密钥 (支持多种过滤条件)
python3 scripts/vault_key_manager.py --vault-token dev-root-token list
python3 scripts/vault_key_manager.py --vault-token dev-root-token list --status unused
python3 scripts/vault_key_manager.py --vault-token dev-root-token list --batch-id batch-001
python3 scripts/vault_key_manager.py --vault-token dev-root-token list --client-type prysm
python3 scripts/vault_key_manager.py --vault-token dev-root-token list --created-after 2024-01-01

# 获取指定密钥详情
python3 scripts/vault_key_manager.py --vault-token dev-root-token get 0x1234...

# 更新密钥状态
python3 scripts/vault_key_manager.py --vault-token dev-root-token status 0x1234... active --client-type prysm --notes "已激活"

# 导出密钥
python3 scripts/vault_key_manager.py --vault-token dev-root-token export 0x1234... --format keystore --password mypassword
python3 scripts/vault_key_manager.py --vault-token dev-root-token export 0x1234... --format mnemonic

# 获取未使用的密钥
python3 scripts/vault_key_manager.py --vault-token dev-root-token unused --count 5
python3 scripts/vault_key_manager.py --vault-token dev-root-token unused --batch-id batch-001
```

#### Dynamic Deposit Generator
```bash
# 生成存款 (从 Vault 读取未使用密钥)
python3 scripts/deposit_generator.py --vault-token dev-root-token generate 5 0xf39Fd6e51aad88F6F4ce6aB8827279cffFb92266
python3 scripts/deposit_generator.py --vault-token dev-root-token generate 3 0xf39Fd6e51aad88F6F4ce6aB8827279cffFb92266 --batch-id batch-001 --client-type prysm

# 列出可用密钥
python3 scripts/deposit_generator.py --vault-token dev-root-token list-keys
python3 scripts/deposit_generator.py --vault-token dev-root-token list-keys --batch-id batch-001

# 获取存款摘要
python3 scripts/deposit_generator.py --vault-token dev-root-token summary 0xf39Fd6e51aad88F6F4ce6aB8827279cffFb92266
```

#### Validator Client Config Generator
```bash
# 生成 Prysm 配置
python3 scripts/validator_client_config.py --vault-token dev-root-token prysm --pubkeys 0x1234... 0x5678... --beacon-node http://localhost:3500

# 生成 Lighthouse 配置
python3 scripts/validator_client_config.py --vault-token dev-root-token lighthouse --pubkeys 0x1234... 0x5678... --beacon-node http://localhost:5052

# 生成 Teku 配置
python3 scripts/validator_client_config.py --vault-token dev-root-token teku --pubkeys 0x1234... 0x5678... --beacon-node http://localhost:5051

# 生成所有客户端配置
python3 scripts/validator_client_config.py --vault-token dev-root-token all --pubkeys 0x1234... 0x5678...

# 列出活跃密钥
python3 scripts/validator_client_config.py --vault-token dev-root-token list-active
```

#### Backup System
```bash
# 创建 keystore 备份
python3 scripts/backup_system.py --vault-token dev-root-token keystore 0x1234... 0x5678... --password mypassword

# 创建 mnemonic 备份
python3 scripts/backup_system.py --vault-token dev-root-token mnemonic 0x1234... 0x5678...

# 创建加密备份
python3 scripts/backup_system.py --vault-token dev-root-token encrypted 0x1234... 0x5678... --password mypassword

# 创建批次备份
python3 scripts/backup_system.py --vault-token dev-root-token batch batch-001 --format both --password mypassword

# 从备份恢复
python3 scripts/backup_system.py --vault-token dev-root-token restore backup-file.json --password mypassword
python3 scripts/backup_system.py --vault-token dev-root-token restore backup-file.json --dry-run  # 试运行

# 列出所有备份
python3 scripts/backup_system.py list
```


## 🔧 Configuration

### Infrastructure Configuration
Edit `test_config.json` for external validator settings:

```json
{
  "external_validator_count": 5,
  "withdrawal_address": "0x0000000000000000000000000000000000000001",
  "timeout_activation": 1800,
  "timeout_exit": 1800,
  "monitoring_duration": 600,
  "kurtosis_testnet": {
    "enabled": true,
    "web3_url": "http://localhost:8545",
    "deposit_contract_address": "0x4242424242424242424242424242424242424242",
    "from_address": "0xf39Fd6e51aad88F6F4ce6aB8827279cffFb92266",
    "private_key": "0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80",
    "gas_price": "20000000000",
    "gas_limit": "1000000"
  }
}
```


## 📊 Monitoring & Debugging

### Service URLs
- **Consul UI**: http://localhost:8500
- **Vault UI**: http://localhost:8200 (token: `dev-root-token`)
- **Web3Signer API**: http://localhost:9000
- **PostgreSQL**: localhost:5432 (user: `postgres`, password: `password`, db: `web3signer`)
- **Beacon API**: http://localhost:5052 (varies by Kurtosis mapping)
- **Prometheus**: http://localhost:3000 (if enabled)
- **Grafana**: http://localhost:3001 (if enabled)

### Check Service Status
```bash
# Infrastructure status
./start.sh status

# Docker services
docker ps

# Kurtosis enclaves
kurtosis enclave ls

# Service health checks
curl http://localhost:8200/v1/sys/health
```


### View Logs
```bash
# Infrastructure logs
./start.sh logs

# Individual service logs
docker-compose logs -f vault
docker-compose logs -f postgres
docker-compose logs -f web3signer
kurtosis service logs eth-devnet cl-1-lighthouse-geth
kurtosis service logs eth-devnet cl-2-teku-geth
```

### Troubleshooting

#### Python Dependencies
If you encounter issues with Python packages:
```bash
cd scripts
rm -rf venv/  # Remove existing virtual environment
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```


#### Docker Issues
```bash
docker system prune -f  # Clean up Docker
docker-compose down -v  # Remove volumes
./start.sh cleanup      # Full cleanup
```

#### Path Issues
If you encounter "no configuration file provided: not found" errors:
```bash
# The scripts now automatically detect the correct project root directory
# You can run from either the project root or scripts directory:
python3 scripts/orchestrate.py status  # From project root
cd scripts && python3 orchestrate.py status  # From scripts directory
```

#### Web3Signer Configuration Issues
If Web3Signer fails to start:
```bash
# Check PostgreSQL connection
docker exec -it postgres psql -U postgres -d web3signer -c "SELECT version FROM database_version;"

# Verify database schema
docker exec -it postgres psql -U postgres -d web3signer -c "\dt"

# Reset database if needed
docker-compose down
docker volume rm eth_validator_test_postgres_data
docker-compose up -d
```


## 🔐 Security Notes

- **Development Only**: Uses weak passwords and dev tokens
- **Key Backup**: Always backup generated mnemonics offline
- **Network Isolation**: Services run in isolated Docker networks
- **Vault Dev Mode**: In-memory storage with dev root token
- **Key Generation**: Uses official `ethstaker-deposit-cli` for BLS12-381 key generation and deposit data creation



## 📁 Project Structure

```
eth_validator_test/
├── docker-compose.yml                    # Remote signing stack
├── start.sh                              # Main entry point
├── test_config.json                     # Test configuration
├── ethstaker-deposit-cli/               # Official Ethereum deposit CLI
├── kurtosis/
│   └── kurtosis-config.yaml             # Devnet configuration (built-in validators)
├── vault/
│   ├── config/vault.hcl                 # Vault configuration
│   └── init/admin-policy.hcl            # Vault policies
├── web3signer/
│   ├── config/config.yaml               # Web3Signer configuration
│   ├── keys/                            # External validator keys
│   └── init-db.sh                       # PostgreSQL schema initialization
├── keys/                                # 密钥导出目录
├── deposits/                            # 存款数据目录
├── configs/                             # 验证者客户端配置目录
├── backups/                             # 备份文件目录
└── scripts/
    ├── orchestrate.py                   # Infrastructure orchestration
    ├── external_validator_manager.py    # 🎯 MAIN: Unified validator lifecycle
    ├── generate_keys.py                 # Key generation (ethstaker-deposit-cli)
    ├── key_manager.py                   # Vault key management (legacy)
    ├── deposit_manager.py               # Deposit handling (ethstaker-deposit-cli)
    ├── vault_setup.py                   # Vault initialization
    ├── vault_key_manager.py             # 🆕 核心：Vault 密钥管理 (CRUD + 状态管理)
    ├── deposit_generator.py             # 🆕 核心：动态存款生成 (从 Vault 读取 + 动态提款地址)
    ├── validator_client_config.py       # 🆕 核心：验证者客户端配置生成 (Prysm/Lighthouse/Teku)
    └── backup_system.py                 # 🆕 备份系统 (keystore + mnemonic)
```


## 🎉 新系统功能总结

这个新系统提供了完整的验证者密钥管理解决方案，满足您的所有需求：

### ✅ 核心功能
- **按公钥、批次、生成日期查询**：支持多种维度的密钥查询和过滤
- **支持 Prysm、Lighthouse、Teku**：三种主流验证者客户端全部支持
- **密钥状态管理**：未使用/使用中/已注销三种状态标记
- **支持 keystore 和 mnemonic 备份**：多种备份格式，支持加密保护

### 🏗️ 新架构优势
- **统一管理**：所有密钥操作通过 Vault 统一管理
- **状态跟踪**：完整的密钥生命周期状态管理
- **灵活查询**：支持多种维度的密钥查询和过滤
- **多客户端**：支持所有主流验证者客户端
- **安全备份**：多种备份格式，支持加密保护
- **自动化**：减少手动操作，提高效率

### 📋 使用流程
```
1. 密钥管理 → 2. 存款生成 → 3. 客户端配置 → 4. 验证者运行
```

### 🔑 快速开始
```bash
# 1. 启动基础设施
./start.sh quick-start

# 2. 使用新系统
python3 scripts/vault_key_manager.py --vault-token dev-root-token list
python3 scripts/deposit_generator.py --vault-token dev-root-token generate 3 0xf39Fd6e51aad88F6F4ce6aB8827279cffFb92266
python3 scripts/validator_client_config.py --vault-token dev-root-token prysm --pubkeys 0x1234...
python3 scripts/backup_system.py --vault-token dev-root-token keystore 0x1234... --password mypassword
```

## 📄 License

This project is for educational and testing purposes. Use appropriate security measures for production deployments.