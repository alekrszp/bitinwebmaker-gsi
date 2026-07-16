import { useEffect, useState } from 'react'
import Card from '../Card'
import CriarUsuarioForm from './CriarUsuarioForm'
import { useAuth } from '../../hooks/useAuth'
import { api } from '../../lib/api'
import type { Sector, User } from '../../lib/types'

export default function GestaoUsuarios({ sectors }: { sectors: Sector[] }) {
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
                // Admin (99) nunca pode ser rebaixado por ninguém, nem por outro admin
                // (2026-07-16, "ninguém pode tirar permissão dele") -- PATCH /users/{id}/
                // permission já rejeita isso no backend com 400; aqui só evita a chamada
                // inútil desabilitando a linha inteira pra qualquer usuário logado, não só
                // pra si mesmo.
                const ehAdmin = u.permission_level === 99
                const desabilitado = souEu || ehAdmin || salvandoId === u.id
                const titulo = ehAdmin
                  ? 'Não é possível alterar a permissão de um administrador.'
                  : souEu
                    ? 'Você não pode alterar o próprio nível'
                    : undefined
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
                        disabled={desabilitado}
                        onChange={(e) => alterarNivel(u.id, Number(e.target.value))}
                        title={titulo}
                        className="rounded border border-line bg-surface px-2 py-1 text-sm text-ink disabled:opacity-50"
                      >
                        <option value={66}>Usuário</option>
                        <option value={77}>Gestor</option>
                        <option value={88}>Cadastro</option>
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
