import React, { useEffect, useState } from 'react'
import { Card, Row, Col, Statistic } from 'antd'
import { monitoringApi, SystemOverview } from '../../api/monitoring'

const Dashboard: React.FC = () => {
  const [overview, setOverview] = useState<SystemOverview | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    loadOverview()
    const interval = setInterval(loadOverview, 30000) // 每30秒刷新
    return () => clearInterval(interval)
  }, [])

  const loadOverview = async () => {
    try {
      const response = await monitoringApi.overview() as any
      setOverview(response as unknown as SystemOverview)
    } catch (error) {
      console.error('加载系统概览失败:', error)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div>
      <h1>系统仪表板</h1>
      <Row gutter={16} style={{ marginBottom: 16 }}>
        <Col span={6}>
          <Card>
            <Statistic
              title="总密钥数"
              value={overview?.total_keys || 0}
              loading={loading}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="活跃验证者"
              value={overview?.active_validators || 0}
              loading={loading}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="总存款数"
              value={overview?.total_deposits || 0}
              loading={loading}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="总收益 (ETH)"
              value={overview?.total_rewards_eth || 0}
              precision={4}
              loading={loading}
            />
          </Card>
        </Col>
      </Row>
    </div>
  )
}

export default Dashboard

