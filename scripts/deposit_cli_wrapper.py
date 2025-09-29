#!/usr/bin/env python3
"""
Deposit CLI Wrapper
Provides deposit data generation using either the official deposit CLI or our simplified version
"""

import os
import json
import subprocess
import argparse
from typing import List, Dict, Any, Optional
from pathlib import Path


class DepositCLIWrapper:
    def __init__(self):
        self.deposit_cli_path = self.find_deposit_cli()

    def find_deposit_cli(self) -> Optional[str]:
        """Find the deposit CLI installation"""
        # Check if eth2-deposit-cli is available in scripts directory
        local_path = Path(__file__).parent / "eth2-deposit-cli" / "deposit.py"
        if local_path.exists():
            return str(local_path)

        # Check if deposit CLI is available in PATH
        try:
            result = subprocess.run(["which", "deposit"], capture_output=True, text=True)
            if result.returncode == 0:
                return result.stdout.strip()
        except:
            pass

        return None

    def generate_keys_with_official_cli(self, mnemonic: str, count: int,
                                       withdrawal_address: str, output_dir: str) -> bool:
        """Generate keys using official deposit CLI"""
        if not self.deposit_cli_path:
            return False

        try:
            cmd = [
                "python3", self.deposit_cli_path,
                "existing-mnemonic",
                "--num_validators", str(count),
                "--validator_start_index", "0",
                "--chain", "devnet",
                "--eth1_withdrawal_address", withdrawal_address,
                "--folder", output_dir,
                "--mnemonic", mnemonic
            ]

            # Run the command
            result = subprocess.run(cmd, capture_output=True, text=True, input="\n")

            if result.returncode == 0:
                print(f"✓ Official deposit CLI generated {count} keys successfully")
                return True
            else:
                print(f"✗ Official deposit CLI failed: {result.stderr}")
                return False

        except Exception as e:
            print(f"✗ Error running official deposit CLI: {e}")
            return False

    def convert_deposit_data_format(self, official_deposit_file: str,
                                   keys_dir: str) -> List[Dict[str, Any]]:
        """Convert official deposit data format to our format"""
        if not os.path.exists(official_deposit_file):
            return []

        # Load official deposit data
        with open(official_deposit_file, 'r') as f:
            official_data = json.load(f)

        # Load keystore files to get additional info
        keystores_dir = Path(keys_dir) / "validator_keys"
        converted_data = []

        for i, deposit_entry in enumerate(official_data):
            # Find corresponding keystore
            keystore_pattern = f"keystore-m_12381_3600_{i}_0_0-*.json"
            keystore_files = list(keystores_dir.glob(keystore_pattern))

            if keystore_files:
                keystore_file = keystore_files[0]
                with open(keystore_file, 'r') as f:
                    keystore = json.load(f)

                converted_entry = {
                    "index": i,
                    "key_id": f"validator_{i:04d}_{deposit_entry['pubkey'][:12]}",
                    "validator_pubkey": deposit_entry["pubkey"],
                    "pubkey": deposit_entry["pubkey"],
                    "withdrawal_credentials": deposit_entry["withdrawal_credentials"],
                    "amount": deposit_entry["amount"],
                    "signature": deposit_entry["signature"],
                    "deposit_message_root": deposit_entry["deposit_message_root"],
                    "deposit_data_root": deposit_entry["deposit_data_root"],
                    "fork_version": deposit_entry["fork_version"],
                    "network_name": deposit_entry["network_name"],
                    "deposit_cli_version": deposit_entry["deposit_cli_version"],
                    "keystore": keystore,
                    "keystore_file": str(keystore_file)
                }
                converted_data.append(converted_entry)

        return converted_data

    def generate_deposit_data(self, mnemonic: str, count: int, withdrawal_address: str,
                             output_dir: str = "./keys") -> List[Dict[str, Any]]:
        """Generate deposit data using the best available method"""

        # Try official CLI first
        if self.deposit_cli_path:
            print("Using official eth2-deposit-cli...")

            # Create temporary directory for official CLI output
            cli_output_dir = Path(output_dir) / "cli_output"
            cli_output_dir.mkdir(exist_ok=True)

            success = self.generate_keys_with_official_cli(
                mnemonic, count, withdrawal_address, str(cli_output_dir)
            )

            if success:
                # Look for generated files
                deposit_file = cli_output_dir / "deposit_data-*.json"
                deposit_files = list(cli_output_dir.glob("deposit_data-*.json"))

                if deposit_files:
                    return self.convert_deposit_data_format(
                        str(deposit_files[0]), str(cli_output_dir)
                    )

        # Fallback to our simplified implementation
        print("Using simplified key generation (for testing only)...")
        print("WARNING: This is not suitable for mainnet use!")

        # Import our simplified implementation
        from generate_keys import derive_keys_from_mnemonic, generate_withdrawal_credentials

        keys = derive_keys_from_mnemonic(mnemonic, 0, count)
        deposit_data = []

        for key_info in keys:
            # Create simplified deposit data
            withdrawal_creds = generate_withdrawal_credentials(withdrawal_address)

            deposit_entry = {
                "index": key_info["index"],
                "key_id": f"validator_{key_info['index']:04d}_{key_info['validator_public_key'][:12]}",
                "validator_pubkey": key_info["validator_public_key"],
                "pubkey": key_info["validator_public_key"],
                "withdrawal_credentials": withdrawal_creds,
                "amount": "32000000000",  # 32 ETH in Gwei
                "signature": "0x" + "00" * 96,  # Dummy signature for testing
                "deposit_message_root": "0x" + "00" * 32,
                "deposit_data_root": "0x" + "00" * 32,
                "fork_version": "0x00000000",
                "network_name": "devnet",
                "deposit_cli_version": "simplified-2.5.0",
                "keystore": key_info["keystore"],
                "password": key_info["password"]
            }
            deposit_data.append(deposit_entry)

        return deposit_data


def generate_withdrawal_credentials(withdrawal_address: str) -> str:
    """Generate withdrawal credentials for an address"""
    # For Ethereum 2.0, withdrawal credentials start with 0x01 followed by 11 zeros and the address
    withdrawal_address = withdrawal_address.lower().replace('0x', '')
    withdrawal_credentials = '01' + '00' * 11 + withdrawal_address
    return '0x' + withdrawal_credentials


def main():
    parser = argparse.ArgumentParser(description="Deposit CLI Wrapper")
    parser.add_argument("--mnemonic", required=True, help="Mnemonic phrase")
    parser.add_argument("--count", type=int, required=True, help="Number of validators")
    parser.add_argument("--withdrawal-address", required=True, help="Withdrawal address")
    parser.add_argument("--output-dir", default="./keys", help="Output directory")
    parser.add_argument("--output-file", default="deposit_data.json", help="Output file")

    args = parser.parse_args()

    wrapper = DepositCLIWrapper()

    deposit_data = wrapper.generate_deposit_data(
        mnemonic=args.mnemonic,
        count=args.count,
        withdrawal_address=args.withdrawal_address,
        output_dir=args.output_dir
    )

    # Save deposit data
    with open(args.output_file, 'w') as f:
        json.dump(deposit_data, f, indent=2)

    print(f"Generated {len(deposit_data)} deposit entries")
    print(f"Deposit data saved to: {args.output_file}")


if __name__ == "__main__":
    main()