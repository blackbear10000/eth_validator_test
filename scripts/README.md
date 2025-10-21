# Scripts Directory

This directory contains helper scripts for debugging, maintenance, and troubleshooting.

## Available Scripts

### Debugging Tools

#### `debug_web3signer.py`
Web3Signer diagnostic tool for checking connection status, loaded keys, and troubleshooting issues.

**Usage:**
```bash
python3 scripts/debug_web3signer.py
```

**Features:**
- Tests Web3Signer connection and health endpoints
- Lists loaded keys in Web3Signer
- Checks Vault connection from Web3Signer
- Provides detailed status information

#### `debug_keys.py`
Key management diagnostic tool for troubleshooting key generation and Vault import issues.

**Usage:**
```bash
python3 scripts/debug_keys.py
```

### Maintenance Tools

#### `fix_database.py`
Database repair tool for fixing PostgreSQL connection issues with Web3Signer.

**Usage:**
```bash
# Via validator.sh (recommended)
./validator.sh fix-database

# Direct execution
python3 scripts/fix_database.py
```

**Features:**
- Checks PostgreSQL container status
- Creates missing databases and tables
- Runs database initialization scripts
- Restarts Web3Signer after fixes
- Verifies database connectivity

### Deployment Tools

#### `quick-deploy.sh`
One-command deployment script for quick setup and testing.

**Usage:**
```bash
./scripts/quick-deploy.sh
```

## Integration

These scripts are integrated into the main `validator.sh` interface:

```bash
# Database maintenance
./validator.sh fix-database

# Web3Signer diagnostics
./validator.sh web3signer-status
./validator.sh web3signer-troubleshoot
```

## Troubleshooting

If you encounter issues with these scripts:

1. **Permission Issues**: Ensure scripts are executable
   ```bash
   chmod +x scripts/*.py
   ```

2. **Python Path Issues**: Run from project root directory
   ```bash
   cd /path/to/eth_validator_test
   python3 scripts/debug_web3signer.py
   ```

3. **Dependencies**: Ensure virtual environment is activated
   ```bash
   cd code && source venv/bin/activate
   cd .. && python3 scripts/debug_web3signer.py
   ```
