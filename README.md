# ETH Validator Testing System

Comprehensive Ethereum validator lifecycle management using Kurtosis, Web3Signer, and Vault with official `ethstaker-deposit-cli` integration.

## 🚀 Quick Start

### One-Time Setup
```bash
# Clone and setup
git clone <your-repository-url> && cd eth_validator_test
git submodule update --init --recursive
cp config.sample.json config/config.json

# Install dependencies
cd code && python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cd external/ethstaker-deposit-cli && pip install -r requirements.txt
cd ../../..
```

### Deploy Your First Validators
```bash
# 1. Start infrastructure
./validator.sh start

# 2. Generate 5 validators
./validator.sh generate-keys --count 5

# 3. Create deposits
./validator.sh create-deposits

# 4. Submit to network
./validator.sh submit-deposits

# 5. Monitor
./validator.sh monitor
```

## 📋 Common Scenarios

### Scenario 1: Deploy 50 Validators
```bash
./validator.sh start
./validator.sh generate-keys --count 50
./validator.sh list-keys  # Get pubkeys for backup
./validator.sh backup mnemonic 0x1234... 0x5678... --name batch-50
./validator.sh create-deposits
# Review deposit_data.json
./validator.sh submit-deposits
```

### Scenario 2: Add More Validators Later
```bash
# Generate additional keys (will use existing mnemonic from Vault)
./validator.sh generate-keys --count 10
./validator.sh create-deposits
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

## 🎯 Command Reference

### Infrastructure Commands
```bash
./validator.sh start          # Start all services
./validator.sh stop           # Stop all services
./validator.sh status         # Check status
```

### Key Management
```bash
./validator.sh generate-keys  # Generate new keys
./validator.sh list-keys      # List all keys
./validator.sh backup         # Backup keys
```

### Deposit Operations
```bash
./validator.sh create-deposits                    # Create deposit data (default withdrawal address)
./validator.sh create-deposits-with-address --withdrawal-address 0xf39Fd6e51aad88F6F4ce6aB8827279cffFb92266  # Create with custom withdrawal address
./validator.sh submit-deposits                    # Submit to network
```

### Monitoring
```bash
./validator.sh monitor        # Monitor validators
```

### Quick Deploy
```bash
./validator.sh deploy         # Run full deployment workflow
```

## 🏗️ Architecture

### Infrastructure Stack
- **Vault** (port 8200): Secure key storage with KV v2 engine
- **PostgreSQL** (port 5432): Slashing protection database for Web3Signer
- **Web3Signer** (port 9000): Remote signing service for external validators
- **Kurtosis Devnet**: Accelerated testnet with 4s slots for fast testing

### Workflow
```
1. Key Generation → 2. Deposit Creation → 3. Client Configuration → 4. Validator Operation
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
- `submit-deposits` - Submit deposits to network
- `monitor` - Monitor validator performance
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

### Web3Signer Configuration Issues
```bash
# Check PostgreSQL connection
docker exec -it postgres psql -U postgres -d web3signer -c "SELECT version FROM database_version;"

# Reset database if needed
docker-compose down
docker volume rm eth_validator_test_postgres_data
docker-compose up -d
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

# 4. Deploy to mainnet
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
│   │   ├── vault_key_manager.py         # Vault key management
│   │   ├── validator_manager.py         # Main validator lifecycle manager
│   │   └── backup_system.py            # Backup system
│   ├── utils/                           # Utility modules
│   │   ├── generate_keys.py            # Key generation (ethstaker-deposit-cli)
│   │   ├── deposit_generator.py         # Dynamic deposit generation
│   │   └── validator_client_config.py  # Client configuration generation
│   ├── external/                        # External dependencies (git submodules)
│   │   └── ethstaker-deposit-cli/      # Official Ethereum deposit CLI
│   └── requirements.txt                 # Python dependencies
│
├── scripts/                              # Helper scripts
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