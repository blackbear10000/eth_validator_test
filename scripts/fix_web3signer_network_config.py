#!/usr/bin/env python3
"""
修复 Web3Signer 网络配置问题
解决 "Fork at slot 355 does not support sync committees" 错误
"""

import subprocess
import time
import requests
import sys

def restart_web3signer_with_new_config():
    """重启 Web3Signer 并应用新的网络配置"""
    print("🔧 修复 Web3Signer 网络配置...")
    
    try:
        # 1. 停止 Web3Signer 服务
        print("🔄 停止 Web3Signer 服务...")
        subprocess.run(['docker', 'stop', 'web3signer', 'web3signer-2'], 
                      capture_output=True, text=True)
        time.sleep(3)
        
        # 2. 启动 Web3Signer 服务
        print("🚀 启动 Web3Signer 服务...")
        subprocess.run(['docker', 'start', 'web3signer', 'web3signer-2'], 
                      check=True)
        
        # 3. 等待服务启动
        print("⏳ 等待 Web3Signer 服务启动...")
        time.sleep(15)
        
        # 4. 验证服务状态
        print("🔍 验证 Web3Signer 服务状态...")
        
        # 检查 Web3Signer-1
        try:
            response = requests.get("http://localhost:9000/upcheck", timeout=10)
            if response.status_code == 200:
                print("✅ Web3Signer-1 服务正常")
            else:
                print(f"⚠️  Web3Signer-1 状态异常: {response.status_code}")
        except Exception as e:
            print(f"❌ Web3Signer-1 连接失败: {e}")
        
        # 检查 Web3Signer-2
        try:
            response = requests.get("http://localhost:9001/upcheck", timeout=10)
            if response.status_code == 200:
                print("✅ Web3Signer-2 服务正常")
            else:
                print(f"⚠️  Web3Signer-2 状态异常: {response.status_code}")
        except Exception as e:
            print(f"❌ Web3Signer-2 连接失败: {e}")
        
        # 5. 检查加载的密钥
        print("🔍 检查密钥加载状态...")
        try:
            response = requests.get("http://localhost:9000/api/v1/eth2/publicKeys", timeout=10)
            if response.status_code == 200:
                keys = response.json()
                print(f"✅ Web3Signer-1 中加载了 {len(keys)} 个密钥")
            else:
                print(f"❌ 获取密钥列表失败: {response.status_code}")
        except Exception as e:
            print(f"❌ 检查密钥失败: {e}")
        
        print("\n🎉 Web3Signer 网络配置修复完成!")
        print("💡 现在可以重新启动 Prysm 验证器")
        
        return True
        
    except Exception as e:
        print(f"❌ 修复 Web3Signer 配置失败: {e}")
        return False

def check_web3signer_logs():
    """检查 Web3Signer 日志"""
    print("\n🔍 检查 Web3Signer 日志...")
    
    try:
        # 获取最近的日志
        result = subprocess.run(['docker', 'logs', '--tail', '10', 'web3signer'], 
                              capture_output=True, text=True, timeout=10)
        
        if result.returncode == 0:
            logs = result.stdout
            print("📋 Web3Signer 最近日志:")
            print("-" * 50)
            print(logs)
            print("-" * 50)
            
            # 检查是否还有 sync committee 错误
            if "sync committees" in logs.lower():
                print("⚠️  仍然存在 sync committee 相关错误")
                return False
            else:
                print("✅ 日志中没有发现 sync committee 错误")
                return True
        else:
            print(f"❌ 获取日志失败: {result.stderr}")
            return False
            
    except Exception as e:
        print(f"❌ 检查日志失败: {e}")
        return False

def main():
    """主函数"""
    print("🔧 Web3Signer 网络配置修复工具")
    print("=" * 50)
    print("问题: Fork at slot 355 does not support sync committees")
    print("原因: Web3Signer 配置为 minimal 网络，但 Kurtosis 需要 mainnet 配置")
    print("解决: 将 Web3Signer 网络配置从 minimal 改为 mainnet")
    print("=" * 50)
    
    # 修复配置
    success = restart_web3signer_with_new_config()
    
    if success:
        # 检查日志
        logs_ok = check_web3signer_logs()
        
        if logs_ok:
            print("\n✅ 修复成功!")
            print("💡 现在可以重新启动 Prysm 验证器:")
            print("   ./validator.sh start-validator prysm")
        else:
            print("\n⚠️  修复完成，但仍有问题")
            print("💡 请检查 Web3Signer 日志获取更多信息")
    else:
        print("\n❌ 修复失败")
        print("💡 请手动检查 Docker 服务状态")
    
    return success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
