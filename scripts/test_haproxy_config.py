#!/usr/bin/env python3
"""
Test HAProxy configuration
"""

import sys
import os
import requests
import time

def test_haproxy_endpoints():
    """Test HAProxy endpoints"""
    print("🔍 Testing HAProxy endpoints...")
    
    endpoints = [
        ("HAProxy Stats", "http://localhost:8080/haproxy_stats"),
        ("Web3Signer LB", "http://localhost:9002/upcheck"),
        ("Web3Signer-1 Direct", "http://localhost:9000/upcheck"),
        ("Web3Signer-2 Direct", "http://localhost:9001/upcheck")
    ]
    
    results = {}
    
    for name, url in endpoints:
        try:
            response = requests.get(url, timeout=5)
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

def test_web3signer_through_haproxy():
    """Test Web3Signer through HAProxy"""
    print("\n🔍 Testing Web3Signer through HAProxy...")
    
    try:
        # Test upcheck
        response = requests.get("http://localhost:9002/upcheck", timeout=5)
        if response.status_code == 200:
            print("✅ HAProxy upcheck: OK")
        else:
            print(f"❌ HAProxy upcheck: HTTP {response.status_code}")
            return False
        
        # Test public keys endpoint
        response = requests.get("http://localhost:9002/api/v1/eth2/publicKeys", timeout=5)
        if response.status_code == 200:
            keys = response.json()
            print(f"✅ HAProxy public keys: {len(keys)} keys loaded")
            return True
        else:
            print(f"❌ HAProxy public keys: HTTP {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ HAProxy test failed: {e}")
        return False

def main():
    """Main test function"""
    print("🚀 HAProxy Configuration Test")
    print("=" * 50)
    
    # Test endpoints
    endpoint_results = test_haproxy_endpoints()
    
    # Test Web3Signer through HAProxy
    web3signer_ok = test_web3signer_through_haproxy()
    
    print("\n📊 Test Summary:")
    print("=" * 50)
    
    for name, result in endpoint_results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{name}: {status}")
    
    print(f"Web3Signer through HAProxy: {'✅ PASS' if web3signer_ok else '❌ FAIL'}")
    
    # Recommendations
    print("\n💡 Recommendations:")
    if not endpoint_results.get("HAProxy Stats", False):
        print("- Check HAProxy container: docker logs web3signer-lb")
    if not endpoint_results.get("Web3Signer LB", False):
        print("- Check HAProxy configuration: cat infra/web3signer/haproxy.cfg")
    if not endpoint_results.get("Web3Signer-1 Direct", False):
        print("- Start Web3Signer-1: docker-compose up -d web3signer-1")
    if not endpoint_results.get("Web3Signer-2 Direct", False):
        print("- Start Web3Signer-2: docker-compose up -d web3signer-2")
    
    # Overall result
    all_passed = all(endpoint_results.values()) and web3signer_ok
    print(f"\n🎯 Overall: {'✅ ALL TESTS PASSED' if all_passed else '❌ SOME TESTS FAILED'}")
    
    return 0 if all_passed else 1

if __name__ == "__main__":
    sys.exit(main())
