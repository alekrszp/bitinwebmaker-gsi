import { useEffect, useState } from 'react'
import Card from '../Card'
import CriarUsuarioForm from './CriarUsuarioForm'
import { TrashIcon } from '../icons'
import { useAuth } from '../../hooks/useAuth'
import { api } from '../../lib/api'
import type { Subgrupo, User } from '../../lib/types'

// Espelha backend/auth/schemas.py::NIVEIS_QUE_EXIGEM_SUBGRUPO (2026-07-16) -- só Admin (99)
// pode ficar sem subgrupo. Checagem no cliente é só UX (mesmo espírito de CriarUsuarioForm.tsx);
// o backend (PATCH /users/{id}/subgrupos) continua sendo quem de fato garante a regra.
const NIVEIS_QUE_EXIGEM_SUBGRUPO = new Set([66, 77, 88])

// Opções do rótulo de papel "Setor" (2026-07-16, NOVO) -- mesmas de CriarUsuarioForm.tsx,
// independente de Permissão e de Subgrupo.
const OPCOES_SETOR: { value: string; label: string }[] = [
  { value: 'cadastro', label: 'Cadastro' },
  { value: 'gestor', label: 'Gestor' },
  { value: 'usuario', label: 'Usuário' },
]

export default function GestaoUsuarios({ subgrupos }: { subgrupos: Subgrupo[] }) {
  const { user: currentUser } = useAuth()
  const [users, setUsers] = useState<User[] | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [salvandoId, setSalvandoId] = useState<number | null>(null)
  // Id do usuário cujo subgrupo está sendo salvo -- separado de salvandoId (nível) pra não
  // desabilitar o <select> de nível enquanto só o subgrupo está sendo salvo, e vice-versa.
  const [salvandoSubgrupoId, setSalvandoSubgrupoId] = useState<number | null>(null)
  // Id do usuário cujo setor (rótulo de papel) está sendo salvo -- mesmo padrão, controle
  // separado dos dois acima.
  const [salvandoSetorId, setSalvandoSetorId] = useState<number | null>(null)
  // Id do usuário sendo excluído (2026-07-17) -- mesmo padrão dos outros controles de loading
  // por linha acima.
  const [excluindoId, setExcluindoId] = useState<number | null>(null)

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

  // Reatribuição de subgrupo(s) de um usuário já cadastrado (2026-07-16, pedido explícito do
  // admin) -- mesmo padrão de auto-save-on-change de alterarNivel acima, mas contra o
  // endpoint dedicado PATCH /users/{id}/subgrupos (não sobrecarrega /permission).
  async function alterarSubgrupos(userId: number, novosSubgrupoIds: number[]) {
    setSalvandoSubgrupoId(userId)
    setError(null)
    try {
      const resp = await api.patch(`/users/${userId}/subgrupos`, { subgrupo_ids: novosSubgrupoIds })
      setUsers((atual) => atual?.map((u) => (u.id === userId ? resp.data : u)) ?? null)
    } catch {
      setError('Não foi possível alterar o subgrupo desse usuário.')
    } finally {
      setSalvandoSubgrupoId(null)
    }
  }

  // Alteração do rótulo de papel "Setor" (2026-07-16, NOVO) -- mesmo padrão de auto-save-on-
  // change de alterarNivel/alterarSubgrupos, contra o endpoint dedicado PATCH /users/{id}/setor.
  async function alterarSetor(userId: number, novoSetor: string) {
    setSalvandoSetorId(userId)
    setError(null)
    try {
      const resp = await api.patch(`/users/${userId}/setor`, { setor: novoSetor })
      setUsers((atual) => atual?.map((u) => (u.id === userId ? resp.data : u)) ?? null)
    } catch {
      setError('Não foi possível alterar o setor desse usuário.')
    } finally {
      setSalvandoSetorId(null)
    }
  }

  // Exclusão de usuário (2026-07-17, pedido explícito) -- DELETE /users/{id} é soft-delete no
  // servidor (backend/api/users.py::delete_user marca ativo=False, não apaga a linha; ver
  // comentário lá pro porquê). GET /users já filtra ativo=False, então basta remover a linha
  // do estado local igual a um delete de verdade, sem precisar de refetch.
  async function excluirUsuario(userId: number, nome: string) {
    if (!window.confirm(`Excluir o usuário "${nome}"? Ele não vai mais conseguir acessar o sistema.`)) return
    setExcluindoId(userId)
    setError(null)
    try {
      await api.delete(`/users/${userId}`)
      setUsers((atual) => atual?.filter((u) => u.id !== userId) ?? null)
    } catch {
      setError('Não foi possível excluir esse usuário.')
    } finally {
      setExcluindoId(null)
    }
  }

  function adicionarUsuarioCriado(novo: User) {
    // Mesmo padrão de atualização otimista local de alterarNivel acima -- evita um refetch de
    // GET /users só pra mostrar a linha nova, o admin já vê o usuário na tabela sem reload.
    setUsers((atual) => (atual ? [...atual, novo] : [novo]))
  }

  return (
    <Card id="gestao-usuarios" title="Gestão de usuários">
      <CriarUsuarioForm subgrupos={subgrupos} onCriado={adicionarUsuarioCriado} />

      {error && <p className="mt-3 text-sm text-red-600">{error}</p>}
      {!users && !error && <p className="mt-3 text-sm text-ink-muted">Carregando...</p>}

      {users && (
        <div className="mt-3 overflow-x-auto rounded border border-line">
          <table className="w-full text-left text-sm">
            <thead>
              <tr className="bg-surface-alt text-xs uppercase tracking-wide text-ink-muted">
                <th className="whitespace-nowrap px-3 py-2 font-medium">Nome</th>
                <th className="whitespace-nowrap px-3 py-2 font-medium">E-mail</th>
                <th className="whitespace-nowrap px-3 py-2 font-medium">Subgrupo</th>
                <th className="whitespace-nowrap px-3 py-2 font-medium">Setor</th>
                <th className="whitespace-nowrap px-3 py-2 font-medium">Nível</th>
                <th className="whitespace-nowrap px-3 py-2 font-medium"></th>
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
                    <td className="px-3 py-2">
                      {/* Checkbox group (2026-07-16, pedido explícito do admin: "reassign de
                          subgrupo de um usuário já cadastrado") -- mesmo padrão de múltipla
                          escolha de CriarUsuarioForm.tsx, auto-save on change (PATCH
                          /users/{id}/subgrupos) igual ao <select> de nível ao lado. */}
                      <div className="flex flex-wrap gap-x-3 gap-y-1">
                        {subgrupos.length === 0 && <span className="text-sm text-ink-faint">—</span>}
                        {subgrupos.map((s) => (
                          <label key={s.id} className="flex items-center gap-1 text-sm text-ink-muted">
                            <input
                              type="checkbox"
                              checked={u.subgrupo_ids.includes(s.id)}
                              disabled={salvandoSubgrupoId === u.id}
                              onChange={(e) => {
                                const novos = e.target.checked
                                  ? [...u.subgrupo_ids, s.id]
                                  : u.subgrupo_ids.filter((id) => id !== s.id)
                                if (NIVEIS_QUE_EXIGEM_SUBGRUPO.has(u.permission_level) && novos.length === 0) {
                                  setError('Este nível de permissão exige ao menos um subgrupo.')
                                  return
                                }
                                alterarSubgrupos(u.id, novos)
                              }}
                              className="rounded border-line text-brand-navy focus:ring-brand-navy/20"
                            />
                            {s.nome}
                          </label>
                        ))}
                      </div>
                    </td>
                    <td className="px-3 py-2">
                      {/* Rótulo de papel "Setor" (2026-07-16, NOVO) -- <select> com auto-save,
                          mesmo padrão do <select> de Nível ao lado; endpoint dedicado PATCH
                          /users/{id}/setor, sem vínculo com Permissão ou Subgrupo. */}
                      <select
                        value={u.setor}
                        disabled={salvandoSetorId === u.id}
                        onChange={(e) => alterarSetor(u.id, e.target.value)}
                        className="rounded border border-line bg-surface px-2 py-1 text-sm text-ink disabled:opacity-50"
                      >
                        {OPCOES_SETOR.map((o) => (
                          <option key={o.value} value={o.value}>
                            {o.label}
                          </option>
                        ))}
                      </select>
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
                    <td className="whitespace-nowrap px-3 py-2 text-right">
                      {/* Mesma proteção do backend (delete_user): admin nunca aparece excluível,
                          e ninguém exclui a própria conta -- desabilitar aqui só evita a chamada
                          inútil, o 400 do servidor é quem garante a regra de verdade. */}
                      <button
                        type="button"
                        onClick={() => excluirUsuario(u.id, u.nome)}
                        disabled={souEu || ehAdmin || excluindoId === u.id}
                        title={ehAdmin ? 'Não é possível excluir um administrador.' : souEu ? 'Você não pode excluir a si mesmo' : 'Excluir usuário'}
                        className="rounded p-1.5 text-ink-faint hover:bg-red-50 hover:text-red-600 disabled:cursor-not-allowed disabled:opacity-30 disabled:hover:bg-transparent dark:hover:bg-red-950"
                      >
                        <TrashIcon className="h-4 w-4" />
                      </button>
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
