import React, { useState, useEffect } from 'react'
import {
  Table,
  Card,
  Button,
  Input,
  Space,
  message,
  Modal,
  Tag,
  Popconfirm,
  Typography,
  Tabs,
  Select,
} from 'antd'
import {
  ExportOutlined,
  DeleteOutlined,
  CheckCircleOutlined,
  HistoryOutlined,
} from '@ant-design/icons'
import { exitsApi } from '../../api/exits'
import { keysApi } from '../../api/keys'
import dayjs from 'dayjs'

const { Search } = Input
const { Text } = Typography
const { TabPane } = Tabs

interface ValidatorKey {
  pubkey: string
  status: string
  withdrawal_address: string
  index: number
}

interface ExitRecord {
  id: number
  pubkey: string
  validator_index: number | null
  exit_epoch: number
  withdrawable_epoch: number | null
  balance_before_exit_eth: number | null
  status: string
  submitted_at: string
  confirmed_at: string | null
}

const ExitList: React.FC = () => {
  const [keys, setKeys] = useState<ValidatorKey[]>([])
  const [loading, setLoading] = useState(false)
  const [selectedKeys, setSelectedKeys] = useState<string[]>([])
  const [exitModalVisible, setExitModalVisible] = useState(false)
  const [exitingKey, setExitingKey] = useState<string | null>(null)
  const [exitData, setExitData] = useState<any>(null)
  
  // 退出记录相关状态
  const [exitRecords, setExitRecords] = useState<ExitRecord[]>([])
  const [recordsLoading, setRecordsLoading] = useState(false)
  const [recordsFilter, setRecordsFilter] = useState<{ status?: string }>({})

  // 加载可退出验证者列表
  const loadKeys = async () => {
    setLoading(true)
    try {
      const response = await keysApi.list({
        status: 'active_on_chain',
        limit: 1000,
      }) as any
      setKeys(response.items || [])
    } catch (error: any) {
      message.error(`加载验证者列表失败: ${error.message}`)
    } finally {
      setLoading(false)
    }
  }

  // 加载退出记录
  const loadExitRecords = async () => {
    setRecordsLoading(true)
    try {
      const response = await exitsApi.getExitRecords({
        status: recordsFilter.status,
        limit: 100,
      }) as any
      setExitRecords(response.items || [])
    } catch (error: any) {
      message.error(`加载退出记录失败: ${error.message}`)
    } finally {
      setRecordsLoading(false)
    }
  }

  useEffect(() => {
    loadKeys()
    loadExitRecords()
  }, [])

  useEffect(() => {
    loadExitRecords()
  }, [recordsFilter])

  // 生成退出签名
  const handleGenerateExit = async (pubkey: string) => {
    try {
      const response = await exitsApi.generateExit(pubkey)
      setExitData(response)
      setExitingKey(pubkey)
      setExitModalVisible(true)
    } catch (error: any) {
      message.error(`生成退出签名失败: ${error.message}`)
    }
  }

  // 提交退出
  const handleSubmitExit = async () => {
    if (!exitingKey) return

    try {
      await exitsApi.submitExit(exitingKey)
      message.success('退出请求已提交')
      setExitModalVisible(false)
      setExitingKey(null)
      setExitData(null)
      loadKeys()
    } catch (error: any) {
      message.error(`提交退出失败: ${error.message}`)
    }
  }

  // 批量退出
  const handleBatchExit = async () => {
    if (selectedKeys.length === 0) {
      message.warning('请先选择要退出的验证者')
      return
    }

    Modal.confirm({
      title: '确认批量退出',
      content: `确定要退出 ${selectedKeys.length} 个验证者吗？`,
      onOk: async () => {
        try {
          const response = await exitsApi.batchExit(selectedKeys) as any
          const successCount = response.results?.filter(
            (r: any) => r.status === 'success'
          ).length || 0
          message.success(`批量退出完成: ${successCount}/${selectedKeys.length} 成功`)
          setSelectedKeys([])
          loadKeys()
        } catch (error: any) {
          message.error(`批量退出失败: ${error.message}`)
        }
      },
    })
  }

  // 完成退出流程
  const handleCompleteExit = async (pubkey: string) => {
    try {
      await exitsApi.completeExit(pubkey)
      message.success('退出流程已完成')
      loadKeys()
    } catch (error: any) {
      message.error(`完成退出流程失败: ${error.message}`)
    }
  }

  // 移除已退出密钥
  const handleRemoveKey = async (pubkey: string) => {
    try {
      await exitsApi.removeKey(pubkey)
      message.success('密钥已从系统移除')
      loadKeys()
    } catch (error: any) {
      message.error(`移除密钥失败: ${error.message}`)
    }
  }

  const columns = [
    {
      title: '公钥',
      dataIndex: 'pubkey',
      key: 'pubkey',
      render: (text: string) => (
        <Text copyable={{ text }} style={{ fontFamily: 'monospace' }}>
          {text.substring(0, 20)}...
        </Text>
      ),
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      render: (status: string) => {
        const statusMap: Record<string, { color: string; text: string }> = {
          active_on_chain: { color: 'green', text: '运行中' },
          pending_exit: { color: 'orange', text: '退出中' },
          exited: { color: 'red', text: '已退出' },
        }
        const config = statusMap[status] || { color: 'default', text: status }
        return <Tag color={config.color}>{config.text}</Tag>
      },
    },
    {
      title: '索引',
      dataIndex: 'index',
      key: 'index',
    },
    {
      title: '提款地址',
      dataIndex: 'withdrawal_address',
      key: 'withdrawal_address',
      render: (text: string) => (
        <Text copyable={{ text }} style={{ fontFamily: 'monospace' }}>
          {text?.substring(0, 20)}...
        </Text>
      ),
    },
    {
      title: '操作',
      key: 'action',
      render: (_: any, record: ValidatorKey) => (
        <Space>
          {record.status === 'active_on_chain' && (
            <Button
              size="small"
              icon={<ExportOutlined />}
              onClick={() => handleGenerateExit(record.pubkey)}
            >
              退出
            </Button>
          )}
          {record.status === 'pending_exit' && (
            <Button
              size="small"
              icon={<CheckCircleOutlined />}
              onClick={() => handleCompleteExit(record.pubkey)}
            >
              完成退出
            </Button>
          )}
          {record.status === 'exited' && (
            <Popconfirm
              title="确定要从系统移除这个密钥吗？"
              onConfirm={() => handleRemoveKey(record.pubkey)}
            >
              <Button size="small" danger icon={<DeleteOutlined />}>
                移除
              </Button>
            </Popconfirm>
          )}
        </Space>
      ),
    },
  ]

  const exitRecordColumns = [
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
      render: (text: string) => (
        <Text copyable={{ text }} style={{ fontFamily: 'monospace' }}>
          {text.substring(0, 20)}...
        </Text>
      ),
    },
    {
      title: '验证者索引',
      dataIndex: 'validator_index',
      key: 'validator_index',
      width: 120,
      render: (index: number | null) => index ?? '-',
    },
    {
      title: '退出 Epoch',
      dataIndex: 'exit_epoch',
      key: 'exit_epoch',
      width: 120,
    },
    {
      title: '预计可取款 Epoch',
      dataIndex: 'withdrawable_epoch',
      key: 'withdrawable_epoch',
      width: 150,
      render: (epoch: number | null) => epoch ?? '-',
    },
    {
      title: '退出前余额 (ETH)',
      dataIndex: 'balance_before_exit_eth',
      key: 'balance_before_exit_eth',
      width: 150,
      render: (balance: number | null) => balance ? balance.toFixed(4) : '-',
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      width: 120,
      render: (status: string) => {
        const statusMap: Record<string, { color: string; text: string }> = {
          submitted: { color: 'blue', text: '已提交' },
          confirmed: { color: 'green', text: '已确认' },
          withdrawable: { color: 'orange', text: '可取款' },
          completed: { color: 'default', text: '已完成' },
        }
        const config = statusMap[status] || { color: 'default', text: status }
        return <Tag color={config.color}>{config.text}</Tag>
      },
    },
    {
      title: '提交时间',
      dataIndex: 'submitted_at',
      key: 'submitted_at',
      width: 180,
      render: (time: string) => dayjs(time).format('YYYY-MM-DD HH:mm:ss'),
    },
    {
      title: '确认时间',
      dataIndex: 'confirmed_at',
      key: 'confirmed_at',
      width: 180,
      render: (time: string | null) => time ? dayjs(time).format('YYYY-MM-DD HH:mm:ss') : '-',
    },
  ]

  return (
    <div>
      <Card>
        <Tabs defaultActiveKey="validators">
          <TabPane
            tab={
              <span>
                <ExportOutlined /> 可退出验证者
              </span>
            }
            key="validators"
          >
            <Card
              title="验证者退出管理"
              extra={
                <Space>
                  <Search
                    placeholder="搜索公钥"
                    style={{ width: 300 }}
                    onSearch={(_value) => {
                      // TODO: 实现搜索
                      message.info('搜索功能待实现')
                    }}
                  />
                  <Button
                    type="primary"
                    onClick={handleBatchExit}
                    disabled={selectedKeys.length === 0}
                  >
                    批量退出 ({selectedKeys.length})
                  </Button>
                  <Button onClick={loadKeys}>刷新</Button>
                </Space>
              }
            >
              <Table
                columns={columns}
                dataSource={keys}
                rowKey="pubkey"
                loading={loading}
                rowSelection={{
                  selectedRowKeys: selectedKeys,
                  onChange: (keys) => setSelectedKeys(keys as string[]),
                  getCheckboxProps: (record) => ({
                    disabled: record.status !== 'active_on_chain',
                  }),
                }}
                pagination={{
                  pageSize: 50,
                  showSizeChanger: true,
                  showTotal: (total) => `共 ${total} 个验证者`,
                }}
              />
            </Card>
          </TabPane>
          <TabPane
            tab={
              <span>
                <HistoryOutlined /> 退出记录
              </span>
            }
            key="records"
          >
            <Card
              title="退出记录"
              extra={
                <Space>
                  <Select
                    placeholder="状态筛选"
                    allowClear
                    style={{ width: 150 }}
                    value={recordsFilter.status}
                    onChange={(value) => setRecordsFilter({ ...recordsFilter, status: value })}
                  >
                    <Select.Option value="submitted">已提交</Select.Option>
                    <Select.Option value="confirmed">已确认</Select.Option>
                    <Select.Option value="withdrawable">可取款</Select.Option>
                    <Select.Option value="completed">已完成</Select.Option>
                  </Select>
                  <Button onClick={loadExitRecords}>刷新</Button>
                </Space>
              }
            >
              <Table
                columns={exitRecordColumns}
                dataSource={exitRecords}
                rowKey="id"
                loading={recordsLoading}
                pagination={{
                  pageSize: 50,
                  showSizeChanger: true,
                  showTotal: (total) => `共 ${total} 条记录`,
                }}
              />
            </Card>
          </TabPane>
        </Tabs>
      </Card>

      {/* 退出确认对话框 */}
      <Modal
        title="确认退出"
        open={exitModalVisible}
        onOk={handleSubmitExit}
        onCancel={() => {
          setExitModalVisible(false)
          setExitingKey(null)
          setExitData(null)
        }}
        okText="确认退出"
        cancelText="取消"
      >
        {exitData && (
          <div>
            <p>验证者公钥: {exitingKey}</p>
            <p>
              退出 Epoch:{' '}
              {exitData.message?.epoch || 'N/A'}
            </p>
            <p>
              验证者索引:{' '}
              {exitData.message?.validator_index || 'N/A'}
            </p>
            <p style={{ color: 'orange' }}>
              警告: 退出后将无法恢复，请确认操作。
            </p>
          </div>
        )}
      </Modal>
    </div>
  )
}

export default ExitList

