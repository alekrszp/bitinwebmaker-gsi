import { useEffect, useState } from 'react'
import { useAuth } from '../context/AuthContext'
import { api } from '../lib/api'
import type { ResumoUsuario } from '../lib/types'

// Primeira página de verdade da área autenticada (era um placeholder só com "Login
// funcionando."). Segue o mesmo padrão visual da tela de login -- título grande + subtítulo
// discreto + faixa de 3 cores como assinatura -- em vez de inventar uma linguagem nova aqui.
//
// Cartões de resumo (2026-07-14): "simples mas útil" -- decisão registrada com o usuário de
// mostrar só os números do próprio usuário (rascunhos/enviados), sem lista de recentes nem
// botão de ação rápida ainda, porque a tela de cadastro/detalhe de BITin não existe (um link
// pra lugar nenhum seria pior que não ter). Ver docs/FRONTEND.md.
export default function Home() {
  const { user } = useAuth()
  const primeiroNome = user?.nome?.split(' ')[0]
  const [resumo, setResumo] = useState<ResumoUsuario | null>(null)

  useEffect(() => {
    let cancelado = false
    api
      .get('/bitins/resumo-usuario')
      .then((resp) => {
        if (!cancelado) setResumo(resp.data)
      })
      .catch(() => {}) // falha silenciosa -- não é crítico o bastante pra mostrar erro numa tela de boas-vindas
    return () => {
      cancelado = true
    }
  }, [])

  return (
    <div className="flex min-h-[70vh] flex-col items-center justify-center text-center">
      <h1 className="text-2xl font-semibold text-ink text-balance sm:text-3xl">
        {primeiroNome ? `Bem-vindo, ${primeiroNome}` : 'Bem-vindo'}
      </h1>
      <p className="mt-2 max-w-sm text-sm text-ink-muted">
        A parte de Bitins (listagem e cadastro) está sendo reconstruída — em breve aparece aqui.
      </p>

      <div className="mt-8 flex gap-4">
        <StatCard label="Rascunhos" value={resumo?.rascunhos} />
        <StatCard label="Enviados" value={resumo?.enviados} />
      </div>

      <div className="mt-8 flex gap-1.5">
        <span className="h-1.5 w-8 rounded-full bg-brand-gold" />
        <span className="h-1.5 w-8 rounded-full bg-brand-green" />
        <span className="h-1.5 w-8 rounded-full bg-brand-orange" />
      </div>
    </div>
  )
}

function StatCard({ label, value }: { label: string; value: number | undefined }) {
  return (
    <div className="min-w-[120px] rounded-lg border border-line bg-surface px-6 py-4">
      <p className="text-3xl font-semibold text-ink">{value ?? '—'}</p>
      <p className="mt-1 text-xs font-medium uppercase tracking-wide text-ink-muted">{label}</p>
    </div>
  )
}
