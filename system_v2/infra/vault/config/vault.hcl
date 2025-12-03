ui = true

storage "consul" {
  address = "consul:8500"
  path    = "vault/"
}

listener "tcp" {
  address     = "0.0.0.0:8200"
  tls_disable = 1
}

# 使用容器名作为 API 地址，这样 Consul 可以正确注册服务
api_addr = "http://vault-1:8200"
cluster_addr = "http://vault-1:8201"

# 服务注册配置
service_registration "consul" {
  address = "consul:8500"
  service = "vault"
  service_address = "vault-1"
}

# 开发模式（生产环境需要移除）
disable_mlock = true

