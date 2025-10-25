#!/usr/bin/env python3
"""
Web3Signer Database Schema Validation Script
验证数据库架构是否正确初始化
"""

import psycopg2
import sys
import json
from typing import Dict, List, Any

def connect_to_database():
    """连接到 PostgreSQL 数据库"""
    try:
        conn = psycopg2.connect(
            host="localhost",
            port="5432",
            database="web3signer",
            user="postgres",
            password="password"
        )
        return conn
    except Exception as e:
        print(f"❌ 无法连接到数据库: {e}")
        return None

def check_database_version(conn):
    """检查数据库版本"""
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM database_version;")
        result = cursor.fetchone()
        cursor.close()
        
        if result:
            version = result[1]
            print(f"✅ 数据库版本: {version}")
            if version == 12:
                print("✅ 数据库版本正确 (应该是 12)")
                return True
            else:
                print(f"❌ 数据库版本不正确 (期望: 12, 实际: {version})")
                return False
        else:
            print("❌ 无法获取数据库版本")
            return False
    except Exception as e:
        print(f"❌ 检查数据库版本时出错: {e}")
        return False

def check_tables(conn):
    """检查所有必要的表是否存在"""
    expected_tables = [
        'validators',
        'signed_blocks', 
        'signed_attestations',
        'low_watermarks',
        'metadata',
        'database_version'
    ]
    
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
            ORDER BY table_name;
        """)
        tables = [row[0] for row in cursor.fetchall()]
        cursor.close()
        
        print(f"📋 发现的表: {tables}")
        
        missing_tables = []
        for table in expected_tables:
            if table not in tables:
                missing_tables.append(table)
        
        if missing_tables:
            print(f"❌ 缺少表: {missing_tables}")
            return False
        else:
            print("✅ 所有必要的表都存在")
            return True
            
    except Exception as e:
        print(f"❌ 检查表时出错: {e}")
        return False

def check_indexes(conn):
    """检查索引是否存在"""
    expected_indexes = [
        'signed_blocks_validator_id_slot_idx',
        'signed_attestations_validator_id_target_epoch_idx',
        'signed_blocks_slot_idx',
        'signed_attestations_source_epoch_idx',
        'signed_attestations_target_epoch_idx'
    ]
    
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT indexname 
            FROM pg_indexes 
            WHERE schemaname = 'public' 
            ORDER BY indexname;
        """)
        indexes = [row[0] for row in cursor.fetchall()]
        cursor.close()
        
        print(f"📋 发现的索引: {indexes}")
        
        missing_indexes = []
        for index in expected_indexes:
            if index not in indexes:
                missing_indexes.append(index)
        
        if missing_indexes:
            print(f"❌ 缺少索引: {missing_indexes}")
            return False
        else:
            print("✅ 所有必要的索引都存在")
            return True
            
    except Exception as e:
        print(f"❌ 检查索引时出错: {e}")
        return False

def check_functions(conn):
    """检查函数是否存在"""
    expected_functions = [
        'upsert_validators',
        'xnor_source_target_low_watermark',
        'check_high_watermarks',
        'check_low_watermarks'
    ]
    
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT routine_name 
            FROM information_schema.routines 
            WHERE routine_schema = 'public' 
            AND routine_type = 'FUNCTION'
            ORDER BY routine_name;
        """)
        functions = [row[0] for row in cursor.fetchall()]
        cursor.close()
        
        print(f"📋 发现的函数: {functions}")
        
        missing_functions = []
        for func in expected_functions:
            if func not in functions:
                missing_functions.append(func)
        
        if missing_functions:
            print(f"❌ 缺少函数: {missing_functions}")
            return False
        else:
            print("✅ 所有必要的函数都存在")
            return True
            
    except Exception as e:
        print(f"❌ 检查函数时出错: {e}")
        return False

def check_triggers(conn):
    """检查触发器是否存在"""
    expected_triggers = [
        'xnor_source_target_low_watermark_trigger',
        'check_before_insert_or_update_high_watermarks',
        'check_before_insert_or_update_low_watermarks'
    ]
    
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT trigger_name 
            FROM information_schema.triggers 
            WHERE trigger_schema = 'public'
            ORDER BY trigger_name;
        """)
        triggers = [row[0] for row in cursor.fetchall()]
        cursor.close()
        
        print(f"📋 发现的触发器: {triggers}")
        
        missing_triggers = []
        for trigger in expected_triggers:
            if trigger not in triggers:
                missing_triggers.append(trigger)
        
        if missing_triggers:
            print(f"❌ 缺少触发器: {missing_triggers}")
            return False
        else:
            print("✅ 所有必要的触发器都存在")
            return True
            
    except Exception as e:
        print(f"❌ 检查触发器时出错: {e}")
        return False

def main():
    """主函数"""
    print("🔍 开始验证 Web3Signer 数据库架构...")
    print("=" * 50)
    
    # 连接数据库
    conn = connect_to_database()
    if not conn:
        sys.exit(1)
    
    try:
        # 执行所有检查
        checks = [
            ("数据库版本", check_database_version),
            ("表结构", check_tables),
            ("索引", check_indexes),
            ("函数", check_functions),
            ("触发器", check_triggers)
        ]
        
        results = []
        for name, check_func in checks:
            print(f"\n🔍 检查 {name}...")
            result = check_func(conn)
            results.append((name, result))
        
        # 总结结果
        print("\n" + "=" * 50)
        print("📊 检查结果总结:")
        
        all_passed = True
        for name, result in results:
            status = "✅ 通过" if result else "❌ 失败"
            print(f"  {name}: {status}")
            if not result:
                all_passed = False
        
        if all_passed:
            print("\n🎉 所有检查都通过了！数据库架构正确。")
            return 0
        else:
            print("\n⚠️  部分检查失败，请检查数据库初始化。")
            return 1
            
    except Exception as e:
        print(f"❌ 验证过程中出错: {e}")
        return 1
    finally:
        conn.close()

if __name__ == "__main__":
    sys.exit(main())
