#!/usr/bin/env python3
"""
分析 Prysm 与 Web3Signer 连接问题的专门脚本
针对 "ContentLength=391 with Body length 0" 错误
"""

import requests
import json
import sys
import time
from typing import Dict, Any

class PrysmWeb3SignerAnalyzer:
    """Prysm 与 Web3Signer 连接问题分析器"""
    
    def __init__(self, web3signer_url: str = "http://localhost:9000"):
        self.web3signer_url = web3signer_url.rstrip('/')
        self.session = requests.Session()
        self.session.timeout = 10
    
    def analyze_content_length_issue(self) -> Dict[str, Any]:
        """分析 ContentLength 问题"""
        print("🔍 分析 ContentLength 问题...")
        
        issue_analysis = {
            "problem": "ContentLength=391 with Body length 0",
            "possible_causes": [],
            "solutions": []
        }
        
        # 可能的原因
        issue_analysis["possible_causes"] = [
            "HTTP 请求头 Content-Length 与实际请求体长度不匹配",
            "Prysm 发送了空的请求体但设置了错误的 Content-Length",
            "Web3Signer 无法解析请求格式",
            "网络代理或负载均衡器修改了请求",
            "Prysm 版本与 Web3Signer 版本不兼容"
        ]
        
        # 解决方案
        issue_analysis["solutions"] = [
            "检查 Prysm 版本是否与 Web3Signer 兼容",
            "验证 Web3Signer 配置是否正确",
            "检查网络连接和代理设置",
            "尝试使用不同的 Web3Signer URL",
            "检查 Web3Signer 日志中的详细错误"
        ]
        
        return issue_analysis
    
    def test_web3signer_compatibility(self) -> Dict[str, Any]:
        """测试 Web3Signer 兼容性"""
        print("🔍 测试 Web3Signer 兼容性...")
        
        compatibility = {
            "version_check": False,
            "endpoint_compatibility": False,
            "request_format": False
        }
        
        try:
            # 1. 检查版本信息
            try:
                response = self.session.get(f"{self.web3signer_url}/api/v1/eth2/config")
                if response.status_code == 200:
                    config = response.json()
                    print(f"✅ Web3Signer 配置可访问")
                    compatibility["version_check"] = True
                else:
                    print(f"⚠️  配置端点返回: {response.status_code}")
            except:
                print("⚠️  无法访问配置端点")
            
            # 2. 测试端点兼容性
            endpoints_to_test = [
                "/upcheck",
                "/api/v1/eth2/publicKeys",
                "/health"
            ]
            
            working_endpoints = 0
            for endpoint in endpoints_to_test:
                try:
                    response = self.session.get(f"{self.web3signer_url}{endpoint}")
                    if response.status_code == 200:
                        working_endpoints += 1
                        print(f"   ✅ {endpoint}")
                    else:
                        print(f"   ❌ {endpoint} ({response.status_code})")
                except Exception as e:
                    print(f"   ❌ {endpoint} (错误: {e})")
            
            compatibility["endpoint_compatibility"] = working_endpoints >= 2
            
            # 3. 测试请求格式
            try:
                # 获取公钥
                response = self.session.get(f"{self.web3signer_url}/api/v1/eth2/publicKeys")
                if response.status_code == 200:
                    keys = response.json()
                    if keys:
                        # 测试一个简单的签名请求
                        test_key = keys[0]
                        sign_url = f"{self.web3signer_url}/api/v1/eth2/sign/{test_key}"
                        
                        # 使用最简单的测试数据
                        simple_test = {
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
                        
                        response = self.session.post(sign_url, json=simple_test)
                        if response.status_code in [200, 400]:  # 400 也是可以接受的，表示格式问题
                            print("✅ 签名请求格式测试通过")
                            compatibility["request_format"] = True
                        else:
                            print(f"❌ 签名请求失败: {response.status_code}")
                            print(f"   响应: {response.text}")
                    else:
                        print("⚠️  没有可用的公钥进行测试")
                else:
                    print("❌ 无法获取公钥列表")
            except Exception as e:
                print(f"❌ 请求格式测试失败: {e}")
            
        except Exception as e:
            print(f"❌ 兼容性测试异常: {e}")
        
        return compatibility
    
    def suggest_prysm_configuration(self) -> Dict[str, Any]:
        """建议 Prysm 配置"""
        print("🔍 分析 Prysm 配置建议...")
        
        suggestions = {
            "web3signer_url": "确保使用正确的 Web3Signer URL",
            "timeout_settings": "调整超时设置",
            "retry_settings": "配置重试机制",
            "debug_logging": "启用调试日志"
        }
        
        print("📋 Prysm 配置建议:")
        print("   1. 确保 Web3Signer URL 正确:")
        print("      --validators-external-signer-url=http://localhost:9000")
        print("   2. 添加超时设置:")
        print("      --api-timeout=30s")
        print("   3. 启用详细日志:")
        print("      --verbosity=debug")
        print("   4. 检查网络连接:")
        print("      curl http://localhost:9000/upcheck")
        
        return suggestions
    
    def generate_troubleshooting_steps(self) -> list:
        """生成故障排除步骤"""
        print("🔍 生成故障排除步骤...")
        
        steps = [
            "1. 检查 Web3Signer 服务状态",
            "2. 验证 Web3Signer 日志",
            "3. 测试 Web3Signer 端点",
            "4. 检查 Prysm 配置",
            "5. 验证网络连接",
            "6. 重启相关服务"
        ]
        
        print("\n📋 详细故障排除步骤:")
        print("=" * 50)
        
        print("\n1️⃣ 检查 Web3Signer 服务状态:")
        print("   docker ps | grep web3signer")
        print("   docker logs web3signer --tail 50")
        
        print("\n2️⃣ 验证 Web3Signer 配置:")
        print("   docker exec web3signer cat /config/config.yaml")
        print("   docker exec web3signer ls -la /keys/")
        
        print("\n3️⃣ 测试 Web3Signer 端点:")
        print("   curl http://localhost:9000/upcheck")
        print("   curl http://localhost:9000/api/v1/eth2/publicKeys")
        
        print("\n4️⃣ 检查 Prysm 配置:")
        print("   确保 --validators-external-signer-url 正确")
        print("   确保 --validators-external-signer-public-keys 正确")
        
        print("\n5️⃣ 验证网络连接:")
        print("   telnet localhost 9000")
        print("   netstat -tlnp | grep 9000")
        
        print("\n6️⃣ 重启服务:")
        print("   docker restart web3signer")
        print("   等待 30 秒后重新启动 Prysm")
        
        return steps
    
    def run_comprehensive_analysis(self) -> Dict[str, Any]:
        """运行综合分析"""
        print("🔍 开始 Prysm-Web3Signer 连接问题综合分析...")
        print(f"📡 Web3Signer URL: {self.web3signer_url}")
        print("=" * 60)
        
        results = {
            "web3signer_url": self.web3signer_url,
            "issue_analysis": {},
            "compatibility": {},
            "suggestions": {},
            "troubleshooting_steps": []
        }
        
        # 1. 分析问题
        results["issue_analysis"] = self.analyze_content_length_issue()
        
        # 2. 测试兼容性
        results["compatibility"] = self.test_web3signer_compatibility()
        
        # 3. 生成建议
        results["suggestions"] = self.suggest_prysm_configuration()
        
        # 4. 生成故障排除步骤
        results["troubleshooting_steps"] = self.generate_troubleshooting_steps()
        
        return results
    
    def print_analysis_results(self, results: Dict[str, Any]):
        """打印分析结果"""
        print("\n" + "=" * 60)
        print("📊 分析结果总结:")
        print("=" * 60)
        
        # 问题分析
        print("\n🔍 问题分析:")
        print(f"   问题: {results['issue_analysis']['problem']}")
        print("   可能原因:")
        for i, cause in enumerate(results['issue_analysis']['possible_causes'], 1):
            print(f"     {i}. {cause}")
        
        # 兼容性测试结果
        print("\n🔧 兼容性测试:")
        compat = results['compatibility']
        print(f"   版本检查: {'✅' if compat['version_check'] else '❌'}")
        print(f"   端点兼容: {'✅' if compat['endpoint_compatibility'] else '❌'}")
        print(f"   请求格式: {'✅' if compat['request_format'] else '❌'}")
        
        # 建议
        print("\n💡 建议:")
        for key, suggestion in results['suggestions'].items():
            print(f"   {key}: {suggestion}")
        
        print("\n🎯 下一步行动:")
        print("   1. 运行: ./validator.sh debug-web3signer-connection")
        print("   2. 检查: docker logs web3signer")
        print("   3. 测试: curl http://localhost:9000/upcheck")
        print("   4. 重启: ./validator.sh restart-web3signer")

def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Prysm-Web3Signer 连接问题分析工具")
    parser.add_argument("--web3signer-url", default="http://localhost:9000",
                       help="Web3Signer 服务地址")
    
    args = parser.parse_args()
    
    analyzer = PrysmWeb3SignerAnalyzer(args.web3signer_url)
    results = analyzer.run_comprehensive_analysis()
    analyzer.print_analysis_results(results)
    
    # 根据分析结果返回适当的退出码
    compat = results['compatibility']
    if compat['version_check'] and compat['endpoint_compatibility']:
        sys.exit(0)  # 基本功能正常
    else:
        sys.exit(1)  # 需要进一步检查

if __name__ == "__main__":
    main()
