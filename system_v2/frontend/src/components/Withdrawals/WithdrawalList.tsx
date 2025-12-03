import React, { useState, useEffect } from 'react'
import {
  Table,
  Card,
  Button,
  Input,
  Space,
  message,
  Statistic,
  Row,
  Col,
  Tag,
  Typography,
  Select,
} from 'antd'
import { ReloadOutlined } from '@ant-design/icons'
import { withdrawalsApi, WithdrawalEvent, WithdrawalStatistics } from '../../api/withdrawals'
import { keysApi } from '../../api/keys'

const { Text } = Typography
const { Option } = Select

const WithdrawalList: React.FC = () => {
  const [withdrawals, setWithdrawals] = useState<WithdrawalEvent[]>([])
  const [statistics, setStatistics] = useState<WithdrawalStatistics | null>(null)
  const [loading, setLoading] = useState(false)
  const [selectedPubkey, setSelectedPubkey] = useState<string>('')
  const [keys, setKeys] = useState<Array<{ pubkey: string; status: string }>>([])

  // 加载验证者列表
  const loadKeys = async () => {
    try {
      const response = await keysApi.list({ limit: 1000 })
      setKeys(response.items || [])
      if (response.items?.length > 0 && !selectedPubkey) {
        setSelectedPubkey(response.items[0].pubkey)
      }
    } catch (error: any) {
      message.error(`加载验证者列表失败: ${error.message}`)
    }
  }

  // 加载取款历史
  const loadWithdrawals = async () => {
    if (!selectedPubkey) return

    setLoading(true)
    try {
      const [withdrawalsRes, statsRes] = await Promise.all([
        withdrawalsApi.getValidatorWithdrawals(selectedPubkey, 100, 0),
        withdrawalsApi.getStatistics(selectedPubkey),
      ])
      setWithdrawals(withdrawalsRes.items || [])
      setStatistics(statsRes)
    } catch (error: any) {
      message.error(`加载取款历史失败: ${error.message}`)
    } finally {
      setLoading(false)
    }
  }

  // 同步取款事件
  const handleSync = async () => {
    try {
      await withdrawalsApi.sync(selectedPubkey)
      message.success('同步任务已启动')
      setTimeout(() => {
        loadWithdrawals()
      }, 2000)
    } catch (error: any) {
      message.error(`同步失败: ${error.message}`)
    }
  }

  useEffect(() => {
    loadKeys()
  }, [])

  useEffect(() => {
    if (selectedPubkey) {
      loadWithdrawals()
    }
  }, [selectedPubkey])

  const columns = [
    {
      title: 'ID',
      dataIndex: 'id',
      key: 'id',
      width: 80,
    },
    {
      title: '类型',
      dataIndex: 'withdrawal_type',
      key: 'withdrawal_type',
      width: 100,
      render: (type: string) => {
        const typeMap: Record<string, { color: string; text: string }> = {
          partial: { color: 'blue', text: '部分取款' },
          full: { color: 'green', text: '全额取款' },
        }
        const config = typeMap[type] || { color: 'default', text: type }
        return <Tag color={config.color}>{config.text}</Tag>
      },
    },
    {
      title: '取款金额',
      dataIndex: 'amount_eth',
      key: 'amount_eth',
      width: 120,
      render: (amount: number) => `${amount.toFixed(6)} ETH`,
    },
    {
      title: '费用',
      dataIndex: 'fee_eth',
      key: 'fee_eth',
      width: 120,
      render: (fee: number) => (
        <Text type="secondary">-{fee.toFixed(6)} ETH</Text>
      ),
    },
    {
      title: '净额',
      dataIndex: 'net_amount_eth',
      key: 'net_amount_eth',
      width: 120,
      render: (net: number) => (
        <Text strong style={{ color: '#52c41a' }}>
          {net.toFixed(6)} ETH
        </Text>
      ),
    },
    {
      title: 'Epoch',
      dataIndex: 'epoch',
      key: 'epoch',
      width: 100,
    },
    {
      title: 'Slot',
      dataIndex: 'slot',
      key: 'slot',
      width: 100,
    },
    {
      title: '时间',
      dataIndex: 'withdrawn_at',
      key: 'withdrawn_at',
      width: 180,
      render: (time: string) => new Date(time).toLocaleString(),
    },
  ]

  return (
    <div>
      <Card
        title="验证者取款管理"
        extra={
          <Space>
            <Select
              value={selectedPubkey}
              onChange={setSelectedPubkey}
              style={{ width: 400 }}
              placeholder="选择验证者"
              showSearch
              filterOption={(input, option) => {
                const children = option?.children
                if (typeof children === 'string') {
                  return children.toLowerCase().includes(input.toLowerCase())
                }
                return false
              }}
            >
              {keys.map((key) => (
                <Option key={key.pubkey} value={key.pubkey}>
                  {key.pubkey.substring(0, 20)}... ({key.status})
                </Option>
              ))}
            </Select>
            <Button icon={<ReloadOutlined />} onClick={handleSync}>
              同步取款事件
            </Button>
            <Button onClick={loadWithdrawals}>刷新</Button>
          </Space>
        }
      >
        {statistics && (
          <Row gutter={16} style={{ marginBottom: 24 }}>
            <Col span={6}>
              <Statistic
                title="总取款次数"
                value={statistics.total_count}
                suffix="次"
              />
            </Col>
            <Col span={6}>
              <Statistic
                title="总取款金额"
                value={statistics.total_amount_eth}
                precision={6}
                suffix="ETH"
              />
            </Col>
            <Col span={6}>
              <Statistic
                title="总费用"
                value={statistics.total_fee_eth}
                precision={6}
                suffix="ETH"
              />
            </Col>
            <Col span={6}>
              <Statistic
                title="净收益"
                value={statistics.total_amount_eth - statistics.total_fee_eth}
                precision={6}
                suffix="ETH"
                valueStyle={{ color: '#52c41a' }}
              />
            </Col>
          </Row>
        )}

        <Table
          columns={columns}
          dataSource={withdrawals}
          rowKey="id"
          loading={loading}
          pagination={{
            pageSize: 20,
            showSizeChanger: true,
            showTotal: (total) => `共 ${total} 条记录`,
          }}
        />
      </Card>
    </div>
  )
}

export default WithdrawalList

