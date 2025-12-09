import React, { useState, useEffect } from 'react'
import {
  Card,
  Form,
  Input,
  Button,
  message,
  Tabs,
  Typography,
  Space,
  Divider,
} from 'antd'
import {
  WalletOutlined,
  UserOutlined,
  LockOutlined,
} from '@ant-design/icons'
import { useAuthStore } from '../../stores/authStore'
import { useMetaMaskStore } from '../../stores/metamaskStore'
import { useNavigate } from 'react-router-dom'

const { Title, Text } = Typography

const LoginPage: React.FC = () => {
  const [loginType, setLoginType] = useState<'wallet' | 'admin'>('wallet')
  const [loading, setLoading] = useState(false)
  const [form] = Form.useForm()
  
  const { loginWithWallet, loginWithPassword, checkAuth, isAuthenticated } = useAuthStore()
  const { connect, isConnected, account } = useMetaMaskStore()
  const navigate = useNavigate()

  useEffect(() => {
    // 检查是否已登录
    checkAuth().then(() => {
      if (isAuthenticated) {
        navigate('/')
      }
    })
  }, [isAuthenticated, navigate])

  const handleWalletLogin = async () => {
    if (!isConnected) {
      try {
        await connect()
      } catch (error: any) {
        message.error(`连接 MetaMask 失败: ${error.message}`)
        return
      }
    }

    if (!account) {
      message.error('请先连接 MetaMask 钱包')
      return
    }

    setLoading(true)
    try {
      await loginWithWallet()
      message.success('登录成功')
      navigate('/')
    } catch (error: any) {
      message.error(`登录失败: ${error.message}`)
    } finally {
      setLoading(false)
    }
  }

  const handleAdminLogin = async (values: { username: string; password: string }) => {
    setLoading(true)
    try {
      await loginWithPassword(values.username, values.password)
      message.success('登录成功')
      navigate('/')
    } catch (error: any) {
      message.error(`登录失败: ${error.message}`)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div style={{
      display: 'flex',
      justifyContent: 'center',
      alignItems: 'center',
      minHeight: '100vh',
      background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
      padding: '20px'
    }}>
      <Card
        style={{
          width: '100%',
          maxWidth: 450,
          boxShadow: '0 8px 24px rgba(0,0,0,0.12)'
        }}
      >
        <Space direction="vertical" size="large" style={{ width: '100%' }}>
          <div style={{ textAlign: 'center' }}>
            <Title level={2}>ETH Validator</Title>
            <Text type="secondary">管理系统</Text>
          </div>

          <Tabs
            activeKey={loginType}
            onChange={(key) => setLoginType(key as 'wallet' | 'admin')}
            items={[
              {
                key: 'wallet',
                label: (
                  <span>
                    <WalletOutlined /> 钱包登录
                  </span>
                ),
                children: (
                  <Space direction="vertical" size="large" style={{ width: '100%' }}>
                    <Text type="secondary">
                      使用 MetaMask 钱包登录（普通用户）
                    </Text>
                    {!isConnected ? (
                      <Button
                        type="primary"
                        icon={<WalletOutlined />}
                        onClick={handleWalletLogin}
                        loading={loading}
                        block
                        size="large"
                      >
                        连接 MetaMask 并登录
                      </Button>
                    ) : (
                      <Space direction="vertical" style={{ width: '100%' }}>
                        <Text>
                          已连接钱包: <Text code>{account?.substring(0, 10)}...{account?.substring(account.length - 8)}</Text>
                        </Text>
                        <Button
                          type="primary"
                          onClick={handleWalletLogin}
                          loading={loading}
                          block
                          size="large"
                        >
                          签名并登录
                        </Button>
                      </Space>
                    )}
                  </Space>
                )
              },
              {
                key: 'admin',
                label: (
                  <span>
                    <UserOutlined /> 管理员登录
                  </span>
                ),
                children: (
                  <Form
                    form={form}
                    onFinish={handleAdminLogin}
                    layout="vertical"
                    size="large"
                  >
                    <Form.Item
                      name="username"
                      rules={[{ required: true, message: '请输入用户名' }]}
                    >
                      <Input
                        prefix={<UserOutlined />}
                        placeholder="用户名"
                      />
                    </Form.Item>
                    <Form.Item
                      name="password"
                      rules={[{ required: true, message: '请输入密码' }]}
                    >
                      <Input.Password
                        prefix={<LockOutlined />}
                        placeholder="密码"
                      />
                    </Form.Item>
                    <Form.Item>
                      <Button
                        type="primary"
                        htmlType="submit"
                        loading={loading}
                        block
                      >
                        登录
                      </Button>
                    </Form.Item>
                  </Form>
                )
              }
            ]}
          />
        </Space>
      </Card>
    </div>
  )
}

export default LoginPage

