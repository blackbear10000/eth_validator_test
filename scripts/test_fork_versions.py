#!/usr/bin/env python3
"""
测试 Web3Signer 和 devnet 的 fork 版本匹配
"""

import requests
import json
import sys
from typing import Dict, Any

class ForkVersionTester:
    def __init__(self, web3signer_url: str = "http://localhost:9000"):
        self.web3signer_url = web3signer_url.rstrip('/')
        self.session = requests.Session()
        self.session.headers.update({
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        })
    
    def get_devnet_fork_versions(self) -> Dict[str, str]:
        """从 network-config.yaml 获取 devnet fork 版本"""
        return {
            "ALTAIR_FORK_VERSION": "0x20000038",
            "BELLATRIX_FORK_VERSION": "0x30000038", 
            "CAPELLA_FORK_VERSION": "0x40000038",
            "DENEB_FORK_VERSION": "0x50000038"
        }
    
    def test_signing_with_fork_versions(self, public_key: str) -> bool:
        """使用正确的 fork 版本测试签名"""
        try:
            # 使用 devnet 的 fork 版本
            block_data = {
                "type": "BLOCK",
                "fork_info": {
                    "fork": {
                        "previous_version": "0x10000038",  # Genesis fork version
                        "current_version": "0x20000038",    # Altair fork version
                        "epoch": "0"
                    },
                    "genesis_validators_root": "0x0000000000000000000000000000000000000000000000000000000000000000"
                },
                "signingRoot": "0x0000000000000000000000000000000000000000000000000000000000000000"
            }
            
            response = self.session.post(
                f"{self.web3signer_url}/api/v1/eth2/{public_key}/sign",
                json=block_data,
                timeout=10
            )
            
            if response.status_code == 200:
                result = response.json()
                print(f"✅ 使用 devnet fork 版本签名成功: {result.get('signature', 'N/A')[:20]}...")
                return True
            else:
                print(f"❌ 签名失败: {response.status_code} - {response.text}")
                return False
        except Exception as e:
            print(f"❌ 签名异常: {e}")
            return False
    
    def test_sync_committee_signing(self, public_key: str) -> bool:
        """测试 sync committee 签名"""
        try:
            # 测试 sync committee 签名
            sync_data = {
                "type": "SYNC_COMMITTEE_MESSAGE",
                "fork_info": {
                    "fork": {
                        "previous_version": "0x10000038",
                        "current_version": "0x20000038",
                        "epoch": "0"
                    },
                    "genesis_validators_root": "0x0000000000000000000000000000000000000000000000000000000000000000"
                },
                "signingRoot": "0x0000000000000000000000000000000000000000000000000000000000000000"
            }
            
            response = self.session.post(
                f"{self.web3signer_url}/api/v1/eth2/{public_key}/sign",
                json=sync_data,
                timeout=10
            )
            
            if response.status_code == 200:
                result = response.json()
                print(f"✅ Sync committee 签名成功: {result.get('signature', 'N/A')[:20]}...")
                return True
            else:
                print(f"❌ Sync committee 签名失败: {response.status_code} - {response.text}")
                return False
        except Exception as e:
            print(f"❌ Sync committee 签名异常: {e}")
            return False
    
    def run_fork_version_test(self) -> bool:
        """运行 fork 版本测试"""
        print("🔍 测试 Web3Signer 和 devnet 的 fork 版本匹配")
        print("=" * 60)
        
        # 1. 检查 Web3Signer 健康状态
        print("\n1️⃣ 检查 Web3Signer 健康状态...")
        try:
            response = self.session.get(f"{self.web3signer_url}/upcheck", timeout=5)
            if response.status_code != 200:
                print("❌ Web3Signer 不可用")
                return False
            print("✅ Web3Signer 健康")
        except Exception as e:
            print(f"❌ Web3Signer 连接失败: {e}")
            return False
        
        # 2. 获取公钥
        print("\n2️⃣ 获取公钥...")
        try:
            response = self.session.get(f"{self.web3signer_url}/api/v1/eth2/publicKeys", timeout=10)
            if response.status_code != 200:
                print("❌ 无法获取公钥")
                return False
            public_keys = response.json()
            if not public_keys:
                print("❌ 没有可用的公钥")
                return False
            test_key = public_keys[0]
            print(f"✅ 使用测试公钥: {test_key[:20]}...")
        except Exception as e:
            print(f"❌ 获取公钥失败: {e}")
            return False
        
        # 3. 显示 devnet fork 版本
        print("\n3️⃣ Devnet Fork 版本:")
        devnet_versions = self.get_devnet_fork_versions()
        for fork, version in devnet_versions.items():
            print(f"  {fork}: {version}")
        
        # 4. 测试区块签名
        print("\n4️⃣ 测试区块签名...")
        block_success = self.test_signing_with_fork_versions(test_key)
        
        # 5. 测试 sync committee 签名
        print("\n5️⃣ 测试 Sync Committee 签名...")
        sync_success = self.test_sync_committee_signing(test_key)
        
        # 6. 总结
        print("\n" + "=" * 60)
        print("📊 测试结果:")
        print("=" * 60)
        print(f"区块签名: {'✅ 成功' if block_success else '❌ 失败'}")
        print(f"Sync Committee 签名: {'✅ 成功' if sync_success else '❌ 失败'}")
        
        if block_success and sync_success:
            print("\n🎉 所有测试通过！Web3Signer 配置正确。")
            return True
        else:
            print("\n⚠️  部分测试失败，请检查 Web3Signer 配置。")
            return False

def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Web3Signer Fork 版本测试工具')
    parser.add_argument('--url', default='http://localhost:9000', 
                       help='Web3Signer 服务 URL')
    
    args = parser.parse_args()
    
    tester = ForkVersionTester(args.url)
    success = tester.run_fork_version_test()
    
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
