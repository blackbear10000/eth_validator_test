# ETH Validator Workflow Testing System

A comprehensive testing framework for Ethereum validator lifecycle management using Kurtosis, Web3Signer, Vault, and Consul.

## 🎯 Overview

This system validates the full Ethereum validator lifecycle with a **hybrid architecture**:
- **Kurtosis Devnet**: Built-in validators for network stability
- **External Validators**: Web3Signer-managed validators for lifecycle testing
- **Key Management**: HashiCorp Vault for secure key storage with advanced query capabilities
- **Remote Signing**: Web3Signer for external validator operations
- **Lifecycle Testing**: Complete validator onboarding/exit workflows
- **Official Implementation**: Uses `ethstaker-deposit-cli` for BLS12-381 key generation and deposit data creation
- **Multi-Client Support**: Supports Prysm, Lighthouse, and Teku validator clients
- **Advanced Backup**: Supports keystore and mnemonic backup formats

## 🏗️ Architecture

### Hybrid Validator Architecture
- **Kurtosis Built-in Validators**: 2 EL/CL pairs (Geth+Lighthouse, Geth+Teku) with built-in validators
- **External Web3Signer Validators**: Additional validators managed via Web3Signer for testing
  - **Validator Clients**: Independent Lighthouse/Teku validator clients
  - **Remote Signing**: Validator clients connect to Web3Signer for signing operations
  - **Beacon API**: Validator clients connect to Kurtosis beacon no

### Infrastructure Stack
- **Consul** (port 8500): Persistent storage backend for Vault
- **Vault** (port 8200): Secure key storage with KV v2 engine
- **PostgreSQL** (port 5432): Slashing protection database for Web3Signer
- **Web3Signer** (port 9000): Remote signing service for external validators
- **Kurtosis Devnet**: Accelerated testnet with 4s slots for fast testing

### New Enhanced Workflow
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

### Smart Validator Loading
The system automatically handles validator loading:
- **Auto-loading**: Commands automatically load validators from Vault if not in memory
- **No manual step needed**: You can directly run `create-deposits` without `load-validators`
- **Manual loading**: Use `load-validators` only for debugging or explicit control
- **Flexible workflow**: Can start from any step (generate-keys or create-deposits)

### Key Injection Process
- **Vault**: Stores BLS private keys securely
- **Web3Signer**: Loads keys from Vault, provides signing API
- **Validator Client**: Connects to Web3Signer for signing operations
- **Beacon API**: Provides network state and validator duties

## 🚀 Quick Start

### Prerequisites
- Docker & Docker Compose
- [Kurtosis CLI](https://docs.kurtosis.com/install)
- Python 3.8+
- Git (for ethstaker-deposit-cli integration)

### 🆕 Latest Updates (ethstaker-deposit-cli Integration)

The system now uses the **official Ethereum Foundation implementation**:
- ✅ **Real BLS12-381**: Official elliptic curve operations (no more simplified implementations)
- ✅ **Official SSZ**: Standard serialization for deposit data
- ✅ **Production Ready**: Cryptographically valid signatures and deposit data
- ✅ **Multi-Network**: Supports mainnet, testnets, and devnet configurations
- ✅ **Clean Architecture**: Removed all test key folders, streamlined project structure

### Key Changes
1. **Official Implementation**: All key generation and deposit data creation now uses `ethstaker-deposit-cli`
2. **Unified Workflow**: Single entry point (`external_validator_manager.py`) for complete lifecycle
3. **Simplified Architecture**: Removed duplicate/conflicting management scripts
4. **Clean Project Structure**: Removed temporary test folders and files
5. **Production Standards**: Generated data is ready for real Ethereum networks

### 🎯 Unified Architecture

The system now uses a **unified architecture** with clear separation of concerns:

- **`external_validator_manager.py`**: Main orchestrator for complete validator lifecycle
- **`key_manager.py`**: Vault operations (store, retrieve, list, cleanup)
- **`deposit_manager.py`**: Deposit data generation and submission
- **`generate_keys.py`**: Official BLS12-381 key generation using ethstaker-deposit-cli

**Removed Scripts** (consolidated into main workflow):
- ❌ `deposit_cli_wrapper.py` - Replaced by direct ethstaker-deposit-cli integration
- ❌ `external_validator_client.py` - Simplified to manual setup instructions
- ❌ `validator_lifecycle.py` - Integrated into external_validator_manager.py
- ❌ `web3signer_key_manager.py` - Functionality moved to key_manager.py

### Two-Phase Workflow

#### Phase 1: Infrastructure Setup
```bash
# Start infrastructure (Vault, Web3Signer, Kurtosis devnet)
./start.sh quick-start
```

#### Phase 2: External Validator Testing
```bash
# Run complete external validator lifecycle test
./start.sh external-test
```

### Step-by-Step External Validator Management
```bash
# 1. Start infrastructure first
./start.sh quick-start

# 2. Run external validator phases
source scripts/venv/bin/activate

# Check service status
python3 scripts/external_validator_manager.py check-services

# Generate external validator keys
python3 scripts/external_validator_manager.py generate-keys --count 5

# Create and submit deposits (auto-loads from Vault if needed)
python3 scripts/external_validator_manager.py submit-deposits

# Start external validator clients (connects to Web3Signer)
python3 scripts/external_validator_manager.py start-clients

# Wait for activation
python3 scripts/external_validator_manager.py wait-activation

# Monitor performance
python3 scripts/external_validator_manager.py monitor

# Test voluntary exit
python3 scripts/external_validator_manager.py test-exit

# Test withdrawal process
python3 scripts/external_validator_manager.py test-withdrawal
```

### Flexible Workflow Options

The system supports multiple workflow patterns:

#### Option 1: Complete Flow (Recommended)
```bash
# Generate keys and create deposits in one go
python3 scripts/external_validator_manager.py generate-keys --count 5
python3 scripts/external_validator_manager.py create-deposits
```

#### Option 2: Resume from Existing Keys
```bash
# Create deposits directly (auto-loads from Vault)
python3 scripts/external_validator_manager.py create-deposits
```

#### Option 3: Debug/Manual Control
```bash
# Manually load validators (for debugging or explicit control)
python3 scripts/external_validator_manager.py load-validators
python3 scripts/external_validator_manager.py create-deposits
```

### Cleanup
```bash
./start.sh cleanup
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
python3 scripts/vault_key_manager.py list
python3 scripts/vault_key_manager.py list --status unused
python3 scripts/vault_key_manager.py list --batch-id batch-001
python3 scripts/vault_key_manager.py list --client-type prysm
python3 scripts/vault_key_manager.py list --created-after 2024-01-01

# 获取指定密钥详情
python3 scripts/vault_key_manager.py get 0x1234...

# 更新密钥状态
python3 scripts/vault_key_manager.py status 0x1234... active --client-type prysm --notes "已激活"

# 导出密钥
python3 scripts/vault_key_manager.py export 0x1234... --format keystore --password mypassword
python3 scripts/vault_key_manager.py export 0x1234... --format mnemonic

# 获取未使用的密钥
python3 scripts/vault_key_manager.py unused --count 5
python3 scripts/vault_key_manager.py unused --batch-id batch-001
```

#### Dynamic Deposit Generator
```bash
# 生成存款 (从 Vault 读取未使用密钥)
python3 scripts/deposit_generator.py generate 5 0xf39Fd6e51aad88F6F4ce6aB8827279cffFb92266
python3 scripts/deposit_generator.py generate 3 0xf39Fd6e51aad88F6F4ce6aB8827279cffFb92266 --batch-id batch-001 --client-type prysm

# 列出可用密钥
python3 scripts/deposit_generator.py list-keys
python3 scripts/deposit_generator.py list-keys --batch-id batch-001

# 获取存款摘要
python3 scripts/deposit_generator.py summary 0xf39Fd6e51aad88F6F4ce6aB8827279cffFb92266
```

#### Validator Client Config Generator
```bash
# 生成 Prysm 配置
python3 scripts/validator_client_config.py prysm --pubkeys 0x1234... 0x5678... --beacon-node http://localhost:3500

# 生成 Lighthouse 配置
python3 scripts/validator_client_config.py lighthouse --pubkeys 0x1234... 0x5678... --beacon-node http://localhost:5052

# 生成 Teku 配置
python3 scripts/validator_client_config.py teku --pubkeys 0x1234... 0x5678... --beacon-node http://localhost:5051

# 生成所有客户端配置
python3 scripts/validator_client_config.py all --pubkeys 0x1234... 0x5678...

# 列出活跃密钥
python3 scripts/validator_client_config.py list-active
```

#### Backup System
```bash
# 创建 keystore 备份
python3 scripts/backup_system.py keystore 0x1234... 0x5678... --password mypassword

# 创建 mnemonic 备份
python3 scripts/backup_system.py mnemonic 0x1234... 0x5678...

# 创建加密备份
python3 scripts/backup_system.py encrypted 0x1234... 0x5678... --password mypassword

# 创建批次备份
python3 scripts/backup_system.py batch batch-001 --format both --password mypassword

# 从备份恢复
python3 scripts/backup_system.py restore backup-file.json --password mypassword
python3 scripts/backup_system.py restore backup-file.json --dry-run  # 试运行

# 列出所有备份
python3 scripts/backup_system.py list
```

### Infrastructure Management
```bash
# Start infrastructure
python3 scripts/orchestrate.py start-infra

# Check status
python3 scripts/orchestrate.py status

# Cleanup
python3 scripts/orchestrate.py cleanup
```

### External Validator Management
```bash
# Check services
python3 scripts/external_validator_manager.py check-services

# Generate keys
python3 scripts/external_validator_manager.py generate-keys --count 5

# Create deposits (auto-loads from Vault if needed)
python3 scripts/external_validator_manager.py create-deposits

# Note: load-validators is optional - only needed for debugging

# Submit deposits
python3 scripts/external_validator_manager.py submit-deposits

# Start validator clients
python3 scripts/external_validator_manager.py start-clients

# Wait for activation
python3 scripts/external_validator_manager.py wait-activation

# Monitor validators
python3 scripts/external_validator_manager.py monitor

# Test exit
python3 scripts/external_validator_manager.py test-exit

# Test withdrawal
python3 scripts/external_validator_manager.py test-withdrawal

# Full test
python3 scripts/external_validator_manager.py full-test

# Cleanup
python3 scripts/external_validator_manager.py cleanup
```

### Unified Workflow (Recommended)

The system now uses a **unified workflow** centered around `external_validator_manager.py`:

#### Complete Validator Lifecycle
```bash
# 1. Generate keys and store in Vault
python3 scripts/external_validator_manager.py generate-keys --count 5

# 2. Create and submit deposits
python3 scripts/external_validator_manager.py submit-deposits

# 3. Start validator clients (manual setup required)
python3 scripts/external_validator_manager.py start-clients

# 4. Monitor activation and performance
python3 scripts/external_validator_manager.py wait-activation
python3 scripts/external_validator_manager.py monitor

# 5. Test exit and withdrawal
python3 scripts/external_validator_manager.py test-exit
python3 scripts/external_validator_manager.py test-withdrawal
```

#### Key Management (Vault Operations)
```bash
# List all keys (including deleted)
python3 scripts/key_manager.py list

# List only active keys (skip deleted, quiet mode)
python3 scripts/key_manager.py list-active

# Permanently destroy deleted keys
python3 scripts/key_manager.py destroy-deleted

# Debug: Show detailed status of all keys
python3 scripts/key_manager.py debug-status

# Clean corrupted keys
python3 scripts/key_manager.py clean-corrupted
```

#### Direct Deposit Management (Advanced)
```bash
# Generate deposit data directly
python3 scripts/deposit_manager.py \
  --keys-file ./external_keys/keys_data.json \
  --withdrawal-address 0xf39Fd6e51aad88F6F4ce6aB8827279cffFb92266 \
  --network devnet \
  --output-file deposits.json

# Submit deposits to Kurtosis testnet
python3 scripts/deposit_manager.py \
  --keys-file ./external_keys/keys_data.json \
  --withdrawal-address 0xf39Fd6e51aad88F6F4ce6aB8827279cffFb92266 \
  --network devnet \
  --output-file deposits.json \
  --submit \
  --config-file test_config.json
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

### Kurtosis Testnet Integration

The system now supports real deposit submission to Kurtosis testnets:

#### Features
- **Real Network Submission**: Submit deposits to actual Kurtosis testnet
- **Pre-funded Account**: Uses `0xf39Fd6e51aad88F6F4ce6aB8827279cffFb92266` with 10000 ETH
- **Automatic Validation**: Validates deposits before submission
- **Transaction Tracking**: Shows transaction hashes and confirmation status

#### Configuration
Enable Kurtosis testnet submission in `test_config.json`:
```json
{
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

#### Usage
```bash
# Create and submit deposits to Kurtosis testnet
python3 scripts/external_validator_manager.py submit-deposits

# Or run full test with real submission
python3 scripts/external_validator_manager.py full-test
```

### Kurtosis Configuration
Edit `kurtosis/kurtosis-config.yaml` for devnet settings:

```yaml
network_params:
  seconds_per_slot: 4
  eth1_follow_distance: 16
  churn_limit_quotient: 32
  max_per_epoch_activation_churn_limit: 64
  num_validator_keys_per_node: 8
  withdrawal_type: "0x01"
  genesis_delay: 90
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

### Key Management

#### List All Keys
```bash
# List keys in Vault and local files
python3 scripts/external_validator_manager.py list-keys

# List keys using KeyManager
python3 scripts/key_manager.py list

# Load validators from Vault (for debugging only)
python3 scripts/external_validator_manager.py load-validators
```

#### Vault Key Operations
```bash
# Import keys to Vault
python3 scripts/key_manager.py import --keys-dir ./external_keys

# Export keys for Web3Signer
python3 scripts/key_manager.py export --output-dir ./web3signer/keys

# List all keys (including deleted)
python3 scripts/key_manager.py list

# List only active keys (skip deleted, quiet mode)
python3 scripts/key_manager.py list-active

# Permanently destroy deleted keys
python3 scripts/key_manager.py destroy-deleted

# Debug: Show detailed status of all keys
python3 scripts/key_manager.py debug-status

# Clean corrupted keys
python3 scripts/key_manager.py clean-corrupted

# Direct Web3Signer health checks
curl http://localhost:9000/upcheck
curl http://localhost:9000/healthcheck/slashing-protection
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

#### ethstaker-deposit-cli Integration
The system now uses the official `ethstaker-deposit-cli` repository:
- **Automatic Integration**: The repository is included in the project
- **Official Implementation**: Uses real BLS12-381 cryptographic operations
- **Production Ready**: Generates cryptographically valid deposit data
- **No Fallback**: No simplified implementation, only official standards

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

#### Vault Key Management Issues
If you encounter "Failed to retrieve key" errors:
```bash
# Check for deleted keys (shows all keys including deleted)
python3 scripts/key_manager.py list

# List only active keys (quiet mode, no error messages)
python3 scripts/key_manager.py list-active

# List active keys with detailed info about deleted keys
python3 scripts/key_manager.py list-active --verbose

# Permanently destroy deleted keys (with progress output)
python3 scripts/key_manager.py destroy-deleted

# Destroy deleted keys quietly (minimal output)
python3 scripts/key_manager.py destroy-deleted --quiet

# Debug: Check detailed status of all keys
python3 scripts/key_manager.py debug-status

# Advanced debug: Show comprehensive key information
python3 scripts/key_manager.py debug-advanced

# Clean corrupted keys (metadata exists but data is inaccessible)
python3 scripts/key_manager.py clean-corrupted

# Clear all keys (auto-destroys deleted keys first)
python3 scripts/key_manager.py destroy-deleted --quiet
```

#### BLS12-381 Key Length Issues
The system now generates proper 48-byte BLS12-381 keys using `ethstaker-deposit-cli`:
```bash
# All keys are now generated with official BLS12-381 implementation
# No more "Invalid pubkey length" errors
python3 scripts/external_validator_manager.py generate-keys --count 5
```

#### Common Key Management Issues

**Problem**: "Failed to retrieve key" errors
```bash
# Solution: Use quiet mode commands that don't trigger errors
python3 scripts/key_manager.py list-active

# Or clean up deleted keys
python3 scripts/key_manager.py destroy-deleted --quiet
```

**Problem**: "Invalid pubkey length" errors
```bash
# Solution: All keys are now generated with official BLS12-381 implementation
# This error should no longer occur with ethstaker-deposit-cli integration
python3 scripts/external_validator_manager.py generate-keys --count 5
```

**Problem**: Keys not loading in external validator manager
```bash
# Solution: Check active keys and reload
python3 scripts/key_manager.py list-active
python3 scripts/external_validator_manager.py load-validators
```

## 🔐 Security Notes

- **Development Only**: Uses weak passwords and dev tokens
- **Key Backup**: Always backup generated mnemonics offline
- **Network Isolation**: Services run in isolated Docker networks
- **Vault Dev Mode**: In-memory storage with dev root token
- **Key Generation**: Uses official `ethstaker-deposit-cli` for BLS12-381 key generation and deposit data creation

### Key Generation Implementation

#### Official ethstaker-deposit-cli (Current)
- **Repository**: Integrated from [ethereum/staking-deposit-cli](https://github.com/ethereum/staking-deposit-cli)
- **Implementation**: Full BLS12-381 cryptographic operations
- **Standards**: EIP-2335 compliant keystores and SSZ serialization
- **Security**: Production-ready with official Ethereum Foundation implementation
- **Features**: 
  - Real BLS12-381 elliptic curve operations
  - Official SSZ deposit data serialization
  - Cryptographically valid signatures
  - Multi-network support (mainnet, testnets, devnet)

The system now exclusively uses the official implementation for all key generation and deposit data creation.

### Vault Key Management

The system includes robust key management features:

#### Key States
- **Active**: Keys that are stored and accessible
- **Deleted**: Keys marked for deletion but not yet destroyed (Vault soft delete)
- **Destroyed**: Keys permanently removed from Vault

#### Key Operations
- **Auto-loading**: Commands automatically skip deleted keys
- **Cleanup tools**: `destroy-deleted` command permanently removes deleted keys
- **Smart listing**: `list-active` shows only accessible keys
- **Bulk operations**: `remove --all` auto-destroys deleted keys before removal

## 🧪 Validation Checklist

The system validates:
- ✅ **Kurtosis Devnet**: Built-in validators provide network stability
- ✅ **Vault Integration**: Securely stores/retrieves BLS keys for external validators
- ✅ **Web3Signer Integration**: Loads keys via HashiCorp Vault with slash protection
- ✅ **PostgreSQL Database**: Slashing protection database with proper schema
- ✅ **Unified Workflow**: Single entry point for complete validator lifecycle
- ✅ **Official Implementation**: Uses ethstaker-deposit-cli for BLS12-381 and SSZ
- ✅ **Deposit Flow**: Generation, submission, and activation
- ✅ **Remote Signing**: External validators sign via Web3Signer
- ✅ **Accelerated Testing**: 4s slots for fast validation cycles
- ✅ **Smart Key Loading**: Auto-loads validators from Vault when needed
- ✅ **Vault Key Management**: Full CRUD operations with cleanup tools
- ✅ **BLS12-381 Compliance**: Generates proper 48-byte validator keys
- ✅ **Simplified Architecture**: Removed duplicate/conflicting management scripts

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

## 🤝 Contributing

1. Test changes with `./start.sh external-test`
2. Ensure all validation checklist items pass
3. Update documentation for new features
4. Follow existing code patterns and error handling

## 📄 License

This project is for educational and testing purposes. Use appropriate security measures for production deployments.