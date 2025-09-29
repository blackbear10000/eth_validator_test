ui = true
disable_mlock = true

storage "consul" {
  address = "consul:8500"
  path    = "vault/"
}

listener "tcp" {
  address = "0.0.0.0:8200"
  tls_disable = true
}

api_addr = "http://0.0.0.0:8200"
cluster_addr = "http://0.0.0.0:8201"