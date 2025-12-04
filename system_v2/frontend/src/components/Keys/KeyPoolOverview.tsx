import React, { useEffect, useState } from 'react'
import {
  Card,
  Statistic,
  Row,
  Col,
  Button,
  Form,
  InputNumber,
  Input,
  Modal,
  message,
  Space,
  Table,
  Tag,
  Typography,
} from 'antd'
import {
  PlusOutlined,
  CheckCircleOutlined,
  ReloadOutlined,
} from '@ant-design/icons'
import { keysApi, KeyPoolStatus, ValidatorKey } from '../../api/keys'

const { Text } = Typography

const KeyPoolOverview: React.FC = () => {
  const [status, setStatus] = useState<KeyPoolStatus | null>(null)
  const [keys, setKeys] = useState<ValidatorKey[]>([])
  const [keysTotal, setKeysTotal] = useState(0)
  const [keysCurrentPage, setKeysCurrentPage] = useState(1)
  const [loading, setLoading] = useState(true)
  const [keysLoading, setKeysLoading] = useState(false)
  const [generateModalVisible, setGenerateModalVisible] = useState(false)
  const [activateModalVisible, setActivateModalVisible] = useState(false)
  const [generateLoading, setGenerateLoading] = useState(false)
  const [activateLoading, setActivateLoading] = useState(false)
  const [generateForm] = Form.useForm()
  const [activateForm] = Form.useForm()

  useEffect(() => {
    loadStatus()
    loadKeys()
  }, [])

  const loadStatus = async () => {
    try {
      setLoading(true)
      const response = await keysApi.getPoolStatus() as any
      setStatus(response as unknown as KeyPoolStatus)
    } catch (error: any) {
      message.error(`加载密钥池状态失败: ${error.message}`)
    } finally {
      setLoading(false)
    }
  }

  const loadKeys = async (page: number = 1) => {
    try {
      setKeysLoading(true)
      const limit = 20
      const offset = (page - 1) * limit
      const response = await keysApi.list({
        limit: limit,
        offset: offset,
      }) as any
      // apiClient 拦截器已经返回了 response.data，所以 response 就是数据对象
      const responseData = response.data || response
      setKeys(responseData.items || [])
      setKeysTotal(responseData.total || 0)
      setKeysCurrentPage(page)
      console.log('KeyPoolOverview 加载密钥:', {
        page: page,
        offset: offset,
        limit: limit,
        itemsCount: responseData.items?.length || 0,
        total: responseData.total || 0
      })
    } catch (error: any) {
      message.error(`加载密钥列表失败: ${error.message}`)
    } finally {
      setKeysLoading(false)
    }
  }

  // 批量生成密钥
  const handleGenerate = async (values: { count: number; batch_id?: string }) => {
    setGenerateLoading(true)
    try {
      await keysApi.batchGenerate(values.count, values.batch_id)
      message.success(`成功生成 ${values.count} 个密钥`)
      setGenerateModalVisible(false)
      generateForm.resetFields()
      // 刷新状态和列表
      await Promise.all([loadStatus(), loadKeys()])
    } catch (error: any) {
      message.error(`生成密钥失败: ${error.message}`)
    } finally {
      setGenerateLoading(false)
    }
  }

  // 批量激活密钥
  const handleActivate = async (values: { count: number; batch_id?: string }) => {
    setActivateLoading(true)
    try {
      await keysApi.activate(values.count, values.batch_id)
      message.success(`成功激活 ${values.count} 个密钥`)
      setActivateModalVisible(false)
      activateForm.resetFields()
      // 刷新状态和列表
      await Promise.all([loadStatus(), loadKeys()])
    } catch (error: any) {
      message.error(`激活密钥失败: ${error.message}`)
    } finally {
      setActivateLoading(false)
    }
  }

  // 获取状态标签
  const getStatusTag = (status: string) => {
    const statusConfig: Record<string, { color: string; text: string }> = {
      unused: { color: 'default', text: '未使用' },
      active: { color: 'processing', text: '已激活' },
      unknown: { color: 'warning', text: '未知' },
      pending: { color: 'warning', text: '待处理' },
      deposited: { color: 'blue', text: '已存款' },
      active_on_chain: { color: 'success', text: '链上激活' },
      pending_exit: { color: 'orange', text: '退出中' },
      slashed: { color: 'error', text: '被惩罚' },
      exited: { color: 'error', text: '已退出' },
    }
    const config = statusConfig[status] || { color: 'default', text: status }
    return <Tag color={config.color}>{config.text}</Tag>
  }

  return (
    <div>
      <h1>密钥池概览</h1>
      
      {/* 统计卡片 */}
      <Row gutter={16} style={{ marginBottom: 24 }}>
        <Col span={6}>
          <Card>
            <Statistic
              title="总密钥数"
              value={status?.total || 0}
              loading={loading}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="未使用"
              value={status?.by_status?.unused || 0}
              loading={loading}
              valueStyle={{ color: '#999' }}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="已激活"
              value={status?.by_status?.active || 0}
              loading={loading}
              valueStyle={{ color: '#1890ff' }}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="链上激活"
              value={status?.by_status?.active_on_chain || 0}
              loading={loading}
              valueStyle={{ color: '#52c41a' }}
            />
          </Card>
        </Col>
      </Row>

      {/* 操作按钮 */}
      <Card>
        <Space>
          <Button
            type="primary"
            icon={<PlusOutlined />}
            onClick={() => setGenerateModalVisible(true)}
          >
            批量生成密钥
          </Button>
          <Button
            type="default"
            icon={<CheckCircleOutlined />}
            onClick={() => setActivateModalVisible(true)}
            disabled={!status || (status.by_status?.unused || 0) === 0}
          >
            批量激活密钥
          </Button>
          <Button
            icon={<ReloadOutlined />}
            onClick={() => {
              loadStatus()
              loadKeys()
            }}
          >
            刷新
          </Button>
        </Space>
      </Card>

      {/* 密钥列表 */}
      <Card title="最近生成的密钥" style={{ marginTop: 24 }}>
        <Table
          columns={[
            {
              title: '公钥',
              dataIndex: 'pubkey',
              key: 'pubkey',
              width: 200,
              render: (text: string) => {
                const formatKeyDisplay = (key: string) => {
                  if (key.length <= 12) {
                    return key
                  }
                  return `${key.slice(0, 6)}...${key.slice(-6)}`
                }
                return (
                  <Text copyable={{ text }} style={{ fontFamily: 'monospace', fontSize: '12px' }}>
                    {formatKeyDisplay(text)}
                  </Text>
                )
              },
            },
            {
              title: '状态',
              dataIndex: 'status',
              key: 'status',
              width: 120,
              render: (status: string) => getStatusTag(status),
            },
            {
              title: '索引',
              dataIndex: 'index',
              key: 'index',
              width: 80,
            },
            {
              title: '批次ID',
              dataIndex: 'batch_id',
              key: 'batch_id',
              width: 150,
              render: (text: string) => text || '-',
            },
            {
              title: '创建时间',
              dataIndex: 'created_at',
              key: 'created_at',
              width: 180,
              render: (text: string) => new Date(text).toLocaleString(),
            },
          ]}
          dataSource={keys}
          rowKey="pubkey"
          loading={keysLoading}
          pagination={{
            current: keysCurrentPage,
            pageSize: 20,
            total: keysTotal,
            showTotal: (total) => `共 ${total} 条`,
            showSizeChanger: false,
            hideOnSinglePage: false,
            onChange: (page, pageSize) => {
              console.log('KeyPoolOverview 分页改变:', { 
                page, 
                pageSize,
                currentPage: keysCurrentPage,
                total: keysTotal 
              })
              loadKeys(page)
            },
          }}
        />
      </Card>

      {/* 批量生成密钥模态框 */}
      <Modal
        title="批量生成密钥"
        open={generateModalVisible}
        onCancel={() => {
          setGenerateModalVisible(false)
          generateForm.resetFields()
        }}
        onOk={() => generateForm.submit()}
        confirmLoading={generateLoading}
      >
        <Form
          form={generateForm}
          layout="vertical"
          onFinish={handleGenerate}
        >
          <Form.Item
            name="count"
            label="生成数量"
            rules={[
              { required: true, message: '请输入生成数量' },
              { type: 'number', min: 1, max: 10000, message: '数量必须在 1-10000 之间' },
            ]}
          >
            <InputNumber
              style={{ width: '100%' }}
              placeholder="请输入要生成的密钥数量"
              min={1}
              max={10000}
            />
          </Form.Item>
          <Form.Item
            name="batch_id"
            label="批次ID（可选）"
          >
            <Input placeholder="请输入批次ID，用于标识这批密钥" />
          </Form.Item>
        </Form>
      </Modal>

      {/* 批量激活密钥模态框 */}
      <Modal
        title="批量激活密钥"
        open={activateModalVisible}
        onCancel={() => {
          setActivateModalVisible(false)
          activateForm.resetFields()
        }}
        onOk={() => activateForm.submit()}
        confirmLoading={activateLoading}
      >
        <Form
          form={activateForm}
          layout="vertical"
          onFinish={handleActivate}
        >
          <Form.Item
            name="count"
            label="激活数量"
            rules={[
              { required: true, message: '请输入激活数量' },
              { type: 'number', min: 1, message: '数量必须大于 0' },
            ]}
          >
            <InputNumber
              style={{ width: '100%' }}
              placeholder={`最多可激活 ${status?.by_status?.unused || 0} 个密钥`}
              min={1}
              max={status?.by_status?.unused || 10000}
            />
          </Form.Item>
          <Form.Item
            name="batch_id"
            label="批次ID（可选）"
            help="如果指定批次ID，只激活该批次的密钥"
          >
            <Input placeholder="请输入批次ID" />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  )
}

export default KeyPoolOverview
