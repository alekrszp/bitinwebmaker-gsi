import { useEffect, useMemo, useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { ChevronDownIcon, SearchIcon } from '../components/icons'
import AjudaPopover from '../components/bitin/AjudaPopover'
import BitinTableSection from '../components/bitin/BitinTableSection'
import { COLUNAS_PADRAO_BITIN } from '../components/bitin/bitinColunas'
import { useAuth } from '../hooks/useAuth'
import { useDebouncedValue } from '../hooks/useDebouncedValue'
import { api } from '../lib/api'
import { criarRascunhoENavegar } from '../lib/criarBitin'
import { SETOR_CADASTRO, SETOR_PROCESSOS, ehDoSetor, isAdmin, isGestor } from '../lib/permissions'
import type { Bitin } from '../lib/types'

// Escopo desta rodada (decidido com o usuário, ver docs/FRONTEND.md): listagem + clique na
// linha abre uma visualização só-leitura (BitinDetail.tsx). GET /bitins vem escopado por
// nível no backend (2026-07-15, ver backend/api/bitins.py::list_bitins): usuário comum só os
// próprios, gestor os de quem compartilha setor, admin o sistema inteiro -- por isso o título
// e o rótulo de busca abaixo não presumem mais "só os meus" pra todo mundo.
type Aba = 'todos' | 'rascunho' | 'enviado'
type CampoBusca = 'todos' | 'codigo' | 'motivo' | 'solicitante'

const ABAS: { value: Aba; label: string }[] = [
  { value: 'todos', label: 'Todos' },
  { value: 'rascunho', label: 'Rascunhos' },
  { value: 'enviado', label: 'Enviados' },
]

const ABAS_VALIDAS = new Set<Aba>(['todos', 'rascunho', 'enviado'])

export default function MeusBitins() {
  const { user } = useAuth()
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const abaInicial = searchParams.get('status')
  const [aba, setAba] = useState<Aba>(
    abaInicial && ABAS_VALIDAS.has(abaInicial as Aba) ? (abaInicial as Aba) : 'todos',
  )
  const [campoBusca, setCampoBusca] = useState<CampoBusca>('todos')
  const [busca, setBusca] = useState('')
  const termo = useDebouncedValue(busca.trim())
  const [bitins, setBitins] = useState<Bitin[] | null>(null)
  const [erro, setErro] = useState<string | null>(null)

  // "Solicitante" como opção de busca só faz sentido pra quem lida com BITins de várias
  // pessoas -- um engenheiro individual (77, engenharia) normalmente é o próprio solicitante
  // dos seus BITins (decisão do usuário, 2026-07-14). Gestor (qualquer setor), Cadastro e
  // Processos (times centrais) e Admin ganham a opção -- 2ª revisão do modelo de permissões
  // (2026-07-20): antes era um threshold numérico (`>= GESTOR_LEVEL`), que parou de fazer
  // sentido com o esquema novo (77 virou o rank MAIS BAIXO, não mais Gestor).
  const ehAdmin = isAdmin(user?.permission_level)
  const ehGestorOuAdmin =
    ehAdmin ||
    isGestor(user?.permission_level) ||
    ehDoSetor(user?.permission_level, user?.setor, SETOR_CADASTRO, SETOR_PROCESSOS)
  // Processos ganhou tela própria em 2026-07-20 (ProcessosPage.tsx, rota /processos) --
  // não aterrissa mais aqui pelo menu (Sidebar.tsx), então a coluna "Processamento" que
  // existia nesta tela saiu (redundante com a tela dedicada). `ehSoProcessos` continua só
  // como rede de segurança: se alguém digitar /bitins na URL diretamente, "+ Novo BITin"
  // continua escondido (2026-07-17, pedido explícito: "processos não pode fazer bitin, só
  // fazer a parte da revisão de roteiro") -- mesma checagem EXATA (não admin) de sempre.
  const ehSoProcessos = ehDoSetor(user?.permission_level, user?.setor, SETOR_PROCESSOS)
  // Cadastro também não cria/edita BITin próprio (2026-07-20, pedido explícito: "usuário de
  // cadastro tem somente a tela cadastro... não pode criar novo bitin nem alterá-lo") --
  // mesma checagem exata (não `isCadastro`, que inclui admin), backend também recusa 403.
  const ehSoCadastro = ehDoSetor(user?.permission_level, user?.setor, SETOR_CADASTRO)
  const camposBusca = useMemo(() => {
    const base: { value: CampoBusca; label: string }[] = [
      { value: 'todos', label: 'Tudo' },
      { value: 'codigo', label: 'Número' },
      { value: 'motivo', label: 'Motivo' },
    ]
    if (ehGestorOuAdmin) {
      base.push({ value: 'solicitante', label: 'Solicitante' })
    }
    return base
  }, [ehGestorOuAdmin])

  function carregar() {
    let cancelado = false
    setBitins(null)
    setErro(null)
    const params: Record<string, string> = {}
    if (aba !== 'todos') params.status = aba
    if (termo) {
      params.termo = termo
      if (campoBusca !== 'todos') params.campo = campoBusca
    }
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

  useEffect(carregar, [aba, termo, campoBusca, searchParams])

  // Excluir BITin já enviado (2026-07-16, admin-only) é mais grave que excluir rascunho --
  // libera o número sequencial -- por isso o texto de confirmação muda pro caso "enviado"
  // (mesma cópia usada em BitinDetail.tsx::handleExcluirEnviado, pra ficar consistente entre
  // as duas telas onde isso aparece).
  // "+ Novo BITin" cria o rascunho na hora (sem tela intermediária em branco, ver
  // lib/criarBitin.ts) e navega direto pro editor completo.
  async function novoBitin() {
    setErro(null)
    try {
      await criarRascunhoENavegar(navigate)
    } catch {
      setErro('Não foi possível criar um novo BITin. Tente novamente.')
    }
  }

  async function excluir(bitin: Bitin) {
    const mensagem =
      bitin.status === 'enviado'
        ? `Excluir este BITin já enviado (código ${bitin.codigo ?? '—'})? Essa ação não pode ser desfeita e vai liberar o número sequencial.`
        : 'Excluir este rascunho? Essa ação não pode ser desfeita.'
    if (!window.confirm(mensagem)) return
    try {
      await api.delete(`/bitins/${bitin.mongo_id}`)
      setBitins((atual) => atual?.filter((b) => b.mongo_id !== bitin.mongo_id) ?? null)
    } catch {
      setErro('Não foi possível excluir. Tente novamente.')
    }
  }

  return (
    <div>
      <div className="flex flex-wrap items-center justify-between gap-4">
        {/* Rota/menu continua "Meus Bitins" (Sidebar.tsx) -- só o título aqui dentro muda pra
            não soar enganoso pra quem vê BITins de outras pessoas (gestor/admin, 2026-07-15). */}
        <div className="flex flex-wrap items-center gap-3">
          <h1 className="text-2xl font-semibold text-ink">{ehGestorOuAdmin ? 'BITins' : 'Meus Bitins'}</h1>
          <AjudaPopover titulo="Hint">
            <p>
              Abas <strong>Todos/Rascunhos/Enviados</strong> filtram por Status. Rascunho é livre
              pra editar; depois de Enviado, o BITin fica travado (só volta a mudar de mãos pelos
              fluxos de Cadastro/Processos).
            </p>
            <p>A busca aceita motivo, número ou solicitante -- escolha o campo no seletor ao lado da lupa.</p>
            <p>
              O "×" na última coluna exclui o BITin -- libera o número sequencial se já tiver
              sido enviado. Ação irreversível.
            </p>
          </AjudaPopover>
        </div>

        <div className="flex items-center gap-3">
          <div className="flex w-full max-w-lg items-center rounded-lg border border-line bg-surface focus-within:ring-2 focus-within:ring-brand-navy/30">
            <SearchIcon className="pointer-events-none ml-3.5 h-5 w-5 shrink-0 text-ink-faint" />
            <input
              type="text"
              value={busca}
              onChange={(e) => setBusca(e.target.value)}
              placeholder="Buscar..."
              className="w-full min-w-0 bg-transparent py-3 pl-2.5 pr-3 text-sm text-ink placeholder:text-ink-faint focus:outline-none"
            />
            <div className="h-6 w-px shrink-0 bg-line" />
            <div className="relative shrink-0">
              {/* appearance-none + seta própria -- a seta nativa do <select> ficava
                  encostada no canto, e a lista de opções ignorava o tema escuro em alguns
                  navegadores (o [color-scheme] força o popup nativo a respeitar o tema,
                  bg-surface sozinho não é suficiente pra isso). */}
              <select
                value={campoBusca}
                onChange={(e) => setCampoBusca(e.target.value as CampoBusca)}
                aria-label="Buscar em"
                className="dark:[color-scheme:dark] [color-scheme:light] appearance-none rounded-r-lg bg-surface py-3 pl-2.5 pr-8 text-sm text-ink-muted focus:outline-none"
              >
                {camposBusca.map(({ value, label }) => (
                  <option key={value} value={value}>
                    {label}
                  </option>
                ))}
              </select>
              <ChevronDownIcon className="pointer-events-none absolute right-2.5 top-1/2 h-4 w-4 -translate-y-1/2 text-ink-faint" />
            </div>
          </div>
          {/* Nem Processos nem Cadastro criam BITin (2026-07-17/20, pedido explícito) --
              backend também recusa (403) se essa checagem de UI for contornada, ver
              POST /bitins/draft::create_or_update_draft. */}
          {!ehSoProcessos && !ehSoCadastro && (
            <button
              type="button"
              onClick={novoBitin}
              className="whitespace-nowrap rounded-lg bg-brand-navy px-4 py-3 text-sm font-medium text-white transition-colors hover:bg-brand-navy-dark"
            >
              + Novo BITin
            </button>
          )}
        </div>
      </div>

      <div className="mt-4 flex gap-1 border-b border-line">
        {ABAS.map(({ value, label }) => (
          <button
            key={value}
            type="button"
            onClick={() => setAba(value)}
            className={`-mb-px border-b-2 px-3 py-2 text-sm font-medium transition-colors ${
              aba === value
                ? 'border-brand-navy text-ink'
                : 'border-transparent text-ink-muted hover:text-ink'
            }`}
          >
            {label}
          </button>
        ))}
      </div>

      <BitinTableSection
        bitins={bitins}
        erro={erro}
        colunas={COLUNAS_PADRAO_BITIN}
        acoes={(b) => {
          const podeExcluir = (b.status === 'rascunho' && b.pode_editar) || (b.status === 'enviado' && ehAdmin)
          if (!podeExcluir) return null
          return (
            <button
              type="button"
              onClick={() => excluir(b)}
              className="text-ink-faint hover:text-red-600"
              aria-label={b.status === 'rascunho' ? 'Excluir rascunho' : 'Excluir BITin enviado'}
              title={b.status === 'rascunho' ? 'Excluir rascunho' : 'Excluir BITin enviado'}
            >
              ×
            </button>
          )
        }}
        mensagemVazia="Nenhum BITin encontrado."
      />
    </div>
  )
}
