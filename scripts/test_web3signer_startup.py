#!/usr/bin/env python3
"""
Test Web3Signer startup without keys
"""

import sys
import os
import requests
import time
from pathlib import Path

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def test_web3signer_startup():
    """Test Web3Signer startup without keys"""
    print("🔍 Testing Web3Signer startup without keys...")
    
    endpoints = [
        ("Web3Signer-1", "http://localhost:9000"),
        ("Web3Signer-2", "http://localhost:9001"),
        ("HAProxy", "http://localhost:9002")
    ]
    
    results = {}
    
    for name, base_url in endpoints:
        print(f"\n📋 Testing {name}...")
        
        # Test upcheck
        try:
            response = requests.get(f"{base_url}/upcheck", timeout=5)
            if response.status_code == 200:
                print(f"✅ {name} upcheck: OK")
                results[f"{name}_upcheck"] = True
            else:
                print(f"❌ {name} upcheck: HTTP {response.status_code}")
                results[f"{name}_upcheck"] = False
        except Exception as e:
            print(f"❌ {name} upcheck: Error: {e}")
            results[f"{name}_upcheck"] = False
        
        # Test public keys endpoint
        try:
            response = requests.get(f"{base_url}/api/v1/eth2/publicKeys", timeout=5)
            if response.status_code == 200:
                keys = response.json()
                print(f"✅ {name} public keys: {len(keys)} keys (expected 0)")
                results[f"{name}_keys"] = True
            else:
                print(f"❌ {name} public keys: HTTP {response.status_code}")
                results[f"{name}_keys"] = False
        except Exception as e:
            print(f"❌ {name} public keys: Error: {e}")
            results[f"{name}_keys"] = False
    
    return results

def test_haproxy_health():
    """Test HAProxy health check"""
    print("\n🔍 Testing HAProxy health check...")
    
    try:
        # Test HAProxy stats
        response = requests.get("http://localhost:8080/haproxy_stats", timeout=5)
        if response.status_code == 200:
            print("✅ HAProxy stats: OK")
            return True
        else:
            print(f"❌ HAProxy stats: HTTP {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ HAProxy stats: Error: {e}")
        return False

def test_vault_connection():
    """Test Vault connection"""
    print("\n🔍 Testing Vault connection...")
    
    try:
        response = requests.get("http://localhost:8200/v1/sys/health", timeout=5)
        if response.status_code == 200:
            print("✅ Vault health: OK")
            return True
        else:
            print(f"❌ Vault health: HTTP {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Vault health: Error: {e}")
        return False

def main():
    """Main test function"""
    print("🚀 Web3Signer Startup Test")
    print("=" * 50)
    
    # Test Web3Signer startup
    startup_results = test_web3signer_startup()
    
    # Test HAProxy health
    haproxy_ok = test_haproxy_health()
    
    # Test Vault connection
    vault_ok = test_vault_connection()
    
    print("\n📊 Test Summary:")
    print("=" * 50)
    
    for name, result in startup_results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{name}: {status}")
    
    print(f"HAProxy Health: {'✅ PASS' if haproxy_ok else '❌ FAIL'}")
    print(f"Vault Connection: {'✅ PASS' if vault_ok else '❌ FAIL'}")
    
    # Recommendations
    print("\n💡 Recommendations:")
    if not all(startup_results.values()):
        print("- Check Web3Signer logs: docker logs web3signer-1 web3signer-2")
        print("- Restart Web3Signer services: docker-compose restart web3signer-1 web3signer-2")
    if not haproxy_ok:
        print("- Check HAProxy logs: docker logs web3signer-lb")
        print("- Restart HAProxy: docker-compose restart haproxy")
    if not vault_ok:
        print("- Check Vault logs: docker logs vault")
        print("- Restart Vault: docker-compose restart vault")
    
    # Overall result
    all_passed = all(startup_results.values()) and haproxy_ok and vault_ok
    print(f"\n🎯 Overall: {'✅ ALL TESTS PASSED' if all_passed else '❌ SOME TESTS FAILED'}")
    
    if all_passed:
        print("\n🎉 Web3Signer is ready for key activation!")
        print("   You can now run: ./validator.sh activate-keys --count 5")
    
    return 0 if all_passed else 1

if __name__ == "__main__":
    sys.exit(main())
