#!/usr/bin/env python3
"""
Ethereum Validator Deposit Manager
Uses ethstaker-deposit-cli for official BLS12-381 deposit data generation
"""

import os
import sys
import json
import argparse
from typing import List, Dict, Any, Optional
from eth_utils import to_checksum_address
from web3 import Web3
import requests

# Add ethstaker-deposit-cli to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'ethstaker-deposit-cli'))

from ethstaker_deposit.utils.ssz import (
    DepositMessage,
    DepositData,
    compute_deposit_domain,
    compute_signing_root
)
from ethstaker_deposit.utils.crypto import SHA256
from py_ecc.bls import G2ProofOfPossession as bls


class DepositManager:
    def __init__(self, web3_url: str = "http://localhost:8545"):
        self.web3 = Web3(Web3.HTTPProvider(web3_url))
        self.deposit_contract_address = "0x00000000219ab540356cBB839Cbe05303d7705Fa"  # Mainnet address

        # Standard deposit amount (32 ETH in Gwei)
        self.deposit_amount_gwei = 32 * 10**9
        
        # Network configurations
        self.network_configs = {
            "mainnet": {
                "fork_version": "0x00000000",
                "deposit_contract_address": "0x00000000219ab540356cBB839Cbe05303d7705Fa",
                "genesis_validators_root": "0x4b363db94e286120d76eb905340fdd4e54bfe9f06bf33ff6cf5ad27f511bfe95"
            },
            "goerli": {
                "fork_version": "0x00001020",
                "deposit_contract_address": "0xff50ed3d0ec03aC01D4C79aAd74928BFF48a7b2b",
                "genesis_validators_root": "0x043db0d9a83813551ee2f33450d23797757d430911a9320530ad8a0eabc43efb"
            },
            "sepolia": {
                "fork_version": "0x90000069",
                "deposit_contract_address": "0x7f02C3E3c98b133055B8B348B2Ac625669Ed295D",
                "genesis_validators_root": "0xd8ea171f3c94aea21ebc42a1ed61052acf3fef9c451dcc82c80a0bef24b1fd56"
            },
            "devnet": {
                "fork_version": "0x00000000",  # Kurtosis devnet uses minimal preset
                "deposit_contract_address": "0x4242424242424242424242424242424242424242",  # From kurtosis config
                "genesis_validators_root": "0x0000000000000000000000000000000000000000000000000000000000000000"
            }
        }

        # Deposit Contract ABI (Web3.py compatible)
        self.deposit_contract_abi = [
            {
                "inputs": [
                    {"name": "pubkey", "type": "bytes"},
                    {"name": "withdrawal_credentials", "type": "bytes"},
                    {"name": "signature", "type": "bytes"},
                    {"name": "deposit_data_root", "type": "bytes32"}
                ],
                "name": "deposit",
                "outputs": [],
                "stateMutability": "payable",
                "type": "function"
            },
            {
                "anonymous": False,
                "inputs": [
                    {"indexed": False, "name": "pubkey", "type": "bytes"},
                    {"indexed": False, "name": "withdrawal_credentials", "type": "bytes"},
                    {"indexed": False, "name": "amount", "type": "bytes"},
                    {"indexed": False, "name": "signature", "type": "bytes"},
                    {"indexed": False, "name": "index", "type": "bytes"}
                ],
                "name": "DepositEvent",
                "type": "event"
            },
            {
                "inputs": [],
                "name": "get_deposit_count",
                "outputs": [{"name": "", "type": "bytes"}],
                "stateMutability": "view",
                "type": "function"
            },
            {
                "inputs": [],
                "name": "get_deposit_root",
                "outputs": [{"name": "", "type": "bytes32"}],
                "stateMutability": "view",
                "type": "function"
            }
        ]

    def generate_withdrawal_credentials(self, withdrawal_address: str) -> bytes:
        """Generate withdrawal credentials for an address"""
        # For Ethereum 2.0, withdrawal credentials start with 0x01 followed by 11 zeros and the address
        withdrawal_address = withdrawal_address.lower().replace('0x', '')
        withdrawal_credentials = '01' + '00' * 11 + withdrawal_address
        return bytes.fromhex(withdrawal_credentials)

    def create_deposit_data(self, pubkey: str, withdrawal_credentials: str, 
                          private_key: int, network_name: str = "devnet") -> Dict[str, Any]:
        """Create deposit data using official ethstaker-deposit-cli implementation"""
        
        # Get network configuration
        if network_name not in self.network_configs:
            raise ValueError(f"Unknown network: {network_name}")
        
        network_config = self.network_configs[network_name]
        
        # Convert inputs to bytes
        pubkey_hex = pubkey.replace('0x', '')
        pubkey_bytes = bytes.fromhex(pubkey_hex)
        withdrawal_credentials_bytes = bytes.fromhex(withdrawal_credentials.replace('0x', ''))
        
        # Handle compressed BLS12-381 public keys (49 bytes with prefix, need 48 bytes)
        if len(pubkey_bytes) == 49:
            # Remove the compression prefix (first byte) to get 48 bytes
            pubkey_bytes = pubkey_bytes[1:]
        elif len(pubkey_bytes) == 48:
            # Already 48 bytes, use as is
            pass
        else:
            raise ValueError(f"Invalid pubkey length: {len(pubkey_bytes)} bytes (expected 48 or 49)")
        
        # Validate input lengths
        if len(pubkey_bytes) != 48:
            raise ValueError(f"Invalid pubkey length after processing: {len(pubkey_bytes)} bytes (expected 48)")
        if len(withdrawal_credentials_bytes) != 32:
            raise ValueError(f"Invalid withdrawal credentials length: {len(withdrawal_credentials_bytes)} bytes (expected 32)")
        
        # Create deposit message using official SSZ
        deposit_message = DepositMessage(
            pubkey=pubkey_bytes,
            withdrawal_credentials=withdrawal_credentials_bytes,
            amount=self.deposit_amount_gwei
        )
        
        # Compute deposit domain using official implementation
        fork_version = bytes.fromhex(network_config["fork_version"].replace('0x', ''))
        domain = compute_deposit_domain(fork_version)
        
        # Compute signing root using official implementation
        signing_root = compute_signing_root(deposit_message, domain)
        
        # Sign using official BLS implementation
        signature = bls.Sign(private_key, signing_root)
        
        # Create deposit data using official SSZ
        deposit_data = DepositData(
            pubkey=pubkey_bytes,
            withdrawal_credentials=withdrawal_credentials_bytes,
            amount=self.deposit_amount_gwei,
            signature=signature
        )
        
        # Compute deposit data root
        deposit_data_root = deposit_data.hash_tree_root
        
        return {
            "pubkey": "0x" + pubkey_bytes.hex(),
            "withdrawal_credentials": "0x" + withdrawal_credentials_bytes.hex(),
            "amount": str(self.deposit_amount_gwei),
            "signature": "0x" + signature.hex(),
            "deposit_message_root": "0x" + deposit_message.hash_tree_root.hex(),
            "deposit_data_root": "0x" + deposit_data_root.hex(),
            "fork_version": network_config["fork_version"],
            "network_name": network_name,
            "deposit_contract_address": network_config["deposit_contract_address"]
        }

    def validate_deposit_data(self, deposit_data: Dict[str, Any]) -> bool:
        """Validate deposit data structure and content"""
        required_fields = [
            "pubkey", "withdrawal_credentials", "amount", "signature",
            "deposit_message_root", "deposit_data_root", "fork_version",
            "network_name", "deposit_contract_address"
        ]
        
        # Check all required fields are present
        for field in required_fields:
            if field not in deposit_data:
                print(f"❌ Missing required field: {field}")
                return False
        
        # Validate field lengths and formats
        try:
            # Validate pubkey (48 bytes = 96 hex chars + 0x prefix = 98 chars)
            pubkey = deposit_data["pubkey"]
            if not pubkey.startswith("0x") or len(pubkey) != 98:
                print(f"❌ Invalid pubkey format: {pubkey}")
                return False
            
            # Validate withdrawal credentials (32 bytes = 64 hex chars + 0x prefix = 66 chars)
            withdrawal_credentials = deposit_data["withdrawal_credentials"]
            if not withdrawal_credentials.startswith("0x") or len(withdrawal_credentials) != 66:
                print(f"❌ Invalid withdrawal credentials format: {withdrawal_credentials}")
                return False
            
            # Validate signature (96 bytes = 192 hex chars + 0x prefix = 194 chars)
            signature = deposit_data["signature"]
            if not signature.startswith("0x") or len(signature) != 194:
                print(f"❌ Invalid signature format: {signature}")
                return False
            
            # Validate amount
            amount = int(deposit_data["amount"])
            if amount != self.deposit_amount_gwei:
                print(f"❌ Invalid amount: {amount} (expected {self.deposit_amount_gwei})")
                return False
            
            # Validate deposit data root (32 bytes = 64 hex chars + 0x prefix = 66 chars)
            deposit_data_root = deposit_data["deposit_data_root"]
            if not deposit_data_root.startswith("0x") or len(deposit_data_root) != 66:
                print(f"❌ Invalid deposit data root format: {deposit_data_root}")
                return False
            
            print("✅ Deposit data validation passed")
            return True
            
        except (ValueError, TypeError) as e:
            print(f"❌ Validation error: {e}")
            return False

    def generate_batch_deposit_data(self, keys: List[Dict[str, Any]], 
                                  withdrawal_address: str, network_name: str = "devnet",
                                  vault_manager=None, output_file: str = None) -> List[Dict[str, Any]]:
        """Generate batch deposit data for multiple validators"""
        print(f"=== Generating Deposit Data for {len(keys)} Validators ===")
        print(f"Network: {network_name}")
        print(f"Withdrawal address: {withdrawal_address}")
        
        # Generate withdrawal credentials
        withdrawal_credentials = self.generate_withdrawal_credentials(withdrawal_address)
        withdrawal_credentials_hex = "0x" + withdrawal_credentials.hex()
        
        deposit_data_list = []
        
        for i, key_data in enumerate(keys):
            print(f"Processing validator {i+1}/{len(keys)}...")
            
            # Extract public key and private key
            pubkey = key_data["validator_public_key"]
            private_key = int(key_data["validator_private_key"], 16)
            
            # Create deposit data
            try:
                deposit_data = self.create_deposit_data(
                    pubkey=pubkey,
                    withdrawal_credentials=withdrawal_credentials_hex,
                    private_key=private_key,
                    network_name=network_name
                )
                
                # Validate deposit data
                if self.validate_deposit_data(deposit_data):
                    deposit_data_list.append(deposit_data)
                    print(f"✅ Validator {i+1} deposit data generated")
                else:
                    print(f"❌ Validator {i+1} deposit data validation failed")
                    
            except Exception as e:
                print(f"❌ Error generating deposit data for validator {i+1}: {e}")
                continue
        
        print(f"Generated {len(deposit_data_list)} valid deposit data entries")
        
        # Save to file if specified
        if output_file:
            with open(output_file, 'w') as f:
                json.dump(deposit_data_list, f, indent=2)
            print(f"Deposit data saved to: {output_file}")
        
        return deposit_data_list

    def submit_deposits(self, deposit_file: str, config: dict) -> bool:
        """Submit deposits to the network"""
        print("=== Submitting Deposits ===")
        
        if not os.path.exists(deposit_file):
            print(f"❌ Deposit file not found: {deposit_file}")
            return False
        
        # Load deposit data
        with open(deposit_file, 'r') as f:
            deposit_data = json.load(f)
        
        if not deposit_data:
            print("❌ No deposit data found")
            return False
        
        print(f"Loaded {len(deposit_data)} deposit entries")
        
        # Validate all deposit data
        for i, deposit in enumerate(deposit_data):
            if not self.validate_deposit_data(deposit):
                print(f"❌ Deposit {i+1} validation failed")
                return False
        
        print("✅ All deposit data validated")
        
        # Check if Kurtosis testnet submission is enabled
        if config.get("kurtosis_testnet", {}).get("enabled", False):
            print("🌐 Kurtosis testnet submission enabled")
            return self._submit_to_kurtosis_testnet(deposit_data, config)
        else:
            print("📝 Test mode: Deposit data generated but not submitted to network")
            print("To enable actual submission, set kurtosis_testnet.enabled=true in config")
            return True

    def _submit_to_kurtosis_testnet(self, deposit_data: List[Dict[str, Any]], config: dict) -> bool:
        """Submit deposits to Kurtosis testnet"""
        try:
            # Import Web3 at the beginning of the method
            from web3 import Web3
            
            kurtosis_config = config["kurtosis_testnet"]
            web3_url = kurtosis_config["web3_url"]
            from_address = kurtosis_config["from_address"]
            private_key = kurtosis_config["private_key"]
            deposit_contract_address = kurtosis_config["deposit_contract_address"]
            gas_price = int(kurtosis_config["gas_price"])
            gas_limit = int(kurtosis_config["gas_limit"])
            
            # Ensure addresses have correct EIP-55 checksum
            from_address = Web3.to_checksum_address(from_address)
            deposit_contract_address = Web3.to_checksum_address(deposit_contract_address)
            
            print(f"🌐 Connecting to Kurtosis testnet: {web3_url}")
            print(f"📝 From address: {from_address}")
            print(f"📝 Deposit contract: {deposit_contract_address}")
            
            # Connect to Web3
            w3 = Web3(Web3.HTTPProvider(web3_url))
            
            if not w3.is_connected():
                print("❌ Failed to connect to Kurtosis testnet")
                return False
            
            print("✅ Connected to Kurtosis testnet")
            
            # Check account balance
            balance = w3.eth.get_balance(from_address)
            balance_eth = w3.from_wei(balance, 'ether')
            print(f"💰 Account balance: {balance_eth} ETH")
            
            # Calculate required ETH for deposits
            required_eth = len(deposit_data) * 32  # 32 ETH per validator
            if balance_eth < required_eth:
                print(f"❌ Insufficient balance: need {required_eth} ETH, have {balance_eth} ETH")
                return False
            
            # Create contract instance
            contract = w3.eth.contract(
                address=deposit_contract_address,
                abi=self.deposit_contract_abi
            )
            
            # Test contract accessibility
            try:
                deposit_count = contract.functions.get_deposit_count().call()
                print(f"✅ Contract accessible, current deposit count: {deposit_count.hex()}")
            except Exception as e:
                print(f"⚠️  Warning: Could not call contract function: {e}")
                print("📝 Proceeding with deposit submission...")
            
            # Submit deposits one by one
            tx_hashes = []
            for i, deposit in enumerate(deposit_data):
                print(f"📤 Submitting deposit {i+1}/{len(deposit_data)}...")
                
                # Prepare deposit data
                pubkey = bytes.fromhex(deposit["pubkey"][2:])  # Remove 0x prefix
                withdrawal_credentials = bytes.fromhex(deposit["withdrawal_credentials"][2:])
                signature = bytes.fromhex(deposit["signature"][2:])
                deposit_data_root = bytes.fromhex(deposit["deposit_data_root"][2:])
                
                # Debug: Print data lengths and content
                print(f"📋 Deposit data lengths:")
                print(f"   - Pubkey: {len(pubkey)} bytes")
                print(f"   - Withdrawal credentials: {len(withdrawal_credentials)} bytes")
                print(f"   - Signature: {len(signature)} bytes")
                print(f"   - Deposit data root: {len(deposit_data_root)} bytes")
                
                # Validate data lengths
                if len(pubkey) != 48:
                    print(f"❌ Invalid pubkey length: {len(pubkey)} bytes (expected 48)")
                    return False
                if len(withdrawal_credentials) != 32:
                    print(f"❌ Invalid withdrawal credentials length: {len(withdrawal_credentials)} bytes (expected 32)")
                    return False
                if len(signature) != 96:
                    print(f"❌ Invalid signature length: {len(signature)} bytes (expected 96)")
                    return False
                if len(deposit_data_root) != 32:
                    print(f"❌ Invalid deposit data root length: {len(deposit_data_root)} bytes (expected 32)")
                    return False
                
                # Build transaction
                try:
                    nonce = w3.eth.get_transaction_count(from_address)
                    print(f"📋 Building transaction for deposit {i+1}:")
                    print(f"   - From: {from_address}")
                    print(f"   - To: {deposit_contract_address}")
                    print(f"   - Value: 32 ETH")
                    print(f"   - Gas: {gas_limit}")
                    print(f"   - Gas Price: {gas_price} wei ({w3.from_wei(gas_price, 'gwei')} gwei)")
                    print(f"   - Nonce: {nonce}")
                    
                    transaction = contract.functions.deposit(
                        pubkey,
                        withdrawal_credentials,
                        signature,
                        deposit_data_root
                    ).build_transaction({
                        'from': from_address,
                        'value': w3.to_wei(32, 'ether'),  # 32 ETH per deposit
                        'gas': gas_limit,
                        'gasPrice': gas_price,
                        'nonce': nonce
                    })
                    print(f"✅ Transaction built for deposit {i+1}")
                except Exception as e:
                    print(f"❌ Failed to build transaction for deposit {i+1}: {e}")
                    return False
                
                # Sign and send transaction
                try:
                    signed_txn = w3.eth.account.sign_transaction(transaction, private_key)
                    # Handle both old and new Web3.py versions
                    raw_tx = getattr(signed_txn, 'raw_transaction', getattr(signed_txn, 'rawTransaction', None))
                    if raw_tx is None:
                        raise AttributeError("Cannot find raw transaction data")
                    tx_hash = w3.eth.send_raw_transaction(raw_tx)
                    
                    print(f"✅ Deposit {i+1} submitted: {tx_hash.hex()}")
                    tx_hashes.append(tx_hash.hex())
                    
                    # Wait for transaction to be mined
                    print(f"⏳ Waiting for transaction confirmation...")
                    try:
                        receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)
                        print(f"📋 Transaction receipt received:")
                        print(f"   - Block Number: {receipt.blockNumber}")
                        print(f"   - Block Hash: {receipt.blockHash.hex()}")
                        print(f"   - Gas Used: {receipt.gasUsed}")
                        print(f"   - Status: {receipt.status}")
                        
                        if receipt.status == 1:
                            print(f"✅ Deposit {i+1} confirmed in block {receipt.blockNumber}")
                        else:
                            print(f"❌ Deposit {i+1} failed with status {receipt.status}")
                            return False
                            
                    except Exception as e:
                        print(f"❌ Error waiting for transaction receipt: {e}")
                        return False
                        
                except Exception as e:
                    print(f"❌ Failed to send transaction for deposit {i+1}: {e}")
                    return False
            
            print(f"🎉 Successfully submitted {len(deposit_data)} deposits to Kurtosis testnet!")
            print(f"📋 Transaction hashes: {tx_hashes}")
            
            return True
            
        except Exception as e:
            print(f"❌ Error submitting to Kurtosis testnet: {e}")
            return False


def main():
    """Main function for testing"""
    parser = argparse.ArgumentParser(description="Generate and submit validator deposits")
    parser.add_argument("--keys-file", required=True, help="JSON file containing validator keys")
    parser.add_argument("--withdrawal-address", required=True, help="Withdrawal address")
    parser.add_argument("--network", default="devnet", help="Network name (mainnet, goerli, sepolia, devnet)")
    parser.add_argument("--output-file", help="Output file for deposit data")
    parser.add_argument("--submit", action="store_true", help="Submit deposits to network")
    parser.add_argument("--config-file", help="Configuration file for network settings")
    
    args = parser.parse_args()
    
    # Load keys
    with open(args.keys_file, 'r') as f:
        keys = json.load(f)
    
    # Create deposit manager
    manager = DepositManager()
    
    # Generate deposit data
    deposit_data = manager.generate_batch_deposit_data(
        keys=keys,
        withdrawal_address=args.withdrawal_address,
        network_name=args.network,
        output_file=args.output_file
    )
    
    if args.submit and args.config_file:
        # Load config and submit
        with open(args.config_file, 'r') as f:
            config = json.load(f)
        
        success = manager.submit_deposits(args.output_file, config)
        if success:
            print("✅ Deposits submitted successfully")
        else:
            print("❌ Failed to submit deposits")
    elif args.submit:
        print("❌ --config-file required when using --submit")


if __name__ == "__main__":
    main()