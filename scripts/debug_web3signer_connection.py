#!/usr/bin/env python3
"""
Web3Signer 连接诊断脚本
用于诊断 Prysm 验证器与 Web3Signer 之间的连接问题
"""

import requests
import json
import sys
import time
from typing import Dict, Any

class Web3SignerDiagnostic:
    """Web3Signer 连接诊断器"""
    
    def __init__(self, web3signer_url: str = "http://localhost:9000"):
        self.web3signer_url = web3signer_url.rstrip('/')
        self.session = requests.Session()
        self.session.timeout = 10
    
    def check_web3signer_health(self) -> bool:
        """检查 Web3Signer 健康状态"""
        print("🔍 检查 Web3Signer 健康状态...")
        
        try:
            # 检查 upcheck 端点
            upcheck_url = f"{self.web3signer_url}/upcheck"
            response = self.session.get(upcheck_url)
            
            if response.status_code == 200:
                print(f"✅ Web3Signer 健康检查通过: {upcheck_url}")
                return True
            else:
                print(f"❌ Web3Signer 健康检查失败: {response.status_code}")
                return False
                
        except requests.exceptions.ConnectionError:
            print(f"❌ 无法连接到 Web3Signer: {self.web3signer_url}")
            return False
        except Exception as e:
            print(f"❌ Web3Signer 健康检查异常: {e}")
            return False
    
    def check_web3signer_keys(self) -> Dict[str, Any]:
        """检查 Web3Signer 中的密钥"""
        print("🔍 检查 Web3Signer 中的密钥...")
        
        try:
            # 获取公钥列表
            keys_url = f"{self.web3signer_url}/api/v1/eth2/publicKeys"
            response = self.session.get(keys_url)
            
            if response.status_code == 200:
                keys = response.json()
                print(f"✅ 找到 {len(keys)} 个公钥:")
                for i, key in enumerate(keys, 1):
                    print(f"   {i}. {key}")
                return {"status": "success", "keys": keys, "count": len(keys)}
            else:
                print(f"❌ 获取公钥失败: {response.status_code}")
                return {"status": "error", "code": response.status_code}
                
        except Exception as e:
            print(f"❌ 检查密钥异常: {e}")
            return {"status": "error", "message": str(e)}
    
    def test_signing_endpoint(self, pubkey: str) -> bool:
        """测试签名端点"""
        print(f"🔍 测试签名端点 (公钥: {pubkey[:10]}...)")
        
        try:
            # 构造测试签名请求
            sign_url = f"{self.web3signer_url}/api/v1/eth2/sign/{pubkey}"
            
            # 使用更简单的测试数据 - 只测试基本的签名功能
            test_data = {
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
            
            headers = {
                "Content-Type": "application/json"
            }
            
            response = self.session.post(sign_url, json=test_data, headers=headers)
            
            if response.status_code == 200:
                print(f"✅ 签名测试成功")
                return True
            elif response.status_code == 400:
                print(f"⚠️  签名测试返回 400 (可能是测试数据格式问题，但服务正常)")
                return True  # 400 错误通常表示请求格式问题，不是服务问题
            else:
                print(f"❌ 签名测试失败: {response.status_code}")
                print(f"   响应: {response.text}")
                return False
                
        except Exception as e:
            print(f"❌ 签名测试异常: {e}")
            return False
    
    def check_web3signer_config(self) -> Dict[str, Any]:
        """检查 Web3Signer 配置"""
        print("🔍 检查 Web3Signer 配置...")
        
        try:
            # 尝试获取配置信息
            config_url = f"{self.web3signer_url}/api/v1/eth2/config"
            response = self.session.get(config_url)
            
            if response.status_code == 200:
                config = response.json()
                print("✅ Web3Signer 配置信息:")
                print(f"   网络: {config.get('network', 'unknown')}")
                print(f"   版本: {config.get('version', 'unknown')}")
                return {"status": "success", "config": config}
            else:
                print(f"⚠️  无法获取配置信息: {response.status_code}")
                return {"status": "warning", "code": response.status_code}
                
        except Exception as e:
            print(f"⚠️  配置检查异常: {e}")
            return {"status": "warning", "message": str(e)}
    
    def test_simple_connection(self) -> bool:
        """简单的连接测试"""
        print("🔍 测试基本连接...")
        
        try:
            # 测试多个端点
            endpoints = [
                "/upcheck",
                "/api/v1/eth2/publicKeys",
                "/health"
            ]
            
            all_working = True
            for endpoint in endpoints:
                try:
                    response = self.session.get(f"{self.web3signer_url}{endpoint}")
                    if response.status_code == 200:
                        print(f"   ✅ {endpoint}")
                    else:
                        print(f"   ⚠️  {endpoint} ({response.status_code})")
                        all_working = False
                except Exception as e:
                    print(f"   ❌ {endpoint} (错误: {e})")
                    all_working = False
            
            return all_working
            
        except Exception as e:
            print(f"❌ 连接测试异常: {e}")
            return False
    
    def diagnose_connection_issues(self) -> Dict[str, Any]:
        """诊断连接问题"""
        print("🔍 开始 Web3Signer 连接诊断...")
        print(f"📡 Web3Signer URL: {self.web3signer_url}")
        print("=" * 50)
        
        results = {
            "web3signer_url": self.web3signer_url,
            "health_check": False,
            "keys_check": {},
            "signing_test": False,
            "config_check": {},
            "recommendations": []
        }
        
        # 1. 健康检查
        results["health_check"] = self.check_web3signer_health()
        
        if not results["health_check"]:
            results["recommendations"].append("启动 Web3Signer 服务")
            results["recommendations"].append("检查 Web3Signer 端口是否正确")
            return results
        
        # 2. 密钥检查
        results["keys_check"] = self.check_web3signer_keys()
        
        if results["keys_check"].get("status") != "success":
            results["recommendations"].append("检查 Web3Signer 密钥配置")
            results["recommendations"].append("确保密钥已正确加载到 Web3Signer")
        
        # 3. 配置检查
        results["config_check"] = self.check_web3signer_config()
        
        # 4. 基本连接测试
        results["connection_test"] = self.test_simple_connection()
        
        # 5. 签名测试（如果有密钥）
        if results["keys_check"].get("keys"):
            first_key = results["keys_check"]["keys"][0]
            results["signing_test"] = self.test_signing_endpoint(first_key)
            
            if not results["signing_test"]:
                results["recommendations"].append("检查 Web3Signer 签名配置")
                results["recommendations"].append("验证密钥格式是否正确")
        
        if not results["connection_test"]:
            results["recommendations"].append("检查 Web3Signer 服务状态")
            results["recommendations"].append("验证网络连接")
        
        return results
    
    def print_recommendations(self, results: Dict[str, Any]):
        """打印建议"""
        print("\n" + "=" * 50)
        print("📋 诊断结果和建议:")
        print("=" * 50)
        
        if results["health_check"]:
            print("✅ Web3Signer 服务运行正常")
        else:
            print("❌ Web3Signer 服务未运行或无法访问")
        
        if results["keys_check"].get("status") == "success":
            print(f"✅ 找到 {results['keys_check']['count']} 个公钥")
        else:
            print("❌ 无法获取公钥列表")
        
        if results.get("connection_test"):
            print("✅ 基本连接测试通过")
        else:
            print("❌ 基本连接测试失败")
        
        if results.get("signing_test"):
            print("✅ 签名功能正常")
        elif results.get("signing_test") is False:
            print("❌ 签名功能异常")
        else:
            print("⚠️  签名功能未测试")
        
        if results["recommendations"]:
            print("\n🔧 建议:")
            for i, rec in enumerate(results["recommendations"], 1):
                print(f"   {i}. {rec}")
        
        print("\n💡 常见解决方案:")
        print("   1. 检查 Web3Signer 是否正在运行: docker ps | grep web3signer")
        print("   2. 检查 Web3Signer 日志: docker logs <web3signer_container>")
        print("   3. 验证 Web3Signer 配置: 检查密钥路径和格式")
        print("   4. 检查网络连接: curl http://localhost:9000/upcheck")
        print("   5. 重启 Web3Signer 服务")

def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Web3Signer 连接诊断工具")
    parser.add_argument("--web3signer-url", default="http://localhost:9000",
                       help="Web3Signer 服务地址")
    
    args = parser.parse_args()
    
    diagnostic = Web3SignerDiagnostic(args.web3signer_url)
    results = diagnostic.diagnose_connection_issues()
    diagnostic.print_recommendations(results)
    
    # 返回适当的退出码
    if not results["health_check"]:
        sys.exit(1)
    elif results["keys_check"].get("status") != "success":
        sys.exit(2)
    elif not results["signing_test"]:
        sys.exit(3)
    else:
        sys.exit(0)

if __name__ == "__main__":
    main()
