import { Link } from 'react-router-dom'
import type { BitinColuna } from './bitinColunas'
import type { ReactNode } from 'react'
import type { Bitin } from '../../lib/types'

// Tabela de listagem de BITins, extraída da mesma estrutura repetida em CadastroPage.tsx,
// ProcessosPage.tsx, MeusBitins.tsx e Settings.tsx (aba "Bitins Concluídos") -- 2026-07-21,
// revisão de componentização ("componetize tudo que puder"). Cada página só declara as
// colunas que precisa (`colunas`, ver bitinColunas.tsx) e, se tiver ações por linha (botão
// "Concluir BITIN", "Baixar PDF", "Voltar bitin", "×" excluir...), passa `acoes`.
export default function BitinTableSection({
  bitins,
  erro,
  colunas,
  acoes,
  mensagemVazia = 'Nenhum BITin nesta visão.',
}: {
  bitins: Bitin[] | null
  erro: string | null
  colunas: BitinColuna[]
  /** Célula de ação à direita, por linha (botões de mudar de etapa, excluir, etc). */
  acoes?: (b: Bitin) => ReactNode
  mensagemVazia?: string
}) {
  return (
    <>
      {erro && <p className="mt-4 text-sm text-red-600">{erro}</p>}
      {!bitins && !erro && <p className="mt-4 text-sm text-ink-muted">Carregando...</p>}
      {bitins && bitins.length === 0 && !erro && <p className="mt-4 text-sm text-ink-muted">{mensagemVazia}</p>}

      {bitins && bitins.length > 0 && (
        <div className="mt-4 overflow-hidden rounded-lg border border-line">
          <table className="w-full text-left text-sm">
            <thead>
              <tr className="bg-surface-alt text-xs uppercase tracking-wide text-ink-muted">
                {colunas.map((c) => (
                  <th key={c.header} className="px-4 py-2 font-medium">
                    {c.header}
                  </th>
                ))}
                {acoes && <th className="w-44" />}
              </tr>
            </thead>
            <tbody className="divide-y divide-line bg-surface">
              {bitins.map((b) => (
                <tr key={b.mongo_id} className="hover:bg-surface-alt">
                  {colunas.map((c) => (
                    <td key={c.header} className={`px-4 py-2 ${c.className ?? ''}`}>
                      {c.link === false ? (
                        c.render(b)
                      ) : (
                        <Link to={`/bitins/${b.mongo_id}`} className="block">
                          {c.render(b)}
                        </Link>
                      )}
                    </td>
                  ))}
                  {acoes && <td className="px-4 py-2 text-right">{acoes(b)}</td>}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </>
  )
}
