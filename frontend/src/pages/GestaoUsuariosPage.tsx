import { useEffect, useState } from 'react'
import AjudaPopover from '../components/bitin/AjudaPopover'
import GestaoUsuarios from '../components/settings/GestaoUsuarios'
import { useAuth } from '../hooks/useAuth'
import { api } from '../lib/api'
import { isAdmin } from '../lib/permissions'
import type { Subgrupo } from '../lib/types'

// Página própria (2026-07-16, pedido explícito: "gestão de usuários e criar usuário devem ser
// desvinculadas de Configurações, páginas juntas") -- antes vivia dentro de Settings.tsx com
// scroll-to-hash pros dois Cards; GestaoUsuarios já renderiza CriarUsuarioForm dentro de si
// mesma, então uma página nova é só o mesmo componente sem o resto de Configurações em volta.
export default function GestaoUsuariosPage() {
  const { user } = useAuth()
  const [subgrupos, setSubgrupos] = useState<Subgrupo[]>([])

  useEffect(() => {
    api
      .get('/subgrupos')
      .then((resp) => setSubgrupos(resp.data))
      .catch(() => {})
  }, [])

  if (!isAdmin(user?.permission_level)) {
    return (
      <div className="mx-auto max-w-6xl">
        <p className="text-sm text-ink-muted">Você não tem permissão para acessar esta página.</p>
      </div>
    )
  }

  return (
    <div className="mx-auto max-w-6xl">
      <div className="flex flex-wrap items-center gap-3">
        <h1 className="text-2xl font-semibold text-ink">Gestão de usuários</h1>
        <AjudaPopover titulo="Como funciona">
          <p>
            <strong>Nível</strong>: 77 Individual, 88 Gestor, 99 Admin. <strong>Setor</strong>:
            Cadastro, Processos ou Engenharia -- define em qual fila de trabalho a pessoa entra.
          </p>
          <p>Editar um usuário existente ou criar um novo usa o mesmo formulário, expandido na lista.</p>
        </AjudaPopover>
      </div>
      <div className="mt-4">
        <GestaoUsuarios subgrupos={subgrupos} />
      </div>
    </div>
  )
}
