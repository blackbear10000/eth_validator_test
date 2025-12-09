# 文档目录

本文档目录包含系统 v2 的详细技术文档。

## 核心文档

- [系统架构](./ARCHITECTURE.md) - 整体架构设计、核心组件、数据流
- [API 文档](./API.md) - API 端点说明、请求/响应格式
- [部署文档](./DEPLOYMENT.md) - 部署指南、环境配置

## 功能文档

- [用户认证系统](./USER_AUTHENTICATION.md) - 用户认证、权限控制、审计日志
- [功能更新](./FEATURE_UPDATES.md) - 最新功能更新和优化说明
- [更新日志](./CHANGELOG.md) - 版本更新历史

## 流程文档

- [验证者存款流程](./VALIDATOR_DEPOSIT_PROCESS.md) - 存款流程详解
- [验证者退出流程](./VALIDATOR_EXIT_PROCESS.md) - 退出流程详解
- [端点发现流程](./ENDPOINT_DISCOVERY_FLOW.md) - 网络端点自动发现机制

## 客户端管理

- [客户端管理](./CLIENT_MANAGEMENT.md) - 客户端管理功能说明
- [客户端管理实现](./CLIENT_MANAGEMENT_IMPLEMENTATION.md) - 实现细节
- [客户端启动命令](./CLIENT_STARTUP_COMMAND.md) - 客户端启动参数说明

## 问题排查

- [Beacon API 连接问题](./BEACON_API_CONNECTION_ISSUE.md)
- [Beacon API 解析修复](./BEACON_API_PARSING_FIX.md)
- [Beacon API 公钥格式](./BEACON_API_PUBKEY_FORMAT.md)
- [Beacon API 公钥前缀修复](./BEACON_API_PUBKEY_PREFIX_FIX.md)
- [退出签名问题排查](./EXIT_SIGNATURE_TROUBLESHOOTING.md)
- [状态检测分析](./STATUS_DETECTION_ANALYSIS.md)
- [存款验证 Epoch 修复](./DEPOSIT_VALIDATION_EPOCH_FIX.md)
- [Web3Signer 主机授权](./WEB3SIGNER_HOST_AUTHORIZATION.md)

## 技术细节

- [Prysm Beacon 端点对比](./PRYSM_BEACON_ENDPOINT_COMPARISON.md)
- [Prysm gRPC 端点调试](./PRYSM_GRPC_ENDPOINT_DEBUG.md)
- [Docker 网络说明](./DOCKER_NETWORK_EXPLAINED.md)

## 快速导航

### 新用户
1. 阅读 [系统架构](./ARCHITECTURE.md) 了解整体设计
2. 阅读 [用户认证系统](./USER_AUTHENTICATION.md) 了解登录和权限
3. 阅读 [API 文档](./API.md) 了解 API 使用

### 开发者
1. [系统架构](./ARCHITECTURE.md) - 了解系统设计
2. [功能更新](./FEATURE_UPDATES.md) - 了解最新功能
3. [更新日志](./CHANGELOG.md) - 了解版本变更

### 运维人员
1. [部署文档](./DEPLOYMENT.md) - 部署指南
2. [用户认证系统](./USER_AUTHENTICATION.md) - 创建管理员账户
3. 问题排查相关文档

## 文档更新

文档会随着系统更新而持续更新。主要更新记录在 [更新日志](./CHANGELOG.md) 中。

## 贡献

如有文档问题或建议，请提交 Issue 或 Pull Request。

