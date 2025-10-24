#!/usr/bin/env python3
"""
诊断 Vault 中 Web3Signer 密钥格式问题
检查密钥存储格式是否符合 Web3Signer 要求
"""

import sys
import os
import json
import requests
from pathlib import Path

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)
sys.path.insert(0, os.path.join(project_root, 'code'))

def check_vault_web3signer_keys():
    """检查 Vault 中 Web3Signer 密钥的存储格式"""
    print("🔍 检查 Vault 中 Web3Signer 密钥格式...")
    
    vault_url = "http://localhost:8200"
    vault_token = "dev-root-token"
    headers = {"X-Vault-Token": vault_token}
    
    try:
        # 1. 检查 Vault 连接
        print("🔍 检查 Vault 连接...")
        response = requests.get(f"{vault_url}/v1/sys/health", headers=headers, timeout=5)
        if response.status_code != 200:
            print(f"❌ Vault 连接失败: {response.status_code}")
            return False
        print("✅ Vault 连接正常")
        
        # 2. 列出 Web3Signer 密钥路径
        print("\n🔍 检查 Web3Signer 密钥路径...")
        web3signer_path = "/v1/secret/metadata/web3signer-keys"
        response = requests.request("LIST", f"{vault_url}{web3signer_path}", headers=headers, timeout=5)
        
        if response.status_code == 200:
            keys_data = response.json()
            keys = keys_data.get('data', {}).get('keys', [])
            print(f"✅ 找到 {len(keys)} 个 Web3Signer 密钥")
            
            if keys:
                print("\n📋 Web3Signer 密钥列表:")
                for i, key in enumerate(keys, 1):
                    print(f"   {i}. {key}")
                
                # 3. 检查第一个密钥的格式
                print(f"\n🔍 检查密钥格式: {keys[0]}")
                key_path = f"/v1/secret/data/web3signer-keys/{keys[0]}"
                response = requests.get(f"{vault_url}{key_path}", headers=headers, timeout=5)
                
                if response.status_code == 200:
                    key_data = response.json()
                    print("✅ 密钥数据获取成功")
                    print(f"📊 密钥数据结构:")
                    print(f"   路径: {key_path}")
                    print(f"   数据: {json.dumps(key_data, indent=2)}")
                    
                    # 检查私钥格式
                    if 'data' in key_data and 'data' in key_data['data']:
                        private_key = key_data['data']['data'].get('value', '')
                        print(f"\n🔍 私钥格式分析:")
                        print(f"   长度: {len(private_key)}")
                        print(f"   前缀: {private_key[:10]}...")
                        print(f"   后缀: ...{private_key[-10:]}")
                        
                        if len(private_key) == 64:
                            print("✅ 私钥长度正确 (64 字符)")
                        else:
                            print(f"❌ 私钥长度错误: 期望 64，实际 {len(private_key)}")
                        
                        if private_key.isalnum() or all(c in '0123456789abcdef' for c in private_key.lower()):
                            print("✅ 私钥格式正确 (十六进制)")
                        else:
                            print("❌ 私钥格式错误 (包含非十六进制字符)")
                    else:
                        print("❌ 密钥数据结构不正确")
                        print(f"   期望: data.data.value")
                        print(f"   实际: {list(key_data.keys())}")
                else:
                    print(f"❌ 获取密钥数据失败: {response.status_code}")
                    print(f"   响应: {response.text}")
            else:
                print("⚠️  没有找到 Web3Signer 密钥")
                print("💡 请先运行: ./validator.sh load-keys")
        else:
            print(f"❌ 列出密钥失败: {response.status_code}")
            print(f"   响应: {response.text}")
            
    except Exception as e:
        print(f"❌ 检查失败: {e}")
        return False
    
    return True

def check_web3signer_config():
    """检查 Web3Signer 配置"""
    print("\n🔍 检查 Web3Signer 配置...")
    
    try:
        # 检查 Web3Signer 健康状态
        response = requests.get("http://localhost:9000/upcheck", timeout=5)
        if response.status_code == 200:
            print("✅ Web3Signer 服务正常")
        else:
            print(f"❌ Web3Signer 服务异常: {response.status_code}")
            return False
        
        # 检查加载的密钥
        response = requests.get("http://localhost:9000/api/v1/eth2/publicKeys", timeout=5)
        if response.status_code == 200:
            keys = response.json()
            print(f"✅ Web3Signer 中加载了 {len(keys)} 个密钥")
            
            if keys:
                print("📋 加载的密钥:")
                for i, key in enumerate(keys, 1):
                    print(f"   {i}. {key}")
            else:
                print("⚠️  Web3Signer 中没有加载任何密钥")
                print("💡 请检查密钥配置和 Vault 连接")
        else:
            print(f"❌ 获取 Web3Signer 密钥失败: {response.status_code}")
            print(f"   响应: {response.text}")
            
    except Exception as e:
        print(f"❌ 检查 Web3Signer 失败: {e}")
        return False
    
    return True

def check_web3signer_logs():
    """检查 Web3Signer 日志"""
    print("\n🔍 检查 Web3Signer 日志...")
    
    try:
        import subprocess
        
        # 获取最近的 Web3Signer 日志
        result = subprocess.run(['docker', 'logs', '--tail', '20', 'web3signer'], 
                              capture_output=True, text=True, timeout=10)
        
        if result.returncode == 0:
            logs = result.stdout
            print("📋 Web3Signer 最近日志:")
            print("-" * 50)
            print(logs)
            print("-" * 50)
            
            # 检查关键错误
            error_keywords = ['error', 'failed', 'exception', 'timeout', 'connection']
            error_lines = [line for line in logs.split('\n') 
                          if any(keyword in line.lower() for keyword in error_keywords)]
            
            if error_lines:
                print("\n⚠️  发现可能的错误:")
                for line in error_lines:
                    print(f"   {line}")
            else:
                print("✅ 日志中没有发现明显错误")
        else:
            print(f"❌ 获取日志失败: {result.stderr}")
            
    except Exception as e:
        print(f"❌ 检查日志失败: {e}")

def main():
    """主函数"""
    print("🔍 Vault-Web3Signer 密钥格式诊断工具")
    print("=" * 50)
    
    # 1. 检查 Vault 中的密钥格式
    vault_ok = check_vault_web3signer_keys()
    
    # 2. 检查 Web3Signer 配置
    web3signer_ok = check_web3signer_config()
    
    # 3. 检查 Web3Signer 日志
    check_web3signer_logs()
    
    # 4. 总结
    print("\n" + "=" * 50)
    print("📊 诊断结果总结:")
    print("=" * 50)
    
    if vault_ok and web3signer_ok:
        print("✅ Vault 和 Web3Signer 配置正常")
        print("💡 如果仍有签名问题，可能是网络或 Prysm 配置问题")
    else:
        print("❌ 发现配置问题")
        print("💡 建议:")
        print("   1. 检查 Vault 密钥存储格式")
        print("   2. 重新加载密钥到 Web3Signer")
        print("   3. 检查 Web3Signer 日志")
        print("   4. 重启相关服务")

if __name__ == "__main__":
    main()
