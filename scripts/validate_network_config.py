#!/usr/bin/env python3
"""
验证网络配置的正确性
检查 Kurtosis 配置和 network-config.yaml 的一致性
"""

import yaml
import sys
from typing import Dict, Any, List

class NetworkConfigValidator:
    def __init__(self):
        self.kurtosis_config_path = "infra/kurtosis/kurtosis-config.yaml"
        self.network_config_path = "infra/kurtosis/network-config.yaml"
    
    def load_kurtosis_config(self) -> Dict[str, Any]:
        """加载 Kurtosis 配置"""
        try:
            with open(self.kurtosis_config_path, 'r') as f:
                return yaml.safe_load(f)
        except Exception as e:
            print(f"❌ 无法加载 Kurtosis 配置: {e}")
            return {}
    
    def load_network_config(self) -> Dict[str, Any]:
        """加载网络配置"""
        try:
            with open(self.network_config_path, 'r') as f:
                return yaml.safe_load(f)
        except Exception as e:
            print(f"❌ 无法加载网络配置: {e}")
            return {}
    
    def extract_fork_epochs_from_kurtosis(self, kurtosis_config: Dict[str, Any]) -> Dict[str, int]:
        """从 Kurtosis 配置中提取 fork epochs"""
        network_params = kurtosis_config.get('network_params', {})
        return {
            'altair': network_params.get('altair_fork_epoch', 0),
            'bellatrix': network_params.get('bellatrix_fork_epoch', 0),
            'capella': network_params.get('capella_fork_epoch', 0),
            'deneb': network_params.get('deneb_fork_epoch', 0),
            'electra': network_params.get('electra_fork_epoch', 0)
        }
    
    def extract_fork_versions_from_network(self, network_config: Dict[str, Any]) -> Dict[str, str]:
        """从网络配置中提取 fork 版本"""
        return {
            'altair': network_config.get('ALTAIR_FORK_VERSION', '0x00000000'),
            'bellatrix': network_config.get('BELLATRIX_FORK_VERSION', '0x00000000'),
            'capella': network_config.get('CAPELLA_FORK_VERSION', '0x00000000'),
            'deneb': network_config.get('DENEB_FORK_VERSION', '0x00000000'),
            'electra': network_config.get('ELECTRA_FORK_VERSION', '0x00000000')
        }
    
    def extract_fork_epochs_from_network(self, network_config: Dict[str, Any]) -> Dict[str, int]:
        """从网络配置中提取 fork epochs"""
        return {
            'altair': network_config.get('ALTAIR_FORK_EPOCH', 0),
            'bellatrix': network_config.get('BELLATRIX_FORK_EPOCH', 0),
            'capella': network_config.get('CAPELLA_FORK_EPOCH', 0),
            'deneb': network_config.get('DENEB_FORK_EPOCH', 0),
            'electra': network_config.get('ELECTRA_FORK_EPOCH', 0)
        }
    
    def validate_fork_consistency(self) -> bool:
        """验证 fork 配置的一致性"""
        print("🔍 验证网络配置一致性...")
        print("=" * 50)
        
        # 加载配置
        kurtosis_config = self.load_kurtosis_config()
        network_config = self.load_network_config()
        
        if not kurtosis_config or not network_config:
            return False
        
        # 提取 fork 信息
        kurtosis_epochs = self.extract_fork_epochs_from_kurtosis(kurtosis_config)
        network_versions = self.extract_fork_versions_from_network(network_config)
        network_epochs = self.extract_fork_epochs_from_network(network_config)
        
        print("\n📋 Kurtosis 配置的 Fork Epochs:")
        for fork, epoch in kurtosis_epochs.items():
            print(f"  {fork}: {epoch}")
        
        print("\n📋 Network 配置的 Fork 版本:")
        for fork, version in network_versions.items():
            print(f"  {fork}: {version}")
        
        print("\n📋 Network 配置的 Fork Epochs:")
        for fork, epoch in network_epochs.items():
            print(f"  {fork}: {epoch}")
        
        # 验证一致性
        print("\n🔍 验证一致性...")
        all_consistent = True
        
        for fork in ['altair', 'bellatrix', 'capella', 'deneb', 'electra']:
            kurtosis_epoch = kurtosis_epochs.get(fork, 0)
            network_epoch = network_epochs.get(fork, 0)
            
            if kurtosis_epoch == network_epoch:
                print(f"✅ {fork}: epoch {kurtosis_epoch} 一致")
            else:
                print(f"❌ {fork}: Kurtosis epoch {kurtosis_epoch} != Network epoch {network_epoch}")
                all_consistent = False
        
        # 检查版本格式
        print("\n🔍 验证版本格式...")
        for fork, version in network_versions.items():
            version_str = str(version)
            if version_str.startswith('0x') and len(version_str) == 10:
                print(f"✅ {fork}: 版本格式正确 {version_str}")
            else:
                print(f"❌ {fork}: 版本格式错误 {version_str}")
                all_consistent = False
        
        return all_consistent
    
    def check_missing_configs(self) -> List[str]:
        """检查缺失的配置"""
        network_config = self.load_network_config()
        missing = []
        
        required_configs = [
            'ALTAIR_FORK_VERSION', 'ALTAIR_FORK_EPOCH',
            'BELLATRIX_FORK_VERSION', 'BELLATRIX_FORK_EPOCH',
            'CAPELLA_FORK_VERSION', 'CAPELLA_FORK_EPOCH',
            'DENEB_FORK_VERSION', 'DENEB_FORK_EPOCH',
            'ELECTRA_FORK_VERSION', 'ELECTRA_FORK_EPOCH'
        ]
        
        for config in required_configs:
            if config not in network_config:
                missing.append(config)
        
        return missing
    
    def provide_fix_suggestions(self) -> None:
        """提供修复建议"""
        print("\n🛠️  修复建议:")
        print("=" * 50)
        
        missing = self.check_missing_configs()
        if missing:
            print("❌ 缺失的配置:")
            for config in missing:
                print(f"  - {config}")
        else:
            print("✅ 所有必要的 fork 配置都存在")
        
        print("\n📝 建议的配置格式:")
        print("""
# 确保所有 fork 都有版本和 epoch 配置
ALTAIR_FORK_VERSION: 0x20000038
ALTAIR_FORK_EPOCH: 0
BELLATRIX_FORK_VERSION: 0x30000038
BELLATRIX_FORK_EPOCH: 0
CAPELLA_FORK_VERSION: 0x40000038
CAPELLA_FORK_EPOCH: 0
DENEB_FORK_VERSION: 0x50000038
DENEB_FORK_EPOCH: 0
ELECTRA_FORK_VERSION: 0x60000038
ELECTRA_FORK_EPOCH: 0
        """)
    
    def run_validation(self) -> bool:
        """运行完整验证"""
        print("🔍 网络配置验证工具")
        print("=" * 50)
        
        # 1. 验证一致性
        consistent = self.validate_fork_consistency()
        
        # 2. 检查缺失配置
        print("\n🔍 检查缺失配置...")
        missing = self.check_missing_configs()
        if missing:
            print(f"❌ 发现 {len(missing)} 个缺失的配置")
        else:
            print("✅ 所有必要配置都存在")
        
        # 3. 提供修复建议
        self.provide_fix_suggestions()
        
        # 4. 总结
        print("\n" + "=" * 50)
        print("📊 验证结果:")
        print("=" * 50)
        
        if consistent and not missing:
            print("✅ 配置验证通过！")
            return True
        else:
            print("❌ 配置验证失败，请根据上述建议进行修复。")
            return False

def main():
    """主函数"""
    validator = NetworkConfigValidator()
    success = validator.run_validation()
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
