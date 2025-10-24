#!/usr/bin/env python3
"""
Web3Signer 连接问题快速修复脚本
"""

import requests
import json
import sys
import time
import subprocess
import os
from typing import Dict, Any

class Web3SignerConnectionFixer:
    """Web3Signer 连接问题修复器"""
    
    def __init__(self, web3signer_url: str = "http://localhost:9000"):
        self.web3signer_url = web3signer_url.rstrip('/')
        self.session = requests.Session()
        self.session.timeout = 10
    
    def check_docker_services(self) -> Dict[str, bool]:
        """检查 Docker 服务状态"""
        print("🔍 检查 Docker 服务状态...")
        
        services = {
            "web3signer": False,
            "vault": False,
            "postgres": False
        }
        
        try:
            # 检查 Web3Signer
            result = subprocess.run(['docker', 'ps', '--filter', 'name=web3signer', '--format', '{{.Names}}'], 
                                  capture_output=True, text=True)
            if 'web3signer' in result.stdout:
                services["web3signer"] = True
                print("✅ Web3Signer 容器正在运行")
            else:
                print("❌ Web3Signer 容器未运行")
            
            # 检查 Vault
            result = subprocess.run(['docker', 'ps', '--filter', 'name=vault', '--format', '{{.Names}}'], 
                                  capture_output=True, text=True)
            if 'vault' in result.stdout:
                services["vault"] = True
                print("✅ Vault 容器正在运行")
            else:
                print("❌ Vault 容器未运行")
            
            # 检查 PostgreSQL
            result = subprocess.run(['docker', 'ps', '--filter', 'name=postgres', '--format', '{{.Names}}'], 
                                  capture_output=True, text=True)
            if 'postgres' in result.stdout:
                services["postgres"] = True
                print("✅ PostgreSQL 容器正在运行")
            else:
                print("❌ PostgreSQL 容器未运行")
                
        except Exception as e:
            print(f"⚠️  检查 Docker 服务时出错: {e}")
        
        return services
    
    def restart_web3signer(self) -> bool:
        """重启 Web3Signer 服务"""
        print("🔄 重启 Web3Signer 服务...")
        
        try:
            # 停止 Web3Signer
            subprocess.run(['docker', 'stop', 'web3signer'], check=False)
            time.sleep(2)
            
            # 启动 Web3Signer
            subprocess.run(['docker', 'start', 'web3signer'], check=True)
            time.sleep(5)
            
            print("✅ Web3Signer 服务已重启")
            return True
            
        except Exception as e:
            print(f"❌ 重启 Web3Signer 失败: {e}")
            return False
    
    def check_web3signer_logs(self) -> str:
        """检查 Web3Signer 日志"""
        print("🔍 检查 Web3Signer 日志...")
        
        try:
            result = subprocess.run(['docker', 'logs', '--tail', '20', 'web3signer'], 
                                  capture_output=True, text=True)
            
            if result.returncode == 0:
                logs = result.stdout
                print("📋 Web3Signer 最近日志:")
                print("-" * 40)
                print(logs)
                print("-" * 40)
                return logs
            else:
                print(f"❌ 无法获取 Web3Signer 日志: {result.stderr}")
                return ""
                
        except Exception as e:
            print(f"❌ 检查日志时出错: {e}")
            return ""
    
    def test_web3signer_endpoints(self) -> Dict[str, bool]:
        """测试 Web3Signer 端点"""
        print("🔍 测试 Web3Signer 端点...")
        
        endpoints = {
            "upcheck": False,
            "public_keys": False,
            "health": False
        }
        
        # 测试 upcheck
        try:
            response = self.session.get(f"{self.web3signer_url}/upcheck")
            endpoints["upcheck"] = response.status_code == 200
            print(f"   upcheck: {'✅' if endpoints['upcheck'] else '❌'}")
        except:
            print("   upcheck: ❌")
        
        # 测试公钥端点
        try:
            response = self.session.get(f"{self.web3signer_url}/api/v1/eth2/publicKeys")
            endpoints["public_keys"] = response.status_code == 200
            print(f"   public_keys: {'✅' if endpoints['public_keys'] else '❌'}")
        except:
            print("   public_keys: ❌")
        
        # 测试健康检查
        try:
            response = self.session.get(f"{self.web3signer_url}/health")
            endpoints["health"] = response.status_code == 200
            print(f"   health: {'✅' if endpoints['health'] else '❌'}")
        except:
            print("   health: ❌")
        
        return endpoints
    
    def fix_connection_issues(self) -> bool:
        """修复连接问题"""
        print("🔧 开始修复 Web3Signer 连接问题...")
        print("=" * 50)
        
        # 1. 检查 Docker 服务
        services = self.check_docker_services()
        
        if not services["web3signer"]:
            print("❌ Web3Signer 容器未运行，请先启动基础设施:")
            print("   ./validator.sh start")
            return False
        
        # 2. 检查日志
        logs = self.check_web3signer_logs()
        
        # 3. 测试端点
        endpoints = self.test_web3signer_endpoints()
        
        # 4. 如果端点测试失败，尝试重启
        if not any(endpoints.values()):
            print("🔄 端点测试失败，尝试重启 Web3Signer...")
            if self.restart_web3signer():
                time.sleep(10)  # 等待服务启动
                endpoints = self.test_web3signer_endpoints()
        
        # 5. 检查修复结果
        if endpoints["upcheck"]:
            print("✅ Web3Signer 连接问题已修复")
            return True
        else:
            print("❌ 无法修复 Web3Signer 连接问题")
            print("\n💡 手动检查步骤:")
            print("   1. 检查 Web3Signer 配置: docker exec web3signer cat /config/config.yaml")
            print("   2. 检查密钥文件: docker exec web3signer ls -la /keys/")
            print("   3. 检查网络连接: curl http://localhost:9000/upcheck")
            print("   4. 查看完整日志: docker logs web3signer")
            return False

def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Web3Signer 连接问题修复工具")
    parser.add_argument("--web3signer-url", default="http://localhost:9000",
                       help="Web3Signer 服务地址")
    parser.add_argument("--restart", action="store_true",
                       help="强制重启 Web3Signer 服务")
    
    args = parser.parse_args()
    
    fixer = Web3SignerConnectionFixer(args.web3signer_url)
    
    if args.restart:
        print("🔄 强制重启 Web3Signer...")
        fixer.restart_web3signer()
        time.sleep(10)
    
    success = fixer.fix_connection_issues()
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
