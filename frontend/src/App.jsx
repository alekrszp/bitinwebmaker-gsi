import { Navigate, Route, Routes } from 'react-router-dom'
import Layout from './components/Layout'
import RequireAuth from './components/RequireAuth'
import BitinDetail from './pages/BitinDetail'
import Login from './pages/Login'
import MeusBitins from './pages/MeusBitins'

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
        <Route path="/bitins" element={<MeusBitins />} />
        <Route path="/bitins/novo" element={<BitinDetail />} />
        <Route path="/bitins/:id" element={<BitinDetail />} />
        <Route path="/" element={<Navigate to="/bitins" replace />} />
      </Route>
    </Routes>
  )
}

export default App
