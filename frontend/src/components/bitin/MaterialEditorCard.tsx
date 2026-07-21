import { memo, useId, useMemo, useState } from 'react'
import Card from '../Card'
import ListaTecnicaInline from './ListaTecnicaInline'
import { erroDominioCampo } from '../../lib/dadosBasicosValidacao'
import { normalizar } from '../../lib/texto'
import type { ItemListaTecnica, MateriaisSchema, MaterialEditavel } from '../../lib/types'

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
// React.memo (2026-07-17, otimização de performance -- pedido explícito: "usa como base o
// frontend antigo que tinha uma otimização feita", ver GPT_Engineering_BITIN/frontend/src/
// components/CodeForm.jsx) -- sem isso, MateriaisSection re-renderiza TODOS os cards a cada
// render de BitinDetail (ex.: editar um campo em QUALQUER outro card, ou até digitar em
// produto/motivo em DadosGeraisCard). Comparador padrão (shallow): só funciona porque
// `onChange`/`onRemove` agora são passados direto do pai (useCallback em BitinDetail.tsx),
// não reembrulhados numa closure nova por card a cada render (ver MateriaisSection.tsx).
const MaterialEditorCard = memo(function MaterialEditorCard({
  id,
  material,
  schema,
  onChange,
  onRemove,
}: {
  id: string
  material: MaterialEditavel
  schema: MateriaisSchema
  onChange: (id: string, m: MaterialEditavel) => void
  onRemove?: (id: string) => void
}) {
  const idPrefixo = useId()
  const camposSapConhecidos = useMemo(() => new Set(schema.dados_basicos.map((c) => c.key)), [schema])

  const [novoCampo, setNovoCampo] = useState('')
  const [mostrarAddCampo, setMostrarAddCampo] = useState(false)
  // Colapsada por padrão (2026-07-16, mesmo padrão do "+ Campo alterado / nota" -- só mostra
  // a grade de lista técnica quando o engenheiro clica, pra não poluir materiais que não têm
  // alteração de lista técnica). Abre sozinha se já houver itens (material importado da página
  // Lista Técnica, ou reaberto depois de salvo).
  const [mostrarListaTecnica, setMostrarListaTecnica] = useState(material.alteracoes.lista_tecnica.length > 0)

  function setListaTecnica(itens: ItemListaTecnica[]) {
    onChange(id, { ...material, alteracoes: { ...material.alteracoes, lista_tecnica: itens } })
  }
  // Campo com "de" preenchido (vindo da ZBPP009, snapshot atual do SAP) também entra na
  // tabela editável, não só campo que já tem "para" -- achado real (2026-07-16): importar da
  // ZBPP009 preenche só o "de" de propósito (o "para" é declarado aqui, na aba BITin), mas
  // antes disso o material chegava com os 30 campos de dados_basicos preenchidos e a tabela
  // "Alteração de dados básicos" aparecia vazia -- o engenheiro tinha que readicionar cada
  // campo na mão, perdendo o "de" que a ZBPP009 já tinha capturado certinho.
  const [camposEmEdicao, setCamposEmEdicao] = useState<Set<string>>(
    () =>
      new Set(
        Object.entries(material.alteracoes.dados_basicos)
          .filter(([campo, entry]) => camposSapConhecidos.has(campo) && (entry.de !== '' || entry.para !== ''))
          .map(([campo]) => campo),
      ),
  )

  function set<K extends keyof MaterialEditavel>(key: K, value: MaterialEditavel[K]) {
    onChange(id, { ...material, [key]: value })
  }

  function setImpacto(key: string, value: string | boolean) {
    onChange(id, {
      ...material,
      alteracoes: { ...material.alteracoes, impactos_operacionais: { ...material.alteracoes.impactos_operacionais, [key]: value } },
    })
  }

  function setDadoBasico(campo: string, de: string, para: string) {
    onChange(id, {
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
    onChange(id, { ...material, alteracoes: { ...material.alteracoes, dados_basicos: resto } })
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
    onChange(id, { ...material, alteracoes: { ...material.alteracoes, dados_basicos: dadosBasicos } })
  }

  function adicionarCampo(textoDigitado: string) {
    const texto = textoDigitado.trim()
    if (!texto) return

    // Busca tolerante (2026-07-16, pedido do usuário: "não precisa ser exatamente o nome do
    // campo (letra maiúscula acentro etc)... se escrever niv vai achar Nível de Revisão") --
    // ignora acento/maiúscula e casa por trecho, não só igualdade exata. Prioriza: chave exata
    // > label exata (já tolerante a acento/caixa) > label que CONTÉM o texto digitado.
    const textoNormalizado = normalizar(texto)
    const campoConhecido =
      schema.dados_basicos.find((c) => c.key === texto) ??
      schema.dados_basicos.find((c) => normalizar(c.label) === textoNormalizado) ??
      schema.dados_basicos.find((c) => normalizar(c.label).includes(textoNormalizado))

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

  // useMemo (2026-07-17) -- antes recalculadas no corpo do render a cada render, mesmo quando
  // nada que afeta o resultado mudou (ex.: um sibling card editado, que antes re-renderizava
  // este card também -- agora não re-renderiza mais, ver React.memo acima, mas mesmo os
  // re-renders que sobram por mudança própria não precisam refazer os 4 `.filter`/
  // `Object.entries` se `material`/`camposSapConhecidos`/`camposEmEdicao`/`schema` não mudaram).
  const entradas = useMemo(() => Object.entries(material.alteracoes.dados_basicos), [material])
  const entradasSap = useMemo(
    () => entradas.filter(([campo]) => camposSapConhecidos.has(campo) && camposEmEdicao.has(campo)),
    [entradas, camposSapConhecidos, camposEmEdicao],
  )
  const entradasLivres = useMemo(
    () => entradas.filter(([campo]) => !camposSapConhecidos.has(campo)),
    [entradas, camposSapConhecidos],
  )
  const camposDisponiveis = useMemo(
    () => schema.dados_basicos.filter((c) => !camposEmEdicao.has(c.key)),
    [schema, camposEmEdicao],
  )

  // Sugestões ao vivo (2026-07-17, pedido explícito: "se eu buscar só 'ni' já aparece...
  // nivel de revisão. hoje precisa escrever exatamente o nome do campo pra achar") --
  // substitui o <datalist> nativo (removido abaixo), que não ignora acento (buscar "ni" não
  // achava "Nível de Revisão" no navegador, só a busca por trecho de `adicionarCampo` já
  // fazia isso, mas só ao CONFIRMAR, não enquanto digitava). Mesma função `normalizar`
  // (escopo do módulo) usada nos dois lugares, pra não divergir.
  const sugestoesCampo = useMemo(() => {
    const texto = normalizar(novoCampo.trim())
    if (!texto) return []
    return camposDisponiveis.filter((c) => normalizar(c.label).includes(texto)).slice(0, 8)
  }, [novoCampo, camposDisponiveis])
  const [sugestoesAbertas, setSugestoesAbertas] = useState(false)

  return (
    <Card>
      {onRemove && (
        <button
          type="button"
          onClick={() => onRemove(id)}
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
          {/* Centro é a planta SAP -- só existem duas em que o BITin opera (2026-07-16,
              restrição pedida pelo usuário): 2001 Marau e 2005 Passo Fundo. NÃO confundir com
              "depósito" (SAP storage location, ex.: deposito_producao/deposito_suprimento_externo
              acima em alteracoes.dados_basicos -- conceito diferente, sem essa restrição). */}
          <select
            id={`${idPrefixo}-centro`}
            required
            value={material.centro}
            onChange={(e) => set('centro', e.target.value)}
            className="dark:[color-scheme:dark] [color-scheme:light] w-full rounded border border-line bg-surface px-2 py-1.5 text-sm text-ink focus:border-brand-navy focus:outline-none"
          >
            <option value="">--</option>
            {/* Só o número (2026-07-17, pedido explícito) -- sem "— Marau"/"— Passo Fundo". */}
            <option value="2001">2001</option>
            <option value="2005">2005</option>
          </select>
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
              {entradasSap.map(([campo, { de, para }]) => {
                const erroDe = erroDominioCampo(campo, de)
                const erroPara = erroDominioCampo(campo, para)
                return (
                  <tr key={campo}>
                    <td className="px-3 py-2 text-ink">{labelDoCampo(campo)}</td>
                    <td className="px-3 py-2">
                      <input
                        type="text"
                        value={de}
                        onChange={(e) => setDadoBasico(campo, e.target.value, para)}
                        className={`w-full rounded border bg-surface px-2 py-1 text-sm text-ink focus:outline-none ${erroDe ? 'border-red-600 focus:border-red-600' : 'border-line focus:border-brand-navy'}`}
                      />
                      {erroDe && <p className="mt-0.5 text-xs text-red-600">{erroDe}</p>}
                    </td>
                    <td className="px-3 py-2">
                      <input
                        type="text"
                        value={para}
                        onChange={(e) => setDadoBasico(campo, de, e.target.value)}
                        className={`w-full rounded border bg-surface px-2 py-1 text-sm text-ink focus:outline-none ${erroPara ? 'border-red-600 focus:border-red-600' : 'border-line focus:border-brand-navy'}`}
                      />
                      {erroPara && <p className="mt-0.5 text-xs text-red-600">{erroPara}</p>}
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
                )
              })}
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
          {/* key={posicao} é deliberado, não um esquecimento (revisado 2026-07-17) -- a
              "identidade" de uma nota livre É o próprio texto (dados_basicos é um objeto
              chaveado pelo texto digitado, sem id próprio), e esse texto muda a CADA tecla
              digitada (renomearNotaLivre substitui a chave no lugar); usar key={campo} remontaria
              o <input> a cada tecla, perdendo o foco/cursor no meio da digitação. Posição é a
              única identidade estável disponível aqui sem uma mudança estrutural maior
              (dados_basicos viraria array de objetos com id próprio em vez de Record). */}
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

      <div className="mt-3 flex flex-wrap items-center gap-2">
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
            <div className="relative w-80">
              <input
                type="text"
                value={novoCampo}
                onChange={(e) => {
                  setNovoCampo(e.target.value)
                  setSugestoesAbertas(true)
                }}
                onFocus={() => setSugestoesAbertas(true)}
                // Delay antes de fechar (2026-07-17) -- dá tempo do onMouseDown da sugestão
                // (abaixo) disparar ANTES do blur fechar a lista; onClick sozinho perderia a
                // corrida (blur fecha a lista antes do click da sugestão ser processado).
                onBlur={() => setTimeout(() => setSugestoesAbertas(false), 150)}
                placeholder="Nome do campo SAP ou uma nota livre (ex.: 'Salvar DWG')"
                className="w-full rounded-lg border border-line bg-surface px-3 py-1.5 text-sm text-ink focus:border-brand-navy focus:outline-none"
              />
              {/* Sugestões ao vivo, tolerantes a acento/maiúscula (2026-07-17) -- substitui o
                  <datalist> nativo, ver comentário em `sugestoesCampo` acima. */}
              {sugestoesAbertas && sugestoesCampo.length > 0 && (
                <ul className="absolute left-0 right-0 top-full z-10 mt-1 max-h-56 overflow-auto rounded-lg border border-line bg-surface py-1 shadow-lg">
                  {sugestoesCampo.map((c) => (
                    <li key={c.key}>
                      <button
                        type="button"
                        onMouseDown={() => adicionarCampo(c.label)}
                        className="block w-full px-3 py-1.5 text-left text-sm text-ink hover:bg-surface-alt"
                      >
                        {c.label}
                      </button>
                    </li>
                  ))}
                </ul>
              )}
            </div>
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

        {/* "+ Lista técnica" (2026-07-16, ao lado de "+ Campo alterado / nota", pedido do
            usuário): edita `material.alteracoes.lista_tecnica` sem sair da aba BITin. Mesmo
            array que a página dedicada Lista Técnica lê/escreve (ver ListaTecnicaInline.tsx) --
            nenhuma das duas depende da outra, igual ao resto desta tela. */}
        <button
          type="button"
          onClick={() => setMostrarListaTecnica((atual) => !atual)}
          className="rounded-lg border border-line px-3 py-1.5 text-sm font-medium text-ink-muted hover:bg-surface-alt"
        >
          {mostrarListaTecnica ? 'Ocultar lista técnica' : '+ Lista técnica'}
        </button>
      </div>

      {mostrarListaTecnica && (
        <div className="mt-3">
          <h3 className="text-xs font-semibold uppercase tracking-wide text-ink-muted">Lista técnica</h3>
          <ListaTecnicaInline itens={material.alteracoes.lista_tecnica} editavel onChange={setListaTecnica} />
        </div>
      )}
    </Card>
  )
})

export default MaterialEditorCard
