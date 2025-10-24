#!/usr/bin/env python3
"""
调试 Prysm 端口解析
检查多行端口解析是否正常工作
"""

import sys
import os
import json
from pathlib import Path

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(project_root)

def debug_prysm_parsing():
    """调试 Prysm 端口解析"""
    print("🔍 调试 Prysm 端口解析")
    print("=" * 50)
    
    # 模拟 Kurtosis 输出
    mock_kurtosis_output = """
========================================== User Services ==========================================
UUID           Name                                             Ports                                          Status
354e03f6ff87   cl-1-prysm-geth                                  http: 3500/tcp -> http://127.0.0.1:33522       RUNNING
                                                                  metrics: 8080/tcp -> http://127.0.0.1:33525
                                                                  profiling: 6060/tcp -> 127.0.0.1:33524
                                                                  quic-discovery: 13000/udp -> 127.0.0.1:32953
                                                                  rpc: 4000/tcp -> 127.0.0.1:33523
                                                                  tcp-discovery: 13000/tcp -> 127.0.0.1:33526
                                                                  udp-discovery: 12000/udp -> 127.0.0.1:32952
e274d5988aca   cl-2-lighthouse-reth                             http: 4000/tcp -> http://127.0.0.1:33527       RUNNING
                                                                  metrics: 5054/tcp -> http://127.0.0.1:33528
                                                                  quic-discovery: 9001/udp -> 127.0.0.1:32955
                                                                  tcp-discovery: 9000/tcp -> 127.0.0.1:33529
                                                                  udp-discovery: 9000/udp -> 127.0.0.1:32954
"""
    
    try:
        from scripts.detect_kurtosis_ports import KurtosisPortDetector
        
        # 创建检测器
        detector = KurtosisPortDetector()
        
        # 解析输出
        print("🔍 解析模拟的 Kurtosis 输出...")
        parsed_services = detector._parse_table_output(mock_kurtosis_output)
        
        print(f"\n📋 解析到的服务:")
        for service_name, service_info in parsed_services.get('services', {}).items():
            print(f"   {service_name}:")
            ports = service_info.get('ports', {})
            for port_name, port_info in ports.items():
                print(f"     {port_name}: {port_info.get('number')}")
        
        # 检查 Prysm 服务
        prysm_service = parsed_services.get('services', {}).get('cl-1-prysm-geth')
        if prysm_service:
            print(f"\n🔍 Prysm 服务详情:")
            print(f"   名称: {prysm_service.get('name')}")
            print(f"   端口: {list(prysm_service.get('ports', {}).keys())}")
            
            # 检查是否有 rpc 端口
            ports = prysm_service.get('ports', {})
            if 'rpc' in ports:
                rpc_port = ports['rpc'].get('number')
                print(f"   ✅ 找到 rpc 端口: {rpc_port}")
            else:
                print(f"   ❌ 未找到 rpc 端口")
                print(f"   可用端口: {list(ports.keys())}")
        else:
            print(f"❌ 未找到 Prysm 服务")
        
        # 测试端口检测
        print(f"\n🔍 测试端口检测...")
        beacon_ports = detector.detect_beacon_ports()
        print(f"📊 检测结果: {beacon_ports}")
        
        return 'prysm' in beacon_ports
        
    except Exception as e:
        print(f"❌ 调试失败: {e}")
        import traceback
        print(traceback.format_exc())
        return False

def main():
    """主函数"""
    print("🚀 Prysm 端口解析调试工具")
    print("=" * 50)
    
    success = debug_prysm_parsing()
    
    if success:
        print("\n✅ 端口解析正常")
    else:
        print("\n❌ 端口解析有问题")
        print("💡 检查多行端口解析逻辑")

if __name__ == "__main__":
    main()
