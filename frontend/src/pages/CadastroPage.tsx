import { useEffect, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import AjudaPopover from '../components/bitin/AjudaPopover'
import BitinTableSection from '../components/bitin/BitinTableSection'
import { COLUNAS_PADRAO_BITIN, COLUNA_TEMPO_ETAPA } from '../components/bitin/bitinColunas'
import FiltroEtapaToolbar from '../components/bitin/FiltroEtapaToolbar'
import { useAuth } from '../hooks/useAuth'
import { useDebouncedValue } from '../hooks/useDebouncedValue'
import { api } from '../lib/api'
import { isCadastro } from '../lib/permissions'
import type { Bitin } from '../lib/types'

const COLUNAS = [...COLUNAS_PADRAO_BITIN, COLUNA_TEMPO_ETAPA]

// Fila de trabalho do setor Cadastro (2026-07-17, ajustada em 2026-07-20/21) -- substitui de
// vez o e-mail/PDF manual que existia antes (Módulo12.bas na macro original, depois um botão
// "Enviar e-mail" nesta v1, removido a pedido do usuário).
//
// Roteamento automático (2026-07-20) -- o próprio ENVIO já decide sozinho se o BITin precisa
// de roteiro (vai direto pro Processos) ou não (vai direto pra "Aguardando cadastro"), ver
// scripts/bitin_lifecycle.py::enviar_bitin. Cadastro só vê o BITin quando ele NÃO precisa de
// roteiro nenhum ou quando o Processos devolve.
//
// STATUS x ETAPA (2026-07-20, pedido explícito: "não confunde status com etapa... a tela de
// painel geral e a tela de cadastro e processos devem conversar na mesma língua" -- ver
// lib/bitinEtapa.ts, mesma fonte usada por PainelGeral.tsx/ProcessosPage.tsx). Esta página só
// mostra Status=Enviado -- BITins concluídos (Status=Concluído, windchill_enviado=True) saíram
// daqui (2026-07-21, pedido explícito: "aba de bitins concluidos ainda junto de cadastro
// remove de lá e faz isso numa aba lá em configurações só do admin") e agora vivem na aba
// "Bitins Concluídos" de Settings.tsx, com opção de reverter.
type EtapaFiltro = 'todos' | 'aguardando_cadastro' | 'pendencia_envio'

const OPCOES_ETAPA: { value: EtapaFiltro; label: string }[] = [
  { value: 'todos', label: 'Todas' },
  { value: 'aguardando_cadastro', label: 'Aguardando cadastro' },
  { value: 'pendencia_envio', label: 'Pendência de envio' },
]

// GET /bitins?status=enviado&<filtro> -- ver backend/api/bitins.py::list_bitins.
function filtroPorEtapa(etapa: EtapaFiltro): Record<string, boolean> {
  switch (etapa) {
    case 'todos':
      return { windchill_enviado: false }
    case 'aguardando_cadastro':
      return { processos_concluido: true, bitin_cadastrado: false }
    case 'pendencia_envio':
      return { bitin_cadastrado: true, windchill_enviado: false }
  }
}

const ETAPAS_VALIDAS = new Set<EtapaFiltro>(OPCOES_ETAPA.map((o) => o.value))

export default function CadastroPage() {
  const { user } = useAuth()
  // Etapa inicial via query string (2026-07-20) -- deixa os cartões de resumo de "Início
  // cadastro" (Home.tsx) linkarem direto pra visão certa.
  const [searchParams] = useSearchParams()
  const etapaInicial = searchParams.get('etapa')
  const [etapa, setEtapa] = useState<EtapaFiltro>(
    etapaInicial && ETAPAS_VALIDAS.has(etapaInicial as EtapaFiltro) ? (etapaInicial as EtapaFiltro) : 'aguardando_cadastro',
  )
  const [busca, setBusca] = useState('')
  const termo = useDebouncedValue(busca.trim())
  const [bitins, setBitins] = useState<Bitin[] | null>(null)
  const [erro, setErro] = useState<string | null>(null)
  const [finalizandoId, setFinalizandoId] = useState<string | null>(null)
  const [baixandoId, setBaixandoId] = useState<string | null>(null)

  const podeAcessar = isCadastro(user?.permission_level, user?.setor)

  function carregar() {
    let cancelado = false
    setBitins(null)
    setErro(null)
    const params: Record<string, string | boolean> = { status: 'enviado', ...filtroPorEtapa(etapa) }
    if (termo) params.termo = termo
    api
      .get('/bitins', { params })
      .then((resp) => {
        if (!cancelado) setBitins(resp.data)
      })
      .catch(() => {
        if (!cancelado) setErro('Não foi possível carregar os BITins.')
      })
    return () => {
      cancelado = true
    }
  }

  useEffect(() => {
    if (!podeAcessar) return
    return carregar()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [etapa, termo, podeAcessar])

  // "Concluir BITIN" (2026-07-20, pedido explícito) -- o Cadastro confirma que já fez o
  // cadastro/liberação de verdade no SAP. Move de "Aguardando cadastro" pra "Pendência de
  // envio" -- só a partir daqui o PDF fica disponível.
  async function concluirBitin(bitin: Bitin) {
    setErro(null)
    setFinalizandoId(bitin.mongo_id)
    try {
      await api.post(`/bitins/${bitin.mongo_id}/concluir-bitin`)
      setBitins((atual) => atual?.filter((b) => b.mongo_id !== bitin.mongo_id) ?? null)
    } catch {
      setErro('Não foi possível concluir o BITin. Tente novamente.')
    } finally {
      setFinalizandoId(null)
    }
  }

  // "Baixar PDF" (2026-07-20, pedido explícito) -- um botão só: baixa o PDF E marca o BITin
  // como Concluído na mesma ação (windchill_enviado=True, ver bitin_lifecycle.
  // enviar_windchill). Confirmação ANTES de baixar -- pedido explícito: "ter um botão de
  // certeza quando baixar o pdf dizendo que ele vai pra uma pasta de bitins concluidos e não
  // terá como voltar" -- essa é a última ação desta tela: depois disso o Status do BITin vira
  // "Concluído" e ele sai da fila de trabalho pra aba "Bitins Concluídos" em Settings.tsx
  // (só admin, único jeito de reverter é lá).
  async function baixarPdfEConcluir(bitin: Bitin) {
    const confirmado = window.confirm(
      `Baixar o PDF do BITin ${bitin.codigo ?? '—'} e marcar como concluído?\n\n` +
        'Ele sai da fila do Cadastro.',
    )
    if (!confirmado) return
    setErro(null)
    setBaixandoId(bitin.mongo_id)
    try {
      const resp = await api.get(`/bitins/${bitin.mongo_id}/pdf`, { responseType: 'blob' })
      const url = window.URL.createObjectURL(new Blob([resp.data]))
      const a = document.createElement('a')
      a.href = url
      a.download = `BITin-${bitin.codigo ?? bitin.mongo_id}.pdf`
      document.body.appendChild(a)
      a.click()
      a.remove()
      window.URL.revokeObjectURL(url)
      await api.post(`/bitins/${bitin.mongo_id}/enviar-windchill`)
      setBitins((atual) => atual?.filter((b) => b.mongo_id !== bitin.mongo_id) ?? null)
    } catch {
      setErro('Não foi possível baixar o PDF/concluir. Tente novamente.')
    } finally {
      setBaixandoId(null)
    }
  }

  if (!podeAcessar) {
    return (
      <div className="mx-auto max-w-6xl">
        <p className="text-sm text-ink-muted">Você não tem permissão para acessar esta página.</p>
      </div>
    )
  }

  function acoesLinha(b: Bitin) {
    if (etapa === 'aguardando_cadastro' || (etapa === 'todos' && b.processos_concluido && !b.bitin_cadastrado)) {
      return (
        <button
          type="button"
          onClick={() => concluirBitin(b)}
          disabled={finalizandoId === b.mongo_id}
          className="whitespace-nowrap rounded-lg bg-brand-navy px-3 py-1.5 text-xs font-medium text-white hover:bg-brand-navy-dark disabled:cursor-not-allowed disabled:opacity-60"
        >
          {finalizandoId === b.mongo_id ? 'Concluindo...' : 'Concluir BITIN'}
        </button>
      )
    }
    if (etapa === 'pendencia_envio' || (etapa === 'todos' && b.bitin_cadastrado)) {
      return (
        <button
          type="button"
          onClick={() => baixarPdfEConcluir(b)}
          disabled={baixandoId === b.mongo_id}
          className="whitespace-nowrap rounded-lg bg-brand-navy px-3 py-1.5 text-xs font-medium text-white hover:bg-brand-navy-dark disabled:cursor-not-allowed disabled:opacity-60"
        >
          {baixandoId === b.mongo_id ? 'Baixando...' : 'Baixar PDF'}
        </button>
      )
    }
    return null
  }

  return (
    <div className="mx-auto max-w-6xl">
      <div className="flex flex-wrap items-center gap-3">
        <h1 className="text-2xl font-semibold text-ink">Cadastro</h1>
        <AjudaPopover titulo="Hint">
          <p>
            Um BITin chega aqui sozinho, sem triagem manual: ao ser enviado pelo engenheiro, o
            sistema já decide se precisa passar por Processos (roteiro) ou não. Quem não precisa
            já cai direto em "Aguardando cadastro"; quem precisa só chega aqui depois que
            Processos revisa e devolve.
          </p>
          <p>
            <strong>Etapa "Aguardando cadastro"</strong>: o BITin já está liberado pra você
            cadastrar/liberar no SAP de verdade. Depois de feito isso, clique <strong>"Concluir
            BITIN"</strong> -- ele passa pra etapa seguinte.
          </p>
          <p>
            <strong>Etapa "Pendência de envio"</strong>: falta só baixar o PDF final e mandar pro
            Windchill. O botão <strong>"Baixar PDF"</strong> faz as duas coisas juntas (baixa e
            marca como concluído) -- por isso pede confirmação antes: depois disso o BITin sai
            desta fila.
          </p>
          <p>
            <strong>Etapa "Todas"</strong> mostra os dois grupos juntos, cada linha com o botão
            certo pro seu estado. A busca filtra por motivo, solicitante ou número.
          </p>
        </AjudaPopover>
      </div>

      <FiltroEtapaToolbar
        opcoes={OPCOES_ETAPA}
        valor={etapa}
        onChange={setEtapa}
        busca={busca}
        onBuscaChange={setBusca}
      />

      <BitinTableSection bitins={bitins} erro={erro} colunas={COLUNAS} acoes={acoesLinha} />
    </div>
  )
}
