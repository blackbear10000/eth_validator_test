#!/usr/bin/env python3
"""
调试 Kurtosis 输出格式
帮助诊断端口检测问题
"""

import sys
import os
import json
import subprocess
from pathlib import Path

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(project_root)

def debug_kurtosis_output():
    """调试 Kurtosis 输出"""
    print("🔍 调试 Kurtosis 输出格式...")
    
    try:
        # 运行 kurtosis enclave inspect 命令
        result = subprocess.run([
            "kurtosis", "enclave", "inspect", "eth-devnet"
        ], capture_output=True, text=True, check=True)
        
        print("=" * 60)
        print("📋 完整输出:")
        print("=" * 60)
        print(result.stdout)
        print("=" * 60)
        
        print(f"\n📊 输出统计:")
        print(f"   总字符数: {len(result.stdout)}")
        print(f"   总行数: {len(result.stdout.splitlines())}")
        
        # 尝试解析 JSON
        print(f"\n🔍 JSON 解析测试:")
        
        # 方法1: 直接解析
        try:
            data = json.loads(result.stdout.strip())
            print("✅ 方法1: 直接解析成功")
            print(f"   根键: {list(data.keys())}")
            if 'services' in data:
                print(f"   服务数量: {len(data['services'])}")
                for service_name in data['services'].keys():
                    print(f"     - {service_name}")
        except Exception as e:
            print(f"❌ 方法1: 直接解析失败 - {e}")
        
        # 方法2: 查找 JSON 部分
        try:
            lines = result.stdout.strip().split('\n')
            json_start = False
            json_lines = []
            
            for line in lines:
                if line.strip().startswith('{'):
                    json_start = True
                if json_start:
                    json_lines.append(line)
            
            if json_lines:
                json_str = '\n'.join(json_lines)
                data = json.loads(json_str)
                print("✅ 方法2: 查找 JSON 部分成功")
                print(f"   根键: {list(data.keys())}")
            else:
                print("❌ 方法2: 未找到 JSON 部分")
        except Exception as e:
            print(f"❌ 方法2: 查找 JSON 部分失败 - {e}")
        
        # 方法3: 查找 services 部分
        try:
            lines = result.stdout.strip().split('\n')
            for i, line in enumerate(lines):
                if '"services"' in line:
                    json_lines = lines[i:]
                    json_str = '\n'.join(json_lines)
                    data = json.loads(json_str)
                    print("✅ 方法3: 从 services 开始解析成功")
                    print(f"   根键: {list(data.keys())}")
                    break
            else:
                print("❌ 方法3: 未找到 services 部分")
        except Exception as e:
            print(f"❌ 方法3: 从 services 解析失败 - {e}")
        
        return True
        
    except subprocess.CalledProcessError as e:
        print(f"❌ Kurtosis 命令执行失败: {e}")
        print(f"   错误输出: {e.stderr}")
        return False
    except FileNotFoundError:
        print("❌ Kurtosis 命令未找到")
        return False
    except Exception as e:
        print(f"❌ 调试过程出错: {e}")
        return False

def main():
    """主函数"""
    print("🚀 Kurtosis 输出调试工具")
    print("=" * 40)
    
    success = debug_kurtosis_output()
    
    if success:
        print("\n✅ 调试完成")
    else:
        print("\n❌ 调试失败")
    
    return success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
