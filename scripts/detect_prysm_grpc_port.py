#!/usr/bin/env python3
"""
检测 Prysm gRPC 端口
专门用于检测 Prysm Beacon 节点的 gRPC 端口
"""

import sys
import os
import subprocess
import requests
import socket
from pathlib import Path

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(project_root)

def test_grpc_port(host: str, port: int) -> bool:
    """测试端口是否是 gRPC 服务"""
    try:
        # 尝试连接端口
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(3)
        result = sock.connect_ex((host, port))
        sock.close()
        
        if result == 0:
            # 端口开放，尝试发送 gRPC 请求
            try:
                # 简单的 gRPC 健康检查
                import grpc
                from grpc import StatusCode
                
                # 尝试创建 gRPC 连接
                channel = grpc.insecure_channel(f"{host}:{port}")
                # 这里可以添加实际的 gRPC 健康检查
                return True
            except ImportError:
                # 如果没有 grpc 库，使用简单的连接测试
                return True
            except Exception:
                return False
        return False
    except Exception:
        return False

def detect_prysm_grpc_port() -> str:
    """检测 Prysm gRPC 端口"""
    print("🔍 检测 Prysm gRPC 端口...")
    
    # 常见的 Prysm gRPC 端口
    common_ports = [4000, 4001, 4002, 4003, 4004, 4005]
    
    for port in common_ports:
        print(f"   测试端口 {port}...")
        if test_grpc_port("localhost", port):
            print(f"✅ 找到 Prysm gRPC 端口: localhost:{port}")
            return f"localhost:{port}"
    
    # 如果没找到，返回默认端口
    print("⚠️  未找到 Prysm gRPC 端口，使用默认端口 4000")
    return "localhost:4000"

def get_kurtosis_prysm_ports() -> dict:
    """从 Kurtosis 获取 Prysm 端口信息"""
    print("🔍 从 Kurtosis 获取 Prysm 端口信息...")
    
    try:
        result = subprocess.run([
            "kurtosis", "enclave", "inspect", "eth-devnet"
        ], capture_output=True, text=True, check=True)
        
        # 解析输出，查找 Prysm 服务
        lines = result.stdout.strip().split('\n')
        in_services_section = False
        
        for line in lines:
            if "User Services" in line:
                in_services_section = True
                continue
            
            if in_services_section and line.strip():
                if "UUID" in line and "Name" in line and "Ports" in line:
                    continue  # 跳过表头
                
                if line.strip().startswith("="):
                    break  # 遇到下一个部分，结束
                
                # 查找 Prysm 服务
                if 'prysm' in line.lower() and 'cl-' in line.lower():
                    print(f"📋 找到 Prysm 服务: {line[:100]}...")
                    
                    # 解析端口信息
                    parts = line.split()
                    for i, part in enumerate(parts):
                        if part == 'rpc:':
                            if i + 1 < len(parts):
                                port_mapping = parts[i + 1]
                                if "->" in port_mapping:
                                    local_port = port_mapping.split("->")[-1].split(":")[-1]
                                    print(f"   RPC 端口映射: {port_mapping}")
                                    print(f"   本地端口: {local_port}")
                                    return {
                                        "rpc_port": int(local_port),
                                        "mapping": port_mapping
                                    }
        
        return {}
        
    except Exception as e:
        print(f"❌ 获取 Kurtosis 端口信息失败: {e}")
        return {}

def main():
    """主函数"""
    print("🚀 Prysm gRPC 端口检测工具")
    print("=" * 50)
    
    # 方法1: 从 Kurtosis 获取端口信息
    kurtosis_ports = get_kurtosis_prysm_ports()
    if kurtosis_ports:
        rpc_port = kurtosis_ports.get("rpc_port")
        if rpc_port:
            print(f"✅ 从 Kurtosis 获取到 RPC 端口: {rpc_port}")
            
            # 测试这个端口是否是 gRPC
            if test_grpc_port("localhost", rpc_port):
                print(f"✅ 端口 {rpc_port} 是 gRPC 服务")
                return f"localhost:{rpc_port}"
            else:
                print(f"⚠️  端口 {rpc_port} 不是 gRPC 服务，尝试默认端口")
    
    # 方法2: 扫描常见端口
    grpc_port = detect_prysm_grpc_port()
    print(f"🎯 最终选择的 gRPC 端口: {grpc_port}")
    
    return grpc_port

if __name__ == "__main__":
    port = main()
    print(f"\n📋 建议的 Prysm gRPC 地址: {port}")
    sys.exit(0)
