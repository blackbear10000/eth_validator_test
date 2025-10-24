# Validator Client 启动指南

## 🎯 概述

本指南将帮助你启动 validator client 连接到 Web3Signer 进行验证签名。

## 📋 前置条件

### 1. 基础设施已启动
```bash
# 启动所有服务（Vault, Web3Signer, PostgreSQL, HAProxy）
./validator.sh start

# 启动 Kurtosis 开发网络
kurtosis run github.com/ethpandaops/ethereum-package --args-file infra/kurtosis/kurtosis-config.yaml --enclave eth-devnet

# 检查服务状态
./validator.sh check-services
```

### 2. 动态端口检测
```bash
# 检测 Kurtosis 网络的实际端口（自动适配随机端口）
./validator.sh detect-kurtosis-ports

# 检查检测结果
cat config/kurtosis_ports.json
```

### 3. 验证者密钥已注册
- 验证者密钥已生成并存储在 Vault 中
- 验证者已通过 deposit 注册到链上
- 验证者状态为 `active`

## 🚀 启动步骤

### 步骤 1: 检查服务状态
```bash
# 检查所有服务是否就绪（包括 Kurtosis 网络）
./validator.sh check-services
```

应该看到：
```
✅ Web3Signer
✅ Vault  
✅ Kurtosis Beacon Node
   ✅ prysm Beacon API: http://localhost:XXXXX
```

### 步骤 2: 选择 Validator Client

支持三种客户端：
- **Prysm**: 功能最全面，推荐用于生产
- **Lighthouse**: 性能优秀，资源占用少
- **Teku**: 企业级，Java 实现

### 步骤 3: 启动 Validator Client

#### 使用 Prysm
```bash
# 启动 Prysm 验证者
./validator.sh start-validator prysm

# 仅生成配置（不启动）
./validator.sh start-validator prysm --config-only
```

#### 使用 Lighthouse
```bash
# 启动 Lighthouse 验证者
./validator.sh start-validator lighthouse

# 仅生成配置（不启动）
./validator.sh start-validator lighthouse --config-only
```

#### 使用 Teku
```bash
# 启动 Teku 验证者
./validator.sh start-validator teku

# 仅生成配置（不启动）
./validator.sh start-validator teku --config-only
```

## 🔧 配置详情

### Web3Signer 连接配置
- **Web3Signer URL**: `http://localhost:9002` (HAProxy 负载均衡)
- **直接连接**: `http://localhost:9000` (Web3Signer-1)
- **备用连接**: `http://localhost:9001` (Web3Signer-2)

### Beacon 节点配置（动态检测）
- **Prysm**: 自动检测 Kurtosis 网络中的 Prysm Beacon API 端口
- **Lighthouse**: 自动检测 Kurtosis 网络中的 Lighthouse Beacon API 端口
- **Teku**: 自动检测 Kurtosis 网络中的 Teku Beacon API 端口

> 💡 **注意**: 端口是动态检测的，无需手动配置。系统会自动适配 Kurtosis 的随机端口分配。

### 生成的配置文件位置
```
configs/
├── prysm/
│   ├── validator-config.yaml
│   ├── web3signer-config.yaml
│   └── start-validator.sh
├── lighthouse/
│   ├── validator-config.yaml
│   ├── web3signer-config.yaml
│   └── start-validator.sh
└── teku/
    ├── validator-config.yaml
    ├── web3signer-config.yaml
    └── start-validator.sh
```

## 📊 监控和验证

### 检查验证者状态
```bash
# 检查 Web3Signer 中的密钥
./validator.sh web3signer-status

# 验证密钥加载
./validator.sh verify-keys

# 监控验证者性能
./validator.sh monitor
```

### 检查 Beacon 链状态
```bash
# 检查信标链健康状态
curl http://localhost:5052/eth/v1/node/health

# 检查验证者状态
curl http://localhost:5052/eth/v1/beacon/states/head/validators
```

## 🛠️ 故障排除

### 常见问题

#### 1. Web3Signer 连接失败
```bash
# 检查 Web3Signer 状态
curl http://localhost:9000/upcheck

# 检查 HAProxy 状态
curl http://localhost:9002/upcheck

# 重启 Web3Signer
docker restart web3signer-1 web3signer-2
```

#### 2. Beacon 节点连接失败
```bash
# 检查 Kurtosis 网络状态
kurtosis enclave ls

# 检查信标链服务
kurtosis service logs eth-devnet cl-1-lighthouse-geth
```

#### 3. 验证者密钥未找到
```bash
# 检查 Vault 中的密钥
./validator.sh list-keys

# 重新加载密钥到 Web3Signer
./validator.sh load-keys
```

### 日志查看
```bash
# 查看 validator client 日志
tail -f configs/prysm/validator.log

# 查看 Web3Signer 日志
docker logs web3signer-1 -f

# 查看 HAProxy 日志
docker logs web3signer-lb -f
```

## 🔐 安全注意事项

1. **密钥安全**: 验证者私钥存储在 Vault 中，Web3Signer 通过 API 访问
2. **网络安全**: 所有服务运行在 Docker 网络中，外部访问受限
3. **访问控制**: 使用 Vault token 进行身份验证
4. **备份**: 定期备份 Vault 中的密钥数据

## 📈 性能优化

### Web3Signer 高可用
- 使用 HAProxy 负载均衡
- 双 Web3Signer 实例提供冗余
- 自动故障转移

### 资源监控
```bash
# 监控 Docker 容器资源使用
docker stats

# 监控 Web3Signer 性能
curl http://localhost:9000/metrics
```

## 🎉 完成

当验证者客户端成功启动后，你将看到：
- 验证者连接到 Web3Signer
- 开始参与共识过程
- 验证者状态变为 `active`
- 开始获得奖励

现在你的验证者已经成功连接到 Web3Signer 并开始验证签名！
