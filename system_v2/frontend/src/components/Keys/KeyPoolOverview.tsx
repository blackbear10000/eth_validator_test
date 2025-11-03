import React, { useEffect, useState } from 'react'
import { Card, Statistic, Row, Col, Button } from 'antd'
import { keysApi, KeyPoolStatus } from '../../api/keys'

const KeyPoolOverview: React.FC = () => {
  const [status, setStatus] = useState<KeyPoolStatus | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    loadStatus()
  }, [])

  const loadStatus = async () => {
    try {
      setLoading(true)
      const data = await keysApi.getPoolStatus()
      setStatus(data)
    } catch (error) {
      console.error('加载密钥池状态失败:', error)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div>
      <h1>密钥池概览</h1>
      <Row gutter={16}>
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
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="已激活"
              value={status?.by_status?.active || 0}
              loading={loading}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="链上激活"
              value={status?.by_status?.active_on_chain || 0}
              loading={loading}
            />
          </Card>
        </Col>
      </Row>
    </div>
  )
}

export default KeyPoolOverview

