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

    def list_active_keys_in_vault(self, verbose: bool = False) -> List[str]:
        """List only active (non-deleted) validator keys in Vault"""
        all_keys = self.list_keys_in_vault()
        active_keys = []
        deleted_count = 0
        error_count = 0
        
        for key_id in all_keys:
            status = self.check_key_status(key_id)
            
            if status == "active":
                active_keys.append(key_id)
            elif status in ["deleted", "destroyed"]:
                deleted_count += 1
                if verbose:
                    print(f"Key {key_id} is {status}, skipping")
            else:  # error
                error_count += 1
                if verbose:
                    print(f"Failed to check key {key_id} status")
        
        if verbose:
            if deleted_count > 0:
                print(f"Found {deleted_count} deleted/destroyed keys (skipped)")
            if error_count > 0:
                print(f"Found {error_count} keys with errors (skipped)")
        
        return active_keys

    def check_key_status(self, key_id: str) -> str:
        """Check the status of a key using Vault KV v2 API best practices"""
        try:
            # Method 1: Check metadata first (most efficient)
            metadata_response = requests.get(
                f"{self.vault_url}/v1/secret/metadata/validators/{key_id}",
                headers=self.headers
            )
            
            if metadata_response.status_code != 200:
                return "error"
            
            metadata = metadata_response.json().get("data", {})
            
            # Check if key has deletion_time (soft deleted)
            if metadata.get("deletion_time"):
                if metadata.get("destroyed", False):
                    return "destroyed"
                else:
                    return "deleted"
            
            # Method 2: Check current version and data accessibility
            # For KV v2, we can check the current version
            current_version = metadata.get("current_version")
            if current_version is None:
                return "deleted"  # No current version means key is deleted
            
            # Method 3: Try to read the data with version parameter
            # This is more reliable than just checking /data endpoint
            data_response = requests.get(
                f"{self.vault_url}/v1/secret/data/validators/{key_id}",
                headers=self.headers,
                params={"version": current_version}
            )
            
            if data_response.status_code == 200:
                data = data_response.json()["data"]
                if data.get("data") is None:
                    return "deleted"  # Data is null, key is effectively deleted
                else:
                    return "active"  # Data is accessible
            elif data_response.status_code == 404:
                return "deleted"  # Key not found
            else:
                return "error"  # Other error
                
        except Exception:
            return "error"

    def check_key_status_advanced(self, key_id: str) -> Dict[str, Any]:
        """Advanced key status check with detailed information"""
        result = {
            "status": "unknown",
            "metadata": None,
            "current_version": None,
            "deletion_time": None,
            "destroyed": False,
            "data_accessible": False,
            "error": None
        }
        
        try:
            # Get metadata
            metadata_response = requests.get(
                f"{self.vault_url}/v1/secret/metadata/validators/{key_id}",
                headers=self.headers
            )
            
            if metadata_response.status_code != 200:
                result["status"] = "error"
                result["error"] = f"Metadata request failed: {metadata_response.status_code}"
                return result
            
            metadata = metadata_response.json().get("data", {})
            result["metadata"] = metadata
            result["current_version"] = metadata.get("current_version")
            result["deletion_time"] = metadata.get("deletion_time")
            result["destroyed"] = metadata.get("destroyed", False)
            
            # Determine status based on metadata
            if result["deletion_time"]:
                if result["destroyed"]:
                    result["status"] = "destroyed"
                else:
                    result["status"] = "deleted"
            elif result["current_version"] is None:
                result["status"] = "deleted"
            else:
                # Try to access data
                data_response = requests.get(
                    f"{self.vault_url}/v1/secret/data/validators/{key_id}",
                    headers=self.headers,
                    params={"version": result["current_version"]}
                )
                
                if data_response.status_code == 200:
                    data = data_response.json()["data"]
                    if data.get("data") is None:
                        result["status"] = "deleted"
                    else:
                        result["status"] = "active"
                        result["data_accessible"] = True
                elif data_response.status_code == 404:
                    result["status"] = "deleted"
                else:
                    result["status"] = "error"
                    result["error"] = f"Data request failed: {data_response.status_code}"
            
        except Exception as e:
            result["status"] = "error"
            result["error"] = str(e)
        
        return result

    def get_key_metadata_safe(self, key_id: str) -> Optional[Dict[str, Any]]:
        """Safely retrieve key metadata without triggering errors"""
        try:
            response = requests.get(
                f"{self.vault_url}/v1/secret/data/validators/{key_id}",
                headers=self.headers
            )
            
            if response.status_code == 200:
                data = response.json()["data"]
                # Check if key data is null (deleted but not destroyed)
                if data.get("data") is None:
                    return None
                return data["data"]
            else:
                return None
        except Exception:
            return None

    def destroy_deleted_keys(self, verbose: bool = True) -> int:
        """Permanently destroy all deleted keys in Vault"""
        all_keys = self.list_keys_in_vault()
        destroyed_count = 0
        error_count = 0
        active_count = 0
        already_destroyed_count = 0
        
        if verbose:
            print(f"Processing {len(all_keys)} keys...")
        
        for key_id in all_keys:
            status = self.check_key_status(key_id)
            
            if verbose:
                print(f"Key {key_id}: status = {status}")
            
            if status == "deleted":
                # Key is deleted but not destroyed, destroy it
                destroy_response = requests.delete(
                    f"{self.vault_url}/v1/secret/metadata/validators/{key_id}",
                    headers=self.headers
                )
                
                if destroy_response.status_code in [200, 204]:
                    if verbose:
                        print(f"✅ Permanently destroyed key: {key_id}")
                    destroyed_count += 1
                else:
                    error_count += 1
                    if verbose:
                        print(f"❌ Failed to destroy key {key_id}: {destroy_response.text}")
            elif status == "error":
                # Try to destroy keys that have errors (might be corrupted)
                if verbose:
                    print(f"⚠️  Attempting to destroy key with error status: {key_id}")
                destroy_response = requests.delete(
                    f"{self.vault_url}/v1/secret/metadata/validators/{key_id}",
                    headers=self.headers
                )
                
                if destroy_response.status_code in [200, 204]:
                    if verbose:
                        print(f"✅ Successfully destroyed error key: {key_id}")
                    destroyed_count += 1
                else:
                    error_count += 1
                    if verbose:
                        print(f"❌ Failed to destroy error key {key_id}: {destroy_response.text}")
            elif status == "active":
                active_count += 1
                if verbose:
                    print(f"⏭️  Skipping active key: {key_id}")
            elif status == "destroyed":
                already_destroyed_count += 1
                if verbose:
                    print(f"⏭️  Key already destroyed: {key_id}")
            elif status == "error":
                error_count += 1
                if verbose:
                    print(f"❌ Failed to check key {key_id} status")
        
        if verbose:
            print(f"Summary: {destroyed_count} destroyed, {active_count} active, {already_destroyed_count} already destroyed, {error_count} errors")
        
        return destroyed_count

    def clean_corrupted_keys(self, verbose: bool = True) -> int:
        """Clean keys that have metadata but no accessible data"""
        all_keys = self.list_keys_in_vault()
        cleaned_count = 0
        error_count = 0
        
        if verbose:
            print(f"Processing {len(all_keys)} keys...")
        
        for key_id in all_keys:
            # Check if key has metadata but no accessible data
            try:
                # Check metadata
                metadata_response = requests.get(
                    f"{self.vault_url}/v1/secret/metadata/validators/{key_id}",
                    headers=self.headers
                )
                
                if metadata_response.status_code != 200:
                    continue
                
                metadata = metadata_response.json().get("data", {})
                if metadata.get("deletion_time"):
                    continue  # Skip already deleted keys
                
                # Check if data is accessible
                data_response = requests.get(
                    f"{self.vault_url}/v1/secret/data/validators/{key_id}",
                    headers=self.headers
                )
                
                if data_response.status_code == 200:
                    data = data_response.json()["data"]
                    if data.get("data") is None:
                        # Key has metadata but no data - this is corrupted
                        if verbose:
                            print(f"🧹 Cleaning corrupted key: {key_id}")
                        
                        # Delete the key
                        delete_response = requests.delete(
                            f"{self.vault_url}/v1/secret/metadata/validators/{key_id}",
                            headers=self.headers
                        )
                        
                        if delete_response.status_code in [200, 204]:
                            cleaned_count += 1
                        else:
                            error_count += 1
                            if verbose:
                                print(f"❌ Failed to clean key {key_id}: {delete_response.text}")
                    else:
                        if verbose:
                            print(f"✅ Key {key_id} is healthy")
                else:
                    # Cannot access data - might be corrupted
                    if verbose:
                        print(f"🧹 Cleaning inaccessible key: {key_id}")
                    
                    delete_response = requests.delete(
                        f"{self.vault_url}/v1/secret/metadata/validators/{key_id}",
                        headers=self.headers
                    )
                    
                    if delete_response.status_code in [200, 204]:
                        cleaned_count += 1
                    else:
                        error_count += 1
                        if verbose:
                            print(f"❌ Failed to clean key {key_id}: {delete_response.text}")
                            
            except Exception as e:
                error_count += 1
                if verbose:
                    print(f"❌ Error processing key {key_id}: {e}")
        
        if verbose and error_count > 0:
            print(f"⚠️  Encountered {error_count} errors while processing keys")
        
        return cleaned_count

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
    list_active_parser = subparsers.add_parser("list-active", help="List only active (non-deleted) keys in Vault")
    list_active_parser.add_argument("--verbose", "-v", action="store_true", help="Show detailed information about deleted keys")

    # Destroy deleted command
    destroy_parser = subparsers.add_parser("destroy-deleted", help="Permanently destroy all deleted keys in Vault")
    destroy_parser.add_argument("--quiet", "-q", action="store_true", help="Suppress detailed output")

    # Debug command
    subparsers.add_parser("debug-status", help="Show detailed status of all keys")

    # Advanced debug command
    subparsers.add_parser("debug-advanced", help="Show advanced detailed status of all keys")

    # Clean corrupted command
    clean_parser = subparsers.add_parser("clean-corrupted", help="Remove keys that have metadata but no accessible data")
    clean_parser.add_argument("--quiet", "-q", action="store_true", help="Suppress detailed output")

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
        verbose = getattr(args, 'verbose', False)
        keys = key_manager.list_active_keys_in_vault(verbose=verbose)
        print(f"Found {len(keys)} active keys in Vault:")
        for key_id in keys:
            # Use safe retrieval that won't trigger errors
            key_data = key_manager.get_key_metadata_safe(key_id)
            if key_data and "metadata" in key_data:
                metadata = key_data["metadata"]
                print(f"  {key_id}: {metadata.get('validator_pubkey', 'N/A')[:12]}... (status: {metadata.get('status', 'unknown')})")
            else:
                # This shouldn't happen for active keys, but handle gracefully
                print(f"  {key_id}: [ERROR - Unable to retrieve data]")

    elif args.command == "destroy-deleted":
        print("=== Destroying Deleted Keys ===")
        quiet = getattr(args, 'quiet', False)
        destroyed_count = key_manager.destroy_deleted_keys(verbose=not quiet)
        print(f"✅ Permanently destroyed {destroyed_count} deleted keys")

    elif args.command == "debug-status":
        print("=== Debug: Key Status Information ===")
        all_keys = key_manager.list_keys_in_vault()
        print(f"Total keys found: {len(all_keys)}")
        
        status_counts = {"active": 0, "deleted": 0, "destroyed": 0, "error": 0}
        
        for key_id in all_keys:
            status = key_manager.check_key_status(key_id)
            status_counts[status] += 1
            print(f"  {key_id}: {status}")
        
        print(f"\nStatus Summary:")
        for status, count in status_counts.items():
            print(f"  {status}: {count}")

    elif args.command == "debug-advanced":
        print("=== Advanced Debug: Detailed Key Status Information ===")
        all_keys = key_manager.list_keys_in_vault()
        print(f"Total keys found: {len(all_keys)}")
        
        status_counts = {"active": 0, "deleted": 0, "destroyed": 0, "error": 0}
        
        for key_id in all_keys:
            status_info = key_manager.check_key_status_advanced(key_id)
            status = status_info["status"]
            status_counts[status] += 1
            
            print(f"\nKey: {key_id}")
            print(f"  Status: {status}")
            print(f"  Current Version: {status_info['current_version']}")
            print(f"  Deletion Time: {status_info['deletion_time']}")
            print(f"  Destroyed: {status_info['destroyed']}")
            print(f"  Data Accessible: {status_info['data_accessible']}")
            if status_info['error']:
                print(f"  Error: {status_info['error']}")
        
        print(f"\nStatus Summary:")
        for status, count in status_counts.items():
            print(f"  {status}: {count}")

    elif args.command == "clean-corrupted":
        print("=== Cleaning Corrupted Keys ===")
        quiet = getattr(args, 'quiet', False)
        cleaned_count = key_manager.clean_corrupted_keys(verbose=not quiet)
        print(f"✅ Cleaned {cleaned_count} corrupted keys")

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