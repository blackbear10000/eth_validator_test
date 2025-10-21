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
    
    # 创建备份目录（在 keys 目录外）
    backup_dir = Path("infra/web3signer/keys_backup")
    backup_dir.mkdir(exist_ok=True)
    
    # 移动所有文件到备份目录
    moved_count = 0
    for file in keys_dir.iterdir():
        if file.is_file():
            shutil.move(str(file), str(backup_dir / file.name))
            print(f"📦 备份文件: {file.name}")
            moved_count += 1
    
    print(f"✅ 已清理 {keys_dir} 目录")
    print(f"📦 备份了 {moved_count} 个文件到: {backup_dir}")
    return True

if __name__ == "__main__":
    clean_web3signer_keys()
