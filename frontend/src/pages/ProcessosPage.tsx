import { useEffect, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import AjudaPopover from '../components/bitin/AjudaPopover'
import BitinTableSection from '../components/bitin/BitinTableSection'
import { COLUNAS_PADRAO_BITIN, type BitinColuna } from '../components/bitin/bitinColunas'
import FiltroEtapaToolbar from '../components/bitin/FiltroEtapaToolbar'
import { useAuth } from '../hooks/useAuth'
import { useDebouncedValue } from '../hooks/useDebouncedValue'
import { api } from '../lib/api'
import { isProcessos } from '../lib/permissions'
import type { Bitin } from '../lib/types'

// Fila de trabalho do setor Processos (2026-07-20) -- antes reaproveitava MeusBitins.tsx
// (tela genérica de "meus BITins"), reformulada como tela própria: mesmo padrão de
// CadastroPage.tsx/PainelGeral.tsx (filtro + busca, sem abas). Ações de edição/conclusão
// continuam em BitinDetail.tsx (/atualizar-processos, /concluir-processos, botão "Concluir")
// -- esta tela é só a listagem/filtro, igual CadastroPage.tsx é só listagem até clicar num
// BITin.
//
// STATUS x ETAPA (2026-07-20, pedido explícito: "não confunde status com etapa... a tela de
// painel geral e a tela de cadastro e processos devem conversar na mesma língua") -- todo
// BITin que o Processos vê tem Status "Enviado" (nunca "Concluído" -- esse é um estado do
// BITin inteiro, só o Cadastro fecha ele de vez via Windchill, ver
// bitin_lifecycle.enviar_windchill). O que muda aqui é só a ETAPA -- "Pendente" (ainda com o
// Processos) ou "Revisado" (Processos já concluiu a revisão, devolveu pro Cadastro). Chamar
// isso de "Concluído" como antes confundia com o Status final do BITin -- daí o nome
// "Revisado", exclusivo dessa etapa.
//
// `EtapaFiltro` (2026-07-21, renomeado de `Etapa`) -- o nome antigo colidia (mesmo
// identificador, valores completamente diferentes) com o `Etapa` de domínio exportado por
// lib/bitinEtapa.ts (usado por PainelGeral.tsx). Este aqui é só o filtro DESTA tela.
//
// Sem tela separada de "Concluídos" (2026-07-20, pedido explícito: "não precisa de uma tela
// de processos concluídos") -- Processos não tem uma pasta trancada como o Cadastro tem
// (Bitins Concluídos); "Revisado" é só mais uma etapa dentro da mesma tela, sem restrição de
// admin.
//
// BITins sem necessidade de roteiro ficam de fora (2026-07-21, achado ao investigar "porque
// tem bitins de troca de fornecedor (-/F) aparecendo como revisado nos processos" -- resposta:
// concluir_sem_roteiro também seta processos_concluido=True como atalho pro mesmo estado
// final, sem o BITin nunca ter passado pelo Processos de verdade -- ver
// bitin_lifecycle.py::concluir_sem_roteiro/sem_necessidade_roteiro). Excluído nas duas etapas
// -- Processos nunca teve contato real com esses BITins, não deviam aparecer nem como
// "Pendente" nem como "Revisado".
type EtapaFiltro = 'todos' | 'pendente' | 'revisado'

const OPCOES_ETAPA: { value: EtapaFiltro; label: string }[] = [
  { value: 'todos', label: 'Todas' },
  { value: 'pendente', label: 'Pendente' },
  { value: 'revisado', label: 'Revisado' },
]

function filtroPorEtapa(etapa: EtapaFiltro): Record<string, boolean> {
  switch (etapa) {
    case 'todos':
      return { sem_necessidade_roteiro: false }
    case 'pendente':
      return { encaminhado_roteiro: true, processos_concluido: false, sem_necessidade_roteiro: false }
    case 'revisado':
      return { processos_concluido: true, sem_necessidade_roteiro: false }
  }
}

const ETAPAS_VALIDAS = new Set<EtapaFiltro>(OPCOES_ETAPA.map((o) => o.value))

// Colunas: mesmas 4 padrão + pill de etapa "Pendente"/"Revisado" no lugar do StatusBadge de
// Status (esta tela já sabe que Status é sempre "Enviado" -- a coluna Etapa é a informação
// nova, não redundante).
const COLUNAS: BitinColuna[] = [
  ...COLUNAS_PADRAO_BITIN,
  {
    header: 'Etapa',
    render: (b) => (
      <span
        className={`whitespace-nowrap rounded-full px-2 py-0.5 text-xs font-medium ${
          b.processos_concluido ? 'bg-green-100 text-green-700' : 'bg-amber-100 text-amber-800'
        }`}
      >
        {b.processos_concluido ? 'Revisado' : 'Pendente'}
      </span>
    ),
  },
]

export default function ProcessosPage() {
  const { user } = useAuth()
  // Etapa inicial via query string (2026-07-20, mesmo padrão de CadastroPage.tsx) -- deixa
  // os cartões de resumo de "Início processos" (Home.tsx) linkarem direto pra visão certa.
  const [searchParams] = useSearchParams()
  const etapaInicial = searchParams.get('etapa')
  const [etapa, setEtapa] = useState<EtapaFiltro>(
    etapaInicial && ETAPAS_VALIDAS.has(etapaInicial as EtapaFiltro) ? (etapaInicial as EtapaFiltro) : 'pendente',
  )
  const [busca, setBusca] = useState('')
  const termo = useDebouncedValue(busca.trim())
  const [bitins, setBitins] = useState<Bitin[] | null>(null)
  const [erro, setErro] = useState<string | null>(null)

  const podeAcessar = isProcessos(user?.permission_level, user?.setor)

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

  if (!podeAcessar) {
    return (
      <div className="mx-auto max-w-6xl">
        <p className="text-sm text-ink-muted">Você não tem permissão para acessar esta página.</p>
      </div>
    )
  }

  return (
    <div className="mx-auto max-w-6xl">
      <div className="flex flex-wrap items-center gap-3">
        <h1 className="text-2xl font-semibold text-ink">Processos</h1>
        <AjudaPopover titulo="Como funciona a fila de Processos">
          <p>
            Só chega aqui um BITin que precisa mesmo de revisão de roteiro (algum material com
            alteração D/P, D/- ou -/P). BITins que não precisam disso (ex.: só troca de
            fornecedor, -/F) vão direto pra "Aguardando cadastro" no Cadastro, sem passar por
            Processos -- por isso não aparecem nem em "Pendente" nem em "Revisado" aqui.
          </p>
          <p>
            <strong>Etapa "Pendente"</strong>: aguardando você revisar o roteiro. Abra o BITin e
            use os botões "Atualizar processos"/"Concluir" na própria tela dele.
          </p>
          <p>
            <strong>Etapa "Revisado"</strong>: você já concluiu e devolveu pro Cadastro seguir o
            fluxo (cadastrar no SAP, depois baixar PDF e mandar pro Windchill) -- fica aqui só
            como histórico, sem ação pendente sua.
          </p>
          <p>O Status de todo BITin aqui é sempre "Enviado" -- só o Cadastro fecha o BITin de vez.</p>
        </AjudaPopover>
      </div>

      <FiltroEtapaToolbar
        opcoes={OPCOES_ETAPA}
        valor={etapa}
        onChange={setEtapa}
        busca={busca}
        onBuscaChange={setBusca}
      />

      <BitinTableSection bitins={bitins} erro={erro} colunas={COLUNAS} />
    </div>
  )
}
