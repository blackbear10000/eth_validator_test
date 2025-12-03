import React, { useEffect, useState } from 'react'
import {
  Card,
  Statistic,
  Row,
  Col,
  Button,
  Form,
  InputNumber,
  Input,
  Modal,
  message,
  Space,
} from 'antd'
import {
  PlusOutlined,
  CheckCircleOutlined,
  ReloadOutlined,
} from '@ant-design/icons'
import { keysApi, KeyPoolStatus } from '../../api/keys'

const KeyPoolOverview: React.FC = () => {
  const [status, setStatus] = useState<KeyPoolStatus | null>(null)
  const [loading, setLoading] = useState(true)
  const [generateModalVisible, setGenerateModalVisible] = useState(false)
  const [activateModalVisible, setActivateModalVisible] = useState(false)
  const [generateLoading, setGenerateLoading] = useState(false)
  const [activateLoading, setActivateLoading] = useState(false)
  const [generateForm] = Form.useForm()
  const [activateForm] = Form.useForm()

  useEffect(() => {
    loadStatus()
  }, [])

  const loadStatus = async () => {
    try {
      setLoading(true)
      const response = await keysApi.getPoolStatus() as any
      setStatus(response as unknown as KeyPoolStatus)
    } catch (error: any) {
      message.error(`加载密钥池状态失败: ${error.message}`)
    } finally {
      setLoading(false)
    }
  }

  // 批量生成密钥
  const handleGenerate = async (values: { count: number; batch_id?: string }) => {
    setGenerateLoading(true)
    try {
      await keysApi.batchGenerate(values.count, values.batch_id)
      message.success(`成功生成 ${values.count} 个密钥`)
      setGenerateModalVisible(false)
      generateForm.resetFields()
      loadStatus()
    } catch (error: any) {
      message.error(`生成密钥失败: ${error.message}`)
    } finally {
      setGenerateLoading(false)
    }
  }

  // 批量激活密钥
  const handleActivate = async (values: { count: number; batch_id?: string }) => {
    setActivateLoading(true)
    try {
      await keysApi.activate(values.count, values.batch_id)
      message.success(`成功激活 ${values.count} 个密钥`)
      setActivateModalVisible(false)
      activateForm.resetFields()
      loadStatus()
    } catch (error: any) {
      message.error(`激活密钥失败: ${error.message}`)
    } finally {
      setActivateLoading(false)
    }
  }

  return (
    <div>
      <h1>密钥池概览</h1>
      
      {/* 统计卡片 */}
      <Row gutter={16} style={{ marginBottom: 24 }}>
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
              valueStyle={{ color: '#999' }}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="已激活"
              value={status?.by_status?.active || 0}
              loading={loading}
              valueStyle={{ color: '#1890ff' }}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="链上激活"
              value={status?.by_status?.active_on_chain || 0}
              loading={loading}
              valueStyle={{ color: '#52c41a' }}
            />
          </Card>
        </Col>
      </Row>

      {/* 操作按钮 */}
      <Card>
        <Space>
          <Button
            type="primary"
            icon={<PlusOutlined />}
            onClick={() => setGenerateModalVisible(true)}
          >
            批量生成密钥
          </Button>
          <Button
            type="default"
            icon={<CheckCircleOutlined />}
            onClick={() => setActivateModalVisible(true)}
            disabled={!status || (status.by_status?.unused || 0) === 0}
          >
            批量激活密钥
          </Button>
          <Button
            icon={<ReloadOutlined />}
            onClick={loadStatus}
          >
            刷新状态
          </Button>
        </Space>
      </Card>

      {/* 批量生成密钥模态框 */}
      <Modal
        title="批量生成密钥"
        open={generateModalVisible}
        onCancel={() => {
          setGenerateModalVisible(false)
          generateForm.resetFields()
        }}
        onOk={() => generateForm.submit()}
        confirmLoading={generateLoading}
      >
        <Form
          form={generateForm}
          layout="vertical"
          onFinish={handleGenerate}
        >
          <Form.Item
            name="count"
            label="生成数量"
            rules={[
              { required: true, message: '请输入生成数量' },
              { type: 'number', min: 1, max: 10000, message: '数量必须在 1-10000 之间' },
            ]}
          >
            <InputNumber
              style={{ width: '100%' }}
              placeholder="请输入要生成的密钥数量"
              min={1}
              max={10000}
            />
          </Form.Item>
          <Form.Item
            name="batch_id"
            label="批次ID（可选）"
          >
            <Input placeholder="请输入批次ID，用于标识这批密钥" />
          </Form.Item>
        </Form>
      </Modal>

      {/* 批量激活密钥模态框 */}
      <Modal
        title="批量激活密钥"
        open={activateModalVisible}
        onCancel={() => {
          setActivateModalVisible(false)
          activateForm.resetFields()
        }}
        onOk={() => activateForm.submit()}
        confirmLoading={activateLoading}
      >
        <Form
          form={activateForm}
          layout="vertical"
          onFinish={handleActivate}
        >
          <Form.Item
            name="count"
            label="激活数量"
            rules={[
              { required: true, message: '请输入激活数量' },
              { type: 'number', min: 1, message: '数量必须大于 0' },
            ]}
          >
            <InputNumber
              style={{ width: '100%' }}
              placeholder={`最多可激活 ${status?.by_status?.unused || 0} 个密钥`}
              min={1}
              max={status?.by_status?.unused || 10000}
            />
          </Form.Item>
          <Form.Item
            name="batch_id"
            label="批次ID（可选）"
            help="如果指定批次ID，只激活该批次的密钥"
          >
            <Input placeholder="请输入批次ID" />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  )
}

export default KeyPoolOverview
