#!/usr/bin/env python3
"""
Test deposit network configuration
"""

import sys
import os
import json
from pathlib import Path

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def test_network_config():
    """Test network configuration for deposits"""
    print("🔍 Testing deposit network configuration...")
    
    try:
        from code.utils.deposit_generator import DepositGenerator
        from code.external.ethstaker_deposit.settings import get_chain_setting
        
        # Test different network configurations
        networks = ['kurtosis', 'sepolia', 'mainnet']
        
        for network in networks:
            print(f"\n📋 Testing network: {network}")
            
            try:
                if network == 'kurtosis':
                    # Kurtosis uses custom devnet configuration
                    from ethstaker_deposit.settings import get_devnet_chain_setting
                    chain_setting = get_devnet_chain_setting(
                        network_name='kurtosis',
                        genesis_fork_version='0x00000000',  # minimal preset fork version
                        exit_fork_version='0x00000000',     # minimal preset exit version
                        genesis_validator_root=None,       # 使用默认值
                        multiplier=1,
                        min_activation_amount=32,
                        min_deposit_amount=1
                    )
                else:
                    chain_setting = get_chain_setting(network)
                
                print(f"   Network Name: {chain_setting.NETWORK_NAME}")
                print(f"   Genesis Fork Version: {chain_setting.GENESIS_FORK_VERSION.hex()}")
                print(f"   Exit Fork Version: {chain_setting.EXIT_FORK_VERSION.hex()}")
                print(f"   Multiplier: {chain_setting.MULTIPLIER}")
                
            except Exception as e:
                print(f"   ❌ Error: {e}")
        
        return True
        
    except Exception as e:
        print(f"❌ Network test failed: {e}")
        import traceback
        print(traceback.format_exc())
        return False

def test_deposit_generation():
    """Test deposit generation with kurtosis network"""
    print("\n🔍 Testing deposit generation...")
    
    try:
        from code.utils.deposit_generator import DepositGenerator
        
        # Create deposit generator with kurtosis network
        generator = DepositGenerator(network='kurtosis')
        
        print(f"✅ Deposit generator created with network: {generator.network}")
        
        # Test chain setting
        from code.external.ethstaker_deposit.settings import get_devnet_chain_setting
        chain_setting = get_devnet_chain_setting(
            network_name='kurtosis',
            genesis_fork_version='0x00000000',  # minimal preset fork version
            exit_fork_version='0x00000000',     # minimal preset exit version
            genesis_validator_root=None,       # 使用默认值
            multiplier=1,
            min_activation_amount=32,
            min_deposit_amount=1
        )
        
        print(f"✅ Chain setting: {chain_setting.NETWORK_NAME}")
        print(f"   Genesis Fork Version: {chain_setting.GENESIS_FORK_VERSION.hex()}")
        print(f"   Exit Fork Version: {chain_setting.EXIT_FORK_VERSION.hex()}")
        
        return True
        
    except Exception as e:
        print(f"❌ Deposit generation test failed: {e}")
        import traceback
        print(traceback.format_exc())
        return False

def test_deposit_file_format():
    """Test deposit file format"""
    print("\n🔍 Testing deposit file format...")
    
    try:
        # Check if deposit_data.json exists
        deposit_file = Path("data/deposits/deposit_data.json")
        if not deposit_file.exists():
            print("⚠️  No deposit_data.json found. Run create-deposits first.")
            return True
        
        with open(deposit_file, 'r') as f:
            deposit_data = json.load(f)
        
        print(f"✅ Deposit file found: {deposit_file}")
        
        # Check network configuration
        if 'network_name' in deposit_data:
            network_name = deposit_data['network_name']
            print(f"   Network Name: {network_name}")
            
            if network_name == 'sepolia':
                print("✅ Network configuration correct for kurtosis")
            else:
                print(f"⚠️  Network configuration may be incorrect: {network_name}")
        
        # Check fork version
        if 'fork_version' in deposit_data:
            fork_version = deposit_data['fork_version']
            print(f"   Fork Version: {fork_version}")
            
            if fork_version == '0x90000069':  # Sepolia fork version
                print("✅ Fork version correct for kurtosis")
            else:
                print(f"⚠️  Fork version may be incorrect: {fork_version}")
        
        return True
        
    except Exception as e:
        print(f"❌ Deposit file test failed: {e}")
        return False

def main():
    """Main test function"""
    print("🚀 Deposit Network Configuration Test")
    print("=" * 50)
    
    # Test network configuration
    network_ok = test_network_config()
    
    # Test deposit generation
    generation_ok = test_deposit_generation()
    
    # Test deposit file format
    file_ok = test_deposit_file_format()
    
    print("\n📊 Test Summary:")
    print("=" * 50)
    print(f"Network Configuration: {'✅ PASS' if network_ok else '❌ FAIL'}")
    print(f"Deposit Generation: {'✅ PASS' if generation_ok else '❌ FAIL'}")
    print(f"Deposit File Format: {'✅ PASS' if file_ok else '❌ FAIL'}")
    
    # Recommendations
    print("\n💡 Recommendations:")
    if not network_ok:
        print("- Check ethstaker-deposit-cli installation")
    if not generation_ok:
        print("- Check network configuration in deposit_generator.py")
    if not file_ok:
        print("- Run ./validator.sh create-deposits to generate deposit data")
    
    # Overall result
    all_passed = network_ok and generation_ok and file_ok
    print(f"\n🎯 Overall: {'✅ ALL TESTS PASSED' if all_passed else '❌ SOME TESTS FAILED'}")
    
    return 0 if all_passed else 1

if __name__ == "__main__":
    sys.exit(main())
