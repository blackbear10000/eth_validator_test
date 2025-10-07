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

# Add the scripts directory to the path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from key_manager import KeyManager
from deposit_manager import DepositManager
from validator_lifecycle import ValidatorLifecycle
from external_validator_client import ExternalValidatorClientManager


class ExternalValidatorManager:
    """Manages external validators connected to Web3Signer"""
    
    def __init__(self, config_file: str = "test_config.json"):
        """Initialize the external validator manager"""
        self.config_file = config_file
        self.config = self.load_config()
        
        # Service endpoints
        self.web3signer_url = "http://localhost:9000"
        self.vault_url = "http://localhost:8200"
        self.beacon_api_url = self.get_beacon_api_url()
        
        # Initialize managers
        self.key_manager = KeyManager()
        self.deposit_manager = DepositManager()
        self.validator_lifecycle = ValidatorLifecycle()
        self.client_manager = ExternalValidatorClientManager(config_file)
        
        # External validator tracking
        self.external_validators = []
        
    def load_config(self) -> Dict:
        """Load configuration from file"""
        config_path = Path(self.config_file)
        if not config_path.exists():
            # Default configuration
            return {
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
            # Try to get the beacon API URL from Kurtosis
            result = subprocess.run(
                ["kurtosis", "service", "ls", "eth-devnet"],
                capture_output=True, text=True, check=True
            )
            
            # Parse the output to find beacon API port
            lines = result.stdout.split('\n')
            for line in lines:
                if 'cl-' in line and 'lighthouse' in line:
                    # Extract port mapping
                    if '->' in line:
                        parts = line.split('->')
                        if len(parts) > 1:
                            port_part = parts[1].strip()
                            if ':' in port_part:
                                port = port_part.split(':')[1].split('/')[0]
                                return f"http://localhost:{port}"
        except subprocess.CalledProcessError:
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
        try:
            response = requests.get(f"{self.beacon_api_url}/eth/v1/node/health", timeout=5)
            if response.status_code in [200, 206]:
                print("✅ Beacon API is accessible")
            else:
                print("❌ Beacon API is not responding")
                return False
        except requests.RequestException:
            print("❌ Beacon API is not accessible")
            return False
        
        return True
    
    def generate_external_keys(self, count: int = None) -> List[str]:
        """Generate keys for external validators"""
        if count is None:
            count = self.config.get("external_validator_count", 5)
        
        print(f"=== Generating {count} External Validator Keys ===")
        
        # Generate keys
        keys_dir = Path("external_keys")
        keys_dir.mkdir(exist_ok=True)
        
        self.key_manager.generate_keys(
            count=count,
            output_dir=str(keys_dir),
            withdrawal_address=self.config.get("withdrawal_address")
        )
        
        # Import keys to Vault
        print("Importing keys to Vault...")
        self.key_manager.import_keys(str(keys_dir))
        
        # Export keys to Web3Signer format
        print("Exporting keys to Web3Signer...")
        web3signer_keys_dir = Path("web3signer/keys")
        web3signer_keys_dir.mkdir(parents=True, exist_ok=True)
        self.key_manager.export_keys(str(web3signer_keys_dir))
        
        # Get public keys
        public_keys = self.key_manager.list_public_keys()
        self.external_validators = public_keys[:count]
        
        print(f"✅ Generated {len(self.external_validators)} external validator keys")
        return self.external_validators
    
    def create_external_deposits(self) -> str:
        """Create deposit data for external validators"""
        print("=== Creating External Validator Deposits ===")
        
        if not self.external_validators:
            print("❌ No external validators found. Generate keys first.")
            return None
        
        # Create deposit data
        deposits_dir = Path("external_deposits")
        deposits_dir.mkdir(exist_ok=True)
        
        deposit_file = self.deposit_manager.generate_deposits(
            validator_count=len(self.external_validators),
            withdrawal_address=self.config.get("withdrawal_address"),
            output_dir=str(deposits_dir)
        )
        
        print(f"✅ Created deposit data: {deposit_file}")
        return deposit_file
    
    def submit_external_deposits(self, deposit_file: str) -> bool:
        """Submit deposits for external validators"""
        print("=== Submitting External Validator Deposits ===")
        
        if not deposit_file or not Path(deposit_file).exists():
            print("❌ Deposit file not found")
            return False
        
        # Submit deposits
        success = self.deposit_manager.submit_deposits(deposit_file)
        
        if success:
            print("✅ External validator deposits submitted")
        else:
            print("❌ Failed to submit external validator deposits")
        
        return success
    
    def start_external_validator_clients(self) -> bool:
        """Start external validator clients connected to Web3Signer"""
        print("=== Starting External Validator Clients ===")
        
        if not self.external_validators:
            print("❌ No external validators found. Generate keys first.")
            return False
        
        # Start validator clients
        success = self.client_manager.start_validator_clients(self.external_validators)
        
        if success:
            print("✅ External validator clients started")
        else:
            print("❌ Failed to start external validator clients")
        
        return success
    
    def wait_for_external_activation(self) -> bool:
        """Wait for external validators to become active"""
        print("=== Waiting for External Validator Activation ===")
        
        if not self.external_validators:
            print("❌ No external validators to monitor")
            return False
        
        # First wait for validators to be active on the network
        timeout = self.config.get("timeout_activation", 1800)
        success = self.validator_lifecycle.wait_for_activation(
            self.external_validators, timeout=timeout
        )
        
        if success:
            print("✅ External validators are active on the network")
            
            # Then wait for validator clients to recognize them as active
            client_success = self.client_manager.wait_for_validators_active(timeout=300)
            if client_success:
                print("✅ External validator clients are active")
            else:
                print("⚠️ External validators are active but clients may not be fully synced")
        else:
            print("❌ External validators failed to activate")
        
        return success
    
    def monitor_external_validators(self, duration: int = None) -> Dict:
        """Monitor external validator performance"""
        if duration is None:
            duration = self.config.get("monitoring_duration", 600)
        
        print(f"=== Monitoring External Validators for {duration}s ===")
        
        if not self.external_validators:
            print("❌ No external validators to monitor")
            return {}
        
        stats = self.validator_lifecycle.monitor_validators(
            self.external_validators, duration=duration
        )
        
        print("✅ External validator monitoring completed")
        return stats
    
    def test_external_exit(self, validator_count: int = 1) -> bool:
        """Test voluntary exit for external validators"""
        print(f"=== Testing Voluntary Exit for {validator_count} External Validators ===")
        
        if not self.external_validators:
            print("❌ No external validators available for exit")
            return False
        
        # Select validators to exit
        validators_to_exit = self.external_validators[:validator_count]
        
        # Perform voluntary exit
        success = self.validator_lifecycle.voluntary_exit(validators_to_exit)
        
        if success:
            print("✅ External validator exit initiated")
            
            # Wait for exit completion
            timeout = self.config.get("timeout_exit", 1800)
            exit_success = self.validator_lifecycle.wait_for_exit(
                validators_to_exit, timeout=timeout
            )
            
            if exit_success:
                print("✅ External validators successfully exited")
            else:
                print("❌ External validators failed to exit")
            
            return exit_success
        else:
            print("❌ Failed to initiate external validator exit")
            return False
    
    def test_external_withdrawal(self) -> bool:
        """Test withdrawal process for external validators"""
        print("=== Testing External Validator Withdrawal ===")
        
        if not self.external_validators:
            print("❌ No external validators available for withdrawal")
            return False
        
        # Wait for withdrawal
        timeout = self.config.get("timeout_exit", 1800)
        success = self.validator_lifecycle.wait_for_withdrawal(
            self.external_validators, timeout=timeout
        )
        
        if success:
            print("✅ External validators successfully withdrawn")
        else:
            print("❌ External validators failed to withdraw")
        
        return success
    
    def get_external_validator_status(self) -> Dict:
        """Get status of external validators"""
        if not self.external_validators:
            return {}
        
        return self.validator_lifecycle.get_validator_status(self.external_validators)
    
    def cleanup_external_validators(self):
        """Clean up external validator resources"""
        print("=== Cleaning Up External Validator Resources ===")
        
        # Stop validator clients
        self.client_manager.stop_all_clients()
        
        # Remove external keys
        external_keys_dir = Path("external_keys")
        if external_keys_dir.exists():
            import shutil
            shutil.rmtree(external_keys_dir)
            print("✅ Removed external keys directory")
        
        # Remove external deposits
        external_deposits_dir = Path("external_deposits")
        if external_deposits_dir.exists():
            import shutil
            shutil.rmtree(external_deposits_dir)
            print("✅ Removed external deposits directory")
        
        # Clear Web3Signer keys
        web3signer_keys_dir = Path("web3signer/keys")
        if web3signer_keys_dir.exists():
            for key_file in web3signer_keys_dir.glob("*.json"):
                key_file.unlink()
            print("✅ Cleared Web3Signer keys")
        
        # Remove validator client data
        validator_data_dir = Path("external_validator_data")
        if validator_data_dir.exists():
            import shutil
            shutil.rmtree(validator_data_dir)
            print("✅ Removed validator client data")
        
        self.external_validators = []
        print("✅ External validator cleanup completed")


def main():
    """Main function for external validator management"""
    parser = argparse.ArgumentParser(description="External Validator Manager")
    parser.add_argument("command", choices=[
        "check-services", "generate-keys", "create-deposits", "submit-deposits",
        "start-clients", "wait-activation", "monitor", "test-exit", "test-withdrawal", 
        "status", "cleanup", "full-test"
    ], help="Command to execute")
    parser.add_argument("--count", type=int, help="Number of validators")
    parser.add_argument("--config", default="test_config.json", help="Config file")
    
    args = parser.parse_args()
    
    # Initialize manager
    manager = ExternalValidatorManager(args.config)
    
    try:
        if args.command == "check-services":
            success = manager.check_services()
            sys.exit(0 if success else 1)
        
        elif args.command == "generate-keys":
            manager.generate_external_keys(args.count)
        
        elif args.command == "create-deposits":
            manager.create_external_deposits()
        
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
