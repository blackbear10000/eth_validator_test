#!/bin/sh

# 重置 Vault 的脚本
# 此脚本会删除 Consul 中的 Vault 数据，使 Vault 可以重新初始化
# 警告：这将删除所有 Vault 数据！

echo "WARNING: This will delete all Vault data from Consul!"
echo "Press Ctrl+C to cancel, or wait 5 seconds to continue..."
sleep 5

CONSUL_ADDR="${CONSUL_ADDR:-consul:8500}"

echo "Connecting to Consul at $CONSUL_ADDR..."

# 检查 Consul 是否可访问
if ! nc -z $(echo $CONSUL_ADDR | cut -d: -f1) $(echo $CONSUL_ADDR | cut -d: -f2) 2>/dev/null; then
  echo "Error: Cannot connect to Consul at $CONSUL_ADDR"
  exit 1
fi

# 删除 Vault 数据
echo "Deleting Vault data from Consul..."
curl -X DELETE "http://$CONSUL_ADDR/v1/kv/vault/?recurse" 2>/dev/null || {
  echo "Error: Failed to delete Vault data from Consul"
  echo "You may need to delete it manually using:"
  echo "  consul kv delete -recurse vault/"
  exit 1
}

echo "Vault data deleted successfully!"
echo "Vault will be re-initialized on next startup."

