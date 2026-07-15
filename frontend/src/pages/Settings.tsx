import { useEffect, useState, type FormEvent } from 'react'
import Card from '../components/Card'
import DetailField from '../components/DetailField'
import { useAuth } from '../context/AuthContext'
import { api } from '../lib/api'
import type { ChangePasswordRequest, Sector, User } from '../lib/types'

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

  const setorNome = sectors.find((s) => s.id === user?.sector_id)?.nome

  return (
    <div className="mx-auto max-w-6xl">
      <h1 className="text-2xl font-semibold text-ink">Configurações</h1>

      <Card title="Minha conta">
        <dl className="mt-4 grid grid-cols-1 gap-4 sm:grid-cols-2">
          <DetailField label="Nome" value={user?.nome} />
          <DetailField label="E-mail" value={user?.email} />
          <DetailField label="Setor" value={setorNome ?? (user?.sector_id ? `#${user.sector_id}` : 'Sem setor')} />
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

  return (
    <Card title="Gestão de usuários">
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
                      {sectors.find((s) => s.id === u.sector_id)?.nome ?? '—'}
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
