#!/usr/bin/env python3
"""
重置 Web3Signer 并重新加载密钥
"""

import subprocess
import time
import sys
from pathlib import Path

def run_command(cmd, description):
    """运行命令并显示结果"""
    print(f"🔧 {description}...")
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=60)
        if result.returncode == 0:
            print(f"✅ {description} 成功")
            if result.stdout:
                print(f"   输出: {result.stdout.strip()}")
            return True
        else:
            print(f"❌ {description} 失败")
            if result.stderr:
                print(f"   错误: {result.stderr.strip()}")
            return False
    except subprocess.TimeoutExpired:
        print(f"❌ {description} 超时")
        return False
    except Exception as e:
        print(f"❌ {description} 出错: {e}")
        return False

def reset_web3signer():
    """重置 Web3Signer 并重新加载密钥"""
    print("🔄 Web3Signer 完整重置流程")
    print("=" * 40)
    
    # 1. 清理 keys 目录
    print("🧹 步骤 1: 清理 keys 目录...")
    if not run_command("python3 ../scripts/clean_web3signer_keys.py", "清理 keys 目录"):
        print("❌ 清理 keys 目录失败")
        return False
    
    # 2. 停止 Web3Signer
    print("\n🛑 步骤 2: 停止 Web3Signer...")
    if not run_command("docker stop web3signer", "停止 Web3Signer"):
        print("⚠️  Web3Signer 可能已经停止")
    
    # 3. 等待服务停止
    print("⏳ 等待服务停止...")
    time.sleep(5)
    
    # 4. 重新启动 Web3Signer
    print("\n🚀 步骤 3: 重新启动 Web3Signer...")
    if not run_command("docker start web3signer", "启动 Web3Signer"):
        print("❌ Web3Signer 启动失败")
        return False
    
    # 5. 等待 Web3Signer 启动
    print("⏳ 等待 Web3Signer 启动...")
    time.sleep(15)
    
    # 6. 检查 Web3Signer 健康状态
    print("\n🔍 步骤 4: 检查 Web3Signer 健康状态...")
    for attempt in range(5):
        print(f"   尝试 {attempt + 1}/5...")
        if run_command("curl -f http://localhost:9000/upcheck", f"检查 Web3Signer 健康状态 (尝试 {attempt + 1})"):
            print("✅ Web3Signer 启动成功")
            break
        else:
            print(f"⏳ 等待 5 秒后重试...")
            time.sleep(5)
    else:
        print("❌ Web3Signer 启动失败")
        return False
    
    # 7. 重新加载密钥
    print("\n🔑 步骤 5: 重新加载密钥...")
    if not run_command("python3 core/web3signer_manager.py load", "加载密钥到 Web3Signer"):
        print("❌ 密钥加载失败")
        return False
    
    # 8. 验证密钥加载
    print("\n🔍 步骤 6: 验证密钥加载...")
    if not run_command("python3 core/web3signer_manager.py verify", "验证密钥加载"):
        print("❌ 密钥验证失败")
        return False
    
    print("\n🎉 Web3Signer 重置和重新加载完成！")
    return True

if __name__ == "__main__":
    if not reset_web3signer():
        sys.exit(1)
