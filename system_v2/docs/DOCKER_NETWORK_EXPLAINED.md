# Docker Compose 网络访问说明

## 网络配置

在你的 `docker-compose.yml` 中：

```yaml
networks:
  validator_network:
    driver: bridge
```

所有服务都连接到 `validator_network` 这个 bridge 网络。

## 端口访问规则

### 1. **容器内部端口 vs 主机端口**

```yaml
vault-1:
  ports:
    - "8200:8200"  # 主机端口:容器端口
```

- **容器内部端口**：容器内应用监听的端口（如 `8200`）
- **主机端口**：从宿主机访问的端口（如 `8200`）
- **映射关系**：`主机端口:容器端口`

### 2. **容器间访问（同一网络）**

在同一 Docker 网络中，容器可以通过**容器名**或**服务名**互相访问：

```yaml
# ✅ 正确：使用容器名 + 容器内部端口
VAULT_URL=http://vault-1:8200        # vault-1 是容器名，8200 是容器内部端口

# ✅ 正确：使用服务名 + 容器内部端口  
VAULT_URL=http://vault-1:8200       # 服务名和容器名相同

# ❌ 错误：使用 localhost
VAULT_URL=http://localhost:8200     # localhost 指向容器自己，不是其他容器

# ❌ 错误：使用主机端口映射
VAULT_URL=http://vault-1:8200        # 这里 8200 是容器端口，不是主机端口
```

### 3. **从宿主机访问**

从宿主机（你的电脑）访问容器：

```bash
# ✅ 使用主机端口映射
curl http://localhost:8200           # 访问 vault-1（通过端口映射）

# ❌ 不能直接使用容器名
curl http://vault-1:8200             # 宿主机无法解析容器名
```

### 4. **端口映射的作用**

```yaml
ports:
  - "8200:8200"  # 将容器的 8200 端口映射到主机的 8200 端口
```

- **作用**：允许从宿主机访问容器内的服务
- **不影响**：容器间访问（容器间使用容器名+容器端口，不需要端口映射）

## 你的配置分析

### ✅ 正确的配置

```yaml
vault-1:
  container_name: vault-1
  ports:
    - "8200:8200"              # 主机:容器端口映射
  networks:
    - validator_network

backend:
  environment:
    - VAULT_URL=http://vault-1:8200  # ✅ 正确：容器名 + 容器内部端口
  networks:
    - validator_network
```

### 工作原理

1. **Vault 容器**：
   - 容器内监听：`0.0.0.0:8200`
   - 主机访问：`localhost:8200`（通过端口映射）
   - 容器间访问：`vault-1:8200`（通过容器名）

2. **Backend 容器访问 Vault**：
   - 使用：`http://vault-1:8200`
   - DNS 解析：Docker 网络自动将 `vault-1` 解析为 Vault 容器的 IP
   - 端口：使用容器内部端口 `8200`（不是主机端口）

3. **Web3Signer 配置**：
   ```yaml
   web3signer-1:
     container_name: web3signer-1
     ports:
       - "9000:9000"           # 主机端口:容器端口
     # 容器内监听 9000 端口
   
   web3signer-2:
     container_name: web3signer-2
     ports:
       - "9001:9000"           # 主机端口不同，但容器内都是 9000
     # 容器内也监听 9000 端口
   
   backend:
     environment:
       - WEB3SIGNER_URL_PRIMARY=http://web3signer-1:9000    # ✅ 容器名 + 容器端口
       - WEB3SIGNER_URL_SECONDARY=http://web3signer-2:9000   # ✅ 容器名 + 容器端口
   ```

## 常见错误

### ❌ 错误 1：使用 localhost

```yaml
backend:
  environment:
    - VAULT_URL=http://localhost:8200  # ❌ localhost 指向容器自己
```

**问题**：`localhost` 在容器内指向容器自己，不是其他容器

### ❌ 错误 2：使用主机 IP

```yaml
backend:
  environment:
    - VAULT_URL=http://192.168.1.100:8200  # ❌ 不必要且可能失败
```

**问题**：应该使用容器名，让 Docker DNS 自动解析

### ✅ 正确做法

```yaml
backend:
  environment:
    - VAULT_URL=http://vault-1:8200  # ✅ 容器名 + 容器内部端口
```

## 验证网络连接

### 从容器内测试

```bash
# 测试 DNS 解析
docker exec backend ping -c 1 vault-1

# 测试端口连接
docker exec backend curl -v http://vault-1:8200/v1/sys/health

# 测试 Web3Signer
docker exec backend curl -v http://web3signer-1:9000/upcheck
```

### 检查网络配置

```bash
# 查看网络详情
docker network inspect validator_network

# 查看容器网络配置
docker inspect backend | grep -A 20 Networks
docker inspect vault-1 | grep -A 20 Networks
```

## 总结

1. **容器间访问**：使用 `容器名:容器内部端口`
2. **主机访问容器**：使用 `localhost:主机端口`（需要端口映射）
3. **端口映射**：只影响主机访问，不影响容器间访问
4. **DNS 解析**：Docker 网络自动提供 DNS 解析，容器名自动解析为容器 IP

你的配置是正确的！问题在于代码处理 hvac 库的返回值。

