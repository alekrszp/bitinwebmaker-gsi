import { useState, type FormEvent } from 'react'
import FormLabel from '../FormLabel'
import TextInput from '../TextInput'
import { api } from '../../lib/api'
import { extrairErro } from '../../lib/errors'
import type { AdminUserCreateRequest, AdminUserCreateResponse, Sector, User } from '../../lib/types'

// Cadastro de usuário SÓ POR ADMIN (2026-07-15, pedido explícito: "tela de cadastro de usuário
// SÓ PARA ADMIN para não ter que cadastrar no banco"). POST /users (backend/api/users.py::
// create_user_by_admin, check_permission(99)) gera a senha temporária no servidor -- essa tela
// não tem campo de senha nenhum, só mostra a gerada UMA VEZ na resposta pro admin repassar
// fora do sistema (chat, verbalmente) antes do dono da conta trocar por conta própria no
// primeiro login (RequireAuth.tsx -> /definir-senha, ver Usuario.senha_temporaria).
export default function CriarUsuarioForm({ sectors, onCriado }: { sectors: Sector[]; onCriado: (u: User) => void }) {
  const [email, setEmail] = useState('')
  const [nome, setNome] = useState('')
  const [numeroEng, setNumeroEng] = useState('')
  // Vários setores marcáveis (2026-07-15, era um <select> de escolha única -- "um usuário
  // poder ser tanto armazenagem tanto quanto proteina").
  const [sectorIds, setSectorIds] = useState<number[]>([])
  const [permissionLevel, setPermissionLevel] = useState(66)
  const [erro, setErro] = useState<string | null>(null)
  const [enviando, setEnviando] = useState(false)
  const [senhaGerada, setSenhaGerada] = useState<{ nome: string; senha: string } | null>(null)

  // Espelha backend/auth/schemas.py::NIVEIS_QUE_EXIGEM_SETOR (2026-07-16, revisão do modelo de
  // permissões) -- só Admin (99) pode ficar sem setor. Checagem no cliente é só UX (evita um
  // round-trip pra descobrir o 400); o backend continua sendo quem de fato garante a regra.
  const exigeSetor = permissionLevel !== 99

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setErro(null)
    if (exigeSetor && sectorIds.length === 0) {
      setErro('Selecione ao menos um setor para este nível de permissão.')
      return
    }
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
      setPermissionLevel(66)
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
          <FormLabel htmlFor="novo-email">E-mail</FormLabel>
          <TextInput id="novo-email" type="email" required value={email} onChange={(e) => setEmail(e.target.value)} />
        </div>
        <div>
          <FormLabel htmlFor="novo-nome">Nome</FormLabel>
          <TextInput id="novo-nome" type="text" required value={nome} onChange={(e) => setNome(e.target.value)} />
        </div>
        <div>
          <FormLabel htmlFor="novo-numero-eng">ID</FormLabel>
          <TextInput id="novo-numero-eng" type="text" value={numeroEng} onChange={(e) => setNumeroEng(e.target.value)} />
        </div>
        <div>
          {/* Checkbox group em vez de <select> de escolha única (2026-07-15) -- um usuário
              pode pertencer a mais de um setor ao mesmo tempo. Não hardcoda os 2 setores
              conhecidos hoje: itera `sectors`, continua correto se um 3º for cadastrado. */}
          <span className="mb-1.5 block text-xs uppercase tracking-wide text-ink-muted">
            Setor {exigeSetor ? '(obrigatório, pode marcar mais de um)' : '(opcional, pode marcar mais de um)'}
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
          <FormLabel htmlFor="novo-permissao">Permissão</FormLabel>
          <select
            id="novo-permissao"
            value={permissionLevel}
            onChange={(e) => setPermissionLevel(Number(e.target.value))}
            className="w-full rounded-lg border border-line bg-surface px-3 py-2 text-sm text-ink focus:border-brand-navy focus:outline-none focus:ring-2 focus:ring-brand-navy/20"
          >
            <option value={66}>Usuário</option>
            <option value={77}>Gestor</option>
            <option value={88}>Cadastro</option>
            <option value={99}>Admin</option>
          </select>
        </div>

        {erro && <p className="sm:col-span-2 text-sm text-red-600">{erro}</p>}

        <div className="sm:col-span-2">
          <button
            type="submit"
            disabled={enviando || !email || !nome || (exigeSetor && sectorIds.length === 0)}
            className="rounded-lg bg-brand-navy px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-brand-navy-dark disabled:cursor-not-allowed disabled:opacity-60"
          >
            {enviando ? 'Cadastrando...' : 'Cadastrar usuário'}
          </button>
        </div>
      </form>
    </div>
  )
}
