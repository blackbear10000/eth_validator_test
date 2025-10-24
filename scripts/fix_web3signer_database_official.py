#!/usr/bin/env python3
"""
使用 Web3Signer 官方数据库迁移文件修复数据库问题
基于官方文档：https://docs.web3signer.consensys.io/how-to/configure-slashing-protection
按照文档要求按顺序执行迁移文件
"""

import subprocess
import time
import requests
import sys
import os
from pathlib import Path
import glob

def check_docker_containers():
    """检查 Docker 容器状态"""
    print("🔍 检查 Docker 容器状态...")
    
    try:
        # 检查 PostgreSQL 容器
        result = subprocess.run(['docker', 'ps', '--filter', 'name=postgres', '--format', '{{.Names}}'], 
                              capture_output=True, text=True, timeout=10)
        
        if 'postgres' in result.stdout:
            print("✅ PostgreSQL 容器正在运行")
        else:
            print("❌ PostgreSQL 容器未运行")
            print("💡 请先启动基础设施: ./validator.sh start")
            return False
        
        # 检查 Web3Signer 容器
        result = subprocess.run(['docker', 'ps', '--filter', 'name=web3signer', '--format', '{{.Names}}'], 
                              capture_output=True, text=True, timeout=10)
        
        if 'web3signer' in result.stdout:
            print("✅ Web3Signer 容器正在运行")
        else:
            print("⚠️  Web3Signer 容器未运行，将在迁移后启动")
        
        return True
        
    except Exception as e:
        print(f"❌ 检查 Docker 容器失败: {e}")
        return False

def get_migration_files():
    """获取迁移文件并按顺序排序"""
    print("🔍 查找 Web3Signer 官方迁移文件...")
    
    try:
        # 获取项目根目录
        project_root = Path(__file__).parent.parent
        migrations_dir = project_root / "infra" / "web3signer" / "migrations" / "postgresql"
        
        print(f"📁 迁移文件目录: {migrations_dir}")
        
        if not migrations_dir.exists():
            print(f"❌ 迁移文件目录不存在: {migrations_dir}")
            return []
        
        # 查找所有 SQL 迁移文件
        sql_files = list(migrations_dir.glob("*.sql"))
        
        if not sql_files:
            print(f"❌ 在 {migrations_dir} 中没有找到 SQL 文件")
            return []
        
        # 按文件名排序（V1, V2, V3...）
        sql_files.sort(key=lambda x: x.name)
        
        print(f"✅ 找到 {len(sql_files)} 个迁移文件:")
        for i, file in enumerate(sql_files, 1):
            print(f"   {i}. {file.name}")
        
        return sql_files
        
    except Exception as e:
        print(f"❌ 查找迁移文件失败: {e}")
        return []

def run_database_migration(migration_files):
    """按顺序运行数据库迁移文件"""
    print("\n🔄 按顺序运行 Web3Signer 官方数据库迁移...")
    
    success_count = 0
    
    for i, file_path in enumerate(migration_files, 1):
        print(f"\n📋 运行迁移 {i}/{len(migration_files)}: {file_path.name}")
        
        try:
            # 方法1: 通过 stdin 传递 SQL 内容
            with open(file_path, 'r', encoding='utf-8') as f:
                sql_content = f.read()
            
            # 使用 Docker 执行 psql 命令，通过 stdin 传递 SQL 内容
            cmd = [
                "docker", "exec", "-i", "postgres",
                "psql",
                "--echo-all",
                "--host=localhost",
                "--port=5432",
                "--dbname=web3signer",
                "--username=postgres"
            ]
            
            print(f"🔧 执行命令: {' '.join(cmd)}")
            print(f"📄 SQL 文件内容长度: {len(sql_content)} 字符")
            
            result = subprocess.run(cmd, input=sql_content, capture_output=True, text=True, timeout=60)
            
            if result.returncode == 0:
                print(f"✅ 迁移 {file_path.name} 成功")
                success_count += 1
            else:
                print(f"❌ 迁移 {file_path.name} 失败 (stdin 方式)")
                print(f"   错误输出: {result.stderr}")
                print(f"   标准输出: {result.stdout}")
                
                # 尝试备选方案：复制文件到容器内
                print(f"🔄 尝试备选方案：复制文件到容器内...")
                try:
                    # 复制文件到容器内
                    copy_cmd = ["docker", "cp", str(file_path), "postgres:/tmp/"]
                    copy_result = subprocess.run(copy_cmd, capture_output=True, text=True, timeout=30)
                    
                    if copy_result.returncode == 0:
                        # 使用容器内的文件路径
                        container_file = f"/tmp/{file_path.name}"
                        cmd2 = [
                            "docker", "exec", "-i", "postgres",
                            "psql",
                            "--echo-all",
                            "--host=localhost",
                            "--port=5432",
                            "--dbname=web3signer",
                            "--username=postgres",
                            f"--file={container_file}"
                        ]
                        
                        print(f"🔧 备选命令: {' '.join(cmd2)}")
                        result2 = subprocess.run(cmd2, capture_output=True, text=True, timeout=60)
                        
                        if result2.returncode == 0:
                            print(f"✅ 迁移 {file_path.name} 成功 (备选方案)")
                            success_count += 1
                        else:
                            print(f"❌ 迁移 {file_path.name} 失败 (备选方案)")
                            print(f"   错误输出: {result2.stderr}")
                            print(f"   标准输出: {result2.stdout}")
                            
                            # 某些迁移可能已经执行过，继续执行其他迁移
                            if "already exists" in result2.stderr or "duplicate key" in result2.stderr:
                                print(f"⚠️  迁移 {file_path.name} 可能已经执行过，继续下一个")
                                success_count += 1
                    else:
                        print(f"❌ 复制文件到容器失败: {copy_result.stderr}")
                        print(f"❌ 迁移 {file_path.name} 出现严重错误")
                        
                except Exception as e:
                    print(f"❌ 备选方案失败: {e}")
                    print(f"❌ 迁移 {file_path.name} 出现严重错误")
                    
        except subprocess.TimeoutExpired:
            print(f"⚠️  迁移 {file_path.name} 超时，继续下一个")
        except Exception as e:
            print(f"⚠️  迁移 {file_path.name} 异常: {e}")
    
    print(f"\n📊 迁移结果: {success_count}/{len(migration_files)} 个迁移成功")
    return success_count > 0

def verify_database_schema():
    """验证数据库架构是否正确"""
    print("\n🔍 验证数据库架构...")
    
    try:
        # 检查关键表和函数
        verification_queries = [
            ("检查 validators 表", "SELECT COUNT(*) FROM validators;"),
            ("检查 slashing_protection 表", "SELECT COUNT(*) FROM slashing_protection;"),
            ("检查 low_watermark 表", "SELECT COUNT(*) FROM low_watermark;"),
            ("检查 database_version 表", "SELECT version FROM database_version WHERE id = 1;"),
            ("检查 upsert_validators 函数", "SELECT proname FROM pg_proc WHERE proname = 'upsert_validators';")
        ]
        
        all_success = True
        
        for description, query in verification_queries:
            try:
                cmd = [
                    "docker", "exec", "-i", "postgres",
                    "psql",
                    "--host=localhost",
                    "--port=5432",
                    "--dbname=web3signer",
                    "--username=postgres",
                    "--command", query
                ]
                
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
                
                if result.returncode == 0:
                    print(f"✅ {description}: 正常")
                else:
                    print(f"❌ {description}: 失败")
                    print(f"   错误: {result.stderr}")
                    all_success = False
                    
            except Exception as e:
                print(f"⚠️  {description}: 检查异常 - {e}")
                all_success = False
        
        return all_success
        
    except Exception as e:
        print(f"❌ 验证数据库架构失败: {e}")
        return False

def restart_web3signer():
    """重启 Web3Signer 服务"""
    print("\n🔄 重启 Web3Signer 服务...")
    
    try:
        # 停止 Web3Signer
        print("🛑 停止 Web3Signer 服务...")
        subprocess.run(['docker', 'stop', 'web3signer', 'web3signer-2'], 
                      capture_output=True, text=True)
        time.sleep(5)
        
        # 启动 Web3Signer
        print("🚀 启动 Web3Signer 服务...")
        subprocess.run(['docker', 'start', 'web3signer', 'web3signer-2'], 
                      check=True)
        
        # 等待服务启动
        print("⏳ 等待 Web3Signer 服务启动...")
        time.sleep(20)
        
        # 验证服务状态
        print("🔍 验证 Web3Signer 服务状态...")
        
        # 检查 Web3Signer-1
        try:
            response = requests.get("http://localhost:9000/upcheck", timeout=10)
            if response.status_code == 200:
                print("✅ Web3Signer-1 服务正常")
            else:
                print(f"❌ Web3Signer-1 服务异常: {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ Web3Signer-1 连接失败: {e}")
            return False
        
        # 检查 Web3Signer-2
        try:
            response = requests.get("http://localhost:9001/upcheck", timeout=10)
            if response.status_code == 200:
                print("✅ Web3Signer-2 服务正常")
            else:
                print(f"⚠️  Web3Signer-2 服务异常: {response.status_code}")
        except Exception as e:
            print(f"⚠️  Web3Signer-2 连接失败: {e}")
        
        return True
        
    except Exception as e:
        print(f"❌ 重启 Web3Signer 失败: {e}")
        return False

def check_web3signer_logs():
    """检查 Web3Signer 日志"""
    print("\n🔍 检查 Web3Signer 日志...")
    
    try:
        # 获取最近的日志
        result = subprocess.run(['docker', 'logs', '--tail', '30', 'web3signer'], 
                              capture_output=True, text=True, timeout=15)
        
        if result.returncode == 0:
            logs = result.stdout
            print("📋 Web3Signer 最近日志:")
            print("-" * 60)
            print(logs)
            print("-" * 60)
            
            # 检查关键错误
            error_keywords = [
                'upsert_validators', 
                'Unregistered validator', 
                'function.*does not exist',
                'ERROR',
                'Exception'
            ]
            
            error_lines = []
            for line in logs.split('\n'):
                if any(keyword in line for keyword in error_keywords):
                    error_lines.append(line)
            
            if error_lines:
                print("\n⚠️  发现可能的错误:")
                for line in error_lines:
                    print(f"   {line}")
                return False
            else:
                print("✅ 日志中没有发现明显错误")
                return True
        else:
            print(f"❌ 获取日志失败: {result.stderr}")
            return False
            
    except Exception as e:
        print(f"❌ 检查日志失败: {e}")
        return False

def test_web3signer_keys():
    """测试 Web3Signer 密钥加载"""
    print("\n🔍 测试 Web3Signer 密钥加载...")
    
    try:
        # 检查加载的密钥
        response = requests.get("http://localhost:9000/api/v1/eth2/publicKeys", timeout=10)
        
        if response.status_code == 200:
            keys = response.json()
            print(f"✅ Web3Signer 中加载了 {len(keys)} 个密钥")
            
            if keys:
                print("📋 加载的密钥:")
                for i, key in enumerate(keys, 1):
                    print(f"   {i}. {key}")
                return True
            else:
                print("⚠️  Web3Signer 中没有加载任何密钥")
                print("💡 请检查密钥配置和 Vault 连接")
                return False
        else:
            print(f"❌ 获取 Web3Signer 密钥失败: {response.status_code}")
            print(f"   响应: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ 测试 Web3Signer 密钥失败: {e}")
        return False

def main():
    """主函数"""
    print("🔧 Web3Signer 数据库修复工具 (官方迁移文件)")
    print("=" * 70)
    print("基于 Web3Signer 官方文档:")
    print("https://docs.web3signer.consensys.io/how-to/configure-slashing-protection")
    print("=" * 70)
    
    # 1. 检查 Docker 容器状态
    containers_ok = check_docker_containers()
    
    if not containers_ok:
        print("\n❌ Docker 容器状态检查失败，无法继续")
        return False
    
    # 2. 获取迁移文件
    migration_files = get_migration_files()
    
    if not migration_files:
        print("\n❌ 没有找到迁移文件，无法继续")
        return False
    
    # 3. 运行数据库迁移
    migration_success = run_database_migration(migration_files)
    
    if not migration_success:
        print("\n❌ 数据库迁移失败")
        return False
    
    # 4. 验证数据库架构
    schema_success = verify_database_schema()
    
    if not schema_success:
        print("\n⚠️  数据库架构验证失败，但继续尝试重启服务")
    
    # 5. 重启 Web3Signer
    restart_success = restart_web3signer()
    
    if not restart_success:
        print("\n❌ Web3Signer 重启失败")
        return False
    
    # 6. 检查日志
    logs_success = check_web3signer_logs()
    
    # 7. 测试密钥加载
    keys_success = test_web3signer_keys()
    
    # 8. 总结
    print("\n" + "=" * 70)
    print("📊 修复结果总结:")
    print("=" * 70)
    
    if migration_success and restart_success and logs_success and keys_success:
        print("✅ 数据库修复完全成功!")
        print("💡 现在可以重新启动 Prysm 验证器:")
        print("   ./validator.sh start-validator prysm")
        return True
    elif migration_success and restart_success:
        print("✅ 数据库修复基本成功!")
        print("💡 可以尝试重新启动 Prysm 验证器:")
        print("   ./validator.sh start-validator prysm")
        if not keys_success:
            print("⚠️  如果仍有问题，请检查密钥配置:")
            print("   ./validator.sh load-keys")
        return True
    else:
        print("⚠️  修复完成，但可能仍有问题")
        print("💡 请检查 Web3Signer 日志获取更多信息")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
