#!/usr/bin/env python3
"""
Kurtosis 替代方案设置
当 Kurtosis 不可用时，提供本地 Beacon 节点配置
"""

import sys
import os
import json
import subprocess
from pathlib import Path

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(project_root)

def check_kurtosis_installation():
    """检查 Kurtosis 是否已安装"""
    try:
        result = subprocess.run(["kurtosis", "--version"], 
                              capture_output=True, text=True, check=True)
        print(f"✅ Kurtosis 已安装: {result.stdout.strip()}")
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("❌ Kurtosis 未安装")
        return False

def install_kurtosis():
    """安装 Kurtosis"""
    print("🔧 安装 Kurtosis...")
    
    try:
        # 使用官方安装脚本
        install_script = """
        #!/bin/bash
        set -e
        curl -fsSL https://docs.kurtosis.com/install.sh | bash
        """
        
        print("📋 请运行以下命令安装 Kurtosis:")
        print("curl -fsSL https://docs.kurtosis.com/install.sh | bash")
        print("\n或者手动安装:")
        print("1. 访问: https://docs.kurtosis.com/install")
        print("2. 下载适合你系统的版本")
        print("3. 添加到 PATH")
        
        return False
        
    except Exception as e:
        print(f"❌ 安装 Kurtosis 失败: {e}")
        return False

def setup_local_beacon_node():
    """设置本地 Beacon 节点配置"""
    print("🔧 设置本地 Beacon 节点配置...")
    
    # 创建本地配置
    local_config = {
        "beacon": {
            "prysm": "http://localhost:3500",
            "lighthouse": "http://localhost:5052",
            "teku": "http://localhost:5051"
        },
        "execution": {
            "geth": "http://localhost:8545",
            "reth": "http://localhost:8545"
        },
        "source": "local_fallback"
    }
    
    # 保存配置
    config_file = Path(project_root) / "config" / "kurtosis_ports.json"
    config_file.parent.mkdir(parents=True, exist_ok=True)
    
    with open(config_file, 'w') as f:
        json.dump(local_config, f, indent=2)
    
    print(f"✅ 本地配置已保存到: {config_file}")
    return True

def test_beacon_endpoints():
    """测试 Beacon 端点"""
    print("🧪 测试 Beacon 端点...")
    
    endpoints = {
        "prysm": "http://localhost:3500",
        "lighthouse": "http://localhost:5052",
        "teku": "http://localhost:5051"
    }
    
    working_endpoints = {}
    
    for client_type, url in endpoints.items():
        try:
            import requests
            health_url = f"{url}/eth/v1/node/health"
            response = requests.get(health_url, timeout=3)
            
            if response.status_code == 200:
                working_endpoints[client_type] = url
                print(f"✅ {client_type}: {url}")
            else:
                print(f"⚠️  {client_type}: {url} (状态码: {response.status_code})")
                
        except requests.exceptions.ConnectionError:
            print(f"❌ {client_type}: {url} (连接失败)")
        except requests.exceptions.Timeout:
            print(f"⏰ {client_type}: {url} (超时)")
        except Exception as e:
            print(f"❌ {client_type}: {url} (错误: {e})")
    
    return working_endpoints

def main():
    """主函数"""
    print("🚀 Kurtosis 替代方案设置")
    print("=" * 40)
    
    # 检查 Kurtosis 安装
    if check_kurtosis_installation():
        print("✅ Kurtosis 已安装，可以使用完整功能")
        return True
    
    print("\n📋 Kurtosis 未安装，设置替代方案...")
    
    # 设置本地配置
    if setup_local_beacon_node():
        print("✅ 本地配置已设置")
    
    # 测试端点
    print("\n🧪 测试 Beacon 端点...")
    working_endpoints = test_beacon_endpoints()
    
    if working_endpoints:
        print(f"\n✅ 找到 {len(working_endpoints)} 个可用的 Beacon 端点")
        print("💡 现在可以使用 validator client 了")
        return True
    else:
        print("\n❌ 未找到可用的 Beacon 端点")
        print("💡 请启动本地 Beacon 节点或安装 Kurtosis")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
