# Vault 健康检查诊断指南

## 快速诊断命令

### 1. 检查 Vault 容器状态
```bash
docker ps | grep vault
docker logs vault-1 --tail 50
```

### 2. 直接检查 Vault 健康状态（不需要认证）
```bash
# 在容器内
docker exec vault-1 vault status

# 或使用 curl（从任何可以访问 Vault 的容器）
curl http://vault-1:8200/v1/sys/health
```

### 3. 检查后端 API 健康检查端点
```bash
# 从后端容器内
curl http://localhost:8000/api/v1/monitoring/health

# 或从外部（如果端口映射了）
curl http://localhost:8001/api/v1/monitoring/health
```

### 4. 检查后端日志
```bash
docker logs backend --tail 100 | grep -i vault
```

### 5. 使用诊断脚本
```bash
# 在服务器上运行
cd system_v2
./scripts/check_vault_health.sh

# 或指定 Vault 地址
VAULT_ADDR=http://vault-1:8200 ./scripts/check_vault_health.sh

# 或指定后端地址
BACKEND_URL=http://localhost:8001 ./scripts/check_vault_health.sh
```

## 常见问题排查

### 问题 1: Vault 显示为异常，但容器正常运行

**可能原因：**
- Vault 已密封（sealed）
- Vault 未初始化
- 网络连接问题
- 后端无法访问 Vault

**排查步骤：**
```bash
# 1. 检查 Vault 状态
docker exec vault-1 vault status

# 2. 如果显示 "Sealed: true"，需要解锁
# 查看 unseal key（从初始化日志或 Consul）
docker exec consul consul kv get vault/unseal_key

# 3. 解锁 Vault
docker exec vault-1 vault operator unseal <unseal-key>

# 4. 检查后端是否能访问 Vault
docker exec backend curl -s http://vault-1:8200/v1/sys/health
```

### 问题 2: 后端日志显示认证失败

**可能原因：**
- VAULT_TOKEN 环境变量不正确
- Vault 重新初始化后 token 已更改

**排查步骤：**
```bash
# 1. 检查当前使用的 token
docker exec backend env | grep VAULT_TOKEN

# 2. 从 Consul 获取最新 token
docker exec consul consul kv get vault/root_token

# 3. 测试 token 是否有效
docker exec vault-1 vault auth <token>

# 4. 更新 docker-compose.yml 中的 VAULT_TOKEN
# 或让后端自动从 Consul 读取（已实现）
```

### 问题 3: 健康检查返回 false

**检查健康状态详情：**
```bash
# 直接调用健康检查 API
curl -s http://localhost:8001/api/v1/monitoring/health | python3 -m json.tool

# 查看返回的 vault 字段值
```

**如果 vault 为 false，检查：**
```bash
# 1. Vault 是否已初始化
curl -s http://vault-1:8200/v1/sys/health | grep initialized

# 2. Vault 是否已解锁
curl -s http://vault-1:8200/v1/sys/health | grep sealed

# 3. 后端日志中的详细错误
docker logs backend --tail 50 | grep -i "vault\|health"
```

## 健康检查逻辑说明

后端健康检查使用以下逻辑：

1. **首先尝试不需要认证的健康检查**：
   - 直接调用 `vault.sys.read_health_status()`（不需要 token）
   - 检查 `initialized=true` 且 `sealed=false`

2. **如果失败，尝试使用 VaultClient**：
   - 创建 VaultClient（可能需要认证）
   - 调用 `health_check()` 方法

3. **如果都失败，返回 false**：
   - 记录错误日志
   - 前端显示为异常

## 手动测试健康检查

### Python 脚本测试
```python
import hvac

# 不需要认证的健康检查
client = hvac.Client(url="http://vault-1:8200")
health = client.sys.read_health_status()
print(f"Initialized: {health.get('initialized')}")
print(f"Sealed: {health.get('sealed')}")
print(f"Healthy: {health.get('initialized') and not health.get('sealed')}")
```

### 使用 vault CLI
```bash
# 在容器内
docker exec vault-1 vault status

# 应该看到：
# Key             Value
# ---             -----
# Seal Type       shamir
# Initialized     true
# Sealed          false
# ...
```

## 修复建议

如果 Vault 显示异常：

1. **确保 Vault 已初始化且未密封**
2. **检查网络连接**（后端能否访问 vault-1:8200）
3. **查看后端日志**（是否有错误信息）
4. **重启后端服务**（应用最新的健康检查逻辑）

```bash
docker-compose restart backend
```

