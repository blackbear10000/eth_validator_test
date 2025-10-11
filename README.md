# ETH Validator Workflow Testing System

A comprehensive testing framework for Ethereum validator lifecycle management using Kurtosis, Web3Signer, Vault, and Consul.

## 🎯 Overview

This system validates the full Ethereum validator lifecycle with a **hybrid architecture**:
- **Kurtosis Devnet**: Built-in validators for network stability
- **External Validators**: Web3Signer-managed validators for lifecycle testing
- **Key Management**: HashiCorp Vault for secure key storage
- **Remote Signing**: Web3Signer for external validator operations
- **Lifecycle Testing**: Complete validator onboarding/exit workflows

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

### External Validator Flow
```
1. Generate Keys → Store in Vault → Export to Web3Signer
2. Create Deposits → Submit to Network → Wait for Activation
3. Start Validator Client → Connect to Web3Signer + Beacon API
4. Monitor Performance → Test Exit → Test Withdrawal
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
- Git (for downloading eth2-deposit-cli)

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
cd scripts && source venv/bin/activate

# Check service status
python3 external_validator_manager.py check-services

# Generate external validator keys
python3 external_validator_manager.py generate-keys --count 5

# Create and submit deposits (auto-loads from Vault if needed)
python3 external_validator_manager.py submit-deposits

# Start external validator clients (connects to Web3Signer)
python3 external_validator_manager.py start-clients

# Wait for activation
python3 external_validator_manager.py wait-activation

# Monitor performance
python3 external_validator_manager.py monitor

# Test voluntary exit
python3 external_validator_manager.py test-exit

# Test withdrawal process
python3 external_validator_manager.py test-withdrawal
```

### Flexible Workflow Options

The system supports multiple workflow patterns:

#### Option 1: Complete Flow (Recommended)
```bash
# Generate keys and create deposits in one go
python3 external_validator_manager.py generate-keys --count 5
python3 external_validator_manager.py create-deposits
```

#### Option 2: Resume from Existing Keys
```bash
# Create deposits directly (auto-loads from Vault)
python3 external_validator_manager.py create-deposits
```

#### Option 3: Debug/Manual Control
```bash
# Manually load validators (for debugging or explicit control)
python3 external_validator_manager.py load-validators
python3 external_validator_manager.py create-deposits
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

### Individual Tools

#### Key Generation
```bash
python3 scripts/generate_keys.py --count 10 --output-dir ./keys
```

#### Key Management
```bash
# Import keys to Vault
python3 scripts/key_manager.py import --keys-dir ./keys

# Export keys for Web3Signer
python3 scripts/key_manager.py export --output-dir ./web3signer/keys

# List all keys (including deleted)
python3 scripts/key_manager.py list

# List only active keys (skip deleted, quiet mode)
python3 scripts/key_manager.py list-active

# List active keys with verbose output
python3 scripts/key_manager.py list-active --verbose

# Permanently destroy deleted keys
python3 scripts/key_manager.py destroy-deleted

# Destroy deleted keys quietly
python3 scripts/key_manager.py destroy-deleted --quiet

# Check validator status
python3 scripts/key_manager.py status
```

#### Deposit Management
```bash
python3 scripts/deposit_manager.py generate \
  --withdrawal-address 0x1234... \
  --validator-count 10
```

#### Validator Lifecycle
```bash
python3 scripts/validator_lifecycle.py status --pubkeys 0xabc... 0xdef...
python3 scripts/validator_lifecycle.py wait-active --pubkeys 0xabc...
python3 scripts/validator_lifecycle.py voluntary-exit --pubkey 0xabc...
python3 scripts/validator_lifecycle.py wait-withdrawal --pubkeys 0xabc...
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
  "monitoring_duration": 600
}
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

# List keys using Web3Signer Key Manager
python3 scripts/web3signer_key_manager.py list

# Load validators from Vault (for debugging only)
python3 scripts/external_validator_manager.py load-validators
```

#### Web3Signer Key Operations
```bash
# Add a new key
python3 scripts/web3signer_key_manager.py add --keystore ./path/to/keystore.json --password "password" --index 0

# Remove a key
python3 scripts/web3signer_key_manager.py remove --key-id "validator_0000_20241211_12345678"

# Remove keys by pattern
python3 scripts/web3signer_key_manager.py remove --pattern "validator_0000"

# Remove all keys (with confirmation, auto-destroys deleted keys)
python3 scripts/web3signer_key_manager.py remove --all

# Update key status
python3 scripts/web3signer_key_manager.py update --key-id "validator_0000_20241211_12345678" --status inactive

# Export keys to Web3Signer format
python3 scripts/web3signer_key_manager.py export

# Check Web3Signer status
python3 scripts/web3signer_key_manager.py status
```
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

#### eth2-deposit-cli Issues
If the official CLI fails to download:
- The system will automatically fall back to simplified key generation
- For production use, manually install from: https://github.com/ethereum/staking-deposit-cli
- Ensure Git is available for automatic download

#### Docker Issues
```bash
docker system prune -f  # Clean up Docker
docker-compose down -v  # Remove volumes
./start.sh cleanup      # Full cleanup
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

# Clear all keys (auto-destroys deleted keys first)
python3 scripts/web3signer_key_manager.py remove --all
```

#### BLS12-381 Key Length Issues
If you encounter "Invalid pubkey length" errors:
```bash
# The system now generates 48-byte BLS12-381 keys by default
# If you have old 32-byte keys, regenerate them:
python3 scripts/web3signer_key_manager.py remove --all
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
# Solution: Regenerate keys with proper BLS12-381 length
python3 scripts/web3signer_key_manager.py remove --all
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
- **Key Generation**: Uses simplified BLS key derivation for testing; production should use official `eth2-deposit-cli`

### Key Generation Approaches

#### Simplified (Default)
- Built-in Python implementation for testing
- Generates 48-byte BLS12-381 compatible keys
- Uses deterministic hash-based key derivation for testing
- Suitable for devnet testing and workflow validation
- ⚠️ **NOT suitable for mainnet use**

#### Official CLI (Recommended for Production)
- Automatically downloaded from [ethereum/staking-deposit-cli](https://github.com/ethereum/staking-deposit-cli)
- Full BLS12-381 cryptographic implementation
- EIP-2335 compliant keystores
- Mainnet-ready security standards

The system attempts to use the official CLI when available, falling back to simplified implementation for testing.

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
- ✅ **External Validator Lifecycle**: pending → active → exited → withdrawn
- ✅ **Deposit Flow**: Generation, submission, and activation
- ✅ **Remote Signing**: External validators sign via Web3Signer
- ✅ **Accelerated Testing**: 4s slots for fast validation cycles
- ✅ **Smart Key Loading**: Auto-loads validators from Vault when needed
- ✅ **Flexible Workflows**: Multiple workflow patterns for different use cases
- ✅ **Key Management**: Full CRUD operations for validator keys
- ✅ **Vault Key Cleanup**: Handles deleted keys and provides cleanup tools
- ✅ **BLS12-381 Compliance**: Generates proper 48-byte validator keys

## 📁 Project Structure

```
eth_validator_test/
├── docker-compose.yml                    # Remote signing stack
├── start.sh                              # Main entry point
├── test_config.json                     # Test configuration
├── kurtosis/
│   └── kurtosis-config.yaml             # Devnet configuration (built-in validators)
├── vault/
│   ├── config/vault.hcl                 # Vault configuration
│   └── init/admin-policy.hcl            # Vault policies
├── web3signer/
│   ├── config/config.yaml               # Web3Signer configuration
│   ├── keys/                            # External validator keys
│   └── init-db.sh                       # PostgreSQL schema initialization
└── scripts/
    ├── orchestrate.py                   # Infrastructure orchestration
    ├── external_validator_manager.py    # External validator lifecycle
    ├── generate_keys.py                 # Key generation
    ├── key_manager.py                   # Key management
    ├── web3signer_key_manager.py        # Web3Signer key CRUD operations
    ├── deposit_manager.py               # Deposit handling
    ├── validator_lifecycle.py           # Lifecycle management
    ├── vault_setup.py                   # Vault initialization
    └── requirements.txt                 # Python dependencies
```

## 🤝 Contributing

1. Test changes with `./start.sh external-test`
2. Ensure all validation checklist items pass
3. Update documentation for new features
4. Follow existing code patterns and error handling

## 📄 License

This project is for educational and testing purposes. Use appropriate security measures for production deployments.