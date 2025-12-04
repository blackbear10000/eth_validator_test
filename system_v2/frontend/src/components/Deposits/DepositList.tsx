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
  DownloadOutlined,
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
  const [statusFilter, setStatusFilter] = useState<string | undefined>(undefined)
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
      // 清理数据：移除空数组、空字符串、null/undefined
      const cleanedValues: any = {
        withdrawal_address: values.withdrawal_address,
      }
      
      // 只有当 pubkeys 不为空时才添加
      if (values.pubkeys && values.pubkeys.length > 0) {
        cleanedValues.pubkeys = values.pubkeys
      }
      
      // amount_eth 必须存在且有效
      if (values.amount_eth !== undefined && values.amount_eth !== null) {
        cleanedValues.amount_eth = values.amount_eth
      }
      
      // fork_version 只有当非空字符串时才添加
      if (values.fork_version && values.fork_version.trim() !== '') {
        cleanedValues.fork_version = values.fork_version.trim()
      }
      
      const response = await depositsApi.generate(cleanedValues) as any
      setGeneratedDepositData(response || [])
      message.success(`成功生成 ${response?.length || 0} 个 Deposit Data`)
      setGenerateModalVisible(false)
      form.resetFields()
      setSubmitModalVisible(true)
    } catch (error: any) {
      message.error(`生成 Deposit Data 失败: ${error.message}`)
    }
  }

  const handleExportDepositData = () => {
    if (generatedDepositData.length === 0) {
      message.warning('请先生成 Deposit Data')
      return
    }

    try {
      // 创建 JSON 文件
      const jsonContent = JSON.stringify(generatedDepositData, null, 2)
      const blob = new Blob([jsonContent], { type: 'application/json' })
      const url = URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = url
      link.download = `deposit_data_${new Date().toISOString().split('T')[0]}.json`
      document.body.appendChild(link)
      link.click()
      document.body.removeChild(link)
      URL.revokeObjectURL(url)
      message.success('Deposit Data 导出成功')
    } catch (error: any) {
      message.error(`导出失败: ${error.message}`)
    }
  }


  const [submitting, setSubmitting] = useState(false)

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

    setSubmitting(true)
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
      // 延迟加载，确保后端已保存记录
      setTimeout(() => {
        loadDeposits()
      }, 1000)
    } catch (error: any) {
      let errorMessage = '提交存款失败'
      if (error?.message) {
        errorMessage = error.message
      } else if (error?.response?.data?.detail) {
        errorMessage = error.response.data.detail
      }
      message.error(`提交存款失败: ${errorMessage}`)
      console.error('提交存款错误详情:', error)
    } finally {
      setSubmitting(false)
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
      // 交易阶段
      submitted: { color: 'orange', text: '已提交' },
      confirmed: { color: 'blue', text: '已确认' },
      
      // 验证阶段
      validated: { color: 'cyan', text: '已验证' },
      invalid: { color: 'red', text: '参数无效' },
      
      // 验证者生命周期
      pending_activation: { color: 'purple', text: '等待激活' },
      activated: { color: 'green', text: '已激活' },
      exiting: { color: 'volcano', text: '退出中' },
      exited: { color: 'default', text: '已退出' },
      
      // 失败状态
      failed: { color: 'red', text: '交易失败' },
      rejected: { color: 'red', text: '交易被拒绝' },
      
      // 向后兼容
      pending: { color: 'orange', text: '等待确认' },
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
      title: '验证者索引',
      dataIndex: 'validator_index',
      key: 'validator_index',
      width: 120,
      render: (index: number | null) => (index !== null && index !== undefined ? index.toLocaleString() : '-'),
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
          {(record.status === 'submitted' || record.status === 'pending' || record.status === 'confirmed') && (
            <Button
              type="link"
              size="small"
              onClick={() => handleSync(record.tx_hash)}
              loading={syncing}
            >
              同步状态
            </Button>
          )}
          {record.status === 'confirmed' && (
            <Button
              type="link"
              size="small"
              onClick={async () => {
                try {
                  await depositsApi.validate(record.tx_hash)
                  message.success('验证请求已提交')
                  setTimeout(() => loadDeposits(), 1000)
                } catch (error: any) {
                  message.error(`验证失败: ${error.message}`)
                }
              }}
            >
              验证交易
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
            <Select
              placeholder="筛选状态"
              allowClear
              style={{ width: 150 }}
              value={statusFilter}
              onChange={(value) => setStatusFilter(value)}
            >
              <Option value="submitted">已提交</Option>
              <Option value="confirmed">已确认</Option>
              <Option value="validated">已验证</Option>
              <Option value="invalid">参数无效</Option>
              <Option value="pending_activation">等待激活</Option>
              <Option value="activated">已激活</Option>
              <Option value="exiting">退出中</Option>
              <Option value="exited">已退出</Option>
              <Option value="failed">交易失败</Option>
              <Option value="rejected">交易被拒绝</Option>
            </Select>
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
          dataSource={deposits.filter((d) => !statusFilter || d.status === statusFilter)}
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
        title={
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <span>提交存款</span>
            <Button
              type="default"
              icon={<DownloadOutlined />}
              onClick={handleExportDepositData}
              disabled={generatedDepositData.length === 0}
            >
              导出 Deposit Data
            </Button>
          </div>
        }
        open={submitModalVisible}
        onCancel={() => {
          setSubmitModalVisible(false)
          submitForm.resetFields()
          setGeneratedDepositData([])
        }}
        onOk={() => submitForm.submit()}
        confirmLoading={submitting}
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
                    {data.withdrawal_credentials && data.withdrawal_credentials.startsWith('01') && (
                      <Descriptions.Item label="提款地址（从提款凭证提取）" span={1}>
                        <Text copyable={{ text: '0x' + data.withdrawal_credentials.slice(-40) }} style={{ fontFamily: 'monospace', fontSize: '12px' }}>
                          {'0x' + data.withdrawal_credentials.slice(-40)}
                        </Text>
                      </Descriptions.Item>
                    )}
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
                    <Descriptions.Item label="Deposit Message Root" span={1}>
                      <Text copyable={{ text: data.deposit_message_root }} style={{ fontFamily: 'monospace', fontSize: '12px' }}>
                        {data.deposit_message_root}
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
                    <Descriptions.Item label="Network Name">
                      <Text code>{data.network_name}</Text>
                    </Descriptions.Item>
                    <Descriptions.Item label="Deposit CLI Version">
                      <Text code>{data.deposit_cli_version}</Text>
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
          (selectedDeposit?.status === 'submitted' || selectedDeposit?.status === 'pending' || selectedDeposit?.status === 'confirmed') && (
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
          selectedDeposit?.status === 'confirmed' && (
            <Button
              key="validate"
              onClick={async () => {
                if (selectedDeposit) {
                  try {
                    await depositsApi.validate(selectedDeposit.tx_hash)
                    message.success('验证请求已提交')
                    setTimeout(() => {
                      loadDeposits()
                      if (selectedDeposit) {
                        handleViewDetail(selectedDeposit)
                      }
                    }, 1000)
                  } catch (error: any) {
                    message.error(`验证失败: ${error.message}`)
                  }
                }
              }}
            >
              验证交易
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
            {selectedDeposit.validated_at && (
              <Descriptions.Item label="验证时间">
                {new Date(selectedDeposit.validated_at).toLocaleString()}
              </Descriptions.Item>
            )}
            {selectedDeposit.validator_index !== null && selectedDeposit.validator_index !== undefined && (
              <Descriptions.Item label="验证者索引">
                {selectedDeposit.validator_index.toLocaleString()}
              </Descriptions.Item>
            )}
            {selectedDeposit.activation_epoch !== null && selectedDeposit.activation_epoch !== undefined && (
              <Descriptions.Item label="激活 Epoch">
                {selectedDeposit.activation_epoch.toLocaleString()}
              </Descriptions.Item>
            )}
            {selectedDeposit.exit_epoch !== null && selectedDeposit.exit_epoch !== undefined && (
              <Descriptions.Item label="退出 Epoch">
                {selectedDeposit.exit_epoch.toLocaleString()}
              </Descriptions.Item>
            )}
            {selectedDeposit.effective_balance_gwei !== null && selectedDeposit.effective_balance_gwei !== undefined && (
              <Descriptions.Item label="有效余额">
                {(selectedDeposit.effective_balance_gwei / 1e9).toFixed(4)} ETH ({selectedDeposit.effective_balance_gwei.toLocaleString()} Gwei)
              </Descriptions.Item>
            )}
            {selectedDeposit.validation_error && (
              <Descriptions.Item label="验证错误">
                <Text type="danger">{selectedDeposit.validation_error}</Text>
              </Descriptions.Item>
            )}
            {selectedDeposit.status_history && selectedDeposit.status_history.length > 0 && (
              <Descriptions.Item label="状态历史">
                <Collapse>
                  {selectedDeposit.status_history.map((history, index) => (
                    <Panel
                      key={index}
                      header={`${history.from_status} → ${history.to_status} (${new Date(history.timestamp).toLocaleString()})`}
                    >
                      <Text type="secondary">{history.reason || '状态变更'}</Text>
                    </Panel>
                  ))}
                </Collapse>
              </Descriptions.Item>
            )}
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
