import { useEffect, useState } from 'react'
import Card from '../components/Card'
import DetailField from '../components/DetailField'
import TrocarSenhaForm from '../components/settings/TrocarSenhaForm'
import { useAuth } from '../hooks/useAuth'
import { api } from '../lib/api'
import type { Subgrupo } from '../lib/types'

// Gestão de usuários/Criar usuário saíram daqui (2026-07-16, pedido explícito: "desvinculadas
// da parte de configurações, páginas juntas") -- ver GestaoUsuariosPage.tsx / rota /usuarios.
// Configurações agora é só "Minha conta", pra qualquer nível de permissão.
export default function Settings() {
  const { user } = useAuth()
  const [subgrupos, setSubgrupos] = useState<Subgrupo[]>([])

  useEffect(() => {
    api
      .get('/subgrupos')
      .then((resp) => setSubgrupos(resp.data))
      .catch(() => {}) // "Minha conta" ainda funciona sem o nome do subgrupo -- só cai pro id
  }, [])

  // "Minha conta" -- vários subgrupos possíveis agora (2026-07-15, era sector_id único): junta
  // os nomes com vírgula.
  const subgruposNomes = (user?.subgrupo_ids ?? [])
    .map((id) => subgrupos.find((s) => s.id === id)?.nome ?? `#${id}`)
    .join(', ')

  return (
    <div className="mx-auto max-w-6xl">
      <h1 className="text-2xl font-semibold text-ink">Configurações</h1>

      <Card title="Minha conta">
        <dl className="mt-4 grid grid-cols-1 gap-4 sm:grid-cols-2">
          <DetailField label="Nome" value={user?.nome} />
          <DetailField label="E-mail" value={user?.email} />
          <DetailField label="Subgrupo" value={subgruposNomes || 'Sem subgrupo'} />
        </dl>

        <TrocarSenhaForm />
      </Card>
    </div>
  )
}
