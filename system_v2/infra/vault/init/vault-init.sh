#!/bin/sh

set -e

export VAULT_ADDR=http://localhost:8200

# 等待 Vault 启动
echo "Waiting for Vault to start..."
for i in $(seq 1 30); do
  if vault status >/dev/null 2>&1; then
    break
  fi
  sleep 1
done

# 检查 Vault 是否已初始化
VAULT_STATUS_OUTPUT=$(vault status 2>&1)
if echo "$VAULT_STATUS_OUTPUT" | grep -q "Initialized.*true"; then
  echo "Initializing Vault..."
  
  # 初始化 Vault（1个密钥份额，阈值为1，适合测试环境）
  INIT_OUTPUT=$(vault operator init -key-shares=1 -key-threshold=1 -format=json)
  
  # 提取 root token 和 unseal key
  ROOT_TOKEN=$(echo "$INIT_OUTPUT" | grep -o '"root_token":"[^"]*' | cut -d'"' -f4)
  UNSEAL_KEY=$(echo "$INIT_OUTPUT" | grep -o '"unseal_keys_b64":\["[^"]*' | cut -d'"' -f4)
  
  # 保存到文件（用于后续使用）
  echo "$ROOT_TOKEN" > /vault/data/root_token.txt
  echo "$UNSEAL_KEY" > /vault/data/unseal_key.txt
  
  # 也保存到共享位置，供其他容器使用（如果使用共享卷）
  mkdir -p /vault/data/shared
  echo "$ROOT_TOKEN" > /vault/data/shared/root_token.txt 2>/dev/null || true
  echo "$UNSEAL_KEY" > /vault/data/shared/unseal_key.txt 2>/dev/null || true
  
  # 使用 unseal key 解锁 Vault
  export VAULT_TOKEN="$ROOT_TOKEN"
  vault operator unseal "$UNSEAL_KEY"
  
  echo "Vault initialized successfully"
  echo "Root Token: $ROOT_TOKEN"
  echo "Unseal Key: $UNSEAL_KEY"
else
  echo "Vault already initialized"
  
  # 如果已初始化但未解锁，尝试使用保存的 unseal key
  VAULT_STATUS_CHECK=$(vault status 2>&1)
  if echo "$VAULT_STATUS_CHECK" | grep -q "Sealed.*true"; then
    if [ -f /vault/data/unseal_key.txt ]; then
      UNSEAL_KEY=$(cat /vault/data/unseal_key.txt)
      vault operator unseal "$UNSEAL_KEY"
      echo "Vault unsealed"
    else
      echo "Warning: Vault is sealed but no unseal key found"
    fi
  fi
  
  # 使用保存的 root token 或默认值
  if [ -f /vault/data/root_token.txt ]; then
    export VAULT_TOKEN=$(cat /vault/data/root_token.txt)
  else
    export VAULT_TOKEN=dev-root-token
  fi
fi

# 启用 userpass 认证
echo "Setting up authentication..."
vault auth enable userpass || true

# 创建 admin 用户
vault write auth/userpass/users/admin password=admin policies=admin || true

# 如果 admin policy 不存在，创建它
if ! vault policy read admin >/dev/null 2>&1; then
  if [ -f /vault/config/../init/admin-policy.hcl ]; then
    vault policy write admin /vault/config/../init/admin-policy.hcl
  else
    # 创建默认的 admin policy
    vault policy write admin - <<EOF
path "*" {
  capabilities = ["create", "read", "update", "delete", "list", "sudo"]
}
EOF
  fi
fi

# 输出重要信息
if [ -f /vault/data/root_token.txt ]; then
  SAVED_TOKEN=$(cat /vault/data/root_token.txt)
  echo "=========================================="
  echo "IMPORTANT: Save this root token securely:"
  echo "$SAVED_TOKEN"
  echo "=========================================="
  echo ""
  echo "To use this token in other services, update VAULT_TOKEN in docker-compose.yml"
  echo "Or use the admin user: username=admin, password=admin"
fi

echo "Vault setup completed"
echo "Note: If this is the first initialization, save the root token and unseal key securely"

