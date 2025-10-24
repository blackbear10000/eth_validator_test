#!/usr/bin/env python3
"""
启动 Validator Client 连接到 Web3Signer
支持 Prysm、Lighthouse、Teku 三种客户端
"""

import sys
import os
import json
import argparse
import subprocess
from pathlib import Path
from typing import List, Dict, Any

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(project_root)
sys.path.append(os.path.join(project_root, 'code'))

from core.vault_key_manager import VaultKeyManager
from utils.validator_client_config import ValidatorClientConfig

class ValidatorClientStarter:
    """Validator Client 启动器"""
    
    def __init__(self):
        self.vault_manager = VaultKeyManager()
        self.config_generator = ValidatorClientConfig()
        
        # Web3Signer 配置（基于你的 docker-compose.yml）
        self.web3signer_url = "http://localhost:9002"  # HAProxy 负载均衡器
        self.web3signer_direct = "http://localhost:9000"  # 直接连接
        
        # 动态检测 Kurtosis 端口
        self.kurtosis_ports = self._detect_kurtosis_ports()
        
        # Beacon 节点配置（动态检测）
        self.beacon_urls = self.kurtosis_ports.get("beacon", {
            "prysm": "http://localhost:3500",
            "lighthouse": "http://localhost:5052", 
            "teku": "http://localhost:5051"
        })
    
    def _detect_kurtosis_ports(self) -> Dict[str, Dict[str, str]]:
        """动态检测 Kurtosis 网络端口"""
        print("🔍 检测 Kurtosis 网络端口...")
        
        try:
            # 总是重新检测端口，确保使用最新的端口信息
            from scripts.detect_kurtosis_ports import KurtosisPortDetector
            detector = KurtosisPortDetector()
            ports = detector.detect_all_ports()
            
            # 保存检测结果
            if ports.get("beacon"):
                detector.save_port_config(ports)
                print("💾 端口配置已保存")
            
            return ports
            
        except Exception as e:
            print(f"⚠️  动态检测端口失败: {e}")
            print("📋 使用默认端口配置")
            return {}
    
    def get_active_validator_keys(self) -> List[str]:
        """获取活跃的验证者公钥"""
        try:
            active_keys = self.vault_manager.list_keys(status='active')
            pubkeys = [key.pubkey for key in active_keys]
            
            print(f"📋 找到 {len(pubkeys)} 个活跃验证者密钥")
            for i, pubkey in enumerate(pubkeys, 1):
                print(f"   {i}. {pubkey[:10]}...")
            
            return pubkeys
            
        except Exception as e:
            print(f"❌ 获取验证者密钥失败: {e}")
            return []
    
    def generate_client_config(self, client_type: str, pubkeys: List[str]) -> str:
        """生成客户端配置"""
        print(f"🔧 生成 {client_type} 客户端配置...")
        
        # 使用动态检测的端口
        beacon_url = self.beacon_urls.get(client_type, "http://localhost:3500")
        print(f"📡 使用 Beacon API: {beacon_url}")
        
        output_dir = f"configs/{client_type}"
        
        if client_type == "prysm":
            config_path = self.config_generator.generate_prysm_config(
                pubkeys, beacon_url, output_dir
            )
        elif client_type == "lighthouse":
            config_path = self.config_generator.generate_lighthouse_config(
                pubkeys, beacon_url, output_dir
            )
        elif client_type == "teku":
            config_path = self.config_generator.generate_teku_config(
                pubkeys, beacon_url, output_dir
            )
        else:
            raise ValueError(f"不支持的客户端类型: {client_type}")
        
        print(f"✅ {client_type} 配置已生成: {config_path}")
        return config_path
    
    def start_prysm_validator(self, config_path: str) -> bool:
        """启动 Prysm 验证者"""
        print("🚀 启动 Prysm 验证者...")
        
        try:
            # 检查 Prysm 是否已安装
            prysm_path = None
            result = subprocess.run(['prysm', 'validator', '--help'], 
                                  capture_output=True, text=True)
            if result.returncode == 0:
                prysm_path = 'prysm'
            else:
                # 尝试其他可能的路径
                alternative_paths = [
                    "/usr/local/bin/prysm",
                    "/usr/bin/prysm",
                    "./prysm.sh"
                ]
                
                for alt_path in alternative_paths:
                    if os.path.exists(alt_path):
                        try:
                            result = subprocess.run([alt_path, 'validator', '--help'], 
                                                  capture_output=True, text=True)
                            if result.returncode == 0:
                                prysm_path = alt_path
                                break
                        except Exception:
                            continue
            
            if not prysm_path:
                print("❌ Prysm 未安装或不在 PATH 中")
                print("💡 请先安装 Prysm:")
                print("   1. 运行: ./validator.sh check-clients")
                print("   2. 运行: ./validator.sh install-commands")
                print("   3. 按照提示安装 Prysm")
                return False
            
            print(f"✅ 找到 Prysm: {prysm_path}")
            
            # 启动 Prysm 验证者
            start_script = Path(config_path) / "start-validator.sh"
            if start_script.exists():
                print(f"📋 运行启动脚本: {start_script}")
                subprocess.run(['bash', str(start_script)], check=True)
                return True
            else:
                print(f"❌ 启动脚本不存在: {start_script}")
                return False
                
        except subprocess.CalledProcessError as e:
            print(f"❌ Prysm 启动失败: {e}")
            return False
        except Exception as e:
            print(f"❌ 启动 Prysm 时出错: {e}")
            return False
    
    def start_lighthouse_validator(self, config_path: str) -> bool:
        """启动 Lighthouse 验证者"""
        print("🚀 启动 Lighthouse 验证者...")
        
        try:
            # 检查 Lighthouse 是否已安装
            result = subprocess.run(['lighthouse', '--version'], 
                                  capture_output=True, text=True)
            if result.returncode != 0:
                print("❌ Lighthouse 未安装或不在 PATH 中")
                print("💡 请先安装 Lighthouse:")
                print("   1. 运行: ./validator.sh check-clients")
                print("   2. 运行: ./validator.sh install-commands")
                print("   3. 按照提示安装 Lighthouse")
                return False
            
            # 启动 Lighthouse 验证者
            start_script = Path(config_path) / "start-validator.sh"
            if start_script.exists():
                print(f"📋 运行启动脚本: {start_script}")
                subprocess.run(['bash', str(start_script)], check=True)
                return True
            else:
                print(f"❌ 启动脚本不存在: {start_script}")
                return False
                
        except subprocess.CalledProcessError as e:
            print(f"❌ Lighthouse 启动失败: {e}")
            return False
        except Exception as e:
            print(f"❌ 启动 Lighthouse 时出错: {e}")
            return False
    
    def start_teku_validator(self, config_path: str) -> bool:
        """启动 Teku 验证者"""
        print("🚀 启动 Teku 验证者...")
        
        try:
            # 检查 Teku 是否已安装
            result = subprocess.run(['teku', '--version'], 
                                  capture_output=True, text=True)
            if result.returncode != 0:
                print("❌ Teku 未安装或不在 PATH 中")
                print("💡 请先安装 Teku:")
                print("   1. 运行: ./validator.sh check-clients")
                print("   2. 运行: ./validator.sh install-commands")
                print("   3. 按照提示安装 Teku")
                return False
            
            # 启动 Teku 验证者
            start_script = Path(config_path) / "start-validator.sh"
            if start_script.exists():
                print(f"📋 运行启动脚本: {start_script}")
                subprocess.run(['bash', str(start_script)], check=True)
                return True
            else:
                print(f"❌ 启动脚本不存在: {start_script}")
                return False
                
        except subprocess.CalledProcessError as e:
            print(f"❌ Teku 启动失败: {e}")
            return False
        except Exception as e:
            print(f"❌ 启动 Teku 时出错: {e}")
            return False
    
    def start_validator_client(self, client_type: str, pubkeys: List[str] = None) -> bool:
        """启动验证者客户端"""
        print(f"🚀 启动 {client_type} 验证者客户端...")
        
        # 获取验证者密钥
        if not pubkeys:
            pubkeys = self.get_active_validator_keys()
            if not pubkeys:
                print("❌ 没有找到活跃的验证者密钥")
                return False
        
        # 生成配置
        try:
            config_path = self.generate_client_config(client_type, pubkeys)
        except Exception as e:
            print(f"❌ 生成配置失败: {e}")
            return False
        
        # 启动客户端
        if client_type == "prysm":
            return self.start_prysm_validator(config_path)
        elif client_type == "lighthouse":
            return self.start_lighthouse_validator(config_path)
        elif client_type == "teku":
            return self.start_teku_validator(config_path)
        else:
            print(f"❌ 不支持的客户端类型: {client_type}")
            return False
    
    def check_services(self) -> Dict[str, bool]:
        """检查服务状态"""
        print("🔍 检查服务状态...")
        
        services = {
            "Web3Signer": False,
            "Vault": False,
            "Kurtosis Beacon Node": False
        }
        
        # 检查 Web3Signer
        try:
            import requests
            response = requests.get(f"{self.web3signer_direct}/upcheck", timeout=5)
            services["Web3Signer"] = response.status_code == 200
        except:
            pass
        
        # 检查 Vault
        try:
            import requests
            headers = {"X-Vault-Token": "dev-root-token"}
            response = requests.get("http://localhost:8200/v1/sys/health", 
                                  headers=headers, timeout=5)
            services["Vault"] = response.status_code == 200
        except:
            pass
        
        # 检查 Kurtosis Beacon 节点（使用动态检测的端口）
        beacon_working = False
        for client_type, beacon_url in self.beacon_urls.items():
            try:
                import requests
                health_url = f"{beacon_url}/eth/v1/node/health"
                response = requests.get(health_url, timeout=5)
                if response.status_code == 200:
                    services["Kurtosis Beacon Node"] = True
                    print(f"   ✅ {client_type} Beacon API: {beacon_url}")
                    beacon_working = True
                    break
            except:
                continue
        
        if not beacon_working:
            print("   ❌ 未找到可用的 Kurtosis Beacon API")
        
        # 显示状态
        for service, status in services.items():
            status_icon = "✅" if status else "❌"
            print(f"   {status_icon} {service}")
        
        return services

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="启动 Validator Client")
    parser.add_argument("client", nargs="?", choices=["prysm", "lighthouse", "teku"], 
                       help="验证者客户端类型")
    parser.add_argument("--pubkeys", nargs="+", help="指定验证者公钥")
    parser.add_argument("--check-services", action="store_true", 
                       help="检查服务状态")
    parser.add_argument("--config-only", action="store_true", 
                       help="仅生成配置，不启动客户端")
    
    args = parser.parse_args()
    
    starter = ValidatorClientStarter()
    
    # 检查服务状态
    if args.check_services:
        services = starter.check_services()
        all_ready = all(services.values())
        
        if not all_ready:
            print("\n⚠️  部分服务未就绪，请先启动基础设施:")
            print("   ./validator.sh start")
            return False
        
        print("\n✅ 所有服务已就绪")
        return True
    
    # 仅生成配置
    if args.config_only:
        pubkeys = args.pubkeys or starter.get_active_validator_keys()
        if not pubkeys:
            print("❌ 没有找到验证者密钥")
            return False
        
        try:
            config_path = starter.generate_client_config(args.client, pubkeys)
            print(f"✅ 配置已生成: {config_path}")
            return True
        except Exception as e:
            print(f"❌ 生成配置失败: {e}")
            return False
    
    # 启动验证者客户端
    success = starter.start_validator_client(args.client, args.pubkeys)
    
    if success:
        print(f"\n🎉 {args.client} 验证者客户端启动成功!")
        print("📋 验证者现在正在使用 Web3Signer 进行签名")
        print("🔗 Web3Signer URL:", starter.web3signer_url)
    else:
        print(f"\n❌ {args.client} 验证者客户端启动失败")
    
    return success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
