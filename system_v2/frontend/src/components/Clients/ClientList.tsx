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
} from 'antd'
import {
  PlusOutlined,
  PlayCircleOutlined,
  StopOutlined,
  ReloadOutlined,
  KeyOutlined,
} from '@ant-design/icons'
import { clientsApi, ClientInstance } from '../../api/clients'
import { keysApi } from '../../api/keys'

const { Title } = Typography
const { Option } = Select

const ClientList: React.FC = () => {
  const [clients, setClients] = useState<ClientInstance[]>([])
  const [loading, setLoading] = useState(false)
  const [createModalVisible, setCreateModalVisible] = useState(false)
  const [assignKeysModalVisible, setAssignKeysModalVisible] = useState(false)
  const [selectedClient, setSelectedClient] = useState<ClientInstance | null>(null)
  const [availableKeys, setAvailableKeys] = useState<any[]>([])
  const [clientStatuses, setClientStatuses] = useState<Record<number, any>>({})
  const [form] = Form.useForm()
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

  const handleStart = async (clientId: number) => {
    try {
      await clientsApi.start(clientId)
      message.success('客户端启动成功')
      setTimeout(() => {
        loadClientStatus(clientId)
      }, 1000)
    } catch (error: any) {
      message.error(`启动客户端失败: ${error.message}`)
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

  const handleAssignKeys = async (clientId: number) => {
    setSelectedClient(clients.find((c) => c.id === clientId) || null)
    
    // 加载可用密钥
    try {
      const response = await keysApi.list({ status: 'active' }) as any
      setAvailableKeys(response.items || [])
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
    if (!status) return <Tag>未知</Tag>
    if (status.is_running) {
      return <Tag color="success">运行中</Tag>
    }
    return <Tag>已停止</Tag>
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

        return (
          <Space>
            {isRunning ? (
              <Popconfirm
                title="确定要停止客户端吗？"
                onConfirm={() => handleStop(record.id)}
              >
                <Button size="small" danger icon={<StopOutlined />}>
                  停止
                </Button>
              </Popconfirm>
            ) : (
              <Button
                size="small"
                type="primary"
                icon={<PlayCircleOutlined />}
                onClick={() => handleStart(record.id)}
              >
                启动
              </Button>
            )}
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
          <Form.Item name="beacon_api_url" label="Beacon API URL">
            <Input placeholder="http://localhost:5052" />
          </Form.Item>
          <Form.Item name="grpc_endpoint" label="gRPC Endpoint">
            <Input placeholder="localhost:4000" />
          </Form.Item>
          <Form.Item
            name="web3signer_url"
            label="Web3Signer URL"
            initialValue="http://localhost:9002"
          >
            <Input placeholder="http://localhost:9002" />
          </Form.Item>
          <Form.Item name="notes" label="备注">
            <Input.TextArea rows={3} placeholder="可选备注信息" />
          </Form.Item>
        </Form>
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
    </div>
  )
}

export default ClientList
