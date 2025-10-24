#!/usr/bin/env python3
"""
检查和管理 Validator Client 安装
"""

import sys
import os
import subprocess
import platform
from pathlib import Path

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(project_root)

class ValidatorClientChecker:
    """Validator Client 检查器"""
    
    def __init__(self):
        self.system = platform.system().lower()
        self.arch = platform.machine().lower()
        
    def check_prysm(self) -> dict:
        """检查 Prysm 安装状态"""
        print("🔍 检查 Prysm...")
        
        status = {
            "installed": False,
            "version": None,
            "path": None,
            "install_command": None
        }
        
        try:
            # 检查 prysm 命令
            result = subprocess.run(['prysm', '--version'], 
                                  capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                status["installed"] = True
                status["version"] = result.stdout.strip()
                print(f"✅ Prysm 已安装: {status['version']}")
                
                # 获取路径
                path_result = subprocess.run(['which', 'prysm'], 
                                           capture_output=True, text=True)
                if path_result.returncode == 0:
                    status["path"] = path_result.stdout.strip()
                    print(f"   路径: {status['path']}")
            else:
                print("❌ Prysm 未安装")
                
        except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
            print("❌ Prysm 未安装或不在 PATH 中")
            
            # 尝试其他可能的路径
            print("🔍 尝试其他路径...")
            alternative_paths = [
                "/usr/local/bin/prysm",
                "/usr/bin/prysm",
                "./prysm.sh"
            ]
            
            for alt_path in alternative_paths:
                if os.path.exists(alt_path):
                    try:
                        result = subprocess.run([alt_path, '--version'], 
                                              capture_output=True, text=True, timeout=10)
                        if result.returncode == 0:
                            status["installed"] = True
                            status["version"] = result.stdout.strip()
                            status["path"] = alt_path
                            print(f"✅ 在 {alt_path} 找到 Prysm: {status['version']}")
                            break
                    except Exception as e:
                        print(f"⚠️  {alt_path} 运行失败: {e}")
        
        # 提供安装命令
        if not status["installed"]:
            if self.system == "linux":
                status["install_command"] = """
# 安装 Prysm (Linux)
curl -sSL https://raw.githubusercontent.com/prysmaticlabs/prysm/master/prysm.sh --output prysm.sh
chmod +x prysm.sh
sudo mv prysm.sh /usr/local/bin/prysm
"""
            else:
                status["install_command"] = """
# 请访问 Prysm 安装页面
https://docs.prylabs.network/docs/install/install-with-script
"""
        
        return status
    
    def check_lighthouse(self) -> dict:
        """检查 Lighthouse 安装状态"""
        print("🔍 检查 Lighthouse...")
        
        status = {
            "installed": False,
            "version": None,
            "path": None,
            "install_command": None
        }
        
        try:
            # 检查 lighthouse 命令
            result = subprocess.run(['lighthouse', '--version'], 
                                  capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                status["installed"] = True
                status["version"] = result.stdout.strip()
                print(f"✅ Lighthouse 已安装: {status['version']}")
                
                # 获取路径
                path_result = subprocess.run(['which', 'lighthouse'], 
                                           capture_output=True, text=True)
                if path_result.returncode == 0:
                    status["path"] = path_result.stdout.strip()
                    print(f"   路径: {status['path']}")
            else:
                print("❌ Lighthouse 未安装")
                
        except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
            print("❌ Lighthouse 未安装或不在 PATH 中")
        
        # 提供安装命令
        if not status["installed"]:
            if self.system == "linux":
                status["install_command"] = """
# 安装 Lighthouse (Linux)
# 方法1: 使用包管理器
sudo apt update
sudo apt install lighthouse

# 方法2: 从源码编译
git clone https://github.com/sigp/lighthouse.git
cd lighthouse
make
sudo make install
"""
            else:
                status["install_command"] = """
# 请访问 Lighthouse 安装页面
https://lighthouse-book.sigmaprime.io/installation.html
"""
        
        return status
    
    def check_teku(self) -> dict:
        """检查 Teku 安装状态"""
        print("🔍 检查 Teku...")
        
        status = {
            "installed": False,
            "version": None,
            "path": None,
            "install_command": None
        }
        
        try:
            # 检查 teku 命令
            result = subprocess.run(['teku', '--version'], 
                                  capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                status["installed"] = True
                status["version"] = result.stdout.strip()
                print(f"✅ Teku 已安装: {status['version']}")
                
                # 获取路径
                path_result = subprocess.run(['which', 'teku'], 
                                           capture_output=True, text=True)
                if path_result.returncode == 0:
                    status["path"] = path_result.stdout.strip()
                    print(f"   路径: {status['path']}")
            else:
                print("❌ Teku 未安装")
                
        except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
            print("❌ Teku 未安装或不在 PATH 中")
        
        # 提供安装命令
        if not status["installed"]:
            status["install_command"] = """
# 安装 Teku
# 方法1: 使用包管理器
sudo apt update
sudo apt install teku

# 方法2: 下载 JAR 文件
wget https://artifacts.consensys.net/public/teku/raw/names/teku.tar.gz/versions/latest/teku-latest.tar.gz
tar -xzf teku-latest.tar.gz
sudo mv teku-*/bin/teku /usr/local/bin/
"""
        
        return status
    
    def check_all_clients(self) -> dict:
        """检查所有客户端"""
        print("🚀 检查所有 Validator Client...")
        print("=" * 50)
        
        results = {
            "prysm": self.check_prysm(),
            "lighthouse": self.check_lighthouse(),
            "teku": self.check_teku()
        }
        
        print("\n📊 检查结果汇总:")
        print("=" * 50)
        
        installed_count = 0
        for client, status in results.items():
            if status["installed"]:
                print(f"✅ {client.capitalize()}: {status['version']}")
                installed_count += 1
            else:
                print(f"❌ {client.capitalize()}: 未安装")
        
        print(f"\n🎯 已安装客户端: {installed_count}/3")
        
        if installed_count == 0:
            print("\n💡 建议安装至少一个客户端:")
            print("   - Prysm: 功能最全面，推荐用于生产")
            print("   - Lighthouse: 性能优秀，资源占用少")
            print("   - Teku: 企业级，Java 实现")
        
        return results
    
    def show_install_commands(self, client: str = None):
        """显示安装命令"""
        if client:
            clients = [client]
        else:
            clients = ["prysm", "lighthouse", "teku"]
        
        for client_name in clients:
            if client_name == "prysm":
                status = self.check_prysm()
            elif client_name == "lighthouse":
                status = self.check_lighthouse()
            elif client_name == "teku":
                status = self.check_teku()
            else:
                continue
            
            if not status["installed"] and status["install_command"]:
                print(f"\n📋 {client_name.capitalize()} 安装命令:")
                print(status["install_command"])

def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description="检查 Validator Client 安装状态")
    parser.add_argument("--client", choices=["prysm", "lighthouse", "teku"], 
                       help="检查特定客户端")
    parser.add_argument("--install-commands", action="store_true", 
                       help="显示安装命令")
    
    args = parser.parse_args()
    
    checker = ValidatorClientChecker()
    
    if args.install_commands:
        checker.show_install_commands(args.client)
    else:
        if args.client:
            if args.client == "prysm":
                checker.check_prysm()
            elif args.client == "lighthouse":
                checker.check_lighthouse()
            elif args.client == "teku":
                checker.check_teku()
        else:
            checker.check_all_clients()
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
