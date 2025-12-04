import { BrowserRouter, Routes, Route } from 'react-router-dom'
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

const { Content } = Layout

function App() {
  return (
    <BrowserRouter>
      <MainLayout>
        <Content style={{ padding: '24px', minHeight: '100vh' }}>
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/keys" element={<KeyPoolOverview />} />
            <Route path="/keys/list" element={<KeyList />} />
            <Route path="/deposits" element={<DepositList />} />
            <Route path="/contracts" element={<BatchContractManager />} />
            <Route path="/clients" element={<ClientList />} />
            <Route path="/network" element={<NetworkManager />} />
            <Route path="/web3signer" element={<Web3SignerMonitor />} />
            <Route path="/exits" element={<ExitList />} />
            <Route path="/withdrawals" element={<WithdrawalList />} />
          </Routes>
        </Content>
      </MainLayout>
    </BrowserRouter>
  )
}

export default App

