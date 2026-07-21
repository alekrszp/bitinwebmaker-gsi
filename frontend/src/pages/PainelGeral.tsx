import { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import AjudaPopover from '../components/bitin/AjudaPopover'
import StatusBadge from '../components/bitin/StatusBadge'
import { useAuth } from '../hooks/useAuth'
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
// CadastroPage.tsx/ProcessosPage.tsx, pra nunca mais divergir):
//   Status: Rascunho / Enviado / Concluído -- o estado geral do BITin.
//   Etapa: só existe pra Status=Enviado -- aonde ele está parado DENTRO de um setor
//   específico (Recebido/Com Processos/Aguardando cadastro/Pendência de envio).
export default function PainelGeral() {
  const { user } = useAuth()
  const admin = isAdmin(user?.permission_level)
  const [bitins, setBitins] = useState<Bitin[] | null>(null)
  const [erro, setErro] = useState<string | null>(null)
  const [busca, setBusca] = useState('')
  const [setorFiltro, setSetorFiltro] = useState('')
  const [usuarioFiltro, setUsuarioFiltro] = useState('')
  const [statusFiltro, setStatusFiltro] = useState<StatusBitin | ''>('')
  const [etapaFiltro, setEtapaFiltro] = useState<Etapa | ''>('')

  const podeAcessar = isAdmin(user?.permission_level) || isGestor(user?.permission_level)

  useEffect(() => {
    if (!podeAcessar) return
    let cancelado = false
    setBitins(null)
    setErro(null)

    // Sem paginação NA TELA (os filtros abaixo são todos client-side, sobre a lista inteira já
    // carregada) -- mas isso não pode significar truncar em 500 e esconder o resto em
    // silêncio. Busca em lotes (`skip`/`limit`) até a página vir mais curta que o lote, com um
    // teto de segurança (10 lotes = 5000 BITins) só pra nunca travar o navegador se o sistema
    // crescer muito além disso -- nesse caso extremo, valeria migrar os filtros pro backend.
    const TAMANHO_LOTE = 500
    const MAX_LOTES = 10
    async function carregarTudo() {
      const acumulado: Bitin[] = []
      for (let lote = 0; lote < MAX_LOTES; lote++) {
        const resp = await api.get('/bitins', { params: { limit: TAMANHO_LOTE, skip: lote * TAMANHO_LOTE } })
        acumulado.push(...resp.data)
        if (resp.data.length < TAMANHO_LOTE) break
      }
      return acumulado
    }

    carregarTudo()
      .then((todos) => {
        if (!cancelado) setBitins(todos)
      })
      .catch(() => {
        if (!cancelado) setErro('Não foi possível carregar os BITins.')
      })
    return () => {
      cancelado = true
    }
  }, [podeAcessar])

  const comStatusEEtapa = useMemo(
    () => (bitins ?? []).map((b) => ({ bitin: b, status: statusDoBitin(b), etapa: etapaDoBitin(b) })),
    [bitins],
  )

  const usuarios = useMemo(
    () => [...new Set(comStatusEEtapa.map(({ bitin }) => bitin.criado_por).filter((e): e is string => !!e))].sort(),
    [comStatusEEtapa],
  )

  if (!podeAcessar) {
    return (
      <div className="mx-auto max-w-6xl">
        <p className="text-sm text-ink-muted">Você não tem permissão para acessar esta página.</p>
      </div>
    )
  }

  const buscaNormalizada = busca.trim().toLowerCase()
  const filtrados = comStatusEEtapa
    // Setor -- Engenharia = Rascunho (ainda com o próprio engenheiro); Cadastro/Processos =
    // quem está com o BITin agora (RESPONSAVEL_POR_ETAPA, só existe com etapa != null).
    .filter(({ status, etapa }) => {
      if (!setorFiltro) return true
      if (setorFiltro === 'Engenharia') return status === 'Rascunho'
      return etapa !== null && RESPONSAVEL_POR_ETAPA[etapa] === setorFiltro
    })
    .filter(({ bitin }) => !usuarioFiltro || bitin.criado_por === usuarioFiltro)
    .filter(({ status }) => !statusFiltro || status === statusFiltro)
    .filter(({ etapa }) => !etapaFiltro || etapa === etapaFiltro)
    .filter(
      ({ bitin }) =>
        !buscaNormalizada ||
        (bitin.criado_por ?? '').toLowerCase().includes(buscaNormalizada) ||
        (bitin.codigo ?? '').toLowerCase().includes(buscaNormalizada),
    )

  function baixarCsv() {
    const cabecalho = ['Numero', 'Usuario', 'Status', 'Etapa', 'Com quem esta', 'Atualizado em']
    const corpo = filtrados.map(({ bitin: b, status, etapa }) => [
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
    a.download = `painel-geral-${new Date().toISOString().slice(0, 10)}.csv`
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
            de um setor (Recebido/Com Processos/Aguardando cadastro/Pendência de envio). Os dois
            filtros são independentes: combine os dois pra achar, por exemplo, todo BITin
            "Enviado" parado em "Com Processos".
          </p>
          <p>
            Filtros de <strong>Setor</strong> e <strong>Usuário</strong> restringem por quem
            criou o BITin. "Exportar CSV" baixa exatamente a lista filtrada na tela.
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
        <select
          value={usuarioFiltro}
          onChange={(e) => setUsuarioFiltro(e.target.value)}
          className="rounded-lg border border-line bg-surface px-3 py-1.5 text-sm text-ink"
        >
          <option value="">Usuário: todos</option>
          {usuarios.map((email) => (
            <option key={email} value={email}>
              {email}
            </option>
          ))}
        </select>
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
          placeholder="Buscar por usuário ou número do BITin..."
          className="w-64 rounded-lg border border-line bg-surface px-3 py-1.5 text-sm text-ink placeholder:text-ink-faint"
        />
        <button
          type="button"
          onClick={baixarCsv}
          disabled={filtrados.length === 0}
          className="whitespace-nowrap rounded-lg border border-line px-3 py-1.5 text-sm font-medium text-ink hover:bg-surface-alt disabled:cursor-not-allowed disabled:opacity-50"
        >
          Exportar CSV
        </button>
      </div>

      {erro && <p className="mt-4 text-sm text-red-600">{erro}</p>}
      {!bitins && !erro && <p className="mt-4 text-sm text-ink-muted">Carregando...</p>}
      {bitins && filtrados.length === 0 && !erro && (
        <p className="mt-4 text-sm text-ink-muted">Nenhum BITin nesta visão.</p>
      )}
      {bitins && filtrados.length > 0 && (
        <p className="mt-4 text-xs text-ink-faint">
          {filtrados.length} de {bitins.length} BITin{bitins.length === 1 ? '' : 's'} carregado{bitins.length === 1 ? '' : 's'}
        </p>
      )}

      {bitins && filtrados.length > 0 && (
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
              {filtrados.map(({ bitin: b, etapa }) => (
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
    </div>
  )
}
