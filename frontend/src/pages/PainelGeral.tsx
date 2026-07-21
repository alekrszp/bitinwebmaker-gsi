import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import AjudaPopover from '../components/bitin/AjudaPopover'
import StatusBadge from '../components/bitin/StatusBadge'
import { useAuth } from '../hooks/useAuth'
import { useDebouncedValue } from '../hooks/useDebouncedValue'
import { api } from '../lib/api'
import { ETAPAS, RESPONSAVEL_POR_ETAPA, etapaDoBitin, statusDoBitin, type Etapa, type StatusBitin } from '../lib/bitinEtapa'
import { isAdmin, isGestor } from '../lib/permissions'
import type { Bitin } from '../lib/types'

// Painel geral (2026-07-20, pedido explícito: "abaixo de gestão de usuários coloca 'painel
// geral' ali vai ser aonde eu vou ver bitins dos engenheiros, quem tá com processo de quem,
// onde tá cada bitin de quem, um painel completo") -- visão de leitura por cima do sistema,
// diferente de "Gestão de usuários" que é só o super-admin (ver Sidebar.tsx). Não é uma fila
// de trabalho (sem ações aqui, sem mover status) -- só onde cada BITin está e com quem.
//
// Ganhou acesso de Gestor em 2026-07-20 (2ª revisão do modelo de permissões, pedido
// explícito: "se for um gestor de cadastro, tem permissão do painel geral do cadastro...
// pode acessar bitin no fluxo de qualquer outro usuário do cadastro" -- mesma ideia pra
// Processos/Engenharia, "Gestoria > Painel geral" no Sidebar.tsx). A página não precisa saber
// SE quem está vendo é admin ou gestor -- reaproveita GET /bitins sem filtro extra porque o
// BACKEND já devolve só o que esse usuário pode ver (admin: tudo; gestor de
// cadastro/processos: fila inteira do setor; gestor de engenharia: colegas do mesmo
// Subgrupo -- ver backend/api/bitins.py::list_bitins).
//
// STATUS x ETAPA (2026-07-20, pedido explícito: "não confunde status com etapa... a tela de
// painel geral e a tela de cadastro e processos devem conversar na mesma língua") -- os dois
// viraram colunas/filtros SEPARADOS, calculados em lib/bitinEtapa.ts (a mesma fonte usada por
// CadastroPage.tsx/ProcessosPage.tsx, pra nunca mais divergir).
//
// Paginação real no servidor (2026-07-21, pedido explícito -- antes buscava até 5000 BITins
// em lotes e filtrava tudo no cliente). Setor/Status/Etapa viram os mesmos parâmetros
// booleanos que CadastroPage.tsx/ProcessosPage.tsx já usam (`encaminhado_roteiro`/
// `processos_concluido`/`bitin_cadastrado`/`windchill_enviado`) -- `paraFiltros` abaixo
// traduz a seleção da UI pra essa combinação, espelhando EXATAMENTE `etapaDoBitin` (nunca
// devem divergir). Usuário virou busca por trecho do e-mail (`criado_por`, substring no
// servidor) em vez de dropdown com todo mundo que já foi visto na tela -- não dava mais pra
// montar esse dropdown sem carregar tudo de novo.
const TAMANHO_PAGINA = 50

function paraFiltros(status: StatusBitin | '', etapa: Etapa | '', setor: string): Record<string, string | boolean> {
  const p: Record<string, string | boolean> = {}

  // Setor força um recorte que pode combinar (ou colidir, se o usuário escolher algo
  // contraditório -- ex. Setor=Engenharia + Status=Enviado -- e a lista simplesmente vem
  // vazia, mesmo comportamento de antes) com Status/Etapa escolhidos à parte.
  if (setor === 'Engenharia') p.status = 'rascunho'
  else if (setor === 'Cadastro') {
    p.status = 'enviado'
    p.processos_concluido = true
    p.windchill_enviado = false
  } else if (setor === 'Processos') {
    p.status = 'enviado'
    p.encaminhado_roteiro = true
    p.processos_concluido = false
  }

  if (status === 'Rascunho') p.status = 'rascunho'
  else if (status === 'Enviado') {
    p.status = 'enviado'
    p.windchill_enviado = false
  } else if (status === 'Concluído') {
    p.status = 'enviado'
    p.windchill_enviado = true
  }

  // Etapa só existe com Status=Enviado -- mesma tradução de etapaDoBitin (lib/bitinEtapa.ts).
  if (etapa === 'Com Processos') {
    p.status = 'enviado'
    p.encaminhado_roteiro = true
    p.processos_concluido = false
  } else if (etapa === 'Aguardando cadastro') {
    p.status = 'enviado'
    p.processos_concluido = true
    p.bitin_cadastrado = false
  } else if (etapa === 'Pendência de envio') {
    p.status = 'enviado'
    p.bitin_cadastrado = true
    p.windchill_enviado = false
  }

  return p
}

export default function PainelGeral() {
  const { user } = useAuth()
  const admin = isAdmin(user?.permission_level)
  const [bitins, setBitins] = useState<Bitin[] | null>(null)
  const [temProximaPagina, setTemProximaPagina] = useState(false)
  const [pagina, setPagina] = useState(1)
  const [erro, setErro] = useState<string | null>(null)
  const [busca, setBusca] = useState('')
  const termo = useDebouncedValue(busca.trim())
  const [usuarioFiltro, setUsuarioFiltro] = useState('')
  const usuarioTermo = useDebouncedValue(usuarioFiltro.trim())
  const [setorFiltro, setSetorFiltro] = useState('')
  const [statusFiltro, setStatusFiltro] = useState<StatusBitin | ''>('')
  const [etapaFiltro, setEtapaFiltro] = useState<Etapa | ''>('')

  const podeAcessar = isAdmin(user?.permission_level) || isGestor(user?.permission_level)

  // Volta pra página 1 sempre que um filtro muda -- senão a página 5 de um filtro anterior
  // podia ficar selecionada num filtro novo que só tem 1 página de resultado.
  useEffect(() => {
    setPagina(1)
  }, [termo, usuarioTermo, setorFiltro, statusFiltro, etapaFiltro])

  useEffect(() => {
    if (!podeAcessar) return
    let cancelado = false
    setBitins(null)
    setErro(null)

    const params: Record<string, string | boolean | number> = {
      ...paraFiltros(statusFiltro, etapaFiltro, setorFiltro),
      limit: TAMANHO_PAGINA,
      skip: (pagina - 1) * TAMANHO_PAGINA,
    }
    if (termo) params.termo = termo
    if (usuarioTermo) params.criado_por = usuarioTermo

    api
      .get('/bitins', { params })
      .then((resp) => {
        if (cancelado) return
        setBitins(resp.data)
        setTemProximaPagina(resp.data.length === TAMANHO_PAGINA)
      })
      .catch(() => {
        if (!cancelado) setErro('Não foi possível carregar os BITins.')
      })
    return () => {
      cancelado = true
    }
  }, [podeAcessar, pagina, termo, usuarioTermo, setorFiltro, statusFiltro, etapaFiltro])

  if (!podeAcessar) {
    return (
      <div className="mx-auto max-w-6xl">
        <p className="text-sm text-ink-muted">Você não tem permissão para acessar esta página.</p>
      </div>
    )
  }

  const linhas = (bitins ?? []).map((b) => ({ bitin: b, status: statusDoBitin(b), etapa: etapaDoBitin(b) }))

  function baixarCsv() {
    const cabecalho = ['Numero', 'Usuario', 'Status', 'Etapa', 'Com quem esta', 'Atualizado em']
    const corpo = linhas.map(({ bitin: b, status, etapa }) => [
      b.codigo ?? '',
      b.criado_por ?? '',
      status,
      etapa ?? '',
      etapa ? RESPONSAVEL_POR_ETAPA[etapa] : '',
      b.updated_at,
    ])
    const csv = [cabecalho, ...corpo]
      .map((linha) => linha.map((campo) => `"${String(campo).replace(/"/g, '""')}"`).join(';'))
      .join('\n')
    const blob = new Blob([`﻿${csv}`], { type: 'text/csv;charset=utf-8;' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `painel-geral-pagina-${pagina}-${new Date().toISOString().slice(0, 10)}.csv`
    document.body.appendChild(a)
    a.click()
    a.remove()
    URL.revokeObjectURL(url)
  }

  return (
    <div className="mx-auto max-w-6xl">
      <div className="flex flex-wrap items-center gap-3">
        <h1 className="text-2xl font-semibold text-ink">Painel geral</h1>
        <AjudaPopover titulo="Como funciona o Painel geral">
          <p>
            É uma visão de leitura -- sem ações, sem mover BITin de lugar. Serve pra achar
            rápido onde qualquer BITin está e com quem, sem precisar entrar em Cadastro,
            Processos e Meus Bitins separadamente.
          </p>
          <p>
            <strong>Status</strong> (Rascunho/Enviado/Concluído) é o estado geral do BITin.
            <strong> Etapa</strong> só existe pra Status=Enviado -- é onde ele está parado DENTRO
            de um setor (Com Processos/Aguardando cadastro/Pendência de envio). Os dois
            filtros são independentes: combine os dois pra achar, por exemplo, todo BITin
            "Enviado" parado em "Com Processos".
          </p>
          <p>
            Filtros de <strong>Setor</strong> e <strong>Usuário</strong> restringem por quem
            criou o BITin -- Usuário aceita um pedaço do e-mail, não precisa ser exato.
            "Exportar CSV" baixa a página atual (50 por vez).
          </p>
        </AjudaPopover>
      </div>
      <p className="mt-1 text-sm text-ink-muted">
        {admin
          ? 'Todos os BITins do sistema, quem está com cada um agora e em que etapa está.'
          : 'BITins do seu setor, quem está com cada um agora e em que etapa está.'}
      </p>

      <div className="mt-6 flex flex-wrap items-center gap-2 border-b border-line pb-3">
        <select
          value={setorFiltro}
          onChange={(e) => setSetorFiltro(e.target.value)}
          className="rounded-lg border border-line bg-surface px-3 py-1.5 text-sm text-ink"
        >
          <option value="">Setor: todos</option>
          <option value="Engenharia">Engenharia</option>
          <option value="Cadastro">Cadastro</option>
          <option value="Processos">Processos</option>
        </select>
        <input
          type="text"
          value={usuarioFiltro}
          onChange={(e) => setUsuarioFiltro(e.target.value)}
          placeholder="Usuário (parte do e-mail)..."
          className="w-48 rounded-lg border border-line bg-surface px-3 py-1.5 text-sm text-ink placeholder:text-ink-faint"
        />
        <select
          value={statusFiltro}
          onChange={(e) => setStatusFiltro(e.target.value as StatusBitin | '')}
          className="rounded-lg border border-line bg-surface px-3 py-1.5 text-sm text-ink"
        >
          <option value="">Status: todos</option>
          <option value="Rascunho">Rascunho</option>
          <option value="Enviado">Enviado</option>
          <option value="Concluído">Concluído</option>
        </select>
        <select
          value={etapaFiltro}
          onChange={(e) => setEtapaFiltro(e.target.value as Etapa | '')}
          className="rounded-lg border border-line bg-surface px-3 py-1.5 text-sm text-ink"
        >
          <option value="">Etapa: todas</option>
          {ETAPAS.map((etapa) => (
            <option key={etapa} value={etapa}>
              {etapa}
            </option>
          ))}
        </select>
        <input
          type="text"
          value={busca}
          onChange={(e) => setBusca(e.target.value)}
          placeholder="Buscar por motivo, solicitante ou número..."
          className="w-64 rounded-lg border border-line bg-surface px-3 py-1.5 text-sm text-ink placeholder:text-ink-faint"
        />
        <button
          type="button"
          onClick={baixarCsv}
          disabled={!bitins || bitins.length === 0}
          className="whitespace-nowrap rounded-lg border border-line px-3 py-1.5 text-sm font-medium text-ink hover:bg-surface-alt disabled:cursor-not-allowed disabled:opacity-50"
        >
          Exportar CSV (página)
        </button>
      </div>

      {erro && <p className="mt-4 text-sm text-red-600">{erro}</p>}
      {!bitins && !erro && <p className="mt-4 text-sm text-ink-muted">Carregando...</p>}
      {bitins && linhas.length === 0 && !erro && (
        <p className="mt-4 text-sm text-ink-muted">Nenhum BITin nesta visão.</p>
      )}

      {bitins && linhas.length > 0 && (
        <div className="mt-4 overflow-hidden rounded-lg border border-line">
          <table className="w-full text-left text-sm">
            <thead>
              <tr className="bg-surface-alt text-xs uppercase tracking-wide text-ink-muted">
                <th className="px-4 py-2 font-medium">Número</th>
                <th className="px-4 py-2 font-medium">Usuário</th>
                <th className="px-4 py-2 font-medium">Status</th>
                <th className="px-4 py-2 font-medium">Etapa</th>
                <th className="px-4 py-2 font-medium">Com quem está</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-line bg-surface">
              {linhas.map(({ bitin: b, etapa }) => (
                <tr key={b.mongo_id} className="hover:bg-surface-alt">
                  <td className="px-4 py-2">
                    <Link to={`/bitins/${b.mongo_id}`} className="block text-ink hover:underline">
                      {b.codigo ?? '—'}
                    </Link>
                  </td>
                  <td className="px-4 py-2 text-ink-muted">{b.criado_por ?? '—'}</td>
                  <td className="px-4 py-2">
                    <StatusBadge status={b.status} windchillEnviado={b.windchill_enviado} />
                  </td>
                  <td className="px-4 py-2 text-ink">{etapa ?? '—'}</td>
                  <td className="px-4 py-2 text-ink-muted">{etapa ? RESPONSAVEL_POR_ETAPA[etapa] : '—'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {bitins && (linhas.length > 0 || pagina > 1) && (
        <div className="mt-3 flex items-center justify-between text-sm text-ink-muted">
          <span>Página {pagina}</span>
          <div className="flex gap-2">
            <button
              type="button"
              onClick={() => setPagina((p) => Math.max(1, p - 1))}
              disabled={pagina === 1}
              className="rounded-lg border border-line px-3 py-1.5 font-medium text-ink hover:bg-surface-alt disabled:cursor-not-allowed disabled:opacity-50"
            >
              Anterior
            </button>
            <button
              type="button"
              onClick={() => setPagina((p) => p + 1)}
              disabled={!temProximaPagina}
              className="rounded-lg border border-line px-3 py-1.5 font-medium text-ink hover:bg-surface-alt disabled:cursor-not-allowed disabled:opacity-50"
            >
              Próxima
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
