#!/usr/bin/env python3
"""
从 Consul 读取 Vault root token
"""
import requests
import base64
import json
import sys
import os

def get_vault_token_from_consul(consul_addr: str = "localhost:8500") -> str:
    """
    从 Consul KV store 读取 Vault root token
    
    Args:
        consul_addr: Consul 地址
        
    Returns:
        Vault token
    """
    consul_url = f"http://{consul_addr}/v1/kv/vault/root_token"
    
    try:
        response = requests.get(consul_url, timeout=5)
        if response.status_code == 200:
            data = response.json()
            if data and len(data) > 0:
                token_b64 = data[0].get('Value', '')
                if token_b64:
                    token = base64.b64decode(token_b64).decode('utf-8')
                    return token.strip()
        
        print(f"Error: Consul returned status {response.status_code}")
        return None
    except requests.exceptions.RequestException as e:
        print(f"Error connecting to Consul at {consul_addr}: {e}")
        return None

def main():
    """主函数"""
    consul_addr = os.getenv("CONSUL_ADDR", "localhost:8500")
    
    print(f"从 Consul ({consul_addr}) 读取 Vault root token...")
    token = get_vault_token_from_consul(consul_addr)
    
    if token:
        print(f"\nVault Root Token: {token}")
        print("\n请更新以下位置的 VAULT_TOKEN:")
        print("1. docker-compose.yml 中的环境变量")
        print("2. 后端服务的环境变量")
        print("\n或者设置环境变量:")
        print(f"export VAULT_TOKEN={token}")
        return 0
    else:
        print("无法从 Consul 读取 token")
        print("请检查:")
        print("1. Consul 是否运行")
        print("2. Vault 是否已初始化")
        print("3. token 是否已保存到 Consul")
        return 1

if __name__ == "__main__":
    sys.exit(main())

