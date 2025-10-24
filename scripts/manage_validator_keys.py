#!/usr/bin/env python3
"""
Remote Keymanager API 管理脚本
用于动态管理 Prysm 验证者密钥
"""

import sys
import os
import json
import requests
import argparse
from pathlib import Path

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(project_root)

class ValidatorKeyManager:
    def __init__(self, validator_url: str = "http://127.0.0.1:7500", auth_token: str = None):
        self.validator_url = validator_url
        self.auth_token = auth_token
        self.headers = {
            "Content-Type": "application/json"
        }
        if auth_token:
            self.headers["Authorization"] = f"Bearer {auth_token}"
    
    def list_keys(self):
        """列出所有验证者密钥"""
        try:
            response = requests.get(f"{self.validator_url}/eth/v1/keystores", headers=self.headers)
            if response.status_code == 200:
                return response.json()
            else:
                print(f"❌ 获取密钥列表失败: {response.status_code}")
                return None
        except Exception as e:
            print(f"❌ 连接验证者失败: {e}")
            return None
    
    def add_keys(self, pubkeys: list):
        """添加验证者密钥"""
        try:
            data = {
                "keystores": pubkeys,
                "passwords": [""] * len(pubkeys)  # Web3Signer 不需要密码
            }
            response = requests.post(f"{self.validator_url}/eth/v1/keystores", 
                                   json=data, headers=self.headers)
            if response.status_code == 200:
                result = response.json()
                print(f"✅ 成功添加 {len(pubkeys)} 个密钥")
                return result
            else:
                print(f"❌ 添加密钥失败: {response.status_code}")
                print(f"   响应: {response.text}")
                return None
        except Exception as e:
            print(f"❌ 添加密钥失败: {e}")
            return None
    
    def remove_keys(self, pubkeys: list):
        """移除验证者密钥"""
        try:
            data = {
                "pubkeys": pubkeys
            }
            response = requests.delete(f"{self.validator_url}/eth/v1/keystores", 
                                     json=data, headers=self.headers)
            if response.status_code == 200:
                result = response.json()
                print(f"✅ 成功移除 {len(pubkeys)} 个密钥")
                return result
            else:
                print(f"❌ 移除密钥失败: {response.status_code}")
                print(f"   响应: {response.text}")
                return None
        except Exception as e:
            print(f"❌ 移除密钥失败: {e}")
            return None
    
    def get_status(self):
        """获取验证者状态"""
        try:
            response = requests.get(f"{self.validator_url}/eth/v1/validator/status", headers=self.headers)
            if response.status_code == 200:
                return response.json()
            else:
                print(f"❌ 获取状态失败: {response.status_code}")
                return None
        except Exception as e:
            print(f"❌ 获取状态失败: {e}")
            return None

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="管理 Prysm 验证者密钥")
    parser.add_argument("--validator-url", default="http://127.0.0.1:7500", help="验证者 API URL")
    parser.add_argument("--auth-token", help="认证令牌")
    parser.add_argument("--list", action="store_true", help="列出所有密钥")
    parser.add_argument("--add", nargs="+", help="添加密钥")
    parser.add_argument("--remove", nargs="+", help="移除密钥")
    parser.add_argument("--status", action="store_true", help="获取验证者状态")
    
    args = parser.parse_args()
    
    manager = ValidatorKeyManager(args.validator_url, args.auth_token)
    
    if args.list:
        print("🔍 列出所有验证者密钥...")
        result = manager.list_keys()
        if result:
            print(json.dumps(result, indent=2))
    
    elif args.add:
        print(f"➕ 添加密钥: {args.add}")
        result = manager.add_keys(args.add)
        if result:
            print(json.dumps(result, indent=2))
    
    elif args.remove:
        print(f"➖ 移除密钥: {args.remove}")
        result = manager.remove_keys(args.remove)
        if result:
            print(json.dumps(result, indent=2))
    
    elif args.status:
        print("📊 获取验证者状态...")
        result = manager.get_status()
        if result:
            print(json.dumps(result, indent=2))
    
    else:
        print("请指定操作: --list, --add, --remove, 或 --status")
        print("示例:")
        print("  python3 scripts/manage_validator_keys.py --list")
        print("  python3 scripts/manage_validator_keys.py --add 0x1234... 0x5678...")
        print("  python3 scripts/manage_validator_keys.py --remove 0x1234...")

if __name__ == "__main__":
    main()
