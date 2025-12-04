import React, { useState, useEffect } from 'react'
import {
  Card,
  Table,
  Button,
  Space,
  Modal,
  Form,
  Input,
  InputNumber,
  message,
  Descriptions,
  Tag,
  Row,
  Col,
  Statistic,
  Typography,
  Tooltip,
} from 'antd'
import {
  PlusOutlined,
  EyeOutlined,
  CopyOutlined,
  ReloadOutlined,
} from '@ant-design/icons'
import { depositsApi, BatchDepositContract, BatchContractStatistics } from '../../api/deposits'
import { networkApi, NetworkInfo } from '../../api/network'
import dayjs from 'dayjs'

const { Title } = Typography

const BatchContractManager: React.FC = () => {
  const [contracts, setContracts] = useState<BatchDepositContract[]>([])
  const [loading, setLoading] = useState(false)
  const [deploying, setDeploying] = useState(false)
  const [deployModalVisible, setDeployModalVisible] = useState(false)
  const [detailModalVisible, setDetailModalVisible] = useState(false)
  const [selectedContract, setSelectedContract] = useState<BatchDepositContract | null>(null)
  const [statistics, setStatistics] = useState<BatchContractStatistics | null>(null)
  const [statisticsLoading, setStatisticsLoading] = useState(false)
  const [rpcEndpoints, setRpcEndpoints] = useState<any>(null)
  const [networkInfo, setNetworkInfo] = useState<NetworkInfo | null>(null)
  
  const [deployForm] = Form.useForm()

  // 将 RPC URL 中的 localhost 替换为 host.docker.internal
  const replaceLocalhostWithDockerHost = (url: string | undefined): string | undefined => {
    if (!url) return url
    return url.replace(/localhost/g, 'host.docker.internal')
  }

  // 加载合约列表
  const loadContracts = async () => {
    setLoading(true)
    try {
      const response = await depositsApi.listBatchContracts() as any
      // apiClient 的响应拦截器已经返回了 response.data，所以这里直接使用 response
      // 如果 response 是数组，直接使用；否则尝试 response.data
      const contractsList = Array.isArray(response) ? response : (response?.data || response || [])
      setContracts(contractsList)
      console.log('加载的合约列表:', contractsList, '总数:', contractsList.length)
    } catch (error: any) {
      message.error(`加载合约列表失败: ${error.message}`)
      console.error('加载合约列表错误:', error)
      setContracts([])
    } finally {
      setLoading(false)
    }
  }

  // 加载 RPC 端点信息
  const loadRpcEndpoints = async () => {
    try {
      const endpoints = await networkApi.getRpcEndpoints()
      // 替换 localhost 为 host.docker.internal
      const processedEndpoints = {
        ...endpoints,
        host_rpc_url: replaceLocalhostWithDockerHost(endpoints.host_rpc_url),
        rpc_url: replaceLocalhostWithDockerHost(endpoints.rpc_url),
      }
      setRpcEndpoints(processedEndpoints)
    } catch (error) {
      console.warn('无法获取 RPC 端点:', error)
    }
  }

  // 加载网络信息
  const loadNetworkInfo = async () => {
    try {
      const response = await networkApi.getInfo() as any
      setNetworkInfo(response.data || response)
    } catch (error) {
      console.warn('无法获取网络信息:', error)
    }
  }

  // 加载统计数据
  const loadStatistics = async (contractId: number) => {
    setStatisticsLoading(true)
    try {
      const response = await depositsApi.getBatchContractStatistics(contractId) as any
      // apiClient 的响应拦截器已经返回了 response.data
      setStatistics(response.data || response)
    } catch (error: any) {
      message.error(`加载统计数据失败: ${error.message}`)
      setStatistics(null)
    } finally {
      setStatisticsLoading(false)
    }
  }

  useEffect(() => {
    loadContracts()
    loadRpcEndpoints()
    loadNetworkInfo()
  }, [])

  // 部署合约
  const handleDeployContract = async (values: any) => {
    setDeploying(true)
    try {
      // 如果没有提供 deposit_contract_address，尝试从网络信息获取
      if (!values.deposit_contract_address) {
        if (networkInfo?.deposit_contract_address) {
          values.deposit_contract_address = networkInfo.deposit_contract_address
        }
      }

      // 替换 RPC URL 中的 localhost 为 host.docker.internal
      if (values.rpc_url) {
        values.rpc_url = replaceLocalhostWithDockerHost(values.rpc_url)
      }

      const result = await depositsApi.deployBatchContract(values) as any
      // apiClient 的响应拦截器已经返回了 response.data
      const contractAddress = result?.contract_address || result?.data?.contract_address
      message.success(`Batch Deposit 合约部署成功: ${contractAddress}`)
      setDeployModalVisible(false)
      deployForm.resetFields()
      loadContracts()
    } catch (error: any) {
      let errorMessage = '部署合约失败'
      if (error?.message) {
        errorMessage = error.message
      } else if (error?.response?.data?.detail) {
        errorMessage = error.response.data.detail
      }
      message.error(`部署合约失败: ${errorMessage}`)
      console.error('部署合约错误详情:', error)
    } finally {
      setDeploying(false)
    }
  }

  // 查看详情
  const handleViewDetails = async (contract: BatchDepositContract) => {
    setSelectedContract(contract)
    setDetailModalVisible(true)
    await loadStatistics(contract.id)
  }

  // 复制地址
  const handleCopyAddress = (address: string) => {
    navigator.clipboard.writeText(address)
    message.success('地址已复制到剪贴板')
  }

  // 格式化地址显示
  const formatAddress = (address: string) => {
    if (!address) return ''
    return `${address.slice(0, 6)}...${address.slice(-6)}`
  }

  // 计算总体统计（仅显示合约数量，详细统计需要查看单个合约详情）
  const totalStats = {
    totalContracts: contracts.length,
  }

  const columns = [
    {
      title: '合约地址',
      dataIndex: 'contract_address',
      key: 'contract_address',
      render: (address: string) => (
        <Space>
          <span style={{ fontFamily: 'monospace' }}>{formatAddress(address)}</span>
          <Tooltip title="复制地址">
            <Button
              type="text"
              size="small"
              icon={<CopyOutlined />}
              onClick={() => handleCopyAddress(address)}
            />
          </Tooltip>
        </Space>
      ),
    },
    {
      title: '网络名称',
      dataIndex: 'network_name',
      key: 'network_name',
    },
    {
      title: '部署者',
      dataIndex: 'deployer_address',
      key: 'deployer_address',
      render: (address: string) => (
        <span style={{ fontFamily: 'monospace', fontSize: '12px' }}>
          {formatAddress(address)}
        </span>
      ),
    },
    {
      title: '部署时间',
      dataIndex: 'deployed_at',
      key: 'deployed_at',
      render: (time: string) => dayjs(time).format('YYYY-MM-DD HH:mm:ss'),
    },
    {
      title: '操作',
      key: 'action',
      render: (_: any, record: BatchDepositContract) => (
        <Space>
          <Button
            type="link"
            icon={<EyeOutlined />}
            onClick={() => handleViewDetails(record)}
          >
            查看详情
          </Button>
        </Space>
      ),
    },
  ]

  return (
    <div>
      <div style={{ marginBottom: 24, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <Title level={2}>Batch Deposit 合约管理</Title>
        <Space>
          <Button icon={<ReloadOutlined />} onClick={loadContracts}>
            刷新
          </Button>
          <Button
            type="primary"
            icon={<PlusOutlined />}
            onClick={() => setDeployModalVisible(true)}
          >
            部署新合约
          </Button>
        </Space>
      </div>

      {/* 统计卡片 */}
      <Row gutter={16} style={{ marginBottom: 24 }}>
        <Col span={24}>
          <Card>
            <Statistic
              title="已部署合约总数"
              value={totalStats.totalContracts}
              prefix={<PlusOutlined />}
            />
            <div style={{ marginTop: 16, fontSize: '12px', color: '#666' }}>
              提示：点击"查看详情"可查看单个合约的详细统计数据（存款数量、总金额、验证者数量等）
            </div>
          </Card>
        </Col>
      </Row>

      {/* 合约列表 */}
      <Card>
        <Table
          columns={columns}
          dataSource={contracts}
          loading={loading}
          rowKey="id"
          pagination={{
            showSizeChanger: true,
            showQuickJumper: true,
            showTotal: (total) => `共 ${total} 个合约`,
          }}
        />
      </Card>

      {/* 部署合约模态框 */}
      <Modal
        title="部署 Batch Deposit 合约"
        open={deployModalVisible}
        onCancel={() => {
          setDeployModalVisible(false)
          deployForm.resetFields()
        }}
        onOk={() => deployForm.submit()}
        confirmLoading={deploying}
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
            help={
              <div>
                {rpcEndpoints?.host_rpc_url ? (
                  <div style={{ marginBottom: 8 }}>
                    <span style={{ color: '#52c41a' }}>✓ 已自动检测到 RPC URL: </span>
                    <span style={{ fontFamily: 'monospace' }}>{rpcEndpoints.host_rpc_url}</span>
                  </div>
                ) : rpcEndpoints?.error ? (
                  <div style={{ marginBottom: 8, color: '#faad14' }}>
                    ⚠ {rpcEndpoints.error}
                  </div>
                ) : null}
              </div>
            }
          >
            <Input
              placeholder={rpcEndpoints?.host_rpc_url || "http://host.docker.internal:8545（留空则自动获取）"}
            />
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
            name="deposit_contract_address"
            label="官方 Deposit 合约地址（可选，留空则自动从网络配置获取）"
            help="如果不提供，系统会尝试从 Kurtosis 网络配置中自动获取"
          >
            <Input placeholder={networkInfo?.deposit_contract_address || "0x4242424242424242424242424242424242424242（留空则自动获取）"} />
          </Form.Item>
          <Form.Item
            name="initial_fee"
            label="初始费用（可选，默认 0，必须是 gwei 的倍数）"
            help="1 gwei = 10^9 wei，例如：0 gwei = 0, 1 gwei = 1000000000"
          >
            <InputNumber
              style={{ width: '100%' }}
              placeholder="初始费用（wei）"
              min={0}
              step={1000000000}
            />
          </Form.Item>
          <Form.Item
            name="gas_price"
            label="Gas 价格（可选，单位：wei）"
          >
            <InputNumber
              style={{ width: '100%' }}
              placeholder="Gas 价格（wei）"
              min={0}
            />
          </Form.Item>
          <Form.Item
            name="gas_limit"
            label="Gas 限制（可选）"
          >
            <InputNumber
              style={{ width: '100%' }}
              placeholder="Gas 限制"
              min={0}
            />
          </Form.Item>
        </Form>
      </Modal>

      {/* 详情模态框 */}
      <Modal
        title="合约详情"
        open={detailModalVisible}
        onCancel={() => {
          setDetailModalVisible(false)
          setSelectedContract(null)
          setStatistics(null)
        }}
        footer={[
          <Button key="close" onClick={() => {
            setDetailModalVisible(false)
            setSelectedContract(null)
            setStatistics(null)
          }}>
            关闭
          </Button>,
        ]}
        width={800}
      >
        {selectedContract && (
          <div>
            <Descriptions title="基本信息" bordered column={2} style={{ marginBottom: 24 }}>
              <Descriptions.Item label="合约地址" span={2}>
                <Space>
                  <span style={{ fontFamily: 'monospace' }}>{selectedContract.contract_address}</span>
                  <Button
                    type="link"
                    size="small"
                    icon={<CopyOutlined />}
                    onClick={() => handleCopyAddress(selectedContract.contract_address)}
                  >
                    复制
                  </Button>
                </Space>
              </Descriptions.Item>
              <Descriptions.Item label="网络名称">
                {selectedContract.network_name}
              </Descriptions.Item>
              <Descriptions.Item label="RPC URL">
                <span style={{ fontFamily: 'monospace', fontSize: '12px' }}>
                  {selectedContract.rpc_url}
                </span>
              </Descriptions.Item>
              <Descriptions.Item label="部署者地址">
                <span style={{ fontFamily: 'monospace', fontSize: '12px' }}>
                  {selectedContract.deployer_address}
                </span>
              </Descriptions.Item>
              <Descriptions.Item label="部署交易哈希">
                <span style={{ fontFamily: 'monospace', fontSize: '12px' }}>
                  {selectedContract.deployment_tx_hash}
                </span>
              </Descriptions.Item>
              <Descriptions.Item label="部署区块号">
                {selectedContract.block_number || 'N/A'}
              </Descriptions.Item>
              <Descriptions.Item label="Gas 使用量">
                {selectedContract.gas_used ? `${selectedContract.gas_used}` : 'N/A'}
              </Descriptions.Item>
              <Descriptions.Item label="部署时间">
                {dayjs(selectedContract.deployed_at).format('YYYY-MM-DD HH:mm:ss')}
              </Descriptions.Item>
              {selectedContract.notes && (
                <Descriptions.Item label="备注" span={2}>
                  {selectedContract.notes}
                </Descriptions.Item>
              )}
            </Descriptions>

            <Descriptions title="统计数据" bordered column={2}>
              {statisticsLoading ? (
                <Descriptions.Item span={2}>加载中...</Descriptions.Item>
              ) : statistics ? (
                <>
                  <Descriptions.Item label="存款交易数量">
                    {statistics.deposit_count}
                  </Descriptions.Item>
                  <Descriptions.Item label="总存款金额">
                    {statistics.total_amount_eth.toFixed(4)} ETH
                  </Descriptions.Item>
                  <Descriptions.Item label="验证者数量">
                    {statistics.validator_count}
                  </Descriptions.Item>
                  <Descriptions.Item label="合约费用">
                    {statistics.contract_fee_gwei !== null && statistics.contract_fee_gwei !== undefined
                      ? `${statistics.contract_fee_gwei} gwei`
                      : statistics.contract_fee_wei !== null && statistics.contract_fee_wei !== undefined
                      ? `${statistics.contract_fee_wei} wei`
                      : 'N/A'}
                  </Descriptions.Item>
                  <Descriptions.Item label="合约余额">
                    {statistics.contract_balance_eth !== null && statistics.contract_balance_eth !== undefined
                      ? `${statistics.contract_balance_eth.toFixed(4)} ETH`
                      : statistics.contract_balance_wei !== null && statistics.contract_balance_wei !== undefined
                      ? `${statistics.contract_balance_wei} wei`
                      : 'N/A'}
                  </Descriptions.Item>
                  <Descriptions.Item label="合约状态">
                    {statistics.is_paused !== null && statistics.is_paused !== undefined ? (
                      <Tag color={statistics.is_paused ? 'red' : 'green'}>
                        {statistics.is_paused ? '已暂停' : '运行中'}
                      </Tag>
                    ) : (
                      'N/A'
                    )}
                  </Descriptions.Item>
                  {statistics.owner_address && (
                    <Descriptions.Item label="所有者地址" span={2}>
                      <span style={{ fontFamily: 'monospace', fontSize: '12px' }}>
                        {statistics.owner_address}
                      </span>
                    </Descriptions.Item>
                  )}
                </>
              ) : (
                <Descriptions.Item span={2}>
                  {statisticsLoading ? '加载中...' : '无法加载统计数据'}
                </Descriptions.Item>
              )}
            </Descriptions>
          </div>
        )}
      </Modal>
    </div>
  )
}

export default BatchContractManager

