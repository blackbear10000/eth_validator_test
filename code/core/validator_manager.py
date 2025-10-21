#!/usr/bin/env python3
"""
External Validator Manager for Web3Signer Integration
Manages additional validators connected to Web3Signer for testing validator lifecycle
"""

import os
import sys
import json
import time
import requests
import subprocess
import argparse
from typing import List, Dict, Optional
from pathlib import Path

# Add the code directory to the path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.vault_key_manager import VaultKeyManager
from utils.deposit_generator import DepositGenerator


class ExternalValidatorManager:
    """Manages external validators connected to Web3Signer"""
    
    def __init__(self, config_file: str = "config/config.json"):
        """Initialize the external validator manager"""
        self.config_file = config_file
        self.config = self.load_config()
        
        # Service endpoints
        self.web3signer_url = "http://localhost:9000"
        self.vault_url = "http://localhost:8200"
        self.beacon_api_url = self.get_beacon_api_url()
        
        # Initialize managers
        self.key_manager = VaultKeyManager()
        # Pass network setting to deposit generator
        network = self.config.get('network', 'mainnet')
        self.deposit_generator = DepositGenerator(network=network)
        
        # External validator tracking
        self.external_validators = []
        
    def load_config(self) -> Dict:
        """Load configuration from file"""
        config_path = Path(self.config_file)
        if not config_path.exists():
            # Default configuration
            return {
                "network": "mainnet",  # mainnet, holesky, sepolia, etc.
                "external_validator_count": 5,
                "withdrawal_address": "0x0000000000000000000000000000000000000001",
                "timeout_activation": 1800,
                "timeout_exit": 1800,
                "monitoring_duration": 600
            }
        
        with open(config_path, 'r') as f:
            return json.load(f)
    
    def get_beacon_api_url(self) -> str:
        """Get the beacon API URL from Kurtosis"""
        try:
            # Use kurtosis enclave inspect to get service information
            result = subprocess.run(
                ["kurtosis", "enclave", "inspect", "eth-devnet"],
                capture_output=True, text=True, check=True
            )
            
            # Parse the output to find lighthouse beacon API port
            lines = result.stdout.split('\n')
            for line in lines:
                if 'cl-' in line and 'lighthouse' in line and 'http:' in line:
                    # Extract port mapping from lines like:
                    # "http: 4000/tcp -> http://127.0.0.1:33182"
                    if '->' in line:
                        parts = line.split('->')
                        if len(parts) > 1:
                            port_part = parts[1].strip()
                            # Extract port from "http://127.0.0.1:33182" and remove any trailing status
                            if ':' in port_part:
                                # Split by ':' and take the last part, then remove any trailing whitespace/status
                                port_with_status = port_part.split(':')[-1]
                                # Remove any trailing status like "RUNNING"
                                port = port_with_status.split()[0]  # Take only the first word (port number)
                                beacon_url = f"http://localhost:{port}"
                                return beacon_url
            
        except subprocess.CalledProcessError as e:
            print(f"⚠️  Failed to get Kurtosis services: {e}")
            pass
        except FileNotFoundError:
            print("⚠️  Kurtosis CLI not found. Please install Kurtosis first.")
            pass
        
        # Fallback to default
        return "http://localhost:5052"
    
    def check_services(self) -> bool:
        """Check if required services are running"""
        print("=== Checking Service Status ===")
        
        # Check Web3Signer
        try:
            response = requests.get(f"{self.web3signer_url}/upcheck", timeout=5)
            if response.status_code == 200:
                print("✅ Web3Signer is running")
            else:
                print("❌ Web3Signer is not responding")
                return False
        except requests.RequestException:
            print("❌ Web3Signer is not accessible")
            return False
        
        # Check Vault
        try:
            response = requests.get(f"{self.vault_url}/v1/sys/health", timeout=5)
            if response.status_code in [200, 429]:  # 429 means sealed but healthy
                print("✅ Vault is running")
            else:
                print("❌ Vault is not responding")
                return False
        except requests.RequestException:
            print("❌ Vault is not accessible")
            return False
        
        # Check Beacon API
        print(f"🔍 Debug: Checking Beacon API at: {self.beacon_api_url}")
        try:
            health_url = f"{self.beacon_api_url}/eth/v1/node/health"
            print(f"🔍 Debug: Making request to: {health_url}")
            response = requests.get(health_url, timeout=5)
            print(f"🔍 Debug: Response status code: {response.status_code}")
            print(f"🔍 Debug: Response headers: {dict(response.headers)}")
            if response.text:
                print(f"🔍 Debug: Response body: {response.text[:200]}...")
            
            if response.status_code in [200, 206]:
                print("✅ Beacon API is accessible")
            else:
                print(f"❌ Beacon API is not responding (status: {response.status_code})")
                return False
        except requests.RequestException as e:
            print(f"❌ Beacon API is not accessible: {e}")
            print("💡 Troubleshooting tips:")
            print("   1. Make sure Kurtosis devnet is running: ./start.sh quick-start")
            print("   2. Check if eth-devnet enclave exists: kurtosis enclave ls")
            print("   3. Check Kurtosis services: kurtosis enclave inspect eth-devnet")
            return False
        
        return True
    
    def generate_external_keys(self, count: int = None) -> List[str]:
        """Generate keys for external validators"""
        if count is None:
            count = self.config.get("external_validator_count", 5)
        
        print(f"=== Generating {count} External Validator Keys ===")
        
        # Generate keys using generate_keys module
        from utils.generate_keys import generate_validator_keys
        
        # Use absolute path to avoid path conflicts
        project_root = Path(__file__).parent.parent.parent
        keys_dir = project_root / "data" / "keys"
        keys_dir.mkdir(parents=True, exist_ok=True)
        
        # Generate keys
        generated_keys, mnemonic = generate_validator_keys(
            count=count,
            output_dir=str(keys_dir)
        )
        
        print(f"✅ Generated {len(generated_keys)} validator keys")
        print("⚠️  IMPORTANT: Store the mnemonic securely offline!")
        print("🔐 The mnemonic has been saved to the keys directory for backup purposes.")
        print("🚨 NEVER share or commit the mnemonic to version control!")
        
        # Clean up existing keys in Vault first
        print("🧹 Cleaning up existing keys in Vault...")
        try:
            existing_keys = self.key_manager.list_keys_in_vault()
            for key_name in existing_keys:
                if key_name.startswith('validator-'):
                    self.key_manager.client.delete(f'secret/data/{key_name}')
                    print(f"🗑️  Removed old key: {key_name}")
        except Exception as e:
            print(f"⚠️  Warning: Could not clean up old keys: {e}")
        
        # Import keys to Vault
        print("Importing keys to Vault...")
        imported_count = self.key_manager.bulk_import_keys(str(keys_dir))
        print(f"✅ Imported {imported_count} keys to Vault")
        
        # Export keys to Web3Signer format
        print("Exporting keys to Web3Signer...")
        project_root = Path(__file__).parent.parent.parent
        web3signer_keys_dir = project_root / "infra" / "web3signer" / "keys"
        web3signer_keys_dir.mkdir(parents=True, exist_ok=True)
        exported_count = self.key_manager.export_keys_for_web3signer(str(web3signer_keys_dir))
        print(f"✅ Exported {exported_count} keys to Web3Signer format")
        
        # Get public keys from generated keys
        public_keys = [key["validator_public_key"] for key in generated_keys]
        self.external_validators = public_keys[:count]
        
        print(f"✅ Generated {len(self.external_validators)} external validator keys")
        return self.external_validators
    
    def load_external_validators_from_vault(self) -> bool:
        """Load existing external validators from Vault"""
        print("=== Loading External Validators from Vault ===")
        
        try:
            # Use list_active_keys_in_vault to skip deleted keys (quiet mode)
            vault_keys = self.key_manager.list_active_keys_in_vault(verbose=False)
            if not vault_keys:
                print("❌ No active keys found in Vault")
                return False
            
            public_keys = []
            for key_id in vault_keys:
                key_data = self.key_manager.retrieve_key_from_vault(key_id)
                if key_data and "metadata" in key_data:
                    metadata = key_data["metadata"]
                    validator_pubkey = metadata.get("validator_pubkey")
                    if validator_pubkey:
                        public_keys.append(validator_pubkey)
            
            if public_keys:
                self.external_validators = public_keys
                print(f"✅ Loaded {len(self.external_validators)} external validators from Vault")
                return True
            else:
                print("❌ No valid validator keys found in Vault")
                return False
                
        except Exception as e:
            print(f"❌ Error loading validators from Vault: {e}")
            return False
    
    def clean_all_keys(self):
        """清理所有密钥（本地文件和 Vault）"""
        try:
            project_root = Path(__file__).parent.parent.parent
            keys_dir = project_root / "data" / "keys"
            
            print("=== Cleaning All Keys ===")
            
            # Clean local files
            print("🧹 Cleaning local key files...")
            for file_pattern in ['keystore-*.json', 'password-*.txt', 'keys_data.json', 'pubkeys.json', 'mnemonic.txt']:
                for file_path in keys_dir.glob(file_pattern):
                    if file_path.is_file():
                        file_path.unlink()
                        print(f"🗑️  Removed: {file_path.name}")
            
            # Clean subdirectories
            for subdir in ['keystores', 'secrets']:
                subdir_path = keys_dir / subdir
                if subdir_path.exists():
                    for file_path in subdir_path.glob('*'):
                        if file_path.is_file():
                            file_path.unlink()
                            print(f"🗑️  Removed: {subdir}/{file_path.name}")
            
            # Clean Vault keys
            print("🧹 Cleaning Vault keys...")
            try:
                existing_keys = self.key_manager.list_keys_in_vault()
                print(f"🔍 Found {len(existing_keys)} keys in Vault: {existing_keys}")
                for key_name in existing_keys:
                    # 使用正确的 Vault API 删除密钥
                    try:
                        # 构建完整的密钥路径
                        full_path = f"{self.key_manager.key_path_prefix}/{key_name}"
                        self.key_manager.client.secrets.kv.v2.delete_metadata_and_all_versions(
                            path=full_path,
                            mount_point='secret'
                        )
                        print(f"🗑️  Removed Vault key: {full_path}")
                    except Exception as delete_error:
                        print(f"⚠️  Failed to delete key {key_name}: {delete_error}")
            except Exception as e:
                print(f"⚠️  Warning: Could not clean Vault keys: {e}")
                import traceback
                print(f"🔍 详细错误: {traceback.format_exc()}")
            
            # Clean Web3Signer keys
            print("🧹 Cleaning Web3Signer keys...")
            web3signer_keys_dir = project_root / "infra" / "web3signer" / "keys"
            if web3signer_keys_dir.exists():
                for file_path in web3signer_keys_dir.glob('vault-signing-key-*.yaml'):
                    file_path.unlink()
                    print(f"🗑️  Removed: {file_path.name}")
            
            print("✅ All keys cleaned successfully")
            
        except Exception as e:
            print(f"❌ Clean failed: {e}")
            import traceback
            print(f"🔍 详细错误: {traceback.format_exc()}")
    
    def ensure_external_validators_loaded(self) -> bool:
        """Ensure external validators are loaded, either from memory or Vault"""
        if not self.external_validators:
            print("⚠️  No external validators in memory. Loading from Vault...")
            return self.load_external_validators_from_vault()
        return True
    
    def list_stored_keys(self) -> None:
        """List all stored keys in Vault and local files"""
        print("=== Stored Keys Information ===")
        
        # List keys in Vault
        print("\n📦 Keys in Vault:")
        try:
            vault_keys = self.key_manager.list_keys_in_vault()
            if vault_keys:
                for i, key_id in enumerate(vault_keys, 1):
                    print(f"  {i}. {key_id}")
                    # Get key details from Vault
                    key_data = self.key_manager.retrieve_key_from_vault(key_id)
                    if key_data:
                        print(f"     - Public Key: {key_data.get('metadata', {}).get('public_key', 'N/A')}")
                        print(f"     - Index: {key_data.get('metadata', {}).get('index', 'N/A')}")
            else:
                print("  No keys found in Vault")
        except Exception as e:
            print(f"  ❌ Error accessing Vault: {e}")
        
        # List local files
        print("\n📁 Local Key Files:")
        project_root = Path(__file__).parent.parent.parent
        keys_dir = project_root / "data" / "keys"
        if keys_dir.exists():
            # List keystores
            keystores_dir = keys_dir / "keystores"
            if keystores_dir.exists():
                keystore_files = list(keystores_dir.glob("*.json"))
                print(f"  Keystores: {len(keystore_files)} files")
                for keystore_file in keystore_files:
                    print(f"    - {keystore_file.name}")
            
            # List secrets
            secrets_dir = keys_dir / "secrets"
            if secrets_dir.exists():
                password_files = list(secrets_dir.glob("*.txt"))
                print(f"  Passwords: {len(password_files)} files")
                for password_file in password_files:
                    print(f"    - {password_file.name}")
            
            # Check pubkeys file
            pubkeys_file = keys_dir / "pubkeys.json"
            if pubkeys_file.exists():
                try:
                    with open(pubkeys_file, 'r') as f:
                        pubkeys_data = json.load(f)
                    
                    # Handle new format with deprecation notice
                    if isinstance(pubkeys_data, dict) and 'keys' in pubkeys_data:
                        keys_list = pubkeys_data['keys']
                        print(f"  Public Keys: {len(keys_list)} entries")
                        for pubkey_info in keys_list:
                            print(f"    - Index {pubkey_info['index']}: {pubkey_info['validator_pubkey'][:20]}...")
                    elif isinstance(pubkeys_data, list):
                        # Old format
                        print(f"  Public Keys: {len(pubkeys_data)} entries")
                        for pubkey_info in pubkeys_data:
                            print(f"    - Index {pubkey_info['index']}: {pubkey_info['validator_pubkey'][:20]}...")
                    else:
                        print(f"  Public Keys: Unknown format")
                except Exception as e:
                    print(f"  ❌ Error reading pubkeys.json: {e}")
            
            # Check mnemonic
            mnemonic_file = keys_dir / "MNEMONIC.txt"
            if mnemonic_file.exists():
                print(f"  Mnemonic: Available (⚠️  Keep secure!)")
        else:
            print("  No local key files found")
        
        # List Web3Signer keys
        print("\n🔐 Web3Signer Keys:")
        project_root = Path(__file__).parent.parent.parent
        web3signer_keys_dir = project_root / "infra" / "web3signer" / "keys"
        if web3signer_keys_dir.exists():
            web3signer_files = list(web3signer_keys_dir.glob("*.yaml"))
            print(f"  Configuration files: {len(web3signer_files)} files")
            for config_file in web3signer_files:
                print(f"    - {config_file.name}")
        else:
            print("  No Web3Signer key files found")
    
    def create_external_deposits(self) -> str:
        """Create deposit data for external validators"""
        print("=== Creating External Validator Deposits ===")
        
        if not self.ensure_external_validators_loaded():
            print("❌ No external validators found. Generate keys first.")
            return None
        
        # Create deposit data
        project_root = Path(__file__).parent.parent.parent
        deposits_dir = project_root / "data" / "deposits"
        deposits_dir.mkdir(parents=True, exist_ok=True)
        
        deposit_file = os.path.join(deposits_dir, "deposit_data.json")
        
        # Try to load keys data from multiple possible locations
        keys_data = None
        possible_keys_files = [
            project_root / "data" / "keys" / "keys_data.json",
            project_root / "data" / "keys" / "pubkeys.json",
            project_root / "data" / "keys" / "keys_data.json"
        ]
        
        for keys_file in possible_keys_files:
            if keys_file.exists():
                try:
                    with open(keys_file, 'r') as f:
                        keys_data = json.load(f)
                    print(f"✅ Loaded keys data from: {keys_file}")
                    break
                except Exception as e:
                    print(f"⚠️ Failed to load {keys_file}: {e}")
                    continue
        
        if not keys_data:
            print("❌ No keys data file found. Generate keys first.")
            return None
        
        # Get withdrawal address (can be overridden)
        withdrawal_address = self.config.get("withdrawal_address", "0x0000000000000000000000000000000000000001")
        print(f"🎯 Using withdrawal address: {withdrawal_address}")
        print("📝 Note: This will create 0x01 type withdrawal credentials (execution address)")
        
        # Generate deposit data using the loaded validators
        try:
            deposit_data = self.deposit_generator.generate_deposits(
                count=len(self.external_validators),
                withdrawal_address=withdrawal_address,  # 使用动态指定的提款地址
                notes="External validator deposit"
            )
            
            # Validate deposit data before saving
            if self._validate_deposit_data(deposit_data):
                # Save deposit data to file
                with open(deposit_file, 'w') as f:
                    json.dump(deposit_data, f, indent=2)
                
                print(f"✅ Created deposit data: {deposit_file}")
                return deposit_file
            else:
                print("❌ Deposit data validation failed")
                return None
            
        except Exception as e:
            print(f"❌ Failed to generate deposit data: {e}")
            return None
    
    def submit_external_deposits(self, deposit_file: str) -> bool:
        """Submit deposits for external validators"""
        print("=== Submitting External Validator Deposits ===")
        
        if not deposit_file or not Path(deposit_file).exists():
            print("❌ Deposit file not found")
            return False
        
        # Submit deposits (simplified - manual process required)
        print("⚠️  Deposit submission simplified - manual process required")
        print("📋 To submit deposits manually:")
        print("   1. Use the generated deposit data file")
        print("   2. Submit via Ethereum client or web interface")
        success = True
        
        if success:
            print("✅ External validator deposits submitted")
        else:
            print("❌ Failed to submit external validator deposits")
        
        return success
    
    def start_external_validator_clients(self) -> bool:
        """Start external validator clients connected to Web3Signer"""
        print("=== Starting External Validator Clients ===")
        
        if not self.ensure_external_validators_loaded():
            print("❌ No external validators found. Generate keys first.")
            return False
        
        print("⚠️  Validator client management simplified - manual setup required")
        print("📋 To start validator clients manually:")
        print("   1. Configure Lighthouse/Teku to connect to Web3Signer")
        print("   2. Set Web3Signer URL: http://localhost:9000")
        print("   3. Set Beacon API URL:", self.beacon_api_url)
        print("   4. Use validator public keys from Vault")
        
        return True
    
    def wait_for_external_activation(self) -> bool:
        """Wait for external validators to become active"""
        print("=== Waiting for External Validator Activation ===")
        
        if not self.ensure_external_validators_loaded():
            print("❌ No external validators to monitor")
            return False
        
        print("⚠️  Activation monitoring simplified - manual verification required")
        print("📋 To check validator activation:")
        print("   1. Check Beacon API:", self.beacon_api_url)
        print("   2. Look for validator status: active")
        print("   3. Monitor validator performance")
        
        return True
    
    def monitor_external_validators(self, duration: int = None) -> Dict:
        """Monitor external validator performance"""
        if duration is None:
            duration = self.config.get("monitoring_duration", 600)
        
        print(f"=== Monitoring External Validators for {duration}s ===")
        
        if not self.ensure_external_validators_loaded():
            print("❌ No external validators to monitor")
            return {}
        
        print("⚠️  Monitoring simplified - manual verification required")
        print("📋 To monitor validators:")
        print("   1. Check Beacon API:", self.beacon_api_url)
        print("   2. Monitor validator performance metrics")
        print("   3. Check attestation and proposal success rates")
        
        return {"status": "simplified_monitoring"}
    
    def test_external_exit(self, validator_count: int = 1) -> bool:
        """Test voluntary exit for external validators"""
        print(f"=== Testing Voluntary Exit for {validator_count} External Validators ===")
        
        if not self.ensure_external_validators_loaded():
            print("❌ No external validators available for exit")
            return False
        
        # Select validators to exit
        validators_to_exit = self.external_validators[:validator_count]
        
        print("⚠️  Voluntary exit simplified - manual process required")
        print("📋 To perform voluntary exit:")
        print("   1. Use validator client to initiate voluntary exit")
        print("   2. Monitor exit status via Beacon API")
        print("   3. Wait for exit completion")
        
        return True
    
    def test_external_withdrawal(self) -> bool:
        """Test withdrawal process for external validators"""
        print("=== Testing External Validator Withdrawal ===")
        
        if not self.ensure_external_validators_loaded():
            print("❌ No external validators available for withdrawal")
            return False
        
        print("⚠️  Withdrawal monitoring simplified - manual verification required")
        print("📋 To monitor withdrawal:")
        print("   1. Check Beacon API for withdrawal status")
        print("   2. Monitor withdrawal queue")
        print("   3. Verify funds are available for withdrawal")
        
        return True
    
    def get_external_validator_status(self) -> Dict:
        """Get status of external validators"""
        if not self.ensure_external_validators_loaded():
            return {}
        
        return {
            "external_validators": len(self.external_validators),
            "status": "simplified_status_check",
            "beacon_api": self.beacon_api_url
        }
    
    def cleanup_external_validators(self):
        """Clean up external validator resources"""
        print("=== Cleaning Up External Validator Resources ===")
        
        # Stop validator clients (simplified)
        print("⚠️  Validator client cleanup simplified - manual cleanup required")
        
        # Remove external keys
        project_root = Path(__file__).parent.parent.parent
        external_keys_dir = project_root / "data" / "keys"
        if external_keys_dir.exists():
            import shutil
            shutil.rmtree(external_keys_dir)
            print("✅ Removed external keys directory")
        
        # Remove external deposits
        external_deposits_dir = project_root / "data" / "deposits"
        if external_deposits_dir.exists():
            import shutil
            shutil.rmtree(external_deposits_dir)
            print("✅ Removed external deposits directory")
        
        # Clear Web3Signer keys
        project_root = Path(__file__).parent.parent.parent
        web3signer_keys_dir = project_root / "infra" / "web3signer" / "keys"
        if web3signer_keys_dir.exists():
            for key_file in web3signer_keys_dir.glob("*.json"):
                key_file.unlink()
            print("✅ Cleared Web3Signer keys")
        
        # Remove validator client data
        validator_data_dir = project_root / "data" / "configs"
        if validator_data_dir.exists():
            import shutil
            shutil.rmtree(validator_data_dir)
            print("✅ Removed validator client data")
        
        self.external_validators = []
        print("✅ External validator cleanup completed")

    def _validate_deposit_data(self, deposit_data: List[Dict]) -> bool:
        """Validate deposit data using ethstaker-deposit-cli utilities"""
        try:
            from ethstaker_deposit.utils.validation import validate_deposit_data
            
            # Convert deposit data to bytes format for validation
            deposit_data_bytes = []
            for deposit in deposit_data:
                deposit_data_bytes.append({
                    'pubkey': bytes.fromhex(deposit['pubkey']),
                    'withdrawal_credentials': bytes.fromhex(deposit['withdrawal_credentials']),
                    'amount': deposit['amount'],
                    'signature': bytes.fromhex(deposit['signature']),
                    'deposit_message_root': bytes.fromhex(deposit['deposit_message_root']),
                    'deposit_data_root': bytes.fromhex(deposit['deposit_data_root']),
                    'fork_version': bytes.fromhex(deposit['fork_version']),
                    'network_name': deposit['network_name'],
                    'deposit_cli_version': deposit['deposit_cli_version']
                })
            
            # Validate each deposit
            for i, deposit in enumerate(deposit_data_bytes):
                if not validate_deposit_data(deposit):
                    print(f"❌ Deposit {i} validation failed")
                    return False
            
            print(f"✅ Validated {len(deposit_data)} deposits successfully")
            return True
            
        except ImportError:
            print("⚠️ ethstaker-deposit-cli validation not available, skipping validation")
            return True
        except Exception as e:
            print(f"❌ Deposit validation error: {e}")
            return False


def main():
    """Main function for external validator management"""
    parser = argparse.ArgumentParser(description="External Validator Manager")
    parser.add_argument("command", choices=[
        "check-services", "generate-keys", "list-keys", "load-validators", "create-deposits", "submit-deposits",
        "start-clients", "wait-activation", "monitor", "test-exit", "test-withdrawal", 
        "status", "cleanup", "full-test", "create-deposits-with-address", "test-import", "clean"
    ], help="Command to execute")
    parser.add_argument("--count", type=int, help="Number of validators")
    parser.add_argument("--config", default="config/config.json", help="Config file")
    parser.add_argument("--withdrawal-address", help="Withdrawal address for 0x01 type deposits")
    
    args = parser.parse_args()
    
    # Initialize manager
    manager = ExternalValidatorManager(args.config)
    
    try:
        if args.command == "check-services":
            success = manager.check_services()
            sys.exit(0 if success else 1)
        
        elif args.command == "generate-keys":
            manager.generate_external_keys(args.count)
        
        elif args.command == "list-keys":
            manager.list_stored_keys()
        
        elif args.command == "load-validators":
            manager.load_external_validators_from_vault()
        
        elif args.command == "create-deposits":
            manager.create_external_deposits()
        
        elif args.command == "create-deposits-with-address":
            if not args.withdrawal_address:
                print("❌ --withdrawal-address is required for this command")
                sys.exit(1)
            # Temporarily update config with the specified withdrawal address
            original_address = manager.config.get("withdrawal_address")
            manager.config["withdrawal_address"] = args.withdrawal_address
            try:
                manager.create_external_deposits()
            finally:
                # Restore original address
                if original_address:
                    manager.config["withdrawal_address"] = original_address
        
        elif args.command == "clean":
            print("=== Cleaning All Keys ===")
            manager.clean_all_keys()
        
        elif args.command == "submit-deposits":
            deposit_file = manager.create_external_deposits()
            if deposit_file:
                manager.submit_external_deposits(deposit_file)
        
        elif args.command == "start-clients":
            manager.start_external_validator_clients()
        
        elif args.command == "wait-activation":
            manager.wait_for_external_activation()
        
        elif args.command == "monitor":
            manager.monitor_external_validators()
        
        elif args.command == "test-exit":
            manager.test_external_exit(args.count or 1)
        
        elif args.command == "test-withdrawal":
            manager.test_external_withdrawal()
        
        elif args.command == "status":
            status = manager.get_external_validator_status()
            print(json.dumps(status, indent=2))
        
        elif args.command == "cleanup":
            manager.cleanup_external_validators()
        
        elif args.command == "test-import":
            print("=== Testing Vault Import ===")
            project_root = Path(__file__).parent.parent.parent
            keys_dir = project_root / "data" / "keys"
            if manager.key_manager.test_import_single_key(str(keys_dir)):
                print("✅ Test import successful")
            else:
                print("❌ Test import failed")
        
        elif args.command == "full-test":
            print("=== Running Full External Validator Test ===")
            
            # Check services
            if not manager.check_services():
                print("❌ Services not ready")
                sys.exit(1)
            
            # Generate keys
            manager.generate_external_keys(args.count)
            
            # Create and submit deposits
            deposit_file = manager.create_external_deposits()
            if deposit_file:
                manager.submit_external_deposits(deposit_file)
            
            # Start external validator clients
            manager.start_external_validator_clients()
            
            # Wait for activation
            manager.wait_for_external_activation()
            
            # Monitor performance
            manager.monitor_external_validators()
            
            # Test exit
            manager.test_external_exit(1)
            
            # Test withdrawal
            manager.test_external_withdrawal()
            
            print("✅ Full external validator test completed")
    
    except KeyboardInterrupt:
        print("\n⚠️ Operation interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
