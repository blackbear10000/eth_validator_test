#!/usr/bin/env python3
"""
数据库完全重置脚本
彻底重置 PostgreSQL 和 Web3Signer
"""

import subprocess
import time
import sys

def run_command(cmd, description):
    """运行命令并显示结果"""
    print(f"🔧 {description}...")
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=60)
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

def reset_database():
    """完全重置数据库"""
    print("🔄 数据库完全重置工具")
    print("=" * 40)
    
    # 1. 停止所有服务
    print("🛑 停止所有服务...")
    run_command("docker-compose -f ../infra/docker-compose.yml down", "停止 Docker 服务")
    
    # 2. 强制停止并删除容器
    print("🛑 强制停止容器...")
    run_command("docker stop postgres web3signer vault consul 2>/dev/null || true", "停止相关容器")
    run_command("docker rm postgres web3signer vault consul 2>/dev/null || true", "删除相关容器")
    
    # 3. 删除数据库卷
    print("🗑️  删除数据库卷...")
    # 先检查实际的卷名称
    run_command("docker volume ls | grep postgres", "检查 PostgreSQL 卷")
    run_command("docker volume rm postgres_data", "删除 PostgreSQL 数据卷")
    
    # 4. 重新启动服务
    print("🚀 重新启动服务...")
    if not run_command("docker-compose -f ../infra/docker-compose.yml up -d", "启动 Docker 服务"):
        print("❌ 服务启动失败")
        return False
    
    # 4. 等待服务启动
    print("⏳ 等待服务启动...")
    time.sleep(30)
    
    # 5. 检查 PostgreSQL 状态
    print("🔍 检查 PostgreSQL 状态...")
    for attempt in range(10):
        if run_command("docker exec postgres pg_isready -U postgres", f"检查 PostgreSQL (尝试 {attempt + 1})"):
            break
        else:
            print(f"⏳ 等待 3 秒后重试...")
            time.sleep(3)
    else:
        print("❌ PostgreSQL 启动失败")
        return False
    
    # 6. 创建数据库
    print("📋 创建 web3signer 数据库...")
    if not run_command("docker exec postgres psql -U postgres -c 'CREATE DATABASE web3signer;'", "创建数据库"):
        print("⚠️  数据库可能已存在，继续...")
    
    # 7. 创建数据库表
    print("📋 创建数据库表...")
    create_tables_cmd = """
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
    
    if not run_command(create_tables_cmd, "创建数据库表"):
        print("❌ 数据库表创建失败")
        return False
    
    # 8. 验证数据库
    print("🔍 验证数据库...")
    if not run_command("docker exec postgres psql -U postgres -d web3signer -c 'SELECT version FROM database_version;'", "验证数据库"):
        print("❌ 数据库验证失败")
        return False
    
    # 9. 重启 Web3Signer
    print("🔄 重启 Web3Signer...")
    if not run_command("docker restart web3signer", "重启 Web3Signer"):
        print("❌ Web3Signer 重启失败")
        return False
    
    # 10. 等待 Web3Signer 启动
    print("⏳ 等待 Web3Signer 启动...")
    time.sleep(30)
    
    # 11. 检查 Web3Signer 状态
    print("🔍 检查 Web3Signer 状态...")
    for attempt in range(10):
        if run_command("curl -f http://localhost:9000/upcheck", f"检查 Web3Signer (尝试 {attempt + 1})"):
            print("✅ Web3Signer 启动成功")
            break
        else:
            print(f"⏳ 等待 5 秒后重试...")
            time.sleep(5)
    else:
        print("❌ Web3Signer 启动失败")
        run_command("docker logs web3signer --tail 20", "Web3Signer 日志")
        return False
    
    print("🎉 数据库重置完成！")
    return True

if __name__ == "__main__":
    success = reset_database()
    sys.exit(0 if success else 1)
