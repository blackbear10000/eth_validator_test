import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { Layout } from 'antd'
import MainLayout from './components/Layout/MainLayout'
import KeyPoolOverview from './components/Keys/KeyPoolOverview'
import KeyList from './components/Keys/KeyList'
import DepositList from './components/Deposits/DepositList'
import ClientList from './components/Clients/ClientList'
import Dashboard from './components/Monitoring/Dashboard'
import ExitList from './components/Exits/ExitList'
import WithdrawalList from './components/Withdrawals/WithdrawalList'
import NetworkManager from './components/Network/NetworkManager'
import BatchContractManager from './components/Contracts/BatchContractManager'
import Web3SignerMonitor from './components/Web3Signer/Web3SignerMonitor'
import LoginPage from './components/Auth/LoginPage'
import ProtectedRoute from './components/Auth/ProtectedRoute'
import AdminPanel from './components/Admin/AdminPanel'
import { useAuthStore } from './stores/authStore'

const { Content } = Layout

function App() {
  const { user } = useAuthStore()
  const isAdmin = user?.role === 'admin'

  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route
          path="/*"
          element={
            <ProtectedRoute>
              <MainLayout>
                <Content style={{ padding: '24px', minHeight: '100vh' }}>
                  <Routes>
                    {/* 所有用户都可以访问 */}
                    <Route path="/" element={<Dashboard />} />
                    <Route path="/deposits" element={<DepositList />} />
                    <Route path="/exits" element={<ExitList />} />
                    <Route path="/withdrawals" element={<WithdrawalList />} />
                    
                    {/* 仅管理员可以访问 */}
                    {isAdmin && (
                      <>
                        <Route path="/keys" element={<KeyPoolOverview />} />
                        <Route path="/keys/list" element={<KeyList />} />
                        <Route path="/contracts" element={<BatchContractManager />} />
                        <Route path="/clients" element={<ClientList />} />
                        <Route path="/network" element={<NetworkManager />} />
                        <Route path="/web3signer" element={<Web3SignerMonitor />} />
                        <Route path="/admin" element={<AdminPanel />} />
                      </>
                    )}
                    
                    <Route path="*" element={<Navigate to="/" replace />} />
                  </Routes>
                </Content>
              </MainLayout>
            </ProtectedRoute>
          }
        />
      </Routes>
    </BrowserRouter>
  )
}

export default App

