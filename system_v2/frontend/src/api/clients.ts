import apiClient from './client'

export interface ClientInstance {
  id: number
  name: string
  client_type: string
  beacon_api_url?: string
  grpc_endpoint?: string
  web3signer_url: string
  is_active: boolean
  status: string
  created_at: string
  key_count: number
}

export const clientsApi = {
  // 创建客户端
  create: (params: {
    name: string
    client_type: string
    beacon_api_url?: string
    grpc_endpoint?: string
    web3signer_url?: string
    notes?: string
  }) => apiClient.post('/clients', params),

  // 列出客户端
  list: (clientType?: string, isActive?: boolean) =>
    apiClient.get('/clients', { 
      params: { 
        ...(clientType ? { client_type: clientType } : {}),
        ...(isActive !== undefined ? { is_active: isActive } : {})
      } 
    }),

  // 分配密钥
  assignKeys: (clientId: number, pubkeys: string[]) =>
    apiClient.put(`/clients/${clientId}/keys`, { pubkeys }),

  // 重新加载密钥
  reloadKeys: (clientId: number) =>
    apiClient.post(`/clients/${clientId}/reload-keys`),

  // 启动客户端
  start: (clientId: number) =>
    apiClient.post(`/clients/${clientId}/start`),

  // 停止客户端
  stop: (clientId: number) =>
    apiClient.post(`/clients/${clientId}/stop`),

  // 暂停客户端容器
  pause: (clientId: number) =>
    apiClient.post(`/clients/${clientId}/pause`),

  // 恢复（取消暂停）客户端容器
  unpause: (clientId: number) =>
    apiClient.post(`/clients/${clientId}/unpause`),

  // 销毁（停止并删除）客户端容器
  destroy: (clientId: number) =>
    apiClient.post(`/clients/${clientId}/destroy`),

  // 获取客户端状态
  getStatus: (clientId: number) =>
    apiClient.get(`/clients/${clientId}/status`),

  // 获取客户端日志
  getLogs: (clientId: number, lines?: number) =>
    apiClient.get(`/clients/${clientId}/logs`, { params: { lines } }),

  // 获取客户端详情
  get: (clientId: number) =>
    apiClient.get(`/clients/${clientId}`),

  // 更新客户端
  update: (clientId: number, params: {
    name?: string
    beacon_api_url?: string
    grpc_endpoint?: string
    web3signer_url?: string
    notes?: string
    is_active?: boolean
  }) => apiClient.put(`/clients/${clientId}`, params),

  // 删除客户端
  delete: (clientId: number, hardDelete?: boolean) =>
    apiClient.delete(`/clients/${clientId}`, { params: { hard_delete: hardDelete } }),

  // 同步密钥到 Validator Client
  syncKeys: (clientId: number) =>
    apiClient.post(`/clients/${clientId}/sync-keys`),

  // 获取客户端密钥列表
  getKeys: (clientId: number) =>
    apiClient.get(`/clients/${clientId}/keys`),

  // 删除客户端密钥
  removeKeys: (clientId: number, pubkeys: string[]) =>
    apiClient.delete(`/clients/${clientId}/keys`, { data: { pubkeys } }),

  // 获取 validator client 实际加载的密钥列表
  getActualKeys: (clientId: number) =>
    apiClient.get(`/clients/${clientId}/keys/actual`),

  // 获取密钥对比信息（数据库 vs validator client）
  getKeysCompare: (clientId: number) =>
    apiClient.get(`/clients/${clientId}/keys/compare`),
}

