import { useEffect, useState } from 'react'
import Card from '../components/Card'
import DetailField from '../components/DetailField'
import GestaoUsuarios from '../components/settings/GestaoUsuarios'
import TrocarSenhaForm from '../components/settings/TrocarSenhaForm'
import { useAuth } from '../hooks/useAuth'
import { api } from '../lib/api'
import type { Sector } from '../lib/types'

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

  // "Minha conta" -- vários setores possíveis agora (2026-07-15, era sector_id único): junta
  // os nomes com vírgula, mesma convenção usada na tabela de GestaoUsuarios abaixo.
  const setoresNomes = (user?.sector_ids ?? [])
    .map((id) => sectors.find((s) => s.id === id)?.nome ?? `#${id}`)
    .join(', ')

  return (
    <div className="mx-auto max-w-6xl">
      <h1 className="text-2xl font-semibold text-ink">Configurações</h1>

      <Card title="Minha conta">
        <dl className="mt-4 grid grid-cols-1 gap-4 sm:grid-cols-2">
          <DetailField label="Nome" value={user?.nome} />
          <DetailField label="E-mail" value={user?.email} />
          <DetailField label="Setor" value={setoresNomes || 'Sem setor'} />
        </dl>

        <TrocarSenhaForm />
      </Card>

      {user && user.permission_level >= ADMIN_LEVEL && <GestaoUsuarios sectors={sectors} />}
    </div>
  )
}
