#!/usr/bin/env python3
"""
调试 Prysm 安装问题
"""

import sys
import os
import subprocess
from pathlib import Path

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(project_root)

def debug_prysm_installation():
    """调试 Prysm 安装问题"""
    print("🔍 调试 Prysm 安装问题...")
    print("=" * 50)
    
    # 1. 检查文件是否存在
    print("1. 检查 Prysm 文件...")
    prysm_paths = [
        "/usr/local/bin/prysm",
        "/usr/bin/prysm",
        "./prysm.sh",
        "prysm"
    ]
    
    for path in prysm_paths:
        if os.path.exists(path):
            print(f"✅ 找到文件: {path}")
            # 检查权限
            if os.access(path, os.X_OK):
                print(f"   ✅ 可执行")
            else:
                print(f"   ❌ 不可执行")
        else:
            print(f"❌ 文件不存在: {path}")
    
    # 2. 检查 PATH 环境变量
    print("\n2. 检查 PATH 环境变量...")
    path_env = os.environ.get('PATH', '')
    print(f"PATH: {path_env}")
    
    # 3. 尝试直接运行
    print("\n3. 尝试直接运行 Prysm...")
    try:
        result = subprocess.run(['prysm', 'validator', '--help'], 
                              capture_output=True, text=True, timeout=10)
        print(f"返回码: {result.returncode}")
        print(f"标准输出: {result.stdout[:200]}...")
        print(f"错误输出: {result.stderr}")
    except FileNotFoundError:
        print("❌ 命令未找到")
    except subprocess.TimeoutExpired:
        print("❌ 命令超时")
    except Exception as e:
        print(f"❌ 运行失败: {e}")
    
    # 4. 尝试使用完整路径
    print("\n4. 尝试使用完整路径...")
    for path in prysm_paths:
        if os.path.exists(path):
            try:
                result = subprocess.run([path, 'validator', '--help'], 
                                      capture_output=True, text=True, timeout=10)
                print(f"✅ {path} 运行成功:")
                print(f"   返回码: {result.returncode}")
                print(f"   输出: {result.stdout[:200]}...")
                break
            except Exception as e:
                print(f"❌ {path} 运行失败: {e}")
    
    # 5. 检查 which 命令
    print("\n5. 检查 which 命令...")
    try:
        result = subprocess.run(['which', 'prysm'], 
                              capture_output=True, text=True)
        if result.returncode == 0:
            print(f"✅ which 找到: {result.stdout.strip()}")
        else:
            print("❌ which 未找到 prysm")
    except Exception as e:
        print(f"❌ which 命令失败: {e}")
    
    # 6. 检查文件内容
    print("\n6. 检查 Prysm 文件内容...")
    for path in prysm_paths:
        if os.path.exists(path):
            try:
                with open(path, 'r') as f:
                    content = f.read(200)  # 读取前200字符
                    print(f"✅ {path} 内容预览:")
                    print(f"   {content[:100]}...")
                    break
            except Exception as e:
                print(f"❌ 读取 {path} 失败: {e}")

def suggest_fixes():
    """建议修复方案"""
    print("\n💡 建议修复方案:")
    print("=" * 50)
    
    print("1. 重新安装 Prysm:")
    print("   curl -sSL https://raw.githubusercontent.com/prysmaticlabs/prysm/master/prysm.sh --output prysm.sh")
    print("   chmod +x prysm.sh")
    print("   sudo mv prysm.sh /usr/local/bin/prysm")
    print("   sudo chmod +x /usr/local/bin/prysm")
    
    print("\n2. 检查 PATH 环境变量:")
    print("   echo $PATH")
    print("   export PATH=$PATH:/usr/local/bin")
    
    print("\n3. 尝试直接运行:")
    print("   /usr/local/bin/prysm --version")
    
    print("\n4. 或者使用相对路径:")
    print("   ./prysm.sh --version")

def main():
    """主函数"""
    print("🚀 Prysm 安装调试工具")
    print("=" * 50)
    
    debug_prysm_installation()
    suggest_fixes()
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
