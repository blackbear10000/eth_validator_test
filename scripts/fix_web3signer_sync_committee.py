#!/usr/bin/env python3
"""
修复 Web3Signer Sync Committee 问题
解决 "Fork at slot 694 does not support sync committees" 错误
"""

import requests
import json
import sys
import time
from typing import Dict, List, Any, Optional

class Web3SignerSyncCommitteeFix:
    def __init__(self, web3signer_url: str = "http://localhost:9000"):
        self.web3signer_url = web3signer_url.rstrip('/')
        self.session = requests.Session()
        self.session.headers.update({
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        })
    
    def check_web3signer_health(self) -> bool:
        """检查 Web3Signer 健康状态"""
        try:
            response = self.session.get(f"{self.web3signer_url}/upcheck", timeout=5)
            if response.status_code == 200:
                print("✅ Web3Signer 健康检查通过")
                return True
            else:
                print(f"❌ Web3Signer 健康检查失败: {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ Web3Signer 健康检查异常: {e}")
            return False
    
    def get_public_keys(self) -> Optional[List[str]]:
        """获取公钥列表"""
        try:
            response = self.session.get(f"{self.web3signer_url}/api/v1/eth2/publicKeys", timeout=10)
            if response.status_code == 200:
                keys = response.json()
                print(f"✅ 获取到 {len(keys)} 个公钥")
                return keys
            else:
                print(f"❌ 获取公钥失败: {response.status_code}")
                return None
        except Exception as e:
            print(f"❌ 获取公钥异常: {e}")
            return None
    
    def test_block_signing(self, public_key: str) -> bool:
        """测试区块签名（不涉及 sync committee）"""
        try:
            # 构造一个简单的区块签名请求
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
                f"{self.web3signer_url}/api/v1/eth2/{public_key}/sign",
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
    
    def test_attestation_signing(self, public_key: str) -> bool:
        """测试证明签名"""
        try:
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
                f"{self.web3signer_url}/api/v1/eth2/{public_key}/sign",
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
    
    def analyze_sync_committee_error(self) -> None:
        """分析 sync committee 错误"""
        print("\n🔍 Sync Committee 错误分析:")
        print("=" * 50)
        print("""
        错误原因分析：
        1. Web3Signer 配置为 mainnet，但测试网络在 slot 694 时还不支持 sync committees
        2. Sync committees 是在 Altair fork 中引入的
        3. 测试网络可能还没有到达 Altair fork 或者配置不正确
        
        解决方案：
        1. 将 Web3Signer 配置改为 'minimal' 网络
        2. 禁用 sync committee 签名功能
        3. 确保 validator 客户端使用正确的网络配置
        """)
    
    def provide_configuration_fixes(self) -> None:
        """提供配置修复建议"""
        print("\n🛠️  配置修复建议:")
        print("=" * 50)
        print("""
        1. Web3Signer 配置修复：
           - 将 eth2.network 改为 'minimal'
           - 添加 eth2.sync-committee-signing-enabled: false
           - 启用调试模式: logging: DEBUG
        
        2. Validator 客户端配置修复：
           - 使用清理过的 network-config-clean.yaml
           - 移除不支持的字段（GLOAS, EIP7441, EIP7805, EIP7928 等）
           - 只保留 Prysm 支持的字段
        
        3. 重启步骤：
           - 停止所有服务: docker-compose down
           - 重新启动: docker-compose up -d
           - 检查日志: docker logs web3signer-1
        """)
    
    def run_diagnosis(self) -> bool:
        """运行完整诊断"""
        print("🔍 Web3Signer Sync Committee 问题诊断")
        print("=" * 50)
        
        # 1. 检查 Web3Signer 健康状态
        print("\n1️⃣ 检查 Web3Signer 健康状态...")
        if not self.check_web3signer_health():
            print("❌ Web3Signer 不可用，请检查服务状态")
            return False
        
        # 2. 获取公钥
        print("\n2️⃣ 获取公钥列表...")
        public_keys = self.get_public_keys()
        if not public_keys:
            print("❌ 无法获取公钥")
            return False
        
        # 3. 测试签名功能
        print("\n3️⃣ 测试签名功能...")
        test_key = public_keys[0]
        
        # 测试区块签名
        print("  📝 测试区块签名...")
        block_success = self.test_block_signing(test_key)
        
        # 测试证明签名
        print("  📝 测试证明签名...")
        attestation_success = self.test_attestation_signing(test_key)
        
        # 4. 分析错误
        self.analyze_sync_committee_error()
        
        # 5. 提供修复建议
        self.provide_configuration_fixes()
        
        # 总结
        print("\n" + "=" * 50)
        print("📊 诊断结果:")
        print("=" * 50)
        
        if block_success and attestation_success:
            print("✅ 基本签名功能正常")
        else:
            print("❌ 签名功能有问题")
        
        print("\n🎯 下一步操作:")
        print("1. 使用清理过的 network-config-clean.yaml")
        print("2. 重启 Web3Signer 服务")
        print("3. 重新测试 validator 客户端")
        
        return block_success and attestation_success

def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Web3Signer Sync Committee 问题诊断工具')
    parser.add_argument('--url', default='http://localhost:9000', 
                       help='Web3Signer 服务 URL')
    
    args = parser.parse_args()
    
    fixer = Web3SignerSyncCommitteeFix(args.url)
    success = fixer.run_diagnosis()
    
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
