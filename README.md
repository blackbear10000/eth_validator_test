# ETH Validator Testing System

A comprehensive testing framework for Ethereum validator lifecycle management using Kurtosis, Web3Signer, and Vault.

## 🎯 Overview

This system provides a complete Ethereum validator testing solution with:
- **Key Management**: HashiCorp Vault for secure key storage
- **Remote Signing**: Web3Signer for external validator signing
- **Multi-Client Support**: Prysm, Lighthouse, and Teku validator clients
- **Lifecycle Testing**: Complete validator onboarding/exit workflows
- **Official Implementation**: Uses `ethstaker-deposit-cli` for BLS12-381 key generation

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

## 🚀 Quick Start

### Prerequisites
- Docker & Docker Compose
- [Kurtosis CLI](https://docs.kurtosis.com/install)
- Python 3.8+
- Git

### Initial Setup
```bash
# Clone the repository
git clone <repository-url>
cd eth_validator_test

# Initialize and update git submodules
git submodule update --init --recursive

# Copy sample configuration
cp config.sample.json config/config.json

# Install Python dependencies
cd code
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cd external/ethstaker-deposit-cli
pip install -r requirements.txt
cd ../../..
```

### 1. Start Infrastructure
```bash
# Start all services (Vault, Web3Signer, Kurtosis)
./start.sh quick-start
```

### 2. Generate Validator Keys
```bash
# Generate 5 validator keys
cd code && source venv/bin/activate
python3 core/validator_manager.py generate-keys --count 5
```

### 3. Create and Submit Deposits
```bash
# Create deposit data
python3 core/validator_manager.py create-deposits

# Submit deposits to testnet
python3 core/validator_manager.py submit-deposits
```

### 4. Monitor Validator Lifecycle
```bash
# Check services status
python3 core/validator_manager.py check-services

# Monitor validator performance
python3 core/validator_manager.py monitor

# Test voluntary exit
python3 core/validator_manager.py test-exit
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
python3 core/backup_system.py --vault-token dev-root-token keystore 0x1234... --password mypassword
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
python3 utils/validator_client_config.py --vault-token dev-root-token prysm --pubkeys 0x1234... 0x5678...

# Generate Lighthouse configuration
python3 utils/validator_client_config.py --vault-token dev-root-token lighthouse --pubkeys 0x1234... 0x5678...

# Generate all client configurations
python3 utils/validator_client_config.py --vault-token dev-root-token all --pubkeys 0x1234... 0x5678...
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

## 🔐 Security Notes

- **Development Only**: Uses weak passwords and dev tokens
- **Key Backup**: Always backup generated mnemonics offline
- **Network Isolation**: Services run in isolated Docker networks
- **Vault Dev Mode**: In-memory storage with dev root token
- **Key Generation**: Uses official `ethstaker-deposit-cli` for BLS12-381 key generation

## 📁 Project Structure

```
eth_validator_test/
├── README.md                             # Project documentation
├── start.sh                              # Main entry point
├── config.sample.json                   # Sample configuration
├── CLAUDE.md                             # Project planning document
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
│   │   ├── generate_keys.py            # Key generation
│   │   ├── deposit_generator.py         # Dynamic deposit generation
│   │   └── validator_client_config.py  # Client configuration generation
│   ├── external/                        # External dependencies (git submodules)
│   │   └── ethstaker-deposit-cli/      # Official Ethereum deposit CLI
│   └── requirements.txt                 # Python dependencies
│
├── config/                               # Configuration directory (git ignored)
│   └── config.json                      # Runtime configuration
├── data/                                 # Data directory (git ignored)
│   ├── keys/                            # Key data
│   │   ├── keystores/                  # keystore files
│   │   ├── secrets/                    # Password files
│   │   └── pubkeys.json                # Public key index
│   ├── deposits/                        # Deposit data
│   ├── backups/                         # Backup files
│   │   ├── keystores/
│   │   └── mnemonics/
│   └── logs/                            # Log files
│
└── docs/                                # Documentation
    ├── api/                             # API documentation
    ├── guides/                          # Usage guides
    └── troubleshooting/                 # Troubleshooting guides
```

## 📄 License

This project is for educational and testing purposes. Use appropriate security measures for production deployments.