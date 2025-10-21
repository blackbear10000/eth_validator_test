#!/usr/bin/env python3
"""
清理 Web3Signer keys 目录
"""

import os
import shutil
from pathlib import Path

def clean_web3signer_keys():
    """清理 Web3Signer keys 目录"""
    print("🧹 清理 Web3Signer keys 目录...")
    
    keys_dir = Path("infra/web3signer/keys")
    
    if not keys_dir.exists():
        print("❌ keys 目录不存在")
        return False
    
    # 备份现有文件
    backup_dir = keys_dir / "backup"
    backup_dir.mkdir(exist_ok=True)
    
    # 移动所有文件到备份目录
    for file in keys_dir.iterdir():
        if file.is_file() and file.name != "backup":
            shutil.move(str(file), str(backup_dir / file.name))
            print(f"📦 备份文件: {file.name}")
    
    print(f"✅ 已清理 {keys_dir} 目录")
    print(f"📦 备份文件保存在: {backup_dir}")
    return True

if __name__ == "__main__":
    clean_web3signer_keys()
