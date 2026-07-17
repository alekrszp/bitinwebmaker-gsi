import { useEffect, useState } from 'react'
import Card from '../Card'
import CriarUsuarioForm from './CriarUsuarioForm'
import { TrashIcon } from '../icons'
import { useAuth } from '../../hooks/useAuth'
import { api } from '../../lib/api'
import { extrairErro } from '../../lib/errors'
import { montarMailtoSenhaTemporaria } from '../../lib/senhaTemporaria'
import type { AdminUserCreateResponse, Subgrupo, User } from '../../lib/types'

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
  // Id do usuário sendo reativado -- mesmo padrão.
  const [reativandoId, setReativandoId] = useState<number | null>(null)
  // Filtro Ativados/Desativados (2026-07-17, pedido explícito) -- GET /users devolve os dois
  // juntos agora (backend/api/users.py::list_users), filtra só no cliente.
  const [filtro, setFiltro] = useState<'ativos' | 'inativos'>('ativos')
  // Senha gerada pela reativação mais recente (2026-07-17, NOVO) -- mesmo padrão do callout
  // de CriarUsuarioForm.tsx: reativar agora gera senha nova do zero (POST /users/{id}/
  // reativar), mostrada UMA ÚNICA VEZ aqui.
  const [senhaReativacao, setSenhaReativacao] = useState<{ nome: string; senha: string; email: string } | null>(null)
  const [senhaReativacaoCopiada, setSenhaReativacaoCopiada] = useState(false)

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
    } catch (err) {
      // extrairErro (não só mensagem genérica) -- alvo sendo admin dá 400 do servidor com
      // motivo específico pra quem não tem o privilégio de mexer em outro admin (ver
      // super-admin oculto, backend/auth/deps.py::eh_super_admin); útil também é pra saber
      // que a exceção foi rejeitada (não "some" sem explicação).
      setError(extrairErro(err, 'Não foi possível alterar o nível desse usuário.'))
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
    } catch (err) {
      // extrairErro (2026-07-17, achado de auditoria, era mensagem genérica fixa) -- mesmo
      // padrão de alterarNivel/excluirUsuario, senão o 400 específico do servidor (ex.: alvo
      // é outro admin e quem chamou não é o super-admin oculto) ficava escondido.
      setError(extrairErro(err, 'Não foi possível alterar o subgrupo desse usuário.'))
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
    } catch (err) {
      setError(extrairErro(err, 'Não foi possível alterar o setor desse usuário.'))
    } finally {
      setSalvandoSetorId(null)
    }
  }

  // Exclusão de usuário (2026-07-17, pedido explícito) -- DELETE /users/{id} é soft-delete no
  // servidor (backend/api/users.py::delete_user marca ativo=False, não apaga a linha; ver
  // comentário lá pro porquê). GET /users agora devolve ativos e inativos juntos (pro filtro
  // Ativados/Desativados abaixo), então atualiza o registro em vez de removê-lo do estado --
  // ele só migra de aba (some de "Ativados", aparece em "Desativados").
  async function excluirUsuario(userId: number, nome: string) {
    if (!window.confirm(`Excluir o usuário "${nome}"? Ele não vai mais conseguir acessar o sistema.`)) return
    setExcluindoId(userId)
    setError(null)
    try {
      const resp = await api.delete(`/users/${userId}`)
      setUsers((atual) => atual?.map((u) => (u.id === userId ? resp.data : u)) ?? null)
    } catch (err) {
      setError(extrairErro(err, 'Não foi possível excluir esse usuário.'))
    } finally {
      setExcluindoId(null)
    }
  }

  // Reativação (2026-07-17) -- reverte o soft-delete, POST /users/{id}/reativar. Pedido
  // explícito: "quando eu reativo aparece de novo com uma nova senha do 0 e novo email" --
  // pede o e-mail (prompt pré-preenchido com o antigo, repetir é válido) e sempre gera senha
  // nova no servidor, mesmo padrão de cadastro (CriarUsuarioForm.tsx).
  async function reativarUsuario(userId: number, nome: string, emailAtual: string) {
    const novoEmail = window.prompt(
      `Reativar "${nome}" -- confirme o e-mail de login (pode repetir o mesmo ou trocar):`,
      emailAtual,
    )
    if (novoEmail === null) return // cancelou o prompt
    const emailLimpo = novoEmail.trim()
    if (!emailLimpo) {
      setError('E-mail não pode ficar vazio.')
      return
    }
    setReativandoId(userId)
    setError(null)
    setSenhaReativacao(null)
    try {
      const resp = await api.post<AdminUserCreateResponse>(`/users/${userId}/reativar`, { email: emailLimpo })
      setUsers((atual) => atual?.map((u) => (u.id === userId ? resp.data : u)) ?? null)
      const gerada = { nome: resp.data.nome, senha: resp.data.senha_temporaria_gerada, email: resp.data.email }
      setSenhaReativacao(gerada)
      setSenhaReativacaoCopiada(false)
      window.location.href = montarMailtoSenhaTemporaria(gerada)
    } catch (err) {
      setError(extrairErro(err, 'Não foi possível reativar esse usuário -- confira se o e-mail já não está em uso.'))
    } finally {
      setReativandoId(null)
    }
  }

  async function copiarSenhaReativacao(senha: string) {
    try {
      await navigator.clipboard.writeText(senha)
      setSenhaReativacaoCopiada(true)
      setTimeout(() => setSenhaReativacaoCopiada(false), 2000)
    } catch {
      // Fallback é a senha continuar selecionável na tela.
    }
  }

  function adicionarUsuarioCriado(novo: User) {
    // Mesmo padrão de atualização otimista local de alterarNivel acima -- evita um refetch de
    // GET /users só pra mostrar a linha nova, o admin já vê o usuário na tabela sem reload.
    // Recadastrar um e-mail já excluído (2026-07-17) REATIVA a mesma linha no servidor (mesmo
    // id, ver backend/api/users.py::create_user_by_admin) em vez de criar outra -- por isso
    // substitui em vez de sempre concatenar, senão duplicava a linha na tabela.
    setUsers((atual) => {
      if (!atual) return [novo]
      const jaExiste = atual.some((u) => u.id === novo.id)
      return jaExiste ? atual.map((u) => (u.id === novo.id ? novo : u)) : [...atual, novo]
    })
  }

  return (
    <Card id="gestao-usuarios" title="Gestão de usuários">
      <CriarUsuarioForm subgrupos={subgrupos} onCriado={adicionarUsuarioCriado} />

      {senhaReativacao && (
        // Mesmo padrão visual do callout de senha gerada em CriarUsuarioForm.tsx -- reativar
        // agora gera senha nova do zero (2026-07-17, pedido explícito), então precisa do
        // mesmo tratamento de "só aparece uma vez".
        <div className="mt-3 rounded-lg border border-amber-300 bg-amber-50 px-4 py-3 text-sm text-amber-900">
          <p className="font-medium">
            Nova senha temporária de {senhaReativacao.nome} ({senhaReativacao.email}):{' '}
            <span className="rounded bg-amber-100 px-1.5 py-0.5 font-mono">{senhaReativacao.senha}</span>
          </p>
          <p className="mt-1 text-xs">
            Essa senha só aparece agora -- anote e repasse pra {senhaReativacao.nome} antes de sair desta tela.
          </p>
          <div className="mt-2 flex flex-wrap gap-2">
            <button
              type="button"
              onClick={() => copiarSenhaReativacao(senhaReativacao.senha)}
              className="rounded-lg border border-amber-300 bg-white px-4 py-2 text-sm font-medium text-amber-900 transition-colors hover:bg-amber-100"
            >
              {senhaReativacaoCopiada ? 'Copiado!' : 'Copiar senha'}
            </button>
            <a
              href={montarMailtoSenhaTemporaria(senhaReativacao)}
              className="rounded-lg bg-brand-navy px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-brand-navy-dark"
            >
              Abrir e-mail
            </a>
          </div>
        </div>
      )}

      {error && <p className="mt-3 text-sm text-red-600">{error}</p>}
      {!users && !error && <p className="mt-3 text-sm text-ink-muted">Carregando...</p>}

      {users && (
        <>
          {/* Filtro Ativados/Desativados (2026-07-17, pedido explícito) -- usuário excluído
              (soft-delete, ativo=False) não some mais da resposta de GET /users, só desta
              aba. */}
          <div className="mt-4 flex gap-1 border-b border-line">
            {(
              [
                ['ativos', `Ativados (${users.filter((u) => u.ativo).length})`],
                ['inativos', `Desativados (${users.filter((u) => !u.ativo).length})`],
              ] as const
            ).map(([valor, rotulo]) => (
              <button
                key={valor}
                type="button"
                onClick={() => setFiltro(valor)}
                className={`-mb-px border-b-2 px-3 py-2 text-sm font-medium transition-colors ${
                  filtro === valor
                    ? 'border-brand-navy text-ink'
                    : 'border-transparent text-ink-muted hover:text-ink'
                }`}
              >
                {rotulo}
              </button>
            ))}
          </div>

          <div className="overflow-x-auto rounded-b border border-t-0 border-line">
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
              {users.filter((u) => (filtro === 'ativos' ? u.ativo : !u.ativo)).map((u) => {
                const souEu = u.id === currentUser?.id
                // Admin (99) nunca pode ser rebaixado/excluído por ninguém, nem por outro
                // admin (2026-07-16) -- EXCETO o super-admin oculto (2026-07-17,
                // backend/auth/deps.py::eh_super_admin), que só existe no servidor, sem
                // nenhum sinal disso aqui. Por isso o front NÃO desabilita o controle pra
                // "quando o alvo é admin" -- só pra "sou eu mesmo" (essa checagem vale pra
                // todo mundo, inclusive o super-admin) e enquanto salva. Quem não tem o
                // privilégio simplesmente recebe o 400 do servidor normalmente.
                const desabilitado = souEu || salvandoId === u.id
                const titulo = souEu ? 'Você não pode alterar o próprio nível' : undefined
                // Linha de usuário desativado (2026-07-17, NOVO) -- só leitura, sem os
                // controles de edição (não faz sentido reatribuir subgrupo/setor/nível de
                // uma conta que não consegue nem logar); a única ação disponível é reativar.
                if (!u.ativo) {
                  return (
                    <tr key={u.id} className="opacity-60">
                      <td className="whitespace-nowrap px-3 py-2 text-ink">{u.nome}</td>
                      <td className="whitespace-nowrap px-3 py-2 text-ink-muted">{u.email}</td>
                      <td className="px-3 py-2 text-sm text-ink-faint">
                        {subgrupos.filter((s) => u.subgrupo_ids.includes(s.id)).map((s) => s.nome).join(', ') || '—'}
                      </td>
                      <td className="px-3 py-2 text-sm text-ink-faint">{u.setor}</td>
                      <td className="px-3 py-2 text-sm text-ink-faint">{u.permission_level}</td>
                      <td className="whitespace-nowrap px-3 py-2 text-right">
                        <button
                          type="button"
                          onClick={() => reativarUsuario(u.id, u.nome, u.email)}
                          disabled={reativandoId === u.id}
                          className="rounded px-2 py-1 text-xs font-medium text-brand-navy hover:bg-surface-alt disabled:cursor-not-allowed disabled:opacity-50"
                        >
                          Reativar
                        </button>
                      </td>
                    </tr>
                  )
                }
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
                        {/* Só o número no UI (2026-07-17, pedido explícito) -- mesmo padrão
                            de CriarUsuarioForm.tsx. */}
                        <option value={99}>99</option>
                        <option value={88}>88</option>
                        <option value={77}>77</option>
                        <option value={66}>66</option>
                      </select>
                    </td>
                    <td className="whitespace-nowrap px-3 py-2 text-right">
                      {/* Só desabilita "sou eu mesmo" -- ver comentário sobre o super-admin
                          oculto acima do <select> de Nível. Quem tenta excluir um admin sem
                          o privilégio recebe o 400 do servidor normalmente. */}
                      <button
                        type="button"
                        onClick={() => excluirUsuario(u.id, u.nome)}
                        disabled={souEu || excluindoId === u.id}
                        title={souEu ? 'Você não pode excluir a si mesmo' : 'Excluir usuário'}
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
        </>
      )}
    </Card>
  )
}
