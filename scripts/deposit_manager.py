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

    def compute_deposit_domain(self, fork_version: str = "0x00000000") -> bytes:
        """Compute deposit domain for signature"""
        # Simplified domain computation for testnet
        domain_type = b'\x03\x00\x00\x00'  # DOMAIN_DEPOSIT
        fork_version_bytes = bytes.fromhex(fork_version.replace('0x', ''))
        genesis_validators_root = b'\x00' * 32  # Use zeros for testnet

        # Domain = domain_type + fork_version
        domain = domain_type + fork_version_bytes + genesis_validators_root[:28]
        return domain[:32]

    def create_deposit_data(self, validator_pubkey: str, withdrawal_address: str,
                           fork_version: str = "0x00000000") -> Dict[str, Any]:
        """Create deposit data for a single validator"""
        # Convert pubkey to bytes
        pubkey_bytes = bytes.fromhex(validator_pubkey.replace('0x', ''))

        # Generate withdrawal credentials
        withdrawal_credentials = self.generate_withdrawal_credentials(withdrawal_address)
        withdrawal_credentials_bytes = bytes.fromhex(withdrawal_credentials.replace('0x', ''))

        # Create deposit message
        deposit_message = {
            "pubkey": pubkey_bytes,
            "withdrawal_credentials": withdrawal_credentials_bytes,
            "amount": self.deposit_amount.to_bytes(8, 'little')
        }

        # For testing purposes, we'll use a dummy signature
        # In production, this should be properly signed with the validator's private key
        dummy_signature = b'\x00' * 96

        # Create deposit data root (simplified)
        # In production, this should be properly computed using SSZ
        deposit_data_root = b'\x00' * 32

        return {
            "pubkey": "0x" + pubkey_bytes.hex(),
            "withdrawal_credentials": withdrawal_credentials,
            "amount": str(self.deposit_amount),
            "signature": "0x" + dummy_signature.hex(),
            "deposit_message_root": "0x" + deposit_data_root.hex(),
            "deposit_data_root": "0x" + deposit_data_root.hex(),
            "fork_version": fork_version,
            "network_name": "devnet",
            "deposit_cli_version": "2.5.0"
        }

    def generate_batch_deposit_data(self, withdrawal_address: str, validator_count: int,
                                   vault_manager, output_file: str = "deposit_data.json",
                                   use_mnemonic: str = None) -> List[Dict[str, Any]]:
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
        for key_info in selected_keys:
            if key_info["status"] not in ["generated", "ready"]:
                print(f"Warning: Key {key_info['key_id']} has status {key_info['status']}")

            deposit_info = self.create_deposit_data(
                validator_pubkey=key_info["validator_pubkey"],
                withdrawal_address=withdrawal_address
            )

            # Add metadata
            deposit_info["validator_index"] = key_info["index"]
            deposit_info["key_id"] = key_info["key_id"]

            deposit_data.append(deposit_info)

        # Save deposit data to file
        with open(output_file, 'w') as f:
            json.dump(deposit_data, f, indent=2)

        print(f"Generated deposit data for {len(deposit_data)} validators")
        print(f"Deposit data saved to: {output_file}")

        return deposit_data

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
        tx_hash = self.web3.eth.send_raw_transaction(signed_txn.rawTransaction)

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
            tx_hash = self.web3.eth.send_raw_transaction(signed_txn.rawTransaction)

            print(f"Submitted batch {i//batch_size + 1} with {len(batch)} deposits: {tx_hash.hex()}")
            tx_hashes.append(tx_hash.hex())

        return tx_hashes

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