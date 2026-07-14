import { useEffect, useState } from 'react'
import { useAuth } from '../context/AuthContext'
import { api } from '../lib/api'
import { version as appVersion } from '../../package.json'
import type { Sector, User } from '../lib/types'

// Mesmo nível usado em backend/api/bitins.py::ADMIN_LEVEL -- só espelhado aqui pra decidir o
// que mostrar na tela; o backend continua sendo quem de fato garante a permissão (PATCH
// /users/{id}/permission exige nível 99 pra valer, com ou sem essa checagem no frontend).
const ADMIN_LEVEL = 99
const NIVEL_LABEL: Record<number, string> = { 0: 'Usuário', 1: 'Gestor', 99: 'Admin' }
function nivelLabel(nivel: number) {
  return NIVEL_LABEL[nivel] ?? `Nível ${nivel}`
}

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
    <div className="mx-auto max-w-2xl">
      <h1 className="text-2xl font-semibold text-ink">Configurações</h1>

      <section className="mt-6 rounded-lg border border-line bg-surface p-5">
        <h2 className="text-sm font-semibold uppercase tracking-wide text-ink-muted">Minha conta</h2>
        <dl className="mt-4 grid grid-cols-1 gap-4 sm:grid-cols-2">
          <InfoField label="Nome" value={user?.nome} />
          <InfoField label="E-mail" value={user?.email} />
          <InfoField label="Setor" value={setorNome ?? (user?.sector_id ? `#${user.sector_id}` : 'Sem setor')} />
          <InfoField label="Nível de permissão" value={user ? nivelLabel(user.permission_level) : undefined} />
        </dl>
      </section>

      {user && user.permission_level >= ADMIN_LEVEL && <GestaoUsuarios sectors={sectors} />}

      <section className="mt-6 rounded-lg border border-line bg-surface p-5">
        <h2 className="text-sm font-semibold uppercase tracking-wide text-ink-muted">Sobre</h2>
        <p className="mt-3 text-sm text-ink">
          BITin <span className="text-ink-muted">— v{appVersion}</span>
        </p>
      </section>
    </div>
  )
}

function InfoField({ label, value }: { label: string; value: string | undefined }) {
  return (
    <div>
      <dt className="text-xs uppercase tracking-wide text-ink-muted">{label}</dt>
      <dd className="mt-0.5 text-sm text-ink">{value ?? '—'}</dd>
    </div>
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
    <section className="mt-6 rounded-lg border border-line bg-surface p-5">
      <h2 className="text-sm font-semibold uppercase tracking-wide text-ink-muted">Gestão de usuários</h2>

      {error && <p className="mt-3 text-sm text-red-600">{error}</p>}
      {!users && !error && <p className="mt-3 text-sm text-ink-muted">Carregando...</p>}

      {users && (
        <div className="mt-3 overflow-hidden rounded border border-line">
          <table className="w-full text-left text-sm">
            <thead>
              <tr className="bg-surface-alt text-xs uppercase tracking-wide text-ink-muted">
                <th className="px-3 py-2 font-medium">Nome</th>
                <th className="px-3 py-2 font-medium">E-mail</th>
                <th className="px-3 py-2 font-medium">Setor</th>
                <th className="px-3 py-2 font-medium">Nível</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-line">
              {users.map((u) => {
                const souEu = u.id === currentUser?.id
                return (
                  <tr key={u.id}>
                    <td className="px-3 py-2 text-ink">{u.nome}</td>
                    <td className="px-3 py-2 text-ink-muted">{u.email}</td>
                    <td className="px-3 py-2 text-ink-muted">
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
    </section>
  )
}
