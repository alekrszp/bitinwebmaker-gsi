import { useEffect, useState, type FormEvent } from 'react'
import Card from '../components/Card'
import DetailField from '../components/DetailField'
import { useAuth } from '../context/AuthContext'
import { api } from '../lib/api'
import type { AdminUserCreateRequest, AdminUserCreateResponse, ChangePasswordRequest, Sector, User } from '../lib/types'

// Extrai mensagem de erro de uma resposta da API -- duas formas possíveis: {detail: string}
// (ex.: senha atual incorreta, backend/auth/routes.py::change_password) ou {detail: [{msg}]}
// (erro de validação do Pydantic, ex.: senha nova fraca, backend/auth/schemas.py::
// ChangePasswordRequest). Mesmo duck-typing de Login.tsx (não usa axios.isAxiosError).
function extrairErro(err: unknown, fallback: string): string {
  const detail = (err as { response?: { data?: { detail?: unknown } } })?.response?.data?.detail
  if (typeof detail === 'string') return detail
  if (Array.isArray(detail) && detail[0]?.msg) return String(detail[0].msg)
  return fallback
}

// Mesmo nível usado em backend/api/bitins.py::ADMIN_LEVEL -- só espelhado aqui pra decidir o
// que mostrar na tela; o backend continua sendo quem de fato garante a permissão (PATCH
// /users/{id}/permission exige nível 99 pra valer, com ou sem essa checagem no frontend).
const ADMIN_LEVEL = 99

export default function Settings() {
  const { user } = useAuth()
  const [sectors, setSectors] = useState<Sector[]>([])

  useEffect(() => {
    api
      .get('/sectors')
      .then((resp) => setSectors(resp.data))
      .catch(() => {}) // "Minha conta" ainda funciona sem o nome do setor -- só cai pro id
  }, [])

  // "Minha conta" -- vários setores possíveis agora (2026-07-15, era sector_id único): junta
  // os nomes com vírgula, mesma convenção usada na tabela de GestaoUsuarios abaixo.
  const setoresNomes = (user?.sector_ids ?? [])
    .map((id) => sectors.find((s) => s.id === id)?.nome ?? `#${id}`)
    .join(', ')

  return (
    <div className="mx-auto max-w-6xl">
      <h1 className="text-2xl font-semibold text-ink">Configurações</h1>

      <Card title="Minha conta">
        <dl className="mt-4 grid grid-cols-1 gap-4 sm:grid-cols-2">
          <DetailField label="Nome" value={user?.nome} />
          <DetailField label="E-mail" value={user?.email} />
          <DetailField label="Setor" value={setoresNomes || 'Sem setor'} />
        </dl>

        <TrocarSenhaForm />
      </Card>

      {user && user.permission_level >= ADMIN_LEVEL && <GestaoUsuarios sectors={sectors} />}
    </div>
  )
}

// Autoatendimento de troca de senha (2026-07-15, pedido explícito do usuário: "wired into the
// Settings screen") -- antes disso não existia nenhum jeito de trocar a própria senha sem
// edição direta no banco. POST /auth/change-password (backend/auth/routes.py) valida a senha
// atual e a força da nova (mesma regra de UserCreate.password no registro).
function TrocarSenhaForm() {
  const [senhaAtual, setSenhaAtual] = useState('')
  const [senhaNova, setSenhaNova] = useState('')
  const [confirmarSenha, setConfirmarSenha] = useState('')
  const [erro, setErro] = useState<string | null>(null)
  const [sucesso, setSucesso] = useState(false)
  const [enviando, setEnviando] = useState(false)

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setErro(null)
    setSucesso(false)

    // Checagem client-side barata -- a validação de verdade (força da senha, senha atual
    // correta) é sempre do servidor, isso aqui só evita uma ida à API por engano de digitação.
    if (senhaNova !== confirmarSenha) {
      setErro('A confirmação não bate com a nova senha.')
      return
    }

    setEnviando(true)
    try {
      const body: ChangePasswordRequest = { senha_atual: senhaAtual, senha_nova: senhaNova }
      await api.post('/auth/change-password', body)
      setSucesso(true)
      setSenhaAtual('')
      setSenhaNova('')
      setConfirmarSenha('')
    } catch (err) {
      setErro(extrairErro(err, 'Não foi possível trocar a senha. Tente novamente.'))
    } finally {
      setEnviando(false)
    }
  }

  return (
    <form onSubmit={handleSubmit} className="mt-6 max-w-sm border-t border-line pt-5">
      <h3 className="text-xs font-semibold uppercase tracking-wide text-ink-muted">Trocar senha</h3>

      <div className="mt-3 space-y-3">
        <div>
          <label htmlFor="senha-atual" className="mb-1.5 block text-xs uppercase tracking-wide text-ink-muted">
            Senha atual
          </label>
          <input
            id="senha-atual"
            type="password"
            autoComplete="current-password"
            value={senhaAtual}
            onChange={(e) => setSenhaAtual(e.target.value)}
            className="w-full rounded-lg border border-line bg-surface px-3 py-2 text-sm text-ink focus:border-brand-navy focus:outline-none focus:ring-2 focus:ring-brand-navy/20"
          />
        </div>
        <div>
          <label htmlFor="senha-nova" className="mb-1.5 block text-xs uppercase tracking-wide text-ink-muted">
            Nova senha
          </label>
          <input
            id="senha-nova"
            type="password"
            autoComplete="new-password"
            value={senhaNova}
            onChange={(e) => setSenhaNova(e.target.value)}
            className="w-full rounded-lg border border-line bg-surface px-3 py-2 text-sm text-ink focus:border-brand-navy focus:outline-none focus:ring-2 focus:ring-brand-navy/20"
          />
        </div>
        <div>
          <label htmlFor="confirmar-senha" className="mb-1.5 block text-xs uppercase tracking-wide text-ink-muted">
            Confirmar nova senha
          </label>
          <input
            id="confirmar-senha"
            type="password"
            autoComplete="new-password"
            value={confirmarSenha}
            onChange={(e) => setConfirmarSenha(e.target.value)}
            className="w-full rounded-lg border border-line bg-surface px-3 py-2 text-sm text-ink focus:border-brand-navy focus:outline-none focus:ring-2 focus:ring-brand-navy/20"
          />
        </div>
      </div>

      {erro && <p className="mt-3 text-sm text-red-600">{erro}</p>}
      {sucesso && <p className="mt-3 text-sm text-green-600">Senha alterada com sucesso.</p>}

      <button
        type="submit"
        disabled={enviando || !senhaAtual || !senhaNova || !confirmarSenha}
        className="mt-4 rounded-lg bg-brand-navy px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-brand-navy-dark disabled:cursor-not-allowed disabled:opacity-60"
      >
        {enviando ? 'Salvando...' : 'Salvar nova senha'}
      </button>
    </form>
  )
}

function GestaoUsuarios({ sectors }: { sectors: Sector[] }) {
  const { user: currentUser } = useAuth()
  const [users, setUsers] = useState<User[] | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [salvandoId, setSalvandoId] = useState<number | null>(null)

  useEffect(() => {
    api
      .get('/users')
      .then((resp) => setUsers(resp.data))
      .catch(() => setError('Não foi possível carregar a lista de usuários.'))
  }, [])

  async function alterarNivel(userId: number, novoNivel: number) {
    setSalvandoId(userId)
    setError(null)
    try {
      const resp = await api.patch(`/users/${userId}/permission`, { permission_level: novoNivel })
      setUsers((atual) => atual?.map((u) => (u.id === userId ? resp.data : u)) ?? null)
    } catch {
      setError('Não foi possível alterar o nível desse usuário.')
    } finally {
      setSalvandoId(null)
    }
  }

  function adicionarUsuarioCriado(novo: User) {
    // Mesmo padrão de atualização otimista local de alterarNivel acima -- evita um refetch de
    // GET /users só pra mostrar a linha nova, o admin já vê o usuário na tabela sem reload.
    setUsers((atual) => (atual ? [...atual, novo] : [novo]))
  }

  return (
    <Card title="Gestão de usuários">
      <CriarUsuarioForm sectors={sectors} onCriado={adicionarUsuarioCriado} />

      {error && <p className="mt-3 text-sm text-red-600">{error}</p>}
      {!users && !error && <p className="mt-3 text-sm text-ink-muted">Carregando...</p>}

      {users && (
        <div className="mt-3 overflow-x-auto rounded border border-line">
          <table className="w-full text-left text-sm">
            <thead>
              <tr className="bg-surface-alt text-xs uppercase tracking-wide text-ink-muted">
                <th className="whitespace-nowrap px-3 py-2 font-medium">Nome</th>
                <th className="whitespace-nowrap px-3 py-2 font-medium">E-mail</th>
                <th className="whitespace-nowrap px-3 py-2 font-medium">Setor</th>
                <th className="whitespace-nowrap px-3 py-2 font-medium">Nível</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-line">
              {users.map((u) => {
                const souEu = u.id === currentUser?.id
                return (
                  <tr key={u.id}>
                    <td className="whitespace-nowrap px-3 py-2 text-ink">{u.nome}</td>
                    <td className="whitespace-nowrap px-3 py-2 text-ink-muted">{u.email}</td>
                    <td className="whitespace-nowrap px-3 py-2 text-ink-muted">
                      {u.sector_ids.length > 0
                        ? u.sector_ids.map((id) => sectors.find((s) => s.id === id)?.nome ?? `#${id}`).join(', ')
                        : '—'}
                    </td>
                    <td className="px-3 py-2">
                      <select
                        value={u.permission_level}
                        disabled={souEu || salvandoId === u.id}
                        onChange={(e) => alterarNivel(u.id, Number(e.target.value))}
                        title={souEu ? 'Você não pode alterar o próprio nível' : undefined}
                        className="rounded border border-line bg-surface px-2 py-1 text-sm text-ink disabled:opacity-50"
                      >
                        <option value={0}>Usuário</option>
                        <option value={1}>Gestor</option>
                        <option value={99}>Admin</option>
                      </select>
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      )}
    </Card>
  )
}

// Cadastro de usuário SÓ POR ADMIN (2026-07-15, pedido explícito: "tela de cadastro de usuário
// SÓ PARA ADMIN para não ter que cadastrar no banco"). POST /users (backend/api/users.py::
// create_user_by_admin, check_permission(99)) gera a senha temporária no servidor -- essa tela
// não tem campo de senha nenhum, só mostra a gerada UMA VEZ na resposta pro admin repassar
// fora do sistema (chat, verbalmente) antes do dono da conta trocar por conta própria no
// primeiro login (RequireAuth.tsx -> /definir-senha, ver Usuario.senha_temporaria).
function CriarUsuarioForm({ sectors, onCriado }: { sectors: Sector[]; onCriado: (u: User) => void }) {
  const [email, setEmail] = useState('')
  const [nome, setNome] = useState('')
  const [numeroEng, setNumeroEng] = useState('')
  // Vários setores marcáveis (2026-07-15, era um <select> de escolha única -- "um usuário
  // poder ser tanto armazenagem tanto quanto proteina").
  const [sectorIds, setSectorIds] = useState<number[]>([])
  const [permissionLevel, setPermissionLevel] = useState(0)
  const [erro, setErro] = useState<string | null>(null)
  const [enviando, setEnviando] = useState(false)
  const [senhaGerada, setSenhaGerada] = useState<{ nome: string; senha: string } | null>(null)

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setErro(null)
    setEnviando(true)
    try {
      const body: AdminUserCreateRequest = {
        email,
        nome,
        numero_eng: numeroEng.trim() || null,
        sector_ids: sectorIds,
        permission_level: permissionLevel,
      }
      const resp = await api.post<AdminUserCreateResponse>('/users', body)
      onCriado(resp.data)
      setSenhaGerada({ nome: resp.data.nome, senha: resp.data.senha_temporaria_gerada })
      setEmail('')
      setNome('')
      setNumeroEng('')
      setSectorIds([])
      setPermissionLevel(0)
    } catch (err) {
      setErro(extrairErro(err, 'Não foi possível cadastrar o usuário.'))
    } finally {
      setEnviando(false)
    }
  }

  return (
    <div className="border-b border-line pb-5">
      <h3 className="text-xs font-semibold uppercase tracking-wide text-ink-muted">Cadastrar usuário</h3>

      {senhaGerada && (
        <div className="mt-3 rounded-lg border border-amber-300 bg-amber-50 px-4 py-3 text-sm text-amber-900">
          <p className="font-medium">
            Senha temporária de {senhaGerada.nome}: <span className="font-mono">{senhaGerada.senha}</span>
          </p>
          <p className="mt-1 text-xs">
            Essa senha só aparece agora -- anote e repasse pra {senhaGerada.nome} antes de sair desta tela. No
            primeiro login ela vai ser obrigada a trocar por uma senha só dela.
          </p>
        </div>
      )}

      <form onSubmit={handleSubmit} className="mt-3 grid grid-cols-1 gap-3 sm:grid-cols-2">
        <div>
          <label htmlFor="novo-email" className="mb-1.5 block text-xs uppercase tracking-wide text-ink-muted">
            E-mail
          </label>
          <input
            id="novo-email"
            type="email"
            required
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            className="w-full rounded-lg border border-line bg-surface px-3 py-2 text-sm text-ink focus:border-brand-navy focus:outline-none focus:ring-2 focus:ring-brand-navy/20"
          />
        </div>
        <div>
          <label htmlFor="novo-nome" className="mb-1.5 block text-xs uppercase tracking-wide text-ink-muted">
            Nome
          </label>
          <input
            id="novo-nome"
            type="text"
            required
            value={nome}
            onChange={(e) => setNome(e.target.value)}
            className="w-full rounded-lg border border-line bg-surface px-3 py-2 text-sm text-ink focus:border-brand-navy focus:outline-none focus:ring-2 focus:ring-brand-navy/20"
          />
        </div>
        <div>
          <label htmlFor="novo-numero-eng" className="mb-1.5 block text-xs uppercase tracking-wide text-ink-muted">
            ID
          </label>
          <input
            id="novo-numero-eng"
            type="text"
            value={numeroEng}
            onChange={(e) => setNumeroEng(e.target.value)}
            className="w-full rounded-lg border border-line bg-surface px-3 py-2 text-sm text-ink focus:border-brand-navy focus:outline-none focus:ring-2 focus:ring-brand-navy/20"
          />
        </div>
        <div>
          {/* Checkbox group em vez de <select> de escolha única (2026-07-15) -- um usuário
              pode pertencer a mais de um setor ao mesmo tempo. Não hardcoda os 2 setores
              conhecidos hoje: itera `sectors`, continua correto se um 3º for cadastrado. */}
          <span className="mb-1.5 block text-xs uppercase tracking-wide text-ink-muted">
            Setor (opcional, pode marcar mais de um)
          </span>
          <div className="flex flex-wrap gap-x-4 gap-y-1.5 rounded-lg border border-line bg-surface px-3 py-2">
            {sectors.length === 0 && <span className="text-sm text-ink-faint">Nenhum setor cadastrado</span>}
            {sectors.map((s) => (
              <label key={s.id} className="flex items-center gap-1.5 text-sm text-ink">
                <input
                  type="checkbox"
                  checked={sectorIds.includes(s.id)}
                  onChange={(e) =>
                    setSectorIds((atual) =>
                      e.target.checked ? [...atual, s.id] : atual.filter((id) => id !== s.id),
                    )
                  }
                  className="rounded border-line text-brand-navy focus:ring-brand-navy/20"
                />
                {s.nome}
              </label>
            ))}
          </div>
        </div>
        <div>
          <label htmlFor="novo-permissao" className="mb-1.5 block text-xs uppercase tracking-wide text-ink-muted">
            Permissão
          </label>
          <select
            id="novo-permissao"
            value={permissionLevel}
            onChange={(e) => setPermissionLevel(Number(e.target.value))}
            className="w-full rounded-lg border border-line bg-surface px-3 py-2 text-sm text-ink focus:border-brand-navy focus:outline-none focus:ring-2 focus:ring-brand-navy/20"
          >
            <option value={0}>Usuário</option>
            <option value={1}>Gestor</option>
            <option value={99}>Admin</option>
          </select>
        </div>

        {erro && <p className="sm:col-span-2 text-sm text-red-600">{erro}</p>}

        <div className="sm:col-span-2">
          <button
            type="submit"
            disabled={enviando || !email || !nome}
            className="rounded-lg bg-brand-navy px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-brand-navy-dark disabled:cursor-not-allowed disabled:opacity-60"
          >
            {enviando ? 'Cadastrando...' : 'Cadastrar usuário'}
          </button>
        </div>
      </form>
    </div>
  )
}
