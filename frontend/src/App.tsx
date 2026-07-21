import { lazy, Suspense } from 'react'
import { Route, Routes } from 'react-router-dom'
import Layout from './components/Layout'
import RequireAuth from './components/RequireAuth'
import Login from './pages/Login'

// Code-splitting por rota (2026-07-17, otimização de performance -- pedido explícito: "usa
// como base o frontend antigo que tinha uma otimização feita"). Antes todas as páginas
// (BitinDetail, CodigosSapPage, ListaTecnicaPage -- as telas mais pesadas do app) entravam
// no MESMO bundle inicial, carregado antes até da tela de login aparecer. `lazy` faz cada
// rota virar um chunk próprio, baixado só quando o engenheiro navega até ela -- carrega mais
// rápido, principalmente em conexão ruim/celular (uso de campo, não só escritório). `Login`
// fica FORA do lazy de propósito -- é a primeira tela pra quem não está logado, lazy-load
// dela só atrasaria o primeiro paint sem ganho nenhum (o chunk teria que baixar de qualquer
// jeito antes de mostrar algo).
const Home = lazy(() => import('./pages/Home'))
const MeusBitins = lazy(() => import('./pages/MeusBitins'))
const BitinDetail = lazy(() => import('./pages/BitinDetail'))
const CodigosSapPage = lazy(() => import('./pages/CodigosSapPage'))
const ListaTecnicaPage = lazy(() => import('./pages/ListaTecnicaPage'))
const Settings = lazy(() => import('./pages/Settings'))
const GestaoUsuariosPage = lazy(() => import('./pages/GestaoUsuariosPage'))
const CadastroPage = lazy(() => import('./pages/CadastroPage'))
const ProcessosPage = lazy(() => import('./pages/ProcessosPage'))
const DefinirSenha = lazy(() => import('./pages/DefinirSenha'))
const PainelGeral = lazy(() => import('./pages/PainelGeral'))

function CarregandoRota() {
  return <p className="p-6 text-sm text-ink-muted">Carregando...</p>
}

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
            <Suspense fallback={<CarregandoRota />}>
              <DefinirSenha />
            </Suspense>
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
        <Route
          path="/"
          element={
            <Suspense fallback={<CarregandoRota />}>
              <Home />
            </Suspense>
          }
        />
        <Route
          path="/bitins"
          element={
            <Suspense fallback={<CarregandoRota />}>
              <MeusBitins />
            </Suspense>
          }
        />
        {/* /bitins/novo removida (2026-07-16) -- "+ Novo BITin" agora cria o rascunho direto
            via POST /bitins/draft e navega pro /bitins/:mongoId real, sem tela intermediária
            em branco (ver lib/criarBitin.ts). */}
        <Route
          path="/bitins/:mongoId/codigos-sap"
          element={
            <Suspense fallback={<CarregandoRota />}>
              <CodigosSapPage />
            </Suspense>
          }
        />
        <Route
          path="/bitins/:mongoId/lista-tecnica"
          element={
            <Suspense fallback={<CarregandoRota />}>
              <ListaTecnicaPage />
            </Suspense>
          }
        />
        <Route
          path="/bitins/:mongoId"
          element={
            <Suspense fallback={<CarregandoRota />}>
              <BitinDetail />
            </Suspense>
          }
        />
        <Route
          path="/configuracoes"
          element={
            <Suspense fallback={<CarregandoRota />}>
              <Settings />
            </Suspense>
          }
        />
        <Route
          path="/usuarios"
          element={
            <Suspense fallback={<CarregandoRota />}>
              <GestaoUsuariosPage />
            </Suspense>
          }
        />
        <Route
          path="/cadastro"
          element={
            <Suspense fallback={<CarregandoRota />}>
              <CadastroPage />
            </Suspense>
          }
        />
        {/* Processos (2026-07-20) -- rota própria, antes reaproveitava /bitins
            (MeusBitins.tsx). ProcessosPage.tsx faz sua própria checagem de isProcessos. */}
        <Route
          path="/processos"
          element={
            <Suspense fallback={<CarregandoRota />}>
              <ProcessosPage />
            </Suspense>
          }
        />
        {/* Painel geral (2026-07-20) -- visão de leitura pra qualquer admin (99), separada de
            /usuarios (agora só o super-admin, ver Sidebar.tsx). PainelGeral.tsx faz sua
            própria checagem de isAdmin, mesmo padrão de CadastroPage.tsx. */}
        <Route
          path="/painel-geral"
          element={
            <Suspense fallback={<CarregandoRota />}>
              <PainelGeral />
            </Suspense>
          }
        />
      </Route>
    </Routes>
  )
}

export default App
