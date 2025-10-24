#!/usr/bin/env python3
"""
Detect Kurtosis network fork version dynamically
"""

import sys
import os
import json
import requests
from pathlib import Path

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(project_root)
sys.path.append(os.path.join(project_root, 'code'))

def detect_kurtosis_fork_version():
    """Detect the actual fork version from Kurtosis network"""
    print("🔍 Detecting Kurtosis network fork version...")
    
    try:
        # Try to get fork version from beacon API
        beacon_urls = [
            "http://localhost:5052",  # Prysm beacon API
            "http://localhost:5051",  # Lighthouse beacon API
            "http://localhost:5050",  # Alternative beacon API
        ]
        
        for beacon_url in beacon_urls:
            try:
                print(f"🔗 Trying beacon API: {beacon_url}")
                
                # Get genesis info
                genesis_url = f"{beacon_url}/eth/v1/beacon/genesis"
                response = requests.get(genesis_url, timeout=5)
                
                if response.status_code == 200:
                    genesis_data = response.json()
                    fork_version = genesis_data.get('data', {}).get('genesis_fork_version')
                    
                    if fork_version:
                        print(f"✅ Found fork version: {fork_version}")
                        return fork_version
                        
            except Exception as e:
                print(f"⚠️ Failed to connect to {beacon_url}: {e}")
                continue
        
        # Fallback: try to get from config
        print("🔍 Trying to get fork version from Kurtosis config...")
        
        # Check if we can get it from Kurtosis enclave
        try:
            import subprocess
            result = subprocess.run(['kurtosis', 'enclave', 'ls'], 
                                  capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                print("📋 Kurtosis enclaves found:")
                print(result.stdout)
        except Exception as e:
            print(f"⚠️ Could not list Kurtosis enclaves: {e}")
        
        print("❌ Could not detect fork version automatically")
        return None
        
    except Exception as e:
        print(f"❌ Error detecting fork version: {e}")
        return None

def update_deposit_generator_config(fork_version):
    """Update deposit generator to use detected fork version"""
    print(f"🔧 Updating deposit generator config with fork version: {fork_version}")
    
    try:
        # Update the deposit generator to use dynamic fork version
        deposit_generator_path = Path("code/utils/deposit_generator.py")
        
        if not deposit_generator_path.exists():
            print("❌ Deposit generator file not found")
            return False
        
        # Read current content
        with open(deposit_generator_path, 'r') as f:
            content = f.read()
        
        # Create backup
        backup_path = deposit_generator_path.with_suffix('.py.backup')
        with open(backup_path, 'w') as f:
            f.write(content)
        print(f"💾 Created backup: {backup_path}")
        
        # Update the fork version in the code
        old_fork_version = 'genesis_fork_version=\'0x00000000\''
        new_fork_version = f'genesis_fork_version=\'{fork_version}\''
        
        if old_fork_version in content:
            updated_content = content.replace(old_fork_version, new_fork_version)
            
            with open(deposit_generator_path, 'w') as f:
                f.write(updated_content)
            
            print(f"✅ Updated deposit generator with fork version: {fork_version}")
            return True
        else:
            print("⚠️ Could not find fork version pattern to replace")
            return False
            
    except Exception as e:
        print(f"❌ Error updating deposit generator: {e}")
        return False

def create_dynamic_deposit_generator():
    """Create a dynamic deposit generator that can use custom fork versions"""
    print("🔧 Creating dynamic deposit generator...")
    
    dynamic_generator_code = '''#!/usr/bin/env python3
"""
Dynamic Deposit Generator with configurable fork versions
"""

import sys
import os
from pathlib import Path

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(project_root)
sys.path.append(os.path.join(project_root, 'code'))

from code.utils.deposit_generator import DepositGenerator as BaseDepositGenerator
from code.external.ethstaker_deposit.settings import get_devnet_chain_setting

class DynamicDepositGenerator(BaseDepositGenerator):
    """Dynamic deposit generator that can use custom fork versions"""
    
    def __init__(self, vault_url="http://localhost:8200", vault_token=None, 
                 network='kurtosis', fork_version=None):
        super().__init__(vault_url, vault_token, network)
        self.fork_version = fork_version or self._detect_fork_version()
    
    def _detect_fork_version(self):
        """Detect fork version from running Kurtosis network"""
        try:
            import requests
            
            # Try to get from beacon API
            beacon_urls = [
                "http://localhost:5052",  # Prysm
                "http://localhost:5051",  # Lighthouse
            ]
            
            for beacon_url in beacon_urls:
                try:
                    genesis_url = f"{beacon_url}/eth/v1/beacon/genesis"
                    response = requests.get(genesis_url, timeout=5)
                    
                    if response.status_code == 200:
                        genesis_data = response.json()
                        fork_version = genesis_data.get('data', {}).get('genesis_fork_version')
                        if fork_version:
                            print(f"🔍 Detected fork version: {fork_version}")
                            return fork_version
                except:
                    continue
            
            # Fallback to default
            print("⚠️ Could not detect fork version, using default: 0x00000000")
            return "0x00000000"
            
        except Exception as e:
            print(f"⚠️ Error detecting fork version: {e}")
            return "0x00000000"
    
    def _create_deposit_data(self, key, withdrawal_address):
        """Create deposit data with dynamic fork version"""
        try:
            from ethstaker_deposit.settings import get_devnet_chain_setting
            from ethstaker_deposit.credentials import Credential
            
            # Use detected fork version
            chain_setting = get_devnet_chain_setting(
                network_name='kurtosis',
                genesis_fork_version=self.fork_version,
                exit_fork_version=self.fork_version,
                genesis_validator_root=None,
                multiplier=1,
                min_activation_amount=32,
                min_deposit_amount=1
            )
            
            # Create credential with dynamic fork version
            credential = Credential(
                mnemonic=key.mnemonic,
                mnemonic_password='',
                index=key.index,
                amount=32000000000,  # 32 ETH in Gwei
                chain_setting=chain_setting,
                hex_withdrawal_address=withdrawal_address
            )
            
            # Get deposit data
            deposit_dict = credential.deposit_datum_dict
            
            # Convert to hex strings
            return {
                'pubkey': deposit_dict['pubkey'].hex(),
                'withdrawal_credentials': deposit_dict['withdrawal_credentials'].hex(),
                'amount': deposit_dict['amount'],
                'signature': deposit_dict['signature'].hex(),
                'deposit_message_root': deposit_dict['deposit_message_root'].hex(),
                'deposit_data_root': deposit_dict['deposit_data_root'].hex(),
                'fork_version': deposit_dict['fork_version'].hex(),
                'network_name': deposit_dict['network_name'],
                'deposit_cli_version': deposit_dict['deposit_cli_version']
            }
            
        except Exception as e:
            print(f"❌ Error creating deposit data: {e}")
            raise

if __name__ == "__main__":
    # Test the dynamic generator
    generator = DynamicDepositGenerator()
    print(f"✅ Dynamic generator created with fork version: {generator.fork_version}")
'''
    
    try:
        dynamic_generator_path = Path("code/utils/dynamic_deposit_generator.py")
        with open(dynamic_generator_path, 'w') as f:
            f.write(dynamic_generator_code)
        
        print(f"✅ Created dynamic deposit generator: {dynamic_generator_path}")
        return True
        
    except Exception as e:
        print(f"❌ Error creating dynamic generator: {e}")
        return False

def main():
    """Main function to detect and configure fork version"""
    print("🚀 Kurtosis Fork Version Detection and Configuration")
    print("=" * 60)
    
    # Step 1: Detect fork version
    fork_version = detect_kurtosis_fork_version()
    
    if not fork_version:
        print("❌ Could not detect fork version")
        print("💡 You can manually specify it using:")
        print("   python3 scripts/detect_kurtosis_fork_version.py --fork-version 0x10000038")
        return False
    
    # Step 2: Update deposit generator
    if update_deposit_generator_config(fork_version):
        print("✅ Successfully updated deposit generator")
    else:
        print("⚠️ Could not update deposit generator automatically")
    
    # Step 3: Create dynamic generator
    if create_dynamic_deposit_generator():
        print("✅ Created dynamic deposit generator")
    
    print("\\n🎉 Configuration complete!")
    print(f"📋 Detected fork version: {fork_version}")
    print("💡 You can now use: ./validator.sh create-deposits")
    
    return True

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Detect and configure Kurtosis fork version")
    parser.add_argument("--fork-version", help="Manually specify fork version (e.g., 0x10000038)")
    
    args = parser.parse_args()
    
    if args.fork_version:
        print(f"🔧 Using manually specified fork version: {args.fork_version}")
        if update_deposit_generator_config(args.fork_version):
            print("✅ Successfully updated deposit generator")
        else:
            print("❌ Failed to update deposit generator")
            sys.exit(1)
    else:
        success = main()
        sys.exit(0 if success else 1)
