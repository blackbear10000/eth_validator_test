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
} from 'antd'
import {
  PlusOutlined,
  PlayCircleOutlined,
  StopOutlined,
  ReloadOutlined,
  KeyOutlined,
  EditOutlined,
  DeleteOutlined,
  EyeOutlined,
  PauseCircleOutlined,
  CaretRightOutlined,
  CloseCircleOutlined,
  FileTextOutlined,
} from '@ant-design/icons'
import { clientsApi, ClientInstance } from '../../api/clients'
import { keysApi } from '../../api/keys'
import { networkApi } from '../../api/network'

const { Title } = Typography
const { Option } = Select

const ClientList: React.FC = () => {
  const [clients, setClients] = useState<ClientInstance[]>([])
  const [loading, setLoading] = useState(false)
  const [createModalVisible, setCreateModalVisible] = useState(false)
  const [editModalVisible, setEditModalVisible] = useState(false)
  const [assignKeysModalVisible, setAssignKeysModalVisible] = useState(false)
  const [viewKeysModalVisible, setViewKeysModalVisible] = useState(false)
  const [selectedClient, setSelectedClient] = useState<ClientInstance | null>(null)
  const [availableKeys, setAvailableKeys] = useState<any[]>([])
  const [clientKeys, setClientKeys] = useState<any[]>([])
  const [clientStatuses, setClientStatuses] = useState<Record<number, any>>({})
  const [startingClients, setStartingClients] = useState<Set<number>>(new Set())
  const [logsModalVisible, setLogsModalVisible] = useState(false)
  const [selectedClientForLogs, setSelectedClientForLogs] = useState<number | null>(null)
  const [clientLogs, setClientLogs] = useState<string[]>([])
  const [loadingLogs, setLoadingLogs] = useState(false)
  const [form] = Form.useForm()
  const [editForm] = Form.useForm()
  const [assignForm] = Form.useForm()

  useEffect(() => {
    loadClients()
  }, [])

  const loadClients = async () => {
    setLoading(true)
    try {
      const response = await clientsApi.list() as any
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
      const recommendedValues: any = {}
      
      // 推荐 Beacon API URL
      if (networkInfo?.beacon_api_url) {
        recommendedValues.beacon_api_url = networkInfo.beacon_api_url
      }
      
      // 推荐 Web3Signer URL（使用默认值，因为这是系统内部服务）
      recommendedValues.web3signer_url = 'http://host.docker.internal:9002' // HAProxy
      
      // gRPC endpoint 根据客户端类型不同而不同，这里先不自动填充
      // 用户可以根据客户端类型手动填写
      
      if (Object.keys(recommendedValues).length > 0) {
        form.setFieldsValue(recommendedValues)
        message.info('已自动填充推荐的 API URL')
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
      beacon_api_url: client.beacon_api_url,
      grpc_endpoint: client.grpc_endpoint,
      web3signer_url: client.web3signer_url,
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

  const handleViewKeys = async (clientId: number) => {
    setSelectedClient(clients.find((c) => c.id === clientId) || null)
    try {
      const keys = await clientsApi.getKeys(clientId) as any
      setClientKeys(keys || [])
      setViewKeysModalVisible(true)
    } catch (error: any) {
      message.error(`加载密钥列表失败: ${error.message}`)
    }
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

  const handleAssignKeys = async (clientId: number) => {
    setSelectedClient(clients.find((c) => c.id === clientId) || null)
    
    // 加载可用密钥（包括已激活、已生成存款数据、已提交到链上的密钥）
    try {
      const [activeResponse, depositDataResponse, pendingResponse, depositedResponse, activeOnChainResponse] = await Promise.all([
        keysApi.list({ status: 'active' }) as any,
        keysApi.list({ status: 'deposit_data_generated' }) as any,
        keysApi.list({ status: 'pending' }) as any,
        keysApi.list({ status: 'deposited' }) as any,
        keysApi.list({ status: 'active_on_chain' }) as any,
      ])
      const allKeys = [
        ...(activeResponse.items || []),
        ...(depositDataResponse.items || []),
        ...(pendingResponse.items || []),
        ...(depositedResponse.items || []),
        ...(activeOnChainResponse.items || []),
      ]
      setAvailableKeys(allKeys)
      setAssignKeysModalVisible(true)
    } catch (error: any) {
      message.error(`加载可用密钥失败: ${error.message}`)
    }
  }

  const handleSubmitAssignKeys = async (values: { pubkeys: string[] }) => {
    if (!selectedClient) return

    try {
      await clientsApi.assignKeys(selectedClient.id, values.pubkeys)
      message.success(`成功分配 ${values.pubkeys.length} 个密钥`)
      setAssignKeysModalVisible(false)
      assignForm.resetFields()
      loadClients()
    } catch (error: any) {
      message.error(`分配密钥失败: ${error.message}`)
    }
  }

  const handleReloadKeys = async (clientId: number) => {
    try {
      await clientsApi.reloadKeys(clientId)
      message.success('密钥重新加载成功')
    } catch (error: any) {
      message.error(`重新加载密钥失败: ${error.message}`)
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
      title: 'Beacon API',
      dataIndex: 'beacon_api_url',
      key: 'beacon_api_url',
      width: 200,
      render: (url: string) => url || '-',
    },
    {
      title: 'Web3Signer URL',
      dataIndex: 'web3signer_url',
      key: 'web3signer_url',
      width: 200,
      render: (url: string) => url || '-',
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
            <Button
              size="small"
              icon={<KeyOutlined />}
              onClick={() => handleAssignKeys(record.id)}
            >
              分配密钥
            </Button>
            <Button
              size="small"
              icon={<ReloadOutlined />}
              onClick={() => handleReloadKeys(record.id)}
            >
              重载密钥
            </Button>
            <Button
              size="small"
              icon={<EyeOutlined />}
              onClick={() => handleViewKeys(record.id)}
            >
              查看密钥
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
            <Popconfirm
              title="确定要删除这个客户端吗？"
              description="删除后可以恢复（软删除），如果有关联的密钥，请先移除密钥"
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
            name="beacon_api_url" 
            label="Beacon API URL"
            tooltip="系统会自动推荐检测到的 Beacon API URL"
          >
            <Input placeholder="http://host.docker.internal:33790" />
          </Form.Item>
          <Form.Item 
            name="grpc_endpoint" 
            label="gRPC Endpoint"
            tooltip="Prysm: 4000, Lighthouse: 5052, Teku: 9000"
          >
            <Input placeholder="host.docker.internal:4000" />
          </Form.Item>
          <Form.Item
            name="web3signer_url"
            label="Web3Signer URL"
            initialValue="http://host.docker.internal:9002"
            tooltip="推荐使用 HAProxy URL (9002 端口)"
          >
            <Input placeholder="http://host.docker.internal:9002" />
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
          <Form.Item name="beacon_api_url" label="Beacon API URL">
            <Input placeholder="http://localhost:5052" />
          </Form.Item>
          <Form.Item name="grpc_endpoint" label="gRPC Endpoint">
            <Input placeholder="localhost:4000" />
          </Form.Item>
          <Form.Item
            name="web3signer_url"
            label="Web3Signer URL"
          >
            <Input placeholder="http://localhost:9002" />
          </Form.Item>
          <Form.Item name="is_active" label="是否激活" valuePropName="checked">
            <Switch />
          </Form.Item>
          <Form.Item name="notes" label="备注">
            <Input.TextArea rows={3} placeholder="可选备注信息" />
          </Form.Item>
        </Form>
      </Modal>

      {/* 查看密钥列表模态框 */}
      <Modal
        title={`客户端密钥列表 - ${selectedClient?.name}`}
        open={viewKeysModalVisible}
        onCancel={() => {
          setViewKeysModalVisible(false)
          setClientKeys([])
          setSelectedClient(null)
        }}
        footer={[
          <Button key="close" onClick={() => {
            setViewKeysModalVisible(false)
            setClientKeys([])
            setSelectedClient(null)
          }}>
            关闭
          </Button>,
        ]}
        width={800}
      >
        <Table
          columns={[
            {
              title: '公钥',
              dataIndex: 'pubkey',
              key: 'pubkey',
              render: (text: string) => (
                <Typography.Text copyable={{ text }} style={{ fontFamily: 'monospace', fontSize: '12px' }}>
                  {text.slice(0, 20)}...
                </Typography.Text>
              ),
            },
            {
              title: '状态',
              dataIndex: 'status',
              key: 'status',
              render: (status: string) => <Tag>{status}</Tag>,
            },
            {
              title: '激活时间',
              dataIndex: 'activated_at',
              key: 'activated_at',
              render: (time: string | null) => (time ? new Date(time).toLocaleString() : '-'),
            },
            {
              title: '存款时间',
              dataIndex: 'deposited_at',
              key: 'deposited_at',
              render: (time: string | null) => (time ? new Date(time).toLocaleString() : '-'),
            },
            {
              title: '批次ID',
              dataIndex: 'batch_id',
              key: 'batch_id',
              render: (batchId: string | null) => batchId || '-',
            },
          ]}
          dataSource={clientKeys}
          rowKey="pubkey"
          pagination={{ pageSize: 10 }}
        />
      </Modal>

      {/* 分配密钥模态框 */}
      <Modal
        title={`分配密钥 - ${selectedClient?.name}`}
        open={assignKeysModalVisible}
        onCancel={() => {
          setAssignKeysModalVisible(false)
          assignForm.resetFields()
        }}
        onOk={() => assignForm.submit()}
        width={600}
      >
        <Form form={assignForm} layout="vertical" onFinish={handleSubmitAssignKeys}>
          <Form.Item
            name="pubkeys"
            label="选择密钥"
            rules={[{ required: true, message: '请至少选择一个密钥' }]}
          >
            <Select
              mode="multiple"
              placeholder="请选择要分配的密钥"
              showSearch
              filterOption={(input, option) => {
                const children = option?.children as string | undefined
                return children ? children.toLowerCase().includes(input.toLowerCase()) : false
              }}
            >
              {availableKeys.map((key) => (
                <Option key={key.pubkey} value={key.pubkey}>
                  {key.pubkey.slice(0, 20)}... ({key.status})
                </Option>
              ))}
            </Select>
          </Form.Item>
        </Form>
      </Modal>

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
                <div key={index} style={{ marginBottom: 4 }}>
                  {log}
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
