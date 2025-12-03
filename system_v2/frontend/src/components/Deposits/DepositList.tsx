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
  InputNumber,
  Select,
  Tag,
  Typography,
  Descriptions,
  Divider,
} from 'antd'
import {
  PlusOutlined,
  SendOutlined,
  ReloadOutlined,
  SyncOutlined,
} from '@ant-design/icons'
import { depositsApi, DepositTransaction, DepositData } from '../../api/deposits'
import { keysApi } from '../../api/keys'

const { Title, Text } = Typography
const { Option } = Select

const DepositList: React.FC = () => {
  const [deposits, setDeposits] = useState<DepositTransaction[]>([])
  const [loading, setLoading] = useState(false)
  const [generateModalVisible, setGenerateModalVisible] = useState(false)
  const [submitModalVisible, setSubmitModalVisible] = useState(false)
  const [availableKeys, setAvailableKeys] = useState<any[]>([])
  const [generatedDepositData, setGeneratedDepositData] = useState<DepositData[]>([])
  const [form] = Form.useForm()
  const [submitForm] = Form.useForm()

  useEffect(() => {
    loadDeposits()
  }, [])

  const loadDeposits = async () => {
    setLoading(true)
    try {
      const response = await depositsApi.list() as any
      setDeposits(response || [])
    } catch (error: any) {
      message.error(`加载存款列表失败: ${error.message}`)
    } finally {
      setLoading(false)
    }
  }

  const loadAvailableKeys = async () => {
    try {
      const response = await keysApi.list({ status: 'active' }) as any
      setAvailableKeys(response.items || [])
    } catch (error: any) {
      message.error(`加载可用密钥失败: ${error.message}`)
    }
  }

  const handleGenerate = async (values: {
    pubkeys?: string[]
    withdrawal_address: string
    amount_eth?: number
    fork_version?: string
  }) => {
    try {
      const response = await depositsApi.generate(values) as any
      setGeneratedDepositData(response || [])
      message.success(`成功生成 ${response?.length || 0} 个 Deposit Data`)
      setGenerateModalVisible(false)
      form.resetFields()
      setSubmitModalVisible(true)
    } catch (error: any) {
      message.error(`生成 Deposit Data 失败: ${error.message}`)
    }
  }

  const handleSubmit = async (values: { from_address: string }) => {
    if (generatedDepositData.length === 0) {
      message.warning('请先生成 Deposit Data')
      return
    }

    try {
      await depositsApi.submit(generatedDepositData, values.from_address)
      message.success('存款提交成功')
      setSubmitModalVisible(false)
      submitForm.resetFields()
      setGeneratedDepositData([])
      loadDeposits()
    } catch (error: any) {
      message.error(`提交存款失败: ${error.message}`)
    }
  }

  const handleSync = async () => {
    try {
      await depositsApi.sync()
      message.success('状态同步成功')
      loadDeposits()
    } catch (error: any) {
      message.error(`状态同步失败: ${error.message}`)
    }
  }

  const getStatusTag = (status: string) => {
    const statusConfig: Record<string, { color: string; text: string }> = {
      pending: { color: 'warning', text: '待提交' },
      submitted: { color: 'processing', text: '已提交' },
      confirmed: { color: 'success', text: '已确认' },
      failed: { color: 'error', text: '失败' },
    }

    const config = statusConfig[status] || { color: 'default', text: status }
    return <Tag color={config.color}>{config.text}</Tag>
  }

  const columns = [
    {
      title: 'ID',
      dataIndex: 'id',
      key: 'id',
      width: 80,
    },
    {
      title: '公钥',
      dataIndex: 'pubkey',
      key: 'pubkey',
      width: 200,
      render: (text: string) => (
        <Text copyable={{ text }} style={{ fontFamily: 'monospace', fontSize: '12px' }}>
          {text.slice(0, 20)}...
        </Text>
      ),
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      width: 120,
      render: (status: string) => getStatusTag(status),
    },
    {
      title: '金额 (ETH)',
      dataIndex: 'amount_eth',
      key: 'amount_eth',
      width: 120,
      render: (amount: number) => amount.toFixed(4),
    },
    {
      title: '交易哈希',
      dataIndex: 'tx_hash',
      key: 'tx_hash',
      width: 200,
      render: (hash: string) =>
        hash ? (
          <Text copyable={{ text: hash }} style={{ fontFamily: 'monospace', fontSize: '12px' }}>
            {hash.slice(0, 20)}...
          </Text>
        ) : (
          '-'
        ),
    },
    {
      title: '批次ID',
      dataIndex: 'batch_id',
      key: 'batch_id',
      width: 150,
      render: (text: string) => text || '-',
    },
    {
      title: '提交时间',
      dataIndex: 'submitted_at',
      key: 'submitted_at',
      width: 180,
      render: (text: string) => (text ? new Date(text).toLocaleString() : '-'),
    },
    {
      title: '确认时间',
      dataIndex: 'confirmed_at',
      key: 'confirmed_at',
      width: 180,
      render: (text: string) => (text ? new Date(text).toLocaleString() : '-'),
    },
  ]

  return (
    <div>
      <Title level={2}>存款管理</Title>

      <Card
        title="存款交易列表"
        extra={
          <Space>
            <Button icon={<SyncOutlined />} onClick={handleSync}>
              同步状态
            </Button>
            <Button
              type="primary"
              icon={<PlusOutlined />}
              onClick={() => {
                loadAvailableKeys()
                setGenerateModalVisible(true)
              }}
            >
              生成 Deposit Data
            </Button>
            <Button icon={<ReloadOutlined />} onClick={loadDeposits}>
              刷新
            </Button>
          </Space>
        }
      >
        <Table
          columns={columns}
          dataSource={deposits}
          rowKey="id"
          loading={loading}
          pagination={{
            showSizeChanger: true,
            showTotal: (total) => `共 ${total} 条存款记录`,
          }}
        />
      </Card>

      {/* 生成 Deposit Data 模态框 */}
      <Modal
        title="生成 Deposit Data"
        open={generateModalVisible}
        onCancel={() => {
          setGenerateModalVisible(false)
          form.resetFields()
        }}
        onOk={() => form.submit()}
        width={600}
      >
        <Form form={form} layout="vertical" onFinish={handleGenerate}>
          <Form.Item
            name="pubkeys"
            label="选择密钥（可选，不选则使用所有激活的密钥）"
          >
            <Select
              mode="multiple"
              placeholder="请选择密钥，留空则使用所有激活的密钥"
              showSearch
              filterOption={(input, option) =>
                (option?.children as string)?.toLowerCase().includes(input.toLowerCase())
              }
            >
              {availableKeys.map((key) => (
                <Option key={key.pubkey} value={key.pubkey}>
                  {key.pubkey.slice(0, 20)}... ({key.status})
                </Option>
              ))}
            </Select>
          </Form.Item>
          <Form.Item
            name="withdrawal_address"
            label="提款地址"
            rules={[
              { required: true, message: '请输入提款地址' },
              { pattern: /^0x[a-fA-F0-9]{40}$/, message: '请输入有效的以太坊地址' },
            ]}
          >
            <Input placeholder="0x..." />
          </Form.Item>
          <Form.Item
            name="amount_eth"
            label="金额 (ETH)"
            initialValue={32.0}
            rules={[{ required: true, message: '请输入金额' }]}
          >
            <InputNumber
              style={{ width: '100%' }}
              min={32}
              precision={0}
            />
          </Form.Item>
          <Form.Item name="fork_version" label="Fork Version（可选，留空则自动检测）">
            <Input placeholder="0x..." />
          </Form.Item>
        </Form>
      </Modal>

      {/* 提交存款模态框 */}
      <Modal
        title="提交存款"
        open={submitModalVisible}
        onCancel={() => {
          setSubmitModalVisible(false)
          submitForm.resetFields()
          setGeneratedDepositData([])
        }}
        onOk={() => submitForm.submit()}
        width={800}
      >
        <Form form={submitForm} layout="vertical" onFinish={handleSubmit}>
          <Form.Item
            name="from_address"
            label="发送地址"
            rules={[
              { required: true, message: '请输入发送地址' },
              { pattern: /^0x[a-fA-F0-9]{40}$/, message: '请输入有效的以太坊地址' },
            ]}
          >
            <Input placeholder="0x..." />
          </Form.Item>
          <Divider />
          <Typography.Text strong>
            已生成 {generatedDepositData.length} 个 Deposit Data：
          </Typography.Text>
          <div style={{ maxHeight: '300px', overflow: 'auto', marginTop: 16 }}>
            {generatedDepositData.map((data, index) => (
              <Card key={index} size="small" style={{ marginBottom: 8 }}>
                <Descriptions column={1} size="small">
                  <Descriptions.Item label="公钥">
                    <Text copyable={{ text: data.pubkey }} style={{ fontFamily: 'monospace', fontSize: '12px' }}>
                      {data.pubkey.slice(0, 20)}...
                    </Text>
                  </Descriptions.Item>
                  <Descriptions.Item label="金额">
                    {data.amount / 1e9} ETH
                  </Descriptions.Item>
                  <Descriptions.Item label="Fork Version">
                    <Text code>{data.fork_version}</Text>
                  </Descriptions.Item>
                </Descriptions>
              </Card>
            ))}
          </div>
        </Form>
      </Modal>
    </div>
  )
}

export default DepositList
