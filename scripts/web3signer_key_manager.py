#!/usr/bin/env python3
"""
Web3Signer Key Manager
Provides CRUD operations for validator keys through Vault integration
"""

import os
import json
import argparse
import requests
from pathlib import Path
from typing import List, Dict, Any, Optional
from key_manager import KeyManager


class Web3SignerKeyManager:
    def __init__(self, vault_url: str = "http://localhost:8200", vault_token: str = "dev-root-token"):
        self.key_manager = KeyManager(vault_url, vault_token)
        self.web3signer_url = "http://localhost:9000"
    
    def list_keys(self) -> List[Dict[str, Any]]:
        """List all validator keys available to Web3Signer"""
        print("=== Web3Signer Available Keys ===")
        
        # Get keys from Vault
        vault_keys = self.key_manager.list_keys_in_vault()
        if not vault_keys:
            print("No keys found in Vault")
            return []
        
        keys_info = []
        for key_id in vault_keys:
            key_data = self.key_manager.retrieve_key_from_vault(key_id)
            if key_data and "metadata" in key_data:
                metadata = key_data["metadata"]
                key_info = {
                    "key_id": key_id,
                    "index": metadata.get("index", "N/A"),
                    "validator_pubkey": metadata.get("validator_pubkey", "N/A"),
                    "withdrawal_pubkey": metadata.get("withdrawal_pubkey", "N/A"),
                    "status": metadata.get("status", "unknown"),
                    "created_at": metadata.get("created_at", "N/A")
                }
                keys_info.append(key_info)
                
                print(f"🔑 {key_id}")
                print(f"   Index: {key_info['index']}")
                print(f"   Validator Pubkey: {key_info['validator_pubkey'][:20]}...")
                print(f"   Status: {key_info['status']}")
                print(f"   Created: {key_info['created_at']}")
                print()
        
        return keys_info
    
    def add_key(self, keystore_path: str, password: str, index: int = None) -> bool:
        """Add a new validator key to Vault and Web3Signer"""
        print(f"=== Adding Key from {keystore_path} ===")
        
        try:
            # Read keystore file
            with open(keystore_path, 'r') as f:
                keystore = json.load(f)
            
            # Extract public key from keystore
            validator_pubkey = keystore.get("pubkey", "")
            if not validator_pubkey:
                print("❌ No public key found in keystore")
                return False
            
            # Generate key ID
            from datetime import datetime
            date_str = datetime.now().strftime("%Y%m%d")
            key_id = f"validator_{index:04d if index is not None else 'new'}_{date_str}_{validator_pubkey[:8]}"
            
            # Prepare metadata
            metadata = {
                "index": index or 0,
                "validator_pubkey": validator_pubkey,
                "withdrawal_pubkey": "",  # Would need to be extracted from keystore
                "keystore": keystore,
                "password": password,
                "status": "active",
                "created_at": str(subprocess.check_output(["date", "-u", "+%Y-%m-%dT%H:%M:%SZ"]).decode().strip())
            }
            
            # Store in Vault
            if self.key_manager.store_key_in_vault(key_id, keystore["crypto"]["cipher"]["message"], metadata):
                print(f"✅ Key {key_id} added to Vault")
                
                # Export to Web3Signer format
                self.export_to_web3signer()
                print("✅ Key exported to Web3Signer format")
                return True
            else:
                print("❌ Failed to store key in Vault")
                return False
                
        except Exception as e:
            print(f"❌ Error adding key: {e}")
            return False
    
    def remove_key(self, key_id: str) -> bool:
        """Remove a validator key from Vault"""
        print(f"=== Removing Key {key_id} ===")
        
        try:
            # Delete from Vault
            response = requests.delete(
                f"{self.key_manager.vault_url}/v1/secret/data/validators/{key_id}",
                headers=self.key_manager.headers
            )
            
            if response.status_code in [200, 204]:
                print(f"✅ Key {key_id} removed from Vault")
                
                # Re-export to Web3Signer format
                self.export_to_web3signer()
                print("✅ Web3Signer configuration updated")
                return True
            else:
                print(f"❌ Failed to remove key: {response.text}")
                return False
                
        except Exception as e:
            print(f"❌ Error removing key: {e}")
            return False
    
    def update_key_status(self, key_id: str, status: str) -> bool:
        """Update the status of a validator key"""
        print(f"=== Updating Key {key_id} Status to {status} ===")
        
        try:
            # Get current key data
            key_data = self.key_manager.retrieve_key_from_vault(key_id)
            if not key_data:
                print(f"❌ Key {key_id} not found")
                return False
            
            # Update metadata
            metadata = key_data.get("metadata", {})
            metadata["status"] = status
            metadata["updated_at"] = str(subprocess.check_output(["date", "-u", "+%Y-%m-%dT%H:%M:%SZ"]).decode().strip())
            
            # Store updated data
            if self.key_manager.store_key_in_vault(key_id, key_data.get("private_key", ""), metadata):
                print(f"✅ Key {key_id} status updated to {status}")
                return True
            else:
                print(f"❌ Failed to update key status")
                return False
                
        except Exception as e:
            print(f"❌ Error updating key: {e}")
            return False
    
    def export_to_web3signer(self) -> int:
        """Export all keys to Web3Signer format"""
        web3signer_keys_dir = Path("web3signer/keys")
        web3signer_keys_dir.mkdir(parents=True, exist_ok=True)
        
        return self.key_manager.export_keys_for_web3signer(str(web3signer_keys_dir))
    
    def check_web3signer_status(self) -> bool:
        """Check if Web3Signer is running and accessible"""
        try:
            response = requests.get(f"{self.web3signer_url}/upcheck", timeout=5)
            if response.status_code == 200:
                print("✅ Web3Signer is running")
                return True
            else:
                print(f"❌ Web3Signer returned status {response.status_code}")
                return False
        except requests.RequestException as e:
            print(f"❌ Web3Signer is not accessible: {e}")
            return False


def main():
    parser = argparse.ArgumentParser(description="Web3Signer Key Manager")
    parser.add_argument("--vault-url", default="http://localhost:8200", help="Vault URL")
    parser.add_argument("--vault-token", default="dev-root-token", help="Vault token")
    parser.add_argument("--web3signer-url", default="http://localhost:9000", help="Web3Signer URL")
    
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # List command
    subparsers.add_parser("list", help="List all validator keys")
    
    # Add command
    add_parser = subparsers.add_parser("add", help="Add a new validator key")
    add_parser.add_argument("--keystore", required=True, help="Path to keystore file")
    add_parser.add_argument("--password", required=True, help="Keystore password")
    add_parser.add_argument("--index", type=int, help="Validator index")
    
    # Remove command
    remove_parser = subparsers.add_parser("remove", help="Remove a validator key")
    remove_parser.add_argument("--key-id", required=True, help="Key ID to remove")
    
    # Update command
    update_parser = subparsers.add_parser("update", help="Update key status")
    update_parser.add_argument("--key-id", required=True, help="Key ID to update")
    update_parser.add_argument("--status", required=True, choices=["active", "inactive", "deprecated"], help="New status")
    
    # Export command
    subparsers.add_parser("export", help="Export keys to Web3Signer format")
    
    # Status command
    subparsers.add_parser("status", help="Check Web3Signer status")
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    manager = Web3SignerKeyManager(args.vault_url, args.vault_token)
    
    if args.command == "list":
        manager.list_keys()
    
    elif args.command == "add":
        manager.add_key(args.keystore, args.password, args.index)
    
    elif args.command == "remove":
        manager.remove_key(args.key_id)
    
    elif args.command == "update":
        manager.update_key_status(args.key_id, args.status)
    
    elif args.command == "export":
        count = manager.export_to_web3signer()
        print(f"✅ Exported {count} keys to Web3Signer format")
    
    elif args.command == "status":
        manager.check_web3signer_status()


if __name__ == "__main__":
    import subprocess
    main()
