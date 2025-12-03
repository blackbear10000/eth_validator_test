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
  Radio,
  Collapse,
} from 'antd'
import {
  PlusOutlined,
  ReloadOutlined,
  SyncOutlined,
} from '@ant-design/icons'
import { depositsApi, DepositTransaction, DepositData, BatchDepositContract } from '../../api/deposits'
import { keysApi } from '../../api/keys'

const { Title, Text } = Typography
const { Option } = Select
const { Panel } = Collapse

const DepositList: React.FC = () => {
  const [deposits, setDeposits] = useState<DepositTransaction[]>([])
  const [loading, setLoading] = useState(false)
  const [generateModalVisible, setGenerateModalVisible] = useState(false)
  const [submitModalVisible, setSubmitModalVisible] = useState(false)
  const [deployModalVisible, setDeployModalVisible] = useState(false)
  const [availableKeys, setAvailableKeys] = useState<any[]>([])
  const [generatedDepositData, setGeneratedDepositData] = useState<DepositData[]>([])
  const [batchContracts, setBatchContracts] = useState<BatchDepositContract[]>([])
  const [form] = Form.useForm()
  const [submitForm] = Form.useForm()
  const [deployForm] = Form.useForm()

  useEffect(() => {
    loadDeposits()
    loadBatchContracts()
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

  const loadBatchContracts = async () => {
    try {
      const response = await depositsApi.listBatchContracts() as any
      setBatchContracts(response || [])
    } catch (error: any) {
      message.error(`加载 Batch Deposit 合约列表失败: ${error.message}`)
    }
  }

  const handleSubmit = async (values: {
    from_address: string
    private_key: string
    deposit_type: 'official' | 'batch'
    batch_contract_address?: string
    official_deposit_contract_address?: string
  }) => {
    if (generatedDepositData.length === 0) {
      message.warning('请先生成 Deposit Data')
      return
    }

    try {
      await depositsApi.submit(
        generatedDepositData,
        values.from_address,
        values.private_key,
        values.deposit_type,
        values.batch_contract_address,
        values.official_deposit_contract_address
      )
      message.success('存款提交成功')
      setSubmitModalVisible(false)
      submitForm.resetFields()
      setGeneratedDepositData([])
      loadDeposits()
    } catch (error: any) {
      message.error(`提交存款失败: ${error.message}`)
    }
  }

  const handleDeployContract = async (values: {
    deployer_private_key: string
    network_name: string
    rpc_url?: string
    gas_price?: number
    gas_limit?: number
  }) => {
    try {
      const result = await depositsApi.deployBatchContract(values) as any
      message.success(`Batch Deposit 合约部署成功: ${result.contract_address}`)
      setDeployModalVisible(false)
      deployForm.resetFields()
      loadBatchContracts()
    } catch (error: any) {
      // 提取错误消息
      let errorMessage = '部署合约失败'
      if (error?.message) {
        errorMessage = error.message
      } else if (typeof error === 'string') {
        errorMessage = error
      } else if (error?.response?.data?.detail) {
        errorMessage = error.response.data.detail
      } else if (error?.response?.data?.message) {
        errorMessage = error.response.data.message
      } else if (error?.detail) {
        errorMessage = error.detail
      }
      message.error(`部署合约失败: ${errorMessage}`)
      console.error('部署合约错误详情:', error)
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
              type="default"
              onClick={() => {
                loadBatchContracts()
                setDeployModalVisible(true)
              }}
            >
              部署 Batch Deposit 合约
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
            name="deposit_type"
            label="存款类型"
            initialValue="batch"
            rules={[{ required: true, message: '请选择存款类型' }]}
          >
            <Radio.Group>
              <Radio value="batch">Batch Deposit 合约（批量存款，节省 Gas）</Radio>
              <Radio value="official">官方 Deposit 合约（单个存款）</Radio>
            </Radio.Group>
          </Form.Item>
          
          <Form.Item
            noStyle
            shouldUpdate={(prevValues, currentValues) => prevValues.deposit_type !== currentValues.deposit_type}
          >
            {({ getFieldValue }) => {
              const depositType = getFieldValue('deposit_type')
              if (depositType === 'batch') {
                return (
                  <Form.Item
                    name="batch_contract_address"
                    label="Batch Deposit 合约地址"
                    help="选择已部署的合约或手动输入地址"
                  >
                    <Select
                      placeholder="选择合约或输入地址"
                      showSearch
                      allowClear
                      filterOption={(input, option) => {
                        const value = option?.value as string | undefined
                        return value ? value.toLowerCase().includes(input.toLowerCase()) : false
                      }}
                    >
                      {batchContracts.map((contract) => (
                        <Option key={contract.id} value={contract.contract_address}>
                          {contract.contract_address} ({contract.network_name})
                        </Option>
                      ))}
                    </Select>
                  </Form.Item>
                )
              } else {
                return (
                  <Form.Item
                    name="official_deposit_contract_address"
                    label="官方 Deposit 合约地址（可选，留空则自动获取）"
                    help="如果留空，系统将尝试从网络信息中获取"
                  >
                    <Input placeholder="0x...（留空则自动获取）" />
                  </Form.Item>
                )
              }
            }}
          </Form.Item>

          <Form.Item
            name="from_address"
            label="发送地址（用于发送存款交易的钱包地址）"
            help="此地址需要有足够的 ETH 来支付存款金额（32 ETH × 验证者数量）和 gas 费用"
            rules={[
              { required: true, message: '请输入发送地址' },
              { pattern: /^0x[a-fA-F0-9]{40}$/, message: '请输入有效的以太坊地址' },
            ]}
          >
            <Input placeholder="0x..." />
          </Form.Item>
          <Form.Item
            name="private_key"
            label="私钥（用于签名交易）"
            help="⚠️ 警告：私钥将用于签名交易，请确保在安全环境中使用"
            rules={[
              { required: true, message: '请输入私钥' },
              { pattern: /^0x[a-fA-F0-9]{64}$/, message: '请输入有效的私钥（64 个十六进制字符，0x开头）' },
            ]}
          >
            <Input.Password placeholder="0x..." />
          </Form.Item>
          <Divider />
          <Typography.Text strong>
            已生成 {generatedDepositData.length} 个 Deposit Data：
          </Typography.Text>
          <div style={{ maxHeight: '400px', overflow: 'auto', marginTop: 16 }}>
            <Collapse>
              {generatedDepositData.map((data, index) => (
                <Panel
                  key={index}
                  header={
                    <Space>
                      <Text strong>验证者 {index + 1}</Text>
                      <Text type="secondary" style={{ fontFamily: 'monospace', fontSize: '12px' }}>
                        {data.pubkey.slice(0, 20)}...
                      </Text>
                    </Space>
                  }
                >
                  <Descriptions column={1} bordered size="small">
                    <Descriptions.Item label="公钥" span={1}>
                      <Text copyable={{ text: data.pubkey }} style={{ fontFamily: 'monospace', fontSize: '12px' }}>
                        {data.pubkey}
                      </Text>
                    </Descriptions.Item>
                    <Descriptions.Item label="提款凭证" span={1}>
                      <Text copyable={{ text: data.withdrawal_credentials }} style={{ fontFamily: 'monospace', fontSize: '12px' }}>
                        {data.withdrawal_credentials}
                      </Text>
                    </Descriptions.Item>
                    <Descriptions.Item label="金额">
                      <Space>
                        <Text>{data.amount / 1e9} ETH</Text>
                        <Text type="secondary">({data.amount} Gwei)</Text>
                      </Space>
                    </Descriptions.Item>
                    <Descriptions.Item label="签名" span={1}>
                      <Text copyable={{ text: data.signature }} style={{ fontFamily: 'monospace', fontSize: '11px' }}>
                        {data.signature.slice(0, 40)}...
                      </Text>
                    </Descriptions.Item>
                    <Descriptions.Item label="Deposit Data Root" span={1}>
                      <Text copyable={{ text: data.deposit_data_root }} style={{ fontFamily: 'monospace', fontSize: '12px' }}>
                        {data.deposit_data_root}
                      </Text>
                    </Descriptions.Item>
                    <Descriptions.Item label="Fork Version">
                      <Text code>{data.fork_version}</Text>
                    </Descriptions.Item>
                    {data.network_name && (
                      <Descriptions.Item label="网络名称">
                        <Text>{data.network_name}</Text>
                      </Descriptions.Item>
                    )}
                    <Descriptions.Item label="提款地址">
                      <Text copyable={{ text: data.withdrawal_address }} style={{ fontFamily: 'monospace', fontSize: '12px' }}>
                        {data.withdrawal_address}
                      </Text>
                    </Descriptions.Item>
                  </Descriptions>
                </Panel>
              ))}
            </Collapse>
          </div>
        </Form>
      </Modal>

      {/* 部署 Batch Deposit 合约模态框 */}
      <Modal
        title="部署 Batch Deposit 合约"
        open={deployModalVisible}
        onCancel={() => {
          setDeployModalVisible(false)
          deployForm.resetFields()
        }}
        onOk={() => deployForm.submit()}
        width={600}
      >
        <Form form={deployForm} layout="vertical" onFinish={handleDeployContract}>
          <Form.Item
            name="network_name"
            label="网络名称"
            rules={[{ required: true, message: '请输入网络名称' }]}
            initialValue="kurtosis-devnet"
          >
            <Input placeholder="例如: kurtosis-devnet, mainnet" />
          </Form.Item>
          <Form.Item
            name="rpc_url"
            label="RPC URL（可选，留空则自动从 Kurtosis 网络获取）"
          >
            <Input placeholder="http://localhost:8545（留空则自动获取）" />
          </Form.Item>
          <Form.Item
            name="deployer_private_key"
            label="部署者私钥"
            rules={[
              { required: true, message: '请输入部署者私钥' },
              { pattern: /^0x[a-fA-F0-9]{64}$/, message: '请输入有效的私钥（64 个十六进制字符，0x开头）' },
            ]}
          >
            <Input.Password placeholder="0x..." />
          </Form.Item>
          <Form.Item
            name="gas_price"
            label="Gas 价格（可选，留空则使用网络建议价格）"
          >
            <InputNumber
              style={{ width: '100%' }}
              placeholder="Gas 价格（wei）"
              min={0}
            />
          </Form.Item>
          <Form.Item
            name="gas_limit"
            label="Gas 限制（可选，默认 5000000）"
          >
            <InputNumber
              style={{ width: '100%' }}
              placeholder="Gas 限制"
              min={1000000}
              max={10000000}
            />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  )
}

export default DepositList
