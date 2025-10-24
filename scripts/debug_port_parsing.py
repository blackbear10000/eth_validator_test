#!/usr/bin/env python3
"""
调试端口解析
测试 Prysm 端口解析逻辑
"""

import sys
import os
import re

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(project_root)

def test_port_parsing():
    """测试端口解析逻辑"""
    print("🧪 测试端口解析逻辑")
    print("=" * 50)
    
    # 模拟 Prysm 的端口文本
    prysm_ports_text = "http: 3500/tcp -> http://127.0.0.1:33522 metrics: 8080/tcp -> http://127.0.0.1:33525 profiling: 6060/tcp -> 127.0.0.1:33524 quic-discovery: 13000/udp -> 127.0.0.1:32953 rpc: 4000/tcp -> 127.0.0.1:33523 tcp-discovery: 13000/tcp -> 127.0.0.1:33526 udp-discovery: 12000/udp -> 127.0.0.1:32952"
    
    print(f"🔍 测试端口文本: {prysm_ports_text}")
    print()
    
    # 使用当前的正则表达式
    port_pattern = r'(\w+):\s*(\d+)/(\w+)\s*->\s*([^\s]+)'
    port_matches = re.findall(port_pattern, prysm_ports_text)
    
    print(f"📋 正则表达式匹配结果:")
    for i, match in enumerate(port_matches):
        port_name, internal_port, protocol, external_mapping = match
        print(f"   {i+1}. {port_name}: {internal_port}/{protocol} -> {external_mapping}")
        
        # 提取本地端口
        if ":" in external_mapping:
            local_port = external_mapping.split(":")[-1]
            print(f"      本地端口: {local_port}")
            
            # 检查是否是 rpc 端口
            if port_name == 'rpc':
                print(f"      ✅ 找到 Prysm gRPC 端口: {local_port}")
            else:
                print(f"      ⚠️  非 gRPC 端口: {port_name}")
        else:
            print(f"      ❌ 无法提取端口号")
        print()
    
    # 检查是否找到了 rpc 端口
    rpc_found = False
    for port_name, internal_port, protocol, external_mapping in port_matches:
        if port_name == 'rpc':
            rpc_found = True
            local_port = external_mapping.split(":")[-1]
            print(f"✅ 成功找到 Prysm gRPC 端口: {local_port}")
            break
    
    if not rpc_found:
        print("❌ 未找到 rpc 端口")
        
        # 尝试不同的正则表达式
        print("\n🔍 尝试其他正则表达式...")
        
        # 更宽松的正则表达式
        alt_pattern = r'(\w+):\s*(\d+)/(\w+)\s*->\s*([^\s,]+)'
        alt_matches = re.findall(alt_pattern, prysm_ports_text)
        print(f"📋 宽松正则表达式匹配结果: {len(alt_matches)} 个")
        
        for match in alt_matches:
            port_name, internal_port, protocol, external_mapping = match
            if port_name == 'rpc':
                local_port = external_mapping.split(":")[-1]
                print(f"✅ 宽松正则找到 rpc 端口: {local_port}")
                break
    
    return rpc_found

def main():
    """主函数"""
    print("🚀 端口解析调试工具")
    print("=" * 50)
    
    success = test_port_parsing()
    
    if success:
        print("\n✅ 端口解析正常")
    else:
        print("\n❌ 端口解析有问题")
        print("💡 建议检查正则表达式或端口文本格式")

if __name__ == "__main__":
    main()
