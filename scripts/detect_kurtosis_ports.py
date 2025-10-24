#!/usr/bin/env python3
"""
动态检测 Kurtosis 网络的实际端口
支持检测 Beacon API、Execution API 等服务的端口
"""

import sys
import os
import json
import subprocess
import requests
import argparse
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(project_root)

class KurtosisPortDetector:
    """Kurtosis 端口检测器"""
    
    def __init__(self, enclave_name: str = "eth-devnet"):
        self.enclave_name = enclave_name
        self.detected_ports = {}
    
    def get_enclave_info(self) -> Optional[Dict]:
        """获取 Kurtosis enclave 信息"""
        try:
            # 首先检查 kurtosis 命令是否可用
            try:
                subprocess.run(["kurtosis", "--version"], capture_output=True, check=True)
            except (subprocess.CalledProcessError, FileNotFoundError):
                print("⚠️  Kurtosis 版本检查失败，但继续尝试运行命令...")
                # 不直接返回 None，继续尝试运行命令
            
            result = subprocess.run([
                "kurtosis", "enclave", "inspect", self.enclave_name
            ], capture_output=True, text=True, check=True)
            
            print(f"🔍 Kurtosis 输出长度: {len(result.stdout)} 字符")
            
            # 解析表格格式的输出
            return self._parse_table_output(result.stdout)
            
        except subprocess.CalledProcessError as e:
            print(f"❌ 无法获取 enclave 信息: {e}")
            print(f"   错误输出: {e.stderr}")
            print(f"💡 请确保 Kurtosis enclave '{self.enclave_name}' 正在运行")
            print(f"   运行: kurtosis enclave ls")
            return None
        except Exception as e:
            print(f"❌ 解析 enclave 信息失败: {e}")
            return None
    
    def _parse_table_output(self, output: str) -> Dict:
        """解析 Kurtosis 表格格式输出"""
        print("🔍 解析表格格式输出...")
        
        services = {}
        lines = output.strip().split('\n')
        
        # 查找 User Services 部分
        in_services_section = False
        for line in lines:
            if "User Services" in line:
                in_services_section = True
                continue
            
            if in_services_section and line.strip():
                # 解析服务行
                if "UUID" in line and "Name" in line and "Ports" in line:
                    continue  # 跳过表头
                
                if line.strip().startswith("="):
                    break  # 遇到下一个部分，结束
                
                # 解析服务信息
                service_info = self._parse_service_line(line)
                if service_info:
                    services[service_info['name']] = service_info
        
        print(f"🔍 解析到 {len(services)} 个服务")
        return {"services": services}
    
    def _parse_service_line(self, line: str) -> Optional[Dict]:
        """解析单个服务行"""
        try:
            print(f"🔍 解析服务行: {line[:100]}...")
            
            # 使用正则表达式解析更复杂的格式
            import re
            
            # 匹配格式: UUID Name Ports Status
            # 例如: 354e03f6ff87 cl-1-prysm-geth http: 3500/tcp -> http://127.0.0.1:33522 RUNNING
            pattern = r'^([a-f0-9]{12})\s+([^\s]+(?:\s+[^\s]+)*?)\s+(.*?)\s+(RUNNING|STOPPED)$'
            match = re.match(pattern, line)
            
            if not match:
                print(f"⚠️  服务行格式不匹配: {line[:50]}...")
                return None
            
            uuid = match.group(1)
            service_name = match.group(2)
            ports_text = match.group(3)
            status = match.group(4)
            
            print(f"   服务名: {service_name}")
            print(f"   端口文本: {ports_text[:50]}...")
            
            # 解析端口信息
            ports = {}
            
            # 查找所有端口映射
            port_pattern = r'(\w+):\s*(\d+)/(\w+)\s*->\s*([^\s]+)'
            port_matches = re.findall(port_pattern, ports_text)
            
            for port_name, internal_port, protocol, external_mapping in port_matches:
                # 从外部映射中提取本地端口
                if ":" in external_mapping:
                    local_port = external_mapping.split(":")[-1]
                    try:
                        ports[port_name] = {
                            "number": int(local_port),
                            "mapping": f"{port_name}: {internal_port}/{protocol} -> {external_mapping}",
                            "internal_port": int(internal_port),
                            "protocol": protocol
                        }
                        print(f"   端口 {port_name}: {local_port}")
                    except ValueError:
                        print(f"   ⚠️  无效端口号: {local_port}")
            
            return {
                "name": service_name,
                "uuid": uuid,
                "ports": ports,
                "status": status
            }
            
        except Exception as e:
            print(f"⚠️  解析服务行失败: {line[:50]}... - {e}")
            import traceback
            print(f"详细错误: {traceback.format_exc()}")
            return None
    
    def detect_beacon_ports(self) -> Dict[str, str]:
        """检测 Beacon API 端口"""
        print("🔍 检测 Beacon API 端口...")
        
        beacon_ports = {}
        enclave_info = self.get_enclave_info()
        
        if not enclave_info:
            print("❌ 无法获取 enclave 信息")
            return beacon_ports
        
        try:
            services = enclave_info.get('services', {})
            print(f"🔍 找到 {len(services)} 个服务")
            
            # 打印所有服务名称以便调试
            for service_name in services.keys():
                print(f"   📋 服务: {service_name}")
            
            # 查找 Beacon API 服务
            for service_name, service_info in services.items():
                print(f"🔍 检查服务: {service_name}")
                ports = service_info.get('ports', {})
                print(f"   端口: {list(ports.keys())}")
                
                # 查找 Prysm Beacon API (cl-1-prysm-geth)
                if 'prysm' in service_name.lower() and 'cl-' in service_name.lower():
                    for port_name, port_info in ports.items():
                        if port_name == 'rpc':  # Prysm 使用 rpc 端口作为 gRPC API
                            port = port_info.get('number')
                            if port:
                                beacon_ports['prysm'] = f"localhost:{port}"
                                print(f"✅ 找到 Prysm Beacon gRPC API: {beacon_ports['prysm']}")
                                break
                
                # 查找 Lighthouse Beacon API (cl-2-lighthouse-reth)
                elif 'lighthouse' in service_name.lower() and 'cl-' in service_name.lower():
                    for port_name, port_info in ports.items():
                        if port_name == 'http':  # Lighthouse 使用 http 端口作为 Beacon API
                            port = port_info.get('number')
                            if port:
                                beacon_ports['lighthouse'] = f"http://localhost:{port}"
                                print(f"✅ 找到 Lighthouse Beacon API: {beacon_ports['lighthouse']}")
                                break
                
                # 查找 Teku Beacon API (如果有的话)
                elif 'teku' in service_name.lower() and 'cl-' in service_name.lower():
                    for port_name, port_info in ports.items():
                        if port_name == 'http':  # Teku 使用 http 端口作为 Beacon API
                            port = port_info.get('number')
                            if port:
                                beacon_ports['teku'] = f"http://localhost:{port}"
                                print(f"✅ 找到 Teku Beacon API: {beacon_ports['teku']}")
                                break
        
        except Exception as e:
            print(f"❌ 检测 Beacon 端口失败: {e}")
            import traceback
            print(f"详细错误: {traceback.format_exc()}")
        
        return beacon_ports
    
    def detect_execution_ports(self) -> Dict[str, str]:
        """检测 Execution API 端口"""
        print("🔍 检测 Execution API 端口...")
        
        execution_ports = {}
        enclave_info = self.get_enclave_info()
        
        if not enclave_info:
            return execution_ports
        
        try:
            services = enclave_info.get('services', {})
            
            # 查找 Execution API 服务
            for service_name, service_info in services.items():
                print(f"🔍 检查 Execution 服务: {service_name}")
                ports = service_info.get('ports', {})
                print(f"   端口: {list(ports.keys())}")
                
                # 查找 Geth Execution API (el-1-geth-prysm)
                if 'geth' in service_name.lower() and 'el-' in service_name.lower():
                    for port_name, port_info in ports.items():
                        if port_name == 'rpc':  # Geth 使用 rpc 端口作为 HTTP API
                            port = port_info.get('number')
                            if port:
                                execution_ports['geth'] = f"http://localhost:{port}"
                                print(f"✅ 找到 Geth Execution API: {execution_ports['geth']}")
                                break
                
                # 查找 Reth Execution API (el-2-reth-lighthouse)
                elif 'reth' in service_name.lower() and 'el-' in service_name.lower():
                    for port_name, port_info in ports.items():
                        if port_name == 'rpc':  # Reth 使用 rpc 端口作为 HTTP API
                            port = port_info.get('number')
                            if port:
                                execution_ports['reth'] = f"http://localhost:{port}"
                                print(f"✅ 找到 Reth Execution API: {execution_ports['reth']}")
                                break
        
        except Exception as e:
            print(f"❌ 检测 Execution 端口失败: {e}")
            import traceback
            print(f"详细错误: {traceback.format_exc()}")
        
        return execution_ports
    
    def test_beacon_endpoints(self, beacon_ports: Dict[str, str]) -> Dict[str, str]:
        """测试 Beacon 端点是否可用"""
        print("🧪 测试 Beacon 端点...")
        
        working_endpoints = {}
        
        for client_type, url in beacon_ports.items():
            try:
                # 测试健康检查端点
                health_url = f"{url}/eth/v1/node/health"
                response = requests.get(health_url, timeout=5)
                
                if response.status_code == 200:
                    working_endpoints[client_type] = url
                    print(f"✅ {client_type} Beacon API 可用: {url}")
                else:
                    print(f"⚠️  {client_type} Beacon API 响应异常: {response.status_code}")
                    
            except requests.exceptions.ConnectionError:
                print(f"❌ {client_type} Beacon API 连接失败: {url}")
            except requests.exceptions.Timeout:
                print(f"⏰ {client_type} Beacon API 超时: {url}")
            except Exception as e:
                print(f"❌ {client_type} Beacon API 测试失败: {e}")
        
        return working_endpoints
    
    def detect_all_ports(self) -> Dict[str, Dict[str, str]]:
        """检测所有端口"""
        print(f"🚀 检测 Kurtosis enclave '{self.enclave_name}' 的端口...")
        
        # 检测 Beacon API 端口
        beacon_ports = self.detect_beacon_ports()
        
        # 检测 Execution API 端口
        execution_ports = self.detect_execution_ports()
        
        # 如果 Kurtosis 检测失败，尝试常见端口
        if not beacon_ports and not execution_ports:
            print("🔄 Kurtosis 检测失败，尝试常见端口...")
            beacon_ports = self._detect_common_ports()
        
        # 测试 Beacon 端点
        working_beacon = self.test_beacon_endpoints(beacon_ports)
        
        return {
            "beacon": working_beacon,
            "execution": execution_ports
        }
    
    def _detect_common_ports(self) -> Dict[str, str]:
        """检测常见端口（当 Kurtosis 不可用时）"""
        print("🔍 检测常见端口...")
        
        common_ports = {
            "prysm": "http://localhost:3500",
            "lighthouse": "http://localhost:5052",
            "teku": "http://localhost:5051"
        }
        
        return common_ports
    
    def save_port_config(self, ports: Dict[str, Dict[str, str]], output_file: str = "config/kurtosis_ports.json"):
        """保存端口配置到文件"""
        output_path = Path(project_root) / output_file
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, 'w') as f:
            json.dump(ports, f, indent=2)
        
        print(f"💾 端口配置已保存到: {output_path}")
        return str(output_path)
    
    def load_port_config(self, config_file: str = "config/kurtosis_ports.json") -> Dict[str, Dict[str, str]]:
        """从文件加载端口配置"""
        config_path = Path(project_root) / config_file
        
        if not config_path.exists():
            print(f"⚠️  配置文件不存在: {config_path}")
            return {}
        
        try:
            with open(config_path, 'r') as f:
                return json.load(f)
        except Exception as e:
            print(f"❌ 加载配置文件失败: {e}")
            return {}

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="检测 Kurtosis 网络端口")
    parser.add_argument("--enclave", default="eth-devnet", help="Kurtosis enclave 名称")
    parser.add_argument("--save", action="store_true", help="保存端口配置到文件")
    parser.add_argument("--load", action="store_true", help="从文件加载端口配置")
    parser.add_argument("--output", default="config/kurtosis_ports.json", help="输出文件路径")
    
    args = parser.parse_args()
    
    detector = KurtosisPortDetector(args.enclave)
    
    if args.load:
        # 从文件加载配置
        ports = detector.load_port_config(args.output)
        if ports:
            print("📋 从文件加载的端口配置:")
            print(json.dumps(ports, indent=2))
        return
    
    # 检测端口
    ports = detector.detect_all_ports()
    
    print("\n📊 检测结果:")
    print("=" * 50)
    
    if ports.get("beacon"):
        print("🔗 Beacon API 端点:")
        for client_type, url in ports["beacon"].items():
            print(f"   {client_type}: {url}")
    else:
        print("❌ 未找到可用的 Beacon API 端点")
    
    if ports.get("execution"):
        print("\n⚡ Execution API 端点:")
        for client_type, url in ports["execution"].items():
            print(f"   {client_type}: {url}")
    else:
        print("❌ 未找到可用的 Execution API 端点")
    
    # 保存配置
    if args.save:
        config_file = detector.save_port_config(ports, args.output)
        print(f"\n💡 使用以下命令加载配置:")
        print(f"   python3 scripts/detect_kurtosis_ports.py --load --output {args.output}")
    
    return ports

if __name__ == "__main__":
    main()
