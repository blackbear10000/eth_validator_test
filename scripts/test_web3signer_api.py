#!/usr/bin/env python3
"""
Web3Signer ETH2 API 测试脚本
基于官方文档: https://consensys.github.io/web3signer/web3signer-eth2.html
"""

import requests
import json
import sys
import time
from typing import Dict, List, Any, Optional

class Web3SignerTester:
    def __init__(self, base_url: str = "http://localhost:9000"):
        self.base_url = base_url.rstrip('/')
        self.session = requests.Session()
        self.session.headers.update({
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        })
    
    def test_upcheck(self) -> bool:
        """测试 Web3Signer 健康检查"""
        try:
            response = self.session.get(f"{self.base_url}/upcheck", timeout=5)
            if response.status_code == 200:
                print("✅ Web3Signer 健康检查通过")
                return True
            else:
                print(f"❌ Web3Signer 健康检查失败: {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ Web3Signer 健康检查异常: {e}")
            return False
    
    def test_eth2_public_keys(self) -> Optional[List[str]]:
        """获取所有 ETH2 公钥"""
        try:
            response = self.session.get(f"{self.base_url}/api/v1/eth2/publicKeys", timeout=10)
            if response.status_code == 200:
                public_keys = response.json()
                print(f"✅ 获取到 {len(public_keys)} 个公钥")
                for i, key in enumerate(public_keys[:5]):  # 只显示前5个
                    print(f"  {i+1}. {key}")
                if len(public_keys) > 5:
                    print(f"  ... 还有 {len(public_keys) - 5} 个公钥")
                return public_keys
            else:
                print(f"❌ 获取公钥失败: {response.status_code} - {response.text}")
                return None
        except Exception as e:
            print(f"❌ 获取公钥异常: {e}")
            return None
    
    def test_eth2_public_key_info(self, public_key: str) -> bool:
        """获取特定公钥信息"""
        try:
            response = self.session.get(f"{self.base_url}/api/v1/eth2/publicKeys/{public_key}", timeout=10)
            if response.status_code == 200:
                info = response.json()
                print(f"✅ 公钥 {public_key[:10]}... 信息:")
                print(f"  - 状态: {info.get('status', 'unknown')}")
                print(f"  - 版本: {info.get('version', 'unknown')}")
                return True
            else:
                print(f"❌ 获取公钥信息失败: {response.status_code} - {response.text}")
                return False
        except Exception as e:
            print(f"❌ 获取公钥信息异常: {e}")
            return False
    
    def test_eth2_sign_block(self, public_key: str) -> bool:
        """测试区块签名"""
        try:
            # 构造一个测试区块数据
            block_data = {
                "type": "BLOCK",
                "fork_info": {
                    "fork": {
                        "previous_version": "0x00000000",
                        "current_version": "0x00000000",
                        "epoch": "0"
                    },
                    "genesis_validators_root": "0x0000000000000000000000000000000000000000000000000000000000000000"
                },
                "signingRoot": "0x0000000000000000000000000000000000000000000000000000000000000000"
            }
            
            response = self.session.post(
                f"{self.base_url}/api/v1/eth2/{public_key}/sign",
                json=block_data,
                timeout=10
            )
            
            if response.status_code == 200:
                result = response.json()
                print(f"✅ 区块签名成功: {result.get('signature', 'N/A')[:20]}...")
                return True
            else:
                print(f"❌ 区块签名失败: {response.status_code} - {response.text}")
                return False
        except Exception as e:
            print(f"❌ 区块签名异常: {e}")
            return False
    
    def test_eth2_sign_attestation(self, public_key: str) -> bool:
        """测试证明签名"""
        try:
            # 构造一个测试证明数据
            attestation_data = {
                "type": "ATTESTATION",
                "fork_info": {
                    "fork": {
                        "previous_version": "0x00000000",
                        "current_version": "0x00000000",
                        "epoch": "0"
                    },
                    "genesis_validators_root": "0x0000000000000000000000000000000000000000000000000000000000000000"
                },
                "signingRoot": "0x0000000000000000000000000000000000000000000000000000000000000000"
            }
            
            response = self.session.post(
                f"{self.base_url}/api/v1/eth2/{public_key}/sign",
                json=attestation_data,
                timeout=10
            )
            
            if response.status_code == 200:
                result = response.json()
                print(f"✅ 证明签名成功: {result.get('signature', 'N/A')[:20]}...")
                return True
            else:
                print(f"❌ 证明签名失败: {response.status_code} - {response.text}")
                return False
        except Exception as e:
            print(f"❌ 证明签名异常: {e}")
            return False
    
    def test_eth2_sign_aggregate_and_proof(self, public_key: str) -> bool:
        """测试聚合证明签名"""
        try:
            # 构造一个测试聚合证明数据
            aggregate_data = {
                "type": "AGGREGATE_AND_PROOF",
                "fork_info": {
                    "fork": {
                        "previous_version": "0x00000000",
                        "current_version": "0x00000000",
                        "epoch": "0"
                    },
                    "genesis_validators_root": "0x0000000000000000000000000000000000000000000000000000000000000000"
                },
                "signingRoot": "0x0000000000000000000000000000000000000000000000000000000000000000"
            }
            
            response = self.session.post(
                f"{self.base_url}/api/v1/eth2/{public_key}/sign",
                json=aggregate_data,
                timeout=10
            )
            
            if response.status_code == 200:
                result = response.json()
                print(f"✅ 聚合证明签名成功: {result.get('signature', 'N/A')[:20]}...")
                return True
            else:
                print(f"❌ 聚合证明签名失败: {response.status_code} - {response.text}")
                return False
        except Exception as e:
            print(f"❌ 聚合证明签名异常: {e}")
            return False
    
    def test_metrics(self) -> bool:
        """测试指标端点"""
        try:
            response = self.session.get(f"{self.base_url}/metrics", timeout=10)
            if response.status_code == 200:
                print("✅ 指标端点可访问")
                return True
            else:
                print(f"❌ 指标端点失败: {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ 指标端点异常: {e}")
            return False
    
    def run_comprehensive_test(self) -> bool:
        """运行综合测试"""
        print("🔍 开始 Web3Signer ETH2 API 综合测试...")
        print("=" * 60)
        
        # 1. 健康检查
        print("\n1️⃣ 测试健康检查...")
        if not self.test_upcheck():
            return False
        
        # 2. 获取公钥列表
        print("\n2️⃣ 测试公钥列表...")
        public_keys = self.test_eth2_public_keys()
        if not public_keys:
            print("❌ 无法获取公钥，停止测试")
            return False
        
        # 3. 测试第一个公钥的详细信息
        print(f"\n3️⃣ 测试公钥详细信息...")
        if not self.test_eth2_public_key_info(public_keys[0]):
            print("⚠️  公钥信息获取失败，但继续测试...")
        
        # 4. 测试签名功能
        print(f"\n4️⃣ 测试签名功能...")
        test_key = public_keys[0]
        
        # 测试区块签名
        print("  📝 测试区块签名...")
        self.test_eth2_sign_block(test_key)
        
        # 测试证明签名
        print("  📝 测试证明签名...")
        self.test_eth2_sign_attestation(test_key)
        
        # 测试聚合证明签名
        print("  📝 测试聚合证明签名...")
        self.test_eth2_sign_aggregate_and_proof(test_key)
        
        # 5. 测试指标
        print("\n5️⃣ 测试指标端点...")
        self.test_metrics()
        
        print("\n" + "=" * 60)
        print("✅ Web3Signer API 测试完成")
        return True

def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Web3Signer ETH2 API 测试工具')
    parser.add_argument('--url', default='http://localhost:9000', 
                       help='Web3Signer 服务 URL (默认: http://localhost:9000)')
    parser.add_argument('--test', choices=['upcheck', 'keys', 'sign', 'all'], 
                       default='all', help='测试类型')
    
    args = parser.parse_args()
    
    tester = Web3SignerTester(args.url)
    
    if args.test == 'upcheck':
        success = tester.test_upcheck()
    elif args.test == 'keys':
        success = tester.test_eth2_public_keys() is not None
    elif args.test == 'sign':
        keys = tester.test_eth2_public_keys()
        success = keys and tester.test_eth2_sign_block(keys[0])
    else:  # all
        success = tester.run_comprehensive_test()
    
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
