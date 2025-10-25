# ETH Validator Testing System

Comprehensive Ethereum validator lifecycle management using Kurtosis, Web3Signer, and Vault with official `ethstaker-deposit-cli` integration.

## 🚀 Quick Start

### One-Time Setup
```bash
# Clone and setup
git clone <your-repository-url> && cd eth_validator_test
git submodule update --init --recursive
mkdir config
cp config.sample.json config/config.json

# Install dependencies
cd code && python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cd external/ethstaker-deposit-cli && pip install -r requirements.txt
cd ../../..
export VAULT_TOKEN=dev-root-token
```

### Deploy Your First Validators (New Bulk Workflow)
```bash
# 1. Start infrastructure
./validator.sh start

# 2. Initialize key pool (generate 10 keys upfront)
./validator.sh init-pool --count 10

# 3. Activate first batch of validators
./validator.sh activate-keys --count 4

# 4. Create deposits (uses only active keys) - NEW CONSISTENT WORKFLOW
# Option A: Use consistent workflow (recommended)
./validator.sh consistent-workflow --count 4 --fork-version 0x10000038

# Option B: Manual steps (ensure consistency)
./validator.sh create-deposits-for-active-keys --fork-version 0x10000038 --count 4 --withdrawal-address 0x8943545177806ED17B9F23F0a21ee5948eCaa776

# 5. Validate deposits (optional)
./validator.sh validate-deposits

# 6. Submit to network
./validator.sh submit-deposits

# 7. Monitor
./validator.sh monitor

./validator.sh start-validator prysm

# 8. Later, activate more validators as needed
./validator.sh activate-keys --count 10
./validator.sh create-deposits
./validator.sh submit-deposits
```

## 📋 Common Scenarios

### Scenario 1: Deploy 50 Validators (New Bulk Workflow)
```bash
./validator.sh start
./validator.sh init-pool --count 1000  # Generate 1000 keys upfront
./validator.sh consistent-workflow --count 50 --fork-version 0x10000038  # Activate keys + create deposits
./validator.sh list-keys  # Get pubkeys for backup
./validator.sh backup mnemonic 0x1234... 0x5678... --name batch-50
# Review deposit_data.json
./validator.sh validate-deposits  # Validate using ethstaker-deposit-cli
./validator.sh submit-deposits
```

### Scenario 2: Add More Validators Later
```bash
# Option A: Use consistent workflow (recommended)
./validator.sh consistent-workflow --count 10 --fork-version 0x10000038

# Option B: Manual steps
./validator.sh activate-keys --count 10
./validator.sh create-deposits-for-active-keys --fork-version 0x10000038 --count 10
./validator.sh submit-deposits
```

### Scenario 2.1: Clean and Start Fresh
```bash
# Clean all existing keys and start fresh
./validator.sh clean
./validator.sh init-pool --count 1000  # Initialize new pool
./validator.sh consistent-workflow --count 5 --fork-version 0x10000038  # Activate + create deposits
./validator.sh submit-deposits
```

### Scenario 2.2: Small Test Setup
```bash
# For testing with smaller key pools
./validator.sh init-pool --count 10    # Generate only 10 keys
./validator.sh consistent-workflow --count 3 --fork-version 0x10000038  # Activate 3 keys + create deposits
./validator.sh submit-deposits
```

### Scenario 3: Backup Everything
```bash
# List all keys first
./validator.sh list-keys

# Backup specific keys (replace with actual pubkeys)
./validator.sh backup mnemonic 0x1234... 0x5678... --name full-backup

# Or backup by batch
./validator.sh backup batch batch-20241021 --format both
```

### Scenario 4: Restore from Backup
```bash
# Restore from backup file
./validator.sh backup restore /secure/backup/full-backup.zip --password your-password

# Or restore from keystore backup
./validator.sh backup restore /secure/backup/keystore-backup.zip --password keystore-password
```

### Scenario 5: Dynamic Withdrawal Address
```bash
# Generate keys without withdrawal address binding
./validator.sh generate-keys --count 5

# Create deposits with different withdrawal addresses
./validator.sh create-deposits-with-address --withdrawal-address 0x8943545177806ED17B9F23F0a21ee5948eCaa776
```

### Scenario 6: Kurtosis Fork Version Compatibility
```bash
# Auto-detect Kurtosis fork version and create compatible deposits
./validator.sh create-deposits-with-fork-version --auto-detect

# Manual fork version specification (if you know the exact version)
./validator.sh create-deposits-with-fork-version --fork-version 0x10000038 --count 10 --withdrawal-address 0x8943545177806ED17B9F23F0a21ee5948eCaa776

# Verify fork version compatibility
python3 scripts/detect_kurtosis_fork_version.py
```

### Scenario 7: Start Validator Client with Web3Signer (Kurtosis Compatible)
```bash
# 1. Detect Kurtosis network ports dynamically
./validator.sh detect-kurtosis-ports

# 2. Check all services are running (including Kurtosis)
./validator.sh check-services

# 3. Load keys to Web3Signer
./validator.sh load-keys

# 4. Start validator client (auto-detects Kurtosis ports)


# 5. Monitor validator performance
./validator.sh monitor

# Alternative: Start Lighthouse validator
./validator.sh start-validator lighthouse

# Alternative: Start Teku validator  
./validator.sh start-validator teku
```

## 🎯 Command Reference

### Infrastructure Commands
```bash
./validator.sh start          # Start all services
./validator.sh stop           # Stop all services
./validator.sh status         # Check status
```

### Key Management
```bash
./validator.sh generate-keys  # Generate new keys (legacy mode)
./validator.sh init-pool      # Initialize key pool (bulk generation)
./validator.sh activate-keys  # Activate keys from pool
./validator.sh pool-status    # Check key pool status
./validator.sh list-keys      # List all keys
./validator.sh backup         # Backup keys
./validator.sh clean         # Clean all keys (local files and Vault)
```

### Deposit Operations
```bash
./validator.sh consistent-workflow --count 4 --fork-version 0x10000038  # NEW: Consistent workflow (activate keys + create deposits)
./validator.sh create-deposits-for-active-keys --fork-version 0x10000038 --count 4  # NEW: Create deposits for active keys only
./validator.sh check-active-keys  # NEW: Check status of active keys
./validator.sh check-workflow-status  # NEW: Check overall workflow status
./validator.sh create-deposits                    # Create deposit data for ACTIVE keys only (uses custom kurtosis network config)
./validator.sh create-deposits-with-fork-version --auto-detect  # Auto-detect Kurtosis fork version and create deposits
./validator.sh create-deposits-with-fork-version --fork-version 0x10000038  # Create deposits with custom fork version
./validator.sh create-deposits-with-address --withdrawal-address 0xf39Fd6e51aad88F6F4ce6aB8827279cffFb92266  # Create with custom withdrawal address
./validator.sh validate-deposits                  # Validate deposit data using ethstaker-deposit-cli
./validator.sh submit-deposits                    # Submit existing deposit_data.json to network (auto-copied to standard location)
```

### Validator Client Operations
```bash
./validator.sh detect-kurtosis-ports  # Detect Kurtosis network ports dynamically
./validator.sh check-services        # Check all services status
./validator.sh check-clients         # Check validator client installation status
./validator.sh install-commands     # Show installation commands for clients
./validator.sh start-validator prysm        # Start Prysm validator client
./validator.sh start-validator lighthouse  # Start Lighthouse validator client
./validator.sh start-validator teku        # Start Teku validator client
./validator.sh start-validator prysm --config-only  # Generate config only
```

### Monitoring & Testing
```bash
./validator.sh monitor        # Monitor validators
./validator.sh test-import    # Test Vault key import
./validator.sh diagnose-web3signer  # Diagnose Web3Signer connection issues
./validator.sh debug-web3signer-connection  # NEW: Detailed Web3Signer connection analysis
./validator.sh analyze-prysm-web3signer  # NEW: Analyze Prysm-Web3Signer connection issues
./validator.sh fix-web3signer-connection  # NEW: Auto-fix Web3Signer connection problems
./validator.sh restart-web3signer  # NEW: Restart Web3Signer service
./validator.sh test-haproxy        # Test HAProxy configuration
./validator.sh test-web3signer-startup  # Test Web3Signer startup without keys
./validator.sh validate-deposits  # Validate deposit data using ethstaker-deposit-cli
```

### Quick Deploy
```bash
./validator.sh deploy         # Run full deployment workflow
```

## 🏗️ Architecture

### Infrastructure Stack
- **Vault** (port 8200): Secure key storage with KV v2 engine
- **PostgreSQL** (port 5432): Slashing protection database for Web3Signer
- **Web3Signer** (ports 9000, 9001): Dual remote signing services for high availability
- **HAProxy** (port 9002): Load balancer for Web3Signer instances
- **Kurtosis Devnet**: Accelerated testnet with 4s slots for fast testing

### High Availability Architecture
- **Dual Web3Signer**: Two instances sharing one PostgreSQL database
- **Zero-downtime key management**: Add/remove keys without service interruption
- **Automatic failover**: HAProxy handles instance failures gracefully
- **Bulk key generation**: Pre-generate large pools of keys for instant activation

### Workflow
```
1. Key Generation → 2. Deposit Creation → 3. Client Configuration → 4. Validator Operation
```

## 🔑 Key Consistency & Workflow

### ⚠️ Important: Key Consistency Issue

**Problem**: The original workflow had a critical inconsistency:
- `activate-keys` activates keys from the pool → stores in Vault → syncs to Web3Signer
- `create-deposits-with-fork-version` generates NEW keys → creates deposit data

This results in **different keys** being used for validation vs. deposit submission!

### ✅ Solution: Consistent Workflow

**New Recommended Workflow:**
```bash
# Option 1: One-command consistent workflow (RECOMMENDED)
./validator.sh consistent-workflow --count 4 --fork-version 0x10000038

# Option 2: Manual consistent steps
./validator.sh activate-keys --count 4
./validator.sh create-deposits-for-active-keys --fork-version 0x10000038 --count 4
```

**Key Benefits:**
- ✅ **Same keys**: Activated keys and deposit data use identical key pairs
- ✅ **State validation**: Each step verifies the previous step completed successfully
- ✅ **Error handling**: Fails fast if insufficient keys or other issues
- ✅ **Status checking**: Built-in status verification at each step

### 🔍 Workflow Status Checking

```bash
# Check overall workflow status
./validator.sh check-workflow-status

# Check active keys status
./validator.sh check-active-keys

# Check key pool status
./validator.sh pool-status
```

## 🔧 Advanced Usage

### Key Management
```bash
# List all keys in Vault
cd code && source venv/bin/activate
python3 core/vault_key_manager.py --vault-token dev-root-token list

# Query keys by status
python3 core/vault_key_manager.py --vault-token dev-root-token list --status unused

# Export keys for backup
python3 core/backup_system.py keystore 0x1234... --password mypassword
```

### Deposit Generation
```bash
# Generate deposits from Vault keys
cd code && source venv/bin/activate
python3 utils/deposit_generator.py --vault-token dev-root-token generate 3 0xf39Fd6e51aad88F6F4ce6aB8827279cffFb92266

# List available keys
python3 utils/deposit_generator.py --vault-token dev-root-token list-keys

# Create deposits with custom fork version
python3 scripts/create_deposits_with_fork_version.py --fork-version 0x10000038 --count 5

# Auto-detect Kurtosis fork version
python3 scripts/create_deposits_with_fork_version.py --auto-detect

# Detect and configure fork version
python3 scripts/detect_kurtosis_fork_version.py --fork-version 0x10000038
```

### Deposit Validation
```bash
# Validate deposit data using ethstaker-deposit-cli
cd code && source venv/bin/activate
python3 utils/validate_deposits_standalone.py ../data/deposits/deposit_data.json

# Validate with specific network
python3 utils/validate_deposits_standalone.py ../data/deposits/deposit_data.json --network sepolia
```

### Deposit Submission
```bash
# Submit deposits to network (Kurtosis devnet)
cd code && source venv/bin/activate
python3 utils/deposit_submitter.py ../data/deposits/deposit_data.json

# Submit with custom config
python3 utils/deposit_submitter.py ../data/deposits/deposit_data.json --config ../config/config.json
```

### Client Configuration
```bash
# Generate Prysm configuration
cd code && source venv/bin/activate
python3 utils/validator_client_config.py prysm --pubkeys 0x1234... 0x5678...

# Generate Lighthouse configuration
python3 utils/validator_client_config.py lighthouse --pubkeys 0x1234... 0x5678...

# Generate all client configurations
python3 utils/validator_client_config.py all --pubkeys 0x1234... 0x5678...
```

## 📋 Commands Reference

### Main Script
```bash
./start.sh [command]
```

**Commands:**
- `quick-start` - Start infrastructure (Vault, Web3Signer, Kurtosis)
- `external-test` - Run external validator lifecycle test
- `full-test` - Alias for external-test
- `status` - Show service status
- `logs` - Show service logs
- `cleanup` - Stop all services
- `help` - Show help

### External Validator Manager
```bash
cd code && source venv/bin/activate
python3 core/validator_manager.py [command]
```

**Commands:**
- `check-services` - Check if all services are running
- `generate-keys` - Generate validator keys
- `list-keys` - List stored keys
- `create-deposits` - Create deposit data
- `create-deposits-with-address` - Create deposit data with custom withdrawal address
- `validate-deposits` - Validate deposit data using ethstaker-deposit-cli
- `submit-deposits` - Submit deposits to network
- `monitor` - Monitor validator performance
- `test-import` - Test Vault key import
- `clean` - Clean all keys (local files and Vault)
- `test-exit` - Test voluntary exit
- `full-test` - Run complete lifecycle test

## 🔐 Configuration

### Infrastructure Configuration
The system uses a sample configuration file that you need to copy and customize:

```bash
# Copy sample configuration to config directory
cp config.sample.json config/config.json

# Edit the configuration file
vim config/config.json
```

**Important Notes:**
- `config.sample.json` is tracked by git and contains safe default values
- `config/config.json` is ignored by git and contains your actual configuration
- Always copy from the sample file to create your runtime configuration

Edit `config/config.json` for external validator settings:

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
```

## 🛠️ Troubleshooting

### Git Submodules
If you encounter issues with missing dependencies or external modules:

**Common Issues:**
- `ethstaker-deposit-cli` module not found
- Import errors for external dependencies
- Missing files in `code/external/` directory

**Solutions:**
```bash
# Update all submodules
git submodule update --init --recursive

# If submodules are out of sync
git submodule sync --recursive
git submodule update --init --recursive

# Force update submodules (if needed)
git submodule update --init --recursive --force

# Check submodule status
git submodule status
```

### Python Dependencies
```bash
cd code
rm -rf venv/
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

### Docker Issues
```bash
docker system prune -f
docker-compose down -v
./start.sh cleanup
```

### Key Management Issues

#### File Exists Errors
If you encounter `[Errno 17] File exists` errors during key generation:

```bash
# Solution 1: Clean and regenerate
./validator.sh clean
./validator.sh generate-keys --count 5

# Solution 2: The system now automatically cleans old files
./validator.sh generate-keys --count 5  # Will auto-clean existing files
```

#### Vault Import Failures
If keys are generated locally but not imported to Vault:

```bash
# Test single key import
./validator.sh test-import

# Check Vault status
./validator.sh list-keys

# Manual Vault import test
cd code && source venv/bin/activate
python3 core/vault_key_manager.py --vault-token dev-root-token list
```

#### No Keys Found in Vault
If `create-deposits` fails with "No valid validator keys found in Vault":

```bash
# 1. Check if keys exist locally
./validator.sh list-keys

# 2. If local keys exist but Vault is empty, re-import
./validator.sh clean  # Clean everything
./validator.sh generate-keys --count 5  # Regenerate and import

# 3. Verify Vault import
./validator.sh test-import
```

### Web3Signer Configuration Issues
```bash
# Check Web3Signer health
curl http://localhost:9000/upcheck

# Check Web3Signer keys
curl http://localhost:9000/api/v1/eth2/publicKeys

# Check PostgreSQL connection
docker exec -it postgres psql -U postgres -d web3signer -c "SELECT version FROM database_version;"

# Reset database if needed
docker-compose down
docker volume rm eth_validator_test_postgres_data
docker-compose up -d
```

### Web3Signer Integration
```bash
# Load keys to Web3Signer
./validator.sh load-keys

# Check Web3Signer status
./validator.sh web3signer-status

# Verify keys are loaded
./validator.sh verify-keys

# Run Web3Signer diagnostic tool
python3 scripts/debug_web3signer.py

# Check Web3Signer logs
docker logs web3signer

# Check Vault connection from Web3Signer
docker exec web3signer curl http://vault:8200/v1/sys/health
```

### Web3Signer Workflow

#### 快速部署（推荐）
```bash
# 一键完整部署
./validator.sh web3signer-deploy --count 5 --client prysm

# 检查系统状态
./validator.sh web3signer-status

# 故障排除
./validator.sh web3signer-troubleshoot
```

### Kurtosis 网络集成

#### 网络配置
项目默认配置为 Kurtosis 测试网络：
- **网络类型**: `kurtosis` (基于 minimal 预设)
- **网络 ID**: `3151908`
- **存款合约**: `0x4242424242424242424242424242424242424242`
- **退出类型**: `0x01` (自动提款)

#### 存款数据生成
```bash
# 为 Kurtosis 网络生成存款数据（自动检测 fork version）
./validator.sh create-deposits-with-fork-version --auto-detect

# 手动指定 fork version（如果已知确切版本）
./validator.sh create-deposits-with-fork-version --fork-version 0x10000038

# 传统方式（使用默认配置）
./validator.sh create-deposits

# 验证存款数据
./validator.sh validate-deposits

# 提交到 Kurtosis 网络
./validator.sh submit-deposits
```

#### 手动步骤
1. **Generate Keys**: `./validator.sh generate-keys --count 5`
2. **Load to Web3Signer**: `./validator.sh load-keys`
3. **Verify Loading**: `./validator.sh verify-keys`
4. **Start Validator**: `./validator.sh start`

#### 支持的客户端
- **Prysm**: `./validator.sh web3signer-deploy --client prysm`
- **Lighthouse**: `./validator.sh web3signer-deploy --client lighthouse`
- **Teku**: `./validator.sh web3signer-deploy --client teku`

### 故障排除

#### 数据库问题
```bash
# 修复 PostgreSQL 数据库问题
./validator.sh fix-database

# 修复数据库版本问题（推荐）
./validator.sh fix-database-version

# 完全重置数据库
./validator.sh reset-database

# 手动检查数据库状态
docker exec postgres psql -U postgres -d web3signer -c "\\dt"

# 手动完全重置数据库
docker-compose down
docker volume rm postgres_data
docker-compose up -d
```

#### Web3Signer 连接问题
```bash
# 检查 Web3Signer 状态
./validator.sh web3signer-status

# 详细诊断 Web3Signer 连接问题
./validator.sh debug-web3signer-connection

# 分析 Prysm-Web3Signer 连接问题
./validator.sh analyze-prysm-web3signer

# 自动修复 Web3Signer 连接问题
./validator.sh fix-web3signer-connection

# 重启 Web3Signer 服务
./validator.sh restart-web3signer

# 检查 Web3Signer 日志
docker logs web3signer
```

#### 常见 Web3Signer 错误及解决方案

**错误**: `"failed to sign the request: http: ContentLength=391 with Body length 0"`

**原因**: HTTP 请求头与实际请求体长度不匹配，通常是 Prysm 与 Web3Signer 通信问题

**解决方案**:
```bash
# 1. 详细诊断
./validator.sh analyze-prysm-web3signer

# 2. 检查 Web3Signer 健康状态
curl http://localhost:9000/upcheck

# 3. 验证密钥加载
curl http://localhost:9000/api/v1/eth2/publicKeys

# 4. 重启服务
./validator.sh restart-web3signer

# 5. 检查 Prysm 配置
./validator.sh start-validator prysm --config-only
```

#### Kurtosis Fork Version 问题
```bash
# 检测 Kurtosis 网络的实际 fork version
python3 scripts/detect_kurtosis_fork_version.py

# 使用检测到的 fork version 创建存款数据
./validator.sh create-deposits-with-fork-version --auto-detect

# 手动指定 fork version（如果已知）
./validator.sh create-deposits-with-fork-version --fork-version 0x10000038

# 验证生成的存款数据
cat data/deposits/deposit_data.json | jq '.[0] | {network_name, fork_version}'
# 应该显示：{"network_name": "kurtosis", "fork_version": "10000038"}
```

## 🏭 Production Considerations

### Before Mainnet Deployment
1. **Test on Testnet First**: Run entire workflow on testnet (holesky/sepolia)
2. **Backup Mnemonic Offline**: Store `data/keys/mnemonic.txt` in secure, offline location
3. **Verify Withdrawal Address**: Double-check withdrawal address in `config/config.json`
4. **Test Backup/Restore**: Verify you can restore from backup
5. **Set Up Monitoring**: Configure alerts and monitoring systems

### Security Checklist
- [ ] Mnemonic backed up offline (hardware wallet or air-gapped device)
- [ ] Withdrawal address verified and tested
- [ ] Infrastructure access controlled (SSH keys, VPN, etc.)
- [ ] Monitoring and alerting configured
- [ ] Disaster recovery plan documented and tested
- [ ] Key rotation procedures established
- [ ] Multi-signature withdrawal address (recommended)

### Production Deployment Steps
```bash
# 1. Test on testnet first
./validator.sh deploy --count 1  # Test with 1 validator

# 2. Verify deposit data
cat data/deposits/deposit_data-*.json | jq '.deposits[0]'

# 3. Backup before mainnet
./validator.sh list-keys  # Get pubkeys for backup
./validator.sh backup mnemonic 0x1234... 0x5678... --name pre-mainnet-backup

# 4. Clean and start fresh for mainnet
./validator.sh clean  # Clean testnet keys
# Update config/config.json with mainnet settings
./validator.sh deploy --count 50
```

### Monitoring Setup
```bash
# Check validator status
./validator.sh monitor

# Check service health
./validator.sh status

# View logs
./start.sh logs
```

## 🔐 Security Notes

- **Development Only**: Uses weak passwords and dev tokens
- **Key Backup**: Always backup generated mnemonics offline
- **Network Isolation**: Services run in isolated Docker networks
- **Vault Dev Mode**: In-memory storage with dev root token
- **Key Generation**: Uses official `ethstaker-deposit-cli` for BLS12-381 key generation
- **Deposit Validation**: Uses official `ethstaker-deposit-cli` validation for cryptographic correctness

## 🔍 Deposit Data Validation

### Official Validation
The system uses `ethstaker-deposit-cli`'s official validation functions to ensure cryptographic correctness:

- **Signature Verification**: BLS signature validation for deposit messages
- **Public Key Validation**: BLS12-381 public key format and length verification
- **Withdrawal Credentials**: Validation of 0x00/0x01/0x02 withdrawal credential types
- **Amount Verification**: Deposit amount compliance with network requirements
- **Root Hash Validation**: Deposit message and data root verification
- **Network Compatibility**: Fork version and network setting validation

### Usage
```bash
# Integrated validation (recommended)
./validator.sh validate-deposits

# Standalone validation
cd code && source venv/bin/activate
python3 utils/validate_deposits_standalone.py ../data/deposits/deposit_data.json

# Network-specific validation
python3 utils/validate_deposits_standalone.py ../data/deposits/deposit_data.json --network sepolia
```

## 🎯 Dynamic Withdrawal Address Support

### Withdrawal Types
- **0x00 Type (BLS)**: Initial withdrawal using BLS keys (default during key generation)
- **0x01 Type (Execution)**: Withdrawal to Ethereum execution address (dynamic binding)

### Workflow
1. **Key Generation**: Generate keys with BLS withdrawal (0x00 type)
2. **Dynamic Binding**: Create deposits with execution address (0x01 type) when needed
3. **Flexibility**: Same keys can be used with different withdrawal addresses

### Benefits
- **Flexibility**: Change withdrawal address without regenerating keys
- **Security**: Keys generated without binding to specific addresses
- **Compliance**: Meet different regulatory requirements
- **Future-proof**: Adapt to changing withdrawal strategies

## 🔧 Kurtosis Fork Version Compatibility

### Problem
Kurtosis devnet networks often use random `genesis_fork_version` values (e.g., `0x10000038`) instead of the standard `0x00000000`, causing deposit data incompatibility.

### Solution
The system now supports automatic fork version detection and custom fork version specification:

#### Auto-Detection (Recommended)
```bash
# Automatically detect Kurtosis fork version and create compatible deposits
./validator.sh create-deposits-with-fork-version --auto-detect

# Or use Python script directly
python3 scripts/create_deposits_with_fork_version.py --auto-detect
```

#### Manual Specification
```bash
# Specify exact fork version if known
./validator.sh create-deposits-with-fork-version --fork-version 0x10000038 --count 10

# Or use Python script
python3 scripts/create_deposits_with_fork_version.py --fork-version 0x10000038 --count 5
```

#### Detection and Configuration
```bash
# Detect and configure fork version
python3 scripts/detect_kurtosis_fork_version.py

# Manual fork version configuration
python3 scripts/detect_kurtosis_fork_version.py --fork-version 0x10000038
```

### How It Works
1. **Beacon API Query**: Queries `http://localhost:5052/eth/v1/beacon/genesis` for actual fork version
2. **Multi-Endpoint Fallback**: Tries multiple beacon API endpoints (Prysm, Lighthouse)
3. **Dynamic Configuration**: Uses detected fork version to create compatible deposit data
4. **Validation**: Ensures deposit data matches Kurtosis network requirements

### Compatibility Features
- ✅ **Auto-Detection**: Automatically detects Kurtosis fork version
- ✅ **Manual Override**: Support for custom fork version specification
- ✅ **Network Validation**: Ensures deposit data compatibility
- ✅ **Error Handling**: Graceful fallback to default values
- ✅ **Multi-Client Support**: Works with Prysm, Lighthouse, and other clients

## 📁 Project Structure

```
eth_validator_test/
├── README.md                             # Project documentation
├── validator.sh                          # Unified command interface
├── start.sh                              # Infrastructure entry point
├── config.sample.json                   # Sample configuration
│
├── infra/                                # Infrastructure configuration
│   ├── docker-compose.yml               # Docker services
│   ├── vault/                           # Vault configuration
│   │   ├── config/vault.hcl
│   │   └── init/admin-policy.hcl
│   ├── web3signer/                      # Web3Signer configuration
│   │   ├── config/config.yaml
│   │   ├── keys/                        # External validator keys
│   │   └── init-db.sh
│   ├── kurtosis/                        # Kurtosis configuration
│   │   └── kurtosis-config.yaml
│   └── scripts/                         # Infrastructure scripts
│       ├── vault_setup.py
│       └── orchestrate.py
│
├── code/                                 # Core code
│   ├── core/                            # Core functionality
│   │   ├── vault_key_manager.py         # Vault key management (with auto-cleanup)
│   │   ├── validator_manager.py         # Main validator lifecycle manager (with clean command)
│   │   └── backup_system.py            # Backup system
│   ├── utils/                           # Utility modules
│   │   ├── generate_keys.py            # Key generation (ethstaker-deposit-cli, auto-cleanup)
│   │   ├── deposit_generator.py         # Dynamic deposit generation
│   │   ├── validator_client_config.py  # Client configuration generation
│   │   ├── validate_deposits_standalone.py  # Deposit data validation tool
│   │   └── deposit_submitter.py         # Deposit submission to network
│   ├── external/                        # External dependencies (git submodules)
│   │   └── ethstaker-deposit-cli/      # Official Ethereum deposit CLI
│   └── requirements.txt                 # Python dependencies
│
├── scripts/                              # Helper scripts
│   ├── debug_web3signer.py             # Web3Signer diagnostic tool
│   ├── fix_database.py                  # Database repair tool
│   ├── detect_kurtosis_fork_version.py  # Kurtosis fork version detection
│   ├── create_deposits_with_fork_version.py  # Create deposits with custom fork version
│   └── quick-deploy.sh                  # One-command deployment
│
├── config/                               # Configuration directory (git ignored)
│   └── config.json                      # Runtime configuration
│
├── data/                                 # Data directory (git ignored)
│   ├── keys/                            # Key data
│   │   ├── keystores/                  # EIP-2335 keystore files
│   │   ├── secrets/                    # Password files
│   │   ├── keys_data.json              # Complete key data with mnemonic
│   │   ├── pubkeys.json                # Public key index (backward compatibility)
│   │   └── mnemonic.txt                # Mnemonic backup (SECURE!)
│   ├── deposits/                        # Deposit data
│   └── logs/                            # Log files
│
└── archived/                            # Archived files and directories
    ├── README.md                        # Archive documentation
    ├── CLAUDE.md                        # Original planning document
    ├── CONFIG.md                        # Configuration documentation
    ├── docs/                            # Empty documentation directories
    ├── tmp/                             # Temporary files
    └── plans/                           # Development planning files
```

## 📄 License

This project is for educational and testing purposes. Use appropriate security measures for production deployments.