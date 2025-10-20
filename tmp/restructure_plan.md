# 项目重构计划

## 🎯 目标
重新组织项目结构，将 infra、code、data 等分门别类，提高可维护性和清晰度。

## 📁 新的目录结构设计

```
eth_validator_test/
├── README.md                              # 项目说明
├── start.sh                               # 主入口脚本
├── test_config.json                       # 测试配置
├── CLAUDE.md                              # 项目规划文档
│
├── infra/                                 # 基础设施配置
│   ├── docker-compose.yml                 # Docker 服务编排
│   ├── vault/                             # Vault 配置
│   │   ├── config/vault.hcl
│   │   └── init/admin-policy.hcl
│   ├── web3signer/                        # Web3Signer 配置
│   │   ├── config/config.yaml
│   │   └── init-db.sh
│   ├── kurtosis/                          # Kurtosis 配置
│   │   └── kurtosis-config.yaml
│   └── scripts/                           # 基础设施脚本
│       ├── vault_setup.py
│       └── orchestrate.py
│
├── code/                                  # 核心代码
│   ├── core/                              # 核心功能模块
│   │   ├── key_manager.py                 # 密钥管理
│   │   ├── deposit_manager.py            # 存款管理
│   │   ├── validator_manager.py           # 验证者管理
│   │   └── backup_system.py               # 备份系统
│   ├── utils/                             # 工具模块
│   │   ├── generate_keys.py               # 密钥生成
│   │   ├── deposit_generator.py          # 存款生成
│   │   └── validator_client_config.py    # 客户端配置
│   ├── external/                          # 外部依赖
│   │   └── ethstaker-deposit-cli/        # 官方存款CLI
│   └── requirements.txt                   # Python 依赖
│
├── data/                                  # 数据目录
│   ├── keys/                              # 密钥数据
│   │   ├── keystores/                     # keystore 文件
│   │   ├── secrets/                       # 密码文件
│   │   └── pubkeys.json                   # 公钥索引
│   ├── deposits/                          # 存款数据
│   │   └── deposit_data.json
│   ├── configs/                           # 配置文件
│   │   ├── prysm/
│   │   ├── lighthouse/
│   │   └── teku/
│   ├── backups/                           # 备份文件
│   │   ├── keystores/
│   │   └── mnemonics/
│   └── logs/                              # 日志文件
│
└── docs/                                  # 文档
    ├── api/                               # API 文档
    ├── guides/                            # 使用指南
    └── troubleshooting/                   # 故障排除
```

## 🔄 重构步骤

### 1. 创建新目录结构
### 2. 移动文件到对应目录
### 3. 更新所有路径引用
### 4. 清理冗余代码
### 5. 更新文档

## 🧹 需要清理的冗余内容

### 重复的密钥管理模块
- `scripts/key_manager.py` (legacy)
- `scripts/vault_key_manager.py` (new)
- 合并为一个统一的密钥管理模块

### 重复的存款管理模块
- `scripts/deposit_manager.py` (legacy)
- `scripts/deposit_generator.py` (new)
- 合并为一个统一的存款管理模块

### 冗余的测试文件
- `ethstaker-deposit-cli/test_*.py` (可以删除)
- `result/1-kurtosis.md` (移动到 docs/)

### 无用的目录
- `external_keys/` (移动到 data/keys/)
- `web3signer/keys/` (移动到 data/keys/)
- `vault/` (移动到 infra/vault/)
- `kurtosis/` (移动到 infra/kurtosis/)
- `web3signer/` (移动到 infra/web3signer/)
