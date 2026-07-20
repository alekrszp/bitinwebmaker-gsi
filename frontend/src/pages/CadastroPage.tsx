import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import StatusBadge from '../components/bitin/StatusBadge'
import { useAuth } from '../hooks/useAuth'
import { api } from '../lib/api'
import { isCadastro } from '../lib/permissions'
import type { Bitin } from '../lib/types'

// Fila de trabalho do setor Cadastro (2026-07-17) -- substitui de vez o e-mail/PDF manual
// que existia antes (Módulo12.bas na macro original, depois um botão "Enviar e-mail" nesta
// v1, removido a pedido do usuário: "sem essa opção de enviar email só enviar de volta pra
// cadastro"). Três abas -- "Recebidos" (recém-enviado, ainda sem decisão), "Enviados para
// roteiros" (encaminhado pro setor Processos, aguardando revisão) e "Retornados de roteiro"
// (estado final -- ou o Processos concluiu, ou o Cadastro decidiu que não precisava ir pra
// lá, ver `b.precisa_roteiro`/concluirSemRoteiro abaixo -- com PDF pra registro externo, "o
// pdf só vai existir no final onde ou voltou de processos ou o bitin não precisa ir pra
// processos"). Mesmo padrão de gating de MeusBitins.tsx/GestaoUsuariosPage.tsx (checagem de
// nível dentro do componente).
type Aba = 'para_cadastro' | 'enviado_roteiro' | 'pronto_cadastro'

const ABAS: { value: Aba; label: string }[] = [
  { value: 'para_cadastro', label: 'Recebidos' },
  { value: 'enviado_roteiro', label: 'Enviados para roteiros' },
  { value: 'pronto_cadastro', label: 'Retornados de roteiro' },
]

// GET /bitins?status=enviado&<filtro da aba> -- cada aba filtra por um campo diferente do
// mesmo par encaminhado_roteiro/processos_concluido (ver backend/api/bitins.py::list_bitins).
const FILTRO_POR_ABA: Record<Aba, Record<string, boolean>> = {
  para_cadastro: { encaminhado_roteiro: false },
  enviado_roteiro: { encaminhado_roteiro: true, processos_concluido: false },
  pronto_cadastro: { processos_concluido: true },
}

export default function CadastroPage() {
  const { user } = useAuth()
  const [aba, setAba] = useState<Aba>('para_cadastro')
  const [bitins, setBitins] = useState<Bitin[] | null>(null)
  const [erro, setErro] = useState<string | null>(null)
  const [encaminhandoId, setEncaminhandoId] = useState<string | null>(null)
  const [concluindoId, setConcluindoId] = useState<string | null>(null)
  const [baixandoId, setBaixandoId] = useState<string | null>(null)

  const podeAcessar = isCadastro(user?.permission_level)

  function carregar() {
    let cancelado = false
    setBitins(null)
    setErro(null)
    api
      .get('/bitins', { params: { status: 'enviado', ...FILTRO_POR_ABA[aba] } })
      .then((resp) => {
        if (!cancelado) setBitins(resp.data)
      })
      .catch(() => {
        if (!cancelado) setErro('Não foi possível carregar os BITins.')
      })
    return () => {
      cancelado = true
    }
  }

  useEffect(() => {
    if (!podeAcessar) return
    return carregar()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [aba, podeAcessar])

  async function encaminhar(bitin: Bitin) {
    setErro(null)
    setEncaminhandoId(bitin.mongo_id)
    try {
      await api.post(`/bitins/${bitin.mongo_id}/encaminhar-roteiro`)
      setBitins((atual) => atual?.filter((b) => b.mongo_id !== bitin.mongo_id) ?? null)
    } catch {
      setErro('Não foi possível encaminhar para o roteiro. Tente novamente.')
    } finally {
      setEncaminhandoId(null)
    }
  }

  // "Não precisa de roteiro" (2026-07-17, pedido explícito: "coloca essa opção, do cadastro
  // não precisar enviar pra processos, quando não houver: D/P, D/- ou -/P") -- alternativa a
  // "Encaminhar para roteiro", só aparece quando `!b.precisa_roteiro` (calculado no backend,
  // ver bitin_document.precisa_roteiro). Chega direto na aba "Retornados de roteiro" (mesmo
  // filtro processos_concluido=true de quem passou pelo Processos de verdade).
  async function concluirSemRoteiro(bitin: Bitin) {
    setErro(null)
    setConcluindoId(bitin.mongo_id)
    try {
      await api.post(`/bitins/${bitin.mongo_id}/concluir-sem-roteiro`)
      setBitins((atual) => atual?.filter((b) => b.mongo_id !== bitin.mongo_id) ?? null)
    } catch {
      setErro('Não foi possível concluir sem roteiro. Tente novamente.')
    } finally {
      setConcluindoId(null)
    }
  }

  // PDF sob demanda (GET /{id}/pdf já existente) -- não precisa de um snapshot guardado à
  // parte: o BITin fica travado
  // depois que o Processos conclui, então o conteúdo não muda mais (decisão do usuário,
  // 2026-07-17: "sob demanda é suficiente").
  async function baixarPdf(bitin: Bitin) {
    setErro(null)
    setBaixandoId(bitin.mongo_id)
    try {
      const resp = await api.get(`/bitins/${bitin.mongo_id}/pdf`, { responseType: 'blob' })
      const url = window.URL.createObjectURL(new Blob([resp.data]))
      const a = document.createElement('a')
      a.href = url
      a.download = `BITin-${bitin.codigo ?? bitin.mongo_id}.pdf`
      document.body.appendChild(a)
      a.click()
      a.remove()
      window.URL.revokeObjectURL(url)
    } catch {
      setErro('Não foi possível baixar o PDF. Tente novamente.')
    } finally {
      setBaixandoId(null)
    }
  }

  if (!podeAcessar) {
    return (
      <div className="mx-auto max-w-6xl">
        <p className="text-sm text-ink-muted">Você não tem permissão para acessar esta página.</p>
      </div>
    )
  }

  return (
    <div className="mx-auto max-w-6xl">
      <h1 className="text-2xl font-semibold text-ink">Cadastro</h1>

      <div className="mt-4 flex gap-1 border-b border-line">
        {ABAS.map(({ value, label }) => (
          <button
            key={value}
            type="button"
            onClick={() => setAba(value)}
            className={`-mb-px border-b-2 px-3 py-2 text-sm font-medium transition-colors ${
              aba === value
                ? 'border-brand-navy text-ink'
                : 'border-transparent text-ink-muted hover:text-ink'
            }`}
          >
            {label}
          </button>
        ))}
      </div>

      {erro && <p className="mt-4 text-sm text-red-600">{erro}</p>}
      {!bitins && !erro && <p className="mt-4 text-sm text-ink-muted">Carregando...</p>}
      {bitins && bitins.length === 0 && !erro && (
        <p className="mt-4 text-sm text-ink-muted">Nenhum BITin nesta fila.</p>
      )}

      {bitins && bitins.length > 0 && (
        <div className="mt-4 overflow-hidden rounded-lg border border-line">
          <table className="w-full text-left text-sm">
            <thead>
              <tr className="bg-surface-alt text-xs uppercase tracking-wide text-ink-muted">
                <th className="px-4 py-2 font-medium">Número</th>
                <th className="px-4 py-2 font-medium">Motivo</th>
                <th className="px-4 py-2 font-medium">Solicitante</th>
                <th className="px-4 py-2 font-medium">Status</th>
                <th className="w-44" />
              </tr>
            </thead>
            <tbody className="divide-y divide-line bg-surface">
              {bitins.map((b) => (
                <tr key={b.mongo_id} className="hover:bg-surface-alt">
                  <td className="px-4 py-2">
                    <Link to={`/bitins/${b.mongo_id}`} className="block text-ink hover:underline">
                      {b.codigo ?? '—'}
                    </Link>
                  </td>
                  <td className="px-4 py-2 text-ink-muted">
                    <Link to={`/bitins/${b.mongo_id}`} className="block">
                      {String(b.content?.motivo ?? '—')}
                    </Link>
                  </td>
                  <td className="px-4 py-2 text-ink-muted">
                    <Link to={`/bitins/${b.mongo_id}`} className="block">
                      {String(b.content?.solicitante ?? '—')}
                    </Link>
                  </td>
                  <td className="px-4 py-2">
                    <Link to={`/bitins/${b.mongo_id}`} className="block">
                      <StatusBadge status={b.status} />
                    </Link>
                  </td>
                  <td className="px-4 py-2 text-right">
                    {aba === 'para_cadastro' &&
                      (b.precisa_roteiro ? (
                        <button
                          type="button"
                          onClick={() => encaminhar(b)}
                          disabled={encaminhandoId === b.mongo_id}
                          className="whitespace-nowrap rounded-lg border border-line px-3 py-1.5 text-xs font-medium text-ink hover:bg-surface-alt disabled:cursor-not-allowed disabled:opacity-60"
                        >
                          {encaminhandoId === b.mongo_id ? 'Encaminhando...' : 'Encaminhar para roteiro'}
                        </button>
                      ) : (
                        <button
                          type="button"
                          onClick={() => concluirSemRoteiro(b)}
                          disabled={concluindoId === b.mongo_id}
                          className="whitespace-nowrap rounded-lg border border-line px-3 py-1.5 text-xs font-medium text-ink hover:bg-surface-alt disabled:cursor-not-allowed disabled:opacity-60"
                        >
                          {concluindoId === b.mongo_id ? 'Concluindo...' : 'Não precisa de roteiro'}
                        </button>
                      ))}
                    {aba === 'pronto_cadastro' && (
                      <button
                        type="button"
                        onClick={() => baixarPdf(b)}
                        disabled={baixandoId === b.mongo_id}
                        className="whitespace-nowrap rounded-lg border border-line px-3 py-1.5 text-xs font-medium text-ink hover:bg-surface-alt disabled:cursor-not-allowed disabled:opacity-60"
                      >
                        {baixandoId === b.mongo_id ? 'Baixando...' : 'Baixar PDF'}
                      </button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
