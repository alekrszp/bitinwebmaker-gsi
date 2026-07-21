import { useState, type FormEvent } from 'react'
import FormLabel from '../FormLabel'
import TextInput from '../TextInput'
import { api } from '../../lib/api'
import { extrairErro } from '../../lib/errors'
import { montarMailtoSenhaTemporaria } from '../../lib/senhaTemporaria'
import type { AdminUserCreateRequest, AdminUserCreateResponse, Subgrupo, User } from '../../lib/types'

// Cadastro de usuário SÓ POR ADMIN (2026-07-15, pedido explícito: "tela de cadastro de usuário
// SÓ PARA ADMIN para não ter que cadastrar no banco"). POST /users (backend/api/users.py::
// create_user_by_admin, check_permission(99)) gera a senha temporária no servidor -- essa tela
// não tem campo de senha nenhum, só mostra a gerada UMA VEZ na resposta pro admin repassar
// fora do sistema (chat, verbalmente) antes do dono da conta trocar por conta própria no
// primeiro login (RequireAuth.tsx -> /definir-senha, ver Usuario.senha_temporaria).
export default function CriarUsuarioForm({ subgrupos, onCriado }: { subgrupos: Subgrupo[]; onCriado: (u: User) => void }) {
  const [email, setEmail] = useState('')
  const [nome, setNome] = useState('')
  const [numeroEng, setNumeroEng] = useState('')
  // Vários subgrupos marcáveis (2026-07-15, era um <select> de escolha única -- "um usuário
  // poder ser tanto armazenagem tanto quanto proteina").
  const [subgrupoIds, setSubgrupoIds] = useState<number[]>([])
  const [permissionLevel, setPermissionLevel] = useState(77)
  // Domínio de trabalho (2026-07-20, 2ª revisão do modelo de permissões) -- agora CONTROLA
  // acesso de verdade, cruzado com Permissão (ver backend/auth/deps.py::eh_do_setor).
  const [setor, setSetor] = useState('engenharia')
  // Reconfirmação de senha do PRÓPRIO admin (2026-07-16, pedido explícito: reconfirmar
  // identidade antes de criar conta) -- nunca a senha do usuário novo, essa continua sendo
  // gerada no servidor (ver comentário acima). Enviada como senha_admin, verificada em
  // backend/api/users.py::create_user_by_admin contra o hash de quem está logado.
  const [senhaAdmin, setSenhaAdmin] = useState('')
  const [erro, setErro] = useState<string | null>(null)
  const [enviando, setEnviando] = useState(false)
  const [senhaGerada, setSenhaGerada] = useState<{ nome: string; senha: string; email: string } | null>(null)
  // Feedback do botão "Copiar" (2026-07-17, NOVO) -- Clipboard API em vez de selecionar o
  // texto na mão, pra evitar arrastar espaço/quebra de linha na seleção (foi exatamente isso
  // que quebrou um login recente: copiar/colar manual do popup ou do corpo do e-mail).
  const [senhaCopiada, setSenhaCopiada] = useState(false)

  async function copiarSenha(senha: string) {
    try {
      await navigator.clipboard.writeText(senha)
      setSenhaCopiada(true)
      setTimeout(() => setSenhaCopiada(false), 2000)
    } catch {
      // Clipboard API pode falhar por permissão do navegador -- não é crítico, a senha
      // continua selecionável na tela como fallback.
    }
  }

  // Espelha backend/auth/schemas.py::exige_subgrupo (2026-07-20, 2ª revisão do modelo de
  // permissões) -- só Engenharia exige subgrupo, Admin nunca exige. Checagem no cliente é só
  // UX (evita um round-trip pra descobrir o 400); o backend continua garantindo a regra.
  const exigeSubgrupo = setor === 'engenharia' && permissionLevel !== 99

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setErro(null)
    if (exigeSubgrupo && subgrupoIds.length === 0) {
      setErro('Selecione ao menos um subgrupo para este nível de permissão.')
      return
    }
    setEnviando(true)
    try {
      const body: AdminUserCreateRequest = {
        email: email.trim(),
        nome,
        numero_eng: numeroEng.trim() || null,
        subgrupo_ids: subgrupoIds,
        permission_level: permissionLevel,
        setor,
        // trim() (2026-07-17, mesmo motivo de Login.tsx/usePasswordChangeForm.ts) -- é a
        // própria senha do admin, mas copiar/colar de um gerenciador de senha também pode
        // arrastar espaço extra.
        senha_admin: senhaAdmin.trim(),
      }
      const resp = await api.post<AdminUserCreateResponse>('/users', body)
      onCriado(resp.data)
      const gerada = { nome: resp.data.nome, senha: resp.data.senha_temporaria_gerada, email }
      setSenhaGerada(gerada)
      setSenhaCopiada(false)
      // Abre o rascunho de e-mail automaticamente ao criar a conta (2026-07-16, pedido
      // explícito: "marcamos uma opção e abre o email", igual a automação em Excel que já
      // existia -- não deveria exigir um clique extra do admin). O botão "Abrir e-mail" abaixo
      // continua existindo como reforço, caso o navegador bloqueie a navegação automática pra
      // mailto: ou o admin feche a aba sem querer.
      window.location.href = montarMailtoSenhaTemporaria(gerada)
      setEmail('')
      setNome('')
      setNumeroEng('')
      setSubgrupoIds([])
      setPermissionLevel(77)
      setSetor('engenharia')
      setSenhaAdmin('')
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
            Senha temporária de {senhaGerada.nome}:{' '}
            <span className="rounded bg-amber-100 px-1.5 py-0.5 font-mono">{senhaGerada.senha}</span>
          </p>
          <p className="mt-1 text-xs">
            Essa senha só aparece agora -- anote e repasse pra {senhaGerada.nome} antes de sair desta tela. No
            primeiro login ela vai ser obrigada a trocar por uma senha só dela.
          </p>
          <div className="mt-2 flex flex-wrap gap-2">
            {/* Copiar via Clipboard API (2026-07-17, NOVO) -- pedido explícito: "essa senha vai
                no corpo do email e pra mim copiar ali também". Evita selecionar o texto na mão,
                que foi o que causou um login falhando por arrastar espaço/quebra de linha extra
                na seleção. */}
            <button
              type="button"
              onClick={() => copiarSenha(senhaGerada.senha)}
              className="rounded-lg border border-amber-300 bg-white px-4 py-2 text-sm font-medium text-amber-900 transition-colors hover:bg-amber-100"
            >
              {senhaCopiada ? 'Copiado!' : 'Copiar senha'}
            </button>
            {/* Botão "Abrir e-mail" -- reforço caso a abertura automática (ver handleSubmit) tenha
                sido bloqueada pelo navegador ou o admin tenha fechado o cliente de e-mail sem
                querer; mailto: em vez de enviar de fato (não há servidor de e-mail integrado). */}
            <a
              href={montarMailtoSenhaTemporaria(senhaGerada)}
              className="rounded-lg bg-brand-navy px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-brand-navy-dark"
            >
              Abrir e-mail
            </a>
          </div>
        </div>
      )}

      <form onSubmit={handleSubmit} className="mt-3 grid grid-cols-1 gap-3 sm:grid-cols-2">
        <div>
          <FormLabel htmlFor="novo-email">E-mail</FormLabel>
          <TextInput
            id="novo-email"
            type="email"
            required
            autoComplete="off"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
          />
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
              pode pertencer a mais de um subgrupo ao mesmo tempo. Não hardcoda os 2 subgrupos
              conhecidos hoje: itera `subgrupos`, continua correto se um 3º for cadastrado. */}
          <span className="mb-1.5 block text-xs uppercase tracking-wide text-ink-muted">
            Subgrupo {exigeSubgrupo ? '(obrigatório, pode marcar mais de um)' : '(opcional, pode marcar mais de um)'}
          </span>
          <div className="flex flex-wrap gap-x-4 gap-y-1.5 rounded-lg border border-line bg-surface px-3 py-2">
            {subgrupos.length === 0 && <span className="text-sm text-ink-faint">Nenhum subgrupo cadastrado</span>}
            {subgrupos.map((s) => (
              <label key={s.id} className="flex items-center gap-1.5 text-sm text-ink">
                <input
                  type="checkbox"
                  checked={subgrupoIds.includes(s.id)}
                  onChange={(e) =>
                    setSubgrupoIds((atual) =>
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
            {/* Permissão É o número (permission_level) -- só o número no UI (2026-07-17,
                pedido explícito), sem rótulo textual ao lado. 2ª revisão do modelo de
                permissões (2026-07-20): só 77 (individual), 88 (Gestor) e 99 (Admin) --
                Cadastro/Processos deixaram de ser níveis próprios, viraram Setor (ver
                dropdown abaixo). */}
            <option value={99}>99</option>
            <option value={88}>88</option>
            <option value={77}>77</option>
          </select>
        </div>
        <div>
          {/* Domínio de trabalho (2026-07-20) -- agora CONTROLA acesso de verdade, cruzado
              com Permissão acima (ver backend/auth/deps.py::eh_do_setor/check_setor). */}
          <FormLabel htmlFor="novo-setor">Setor</FormLabel>
          <select
            id="novo-setor"
            value={setor}
            required
            onChange={(e) => setSetor(e.target.value)}
            className="w-full rounded-lg border border-line bg-surface px-3 py-2 text-sm text-ink focus:border-brand-navy focus:outline-none focus:ring-2 focus:ring-brand-navy/20"
          >
            <option value="cadastro">Cadastro</option>
            <option value="processos">Processos</option>
            <option value="engenharia">Engenharia</option>
          </select>
        </div>
        <div>
          {/* Reconfirmação de senha do PRÓPRIO admin (2026-07-16, pedido explícito) --
              não é a senha do usuário novo (essa continua sendo gerada no servidor, ver
              callout acima); é a senha ATUAL de quem está logado, checada em
              backend/api/users.py::create_user_by_admin antes de criar a conta.
              `autoComplete="new-password"` (2026-07-17, pedido explícito: "quero campos
              preenchidos sozinhos só os de login") -- "off" sozinho não bastava, Chrome
              ignora esse valor pra campos de senha e continuava preenchendo com a credencial
              salva. "new-password" sinaliza "não é um formulário de login", o que também tira
              o campo de E-mail acima da mira (Chrome só tenta parear e-mail+senha como
              usuário/senha quando reconhece o par como login). Diferente da tentativa anterior
              (campo `username` oculto decoy) -- essa não deixa nenhum elemento extra na
              página, então não tem o efeito colateral de disparar "Salvar senha?" em ações
              não relacionadas. */}
          <FormLabel htmlFor="novo-senha-admin">Sua senha (confirmação)</FormLabel>
          <TextInput
            id="novo-senha-admin"
            type="password"
            required
            autoComplete="new-password"
            value={senhaAdmin}
            onChange={(e) => setSenhaAdmin(e.target.value)}
          />
        </div>

        {erro && <p className="sm:col-span-2 text-sm text-red-600">{erro}</p>}

        <div className="sm:col-span-2">
          <button
            type="submit"
            disabled={enviando || !email || !nome || !senhaAdmin || (exigeSubgrupo && subgrupoIds.length === 0)}
            className="rounded-lg bg-brand-navy px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-brand-navy-dark disabled:cursor-not-allowed disabled:opacity-60"
          >
            {enviando ? 'Cadastrando...' : 'Cadastrar usuário'}
          </button>
        </div>
      </form>
    </div>
  )
}
