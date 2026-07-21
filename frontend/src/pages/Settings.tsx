import { useEffect, useState } from 'react'
import Card from '../components/Card'
import DetailField from '../components/DetailField'
import AjudaPopover from '../components/bitin/AjudaPopover'
import BitinTableSection from '../components/bitin/BitinTableSection'
import { COLUNAS_PADRAO_BITIN } from '../components/bitin/bitinColunas'
import TrocarSenhaForm from '../components/settings/TrocarSenhaForm'
import { useAuth } from '../hooks/useAuth'
import { api } from '../lib/api'
import { isAdmin } from '../lib/permissions'
import type { Bitin, Subgrupo } from '../lib/types'

// Gestão de usuários/Criar usuário saíram daqui (2026-07-16, pedido explícito: "desvinculadas
// da parte de configurações, páginas juntas") -- ver GestaoUsuariosPage.tsx / rota /usuarios.
// Configurações agora tem "Minha conta" (qualquer nível) + "Bitins Concluídos" (só admin,
// 2026-07-21, pedido explícito: "aba de bitins concluidos ainda junto de cadastro remove de
// lá e faz isso numa aba lá em configurações só do admin... lista dos bitins concluidos com
// opções de voltar bitin etc.").
type Aba = 'conta' | 'concluidos'

export default function Settings() {
  const { user } = useAuth()
  const admin = isAdmin(user?.permission_level)
  const [aba, setAba] = useState<Aba>('conta')
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

      {admin && (
        <div className="mt-6 flex gap-1 border-b border-line">
          <button
            type="button"
            onClick={() => setAba('conta')}
            className={`rounded-t-lg px-4 py-2 text-sm font-medium ${
              aba === 'conta' ? 'border-b-2 border-brand-navy text-brand-navy' : 'text-ink-muted hover:text-ink'
            }`}
          >
            Minha conta
          </button>
          <button
            type="button"
            onClick={() => setAba('concluidos')}
            className={`rounded-t-lg px-4 py-2 text-sm font-medium ${
              aba === 'concluidos' ? 'border-b-2 border-brand-navy text-brand-navy' : 'text-ink-muted hover:text-ink'
            }`}
          >
            Bitins Concluídos
          </button>
        </div>
      )}

      {aba === 'conta' && (
        <Card title="Minha conta">
          <dl className="mt-4 grid grid-cols-1 gap-4 sm:grid-cols-2">
            <DetailField label="Nome" value={user?.nome} />
            <DetailField label="E-mail" value={user?.email} />
            <DetailField label="Subgrupo" value={subgruposNomes || 'Sem subgrupo'} />
          </dl>

          <TrocarSenhaForm />
        </Card>
      )}

      {admin && aba === 'concluidos' && <BitinsConcluidosTab />}
    </div>
  )
}

// Lista dos BITins com Status=Concluído (windchill_enviado=True) -- pasta trancada que saiu
// de CadastroPage.tsx/Sidebar.tsx (2026-07-21). Só admin chega aqui, e só admin pode
// "Voltar" (POST /{id}/reverter-windchill, backend/api/bitins.py, check_permission(NIVEL_ADMIN)).
function BitinsConcluidosTab() {
  const [bitins, setBitins] = useState<Bitin[] | null>(null)
  const [erro, setErro] = useState<string | null>(null)
  const [revertendoId, setRevertendoId] = useState<string | null>(null)

  function carregar() {
    setBitins(null)
    setErro(null)
    api
      .get('/bitins', { params: { status: 'enviado', windchill_enviado: true } })
      .then((resp) => setBitins(resp.data))
      .catch(() => setErro('Não foi possível carregar os BITins concluídos.'))
  }

  useEffect(() => {
    carregar()
  }, [])

  async function voltarBitin(bitin: Bitin) {
    const confirmado = window.confirm(
      `Voltar o BITin ${bitin.codigo ?? '—'}? Ele sai de "Concluído" e volta pra "Pendência de envio" no Cadastro.`,
    )
    if (!confirmado) return
    setErro(null)
    setRevertendoId(bitin.mongo_id)
    try {
      await api.post(`/bitins/${bitin.mongo_id}/reverter-windchill`)
      setBitins((atual) => atual?.filter((b) => b.mongo_id !== bitin.mongo_id) ?? null)
    } catch {
      setErro('Não foi possível voltar o BITin. Tente novamente.')
    } finally {
      setRevertendoId(null)
    }
  }

  function acoesLinha(b: Bitin) {
    return (
      <button
        type="button"
        onClick={() => voltarBitin(b)}
        disabled={revertendoId === b.mongo_id}
        className="whitespace-nowrap rounded-lg border border-line px-3 py-1.5 text-xs font-medium text-ink hover:bg-surface-alt disabled:cursor-not-allowed disabled:opacity-60"
      >
        {revertendoId === b.mongo_id ? 'Voltando...' : 'Voltar bitin'}
      </button>
    )
  }

  return (
    <Card
      title={
        <div className="flex items-center gap-2">
          Lista dos bitins concluídos
          <AjudaPopover titulo="Sobre esta lista">
            <p>
              BITin cai aqui quando o Cadastro baixa o PDF final e marca como concluído
              (Status="Concluído", último passo do fluxo, ver Windchill). É uma pasta trancada,
              por isso ela vive só aqui, não mais em Cadastro.
            </p>
            <p>
              <strong>"Voltar bitin"</strong> desfaz esse último passo -- ele volta pra
              "Pendência de envio" na fila do Cadastro, pra baixar o PDF de novo se precisar
              (ex.: erro no envio ao Windchill).
            </p>
          </AjudaPopover>
        </div>
      }
    >
      <BitinTableSection
        bitins={bitins}
        erro={erro}
        colunas={COLUNAS_PADRAO_BITIN}
        acoes={acoesLinha}
        mensagemVazia="Nenhum BITin concluído."
      />
    </Card>
  )
}
