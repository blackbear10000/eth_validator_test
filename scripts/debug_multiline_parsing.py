#!/usr/bin/env python3
"""
调试多行端口解析
检查多行端口解析的详细过程
"""

import sys
import os
import re

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(project_root)

def debug_multiline_parsing():
    """调试多行端口解析"""
    print("🔍 调试多行端口解析")
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
    
    print("🔍 模拟 Kurtosis 输出:")
    print(mock_kurtosis_output)
    print("\n" + "="*50)
    
    # 手动解析每一行
    lines = mock_kurtosis_output.strip().split('\n')
    in_services_section = False
    current_service = None
    
    for i, line in enumerate(lines):
        print(f"\n行 {i+1}: {repr(line)}")
        
        if "User Services" in line:
            in_services_section = True
            print("   → 进入服务部分")
            continue
        
        if in_services_section and line.strip():
            if "UUID" in line and "Name" in line and "Ports" in line:
                print("   → 跳过表头")
                continue
            
            if line.strip().startswith("="):
                print("   → 遇到分隔符，结束")
                break
            
            # 检查是否是新的服务行
            if re.match(r'^[a-f0-9]{12}\s+', line):
                print("   → 新服务行")
                current_service = "cl-1-prysm-geth"  # 简化处理
                print(f"   → 当前服务: {current_service}")
            elif current_service and (line.strip().startswith(' ') or 
                                     line.strip().startswith('rpc:') or 
                                     line.strip().startswith('metrics:') or 
                                     line.strip().startswith('profiling:') or
                                     line.strip().startswith('quic-discovery:') or
                                     line.strip().startswith('tcp-discovery:') or
                                     line.strip().startswith('udp-discovery:')):
                print("   → 额外端口行")
                print(f"   → 内容: {line.strip()}")
                
                # 检查是否包含 rpc 端口
                if 'rpc:' in line:
                    print("   → ✅ 找到 rpc 端口行")
                else:
                    print("   → ⚠️  非 rpc 端口行")
            else:
                print("   → 其他行")

def main():
    """主函数"""
    print("🚀 多行端口解析调试工具")
    print("=" * 50)
    
    debug_multiline_parsing()

if __name__ == "__main__":
    main()
