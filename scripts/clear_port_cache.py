#!/usr/bin/env python3
"""
清除端口缓存
删除旧的端口配置文件，强制重新检测
"""

import sys
import os
from pathlib import Path

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(project_root)

def clear_port_cache():
    """清除端口缓存"""
    print("🧹 清除端口缓存...")
    
    # 删除端口配置文件
    config_file = Path(project_root) / "config" / "kurtosis_ports.json"
    if config_file.exists():
        config_file.unlink()
        print(f"✅ 已删除: {config_file}")
    else:
        print(f"📋 配置文件不存在: {config_file}")
    
    # 删除 Prysm 配置目录
    prysm_config_dir = Path(project_root) / "configs" / "prysm"
    if prysm_config_dir.exists():
        import shutil
        shutil.rmtree(prysm_config_dir)
        print(f"✅ 已删除: {prysm_config_dir}")
    else:
        print(f"📋 配置目录不存在: {prysm_config_dir}")
    
    print("🎯 端口缓存已清除，下次启动将重新检测端口")

def main():
    """主函数"""
    print("🚀 端口缓存清理工具")
    print("=" * 40)
    
    clear_port_cache()
    
    print("\n✅ 清理完成")
    print("💡 现在可以重新运行: ./validator.sh start-validator prysm")

if __name__ == "__main__":
    main()
