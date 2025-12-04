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
  const [detailModalVisible, setDetailModalVisible] = useState(false)
  const [selectedDeposit, setSelectedDeposit] = useState<DepositTransaction | null>(null)
  const [availableKeys, setAvailableKeys] = useState<any[]>([])
  const [generatedDepositData, setGeneratedDepositData] = useState<DepositData[]>([])
  const [batchContracts, setBatchContracts] = useState<BatchDepositContract[]>([])
  const [syncing, setSyncing] = useState(false)
  const [form] = Form.useForm()
  const [submitForm] = Form.useForm()

  const loadBatchContracts = async () => {
    try {
      const response = await depositsApi.listBatchContracts() as any
      // apiClient 的响应拦截器已经返回了 response.data
      const contractsList = Array.isArray(response) ? response : (response?.data || response || [])
      setBatchContracts(contractsList)
    } catch (error: any) {
      console.warn(`加载 Batch Deposit 合约列表失败: ${error.message}`)
    }
  }

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
      const response = await depositsApi.submit(
        generatedDepositData,
        values.from_address,
        values.private_key,
        values.deposit_type,
        values.batch_contract_address,
        values.official_deposit_contract_address
      ) as any
      
      // 检查返回结果
      const results = response.data || response || []
      const successCount = results.filter((r: any) => r.status === 'submitted' || r.status === 'success').length
      const failedCount = results.filter((r: any) => r.status === 'failed').length
      
      if (failedCount === 0) {
        message.success(`存款提交成功: ${successCount} 个批次已提交`)
      } else if (successCount > 0) {
        message.warning(`部分提交成功: ${successCount} 个批次成功，${failedCount} 个批次失败`)
      } else {
        message.error(`存款提交失败: ${failedCount} 个批次全部失败`)
      }
      
      // 显示详细错误信息（如果有）
      if (failedCount > 0) {
        const errors = results
          .filter((r: any) => r.status === 'failed')
          .map((r: any) => r.error || '未知错误')
          .filter((e: string, i: number, arr: string[]) => arr.indexOf(e) === i) // 去重
        if (errors.length > 0) {
          console.error('提交失败详情:', errors)
        }
      }
      
      setSubmitModalVisible(false)
      submitForm.resetFields()
      setGeneratedDepositData([])
      loadDeposits()
    } catch (error: any) {
      message.error(`提交存款失败: ${error.message}`)
      console.error('提交存款错误详情:', error)
    }
  }


  const handleSync = async (txHash?: string) => {
    try {
      setSyncing(true)
      const result = await depositsApi.sync(txHash) as any
      const resultData = result.data || result
      message.success(
        `状态同步完成: 同步 ${resultData.synced_count || 0} 个，确认 ${resultData.confirmed_count || 0} 个，失败 ${resultData.failed_count || 0} 个`
      )
      loadDeposits()
    } catch (error: any) {
      message.error(`状态同步失败: ${error.message}`)
    } finally {
      setSyncing(false)
    }
  }

  const handleViewDetail = (deposit: DepositTransaction) => {
    setSelectedDeposit(deposit)
    setDetailModalVisible(true)
  }

  const getStatusTag = (status: string) => {
    const statusConfig: Record<string, { color: string; text: string }> = {
      pending: { color: 'warning', text: '待确认' },
      submitted: { color: 'processing', text: '已提交' },
      confirmed: { color: 'success', text: '已确认' },
      failed: { color: 'error', text: '失败' },
    }

    const config = statusConfig[status] || { color: 'default', text: status }
    return <Tag color={config.color}>{config.text}</Tag>
  }

  const formatKeyDisplay = (key: string, length: number = 6) => {
    if (!key || key.length <= length * 2) {
      return key
    }
    return `${key.slice(0, length)}...${key.slice(-length)}`
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
        hash && !hash.startsWith('failed-') ? (
          <Text copyable={{ text: hash }} style={{ fontFamily: 'monospace', fontSize: '12px' }}>
            {formatKeyDisplay(hash, 8)}
          </Text>
        ) : (
          '-'
        ),
    },
    {
      title: '区块号',
      dataIndex: 'block_number',
      key: 'block_number',
      width: 120,
      render: (blockNumber: number) => (blockNumber ? blockNumber.toLocaleString() : '-'),
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
    {
      title: '操作',
      key: 'action',
      width: 150,
      render: (_: any, record: DepositTransaction) => (
        <Space>
          <Button type="link" size="small" onClick={() => handleViewDetail(record)}>
            查看详情
          </Button>
          {record.status === 'pending' && (
            <Button
              type="link"
              size="small"
              onClick={() => handleSync(record.tx_hash)}
              loading={syncing}
            >
              同步状态
            </Button>
          )}
        </Space>
      ),
    },
  ]

  return (
    <div>
      <Title level={2}>存款管理</Title>

      <Card
        title="存款交易列表"
        extra={
          <Space>
            <Button icon={<SyncOutlined />} onClick={() => handleSync()} loading={syncing}>
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

      {/* 存款详情模态框 */}
      <Modal
        title="存款交易详情"
        open={detailModalVisible}
        onCancel={() => {
          setDetailModalVisible(false)
          setSelectedDeposit(null)
        }}
        footer={[
          <Button key="close" onClick={() => {
            setDetailModalVisible(false)
            setSelectedDeposit(null)
          }}>
            关闭
          </Button>,
          selectedDeposit?.status === 'pending' && (
            <Button
              key="sync"
              type="primary"
              onClick={() => {
                if (selectedDeposit) {
                  handleSync(selectedDeposit.tx_hash)
                }
              }}
              loading={syncing}
            >
              同步状态
            </Button>
          ),
        ].filter(Boolean)}
        width={800}
      >
        {selectedDeposit && (
          <Descriptions column={1} bordered>
            <Descriptions.Item label="ID">{selectedDeposit.id}</Descriptions.Item>
            <Descriptions.Item label="公钥">
              <Text copyable={{ text: selectedDeposit.pubkey }} style={{ fontFamily: 'monospace' }}>
                {selectedDeposit.pubkey}
              </Text>
            </Descriptions.Item>
            <Descriptions.Item label="状态">{getStatusTag(selectedDeposit.status)}</Descriptions.Item>
            <Descriptions.Item label="交易哈希">
              {selectedDeposit.tx_hash && !selectedDeposit.tx_hash.startsWith('failed-') ? (
                <Text copyable={{ text: selectedDeposit.tx_hash }} style={{ fontFamily: 'monospace' }}>
                  {selectedDeposit.tx_hash}
                </Text>
              ) : (
                '-'
              )}
            </Descriptions.Item>
            <Descriptions.Item label="批次ID">{selectedDeposit.batch_id || '-'}</Descriptions.Item>
            <Descriptions.Item label="金额 (ETH)">{selectedDeposit.amount_eth.toFixed(8)}</Descriptions.Item>
            {selectedDeposit.amount_wei && (
              <Descriptions.Item label="金额 (Wei)">
                {selectedDeposit.amount_wei.toLocaleString()}
              </Descriptions.Item>
            )}
            <Descriptions.Item label="区块号">
              {selectedDeposit.block_number ? selectedDeposit.block_number.toLocaleString() : '-'}
            </Descriptions.Item>
            <Descriptions.Item label="提交时间">
              {selectedDeposit.submitted_at ? new Date(selectedDeposit.submitted_at).toLocaleString() : '-'}
            </Descriptions.Item>
            <Descriptions.Item label="确认时间">
              {selectedDeposit.confirmed_at ? new Date(selectedDeposit.confirmed_at).toLocaleString() : '-'}
            </Descriptions.Item>
            {selectedDeposit.notes && (
              <Descriptions.Item label="备注">
                <Text type="warning">{selectedDeposit.notes}</Text>
              </Descriptions.Item>
            )}
          </Descriptions>
        )}
      </Modal>
    </div>
  )
}

export default DepositList
