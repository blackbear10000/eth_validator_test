#!/usr/bin/env python3
"""
Validator 问题诊断脚本
基于您遇到的错误进行针对性诊断
"""

import requests
import psycopg2
import json
import sys
import time
from typing import Dict, List, Any, Optional

class ValidatorDiagnostic:
    def __init__(self):
        self.web3signer_urls = [
            "http://localhost:9000",  # web3signer-1
            "http://localhost:9001",  # web3signer-2
            "http://localhost:9002"   # haproxy
        ]
    
    def check_web3signer_health(self) -> Dict[str, bool]:
        """检查所有 Web3Signer 实例的健康状态"""
        print("🔍 检查 Web3Signer 健康状态...")
        results = {}
        
        for url in self.web3signer_urls:
            try:
                response = requests.get(f"{url}/upcheck", timeout=5)
                if response.status_code == 200:
                    print(f"✅ {url}: 健康")
                    results[url] = True
                else:
                    print(f"❌ {url}: 不健康 (状态码: {response.status_code})")
                    results[url] = False
            except Exception as e:
                print(f"❌ {url}: 连接失败 - {e}")
                results[url] = False
        
        return results
    
    def check_web3signer_keys(self) -> Dict[str, List[str]]:
        """检查每个 Web3Signer 实例的公钥"""
        print("\n🔍 检查 Web3Signer 公钥...")
        results = {}
        
        for url in self.web3signer_urls:
            try:
                response = requests.get(f"{url}/api/v1/eth2/publicKeys", timeout=10)
                if response.status_code == 200:
                    keys = response.json()
                    print(f"✅ {url}: {len(keys)} 个公钥")
                    results[url] = keys
                else:
                    print(f"❌ {url}: 获取公钥失败 - {response.status_code}")
                    results[url] = []
            except Exception as e:
                print(f"❌ {url}: 获取公钥异常 - {e}")
                results[url] = []
        
        return results
    
    def check_database_connection(self) -> bool:
        """检查数据库连接"""
        print("\n🔍 检查数据库连接...")
        try:
            conn = psycopg2.connect(
                host="localhost",
                port="5432",
                database="web3signer",
                user="postgres",
                password="password"
            )
            cursor = conn.cursor()
            cursor.execute("SELECT version();")
            version = cursor.fetchone()[0]
            cursor.close()
            conn.close()
            print(f"✅ 数据库连接正常: {version}")
            return True
        except Exception as e:
            print(f"❌ 数据库连接失败: {e}")
            return False
    
    def check_database_schema(self) -> bool:
        """检查数据库架构"""
        print("\n🔍 检查数据库架构...")
        try:
            conn = psycopg2.connect(
                host="localhost",
                port="5432",
                database="web3signer",
                user="postgres",
                password="password"
            )
            cursor = conn.cursor()
            
            # 检查数据库版本
            cursor.execute("SELECT * FROM database_version;")
            version = cursor.fetchone()
            if version:
                print(f"✅ 数据库版本: {version[1]}")
                if version[1] != 12:
                    print(f"⚠️  警告: 数据库版本应该是 12，实际是 {version[1]}")
            else:
                print("❌ 无法获取数据库版本")
                return False
            
            # 检查表
            cursor.execute("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public' 
                ORDER BY table_name;
            """)
            tables = [row[0] for row in cursor.fetchall()]
            expected_tables = ['validators', 'signed_blocks', 'signed_attestations', 
                             'low_watermarks', 'metadata', 'database_version']
            
            missing_tables = [t for t in expected_tables if t not in tables]
            if missing_tables:
                print(f"❌ 缺少表: {missing_tables}")
                return False
            else:
                print("✅ 所有必要的表都存在")
            
            cursor.close()
            conn.close()
            return True
            
        except Exception as e:
            print(f"❌ 数据库架构检查失败: {e}")
            return False
    
    def test_signing_capability(self, url: str, public_key: str) -> bool:
        """测试签名能力"""
        print(f"\n🔍 测试 {url} 的签名能力...")
        
        # 测试区块签名
        try:
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
            
            response = requests.post(
                f"{url}/api/v1/eth2/{public_key}/sign",
                json=block_data,
                timeout=10
            )
            
            if response.status_code == 200:
                print(f"✅ {url}: 区块签名成功")
                return True
            else:
                print(f"❌ {url}: 区块签名失败 - {response.status_code}: {response.text}")
                return False
                
        except Exception as e:
            print(f"❌ {url}: 签名测试异常 - {e}")
            return False
    
    def analyze_committee_bits_error(self) -> None:
        """分析 CommitteeBits 错误"""
        print("\n🔍 分析 CommitteeBits 错误...")
        print("""
        CommitteeBits 错误通常表示：
        1. 网络配置不匹配 (mainnet vs testnet)
        2. Fork 版本不正确
        3. Genesis 验证器根不匹配
        4. 委员会大小配置错误
        
        建议检查：
        - Web3Signer 网络配置 (mainnet/testnet)
        - Validator 客户端的网络配置
        - Genesis 验证器根是否匹配
        """)
    
    def check_network_configuration(self) -> None:
        """检查网络配置"""
        print("\n🔍 检查网络配置...")
        
        # 检查 Web3Signer 配置
        try:
            with open('/Users/yuanshuai/Documents/Github/eth_validator_test/infra/web3signer/config/config.yaml', 'r') as f:
                config_content = f.read()
                if 'mainnet' in config_content:
                    print("✅ Web3Signer 配置为 mainnet")
                else:
                    print("⚠️  Web3Signer 配置可能不是 mainnet")
        except Exception as e:
            print(f"❌ 无法读取 Web3Signer 配置: {e}")
    
    def provide_solutions(self) -> None:
        """提供解决方案"""
        print("\n" + "="*60)
        print("🛠️  解决方案建议:")
        print("="*60)
        
        print("""
        1. 数据库问题解决：
           - 停止所有服务: docker-compose down
           - 删除 postgres volume: docker volume rm eth_validator_test_postgres_data
           - 重新启动: docker-compose up -d
        
        2. Web3Signer 配置检查：
           - 确保网络配置正确 (mainnet/testnet)
           - 检查密钥文件路径
           - 验证数据库连接参数
        
        3. Validator 客户端配置：
           - 确保与 Web3Signer 网络配置一致
           - 检查 Web3Signer URL 配置
           - 验证公钥匹配
        
        4. 网络连接检查：
           - 确保所有服务都在运行
           - 检查端口映射
           - 验证防火墙设置
        
        5. 日志分析：
           - 查看 Web3Signer 日志: docker logs web3signer-1
           - 查看 Validator 日志
           - 检查数据库日志
        """)
    
    def run_full_diagnosis(self) -> bool:
        """运行完整诊断"""
        print("🔍 开始 Validator 问题完整诊断...")
        print("="*60)
        
        # 1. 检查 Web3Signer 健康状态
        health_results = self.check_web3signer_health()
        
        # 2. 检查公钥
        key_results = self.check_web3signer_keys()
        
        # 3. 检查数据库
        db_connected = self.check_database_connection()
        db_schema_ok = self.check_database_schema() if db_connected else False
        
        # 4. 测试签名能力
        signing_tests = {}
        for url, keys in key_results.items():
            if keys and health_results.get(url, False):
                signing_tests[url] = self.test_signing_capability(url, keys[0])
        
        # 5. 分析特定错误
        self.analyze_committee_bits_error()
        
        # 6. 检查网络配置
        self.check_network_configuration()
        
        # 7. 提供解决方案
        self.provide_solutions()
        
        # 总结
        print("\n" + "="*60)
        print("📊 诊断结果总结:")
        print("="*60)
        
        all_healthy = all(health_results.values())
        all_have_keys = all(len(keys) > 0 for keys in key_results.values())
        all_signing_ok = all(signing_tests.values()) if signing_tests else False
        
        print(f"Web3Signer 健康状态: {'✅' if all_healthy else '❌'}")
        print(f"公钥可用性: {'✅' if all_have_keys else '❌'}")
        print(f"数据库连接: {'✅' if db_connected else '❌'}")
        print(f"数据库架构: {'✅' if db_schema_ok else '❌'}")
        print(f"签名能力: {'✅' if all_signing_ok else '❌'}")
        
        if all_healthy and all_have_keys and db_connected and db_schema_ok and all_signing_ok:
            print("\n🎉 所有检查都通过！")
            return True
        else:
            print("\n⚠️  发现问题，请参考上述解决方案。")
            return False

def main():
    """主函数"""
    diagnostic = ValidatorDiagnostic()
    success = diagnostic.run_full_diagnosis()
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
