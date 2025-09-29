# ETH Validator Workflow Testing System

A comprehensive testing framework for Ethereum validator lifecycle management using Kurtosis, Web3Signer, Vault, and Consul.

## 🎯 Overview

This system validates the full Ethereum validator lifecycle:
- **Key Generation**: BLS validator keys using secure mnemonic derivation
- **Key Storage**: HashiCorp Vault with Consul backend for persistence
- **Remote Signing**: Web3Signer integration for validator operations
- **Network Setup**: Accelerated devnet using Kurtosis with 4 EL/CL pairs
- **Deposit Flow**: Batch deposit generation and submission
- **Lifecycle Management**: Activation, monitoring, voluntary exit, and withdrawal

## 🏗️ Architecture

### Remote Signing Stack
- **Consul** (port 8500): Persistent storage backend
- **Vault** (port 8200): Secure key storage with KV v2 engine
- **Web3Signer** (port 9000): Remote signing service with Key Manager API

### Ethereum Devnet (Kurtosis)
- **4 EL/CL pairs**: geth+prysm, reth+lighthouse, geth+lighthouse, reth+prysm
- **Accelerated parameters**: 6s slots, 8 slot epochs for fast testing
- **Dynamic port mapping**: Isolated network with external access

## 🚀 Quick Start

### Prerequisites
- Docker & Docker Compose
- [Kurtosis CLI](https://docs.kurtosis.com/install)
- Python 3.8+
- Git (for downloading eth2-deposit-cli)

**Note**: The system uses a simplified key generation approach for testing. For production use, the official `eth2-deposit-cli` is automatically downloaded from GitHub when available.

### One-Command Test
```bash
./start.sh full-test
```

### Step-by-Step Setup
```bash
# 1. Start infrastructure
./start.sh quick-start

# 2. Run individual phases
cd scripts && source venv/bin/activate

# Generate and store keys
python3 orchestrate.py generate-keys

# Create deposit data
python3 orchestrate.py create-deposits

# Wait for validator activation
python3 orchestrate.py wait-activation

# Monitor validator performance
python3 orchestrate.py monitor

# Test voluntary exit
python3 orchestrate.py test-exit

# Test withdrawal process
python3 orchestrate.py test-withdrawal

# Generate final report
python3 orchestrate.py generate-report
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
- `full-test` - Complete validator lifecycle test
- `quick-start` - Infrastructure setup only
- `status` - Show service status
- `logs` - Show service logs
- `cleanup` - Stop all services
- `help` - Show help

### Individual Tools

#### Key Generation
```bash
python3 scripts/generate_keys.py --count 10 --output-dir ./keys
```

#### Key Management
```bash
python3 scripts/key_manager.py import --keys-dir ./keys
python3 scripts/key_manager.py export --output-dir ./web3signer/keys
python3 scripts/key_manager.py list
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

Edit `test_config.json`:

```json
{
  "validator_count": 10,
  "withdrawal_address": "0x1234567890123456789012345678901234567890",
  "timeout_activation": 1800,
  "timeout_exit": 1800,
  "monitoring_duration": 600,
  "network_params": {
    "slots_per_epoch": 8,
    "seconds_per_slot": 6
  }
}
```

## 📊 Monitoring & Debugging

### Service URLs
- **Consul UI**: http://localhost:8500
- **Vault UI**: http://localhost:8200 (token: `dev-root-token`)
- **Web3Signer API**: http://localhost:9000
- **Beacon API**: http://localhost:5052 (varies by Kurtosis mapping)

### Check Service Status
```bash
docker ps
kurtosis enclave ls
curl http://localhost:8200/v1/sys/health
curl http://localhost:9000/upcheck
```

### View Logs
```bash
docker-compose logs -f vault
docker-compose logs -f web3signer
kurtosis service logs eth-devnet cl-1-lighthouse-prysm
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

## 🔐 Security Notes

- **Development Only**: Uses weak passwords and dev tokens
- **Key Backup**: Always backup generated mnemonics offline
- **Network Isolation**: Services run in isolated Docker networks
- **Vault Dev Mode**: In-memory storage with dev root token
- **Key Generation**: Uses simplified BLS key derivation for testing; production should use official `eth2-deposit-cli`

### Key Generation Approaches

#### Simplified (Default)
- Built-in Python implementation for testing
- Uses HMAC-based key derivation (not full BLS12-381)
- Suitable for devnet testing and workflow validation
- ⚠️ **NOT suitable for mainnet use**

#### Official CLI (Recommended for Production)
- Automatically downloaded from [ethereum/staking-deposit-cli](https://github.com/ethereum/staking-deposit-cli)
- Full BLS12-381 cryptographic implementation
- EIP-2335 compliant keystores
- Mainnet-ready security standards

The system attempts to use the official CLI when available, falling back to simplified implementation for testing.

## 🧪 Validation Checklist

The system validates:
- ✅ Vault securely stores/retrieves BLS keys
- ✅ Web3Signer loads keys via Key Manager API
- ✅ Validator clients connect to Web3Signer for signing
- ✅ Deposit data generation and validation
- ✅ Validator lifecycle: pending → active → exited → withdrawn
- ✅ Accelerated network parameters for fast testing

## 📁 Project Structure

```
eth_validator/
├── docker-compose.yml           # Remote signing stack
├── start.sh                     # Main entry point
├── test_config.json            # Test configuration
├── kurtosis/
│   ├── kurtosis-config.yaml    # Devnet configuration
│   └── network-params.yaml     # Network parameters
├── vault/
│   ├── config/vault.hcl        # Vault configuration
│   └── init/admin-policy.hcl   # Vault policies
├── web3signer/
│   └── config/config.yaml      # Web3Signer configuration
└── scripts/
    ├── generate_keys.py        # Key generation
    ├── key_manager.py          # Key management
    ├── deposit_manager.py      # Deposit handling
    ├── validator_lifecycle.py  # Lifecycle management
    ├── vault_setup.py          # Vault initialization
    ├── orchestrate.py          # Test orchestration
    └── requirements.txt        # Python dependencies
```

## 🤝 Contributing

1. Test changes with `./start.sh full-test`
2. Ensure all validation checklist items pass
3. Update documentation for new features
4. Follow existing code patterns and error handling

## 📄 License

This project is for educational and testing purposes. Use appropriate security measures for production deployments.