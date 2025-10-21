#!/usr/bin/env python3
"""
创建数据库表脚本
专门解决 database_version 表不存在的问题
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

def create_database_tables():
    """创建数据库表"""
    print("🔧 创建数据库表工具")
    print("=" * 40)
    
    # 1. 检查 PostgreSQL 容器
    if not run_command("docker ps | grep postgres", "检查 PostgreSQL 容器"):
        print("❌ PostgreSQL 容器未运行")
        return False
    
    # 2. 创建数据库表
    print("📋 创建数据库表...")
    create_tables_cmd = """
    docker exec postgres psql -U postgres -d web3signer << 'EOF'
    -- 创建 database_version 表
    CREATE TABLE IF NOT EXISTS database_version (
        id INTEGER PRIMARY KEY,
        version INTEGER NOT NULL
    );
    
    -- 创建 slashing_protection 表
    CREATE TABLE IF NOT EXISTS slashing_protection (
        id SERIAL PRIMARY KEY,
        validator_id INTEGER NOT NULL,
        slot BIGINT NOT NULL,
        signing_root VARCHAR(66) NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(validator_id, slot, signing_root)
    );
    
    -- 创建 low_watermark 表
    CREATE TABLE IF NOT EXISTS low_watermark (
        id SERIAL PRIMARY KEY,
        validator_id INTEGER NOT NULL,
        slot BIGINT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(validator_id)
    );
    
    -- 创建索引
    CREATE INDEX IF NOT EXISTS idx_slashing_protection_validator_id ON slashing_protection(validator_id);
    CREATE INDEX IF NOT EXISTS idx_slashing_protection_slot ON slashing_protection(slot);
    CREATE INDEX IF NOT EXISTS idx_low_watermark_validator_id ON low_watermark(validator_id);
    
    -- 插入版本数据
    INSERT INTO database_version (id, version) VALUES (1, 12) ON CONFLICT (id) DO NOTHING;
    
    -- 验证表创建
    \\dt
    SELECT * FROM database_version;
    EOF
    """
    
    if not run_command(create_tables_cmd, "创建数据库表"):
        print("❌ 数据库表创建失败")
        return False
    
    # 3. 验证表创建
    print("🔍 验证表创建...")
    verify_cmd = """docker exec postgres psql -U postgres -d web3signer -c "SELECT version FROM database_version WHERE id = 1;" """
    if not run_command(verify_cmd, "验证数据库表"):
        print("❌ 数据库表验证失败")
        return False
    
    # 4. 重启 Web3Signer
    print("🔄 重启 Web3Signer...")
    if not run_command("docker restart web3signer", "重启 Web3Signer"):
        print("❌ Web3Signer 重启失败")
        return False
    
    # 5. 等待 Web3Signer 启动
    print("⏳ 等待 Web3Signer 启动...")
    time.sleep(20)
    
    # 6. 检查 Web3Signer 状态
    print("🔍 检查 Web3Signer 状态...")
    for attempt in range(5):
        if run_command("curl -f http://localhost:9000/upcheck", f"检查 Web3Signer (尝试 {attempt + 1})"):
            print("✅ Web3Signer 启动成功")
            break
        else:
            print(f"⏳ 等待 5 秒后重试...")
            time.sleep(5)
    else:
        print("❌ Web3Signer 启动失败")
        run_command("docker logs web3signer --tail 10", "Web3Signer 日志")
        return False
    
    print("🎉 数据库表创建完成！")
    return True

if __name__ == "__main__":
    success = create_database_tables()
    sys.exit(0 if success else 1)
