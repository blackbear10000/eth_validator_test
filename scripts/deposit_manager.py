#!/usr/bin/env python3
"""
Ethereum Validator Deposit Manager
Generates deposit data and handles batch deposits
"""

import os
import json
import argparse
from typing import List, Dict, Any, Optional
from eth_utils import to_checksum_address
from web3 import Web3
import requests


class DepositManager:
    def __init__(self, web3_url: str = "http://localhost:8545"):
        self.web3 = Web3(Web3.HTTPProvider(web3_url))
        self.deposit_contract_address = "0x00000000219ab540356cBB839Cbe05303d7705Fa"  # Mainnet address
        self.batch_deposit_contract_address = None  # To be set later

        # Standard deposit amount (32 ETH in Wei)
        self.deposit_amount = 32 * 10**18
        
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
                "deposit_contract_address": "0x7f7C6c8c8c8c8c8c8c8c8c8c8c8c8c8c8c8c8c8c",
                "genesis_validators_root": "0x0000000000000000000000000000000000000000000000000000000000000000"
            },
            "devnet": {
                "fork_version": "0x00000000",  # Kurtosis devnet uses minimal preset
                "deposit_contract_address": "0x4242424242424242424242424242424242424242",  # From kurtosis config
                "genesis_validators_root": "0x0000000000000000000000000000000000000000000000000000000000000000"
            }
        }

        # Batch Deposit Contract ABI (simplified)
        self.batch_deposit_abi = [
            {
                "inputs": [
                    {"name": "pubkeys", "type": "bytes[]"},
                    {"name": "withdrawal_credentials", "type": "bytes[]"},
                    {"name": "signatures", "type": "bytes[]"},
                    {"name": "deposit_data_roots", "type": "bytes32[]"}
                ],
                "name": "batchDeposit",
                "outputs": [],
                "stateMutability": "payable",
                "type": "function"
            }
        ]

    def load_keys_from_vault(self, vault_manager) -> List[Dict[str, Any]]:
        """Load validator keys from Vault"""
        keys = vault_manager.list_keys_in_vault()
        validator_keys = []

        for key_id in keys:
            key_data = vault_manager.retrieve_key_from_vault(key_id)
            if key_data and "metadata" in key_data:
                metadata = key_data["metadata"]
                validator_keys.append({
                    "key_id": key_id,
                    "index": metadata.get("index"),
                    "validator_pubkey": metadata.get("validator_pubkey"),
                    "withdrawal_pubkey": metadata.get("withdrawal_pubkey"),
                    "status": metadata.get("status", "generated")
                })

        return sorted(validator_keys, key=lambda x: x.get("index", 0))

    def generate_withdrawal_credentials(self, withdrawal_address: str) -> str:
        """Generate withdrawal credentials for an address"""
        # For Ethereum 2.0, withdrawal credentials start with 0x01 followed by 11 zeros and the address
        withdrawal_address = withdrawal_address.lower().replace('0x', '')
        withdrawal_credentials = '01' + '00' * 11 + withdrawal_address
        return '0x' + withdrawal_credentials

    def compute_deposit_domain(self, fork_version: str = "0x00000000", network_name: str = "devnet") -> bytes:
        """Compute deposit domain for signature"""
        # Domain computation for Ethereum 2.0
        # DOMAIN_DEPOSIT = 0x03000000
        domain_type = b'\x03\x00\x00\x00'  # DOMAIN_DEPOSIT (little-endian)
        fork_version_bytes = bytes.fromhex(fork_version.replace('0x', ''))
        
        # Get genesis validators root from network config
        network_config = self.network_configs.get(network_name, self.network_configs["devnet"])
        genesis_validators_root_hex = network_config["genesis_validators_root"]
        genesis_validators_root = bytes.fromhex(genesis_validators_root_hex.replace('0x', ''))

        # Domain = domain_type + fork_version + genesis_validators_root
        domain = domain_type + fork_version_bytes + genesis_validators_root
        return domain

    def create_deposit_data(self, validator_pubkey: str, withdrawal_address: str,
                           fork_version: str = None, network_name: str = "devnet") -> Dict[str, Any]:
        """
        Create deposit data for a single validator
        
        NOTE: This is a TESTING implementation that creates deterministic but 
        NOT cryptographically valid signatures. For production use, implement
        proper BLS12-381 signing with the validator's private key.
        """
        # Get network configuration
        if network_name not in self.network_configs:
            raise ValueError(f"Unknown network: {network_name}")
        
        network_config = self.network_configs[network_name]
        if fork_version is None:
            fork_version = network_config["fork_version"]
        
        try:
            # Convert pubkey to bytes
            pubkey_hex = validator_pubkey.replace('0x', '')
            pubkey_bytes = bytes.fromhex(pubkey_hex)
            print(f"Debug: Processing validator pubkey: {validator_pubkey[:20]}...")
            print(f"Debug: Pubkey length: {len(pubkey_bytes)} bytes ({len(pubkey_hex)} hex chars)")
            print(f"Debug: Using network: {network_name}, fork_version: {fork_version}")
            
            # Ensure we have the right length for BLS12-381
            if len(pubkey_bytes) == 32:
                print("Warning: Using 32-byte pubkey, extending to 48 bytes for BLS12-381")
                # Extend 32-byte pubkey to 48 bytes for BLS12-381
                import hashlib
                extended = hashlib.sha256(pubkey_bytes + b"extension").digest()[:16]
                pubkey_bytes = pubkey_bytes + extended
            elif len(pubkey_bytes) != 48:
                raise ValueError(f"Invalid pubkey length: {len(pubkey_bytes)} bytes (expected 32 or 48)")
                
        except Exception as e:
            print(f"Error processing pubkey {validator_pubkey}: {e}")
            raise

        # Generate withdrawal credentials
        withdrawal_credentials = self.generate_withdrawal_credentials(withdrawal_address)
        withdrawal_credentials_bytes = bytes.fromhex(withdrawal_credentials.replace('0x', ''))

        # Create deposit message
        # Convert deposit amount to Gwei (32 ETH = 32,000,000,000 Gwei)
        deposit_amount_gwei = 32 * 10**9  # 32 ETH in Gwei
        deposit_message = {
            "pubkey": pubkey_bytes,
            "withdrawal_credentials": withdrawal_credentials_bytes,
            "amount": deposit_amount_gwei.to_bytes(8, 'little')
        }

        # Create proper deposit message hash
        import hashlib
        
        # Create deposit message (SSZ structure)
        deposit_message = {
            "pubkey": pubkey_bytes,
            "withdrawal_credentials": withdrawal_credentials_bytes,
            "amount": deposit_amount_gwei.to_bytes(8, 'little')
        }
        
        # Compute deposit message root (simplified SSZ hash)
        # In real implementation, this should use proper SSZ serialization
        # For testing, we'll create a deterministic hash
        message_data = (
            deposit_message["pubkey"] +
            deposit_message["withdrawal_credentials"] +
            deposit_message["amount"]
        )
        deposit_message_root = hashlib.sha256(message_data).digest()
        
        print(f"Debug: Deposit message root: {deposit_message_root.hex()}")
        
        # Create a deterministic signature for testing
        # In production, this should be properly signed with the validator's private key
        domain = self.compute_deposit_domain(fork_version, network_name)
        
        # Create signing root: hash(deposit_message_root + domain)
        signing_root = hashlib.sha256(deposit_message_root + domain).digest()
        
        # For testing: create a deterministic signature based on the signing root
        # This creates a unique signature for each validator but is NOT cryptographically valid
        signature_data = hashlib.sha256(
            signing_root + 
            pubkey_bytes + 
            withdrawal_credentials_bytes
        ).digest()
        
        # Create a deterministic signature (96 bytes)
        # This is NOT cryptographically valid but serves for testing
        signature = (signature_data * 3)[:96]  # Repeat and truncate to 96 bytes
        
        # Compute deposit data root
        deposit_data = deposit_message_root + signature
        deposit_data_root = hashlib.sha256(deposit_data).digest()

        return {
            "pubkey": "0x" + pubkey_bytes.hex(),
            "withdrawal_credentials": withdrawal_credentials,
            "amount": str(deposit_amount_gwei),
            "signature": "0x" + signature.hex(),
            "deposit_message_root": "0x" + deposit_message_root.hex(),
            "deposit_data_root": "0x" + deposit_data_root.hex(),
            "fork_version": fork_version,
            "network_name": network_name,
            "deposit_contract_address": network_config["deposit_contract_address"],
            "genesis_validators_root": network_config["genesis_validators_root"],
            "deposit_cli_version": "2.5.0"
        }

    def generate_batch_deposit_data(self, withdrawal_address: str, validator_count: int,
                                   vault_manager, output_file: str = "deposit_data.json",
                                   use_mnemonic: str = None, network_name: str = "devnet") -> List[Dict[str, Any]]:
        """Generate deposit data for multiple validators"""

        # If mnemonic is provided, use the deposit CLI wrapper
        if use_mnemonic:
            from deposit_cli_wrapper import DepositCLIWrapper
            wrapper = DepositCLIWrapper()

            deposit_data = wrapper.generate_deposit_data(
                mnemonic=use_mnemonic,
                count=validator_count,
                withdrawal_address=withdrawal_address,
                output_dir=os.path.dirname(output_file) or "./keys"
            )

            # Save deposit data to file
            with open(output_file, 'w') as f:
                json.dump(deposit_data, f, indent=2)

            print(f"Generated deposit data for {len(deposit_data)} validators using CLI wrapper")
            print(f"Deposit data saved to: {output_file}")
            return deposit_data

        # Otherwise use vault-based approach
        # Load available keys from Vault
        available_keys = self.load_keys_from_vault(vault_manager)

        if len(available_keys) < validator_count:
            raise ValueError(f"Requested {validator_count} validators but only {len(available_keys)} keys available")

        # Select keys for deposit
        selected_keys = available_keys[:validator_count]

        # Generate deposit data
        deposit_data = []
        for i, key_info in enumerate(selected_keys):
            print(f"Debug: Processing key {i+1}/{len(selected_keys)}: {key_info['key_id']}")
            if key_info["status"] not in ["generated", "ready"]:
                print(f"Warning: Key {key_info['key_id']} has status {key_info['status']}")

            try:
                deposit_info = self.create_deposit_data(
                    validator_pubkey=key_info["validator_pubkey"],
                    withdrawal_address=withdrawal_address,
                    network_name=network_name
                )
            except Exception as e:
                print(f"Error creating deposit data for key {key_info['key_id']}: {e}")
                raise

            # Add metadata
            deposit_info["validator_index"] = key_info["index"]
            deposit_info["key_id"] = key_info["key_id"]

            deposit_data.append(deposit_info)

        # Validate deposit data
        print("\n=== Validating Deposit Data ===")
        for i, deposit in enumerate(deposit_data):
            validation = self.validate_deposit_data(deposit)
            if not validation["is_valid"]:
                print(f"❌ Validator {i}: {validation['errors']}")
            else:
                print(f"✅ Validator {i}: Valid")
                if validation["warnings"]:
                    print(f"   ⚠️  Warnings: {validation['warnings']}")

        # Save deposit data to file
        with open(output_file, 'w') as f:
            json.dump(deposit_data, f, indent=2)

        print(f"\nGenerated deposit data for {len(deposit_data)} validators")
        print(f"Deposit data saved to: {output_file}")

        return deposit_data

    def validate_deposit_data(self, deposit_data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate deposit data structure and values"""
        validation_results = {
            "is_valid": True,
            "errors": [],
            "warnings": []
        }
        
        # Check required fields
        required_fields = [
            "pubkey", "withdrawal_credentials", "amount", "signature",
            "deposit_message_root", "deposit_data_root", "fork_version"
        ]
        
        for field in required_fields:
            if field not in deposit_data:
                validation_results["errors"].append(f"Missing required field: {field}")
                validation_results["is_valid"] = False
        
        if not validation_results["is_valid"]:
            return validation_results
        
        # Validate field lengths
        pubkey_length = len(deposit_data["pubkey"])
        if pubkey_length == 66:  # 0x + 32 bytes * 2 (SECP256k1)
            validation_results["warnings"].append("Using SECP256k1 pubkey (32 bytes) instead of BLS12-381 (48 bytes)")
        elif pubkey_length == 98:  # 0x + 48 bytes * 2 (BLS12-381)
            pass  # Correct length
        else:
            validation_results["errors"].append(f"Invalid pubkey length: {pubkey_length} (expected 66 for SECP256k1 or 98 for BLS12-381)")
            validation_results["is_valid"] = False
            
        if len(deposit_data["withdrawal_credentials"]) != 66:  # 0x + 32 bytes * 2
            validation_results["errors"].append("Invalid withdrawal_credentials length")
            validation_results["is_valid"] = False
            
        if len(deposit_data["signature"]) != 194:  # 0x + 96 bytes * 2
            validation_results["errors"].append("Invalid signature length")
            validation_results["is_valid"] = False
            
        if len(deposit_data["deposit_message_root"]) != 66:  # 0x + 32 bytes * 2
            validation_results["errors"].append("Invalid deposit_message_root length")
            validation_results["is_valid"] = False
            
        if len(deposit_data["deposit_data_root"]) != 66:  # 0x + 32 bytes * 2
            validation_results["errors"].append("Invalid deposit_data_root length")
            validation_results["is_valid"] = False
        
        # Validate amount
        try:
            amount = int(deposit_data["amount"])
            if amount != 32000000000:  # 32 ETH in Gwei
                validation_results["warnings"].append(f"Amount is {amount} Gwei, expected 32000000000 Gwei")
        except ValueError:
            validation_results["errors"].append("Invalid amount format")
            validation_results["is_valid"] = False
        
        # Validate withdrawal credentials format
        wc = deposit_data["withdrawal_credentials"]
        if not wc.startswith("0x01"):
            validation_results["warnings"].append("Withdrawal credentials should start with 0x01 for ETH1 address")
        
        # Check for zero values (warnings)
        if deposit_data["signature"] == "0x" + "0" * 192:
            validation_results["warnings"].append("Signature is all zeros (testing signature)")
            
        if deposit_data["deposit_message_root"] == "0x" + "0" * 64:
            validation_results["warnings"].append("Deposit message root is all zeros")
            
        if deposit_data["deposit_data_root"] == "0x" + "0" * 64:
            validation_results["warnings"].append("Deposit data root is all zeros")
        
        return validation_results

    def deploy_batch_deposit_contract(self, from_address: str, private_key: str) -> str:
        """Deploy batch deposit contract (simplified version)"""

        # Simplified batch deposit contract bytecode
        # In production, use a proper audited contract like stakefish's
        contract_bytecode = "0x608060405234801561001057600080fd5b50610200806100206000396000f3fe608060405260043610610041576000357c0100000000000000000000000000000000000000000000000000000000900463ffffffff1680634d238c8e14610046575b600080fd5b34801561005257600080fd5b5061005b61005d565b005b7f00000000219ab540356cbb839cbe05303d7705fa73ffffffffffffffffffffffffffffffffffffffff1663228951186040518163ffffffff167c0100000000000000000000000000000000000000000000000000000000028152600401600060405180830381600087803b1580156100d457600080fd5b505af11580156100e8573d6000803e3d6000fd5b50505050565b"

        # Build transaction
        transaction = {
            'from': from_address,
            'data': contract_bytecode,
            'gas': 1000000,
            'gasPrice': self.web3.to_wei('20', 'gwei'),
            'nonce': self.web3.eth.get_transaction_count(from_address),
        }

        # Sign and send transaction
        signed_txn = self.web3.eth.account.sign_transaction(transaction, private_key)
        # Handle both old and new Web3.py versions
        raw_tx = getattr(signed_txn, 'raw_transaction', getattr(signed_txn, 'rawTransaction', None))
        if raw_tx is None:
            raise AttributeError("Cannot find raw transaction data")
        tx_hash = self.web3.eth.send_raw_transaction(raw_tx)

        # Wait for receipt
        receipt = self.web3.eth.wait_for_transaction_receipt(tx_hash)
        contract_address = receipt.contractAddress

        print(f"Batch deposit contract deployed at: {contract_address}")
        self.batch_deposit_contract_address = contract_address

        return contract_address

    def submit_batch_deposit(self, deposit_data: List[Dict[str, Any]], from_address: str,
                           private_key: str, batch_size: int = 100) -> List[str]:
        """Submit batch deposits to the network"""
        if not self.batch_deposit_contract_address:
            raise ValueError("Batch deposit contract not deployed")

        contract = self.web3.eth.contract(
            address=self.batch_deposit_contract_address,
            abi=self.batch_deposit_abi
        )

        tx_hashes = []
        total_deposits = len(deposit_data)

        # Process deposits in batches
        for i in range(0, total_deposits, batch_size):
            batch = deposit_data[i:i + batch_size]

            # Prepare batch data
            pubkeys = [d["pubkey"] for d in batch]
            withdrawal_credentials = [d["withdrawal_credentials"] for d in batch]
            signatures = [d["signature"] for d in batch]
            deposit_data_roots = [d["deposit_data_root"] for d in batch]

            # Calculate total value
            total_value = len(batch) * self.deposit_amount

            # Build transaction
            transaction = contract.functions.batchDeposit(
                pubkeys,
                withdrawal_credentials,
                signatures,
                deposit_data_roots
            ).build_transaction({
                'from': from_address,
                'value': total_value,
                'gas': 300000 * len(batch),
                'gasPrice': self.web3.to_wei('20', 'gwei'),
                'nonce': self.web3.eth.get_transaction_count(from_address),
            })

            # Sign and send
            signed_txn = self.web3.eth.account.sign_transaction(transaction, private_key)
            # Handle both old and new Web3.py versions
            raw_tx = getattr(signed_txn, 'raw_transaction', getattr(signed_txn, 'rawTransaction', None))
            if raw_tx is None:
                raise AttributeError("Cannot find raw transaction data")
            tx_hash = self.web3.eth.send_raw_transaction(raw_tx)

            print(f"Submitted batch {i//batch_size + 1} with {len(batch)} deposits: {tx_hash.hex()}")
            tx_hashes.append(tx_hash.hex())

        return tx_hashes

    def submit_deposits(self, deposit_file: str, config: dict = None) -> bool:
        """Submit deposits from a deposit file to the network"""
        try:
            # Load deposit data from file
            with open(deposit_file, 'r') as f:
                deposit_data = json.load(f)
            
            if not isinstance(deposit_data, list):
                print("❌ Invalid deposit file format")
                return False
            
            print(f"📄 Loaded {len(deposit_data)} deposits from {deposit_file}")
            
            # Validate deposits first
            valid_count = 0
            for i, deposit in enumerate(deposit_data):
                validation = self.validate_deposit_data(deposit)
                if validation["is_valid"]:
                    valid_count += 1
                    if validation["warnings"]:
                        print(f"⚠️  Deposit {i}: {', '.join(validation['warnings'])}")
                else:
                    print(f"❌ Deposit {i} invalid: {', '.join(validation['errors'])}")
            
            print(f"✅ Validated {valid_count}/{len(deposit_data)} deposits")
            
            if valid_count != len(deposit_data):
                print("❌ Some deposits are invalid, cannot submit")
                return False
            
            # Check if Kurtosis testnet is enabled
            if config and config.get("kurtosis_testnet", {}).get("enabled", False):
                return self._submit_to_kurtosis_testnet(deposit_data, config)
            else:
                print("📝 Note: Kurtosis testnet not enabled, only validating deposit data structure")
                print("📝 To enable real submission, set kurtosis_testnet.enabled=true in config")
                return True
                
        except Exception as e:
            print(f"❌ Error processing deposit file: {e}")
            return False

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
            
            # Deposit contract ABI (complete)
            deposit_contract_abi = [
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
            
            # Create contract instance
            contract = w3.eth.contract(
                address=deposit_contract_address,
                abi=deposit_contract_abi
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
                
                # Build transaction
                try:
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
                        'nonce': w3.eth.get_transaction_count(from_address)
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
                    receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
                    if receipt.status == 1:
                        print(f"✅ Deposit {i+1} confirmed in block {receipt.blockNumber}")
                    else:
                        print(f"❌ Deposit {i+1} failed")
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

    def check_deposit_status(self, deposit_data: List[Dict[str, Any]], beacon_url: str = "http://localhost:5052"):
        """Check the status of deposited validators"""
        for deposit in deposit_data:
            pubkey = deposit["pubkey"]

            try:
                # Query beacon node for validator status
                response = requests.get(f"{beacon_url}/eth/v1/beacon/states/head/validators/{pubkey}")
                if response.status_code == 200:
                    validator_data = response.json()["data"]
                    status = validator_data["status"]
                    balance = int(validator_data["balance"]) / 10**9  # Convert to ETH

                    print(f"Validator {pubkey[:12]}...: {status}, Balance: {balance:.2f} ETH")
                else:
                    print(f"Validator {pubkey[:12]}...: Not found in beacon state")

            except requests.RequestException as e:
                print(f"Error checking validator {pubkey[:12]}...: {e}")


def main():
    parser = argparse.ArgumentParser(description="Ethereum Validator Deposit Manager")
    parser.add_argument("--web3-url", default="http://localhost:8545", help="Web3 provider URL")
    parser.add_argument("--vault-url", default="http://localhost:8200", help="Vault URL")
    parser.add_argument("--vault-token", default="dev-root-token", help="Vault token")

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Generate deposit data command
    gen_parser = subparsers.add_parser("generate", help="Generate deposit data")
    gen_parser.add_argument("--withdrawal-address", required=True, help="Withdrawal address")
    gen_parser.add_argument("--validator-count", type=int, required=True, help="Number of validators")
    gen_parser.add_argument("--output", default="deposit_data.json", help="Output file")

    # Deploy contract command
    deploy_parser = subparsers.add_parser("deploy", help="Deploy batch deposit contract")
    deploy_parser.add_argument("--from-address", required=True, help="Deployment address")
    deploy_parser.add_argument("--private-key", required=True, help="Private key")

    # Submit deposits command
    submit_parser = subparsers.add_parser("submit", help="Submit batch deposits")
    submit_parser.add_argument("--deposit-file", required=True, help="Deposit data file")
    submit_parser.add_argument("--from-address", required=True, help="Sender address")
    submit_parser.add_argument("--private-key", required=True, help="Private key")
    submit_parser.add_argument("--batch-size", type=int, default=100, help="Batch size")

    # Check status command
    status_parser = subparsers.add_parser("status", help="Check deposit status")
    status_parser.add_argument("--deposit-file", required=True, help="Deposit data file")
    status_parser.add_argument("--beacon-url", default="http://localhost:5052", help="Beacon node URL")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    deposit_manager = DepositManager(args.web3_url)

    if args.command == "generate":
        # Import here to avoid circular imports
        from key_manager import KeyManager
        vault_manager = KeyManager(args.vault_url, args.vault_token)

        deposit_data = deposit_manager.generate_batch_deposit_data(
            withdrawal_address=args.withdrawal_address,
            validator_count=args.validator_count,
            vault_manager=vault_manager,
            output_file=args.output
        )

    elif args.command == "deploy":
        contract_address = deposit_manager.deploy_batch_deposit_contract(
            from_address=args.from_address,
            private_key=args.private_key
        )

    elif args.command == "submit":
        with open(args.deposit_file, 'r') as f:
            deposit_data = json.load(f)

        tx_hashes = deposit_manager.submit_batch_deposit(
            deposit_data=deposit_data,
            from_address=args.from_address,
            private_key=args.private_key,
            batch_size=args.batch_size
        )

        print(f"Submitted {len(deposit_data)} deposits in {len(tx_hashes)} transactions")

    elif args.command == "status":
        with open(args.deposit_file, 'r') as f:
            deposit_data = json.load(f)

        deposit_manager.check_deposit_status(deposit_data, args.beacon_url)


if __name__ == "__main__":
    main()