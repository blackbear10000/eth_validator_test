#!/usr/bin/env python3
"""
修复数据库版本脚本
专门解决 Web3Signer 数据库版本不匹配问题
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

def fix_database_version():
    """修复数据库版本"""
    print("🔧 数据库版本修复工具")
    print("=" * 40)
    
    # 1. 检查当前数据库版本
    print("🔍 检查当前数据库版本...")
    check_version_cmd = """docker exec postgres psql -U postgres -d web3signer -c "SELECT * FROM database_version;" """
    run_command(check_version_cmd, "检查数据库版本")
    
    # 2. 修复数据库版本
    print("🔄 修复数据库版本...")
    fix_version_cmd = """
    docker exec postgres psql -U postgres -d web3signer << 'EOF'
    -- 删除现有版本记录
    DELETE FROM database_version;
    
    -- 插入正确的版本号
    INSERT INTO database_version (id, version) VALUES (1, 12);
    
    -- 验证版本
    SELECT * FROM database_version;
    EOF
    """
    
    if not run_command(fix_version_cmd, "修复数据库版本"):
        print("❌ 数据库版本修复失败")
        return False
    
    # 3. 验证版本修复
    print("🔍 验证版本修复...")
    verify_version_cmd = """docker exec postgres psql -U postgres -d web3signer -c "SELECT version FROM database_version WHERE id = 1;" """
    if not run_command(verify_version_cmd, "验证数据库版本"):
        print("❌ 数据库版本验证失败")
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
    
    print("🎉 数据库版本修复完成！")
    return True

if __name__ == "__main__":
    success = fix_database_version()
    sys.exit(0 if success else 1)
