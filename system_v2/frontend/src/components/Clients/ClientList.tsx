import React, { useState, useEffect } from 'react'
import {
  Table,
  Card,
  Button,
  Space,
  message,
  Modal,
  Form,
  Input,
  Select,
  Tag,
  Typography,
  Popconfirm,
  Switch,
  Alert,
  Spin,
  Tabs,
} from 'antd'
import {
  PlusOutlined,
  PlayCircleOutlined,
  StopOutlined,
  KeyOutlined,
  EditOutlined,
  DeleteOutlined,
  PauseCircleOutlined,
  CaretRightOutlined,
  CloseCircleOutlined,
  FileTextOutlined,
} from '@ant-design/icons'
import { clientsApi, ClientInstance } from '../../api/clients'
import { keysApi } from '../../api/keys'
import { networkApi } from '../../api/network'
import ClientKeyManagementModal from './ClientKeyManagementModal'

const { Title } = Typography
const { Option } = Select

const ClientList: React.FC = () => {
  const [clients, setClients] = useState<ClientInstance[]>([])
  const [loading, setLoading] = useState(false)
  const [activeTab, setActiveTab] = useState<string>('active')
  const [createModalVisible, setCreateModalVisible] = useState(false)
  const [editModalVisible, setEditModalVisible] = useState(false)
  const [keyManagementModalVisible, setKeyManagementModalVisible] = useState(false)
  const [selectedClient, setSelectedClient] = useState<ClientInstance | null>(null)
  const [clientStatuses, setClientStatuses] = useState<Record<number, any>>({})
  const [startingClients, setStartingClients] = useState<Set<number>>(new Set())
  const [logsModalVisible, setLogsModalVisible] = useState(false)
  const [selectedClientForLogs, setSelectedClientForLogs] = useState<number | null>(null)
  const [clientLogs, setClientLogs] = useState<string[]>([])
  const [loadingLogs, setLoadingLogs] = useState(false)
  const [form] = Form.useForm()
  const [editForm] = Form.useForm()

  const loadClients = async () => {
    setLoading(true)
    try {
      // 根据当前 tab 加载不同的客户端列表
      const isActive = activeTab === 'active'
      const response = await clientsApi.list(undefined, isActive) as any
      setClients(response || [])
      
      // 加载每个客户端的状态
      for (const client of response || []) {
        loadClientStatus(client.id)
      }
    } catch (error: any) {
      message.error(`加载客户端列表失败: ${error.message}`)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadClients()
  }, [activeTab])

  const loadClientStatus = async (clientId: number) => {
    try {
      const status = await clientsApi.getStatus(clientId) as any
      setClientStatuses((prev) => ({
        ...prev,
        [clientId]: status,
      }))
    } catch (error) {
      // 忽略错误，可能客户端未运行
    }
  }

  const loadRecommendedUrls = async () => {
    try {
      const networkInfo = await networkApi.getInfo() as any
      const rpcEndpoints = await networkApi.getRpcEndpoints()
      const recommendedValues: any = {}
      
      // 推荐 Web3Signer URL（使用默认值，因为这是系统内部服务）
      recommendedValues.web3signer_url = 'http://haproxy:9002' // HAProxy
      
      // 推荐 gRPC endpoint（从网络服务获取，特别是对于 Prysm）
      if (rpcEndpoints?.grpc_endpoint) {
        recommendedValues.grpc_endpoint = rpcEndpoints.grpc_endpoint
      }
      
      if (Object.keys(recommendedValues).length > 0) {
        form.setFieldsValue(recommendedValues)
        message.info('已自动填充推荐的 API URL（包括 gRPC 端点）')
      }
    } catch (error) {
      // 忽略错误，不影响用户手动输入
      console.warn('无法获取推荐的 API URL:', error)
    }
  }

  const handleCreate = async (values: any) => {
    try {
      await clientsApi.create(values)
      message.success('客户端创建成功')
      setCreateModalVisible(false)
      form.resetFields()
      loadClients()
    } catch (error: any) {
      message.error(`创建客户端失败: ${error.message}`)
    }
  }

  const handleEdit = async (client: ClientInstance) => {
    setSelectedClient(client)
    editForm.setFieldsValue({
      name: client.name,
      grpc_endpoint: client.grpc_endpoint,
      web3signer_url: client.web3signer_url || 'http://haproxy:9002',
      is_active: client.is_active,
    })
    setEditModalVisible(true)
  }

  const handleUpdate = async (values: any) => {
    if (!selectedClient) return

    try {
      await clientsApi.update(selectedClient.id, values)
      message.success('客户端更新成功')
      setEditModalVisible(false)
      editForm.resetFields()
      setSelectedClient(null)
      loadClients()
    } catch (error: any) {
      message.error(`更新客户端失败: ${error.message}`)
    }
  }

  const handleDelete = async (clientId: number) => {
    try {
      await clientsApi.delete(clientId, false)
      message.success('客户端已删除')
      loadClients()
    } catch (error: any) {
      message.error(`删除客户端失败: ${error.message}`)
    }
  }

  const handleRestore = async (clientId: number) => {
    try {
      await clientsApi.update(clientId, { is_active: true })
      message.success('客户端已恢复')
      loadClients()
    } catch (error: any) {
      message.error(`恢复客户端失败: ${error.message}`)
    }
  }

  const handleRemoveKey = async (clientId: number, pubkey: string) => {
    try {
      await clientsApi.removeKeys(clientId, [pubkey])
      message.success('密钥已移除')
      // 重新加载密钥列表
      const keys = await clientsApi.getKeys(clientId) as any
      setClientKeys(keys || [])
      loadClients() // 刷新客户端列表（更新密钥数量）
    } catch (error: any) {
      message.error(`移除密钥失败: ${error.message}`)
    }
  }

  const handleManageKeys = (clientId: number) => {
    setSelectedClient(clients.find((c) => c.id === clientId) || null)
    setKeyManagementModalVisible(true)
  }

  const handleStart = async (clientId: number) => {
    setStartingClients((prev) => new Set(prev).add(clientId))
    try {
      const result = await clientsApi.start(clientId) as any
      
      // 检查返回的状态
      if (result.status && !result.status.is_running) {
        // 容器启动失败
        const errorMsg = result.message || '容器启动失败'
        const errorLogs = result.error_logs || result.status.error
        message.error(errorMsg, 10)
        
        // 如果有错误日志，显示详细信息
        if (errorLogs) {
          Modal.error({
            title: '容器启动失败',
            width: 800,
            content: (
              <div>
                <p>{errorMsg}</p>
                <p style={{ marginTop: 16, fontWeight: 'bold' }}>错误日志：</p>
                <pre style={{ 
                  background: '#f5f5f5', 
                  padding: 12, 
                  borderRadius: 4,
                  maxHeight: '400px',
                  overflow: 'auto',
                  fontSize: '12px',
                  whiteSpace: 'pre-wrap',
                  wordBreak: 'break-word'
                }}>
                  {typeof errorLogs === 'string' ? errorLogs : JSON.stringify(errorLogs, null, 2)}
                </pre>
              </div>
            ),
          })
        }
      } else {
      message.success('客户端启动成功')
      }
      
      // 立即刷新一次状态
      await loadClientStatus(clientId)
      
      // 启动后自动刷新状态（每2秒一次，持续10秒）
      let refreshCount = 0
      const maxRefreshes = 5
      const refreshInterval = setInterval(async () => {
        refreshCount++
        await loadClientStatus(clientId)
        
        // 使用最新的状态检查
        const currentStatus = await clientsApi.getStatus(clientId) as any
        if (currentStatus?.is_running || refreshCount >= maxRefreshes) {
          clearInterval(refreshInterval)
          setStartingClients((prev) => {
            const newSet = new Set(prev)
            newSet.delete(clientId)
            return newSet
          })
        }
      }, 2000)
    } catch (error: any) {
      setStartingClients((prev) => {
        const newSet = new Set(prev)
        newSet.delete(clientId)
        return newSet
      })
      
      // 解析错误详情
      const errorDetail = error.response?.data?.detail
      let errorMsg = error.message || '启动客户端失败'
      
      if (errorDetail) {
        if (typeof errorDetail === 'string') {
          errorMsg = errorDetail
        } else if (errorDetail.error) {
          errorMsg = errorDetail.error
          // 如果有错误日志，显示详细信息
          if (errorDetail.error_logs) {
            Modal.error({
              title: '容器启动失败',
              width: 800,
              content: (
                <div>
                  <p>{errorDetail.error}</p>
                  {errorDetail.config_file_path && (
                    <p style={{ marginTop: 8, fontSize: '12px', color: '#666' }}>
                      配置文件路径: {errorDetail.config_file_path}
                    </p>
                  )}
                  <p style={{ marginTop: 16, fontWeight: 'bold' }}>错误日志：</p>
                  <pre style={{ 
                    background: '#f5f5f5', 
                    padding: 12, 
                    borderRadius: 4,
                    maxHeight: '400px',
                    overflow: 'auto',
                    fontSize: '12px',
                    whiteSpace: 'pre-wrap',
                    wordBreak: 'break-word'
                  }}>
                    {errorDetail.error_logs}
                  </pre>
                </div>
              ),
            })
            return
          }
        }
      }
      
      message.error(`启动客户端失败: ${errorMsg}`, 10)
    }
  }

  const handleStop = async (clientId: number) => {
    try {
      await clientsApi.stop(clientId)
      message.success('客户端已停止')
      setTimeout(() => {
        loadClientStatus(clientId)
      }, 1000)
    } catch (error: any) {
      message.error(`停止客户端失败: ${error.message}`)
    }
  }

  const handlePause = async (clientId: number) => {
    try {
      await clientsApi.pause(clientId)
      message.success('客户端已暂停')
      setTimeout(() => {
        loadClientStatus(clientId)
      }, 1000)
    } catch (error: any) {
      message.error(`暂停客户端失败: ${error.message}`)
    }
  }

  const handleUnpause = async (clientId: number) => {
    try {
      await clientsApi.unpause(clientId)
      message.success('客户端已恢复')
      setTimeout(() => {
        loadClientStatus(clientId)
      }, 1000)
    } catch (error: any) {
      message.error(`恢复客户端失败: ${error.message}`)
    }
  }

  const handleDestroy = async (clientId: number) => {
    try {
      await clientsApi.destroy(clientId)
      message.success('客户端容器已销毁')
      setTimeout(() => {
        loadClientStatus(clientId)
      }, 1000)
    } catch (error: any) {
      message.error(`销毁客户端容器失败: ${error.message}`)
    }
  }


  const getStatusTag = (clientId: number) => {
    const status = clientStatuses[clientId]
    if (!status) {
      if (startingClients.has(clientId)) {
        return <Tag color="processing">启动中...</Tag>
      }
      return <Tag>未知</Tag>
    }
    if (status.is_running) {
      return <Tag color="success">运行中</Tag>
    }
    if (status.state === 'paused') {
      return <Tag color="warning">已暂停</Tag>
    }
    if (status.exit_code !== null && status.exit_code !== undefined) {
      return <Tag color="error">已退出 ({status.exit_code})</Tag>
    }
    if (status.error) {
      return <Tag color="error">错误</Tag>
    }
    return <Tag>已停止</Tag>
  }

  const handleViewLogs = async (clientId: number) => {
    setSelectedClientForLogs(clientId)
    setLogsModalVisible(true)
    await loadClientLogs(clientId)
  }

  const loadClientLogs = async (clientId: number) => {
    setLoadingLogs(true)
    try {
      const result = await clientsApi.getLogs(clientId, 100) as any
      if (result.logs) {
        setClientLogs(result.logs)
      } else if (result.error) {
        setClientLogs([`错误: ${result.error}`])
      } else {
        setClientLogs(['暂无日志'])
      }
    } catch (error: any) {
      message.error(`加载日志失败: ${error.message}`)
      setClientLogs([`加载日志失败: ${error.message}`])
    } finally {
      setLoadingLogs(false)
    }
  }

  const columns = [
    {
      title: 'ID',
      dataIndex: 'id',
      key: 'id',
      width: 80,
    },
    {
      title: '名称',
      dataIndex: 'name',
      key: 'name',
      width: 150,
    },
    {
      title: '类型',
      dataIndex: 'client_type',
      key: 'client_type',
      width: 120,
      render: (type: string) => <Tag>{type}</Tag>,
    },
    {
      title: '状态',
      key: 'status',
      width: 100,
      render: (_: any, record: ClientInstance) => getStatusTag(record.id),
    },
    {
      title: '密钥数',
      dataIndex: 'key_count',
      key: 'key_count',
      width: 100,
    },
    {
      title: '操作',
      key: 'action',
      width: 300,
      render: (_: any, record: ClientInstance) => {
        const status = clientStatuses[record.id]
        const isRunning = status?.is_running
        const isPaused = status?.state === 'paused'

        return (
          <Space>
            {isRunning && !isPaused ? (
              <>
                <Popconfirm
                  title="确定要停止客户端吗？"
                  onConfirm={() => handleStop(record.id)}
                >
                  <Button size="small" danger icon={<StopOutlined />}>
                    停止
                  </Button>
                </Popconfirm>
                <Popconfirm
                  title="确定要暂停客户端吗？"
                  description="暂停后容器会暂停运行，但不会删除"
                  onConfirm={() => handlePause(record.id)}
                >
                  <Button size="small" icon={<PauseCircleOutlined />}>
                    暂停
                  </Button>
                </Popconfirm>
              </>
            ) : isPaused ? (
              <>
                <Button
                  size="small"
                  type="primary"
                  icon={<CaretRightOutlined />}
                  onClick={() => handleUnpause(record.id)}
                >
                  恢复
                </Button>
              <Popconfirm
                title="确定要停止客户端吗？"
                onConfirm={() => handleStop(record.id)}
              >
                <Button size="small" danger icon={<StopOutlined />}>
                  停止
                </Button>
              </Popconfirm>
              </>
            ) : (
              <Button
                size="small"
                type="primary"
                icon={<PlayCircleOutlined />}
                onClick={() => handleStart(record.id)}
                loading={startingClients.has(record.id)}
              >
                启动
              </Button>
            )}
            <Popconfirm
              title="确定要销毁容器吗？"
              description="销毁会停止并删除容器，但不会删除客户端配置。容器销毁后可以重新启动。"
              onConfirm={() => handleDestroy(record.id)}
            >
              <Button
                size="small"
                danger
                icon={<CloseCircleOutlined />}
              >
                销毁
              </Button>
            </Popconfirm>
            {activeTab === 'active' && (
              <>
                <Button
                  size="small"
                  icon={<KeyOutlined />}
                  onClick={() => handleManageKeys(record.id)}
                >
                  管理密钥
                </Button>
                <Button
                  size="small"
                  icon={<FileTextOutlined />}
                  onClick={() => handleViewLogs(record.id)}
                >
                  查看日志
                </Button>
                <Button
                  size="small"
                  icon={<EditOutlined />}
                  onClick={() => handleEdit(record)}
                >
                  编辑
                </Button>
              </>
            )}
            {activeTab === 'active' ? (
              <Popconfirm
                title="确定要删除这个客户端吗？"
                description="删除后可以恢复（软删除），如果有关联的密钥，将自动释放"
                onConfirm={() => handleDelete(record.id)}
              >
                <Button
                  size="small"
                  danger
                  icon={<DeleteOutlined />}
                >
                  删除
                </Button>
              </Popconfirm>
            ) : (
              <Button
                size="small"
                type="primary"
                icon={<ReloadOutlined />}
                onClick={() => handleRestore(record.id)}
              >
                恢复
              </Button>
            )}
          </Space>
        )
      },
    },
  ]

  return (
    <div>
      <Title level={2}>客户端管理</Title>

      <Card
        title="客户端列表"
        extra={
          <Button
            type="primary"
            icon={<PlusOutlined />}
            onClick={() => setCreateModalVisible(true)}
          >
            创建客户端
          </Button>
        }
      >
        <Tabs
          activeKey={activeTab}
          onChange={setActiveTab}
          items={[
            {
              key: 'active',
              label: '激活的客户端',
            },
            {
              key: 'deleted',
              label: '已删除的客户端',
            },
          ]}
        />
        {/* 显示有错误的客户端 */}
        {clients.some((client) => {
          const status = clientStatuses[client.id]
          return status && (status.error || (status.exit_code !== null && status.exit_code !== undefined))
        }) && (
          <Alert
            message="部分客户端容器异常"
            description={
              <div>
                {clients
                  .filter((client) => {
                    const status = clientStatuses[client.id]
                    return status && (status.error || (status.exit_code !== null && status.exit_code !== undefined))
                  })
                  .map((client) => {
                    const status = clientStatuses[client.id]
                    return (
                      <div key={client.id} style={{ marginTop: 8 }}>
                        <strong>{client.name}</strong>: {status.error || `退出代码 ${status.exit_code}`}
                        {' '}
                        <Button
                          type="link"
                          size="small"
                          icon={<FileTextOutlined />}
                          onClick={() => handleViewLogs(client.id)}
                        >
                          查看日志
                        </Button>
                      </div>
                    )
                  })}
              </div>
            }
            type="error"
            showIcon
            closable
            style={{ marginBottom: 16 }}
          />
        )}
        <Table
          columns={columns}
          dataSource={clients}
          rowKey="id"
          loading={loading}
          pagination={{
            showSizeChanger: true,
            showTotal: (total) => `共 ${total} 个客户端`,
          }}
        />
      </Card>

      {/* 创建客户端模态框 */}
      <Modal
        title="创建客户端"
        open={createModalVisible}
        onCancel={() => {
          setCreateModalVisible(false)
          form.resetFields()
        }}
        onOk={() => form.submit()}
        afterOpenChange={(open) => {
          if (open) {
            loadRecommendedUrls()
          }
        }}
      >
        <Form form={form} layout="vertical" onFinish={handleCreate}>
          <Form.Item
            name="name"
            label="名称"
            rules={[{ required: true, message: '请输入客户端名称' }]}
          >
            <Input placeholder="请输入客户端名称" />
          </Form.Item>
          <Form.Item
            name="client_type"
            label="客户端类型"
            rules={[{ required: true, message: '请选择客户端类型' }]}
          >
            <Select placeholder="请选择客户端类型">
              <Option value="prysm">Prysm</Option>
              <Option value="lighthouse">Lighthouse</Option>
              <Option value="teku">Teku</Option>
            </Select>
          </Form.Item>
          <Form.Item 
            name="grpc_endpoint" 
            label="gRPC Endpoint"
            tooltip="系统会自动填充检测到的 gRPC 端点（Prysm 专用）。如果未检测到，Prysm 默认使用 4000 端口。"
          >
            <Input placeholder="host.docker.internal:33838（自动检测）" />
          </Form.Item>
          <Form.Item
            name="web3signer_url"
            label="Web3Signer URL"
            initialValue="http://haproxy:9002"
          >
            <Input placeholder="http://haproxy:9002" />
          </Form.Item>
          <Form.Item name="notes" label="备注">
            <Input.TextArea rows={3} placeholder="可选备注信息" />
          </Form.Item>
        </Form>
      </Modal>

      {/* 编辑客户端模态框 */}
      <Modal
        title="编辑客户端"
        open={editModalVisible}
        onCancel={() => {
          setEditModalVisible(false)
          editForm.resetFields()
          setSelectedClient(null)
        }}
        onOk={() => editForm.submit()}
      >
        <Form form={editForm} layout="vertical" onFinish={handleUpdate}>
          <Form.Item
            name="name"
            label="名称"
            rules={[{ required: true, message: '请输入客户端名称' }]}
          >
            <Input placeholder="请输入客户端名称" />
          </Form.Item>
          <Form.Item name="grpc_endpoint" label="gRPC Endpoint">
            <Input placeholder="localhost:4000" />
          </Form.Item>
          <Form.Item
            name="web3signer_url"
            label="Web3Signer URL"
          >
            <Input placeholder="http://haproxy:9002" />
          </Form.Item>
          <Form.Item name="is_active" label="是否激活" valuePropName="checked">
            <Switch />
          </Form.Item>
          <Form.Item name="notes" label="备注">
            <Input.TextArea rows={3} placeholder="可选备注信息" />
          </Form.Item>
        </Form>
      </Modal>

      {/* 密钥管理对话框 */}
      <ClientKeyManagementModal
        visible={keyManagementModalVisible}
        client={selectedClient}
        onClose={() => {
          setKeyManagementModalVisible(false)
          setSelectedClient(null)
        }}
        onRefresh={loadClients}
      />

      {/* 查看日志模态框 */}
      <Modal
        title={`容器日志 - ${clients.find((c) => c.id === selectedClientForLogs)?.name || `客户端 ${selectedClientForLogs}`}`}
        open={logsModalVisible}
        onCancel={() => {
          setLogsModalVisible(false)
          setSelectedClientForLogs(null)
          setClientLogs([])
        }}
        footer={[
          <Button
            key="refresh"
            icon={<ReloadOutlined />}
            onClick={() => selectedClientForLogs && loadClientLogs(selectedClientForLogs)}
            loading={loadingLogs}
          >
            刷新
          </Button>,
          <Button key="close" onClick={() => {
            setLogsModalVisible(false)
            setSelectedClientForLogs(null)
            setClientLogs([])
          }}>
            关闭
          </Button>,
        ]}
        width={900}
      >
        <Spin spinning={loadingLogs}>
          <div
            style={{
              background: '#1e1e1e',
              color: '#d4d4d4',
              padding: 16,
              borderRadius: 4,
              maxHeight: '600px',
              overflow: 'auto',
              fontFamily: 'monospace',
              fontSize: '12px',
              lineHeight: '1.5',
            }}
          >
            {clientLogs.length > 0 ? (
              clientLogs.map((log, index) => (
                <div key={index} style={{ marginBottom: 2, lineHeight: '1.5', whiteSpace: 'pre-wrap' }}>
                  {log || '\u00A0'}
                </div>
              ))
            ) : (
              <div style={{ color: '#888' }}>暂无日志</div>
            )}
          </div>
        </Spin>
      </Modal>
    </div>
  )
}

export default ClientList
