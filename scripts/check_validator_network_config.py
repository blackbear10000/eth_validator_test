#!/usr/bin/env python3
"""
检查 Validator Client 的网络配置
排查签名根不匹配问题
"""
import sys
import os
import subprocess
import json
import yaml
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "system_v2" / "backend"))

def check_docker_container(container_name: str) -> dict:
    """检查 Docker 容器状态和配置"""
    print(f"\n🔍 检查容器: {container_name}")
    
    try:
        # 检查容器是否存在
        result = subprocess.run(
            ["docker", "ps", "-a", "--filter", f"name={container_name}", "--format", "{{.Names}}\t{{.Status}}"],
            capture_output=True,
            text=True,
            timeout=5
        )
        
        if result.returncode != 0 or not result.stdout.strip():
            print(f"❌ 容器不存在或未运行")
            return {"exists": False}
        
        print(f"✅ 容器存在")
        print(f"   状态: {result.stdout.strip()}")
        
        # 检查挂载点
        inspect_result = subprocess.run(
            ["docker", "inspect", container_name, "--format", "{{json .Mounts}}"],
            capture_output=True,
            text=True,
            timeout=5
        )
        
        if inspect_result.returncode == 0:
            mounts = json.loads(inspect_result.stdout)
            print(f"\n📁 挂载点:")
            for mount in mounts:
                print(f"   {mount.get('Source', 'N/A')} -> {mount.get('Destination', 'N/A')}")
                if 'network-config.yaml' in mount.get('Destination', ''):
                    print(f"   ✅ 找到 network-config.yaml 挂载")
        
        # 检查容器内的文件
        exec_result = subprocess.run(
            ["docker", "exec", container_name, "ls", "-la", "/network-config.yaml"],
            capture_output=True,
            text=True,
            timeout=5
        )
        
        if exec_result.returncode == 0:
            print(f"\n✅ 容器内文件存在: /network-config.yaml")
            print(f"   {exec_result.stdout.strip()}")
            
            # 读取文件内容（前几行）
            read_result = subprocess.run(
                ["docker", "exec", container_name, "head", "-20", "/network-config.yaml"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if read_result.returncode == 0:
                print(f"\n📄 文件内容预览:")
                print(read_result.stdout)
        else:
            print(f"\n❌ 容器内文件不存在: /network-config.yaml")
            print(f"   错误: {exec_result.stderr}")
        
        # 检查进程参数
        exec_result = subprocess.run(
            ["docker", "exec", container_name, "ps", "aux"],
            capture_output=True,
            text=True,
            timeout=5
        )
        
        if exec_result.returncode == 0:
            output = exec_result.stdout
            if '--chain-config-file' in output:
                print(f"\n✅ 启动命令包含 --chain-config-file 参数")
                # 提取包含 chain-config-file 的行
                for line in output.split('\n'):
                    if '--chain-config-file' in line:
                        print(f"   {line[:200]}...")
            else:
                print(f"\n⚠️  启动命令中未找到 --chain-config-file 参数")
        
        return {"exists": True, "running": "Up" in result.stdout}
        
    except Exception as e:
        print(f"❌ 检查失败: {e}")
        return {"error": str(e)}

def check_beacon_api_network_info():
    """从 Beacon API 获取网络信息"""
    print(f"\n🔍 从 Beacon API 获取网络信息...")
    
    try:
        import requests
        
        # 尝试多个可能的端口
        ports = [5052, 3500, 4000]
        beacon_api_url = None
        
        for port in ports:
            url = f"http://localhost:{port}/eth/v1/beacon/genesis"
            try:
                response = requests.get(url, timeout=5)
                if response.status_code == 200:
                    beacon_api_url = f"http://localhost:{port}"
                    break
            except:
                continue
        
        if not beacon_api_url:
            print("❌ 无法连接到 Beacon API")
            return None
        
        print(f"✅ 连接到 Beacon API: {beacon_api_url}")
        
        # 获取 genesis 信息
        genesis_url = f"{beacon_api_url}/eth/v1/beacon/genesis"
        response = requests.get(genesis_url, timeout=5)
        if response.status_code == 200:
            genesis_data = response.json().get('data', {})
            genesis_validators_root = genesis_data.get('genesis_validators_root')
            genesis_time = genesis_data.get('genesis_time')
            print(f"\n📊 Genesis 信息:")
            print(f"   Genesis Validators Root: {genesis_validators_root}")
            print(f"   Genesis Time: {genesis_time}")
        
        # 获取 fork 信息
        fork_url = f"{beacon_api_url}/eth/v1/beacon/states/head/fork"
        response = requests.get(fork_url, timeout=5)
        if response.status_code == 200:
            fork_data = response.json().get('data', {})
            current_version = fork_data.get('current_version')
            previous_version = fork_data.get('previous_version')
            epoch = fork_data.get('epoch')
            print(f"\n📊 Fork 信息:")
            print(f"   Current Version: {current_version}")
            print(f"   Previous Version: {previous_version}")
            print(f"   Epoch: {epoch}")
        
        return {
            "genesis_validators_root": genesis_validators_root,
            "genesis_time": genesis_time,
            "current_version": current_version,
            "previous_version": previous_version,
            "epoch": epoch
        }
        
    except Exception as e:
        print(f"❌ 获取网络信息失败: {e}")
        return None

def check_network_config_file():
    """检查 network-config.yaml 文件"""
    print(f"\n🔍 检查 network-config.yaml 文件...")
    
    config_path = project_root / "infra" / "kurtosis" / "network-config.yaml"
    
    if not config_path.exists():
        print(f"❌ 文件不存在: {config_path}")
        return None
    
    print(f"✅ 文件存在: {config_path}")
    
    try:
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
        
        print(f"\n📊 网络配置关键参数:")
        print(f"   GENESIS_FORK_VERSION: {config.get('GENESIS_FORK_VERSION')}")
        print(f"   CONFIG_NAME: {config.get('CONFIG_NAME')}")
        print(f"   PRESET_BASE: {config.get('PRESET_BASE')}")
        print(f"   MIN_GENESIS_TIME: {config.get('MIN_GENESIS_TIME')}")
        print(f"   SECONDS_PER_SLOT: {config.get('SECONDS_PER_SLOT')}")
        
        # Fork versions
        print(f"\n📊 Fork Versions:")
        print(f"   ALTAIR_FORK_VERSION: {config.get('ALTAIR_FORK_VERSION')}")
        print(f"   BELLATRIX_FORK_VERSION: {config.get('BELLATRIX_FORK_VERSION')}")
        print(f"   CAPELLA_FORK_VERSION: {config.get('CAPELLA_FORK_VERSION')}")
        print(f"   DENEB_FORK_VERSION: {config.get('DENEB_FORK_VERSION')}")
        print(f"   ELECTRA_FORK_VERSION: {config.get('ELECTRA_FORK_VERSION')}")
        
        return config
        
    except Exception as e:
        print(f"❌ 读取文件失败: {e}")
        return None

def compare_configs(network_config: dict, beacon_info: dict):
    """比较网络配置和 Beacon API 信息"""
    print(f"\n🔍 比较配置...")
    
    if not network_config or not beacon_info:
        print("⚠️  无法比较：缺少配置或网络信息")
        return
    
    # 检查 fork version
    network_fork_version = network_config.get('GENESIS_FORK_VERSION', '').lower()
    beacon_current_version = beacon_info.get('current_version', '').lower()
    
    print(f"\n📊 Fork Version 比较:")
    print(f"   network-config.yaml: {network_fork_version}")
    print(f"   Beacon API (current): {beacon_current_version}")
    
    if network_fork_version == beacon_current_version:
        print(f"   ✅ Fork version 匹配")
    else:
        print(f"   ❌ Fork version 不匹配！这可能是问题的根源")
    
    # 注意：genesis_validators_root 在 network-config.yaml 中可能不存在
    # 它是在创世时动态生成的

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="检查 Validator Client 网络配置")
    parser.add_argument("--container", help="Validator Client 容器名称（可选，自动查找）")
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("Validator Client 网络配置检查工具")
    print("=" * 60)
    
    # 1. 检查 network-config.yaml 文件
    network_config = check_network_config_file()
    
    # 2. 从 Beacon API 获取网络信息
    beacon_info = check_beacon_api_network_info()
    
    # 3. 比较配置
    if network_config and beacon_info:
        compare_configs(network_config, beacon_info)
    
    # 4. 检查容器（如果提供了容器名）
    if args.container:
        check_docker_container(args.container)
    else:
        # 自动查找 Prysm validator 容器
        print(f"\n🔍 查找 Validator Client 容器...")
        result = subprocess.run(
            ["docker", "ps", "--format", "{{.Names}}"],
            capture_output=True,
            text=True,
            timeout=5
        )
        
        if result.returncode == 0:
            containers = result.stdout.strip().split('\n')
            validator_containers = [c for c in containers if 'validator' in c.lower() or 'prysm' in c.lower() or 'lighthouse' in c.lower() or 'teku' in c.lower()]
            
            if validator_containers:
                print(f"✅ 找到 {len(validator_containers)} 个 Validator Client 容器:")
                for container in validator_containers:
                    print(f"   - {container}")
                    check_docker_container(container)
            else:
                print(f"⚠️  未找到 Validator Client 容器")
    
    print("\n" + "=" * 60)
    print("检查完成")
    print("=" * 60)
    
    print("\n💡 排查建议:")
    print("1. 确认 network-config.yaml 文件已正确挂载到容器")
    print("2. 确认 Validator Client 启动命令包含 --chain-config-file 参数")
    print("3. 检查 network-config.yaml 中的 fork version 是否与 Beacon API 一致")
    print("4. 检查 genesis_validators_root（这个值在创世时确定，network-config.yaml 中可能没有）")
    print("5. 如果配置不匹配，可能需要重新生成 network-config.yaml 或重启 Validator Client")

if __name__ == "__main__":
    main()

