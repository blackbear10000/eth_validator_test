#!/usr/bin/env python3
"""
测试 Kurtosis 命令可用性
"""

import sys
import os
import subprocess

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(project_root)

def test_kurtosis_command():
    """测试 Kurtosis 命令"""
    print("🔍 测试 Kurtosis 命令可用性...")
    
    # 测试 1: 检查 kurtosis 命令是否存在
    try:
        result = subprocess.run(["which", "kurtosis"], capture_output=True, text=True)
        if result.returncode == 0:
            print(f"✅ Kurtosis 路径: {result.stdout.strip()}")
        else:
            print("❌ Kurtosis 命令未找到")
            return False
    except Exception as e:
        print(f"❌ 检查 Kurtosis 路径失败: {e}")
        return False
    
    # 测试 2: 检查 kurtosis 版本
    try:
        result = subprocess.run(["kurtosis", "--version"], capture_output=True, text=True)
        if result.returncode == 0:
            print(f"✅ Kurtosis 版本: {result.stdout.strip()}")
        else:
            print(f"⚠️  Kurtosis 版本检查失败: {result.stderr}")
    except Exception as e:
        print(f"⚠️  Kurtosis 版本检查异常: {e}")
    
    # 测试 3: 检查 enclave 列表
    try:
        result = subprocess.run(["kurtosis", "enclave", "ls"], capture_output=True, text=True)
        if result.returncode == 0:
            print(f"✅ Kurtosis enclave 列表:")
            print(result.stdout)
        else:
            print(f"❌ Kurtosis enclave 列表失败: {result.stderr}")
    except Exception as e:
        print(f"❌ Kurtosis enclave 列表异常: {e}")
    
    # 测试 4: 检查特定 enclave
    try:
        result = subprocess.run(["kurtosis", "enclave", "inspect", "eth-devnet"], 
                              capture_output=True, text=True)
        if result.returncode == 0:
            print(f"✅ Kurtosis enclave inspect 成功")
            print(f"   输出长度: {len(result.stdout)} 字符")
            print(f"   前 100 字符: {result.stdout[:100]}...")
        else:
            print(f"❌ Kurtosis enclave inspect 失败: {result.stderr}")
    except Exception as e:
        print(f"❌ Kurtosis enclave inspect 异常: {e}")
    
    return True

def main():
    """主函数"""
    print("🚀 Kurtosis 命令测试")
    print("=" * 40)
    
    success = test_kurtosis_command()
    
    if success:
        print("\n✅ 测试完成")
    else:
        print("\n❌ 测试失败")
    
    return success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
