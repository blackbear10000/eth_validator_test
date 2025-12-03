# Web3Signer 主机授权配置说明

## 问题描述

Web3Signer 返回 403 "Host not authorized." 错误，这是因为 Web3Signer 默认启用了主机授权检查。

## 解决方案

在 `config.yaml` 中添加 `http-host-allowlist` 配置：

```yaml
# HTTP settings
http-listen-host: "0.0.0.0"
http-listen-port: 9000
# Host allowlist - 允许所有主机访问
http-host-allowlist: ["*"]
# CORS settings
http-cors-origins: ["*"]
```

## 配置说明

### `http-host-allowlist`

- **作用**：指定允许访问 Web3Signer 的主机名列表
- **默认值**：如果未配置，Web3Signer 会拒绝来自未授权主机的请求
- **值**：
  - `["*"]` - 允许所有主机（开发环境推荐）
  - `["localhost", "127.0.0.1", "web3signer-1"]` - 指定允许的主机名列表（生产环境推荐）

### 为什么需要这个配置？

在 Docker 网络中：
- 后端容器通过 `web3signer-1:9000` 访问 Web3Signer
- Web3Signer 检查请求的 `Host` 头：`web3signer-1:9000`
- 如果 `web3signer-1` 不在允许列表中，返回 403

### 应用配置

修改配置后，需要重启 Web3Signer 容器：

```bash
docker-compose restart web3signer-1 web3signer-2
```

### 验证配置

重启后，测试访问：

```bash
# 从后端容器测试
docker exec backend curl -v http://web3signer-1:9000/upcheck
docker exec backend curl -v http://web3signer-2:9000/upcheck

# 应该返回 200 OK，而不是 403 Forbidden
```

## 生产环境建议

在生产环境中，建议使用更严格的主机列表：

```yaml
http-host-allowlist: 
  - "localhost"
  - "127.0.0.1"
  - "web3signer-1"
  - "web3signer-2"
  - "backend"
  - "haproxy"
```

这样可以提高安全性，只允许已知的服务访问。

