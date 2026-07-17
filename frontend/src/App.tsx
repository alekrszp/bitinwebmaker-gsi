import { Route, Routes } from 'react-router-dom'
import Layout from './components/Layout'
import RequireAuth from './components/RequireAuth'
import BitinDetail from './pages/BitinDetail'
import CodigosSapPage from './pages/CodigosSapPage'
import DefinirSenha from './pages/DefinirSenha'
import GestaoUsuariosPage from './pages/GestaoUsuariosPage'
import Home from './pages/Home'
import ListaTecnicaPage from './pages/ListaTecnicaPage'
import Login from './pages/Login'
import MeusBitins from './pages/MeusBitins'
import Settings from './pages/Settings'

function App() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      {/* Fora do Layout (sem sidebar/topbar) de propósito -- mesmo espírito standalone de
          /login -- mas AINDA dentro de RequireAuth: precisa estar logado pra chegar aqui,
          RequireAuth.tsx só isenta ESTA rota específica do redirecionamento por senha
          temporária (senão seria loop: /definir-senha redirecionando pra /definir-senha). */}
      <Route
        path="/definir-senha"
        element={
          <RequireAuth>
            <DefinirSenha />
          </RequireAuth>
        }
      />
      <Route
        element={
          <RequireAuth>
            <Layout />
          </RequireAuth>
        }
      >
        <Route path="/" element={<Home />} />
        <Route path="/bitins" element={<MeusBitins />} />
        {/* /bitins/novo removida (2026-07-16) -- "+ Novo BITin" agora cria o rascunho direto
            via POST /bitins/draft e navega pro /bitins/:mongoId real, sem tela intermediária
            em branco (ver lib/criarBitin.ts). */}
        <Route path="/bitins/:mongoId/codigos-sap" element={<CodigosSapPage />} />
        <Route path="/bitins/:mongoId/lista-tecnica" element={<ListaTecnicaPage />} />
        <Route path="/bitins/:mongoId" element={<BitinDetail />} />
        <Route path="/configuracoes" element={<Settings />} />
        <Route path="/usuarios" element={<GestaoUsuariosPage />} />
      </Route>
    </Routes>
  )
}

export default App
