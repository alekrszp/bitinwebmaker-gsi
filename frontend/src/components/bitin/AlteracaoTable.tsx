import { Fragment } from 'react'
import Card from '../Card'

interface CampoAlterado {
  campo: string
  de: string
  para: string
  livre: boolean
}

interface ItemListaTecnica {
  codigo_filho: string
  quantidade_de: string
  quantidade_para: string
}

interface MaterialAlteracao {
  codigo_material: string
  descricao_material: string
  centro: string
  impactos_operacionais: Record<string, unknown>
  dados_basicos_alterados: CampoAlterado[]
  lista_tecnica: ItemListaTecnica[]
}

// Tabela única mesclada, igual ao documento original (examples/A263326.xlsm, aba "Template
// apresentação"): uma linha por material com código/descrição/indicadores (Alt/Est/Esp/LP/
// Pre/OC/OF), seguida por linhas aninhadas de "Alteração de Dados Básicos no Centro: X" e
// "Alteração de Lista Técnica no Centro: X" com De/Para -- não tabelas separadas.
//
// Campos livres (texto que o engenheiro escreveu fora do crosswalk SAP reconhecido, tipo
// "Salvar DWG") entram por último dentro do mesmo bloco "Alteração de Dados Básicos" -- linha
// normal (mesmo fundo das outras), texto corrido (campo + valor juntos, não separados em
// colunas De/Para), centralizado exatamente sob as colunas "De:"/"Para:" (não a linha toda) --
// é literalmente um campo de texto livre, sem caixa/borda própria (decisão do usuário,
// 2026-07-14). Só eles ficam vermelhos, não qualquer campo SAP reconhecido.
const COLUNAS_IMPACTO: { chave: string; label: string }[] = [
  { chave: 'alt', label: 'Alt' },
  { chave: 'est', label: 'Est' },
  { chave: 'esp', label: 'Esp' },
  { chave: 'lp', label: 'LP' },
  { chave: 'pre', label: 'Pre' },
  { chave: 'oc', label: 'OC' },
  { chave: 'of', label: 'OF' },
]

export default function AlteracaoTable({ materiais }: { materiais: MaterialAlteracao[] }) {
  return (
    <Card title="Alteração">
      <div className="mt-4 overflow-x-auto rounded border border-line">
        <table className="w-full text-left text-sm">
          <thead>
            <tr className="bg-surface-alt text-xs uppercase tracking-wide text-ink-muted">
              <th className="px-3 py-2 font-medium">Código</th>
              <th className="px-3 py-2 font-medium" colSpan={3}>
                Alteração
              </th>
              {COLUNAS_IMPACTO.map(({ chave, label }) => (
                <th key={chave} className="w-14 px-2 py-2 text-center font-medium">
                  {label}
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-line">
            {materiais.map((material) => {
              const camposSap = material.dados_basicos_alterados.filter((d) => !d.livre)
              const camposLivres = material.dados_basicos_alterados.filter((d) => d.livre)

              return (
                <Fragment key={material.codigo_material}>
                  <tr className="bg-surface-header">
                    <td className="whitespace-nowrap px-3 py-2 font-semibold text-ink">{material.codigo_material}</td>
                    <td className="px-3 py-2 font-semibold text-ink" colSpan={3}>
                      {material.descricao_material || '—'}
                    </td>
                    {COLUNAS_IMPACTO.map(({ chave }) => {
                      const valor = String(material.impactos_operacionais[chave] ?? '-')
                      const semImpacto = valor === '-' || valor === ''
                      return (
                        <td
                          key={chave}
                          className={`px-2 py-2 text-center ${semImpacto ? 'text-ink-faint' : 'font-medium text-ink'}`}
                        >
                          {valor}
                        </td>
                      )
                    })}
                  </tr>

                  {(camposSap.length > 0 || camposLivres.length > 0) && (
                    <>
                      <tr className="bg-surface-alt/60">
                        <td />
                        <td className="px-3 py-2 font-medium text-ink-muted">
                          Alteração de Dados Básicos no Centro: {material.centro || '—'}
                        </td>
                        <td className="px-3 py-2 text-center text-xs font-semibold uppercase text-ink-muted">De:</td>
                        <td className="px-3 py-2 text-center text-xs font-semibold uppercase text-ink-muted">
                          Para:
                        </td>
                        {COLUNAS_IMPACTO.map(({ chave }) => (
                          <td key={chave} />
                        ))}
                      </tr>
                      {camposSap.map((diff) => (
                        <tr key={diff.campo}>
                          <td />
                          <td className="px-3 py-2 text-ink">{diff.campo}</td>
                          <td className="px-3 py-2 text-center text-ink-muted">{diff.de || '—'}</td>
                          <td className="px-3 py-2 text-center text-ink-muted">{diff.para || '—'}</td>
                          {COLUNAS_IMPACTO.map(({ chave }) => (
                            <td key={chave} />
                          ))}
                        </tr>
                      ))}
                      {camposLivres.map((diff) => (
                        <tr key={diff.campo}>
                          <td />
                          <td />
                          <td className="px-3 py-2 text-center font-medium text-livre-text" colSpan={2}>
                            {diff.para ? `${diff.campo}: ${diff.para}` : diff.campo}
                          </td>
                          {COLUNAS_IMPACTO.map(({ chave }) => (
                            <td key={chave} />
                          ))}
                        </tr>
                      ))}
                    </>
                  )}

                  {material.lista_tecnica.length > 0 && (
                    <>
                      <tr className="bg-surface-alt/60">
                        <td />
                        <td className="px-3 py-2 font-medium text-ink-muted">
                          Alteração de Lista Técnica no Centro: {material.centro || '—'}
                        </td>
                        <td className="px-3 py-2 text-center text-xs font-semibold uppercase text-ink-muted">De:</td>
                        <td className="px-3 py-2 text-center text-xs font-semibold uppercase text-ink-muted">
                          Para:
                        </td>
                        {COLUNAS_IMPACTO.map(({ chave }) => (
                          <td key={chave} />
                        ))}
                      </tr>
                      {material.lista_tecnica.map((item, i) => (
                        <tr key={`${item.codigo_filho}-${i}`}>
                          <td className="whitespace-nowrap px-3 py-2 text-ink">{item.codigo_filho}</td>
                          <td />
                          <td className="px-3 py-2 text-center text-ink-muted">{item.quantidade_de || '0'}</td>
                          <td className="px-3 py-2 text-center text-ink-muted">{item.quantidade_para || '0'}</td>
                          {COLUNAS_IMPACTO.map(({ chave }) => (
                            <td key={chave} />
                          ))}
                        </tr>
                      ))}
                    </>
                  )}

                </Fragment>
              )
            })}
          </tbody>
        </table>
      </div>
    </Card>
  )
}
