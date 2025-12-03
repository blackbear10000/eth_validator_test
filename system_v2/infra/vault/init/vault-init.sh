#!/bin/sh

export VAULT_ADDR=http://localhost:8200

# 等待 Vault 启动并响应
echo "Waiting for Vault to start..."
for i in $(seq 1 60); do
  # 检查 Vault 是否响应（即使未初始化也会响应）
  if vault status 2>&1 | grep -qE "(Initialized|Error making API request)" || vault status 2>&1 | grep -q "seal configuration missing"; then
    echo "Vault is responding"
    break
  fi
  if [ $i -eq 60 ]; then
    echo "Error: Vault did not start within 60 seconds"
    exit 1
  fi
  sleep 1
done

# 额外等待确保 Vault 完全启动
sleep 2

# 检查 Vault 是否已初始化
VAULT_STATUS_OUTPUT=$(vault status 2>&1)
if ! echo "$VAULT_STATUS_OUTPUT" | grep -q "Initialized.*true"; then
  echo "Vault is not initialized, initializing now..."
  
  # 初始化 Vault（1个密钥份额，阈值为1，适合测试环境）
  echo "Running vault operator init..."
  INIT_OUTPUT=$(vault operator init -key-shares=1 -key-threshold=1 -format=json 2>&1)
  
  if [ $? -ne 0 ]; then
    echo "Error initializing Vault: $INIT_OUTPUT"
    exit 1
  fi
  
  # 提取 root token 和 unseal key
  # 将 JSON 压缩为单行以便处理
  INIT_JSON=$(echo "$INIT_OUTPUT" | tr -d '\n' | tr -d ' ')
  
  # 提取 root_token 值
  ROOT_TOKEN=$(echo "$INIT_JSON" | sed 's/.*"root_token":"\([^"]*\)".*/\1/')
  
  # 提取 unseal_keys_b64 数组中的第一个值
  UNSEAL_KEY=$(echo "$INIT_JSON" | sed 's/.*"unseal_keys_b64":\["\([^"]*\)".*/\1/')
  
  # 如果压缩后提取失败，尝试从原始输出中提取
  if [ -z "$ROOT_TOKEN" ] || [ "$ROOT_TOKEN" = "$INIT_JSON" ]; then
    ROOT_TOKEN=$(echo "$INIT_OUTPUT" | grep '"root_token"' | sed 's/.*"root_token"[^"]*"\([^"]*\)".*/\1/')
  fi
  
  if [ -z "$UNSEAL_KEY" ] || [ "$UNSEAL_KEY" = "$INIT_JSON" ]; then
    # 查找 unseal_keys_b64 数组中的第一个字符串
    UNSEAL_KEY=$(echo "$INIT_OUTPUT" | grep -A 2 '"unseal_keys_b64"' | grep -o '"[^"]*"' | head -1 | tr -d '"')
  fi
  
  if [ -z "$ROOT_TOKEN" ] || [ -z "$UNSEAL_KEY" ] || [ "$ROOT_TOKEN" = "$INIT_JSON" ] || [ "$UNSEAL_KEY" = "$INIT_JSON" ]; then
    echo "Error: Failed to extract root token or unseal key from init output"
    echo "Init output: $INIT_OUTPUT"
    echo "Extracted ROOT_TOKEN: $ROOT_TOKEN"
    echo "Extracted UNSEAL_KEY: $UNSEAL_KEY"
    exit 1
  fi
  
  # 保存到文件（用于后续使用）
  echo "$ROOT_TOKEN" > /vault/data/root_token.txt
  echo "$UNSEAL_KEY" > /vault/data/unseal_key.txt
  
  # 也保存到共享位置，供其他容器使用（如果使用共享卷）
  mkdir -p /vault/data/shared
  echo "$ROOT_TOKEN" > /vault/data/shared/root_token.txt 2>/dev/null || true
  echo "$UNSEAL_KEY" > /vault/data/shared/unseal_key.txt 2>/dev/null || true
  
  # 保存到 Consul（持久化存储，即使 volume 丢失也能恢复）
  CONSUL_ADDR="${CONSUL_ADDR:-consul:8500}"
  CONSUL_HOST=$(echo "$CONSUL_ADDR" | cut -d: -f1)
  CONSUL_PORT=$(echo "$CONSUL_ADDR" | cut -d: -f2)
  
  # 使用 curl、wget 或 nc 保存到 Consul
  if command -v curl >/dev/null 2>&1; then
    curl -s -X PUT "http://$CONSUL_ADDR/v1/kv/vault/unseal_key" -d "$UNSEAL_KEY" >/dev/null 2>&1 && \
      echo "Unseal key saved to Consul" || echo "Warning: Failed to save unseal key to Consul"
    curl -s -X PUT "http://$CONSUL_ADDR/v1/kv/vault/root_token" -d "$ROOT_TOKEN" >/dev/null 2>&1 && \
      echo "Root token saved to Consul" || echo "Warning: Failed to save root token to Consul"
  elif command -v wget >/dev/null 2>&1; then
    wget -q -O /dev/null --method=PUT --body-data="$UNSEAL_KEY" "http://$CONSUL_ADDR/v1/kv/vault/unseal_key" 2>/dev/null && \
      echo "Unseal key saved to Consul" || echo "Warning: Failed to save unseal key to Consul"
    wget -q -O /dev/null --method=PUT --body-data="$ROOT_TOKEN" "http://$CONSUL_ADDR/v1/kv/vault/root_token" 2>/dev/null && \
      echo "Root token saved to Consul" || echo "Warning: Failed to save root token to Consul"
  elif command -v nc >/dev/null 2>&1; then
    # 使用 nc 发送 HTTP PUT 请求
    (echo -e "PUT /v1/kv/vault/unseal_key HTTP/1.1\r\nHost: $CONSUL_HOST:$CONSUL_PORT\r\nContent-Length: ${#UNSEAL_KEY}\r\n\r\n$UNSEAL_KEY" | nc "$CONSUL_HOST" "$CONSUL_PORT" >/dev/null 2>&1) && \
      echo "Unseal key saved to Consul" || echo "Warning: Failed to save unseal key to Consul"
    (echo -e "PUT /v1/kv/vault/root_token HTTP/1.1\r\nHost: $CONSUL_HOST:$CONSUL_PORT\r\nContent-Length: ${#ROOT_TOKEN}\r\n\r\n$ROOT_TOKEN" | nc "$CONSUL_HOST" "$CONSUL_PORT" >/dev/null 2>&1) && \
      echo "Root token saved to Consul" || echo "Warning: Failed to save root token to Consul"
  else
    echo "Warning: No HTTP client found (curl/wget/nc), cannot save to Consul"
  fi
  
  # 使用 unseal key 解锁 Vault
  echo "Unsealing Vault..."
  export VAULT_TOKEN="$ROOT_TOKEN"
  UNSEAL_OUTPUT=$(vault operator unseal "$UNSEAL_KEY" 2>&1)
  
  if [ $? -ne 0 ]; then
    echo "Error unsealing Vault: $UNSEAL_OUTPUT"
    exit 1
  fi
  
  echo "Vault initialized and unsealed successfully"
  echo "Root Token: $ROOT_TOKEN"
  echo "Unseal Key: $UNSEAL_KEY"
else
  echo "Vault already initialized"
  
  # 如果已初始化但未解锁，尝试使用保存的 unseal key
  VAULT_STATUS_CHECK=$(vault status 2>&1)
  if echo "$VAULT_STATUS_CHECK" | grep -q "Sealed.*true"; then
    echo "Vault is sealed, attempting to unseal..."
    
    # 尝试从多个位置获取 unseal key
    UNSEAL_KEY=""
    
    # 1. 从本地文件
    if [ -f /vault/data/unseal_key.txt ]; then
      UNSEAL_KEY=$(cat /vault/data/unseal_key.txt)
      echo "Found unseal key in /vault/data/unseal_key.txt"
    fi
    
    # 2. 从共享位置
    if [ -z "$UNSEAL_KEY" ] && [ -f /vault/data/shared/unseal_key.txt ]; then
      UNSEAL_KEY=$(cat /vault/data/shared/unseal_key.txt)
      echo "Found unseal key in /vault/data/shared/unseal_key.txt"
    fi
    
    # 3. 从环境变量
    if [ -z "$UNSEAL_KEY" ] && [ -n "$VAULT_UNSEAL_KEY" ]; then
      UNSEAL_KEY="$VAULT_UNSEAL_KEY"
      echo "Using unseal key from environment variable"
    fi
    
    # 4. 尝试从 Consul 获取（如果可能）
    if [ -z "$UNSEAL_KEY" ]; then
      CONSUL_ADDR="${CONSUL_ADDR:-consul:8500}"
      CONSUL_HOST=$(echo "$CONSUL_ADDR" | cut -d: -f1)
      CONSUL_PORT=$(echo "$CONSUL_ADDR" | cut -d: -f2)
      
      if command -v curl >/dev/null 2>&1; then
        CONSUL_KEY=$(curl -s "http://$CONSUL_ADDR/v1/kv/vault/unseal_key?raw" 2>/dev/null || echo "")
        if [ -n "$CONSUL_KEY" ]; then
          UNSEAL_KEY="$CONSUL_KEY"
          echo "Found unseal key in Consul (via curl)"
          # 同时保存到本地文件以便下次使用
          echo "$UNSEAL_KEY" > /vault/data/unseal_key.txt 2>/dev/null || true
        fi
      elif command -v wget >/dev/null 2>&1; then
        CONSUL_KEY=$(wget -q -O- "http://$CONSUL_ADDR/v1/kv/vault/unseal_key?raw" 2>/dev/null || echo "")
        if [ -n "$CONSUL_KEY" ]; then
          UNSEAL_KEY="$CONSUL_KEY"
          echo "Found unseal key in Consul (via wget)"
          # 同时保存到本地文件以便下次使用
          echo "$UNSEAL_KEY" > /vault/data/unseal_key.txt 2>/dev/null || true
        fi
      elif command -v nc >/dev/null 2>&1; then
        # 使用 nc 发送 HTTP GET 请求
        CONSUL_KEY=$(echo -e "GET /v1/kv/vault/unseal_key?raw HTTP/1.1\r\nHost: $CONSUL_HOST:$CONSUL_PORT\r\n\r\n" | nc "$CONSUL_HOST" "$CONSUL_PORT" 2>/dev/null | grep -v "^HTTP" | tail -n +2 | tr -d '\r\n')
        if [ -n "$CONSUL_KEY" ] && [ "$CONSUL_KEY" != "404" ]; then
          UNSEAL_KEY="$CONSUL_KEY"
          echo "Found unseal key in Consul (via nc)"
          # 同时保存到本地文件以便下次使用
          echo "$UNSEAL_KEY" > /vault/data/unseal_key.txt 2>/dev/null || true
        fi
      elif command -v consul >/dev/null 2>&1; then
        CONSUL_KEY=$(consul kv get vault/unseal_key 2>/dev/null || echo "")
        if [ -n "$CONSUL_KEY" ]; then
          UNSEAL_KEY="$CONSUL_KEY"
          echo "Found unseal key in Consul (via consul CLI)"
          # 同时保存到本地文件以便下次使用
          echo "$UNSEAL_KEY" > /vault/data/unseal_key.txt 2>/dev/null || true
        fi
      fi
    fi
    
    if [ -n "$UNSEAL_KEY" ]; then
      echo "Unsealing Vault..."
      UNSEAL_OUTPUT=$(vault operator unseal "$UNSEAL_KEY" 2>&1)
      if [ $? -eq 0 ]; then
        echo "Vault unsealed successfully"
      else
        echo "Error unsealing Vault: $UNSEAL_OUTPUT"
        echo "The unseal key may be incorrect"
        exit 1
      fi
    else
      echo "ERROR: Vault is sealed but no unseal key found!"
      echo ""
      echo "Options to resolve this:"
      echo ""
      echo "Option 1: Provide the unseal key"
      echo "  - Place it in /vault/data/unseal_key.txt"
      echo "  - Set environment variable VAULT_UNSEAL_KEY in docker-compose.yml"
      echo "  - Store it in Consul at key 'vault/unseal_key'"
      echo ""
      echo "Option 2: Reset Vault (for test environments only)"
      echo "  If VAULT_AUTO_RESET=true is set, Vault data will be deleted and re-initialized"
      echo "  WARNING: This will delete all existing Vault data!"
      echo ""
      
      # 检查是否允许自动重置
      if [ "$VAULT_AUTO_RESET" = "true" ]; then
        echo "VAULT_AUTO_RESET=true detected. Resetting Vault..."
        echo "Deleting Vault data from Consul..."
        
        # 尝试通过 Consul API 删除数据
        CONSUL_ADDR="${CONSUL_ADDR:-consul:8500}"
        CONSUL_HOST=$(echo "$CONSUL_ADDR" | cut -d: -f1)
        CONSUL_PORT=$(echo "$CONSUL_ADDR" | cut -d: -f2)
        
        DELETE_SUCCESS=0
        if command -v curl >/dev/null 2>&1; then
          DELETE_RESULT=$(curl -s -X DELETE "http://$CONSUL_ADDR/v1/kv/vault/?recurse" 2>&1)
          DELETE_SUCCESS=$?
        elif command -v wget >/dev/null 2>&1; then
          DELETE_RESULT=$(wget -q -O- --method=DELETE "http://$CONSUL_ADDR/v1/kv/vault/?recurse" 2>&1)
          DELETE_SUCCESS=$?
        elif command -v nc >/dev/null 2>&1; then
          # 使用 nc 发送 HTTP DELETE 请求
          DELETE_RESULT=$(echo -e "DELETE /v1/kv/vault/?recurse HTTP/1.1\r\nHost: $CONSUL_HOST:$CONSUL_PORT\r\n\r\n" | nc "$CONSUL_HOST" "$CONSUL_PORT" 2>&1)
          # 检查响应是否包含 200 OK
          if echo "$DELETE_RESULT" | grep -q "200 OK"; then
            DELETE_SUCCESS=0
          else
            DELETE_SUCCESS=1
          fi
        else
          DELETE_RESULT="Neither wget nor nc found"
          DELETE_SUCCESS=1
        fi
        
        if [ $DELETE_SUCCESS -eq 0 ]; then
          echo "Vault data deleted from Consul successfully."
          echo "Restarting Vault process to detect the change..."
          
          # 找到 Vault 进程并优雅地重启它
          VAULT_PID=$(pgrep -f "vault server" | head -1)
          if [ -n "$VAULT_PID" ]; then
            echo "Stopping Vault process (PID: $VAULT_PID)..."
            # 发送 TERM 信号让 Vault 优雅关闭
            kill -TERM "$VAULT_PID" 2>/dev/null || kill "$VAULT_PID" 2>/dev/null || true
            # 等待进程退出
            for i in $(seq 1 10); do
              if ! kill -0 "$VAULT_PID" 2>/dev/null; then
                break
              fi
              sleep 1
            done
            # 如果还在运行，强制杀死
            if kill -0 "$VAULT_PID" 2>/dev/null; then
              kill -9 "$VAULT_PID" 2>/dev/null || true
            fi
            sleep 2
            
            # 重新启动 Vault
            echo "Restarting Vault server..."
            vault server -config=/vault/config/vault.hcl &
            sleep 8
          else
            echo "Warning: Could not find Vault process, waiting for it to detect changes..."
            sleep 5
          fi
          
          # 等待 Vault 检测到数据被删除（最多等待 30 秒）
          for i in $(seq 1 30); do
            sleep 1
            VAULT_STATUS_AFTER_RESET=$(vault status 2>&1)
            if ! echo "$VAULT_STATUS_AFTER_RESET" | grep -q "Initialized.*true"; then
              echo "Vault is now uninitialized. Re-initializing..."
              
              # 执行初始化
              INIT_OUTPUT=$(vault operator init -key-shares=1 -key-threshold=1 -format=json 2>&1)
              
              if [ $? -ne 0 ]; then
                echo "Error re-initializing Vault: $INIT_OUTPUT"
                exit 1
              fi
              
              # 提取 root token 和 unseal key（重用之前的提取逻辑）
              INIT_JSON=$(echo "$INIT_OUTPUT" | tr -d '\n' | tr -d ' ')
              ROOT_TOKEN=$(echo "$INIT_JSON" | sed 's/.*"root_token":"\([^"]*\)".*/\1/')
              UNSEAL_KEY=$(echo "$INIT_JSON" | sed 's/.*"unseal_keys_b64":\["\([^"]*\)".*/\1/')
              
              if [ -z "$ROOT_TOKEN" ] || [ "$ROOT_TOKEN" = "$INIT_JSON" ]; then
                ROOT_TOKEN=$(echo "$INIT_OUTPUT" | grep '"root_token"' | sed 's/.*"root_token"[^"]*"\([^"]*\)".*/\1/')
              fi
              
              if [ -z "$UNSEAL_KEY" ] || [ "$UNSEAL_KEY" = "$INIT_JSON" ]; then
                UNSEAL_KEY=$(echo "$INIT_OUTPUT" | grep -A 2 '"unseal_keys_b64"' | grep -o '"[^"]*"' | head -1 | tr -d '"')
              fi
              
              if [ -z "$ROOT_TOKEN" ] || [ -z "$UNSEAL_KEY" ] || [ "$ROOT_TOKEN" = "$INIT_JSON" ] || [ "$UNSEAL_KEY" = "$INIT_JSON" ]; then
                echo "Error: Failed to extract root token or unseal key"
                exit 1
              fi
              
              # 保存到文件和 Consul
              echo "$ROOT_TOKEN" > /vault/data/root_token.txt
              echo "$UNSEAL_KEY" > /vault/data/unseal_key.txt
              
              # 保存到 Consul
              if command -v curl >/dev/null 2>&1; then
                curl -s -X PUT "http://$CONSUL_ADDR/v1/kv/vault/unseal_key" -d "$UNSEAL_KEY" >/dev/null 2>&1
                curl -s -X PUT "http://$CONSUL_ADDR/v1/kv/vault/root_token" -d "$ROOT_TOKEN" >/dev/null 2>&1
              elif command -v wget >/dev/null 2>&1; then
                wget -q -O /dev/null --method=PUT --body-data="$UNSEAL_KEY" "http://$CONSUL_ADDR/v1/kv/vault/unseal_key" 2>/dev/null
                wget -q -O /dev/null --method=PUT --body-data="$ROOT_TOKEN" "http://$CONSUL_ADDR/v1/kv/vault/root_token" 2>/dev/null
              elif command -v nc >/dev/null 2>&1; then
                (echo -e "PUT /v1/kv/vault/unseal_key HTTP/1.1\r\nHost: $CONSUL_HOST:$CONSUL_PORT\r\nContent-Length: ${#UNSEAL_KEY}\r\n\r\n$UNSEAL_KEY" | nc "$CONSUL_HOST" "$CONSUL_PORT" >/dev/null 2>&1)
                (echo -e "PUT /v1/kv/vault/root_token HTTP/1.1\r\nHost: $CONSUL_HOST:$CONSUL_PORT\r\nContent-Length: ${#ROOT_TOKEN}\r\n\r\n$ROOT_TOKEN" | nc "$CONSUL_HOST" "$CONSUL_PORT" >/dev/null 2>&1)
              fi
              
              # 解锁 Vault
              export VAULT_TOKEN="$ROOT_TOKEN"
              vault operator unseal "$UNSEAL_KEY"
              
              echo "Vault re-initialized and unsealed successfully"
              break
            fi
          done
          
          # 如果 30 秒后仍然显示为已初始化，提示重启
          VAULT_FINAL_CHECK=$(vault status 2>&1)
          if echo "$VAULT_FINAL_CHECK" | grep -q "Initialized.*true"; then
            echo "Warning: Vault still shows as initialized after reset."
            echo "You may need to restart the container: docker restart vault-1"
            exit 0
          fi
        else
          echo "Failed to delete Vault data: $DELETE_RESULT"
          echo "You may need to delete it manually:"
          echo "  docker exec consul consul kv delete -recurse vault/"
          exit 1
        fi
      else
        echo "To enable auto-reset, set VAULT_AUTO_RESET=true in docker-compose.yml"
        echo "Or manually reset by running:"
        echo "  docker exec consul consul kv delete -recurse vault/"
        echo "  docker restart vault-1"
        exit 1
      fi
    fi
  else
    echo "Vault is already unsealed"
  fi
  
  # 使用保存的 root token 或默认值
  if [ -f /vault/data/root_token.txt ]; then
    export VAULT_TOKEN=$(cat /vault/data/root_token.txt)
    echo "Using root token from /vault/data/root_token.txt"
  elif [ -f /vault/data/shared/root_token.txt ]; then
    export VAULT_TOKEN=$(cat /vault/data/shared/root_token.txt)
    echo "Using root token from /vault/data/shared/root_token.txt"
  elif [ -n "$VAULT_TOKEN" ]; then
    echo "Using root token from environment variable"
  else
    echo "WARNING: No root token found, some operations may fail"
    echo "Please set VAULT_TOKEN environment variable or place token in /vault/data/root_token.txt"
  fi
fi

# 等待 Vault 完全就绪
echo "Waiting for Vault to be fully ready..."
sleep 3

# 检查 Vault 是否已解锁
VAULT_FINAL_STATUS=$(vault status 2>&1)
if echo "$VAULT_FINAL_STATUS" | grep -q "Sealed.*true"; then
  echo "ERROR: Vault is still sealed!"
  echo "Vault status:"
  echo "$VAULT_FINAL_STATUS"
  echo ""
  echo "Cannot proceed with authentication setup while Vault is sealed."
  echo "Please unseal Vault manually or provide the unseal key."
  exit 1
fi

echo "Vault is unsealed and ready"

# 启用 userpass 认证
echo "Setting up authentication..."
vault auth enable userpass 2>&1 || echo "userpass auth may already be enabled"

# 创建 admin 用户
vault write auth/userpass/users/admin password=admin policies=admin 2>&1 || echo "admin user may already exist"

# 如果 admin policy 不存在，创建它
if ! vault policy read admin >/dev/null 2>&1; then
  if [ -f /vault/init/admin-policy.hcl ]; then
    vault policy write admin /vault/init/admin-policy.hcl
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

