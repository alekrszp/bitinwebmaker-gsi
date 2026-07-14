import { useAuth } from '../context/AuthContext'

// Primeira página de verdade da área autenticada (era um placeholder só com "Login
// funcionando."). Segue o mesmo padrão visual da tela de login -- título grande + subtítulo
// discreto + faixa de 3 cores como assinatura -- em vez de inventar uma linguagem nova aqui.
export default function Home() {
  const { user } = useAuth()
  const primeiroNome = user?.nome?.split(' ')[0]

  return (
    <div className="flex min-h-[70vh] flex-col items-center justify-center text-center">
      <h1 className="text-2xl font-semibold text-ink text-balance sm:text-3xl">
        {primeiroNome ? `Bem-vindo, ${primeiroNome}` : 'Bem-vindo'}
      </h1>
      <p className="mt-2 max-w-sm text-sm text-ink-muted">
        A parte de Bitins (listagem e cadastro) está sendo reconstruída — em breve aparece aqui.
      </p>
      <div className="mt-6 flex gap-1.5">
        <span className="h-1.5 w-8 rounded-full bg-brand-gold" />
        <span className="h-1.5 w-8 rounded-full bg-brand-green" />
        <span className="h-1.5 w-8 rounded-full bg-brand-orange" />
      </div>
    </div>
  )
}
