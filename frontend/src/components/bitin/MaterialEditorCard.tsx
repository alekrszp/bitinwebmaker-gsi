import { useId, useState } from 'react'
import Card from '../Card'
import type { MateriaisSchema, MaterialEditavel } from '../../lib/types'

const COLUNAS_IMPACTO = [
  { chave: 'alt', label: 'Alt' },
  { chave: 'est', label: 'Est' },
  { chave: 'esp', label: 'Esp' },
  { chave: 'lp', label: 'LP' },
  { chave: 'pre', label: 'Pre' },
  { chave: 'oc', label: 'OC' },
  { chave: 'of', label: 'OF' },
] as const

// Bloco editável de um material na aba "BITin" -- mesma estrutura da visualização quando
// enviado (AlteracaoTable): código + descrição + indicadores em destaque no topo, alteração
// de dados básicos (De/Para) logo abaixo, notas livres do engenheiro em vermelho centralizadas
// no meio do bloco. A diferença entre as duas telas é só travar ou não os campos -- não duas
// estruturas diferentes (decisão do usuário, 2026-07-15: "tela de BITin vai ser a MESMA COISA
// QUE VISUALIZAÇÃO QUANDO ENVIADO, mas podendo editar os campos").
//
// Código/centro/descrição/tipo ficam editáveis sempre aqui -- o engenheiro pode cadastrar um
// material inteiro à mão nesta aba sem nunca abrir Códigos SAP ("ele só vai editar na tela
// BITin a mão fácil e enviar"). Códigos SAP é só outro jeito de chegar no mesmo materiais[]
// (colar/digitar em tabela, igual à ZBPP009) -- nenhuma das duas telas depende da outra.
//
// Campo SAP reconhecido (bate com `schema.dados_basicos`) vira uma linha De/Para na tabela.
// Campo que não bate é nota livre -- mostrada só como texto corrido vermelho, sem par De/Para,
// igual a visualização já trata (`AlteracaoTable`/`scripts/bitin_document.py::
// build_campo_alterado_diffs`).
//
// Sem "Atualizar DWG/SAT" nem "Centro de custo"/"Conta razão" aqui (2026-07-15, decisão do
// usuário: "não precisa disso"): "Atualizar DWG/SAT" agora é só clicar no item 18 da
// checklist (override manual, ver ChecklistTable) -- e o centro de custo/conta razão do
// sucateamento de estoque (Est=S) viram a descrição do item 22 da checklist ("Centro de
// custo (se tem sucata)"), não mais um campo por material.
//
// "Tipo do material" também não aparece mais aqui (2026-07-15, decisão do usuário: "tirar o
// campo tipo de material ali do bloco do código, deixa isso escondido, não precisa mostrar")
// -- continua no modelo (`material.tipo_material`, obrigatório em bitin_model.py) e por isso
// `materialVazio()` já preenche um padrão sensato ("HALB"), já que não há mais controle na UI
// pra digitá-lo.
export default function MaterialEditorCard({
  material,
  schema,
  onChange,
  onRemove,
}: {
  material: MaterialEditavel
  schema: MateriaisSchema
  onChange: (m: MaterialEditavel) => void
  onRemove?: () => void
}) {
  const idPrefixo = useId()
  const camposSapConhecidos = new Set(schema.dados_basicos.map((c) => c.key))

  const [novoCampo, setNovoCampo] = useState('')
  const [mostrarAddCampo, setMostrarAddCampo] = useState(false)
  const [camposEmEdicao, setCamposEmEdicao] = useState<Set<string>>(
    () =>
      new Set(
        Object.entries(material.alteracoes.dados_basicos)
          .filter(([campo, entry]) => camposSapConhecidos.has(campo) && entry.para !== '')
          .map(([campo]) => campo),
      ),
  )

  function set<K extends keyof MaterialEditavel>(key: K, value: MaterialEditavel[K]) {
    onChange({ ...material, [key]: value })
  }

  function setImpacto(key: string, value: string | boolean) {
    onChange({
      ...material,
      alteracoes: { ...material.alteracoes, impactos_operacionais: { ...material.alteracoes.impactos_operacionais, [key]: value } },
    })
  }

  function setDadoBasico(campo: string, de: string, para: string) {
    onChange({
      ...material,
      alteracoes: {
        ...material.alteracoes,
        dados_basicos: { ...material.alteracoes.dados_basicos, [campo]: { de, para } },
      },
    })
  }

  function removerDadoBasico(campo: string) {
    const resto = { ...material.alteracoes.dados_basicos }
    delete resto[campo]
    onChange({ ...material, alteracoes: { ...material.alteracoes, dados_basicos: resto } })
    setCamposEmEdicao((atual) => {
      const copia = new Set(atual)
      copia.delete(campo)
      return copia
    })
  }

  // Nota livre é texto corrido único (a chave inteira é o texto, sem campo/valor separados --
  // "Salvar DWG" não tem detalhe nenhum, "Alterado lista tecnica: Alterado peso e IS" é uma
  // frase só, exatamente como está escrito no documento original). Editar substitui a chave
  // no lugar (não apaga+recria), senão a ordem das notas mudaria a cada tecla digitada e o
  // cursor "pularia" de uma nota pra outra quando há mais de uma (decisão do usuário,
  // 2026-07-15: "o campo de texto livre ta tendo como se fosse um campo com valor, é tudo
  // livre").
  function renomearNotaLivre(campoAntigo: string, novoTexto: string) {
    if (novoTexto.trim() === '') {
      removerDadoBasico(campoAntigo)
      return
    }
    const entradasAtuais = Object.entries(material.alteracoes.dados_basicos)
    const dadosBasicos = Object.fromEntries(
      entradasAtuais.map(([c, v]) => (c === campoAntigo ? [novoTexto, { de: '', para: '' }] : [c, v])),
    )
    onChange({ ...material, alteracoes: { ...material.alteracoes, dados_basicos: dadosBasicos } })
  }

  function adicionarCampo(textoDigitado: string) {
    const texto = textoDigitado.trim()
    if (!texto) return

    const campoConhecido = schema.dados_basicos.find(
      (c) => c.key === texto || c.label.toLowerCase() === texto.toLowerCase(),
    )

    if (campoConhecido) {
      const existente = material.alteracoes.dados_basicos[campoConhecido.key]
      if (!existente) setDadoBasico(campoConhecido.key, '', '')
      setCamposEmEdicao((atual) => new Set(atual).add(campoConhecido.key))
    } else {
      // Não bate com nenhum campo SAP conhecido -- vira nota livre (a própria chave carrega
      // o que foi escrito, igual a visualização já trata campos livres).
      setDadoBasico(texto, '', '')
    }

    setNovoCampo('')
    setMostrarAddCampo(false)
  }

  const labelDoCampo = (key: string) => schema.dados_basicos.find((c) => c.key === key)?.label ?? key

  const entradas = Object.entries(material.alteracoes.dados_basicos)
  const entradasSap = entradas.filter(
    ([campo]) => camposSapConhecidos.has(campo) && camposEmEdicao.has(campo),
  )
  const entradasLivres = entradas.filter(([campo]) => !camposSapConhecidos.has(campo))
  const camposDisponiveis = schema.dados_basicos.filter((c) => !camposEmEdicao.has(c.key))

  return (
    <Card>
      {onRemove && (
        <button
          type="button"
          onClick={onRemove}
          className="absolute right-5 top-5 text-xs font-medium text-red-600 hover:underline"
        >
          Remover
        </button>
      )}

      {/* Cabeçalho: código + descrição + indicadores lado a lado, igual a linha de destaque
          da visualização (AlteracaoTable). */}
      <div className="flex flex-wrap items-end gap-3 pr-16">
        <div className="w-32">
          <label htmlFor={`${idPrefixo}-codigo`} className="mb-1 block text-[0.65rem] uppercase tracking-wide text-ink-muted">
            Código *
          </label>
          <input
            id={`${idPrefixo}-codigo`}
            type="text"
            required
            value={material.codigo_material}
            onChange={(e) => set('codigo_material', e.target.value)}
            className="w-full rounded border border-line bg-surface px-2 py-1.5 text-sm font-semibold text-ink focus:border-brand-navy focus:outline-none"
          />
        </div>
        <div className="w-24">
          <label htmlFor={`${idPrefixo}-centro`} className="mb-1 block text-[0.65rem] uppercase tracking-wide text-ink-muted">
            Centro *
          </label>
          <input
            id={`${idPrefixo}-centro`}
            type="text"
            required
            value={material.centro}
            onChange={(e) => set('centro', e.target.value)}
            className="w-full rounded border border-line bg-surface px-2 py-1.5 text-sm text-ink focus:border-brand-navy focus:outline-none"
          />
        </div>
        <div className="min-w-[12rem] flex-1">
          <label htmlFor={`${idPrefixo}-descricao`} className="mb-1 block text-[0.65rem] uppercase tracking-wide text-ink-muted">
            Descrição
          </label>
          <input
            id={`${idPrefixo}-descricao`}
            type="text"
            value={material.descricao_material}
            onChange={(e) => set('descricao_material', e.target.value)}
            className="w-full rounded border border-line bg-surface px-2 py-1.5 text-sm font-semibold text-ink focus:border-brand-navy focus:outline-none"
          />
        </div>
        {COLUNAS_IMPACTO.map(({ chave, label }) => (
          <div key={chave} className="w-14">
            <label
              htmlFor={`${idPrefixo}-${chave}`}
              className="mb-1 block text-center text-[0.65rem] uppercase tracking-wide text-ink-muted"
            >
              {label}
            </label>
            <select
              id={`${idPrefixo}-${chave}`}
              value={String(material.alteracoes.impactos_operacionais[chave] ?? '-')}
              onChange={(e) => setImpacto(chave, e.target.value)}
              className="dark:[color-scheme:dark] [color-scheme:light] w-full rounded border border-line bg-surface px-1 py-1.5 text-center text-sm text-ink focus:border-brand-navy focus:outline-none"
            >
              {(schema.impactos_operacionais.find((c) => c.key === chave)?.options ?? []).map((opt) => (
                <option key={opt} value={opt}>
                  {opt}
                </option>
              ))}
            </select>
          </div>
        ))}
      </div>

      {/* Alteração de dados básicos: mesma tabela De/Para da visualização, editável. */}
      <h3 className="mt-5 text-xs font-semibold uppercase tracking-wide text-ink-muted">
        Alteração de dados básicos {material.centro && `no Centro: ${material.centro}`}
      </h3>
      {entradasSap.length > 0 && (
        <div className="mt-2 overflow-hidden rounded border border-line">
          <table className="w-full text-left text-sm">
            <thead>
              <tr className="bg-surface-alt text-xs uppercase tracking-wide text-ink-muted">
                <th className="px-3 py-2 font-medium">Campo</th>
                <th className="px-3 py-2 font-medium">De</th>
                <th className="px-3 py-2 font-medium">Para</th>
                <th className="w-10" />
              </tr>
            </thead>
            <tbody className="divide-y divide-line">
              {entradasSap.map(([campo, { de, para }]) => (
                <tr key={campo}>
                  <td className="px-3 py-2 text-ink">{labelDoCampo(campo)}</td>
                  <td className="px-3 py-2">
                    <input
                      type="text"
                      value={de}
                      onChange={(e) => setDadoBasico(campo, e.target.value, para)}
                      className="w-full rounded border border-line bg-surface px-2 py-1 text-sm text-ink focus:border-brand-navy focus:outline-none"
                    />
                  </td>
                  <td className="px-3 py-2">
                    <input
                      type="text"
                      value={para}
                      onChange={(e) => setDadoBasico(campo, de, e.target.value)}
                      className="w-full rounded border border-line bg-surface px-2 py-1 text-sm text-ink focus:border-brand-navy focus:outline-none"
                    />
                  </td>
                  <td className="px-3 py-2 text-center">
                    <button
                      type="button"
                      onClick={() => removerDadoBasico(campo)}
                      className="text-ink-faint hover:text-red-600"
                      aria-label={`Remover ${labelDoCampo(campo)}`}
                    >
                      ×
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Notas livres do engenheiro: texto corrido único, vermelho, centralizado no meio do
          bloco -- sem campo/valor separados, igual ao documento original ("Salvar DWG" é só
          isso, sem nada mais; "Alterado lista tecnica: Alterado peso e IS" é uma frase só).
          Nunca numa tabela De/Para (decisão do usuário, 2026-07-15). */}
      {entradasLivres.length > 0 && (
        <div className="mt-3 space-y-1 text-center">
          {entradasLivres.map(([campo], posicao) => (
            <div key={posicao} className="group inline-flex items-center gap-1.5">
              <input
                type="text"
                value={campo}
                onChange={(e) => renomearNotaLivre(campo, e.target.value)}
                className="w-96 rounded border border-transparent bg-transparent px-1 py-0.5 text-center text-sm font-medium text-livre-text focus:border-line focus:outline-none"
              />
              <button
                type="button"
                onClick={() => removerDadoBasico(campo)}
                className="text-ink-faint opacity-0 group-hover:opacity-100 hover:text-red-600"
                aria-label={`Remover nota "${campo}"`}
              >
                ×
              </button>
            </div>
          ))}
        </div>
      )}

      <div className="mt-3">
        {!mostrarAddCampo ? (
          <button
            type="button"
            onClick={() => setMostrarAddCampo(true)}
            className="rounded-lg border border-line px-3 py-1.5 text-sm font-medium text-ink-muted hover:bg-surface-alt"
          >
            + Campo alterado / nota
          </button>
        ) : (
          <div className="flex flex-wrap items-center gap-2">
            <input
              type="text"
              list={`campos-sap-${material.codigo_material}`}
              value={novoCampo}
              onChange={(e) => setNovoCampo(e.target.value)}
              placeholder="Nome do campo SAP ou uma nota livre (ex.: 'Salvar DWG')"
              className="w-80 rounded-lg border border-line bg-surface px-3 py-1.5 text-sm text-ink focus:border-brand-navy focus:outline-none"
            />
            <datalist id={`campos-sap-${material.codigo_material}`}>
              {camposDisponiveis.map((c) => (
                <option key={c.key} value={c.label} />
              ))}
            </datalist>
            <button
              type="button"
              onClick={() => adicionarCampo(novoCampo)}
              className="rounded-lg bg-brand-navy px-3 py-1.5 text-sm font-medium text-white hover:bg-brand-navy-dark"
            >
              Adicionar
            </button>
            <button
              type="button"
              onClick={() => {
                setMostrarAddCampo(false)
                setNovoCampo('')
              }}
              className="text-sm text-ink-muted hover:text-ink"
            >
              Cancelar
            </button>
          </div>
        )}
      </div>
    </Card>
  )
}
