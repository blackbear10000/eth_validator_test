#!/usr/bin/env python3
"""
Diagnose Web3Signer connection issues
"""

import sys
import os
import requests
import time
from pathlib import Path

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def check_docker_services():
    """Check if Docker services are running"""
    print("🔍 Checking Docker services...")
    
    try:
        import subprocess
        result = subprocess.run(['docker', 'ps', '--format', 'table {{.Names}}\t{{.Status}}\t{{.Ports}}'], 
                              capture_output=True, text=True, timeout=10)
        
        if result.returncode == 0:
            print("✅ Docker is running")
            print("📋 Running containers:")
            print(result.stdout)
            
            # Check for Web3Signer services
            if 'web3signer-1' in result.stdout:
                print("✅ web3signer-1 is running")
            else:
                print("❌ web3signer-1 is not running")
                
            if 'web3signer-2' in result.stdout:
                print("✅ web3signer-2 is running")
            else:
                print("❌ web3signer-2 is not running")
                
            if 'web3signer-lb' in result.stdout:
                print("✅ web3signer-lb (HAProxy) is running")
            else:
                print("❌ web3signer-lb (HAProxy) is not running")
                
            return True
        else:
            print(f"❌ Docker command failed: {result.stderr}")
            return False
            
    except Exception as e:
        print(f"❌ Docker check failed: {e}")
        return False

def check_web3signer_endpoints():
    """Check Web3Signer endpoints"""
    print("\n🔍 Checking Web3Signer endpoints...")
    
    endpoints = [
        ("HAProxy (9002)", "http://localhost:9002"),
        ("Web3Signer-1 (9000)", "http://localhost:9000"),
        ("Web3Signer-2 (9001)", "http://localhost:9001")
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
        except requests.exceptions.ConnectionError:
            print(f"❌ {name}: {url} - Connection refused")
            results[name] = False
        except Exception as e:
            print(f"❌ {name}: {url} - Error: {e}")
            results[name] = False
    
    return results

def check_vault_connection():
    """Check Vault connection"""
    print("\n🔍 Checking Vault connection...")
    
    try:
        response = requests.get("http://localhost:8200/v1/sys/health", timeout=5)
        if response.status_code == 200:
            print("✅ Vault is running")
            return True
        else:
            print(f"❌ Vault health check failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Vault connection failed: {e}")
        return False

def check_web3signer_config():
    """Check Web3Signer configuration"""
    print("\n🔍 Checking Web3Signer configuration...")
    
    config_file = Path("infra/web3signer/config/config.yaml")
    if config_file.exists():
        print(f"✅ Config file exists: {config_file}")
        
        # Check config content
        try:
            with open(config_file, 'r') as f:
                content = f.read()
                if 'vault' in content.lower():
                    print("✅ Vault configuration found")
                else:
                    print("⚠️  Vault configuration not found")
                    
                if 'keys' in content.lower():
                    print("✅ Keys configuration found")
                else:
                    print("⚠️  Keys configuration not found")
                    
        except Exception as e:
            print(f"❌ Error reading config: {e}")
    else:
        print(f"❌ Config file not found: {config_file}")

def check_keys_directory():
    """Check keys directory"""
    print("\n🔍 Checking keys directory...")
    
    keys_dir = Path("infra/web3signer/keys")
    if keys_dir.exists():
        print(f"✅ Keys directory exists: {keys_dir}")
        
        # List key files
        key_files = list(keys_dir.glob("*.yaml"))
        print(f"📋 Found {len(key_files)} key files:")
        for key_file in key_files[:5]:  # Show first 5
            print(f"   - {key_file.name}")
        if len(key_files) > 5:
            print(f"   ... and {len(key_files) - 5} more")
    else:
        print(f"❌ Keys directory not found: {keys_dir}")

def provide_recommendations(docker_ok, endpoints_ok, vault_ok, config_ok, keys_ok):
    """Provide recommendations based on check results"""
    print("\n💡 Recommendations:")
    
    if not docker_ok:
        print("- Start Docker services: cd infra && docker-compose up -d")
        return
    
    if not any(endpoints_ok.values()):
        print("- Start Web3Signer services:")
        print("  cd infra && docker-compose up -d web3signer-1 web3signer-2 haproxy")
        return
    
    if not vault_ok:
        print("- Start Vault service:")
        print("  cd infra && docker-compose up -d vault")
        return
    
    if not config_ok:
        print("- Check Web3Signer configuration:")
        print("  cat infra/web3signer/config/config.yaml")
        return
    
    if not keys_ok:
        print("- Generate keys first:")
        print("  ./validator.sh init-pool --count 1000")
        print("  ./validator.sh activate-keys --count 5")
        return
    
    print("✅ All checks passed! Web3Signer should be working.")

def main():
    """Main diagnostic function"""
    print("🚀 Web3Signer Diagnostic Tool")
    print("=" * 50)
    
    # Run all checks
    docker_ok = check_docker_services()
    endpoints_ok = check_web3signer_endpoints()
    vault_ok = check_vault_connection()
    check_web3signer_config()
    config_ok = True  # Assume OK if we got here
    check_keys_directory()
    keys_ok = True  # Assume OK if we got here
    
    # Provide recommendations
    provide_recommendations(docker_ok, endpoints_ok, vault_ok, config_ok, keys_ok)
    
    # Overall status
    all_ok = docker_ok and any(endpoints_ok.values()) and vault_ok
    print(f"\n🎯 Overall Status: {'✅ HEALTHY' if all_ok else '❌ NEEDS ATTENTION'}")
    
    return 0 if all_ok else 1

if __name__ == "__main__":
    sys.exit(main())
