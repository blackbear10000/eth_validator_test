#!/usr/bin/env python3
"""
Test Web3Signer connection and HA setup
"""

import sys
import os
import requests
from pathlib import Path

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def test_web3signer_connections():
    """Test all Web3Signer endpoints"""
    print("🔍 Testing Web3Signer connections...")
    
    endpoints = [
        ("HAProxy (recommended)", "http://localhost:9002"),
        ("Web3Signer-1", "http://localhost:9000"),
        ("Web3Signer-2", "http://localhost:9001")
    ]
    
    results = {}
    
    for name, url in endpoints:
        try:
            response = requests.get(f"{url}/upcheck", timeout=5)
            if response.status_code == 200:
                print(f"✅ {name}: {url} - OK")
                results[name] = True
            else:
                print(f"❌ {name}: {url} - HTTP {response.status_code}")
                results[name] = False
        except Exception as e:
            print(f"❌ {name}: {url} - Error: {e}")
            results[name] = False
    
    return results

def test_web3signer_keys():
    """Test Web3Signer key loading"""
    print("\n🔍 Testing Web3Signer key loading...")
    
    try:
        from code.core.web3signer_manager import Web3SignerManager
        
        manager = Web3SignerManager()
        
        # Test connection
        if manager._test_web3signer_connection():
            print("✅ Web3Signer connection successful")
        else:
            print("❌ Web3Signer connection failed")
            return False
        
        # Test Vault connection
        if manager._test_vault_connection():
            print("✅ Vault connection successful")
        else:
            print("❌ Vault connection failed")
            return False
        
        # Get loaded keys
        loaded_keys = manager.get_loaded_keys()
        print(f"📋 Loaded keys in Web3Signer: {len(loaded_keys)}")
        
        if loaded_keys:
            print("   Active keys:")
            for key in loaded_keys[:5]:  # Show first 5
                print(f"     - {key}")
            if len(loaded_keys) > 5:
                print(f"     ... and {len(loaded_keys) - 5} more")
        
        return True
        
    except Exception as e:
        print(f"❌ Web3Signer test failed: {e}")
        import traceback
        print(traceback.format_exc())
        return False

def test_vault_keys():
    """Test Vault key status"""
    print("\n🔍 Testing Vault key status...")
    
    try:
        from code.core.vault_key_manager import VaultKeyManager
        
        manager = VaultKeyManager()
        
        # Get key counts by status
        all_keys = manager.list_keys()
        
        status_counts = {
            'unused': 0,
            'active': 0,
            'retired': 0,
            'total': len(all_keys)
        }
        
        for key in all_keys:
            if key.status == 'unused':
                status_counts['unused'] += 1
            elif key.status == 'active':
                status_counts['active'] += 1
            elif key.status == 'retired':
                status_counts['retired'] += 1
        
        print(f"📊 Vault key status:")
        print(f"   Total: {status_counts['total']}")
        print(f"   Unused: {status_counts['unused']}")
        print(f"   Active: {status_counts['active']}")
        print(f"   Retired: {status_counts['retired']}")
        
        return True
        
    except Exception as e:
        print(f"❌ Vault test failed: {e}")
        import traceback
        print(traceback.format_exc())
        return False

def main():
    """Main test function"""
    print("🚀 Web3Signer Connection Test")
    print("=" * 50)
    
    # Test connections
    connection_results = test_web3signer_connections()
    
    # Test Web3Signer functionality
    web3signer_ok = test_web3signer_keys()
    
    # Test Vault keys
    vault_ok = test_vault_keys()
    
    print("\n📊 Test Summary:")
    print("=" * 50)
    
    for name, result in connection_results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{name}: {status}")
    
    print(f"Web3Signer Keys: {'✅ PASS' if web3signer_ok else '❌ FAIL'}")
    print(f"Vault Keys: {'✅ PASS' if vault_ok else '❌ FAIL'}")
    
    # Recommendations
    print("\n💡 Recommendations:")
    if not connection_results.get("HAProxy (recommended)", False):
        print("- Start HAProxy: docker-compose up -d haproxy")
    if not connection_results.get("Web3Signer-1", False):
        print("- Start Web3Signer-1: docker-compose up -d web3signer-1")
    if not connection_results.get("Web3Signer-2", False):
        print("- Start Web3Signer-2: docker-compose up -d web3signer-2")
    if not web3signer_ok:
        print("- Check Web3Signer logs: docker logs web3signer-1 web3signer-2")
    if not vault_ok:
        print("- Check Vault connection and token")
    
    # Overall result
    all_passed = all(connection_results.values()) and web3signer_ok and vault_ok
    print(f"\n🎯 Overall: {'✅ ALL TESTS PASSED' if all_passed else '❌ SOME TESTS FAILED'}")
    
    return 0 if all_passed else 1

if __name__ == "__main__":
    sys.exit(main())
