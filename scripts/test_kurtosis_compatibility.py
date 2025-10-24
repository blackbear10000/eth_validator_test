#!/usr/bin/env python3
"""
Test Kurtosis network compatibility for deposit generation
"""

import sys
import os
import json
from pathlib import Path

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def test_kurtosis_network_config():
    """Test Kurtosis network configuration"""
    print("🔍 Testing Kurtosis network configuration...")
    
    try:
        from code.utils.deposit_generator import DepositGenerator
        from code.external.ethstaker_deposit.settings import get_devnet_chain_setting
        
        # Test Kurtosis chain setting
        chain_setting = get_devnet_chain_setting(
            network_name='kurtosis',
            genesis_fork_version='0x00000000',
            exit_fork_version='0x00000000',
            genesis_validator_root=None,
            multiplier=1,
            min_activation_amount=32,
            min_deposit_amount=1
        )
        
        print(f"✅ Network Name: {chain_setting.NETWORK_NAME}")
        print(f"✅ Genesis Fork Version: {chain_setting.GENESIS_FORK_VERSION.hex()}")
        print(f"✅ Exit Fork Version: {chain_setting.EXIT_FORK_VERSION.hex()}")
        print(f"✅ Multiplier: {chain_setting.MULTIPLIER}")
        print(f"✅ Min Activation Amount: {chain_setting.MIN_ACTIVATION_AMOUNT}")
        print(f"✅ Min Deposit Amount: {chain_setting.MIN_DEPOSIT_AMOUNT}")
        
        return True
        
    except Exception as e:
        print(f"❌ Kurtosis network configuration test failed: {e}")
        import traceback
        print(traceback.format_exc())
        return False

def test_deposit_generator_network():
    """Test DepositGenerator with kurtosis network"""
    print("\n🔍 Testing DepositGenerator with kurtosis network...")
    
    try:
        from code.utils.deposit_generator import DepositGenerator
        
        # Create deposit generator with kurtosis network
        generator = DepositGenerator(network='kurtosis')
        
        print(f"✅ DepositGenerator created with network: {generator.network}")
        
        # Test chain setting creation
        from code.external.ethstaker_deposit.settings import get_devnet_chain_setting
        chain_setting = get_devnet_chain_setting(
            network_name='kurtosis',
            genesis_fork_version='0x00000000',
            exit_fork_version='0x00000000',
            genesis_validator_root=None,
            multiplier=1,
            min_activation_amount=32,
            min_deposit_amount=1
        )
        
        print(f"✅ Chain setting: {chain_setting.NETWORK_NAME}")
        print(f"   Genesis Fork Version: {chain_setting.GENESIS_FORK_VERSION.hex()}")
        print(f"   Exit Fork Version: {chain_setting.EXIT_FORK_VERSION.hex()}")
        
        return True
        
    except Exception as e:
        print(f"❌ DepositGenerator test failed: {e}")
        import traceback
        print(traceback.format_exc())
        return False

def test_existing_deposit_data():
    """Test existing deposit data compatibility"""
    print("\n🔍 Testing existing deposit data...")
    
    try:
        deposit_file = Path("data/deposits/deposit_data.json")
        if not deposit_file.exists():
            print("⚠️ No existing deposit data found")
            return True
        
        with open(deposit_file, 'r') as f:
            deposit_data = json.load(f)
        
        if not deposit_data:
            print("⚠️ Empty deposit data")
            return True
        
        first_deposit = deposit_data[0]
        
        print(f"📋 Network Name: {first_deposit.get('network_name', 'N/A')}")
        print(f"📋 Fork Version: {first_deposit.get('fork_version', 'N/A')}")
        print(f"📋 Withdrawal Credentials: {first_deposit.get('withdrawal_credentials', 'N/A')}")
        print(f"📋 Amount: {first_deposit.get('amount', 'N/A')}")
        
        # Check compatibility
        network_name = first_deposit.get('network_name')
        fork_version = first_deposit.get('fork_version')
        
        if network_name == 'kurtosis' and fork_version == '00000000':
            print("✅ Deposit data is compatible with Kurtosis network")
            return True
        else:
            print(f"⚠️ Deposit data may not be compatible:")
            print(f"   Expected: network_name='kurtosis', fork_version='00000000'")
            print(f"   Actual: network_name='{network_name}', fork_version='{fork_version}'")
            return False
        
    except Exception as e:
        print(f"❌ Deposit data test failed: {e}")
        return False

def test_kurtosis_config_compatibility():
    """Test compatibility with kurtosis-config.yaml"""
    print("\n🔍 Testing compatibility with kurtosis-config.yaml...")
    
    try:
        kurtosis_config_file = Path("infra/kurtosis/kurtosis-config.yaml")
        if not kurtosis_config_file.exists():
            print("⚠️ kurtosis-config.yaml not found")
            return False
        
        import yaml
        with open(kurtosis_config_file, 'r') as f:
            kurtosis_config = yaml.safe_load(f)
        
        network_params = kurtosis_config.get('network_params', {})
        
        print(f"📋 Kurtosis Network ID: {network_params.get('network_id')}")
        print(f"📋 Deposit Contract: {network_params.get('deposit_contract_address')}")
        print(f"📋 Preset: {network_params.get('preset')}")
        print(f"📋 Withdrawal Type: {network_params.get('withdrawal_type')}")
        
        # Check key parameters
        expected_contract = "0x4242424242424242424242424242424242424242"
        actual_contract = network_params.get('deposit_contract_address')
        
        if actual_contract == expected_contract:
            print("✅ Deposit contract address matches")
        else:
            print(f"⚠️ Deposit contract mismatch: expected {expected_contract}, got {actual_contract}")
        
        if network_params.get('preset') == 'minimal':
            print("✅ Using minimal preset (compatible with fork version 0x00000000)")
        else:
            print(f"⚠️ Using {network_params.get('preset')} preset")
        
        return True
        
    except Exception as e:
        print(f"❌ Kurtosis config test failed: {e}")
        return False

def main():
    """Run all compatibility tests"""
    print("🚀 Kurtosis Network Compatibility Test")
    print("=" * 50)
    
    tests = [
        test_kurtosis_network_config,
        test_deposit_generator_network,
        test_existing_deposit_data,
        test_kurtosis_config_compatibility
    ]
    
    results = []
    for test in tests:
        try:
            result = test()
            results.append(result)
        except Exception as e:
            print(f"❌ Test {test.__name__} failed with exception: {e}")
            results.append(False)
    
    print("\n" + "=" * 50)
    print("📊 Test Results:")
    passed = sum(results)
    total = len(results)
    print(f"✅ Passed: {passed}/{total}")
    
    if passed == total:
        print("🎉 All tests passed! Your setup is compatible with Kurtosis network.")
    else:
        print("⚠️ Some tests failed. Check the output above for details.")
    
    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
