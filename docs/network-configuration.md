# Network Configuration Guide

## Kurtosis Network Configuration

### Overview
The system uses a custom network configuration for Kurtosis that matches the parameters defined in `infra/kurtosis/kurtosis-config.yaml`.

### Kurtosis Network Parameters
```yaml
# From kurtosis-config.yaml
preset: minimal
network_id: "3151908"
deposit_contract_address: "0x4242424242424242424242424242424242424242"
altair_fork_epoch: 0
bellatrix_fork_epoch: 0
capella_fork_epoch: 0
deneb_fork_epoch: 0
electra_fork_epoch: 0
```

### Deposit Configuration
The deposit generator uses a custom devnet configuration that matches Kurtosis:

```python
chain_setting = get_devnet_chain_setting(
    network_name='kurtosis',
    genesis_fork_version='0x00000000',  # minimal preset fork version
    exit_fork_version='0x00000000',     # minimal preset exit version
    genesis_validator_root=None,       # 使用默认值
    multiplier=1,
    min_activation_amount=32,
    min_deposit_amount=1
)
```

### Why Not Sepolia?
- **Sepolia network_id**: 11155111
- **Kurtosis network_id**: 3151908
- **Sepolia fork version**: 0x90000069
- **Kurtosis fork version**: 0x00000000 (minimal preset)

Using Sepolia configuration would create incompatible deposit data for the Kurtosis network.

### Network Compatibility
| Network | Network ID | Fork Version | Deposit Contract |
|---------|------------|--------------|------------------|
| Mainnet | 1 | 0x00000000 | 0x00000000219ab540356cBB839Cbe05303d7705Fa |
| Sepolia | 11155111 | 0x90000069 | 0x7f787A8c745F2C7fdD9D5be61c3084F74aB09543 |
| Kurtosis | 3151908 | 0x00000000 | 0x4242424242424242424242424242424242424242 |

### Validation
To verify the network configuration is correct:

```bash
# Test network configuration
./validator.sh test-deposit-network

# Check generated deposit data
cat data/deposits/deposit_data.json | jq '.network_name'
# Should output: "kurtosis"

cat data/deposits/deposit_data.json | jq '.fork_version'
# Should output: "0x00000000"
```

### Troubleshooting
If you encounter network mismatches:

1. **Check Kurtosis network parameters**:
   ```bash
   # Check kurtosis network ID
   curl -X POST -H "Content-Type: application/json" \
     --data '{"jsonrpc":"2.0","method":"net_version","params":[],"id":1}' \
     http://localhost:8545
   ```

2. **Verify deposit contract address**:
   ```bash
   # Check deposit contract
   curl -X POST -H "Content-Type: application/json" \
     --data '{"jsonrpc":"2.0","method":"eth_getCode","params":["0x4242424242424242424242424242424242424242","latest"],"id":1}' \
     http://localhost:8545
   ```

3. **Test deposit submission**:
   ```bash
   # Test with a small deposit first
   ./validator.sh create-deposits
   ./validator.sh submit-deposits
   ```

### Custom Network Setup
If you need to modify the network configuration:

1. **Update kurtosis-config.yaml**:
   ```yaml
   network_id: "YOUR_NETWORK_ID"
   deposit_contract_address: "YOUR_CONTRACT_ADDRESS"
   ```

2. **Update deposit_generator.py**:
   ```python
   chain_setting = get_devnet_chain_setting(
       network_name='your_network',
       genesis_fork_version='YOUR_FORK_VERSION',
       exit_fork_version='YOUR_EXIT_VERSION',
       genesis_validator_root=None,
       multiplier=1,
       min_activation_amount=32,
       min_deposit_amount=1
   )
   ```

3. **Test the configuration**:
   ```bash
   ./validator.sh test-deposit-network
   ```
