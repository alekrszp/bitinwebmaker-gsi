import { useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import AgenteConexaoToast from '../components/bitin/AgenteConexaoToast'
import PreenchimentoCodigos from '../components/bitin/PreenchimentoCodigos'
import PreenchimentoListaTecnica from '../components/bitin/PreenchimentoListaTecnica'
import { useAgenteSapConectado } from '../hooks/useAgenteSapConectado'
import { useFaviconAgente } from '../hooks/useFaviconAgente'

type SubAba = 'codigos' | 'lista-tecnica'

// Aba "Preenchimento" (2026-07-23) -- só existe no modo manual (sem agente conectado), no
// lugar simétrico da aba "Automação" (que só existe com o agente). Reúne o preenchimento em
// massa que antes vivia em 2 páginas próprias (ZBPP009/"CodigosSapPage" e "ListaTecnicaPage",
// removidas quando as 3 telas viraram uma só) como 2 sub-abas de UMA aba só, sem reviver rotas
// próprias -- pedido explícito do usuário: "criar uma aba igual tem com o agente automação,
// criar para sem o agente, preenchimento... nessa tela vai ter esse preenchimento em massa de
// campos, tanto pra códigos de alteração de dados ou lista técnica".
//
// Cada sub-aba é dona do próprio carregamento/salvamento (POST /bitins/draft, igual às antigas
// páginas) -- trocar de sub-aba desmonta a anterior e remonta a outra já com dado fresco do
// servidor, evitando o risco de duas cópias locais divergentes do mesmo materiais[] (a Lista
// Técnica e os Códigos de alteração escrevem no MESMO array, só que a partir de duas
// representações locais diferentes -- se ficassem montadas ao mesmo tempo sem se falar, salvar
// uma podia sobrescrever silenciosamente uma edição pendente da outra). Por isso a troca de
// sub-aba avisa (confirm simples, mesmo padrão já usado em "Limpar tudo"/Enviar) se a sub-aba
// atual tem alteração não salva, em vez de reaproveitar o AvisoSairModal (pensado pra navegação
// de rota, não troca de aba dentro da mesma página).
export default function PreenchimentoPage() {
  const { mongoId } = useParams<{ mongoId: string }>()
  const navigate = useNavigate()
  const { conectado: agenteConectado, verificado } = useAgenteSapConectado()
  const [subAba, setSubAba] = useState<SubAba>('codigos')
  const [sujoAtivo, setSujoAtivo] = useState(false)
  useFaviconAgente(verificado ? (agenteConectado ? 'conectado' : 'desligado') : undefined)

  // Se o agente conectar enquanto o engenheiro está aqui, o preenchimento manual deixa de fazer
  // sentido -- redireciona pra Automação (mesma regra inversa do fallback em AutomacaoPage.tsx).
  // Só decide depois da 1ª checagem (`verificado`), senão redirecionaria sempre de cara.
  useEffect(() => {
    if (verificado && agenteConectado) navigate(`/bitins/${mongoId}/automacao`, { replace: true })
  }, [agenteConectado, verificado, mongoId, navigate])

  function trocarSubAba(destino: SubAba) {
    if (destino === subAba) return
    if (sujoAtivo && !window.confirm('Trocar de sub-aba sem salvar as alterações atuais?')) return
    setSubAba(destino)
    setSujoAtivo(false)
  }

  function voltarProBitin() {
    if (sujoAtivo && !window.confirm('Sair sem salvar as alterações desta seção?')) return
    navigate(`/bitins/${mongoId}`)
  }

  return (
    <div className="mx-auto max-w-[1600px] pb-24">
      <button
        type="button"
        onClick={voltarProBitin}
        className="text-sm text-ink-muted hover:text-ink hover:underline"
      >
        ← Voltar pro BITin
      </button>

      <div className="mt-3 flex flex-wrap items-center gap-3">
        <h1 className="text-2xl font-semibold text-ink">Preenchimento</h1>
      </div>

      <div className="mt-4 inline-flex rounded-lg border border-line bg-surface-alt p-1">
        <button
          type="button"
          onClick={() => trocarSubAba('codigos')}
          className={`rounded-md px-4 py-1.5 text-sm font-medium transition-colors ${
            subAba === 'codigos' ? 'bg-surface text-ink shadow-sm' : 'text-ink-muted hover:text-ink'
          }`}
        >
          Códigos de alteração
        </button>
        <button
          type="button"
          onClick={() => trocarSubAba('lista-tecnica')}
          className={`rounded-md px-4 py-1.5 text-sm font-medium transition-colors ${
            subAba === 'lista-tecnica' ? 'bg-surface text-ink shadow-sm' : 'text-ink-muted hover:text-ink'
          }`}
        >
          Lista Técnica
        </button>
      </div>

      {/* `key` força remontagem completa ao trocar de sub-aba -- sempre busca o materiais[]
          mais recente do servidor em vez de reaproveitar estado antigo (ver comentário acima). */}
      {subAba === 'codigos' ? (
        <PreenchimentoCodigos key="codigos" agenteConectado={agenteConectado} onSujoChange={setSujoAtivo} />
      ) : (
        <PreenchimentoListaTecnica key="lista-tecnica" agenteConectado={agenteConectado} onSujoChange={setSujoAtivo} />
      )}
      <AgenteConexaoToast conectado={agenteConectado} verificado={verificado} />
    </div>
  )
}
