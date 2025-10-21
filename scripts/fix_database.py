#!/usr/bin/env python3
"""
数据库修复脚本
解决 Web3Signer PostgreSQL 连接问题
"""

import subprocess
import time
import sys

def run_command(cmd, description):
    """运行命令并显示结果"""
    print(f"🔧 {description}...")
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=30)
        if result.returncode == 0:
            print(f"✅ {description} 成功")
            if result.stdout:
                print(f"   输出: {result.stdout.strip()}")
        else:
            print(f"❌ {description} 失败")
            print(f"   错误: {result.stderr.strip()}")
            return False
        return True
    except subprocess.TimeoutExpired:
        print(f"⏰ {description} 超时")
        return False
    except Exception as e:
        print(f"❌ {description} 出错: {e}")
        return False

def fix_database():
    """修复数据库问题"""
    print("🔧 数据库修复工具")
    print("=" * 40)
    
    # 1. 检查 PostgreSQL 容器状态
    if not run_command("docker ps | grep postgres", "检查 PostgreSQL 容器"):
        print("❌ PostgreSQL 容器未运行")
        return False
    
    # 2. 等待 PostgreSQL 完全启动
    print("⏳ 等待 PostgreSQL 启动...")
    time.sleep(10)
    
    # 3. 检查数据库是否存在
    check_db_cmd = """docker exec postgres psql -U postgres -c "SELECT 1 FROM pg_database WHERE datname='web3signer';" """
    if not run_command(check_db_cmd, "检查 web3signer 数据库"):
        print("❌ 无法连接到 PostgreSQL")
        return False
    
    # 4. 创建数据库（如果不存在）
    create_db_cmd = """docker exec postgres psql -U postgres -c "CREATE DATABASE web3signer;" """
    run_command(create_db_cmd, "创建 web3signer 数据库")
    
    # 5. 运行数据库初始化脚本
    init_cmd = """docker exec -i postgres psql -U postgres -d web3signer < /docker-entrypoint-initdb.d/init-db.sh"""
    if not run_command(init_cmd, "运行数据库初始化脚本"):
        # 如果脚本执行失败，手动创建表
        print("🔄 尝试手动创建数据库表...")
        manual_init_cmd = """
        docker exec postgres psql -U postgres -d web3signer << 'EOF'
        CREATE TABLE IF NOT EXISTS database_version (
            id INTEGER PRIMARY KEY,
            version INTEGER NOT NULL
        );
        INSERT INTO database_version (id, version) VALUES (1, 12) ON CONFLICT (id) DO NOTHING;
        CREATE TABLE IF NOT EXISTS slashing_protection (
            id SERIAL PRIMARY KEY,
            validator_id INTEGER NOT NULL,
            slot BIGINT NOT NULL,
            signing_root VARCHAR(66) NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(validator_id, slot, signing_root)
        );
        CREATE INDEX IF NOT EXISTS idx_slashing_protection_validator_id ON slashing_protection(validator_id);
        CREATE INDEX IF NOT EXISTS idx_slashing_protection_slot ON slashing_protection(slot);
        CREATE TABLE IF NOT EXISTS low_watermark (
            id SERIAL PRIMARY KEY,
            validator_id INTEGER NOT NULL,
            slot BIGINT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(validator_id)
        );
        CREATE INDEX IF NOT EXISTS idx_low_watermark_validator_id ON low_watermark(validator_id);
        EOF
        """
        if not run_command(manual_init_cmd, "手动创建数据库表"):
            print("❌ 数据库初始化失败")
            return False
    
    # 6. 验证数据库表
    verify_cmd = """docker exec postgres psql -U postgres -d web3signer -c "\\dt" """
    if not run_command(verify_cmd, "验证数据库表"):
        print("❌ 数据库表验证失败")
        return False
    
    # 7. 重启 Web3Signer
    print("🔄 重启 Web3Signer...")
    if not run_command("docker restart web3signer", "重启 Web3Signer"):
        print("❌ Web3Signer 重启失败")
        return False
    
    # 8. 等待 Web3Signer 启动
    print("⏳ 等待 Web3Signer 启动...")
    time.sleep(15)
    
    # 9. 检查 Web3Signer 状态
    if not run_command("curl -f http://localhost:9000/upcheck", "检查 Web3Signer 健康状态"):
        print("❌ Web3Signer 启动失败")
        return False
    
    print("🎉 数据库修复完成！")
    return True

if __name__ == "__main__":
    success = fix_database()
    sys.exit(0 if success else 1)
