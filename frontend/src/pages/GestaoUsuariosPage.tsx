import { useEffect, useState } from 'react'
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
      <h1 className="text-2xl font-semibold text-ink">Gestão de usuários</h1>
      <div className="mt-4">
        <GestaoUsuarios subgrupos={subgrupos} />
      </div>
    </div>
  )
}
