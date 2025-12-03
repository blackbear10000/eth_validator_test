#!/usr/bin/env python3
"""
Word Lists 诊断脚本
用于检查 ethstaker-deposit-cli 包中的 word_lists 文件是否可用
"""
import os
import sys
import tempfile
import shutil

print("=" * 80)
print("Word Lists 诊断脚本")
print("=" * 80)
print()

# 1. 检查包是否已安装
print("1. 检查 ethstaker-deposit-cli 包安装状态")
print("-" * 80)
try:
    import ethstaker_deposit
    print(f"✅ 包已导入: {ethstaker_deposit}")
    print(f"   包路径: {ethstaker_deposit.__file__}")
    print(f"   包目录: {os.path.dirname(ethstaker_deposit.__file__)}")
except ImportError as e:
    print(f"❌ 包导入失败: {e}")
    sys.exit(1)
print()

# 2. 检查 WORD_LISTS_PATH 常量
print("2. 检查 WORD_LISTS_PATH 常量")
print("-" * 80)
try:
    from ethstaker_deposit.utils.constants import WORD_LISTS_PATH
    print(f"✅ WORD_LISTS_PATH = {WORD_LISTS_PATH}")
    print(f"   类型: {type(WORD_LISTS_PATH)}")
    
    # 尝试构建完整路径
    package_dir = os.path.dirname(ethstaker_deposit.__file__)
    full_path = os.path.join(package_dir, WORD_LISTS_PATH)
    print(f"   完整路径: {full_path}")
    print(f"   路径存在: {os.path.exists(full_path)}")
    
    if os.path.exists(full_path):
        english_file = os.path.join(full_path, 'english.txt')
        print(f"   english.txt 存在: {os.path.exists(english_file)}")
        if os.path.exists(english_file):
            with open(english_file, 'r') as f:
                lines = f.readlines()
                print(f"   文件行数: {len(lines)}")
                print(f"   前5行: {lines[:5]}")
except Exception as e:
    print(f"❌ 检查失败: {e}")
print()

# 3. 检查包的 __file__ 路径
print("3. 检查包的 __file__ 路径")
print("-" * 80)
try:
    package_path = os.path.dirname(ethstaker_deposit.__file__)
    word_lists_path = os.path.join(
        package_path, 
        'key_handling', 
        'key_derivation', 
        'word_lists'
    )
    print(f"   构建路径: {word_lists_path}")
    print(f"   路径存在: {os.path.exists(word_lists_path)}")
    
    if os.path.exists(word_lists_path):
        english_file = os.path.join(word_lists_path, 'english.txt')
        print(f"   english.txt 存在: {os.path.exists(english_file)}")
        if os.path.exists(english_file):
            with open(english_file, 'r') as f:
                lines = f.readlines()
                print(f"   文件行数: {len(lines)}")
except Exception as e:
    print(f"❌ 检查失败: {e}")
print()

# 4. 检查 importlib.resources
print("4. 检查 importlib.resources")
print("-" * 80)
try:
    import importlib.resources
    
    # Python 3.9+ 方法
    if hasattr(importlib.resources, 'files'):
        print("   ✅ 支持 files() API (Python 3.9+)")
        try:
            word_lists_ref = importlib.resources.files('ethstaker_deposit').joinpath(
                'key_handling', 'key_derivation', 'word_lists'
            )
            print(f"   资源引用: {word_lists_ref}")
            
            # 尝试读取文件
            try:
                english_file_ref = word_lists_ref.joinpath('english.txt')
                print(f"   english.txt 引用: {english_file_ref}")
                
                # 尝试读取内容
                try:
                    content = english_file_ref.read_text(encoding='utf-8')
                    lines = content.split('\n')
                    print(f"   ✅ 成功读取文件内容")
                    print(f"   行数: {len([l for l in lines if l.strip()])}")
                    print(f"   前5行: {lines[:5]}")
                    
                    # 测试创建临时文件
                    temp_dir = tempfile.mkdtemp(prefix='test_word_lists_')
                    temp_word_lists_dir = os.path.join(temp_dir, 'word_lists')
                    os.makedirs(temp_word_lists_dir, exist_ok=True)
                    
                    temp_english_file = os.path.join(temp_word_lists_dir, 'english.txt')
                    with open(temp_english_file, 'w', encoding='utf-8') as f:
                        f.write(content)
                    
                    print(f"   ✅ 成功创建临时文件: {temp_english_file}")
                    print(f"   临时文件存在: {os.path.exists(temp_english_file)}")
                    
                    # 清理
                    shutil.rmtree(temp_dir)
                    print(f"   ✅ 临时目录已清理")
                    
                except Exception as e:
                    print(f"   ❌ 读取文件内容失败: {e}")
            except Exception as e:
                print(f"   ❌ 获取 english.txt 引用失败: {e}")
        except Exception as e:
            print(f"   ❌ files() API 失败: {e}")
    else:
        print("   ⚠️  不支持 files() API，尝试 path() API")
        try:
            word_lists_ref = importlib.resources.path(
                'ethstaker_deposit.key_handling.key_derivation.word_lists', 
                'english.txt'
            )
            with word_lists_ref as path:
                print(f"   ✅ path() API 成功")
                print(f"   路径: {path}")
                print(f"   路径存在: {os.path.exists(path)}")
        except Exception as e:
            print(f"   ❌ path() API 失败: {e}")
            
except Exception as e:
    print(f"❌ importlib.resources 检查失败: {e}")
print()

# 5. 列出包目录结构
print("5. 列出包目录结构")
print("-" * 80)
try:
    package_path = os.path.dirname(ethstaker_deposit.__file__)
    print(f"   包根目录: {package_path}")
    
    # 列出直接子目录
    if os.path.exists(package_path):
        subdirs = [d for d in os.listdir(package_path) if os.path.isdir(os.path.join(package_path, d))]
        print(f"   子目录: {subdirs}")
        
        # 检查 key_handling 目录
        key_handling_path = os.path.join(package_path, 'key_handling')
        if os.path.exists(key_handling_path):
            print(f"   ✅ key_handling 目录存在")
            subdirs2 = [d for d in os.listdir(key_handling_path) if os.path.isdir(os.path.join(key_handling_path, d))]
            print(f"   key_handling 子目录: {subdirs2}")
            
            key_derivation_path = os.path.join(key_handling_path, 'key_derivation')
            if os.path.exists(key_derivation_path):
                print(f"   ✅ key_derivation 目录存在")
                subdirs3 = [d for d in os.listdir(key_derivation_path) if os.path.isdir(os.path.join(key_derivation_path, d))]
                print(f"   key_derivation 子目录: {subdirs3}")
                
                word_lists_path = os.path.join(key_derivation_path, 'word_lists')
                if os.path.exists(word_lists_path):
                    print(f"   ✅ word_lists 目录存在")
                    files = os.listdir(word_lists_path)
                    print(f"   word_lists 文件: {files}")
                else:
                    print(f"   ❌ word_lists 目录不存在")
        else:
            print(f"   ❌ key_handling 目录不存在")
except Exception as e:
    print(f"❌ 列出目录结构失败: {e}")
print()

# 6. 测试 get_mnemonic 函数
print("6. 测试 get_mnemonic 函数")
print("-" * 80)
try:
    from ethstaker_deposit.key_handling.key_derivation.mnemonic import get_mnemonic
    print("   ✅ get_mnemonic 函数已导入")
    
    # 尝试找到可用的路径
    words_path = None
    
    # 方法1: 使用包的 __file__ 路径
    package_path = os.path.dirname(ethstaker_deposit.__file__)
    test_path = os.path.join(package_path, 'key_handling', 'key_derivation', 'word_lists')
    if os.path.exists(test_path) and os.path.exists(os.path.join(test_path, 'english.txt')):
        words_path = test_path
        print(f"   ✅ 找到路径（方法1）: {words_path}")
    
    # 方法2: 使用 importlib.resources
    if not words_path:
        try:
            import importlib.resources
            if hasattr(importlib.resources, 'files'):
                word_lists_ref = importlib.resources.files('ethstaker_deposit').joinpath(
                    'key_handling', 'key_derivation', 'word_lists'
                )
                english_file_ref = word_lists_ref.joinpath('english.txt')
                content = english_file_ref.read_text(encoding='utf-8')
                
                # 创建临时目录
                temp_dir = tempfile.mkdtemp(prefix='word_lists_')
                temp_word_lists_dir = os.path.join(temp_dir, 'word_lists')
                os.makedirs(temp_word_lists_dir, exist_ok=True)
                
                temp_english_file = os.path.join(temp_word_lists_dir, 'english.txt')
                with open(temp_english_file, 'w', encoding='utf-8') as f:
                    f.write(content)
                
                words_path = temp_word_lists_dir
                print(f"   ✅ 找到路径（方法2，临时目录）: {words_path}")
        except Exception as e:
            print(f"   ⚠️  方法2失败: {e}")
    
    # 测试生成助记词
    if words_path:
        try:
            mnemonic = get_mnemonic(language='english', words_path=words_path)
            print(f"   ✅ 成功生成助记词: {mnemonic[:50]}...")
        except Exception as e:
            print(f"   ❌ 生成助记词失败: {e}")
            import traceback
            traceback.print_exc()
    else:
        print(f"   ❌ 无法找到可用的 word lists 路径")
        
except Exception as e:
    print(f"❌ 测试失败: {e}")
    import traceback
    traceback.print_exc()
print()

print("=" * 80)
print("诊断完成")
print("=" * 80)

