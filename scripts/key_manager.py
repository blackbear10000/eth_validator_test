#!/usr/bin/env python3
"""
Validator Key Manager
Handles key generation, storage, and lifecycle management
"""

import os
import json
import argparse
import requests
import subprocess
from typing import List, Dict, Any, Optional
from pathlib import Path


class KeyManager:
    def __init__(self, vault_url: str = "http://localhost:8200", vault_token: str = "dev-root-token"):
        self.vault_url = vault_url
        self.vault_token = vault_token
        self.headers = {"X-Vault-Token": vault_token}

    def store_key_in_vault(self, key_id: str, private_key: str, metadata: Dict[str, Any]) -> bool:
        """Store a private key in Vault"""
        data = {
            "data": {
                "private_key": private_key,
                "metadata": metadata
            }
        }

        response = requests.post(
            f"{self.vault_url}/v1/secret/data/validators/{key_id}",
            headers=self.headers,
            json=data
        )

        if response.status_code == 200:
            print(f"Successfully stored key {key_id} in Vault")
            return True
        else:
            print(f"Failed to store key {key_id}: {response.text}")
            return False

    def retrieve_key_from_vault(self, key_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve a private key from Vault"""
        response = requests.get(
            f"{self.vault_url}/v1/secret/data/validators/{key_id}",
            headers=self.headers
        )

        if response.status_code == 200:
            data = response.json()["data"]
            # Check if key data is null (deleted but not destroyed)
            if data.get("data") is None:
                print(f"Key {key_id} is deleted but not destroyed")
                return None
            return data["data"]
        else:
            print(f"Failed to retrieve key {key_id}: {response.text}")
            return None

    def list_keys_in_vault(self) -> List[str]:
        """List all validator keys in Vault"""
        response = requests.get(
            f"{self.vault_url}/v1/secret/metadata/validators",
            headers=self.headers,
            params={"list": "true"}
        )

        if response.status_code == 200:
            return response.json().get("data", {}).get("keys", [])
        else:
            print(f"Failed to list keys: {response.text}")
            return []

    def list_active_keys_in_vault(self) -> List[str]:
        """List only active (non-deleted) validator keys in Vault"""
        all_keys = self.list_keys_in_vault()
        active_keys = []
        
        for key_id in all_keys:
            # Check if key is active (not deleted)
            response = requests.get(
                f"{self.vault_url}/v1/secret/metadata/validators/{key_id}",
                headers=self.headers
            )
            
            if response.status_code == 200:
                metadata = response.json().get("data", {})
                # Check if key is not deleted (no deletion_time or destroyed)
                if not metadata.get("deletion_time") and not metadata.get("destroyed", False):
                    active_keys.append(key_id)
                else:
                    print(f"Key {key_id} is deleted/destroyed, skipping")
            else:
                print(f"Failed to check key {key_id} status: {response.text}")
        
        return active_keys

    def destroy_deleted_keys(self) -> int:
        """Permanently destroy all deleted keys in Vault"""
        all_keys = self.list_keys_in_vault()
        destroyed_count = 0
        
        for key_id in all_keys:
            # Check if key is deleted but not destroyed
            response = requests.get(
                f"{self.vault_url}/v1/secret/metadata/validators/{key_id}",
                headers=self.headers
            )
            
            if response.status_code == 200:
                metadata = response.json().get("data", {})
                # If key has deletion_time but is not destroyed, destroy it
                if metadata.get("deletion_time") and not metadata.get("destroyed", False):
                    destroy_response = requests.delete(
                        f"{self.vault_url}/v1/secret/metadata/validators/{key_id}",
                        headers=self.headers
                    )
                    
                    if destroy_response.status_code in [200, 204]:
                        print(f"✅ Permanently destroyed key: {key_id}")
                        destroyed_count += 1
                    else:
                        print(f"❌ Failed to destroy key {key_id}: {destroy_response.text}")
        
        return destroyed_count

    def bulk_import_keys(self, keys_dir: str) -> int:
        """Import keys from local directory to Vault"""
        keystores_dir = os.path.join(keys_dir, 'keystores')
        secrets_dir = os.path.join(keys_dir, 'secrets')
        pubkeys_file = os.path.join(keys_dir, 'pubkeys.json')

        if not os.path.exists(pubkeys_file):
            print(f"Public keys index not found: {pubkeys_file}")
            return 0

        with open(pubkeys_file, 'r') as f:
            pubkeys_data = json.load(f)

        imported_count = 0

        for key_info in pubkeys_data:
            index = key_info['index']
            validator_pubkey = key_info['validator_pubkey']

            # Read keystore
            keystore_path = os.path.join(keystores_dir, f'keystore-{index:04d}.json')
            if not os.path.exists(keystore_path):
                print(f"Keystore not found: {keystore_path}")
                continue

            with open(keystore_path, 'r') as f:
                keystore = json.load(f)

            # Read password
            password_path = os.path.join(secrets_dir, f'password-{index:04d}.txt')
            if not os.path.exists(password_path):
                print(f"Password not found: {password_path}")
                continue

            with open(password_path, 'r') as f:
                password = f.read().strip()

            # Prepare metadata
            metadata = {
                "index": index,
                "validator_pubkey": validator_pubkey,
                "withdrawal_pubkey": key_info['withdrawal_pubkey'],
                "keystore": keystore,
                "password": password,
                "status": "generated",
                "created_at": str(subprocess.check_output(["date", "-u", "+%Y-%m-%dT%H:%M:%SZ"]).decode().strip())
            }

            # Generate friendly key ID with date and short pubkey
            import time
            from datetime import datetime
            date_str = datetime.now().strftime("%Y%m%d")
            key_id = f"validator_{index:04d}_{date_str}_{validator_pubkey[:8]}"

            if self.store_key_in_vault(key_id, keystore["crypto"]["cipher"]["message"], metadata):
                imported_count += 1

        return imported_count

    def export_keys_for_web3signer(self, output_dir: str) -> int:
        """Export keys in Web3Signer format"""
        os.makedirs(output_dir, exist_ok=True)

        keys = self.list_keys_in_vault()
        exported_count = 0

        for key_id in keys:
            key_data = self.retrieve_key_from_vault(key_id)
            if not key_data:
                continue

            metadata = key_data.get("metadata", {})
            keystore = metadata.get("keystore")
            password = metadata.get("password")

            if not keystore or not password:
                continue

            # Save keystore file
            keystore_path = os.path.join(output_dir, f"{key_id}.json")
            with open(keystore_path, 'w') as f:
                json.dump(keystore, f, indent=2)

            # Save password file
            password_path = os.path.join(output_dir, f"{key_id}.txt")
            with open(password_path, 'w') as f:
                f.write(password)

            exported_count += 1

        return exported_count

    def get_validator_status(self, pubkey: str, beacon_url: str = "http://localhost:5052") -> Dict[str, Any]:
        """Get validator status from beacon node"""
        try:
            response = requests.get(f"{beacon_url}/eth/v1/beacon/states/head/validators/{pubkey}")
            if response.status_code == 200:
                return response.json()["data"]
            else:
                return {"status": "unknown", "error": response.text}
        except requests.RequestException as e:
            return {"status": "error", "error": str(e)}

    def update_key_status(self, key_id: str, status: str, additional_info: Dict[str, Any] = None):
        """Update key status in Vault"""
        key_data = self.retrieve_key_from_vault(key_id)
        if not key_data:
            return False

        metadata = key_data.get("metadata", {})
        metadata["status"] = status

        if additional_info:
            metadata.update(additional_info)

        data = {
            "data": {
                "private_key": key_data["private_key"],
                "metadata": metadata
            }
        }

        response = requests.post(
            f"{self.vault_url}/v1/secret/data/validators/{key_id}",
            headers=self.headers,
            json=data
        )

        return response.status_code == 200


def main():
    parser = argparse.ArgumentParser(description="Validator Key Manager")
    parser.add_argument("--vault-url", default="http://localhost:8200", help="Vault URL")
    parser.add_argument("--vault-token", default="dev-root-token", help="Vault token")

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Import command
    import_parser = subparsers.add_parser("import", help="Import keys to Vault")
    import_parser.add_argument("--keys-dir", required=True, help="Directory containing generated keys")

    # Export command
    export_parser = subparsers.add_parser("export", help="Export keys for Web3Signer")
    export_parser.add_argument("--output-dir", default="./web3signer/keys", help="Output directory")

    # List command
    subparsers.add_parser("list", help="List keys in Vault")
    
    # List active command
    subparsers.add_parser("list-active", help="List only active (non-deleted) keys in Vault")

    # Destroy deleted command
    subparsers.add_parser("destroy-deleted", help="Permanently destroy all deleted keys in Vault")

    # Status command
    status_parser = subparsers.add_parser("status", help="Check validator status")
    status_parser.add_argument("--beacon-url", default="http://localhost:5052", help="Beacon node URL")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    key_manager = KeyManager(args.vault_url, args.vault_token)

    if args.command == "import":
        count = key_manager.bulk_import_keys(args.keys_dir)
        print(f"Imported {count} keys to Vault")

    elif args.command == "export":
        count = key_manager.export_keys_for_web3signer(getattr(args, 'output_dir', './web3signer/keys'))
        print(f"Exported {count} keys for Web3Signer")

    elif args.command == "list":
        keys = key_manager.list_keys_in_vault()
        print(f"Found {len(keys)} keys in Vault:")
        for key_id in keys:
            key_data = key_manager.retrieve_key_from_vault(key_id)
            if key_data and "metadata" in key_data:
                metadata = key_data["metadata"]
                print(f"  {key_id}: {metadata.get('validator_pubkey', 'N/A')[:12]}... (status: {metadata.get('status', 'unknown')})")
            else:
                print(f"  {key_id}: [DELETED]")

    elif args.command == "list-active":
        keys = key_manager.list_active_keys_in_vault()
        print(f"Found {len(keys)} active keys in Vault:")
        for key_id in keys:
            key_data = key_manager.retrieve_key_from_vault(key_id)
            if key_data and "metadata" in key_data:
                metadata = key_data["metadata"]
                print(f"  {key_id}: {metadata.get('validator_pubkey', 'N/A')[:12]}... (status: {metadata.get('status', 'unknown')})")

    elif args.command == "destroy-deleted":
        print("=== Destroying Deleted Keys ===")
        destroyed_count = key_manager.destroy_deleted_keys()
        print(f"✅ Permanently destroyed {destroyed_count} deleted keys")

    elif args.command == "status":
        keys = key_manager.list_keys_in_vault()
        for key_id in keys:
            key_data = key_manager.retrieve_key_from_vault(key_id)
            if key_data and "metadata" in key_data:
                pubkey = key_data["metadata"].get("validator_pubkey")
                if pubkey:
                    status = key_manager.get_validator_status(pubkey, args.beacon_url)
                    print(f"{key_id}: {status}")


if __name__ == "__main__":
    main()