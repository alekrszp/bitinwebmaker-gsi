import { useEffect, useMemo, useState } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'
import { ChevronDownIcon, SearchIcon } from '../components/icons'
import StatusBadge from '../components/bitin/StatusBadge'
import { useAuth } from '../hooks/useAuth'
import { api } from '../lib/api'
import { criarRascunhoENavegar } from '../lib/criarBitin'
import { NIVEL_PROCESSOS, isAdmin, isProcessos } from '../lib/permissions'
import type { Bitin } from '../lib/types'

// Escopo desta rodada (decidido com o usuário, ver docs/FRONTEND.md): listagem + clique na
// linha abre uma visualização só-leitura (BitinDetail.tsx). GET /bitins vem escopado por
// nível no backend (2026-07-15, ver backend/api/bitins.py::list_bitins): usuário comum só os
// próprios, gestor os de quem compartilha setor, admin o sistema inteiro -- por isso o título
// e o rótulo de busca abaixo não presumem mais "só os meus" pra todo mundo.
// GESTOR_LEVEL = 77 (2026-07-17, achado de auditoria -- era 1, sobra do esquema antigo
// 0/1/99). Com a revisão de permissões de 2026-07-16 (66/77/88/99), `>= 1` virou sempre
// verdadeiro pra QUALQUER usuário logado (66 já satisfaz), então usuário comum também via a
// opção de busca por "Solicitante" -- deveria ser só gestor/admin, como o comentário acima
// sempre disse que era a intenção. Sem risco de segurança (GET /bitins já é escopado certo
// no servidor, isso só controlava um campo de busca a mais na UI), mas era um bug real de UI.
const GESTOR_LEVEL = 77

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
  const [termo, setTermo] = useState('')
  const [bitins, setBitins] = useState<Bitin[] | null>(null)
  const [erro, setErro] = useState<string | null>(null)

  // "Solicitante" como opção de busca só faz sentido pra quem lida com BITins de várias
  // pessoas -- um engenheiro comum normalmente é o próprio solicitante dos seus BITins
  // (decisão do usuário, 2026-07-14). Gestor passou a ver BITins de colegas de setor
  // (2026-07-15), então ganha a mesma opção que já existia só pra admin.
  const ehGestorOuAdmin = (user?.permission_level ?? 0) >= GESTOR_LEVEL
  const ehAdmin = isAdmin(user?.permission_level)
  // Setor Processos (2026-07-17) -- ganha uma coluna extra mostrando quais BITins da fila
  // (encaminhados pelo Cadastro) ainda precisam de atenção vs já foram concluídos, já que
  // GET /bitins devolve os dois juntos pra esse nível (ver backend/api/bitins.py::list_bitins).
  const ehProcessos = isProcessos(user?.permission_level)
  // Diferente de `ehProcessos` acima (que inclui admin, pra permissão de UI genérica) --
  // aqui precisa ser EXATAMENTE o nível Processos, porque admin continua podendo criar BITin
  // normalmente (2026-07-17, pedido explícito: "processos não pode fazer bitin, só fazer a
  // parte da revisão de roteiro").
  const ehSoProcessos = user?.permission_level === NIVEL_PROCESSOS
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

  // Debounce -- espera parar de digitar antes de bater na API (GET /bitins?termo=&campo=, já
  // suportado no backend: busca em motivo/solicitante/número, tudo junto ou um campo só, ver
  // bitins.py).
  useEffect(() => {
    const id = setTimeout(() => setTermo(busca.trim()), 300)
    return () => clearTimeout(id)
  }, [busca])

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

  useEffect(carregar, [aba, termo, campoBusca])

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
        <h1 className="text-2xl font-semibold text-ink">{ehGestorOuAdmin ? 'BITins' : 'Meus Bitins'}</h1>

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
          {/* Processos não cria BITin, só revisa os encaminhados pelo Cadastro (2026-07-17,
              pedido explícito) -- backend também recusa (403) se essa checagem de UI for
              contornada, ver POST /bitins/draft::create_or_update_draft. */}
          {!ehSoProcessos && (
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

      {erro && <p className="mt-4 text-sm text-red-600">{erro}</p>}
      {!bitins && !erro && <p className="mt-4 text-sm text-ink-muted">Carregando...</p>}
      {bitins && bitins.length === 0 && !erro && (
        <p className="mt-4 text-sm text-ink-muted">Nenhum BITin encontrado.</p>
      )}

      {bitins && bitins.length > 0 && (
        <div className="mt-4 overflow-hidden rounded-lg border border-line">
          <table className="w-full text-left text-sm">
            <thead>
              <tr className="bg-surface-alt text-xs uppercase tracking-wide text-ink-muted">
                <th className="px-4 py-2 font-medium">Número</th>
                <th className="px-4 py-2 font-medium">Motivo</th>
                <th className="px-4 py-2 font-medium">Solicitante</th>
                <th className="px-4 py-2 font-medium">Status</th>
                {ehProcessos && <th className="px-4 py-2 font-medium">Processamento</th>}
                <th className="w-10" />
              </tr>
            </thead>
            <tbody className="divide-y divide-line bg-surface">
              {bitins.map((b) => (
                <tr key={b.mongo_id} className="hover:bg-surface-alt">
                  <td className="px-4 py-2">
                    <Link to={`/bitins/${b.mongo_id}`} className="block text-ink hover:underline">
                      {b.codigo ?? '—'}
                    </Link>
                  </td>
                  <td className="px-4 py-2 text-ink-muted">
                    <Link to={`/bitins/${b.mongo_id}`} className="block">
                      {String(b.content?.motivo ?? '—')}
                    </Link>
                  </td>
                  <td className="px-4 py-2 text-ink-muted">
                    <Link to={`/bitins/${b.mongo_id}`} className="block">
                      {String(b.content?.solicitante ?? '—')}
                    </Link>
                  </td>
                  <td className="px-4 py-2">
                    <Link to={`/bitins/${b.mongo_id}`} className="block">
                      <StatusBadge status={b.status} />
                    </Link>
                  </td>
                  {ehProcessos && (
                    <td className="px-4 py-2">
                      {b.encaminhado_roteiro ? (
                        <span
                          className={`whitespace-nowrap rounded-full px-2 py-0.5 text-xs font-medium ${
                            b.processos_concluido
                              ? 'bg-green-100 text-green-700'
                              : 'bg-amber-100 text-amber-800'
                          }`}
                        >
                          {b.processos_concluido ? 'Concluído' : 'Pendente'}
                        </span>
                      ) : (
                        <span className="text-xs text-ink-faint">—</span>
                      )}
                    </td>
                  )}
                  <td className="px-4 py-2 text-center">
                    {b.status === 'rascunho' && b.pode_editar && (
                      <button
                        type="button"
                        onClick={() => excluir(b)}
                        className="text-ink-faint hover:text-red-600"
                        aria-label="Excluir rascunho"
                        title="Excluir rascunho"
                      >
                        ×
                      </button>
                    )}
                    {b.status === 'enviado' && ehAdmin && (
                      <button
                        type="button"
                        onClick={() => excluir(b)}
                        className="text-ink-faint hover:text-red-600"
                        aria-label="Excluir BITin enviado"
                        title="Excluir BITin enviado"
                      >
                        ×
                      </button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
