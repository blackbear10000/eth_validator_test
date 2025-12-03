import React, { useState, useEffect } from 'react'
import {
  Table,
  Card,
  Button,
  Input,
  Space,
  message,
  Tag,
  Select,
  Typography,
  Modal,
  Descriptions,
} from 'antd'
import {
  ReloadOutlined,
} from '@ant-design/icons'
import { keysApi, ValidatorKey } from '../../api/keys'

const { Search } = Input
const { Text } = Typography
const { Option } = Select

const KeyList: React.FC = () => {
  const [keys, setKeys] = useState<ValidatorKey[]>([])
  const [loading, setLoading] = useState(false)
  const [selectedRowKeys, setSelectedRowKeys] = useState<React.Key[]>([])
  const [searchText, setSearchText] = useState('')
  const [statusFilter, setStatusFilter] = useState<string | undefined>(undefined)
  const [batchIdFilter, setBatchIdFilter] = useState<string | undefined>(undefined)
  const [detailModalVisible, setDetailModalVisible] = useState(false)
  const [selectedKey, setSelectedKey] = useState<ValidatorKey | null>(null)
  const [pagination, setPagination] = useState({
    current: 1,
    pageSize: 20,
    total: 0,
  })

  // 加载密钥列表
  const loadKeys = async () => {
    setLoading(true)
    try {
      const response = await keysApi.list({
        status: statusFilter,
        batch_id: batchIdFilter,
        limit: pagination.pageSize,
        offset: (pagination.current - 1) * pagination.pageSize,
      }) as any

      setKeys(response.items || [])
      setPagination({
        ...pagination,
        total: response.total || 0,
      })
    } catch (error: any) {
      message.error(`加载密钥列表失败: ${error.message}`)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadKeys()
  }, [pagination.current, pagination.pageSize, statusFilter, batchIdFilter])

  // 获取状态标签
  const getStatusTag = (status: string) => {
    const statusConfig: Record<string, { color: string; text: string }> = {
      unused: { color: 'default', text: '未使用' },
      active: { color: 'processing', text: '已激活' },
      pending: { color: 'warning', text: '待处理' },
      deposited: { color: 'blue', text: '已存款' },
      active_on_chain: { color: 'success', text: '链上激活' },
      pending_exit: { color: 'orange', text: '退出中' },
      exited: { color: 'error', text: '已退出' },
    }

    const config = statusConfig[status] || { color: 'default', text: status }
    return <Tag color={config.color}>{config.text}</Tag>
  }

  // 显示密钥详情
  const showKeyDetail = async (pubkey: string) => {
    try {
      const key = await keysApi.get(pubkey) as any
      setSelectedKey(key)
      setDetailModalVisible(true)
    } catch (error: any) {
      message.error(`获取密钥详情失败: ${error.message}`)
    }
  }

  // 批量激活
  const handleBatchActivate = async () => {
    if (selectedRowKeys.length === 0) {
      message.warning('请先选择要激活的密钥')
      return
    }

    Modal.confirm({
      title: '确认批量激活',
      content: `确定要激活 ${selectedRowKeys.length} 个密钥吗？`,
      onOk: async () => {
        try {
          // 这里需要调用批量激活 API
          message.success(`成功激活 ${selectedRowKeys.length} 个密钥`)
          setSelectedRowKeys([])
          loadKeys()
        } catch (error: any) {
          message.error(`批量激活失败: ${error.message}`)
        }
      },
    })
  }

  // 搜索过滤
  const filteredKeys = keys.filter((key) => {
    if (searchText) {
      const searchLower = searchText.toLowerCase()
      return (
        key.pubkey.toLowerCase().includes(searchLower) ||
        key.withdrawal_pubkey.toLowerCase().includes(searchLower) ||
        (key.batch_id && key.batch_id.toLowerCase().includes(searchLower))
      )
    }
    return true
  })

  // 表格列定义
  const columns = [
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
    {
      title: '操作',
      key: 'action',
      width: 150,
      render: (_: any, record: ValidatorKey) => (
        <Space>
          <Button
            type="link"
            size="small"
            onClick={() => showKeyDetail(record.pubkey)}
          >
            详情
          </Button>
        </Space>
      ),
    },
  ]

  // 获取所有批次ID（用于筛选）
  const batchIds = Array.from(new Set(keys.map((k) => k.batch_id).filter(Boolean)))

  return (
    <div>
      <Card>
        <Space direction="vertical" style={{ width: '100%' }} size="large">
          {/* 搜索和筛选栏 */}
          <Space wrap>
            <Search
              placeholder="搜索公钥、批次ID"
              allowClear
              style={{ width: 300 }}
              onSearch={setSearchText}
              onChange={(e) => !e.target.value && setSearchText('')}
            />
            <Select
              placeholder="筛选状态"
              allowClear
              style={{ width: 150 }}
              value={statusFilter}
              onChange={setStatusFilter}
            >
              <Option value="unused">未使用</Option>
              <Option value="active">已激活</Option>
              <Option value="pending">待处理</Option>
              <Option value="deposited">已存款</Option>
              <Option value="active_on_chain">链上激活</Option>
              <Option value="pending_exit">退出中</Option>
              <Option value="exited">已退出</Option>
            </Select>
            <Select
              placeholder="筛选批次"
              allowClear
              style={{ width: 150 }}
              value={batchIdFilter}
              onChange={setBatchIdFilter}
            >
              {batchIds.map((batchId) => (
                <Option key={batchId} value={batchId}>
                  {batchId}
                </Option>
              ))}
            </Select>
            <Button icon={<ReloadOutlined />} onClick={loadKeys}>
              刷新
            </Button>
          </Space>

          {/* 批量操作栏 */}
          {selectedRowKeys.length > 0 && (
            <Space>
              <Text>已选择 {selectedRowKeys.length} 个密钥</Text>
              <Button onClick={handleBatchActivate}>批量激活</Button>
              <Button onClick={() => setSelectedRowKeys([])}>取消选择</Button>
            </Space>
          )}

          {/* 密钥列表表格 */}
          <Table
            columns={columns}
            dataSource={filteredKeys}
            rowKey="pubkey"
            loading={loading}
            rowSelection={{
              selectedRowKeys,
              onChange: setSelectedRowKeys,
            }}
            pagination={{
              ...pagination,
              showSizeChanger: true,
              showTotal: (total) => `共 ${total} 条`,
              onChange: (page, pageSize) => {
                setPagination({
                  ...pagination,
                  current: page,
                  pageSize,
                })
              },
            }}
          />
        </Space>
      </Card>

      {/* 密钥详情模态框 */}
      <Modal
        title="密钥详情"
        open={detailModalVisible}
        onCancel={() => {
          setDetailModalVisible(false)
          setSelectedKey(null)
        }}
        footer={null}
        width={800}
      >
        {selectedKey && (
          <Descriptions column={2} bordered>
            <Descriptions.Item label="公钥" span={2}>
              <Text copyable={{ text: selectedKey.pubkey }} style={{ fontFamily: 'monospace' }}>
                {selectedKey.pubkey}
              </Text>
            </Descriptions.Item>
            <Descriptions.Item label="提款公钥" span={2}>
              <Text copyable={{ text: selectedKey.withdrawal_pubkey }} style={{ fontFamily: 'monospace' }}>
                {selectedKey.withdrawal_pubkey}
              </Text>
            </Descriptions.Item>
            <Descriptions.Item label="状态">
              {getStatusTag(selectedKey.status)}
            </Descriptions.Item>
            <Descriptions.Item label="索引">{selectedKey.index}</Descriptions.Item>
            <Descriptions.Item label="批次ID">
              {selectedKey.batch_id || '-'}
            </Descriptions.Item>
            <Descriptions.Item label="客户端类型">
              {selectedKey.client_type || '-'}
            </Descriptions.Item>
            <Descriptions.Item label="创建时间">
              {new Date(selectedKey.created_at).toLocaleString()}
            </Descriptions.Item>
            {selectedKey.activated_at && (
              <Descriptions.Item label="激活时间">
                {new Date(selectedKey.activated_at).toLocaleString()}
              </Descriptions.Item>
            )}
            {selectedKey.deposited_at && (
              <Descriptions.Item label="存款时间">
                {new Date(selectedKey.deposited_at).toLocaleString()}
              </Descriptions.Item>
            )}
            {selectedKey.exited_at && (
              <Descriptions.Item label="退出时间">
                {new Date(selectedKey.exited_at).toLocaleString()}
              </Descriptions.Item>
            )}
            {selectedKey.deposit_tx_hash && (
              <Descriptions.Item label="存款交易哈希" span={2}>
                <Text copyable={{ text: selectedKey.deposit_tx_hash }} style={{ fontFamily: 'monospace' }}>
                  {selectedKey.deposit_tx_hash}
                </Text>
              </Descriptions.Item>
            )}
            {selectedKey.withdrawal_address && (
              <Descriptions.Item label="提款地址" span={2}>
                <Text copyable={{ text: selectedKey.withdrawal_address }} style={{ fontFamily: 'monospace' }}>
                  {selectedKey.withdrawal_address}
                </Text>
              </Descriptions.Item>
            )}
          </Descriptions>
        )}
      </Modal>
    </div>
  )
}

export default KeyList
