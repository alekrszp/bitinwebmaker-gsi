import { Route, Routes } from 'react-router-dom'
import Layout from './components/Layout'
import RequireAuth from './components/RequireAuth'
import BitinDetail from './pages/BitinDetail'
import Home from './pages/Home'
import Login from './pages/Login'
import MeusBitins from './pages/MeusBitins'
import Settings from './pages/Settings'

function App() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route
        element={
          <RequireAuth>
            <Layout />
          </RequireAuth>
        }
      >
        <Route path="/" element={<Home />} />
        <Route path="/bitins" element={<MeusBitins />} />
        <Route path="/bitins/:mongoId" element={<BitinDetail />} />
        <Route path="/configuracoes" element={<Settings />} />
      </Route>
    </Routes>
  )
}

export default App
