import { memo, useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import Card from '../Card'
import AjudaPopover from './AjudaPopover'
import EdicaoBottomBar from './EdicaoBottomBar'
import ErrosEnvioBanner from './ErrosEnvioBanner'
import { useAvisoSairSemSalvar } from '../../hooks/useAvisoSairSemSalvar'
import { api } from '../../lib/api'
import { materialVazio, normalizarMaterial } from '../../lib/bitinDefaults'
import { useEnviarBitin } from '../../lib/useEnviarBitin'
import type { Bitin, ItemListaTecnica, MaterialEditavel, OperacaoListaTecnica } from '../../lib/types'

// Grade de preenchimento em massa da Lista Técnica -- sub-aba "Lista Técnica" dentro da aba
// "Preenchimento" (2026-07-23, só existe no modo manual; ver PreenchimentoPage.tsx). Herdada
// quase sem mudança da antiga página própria (ListaTecnicaPage.tsx, removida quando as 3 telas
// viraram uma só) -- grade plana (uma linha = um componente filho), código pai como texto
// livre, não precisa existir ainda em materiais[].
interface LinhaListaTecnicaBase extends ItemListaTecnica {
  codigo_pai: string
  centro: string
  descricao: string
}

type LinhaListaTecnica = LinhaListaTecnicaBase & { _id: string }

function linhaVazia(): LinhaListaTecnica {
  return {
    codigo_pai: '',
    centro: '',
    descricao: '',
    operacao: 'alterar',
    codigo_filho: '',
    quantidade_de: '',
    quantidade_para: '',
    _id: crypto.randomUUID(),
  }
}

function derivarOperacao(item: ItemListaTecnica): OperacaoListaTecnica {
  const temDe = item.quantidade_de.trim() !== ''
  const temPara = item.quantidade_para.trim() !== ''
  if (!temDe && temPara) return 'inserir'
  if (temDe && !temPara) return 'excluir'
  return 'alterar'
}

function materiaisParaLinhas(materiais: MaterialEditavel[]): LinhaListaTecnica[] {
  const linhas = materiais.flatMap((m) =>
    m.alteracoes.lista_tecnica.map((item) => ({
      codigo_pai: m.codigo_material,
      centro: m.centro,
      descricao: m.descricao_material,
      ...item,
      _id: crypto.randomUUID(),
    })),
  )
  return [...linhas, linhaVazia()]
}

const CelulaTexto = memo(function CelulaTexto({
  valor,
  onCommit,
  numerico,
  className,
  listId,
}: {
  valor: string
  onCommit: (novoValor: string) => void
  numerico?: boolean
  className: string
  listId?: string
}) {
  const [local, setLocal] = useState(valor)
  useEffect(() => setLocal(valor), [valor])
  return (
    <input
      type="text"
      inputMode={numerico ? 'decimal' : undefined}
      list={listId}
      value={local}
      onChange={(e) => setLocal(numerico ? e.target.value.replace(/[^0-9.]/g, '') : e.target.value)}
      onBlur={() => {
        if (local !== valor) onCommit(local)
      }}
      className={className}
    />
  )
})

const LinhaTecnicaRow = memo(function LinhaTecnicaRow({
  linha,
  selecionada,
  onCampoCommit,
  onRemover,
  onToggleSelecao,
}: {
  linha: LinhaListaTecnica
  selecionada: boolean
  onCampoCommit: (id: string, campo: keyof LinhaListaTecnicaBase, valor: string) => void
  onRemover: (id: string) => void
  onToggleSelecao: (id: string) => void
}) {
  const classeInput =
    'rounded border border-line bg-surface px-2 py-1.5 text-sm text-ink focus:border-brand-navy focus:outline-none'
  return (
    <tr>
      <td className="px-3 py-1.5 text-center">
        <input
          type="checkbox"
          checked={selecionada}
          onChange={() => onToggleSelecao(linha._id)}
          aria-label="Selecionar linha"
        />
      </td>
      <td className="p-1.5">
        <CelulaTexto
          valor={linha.codigo_pai}
          onCommit={(valor) => onCampoCommit(linha._id, 'codigo_pai', valor)}
          className={`w-32 ${classeInput}`}
          listId="lista-tecnica-codigos-pai"
        />
      </td>
      <td className="p-1.5">
        <CelulaTexto
          valor={linha.centro}
          onCommit={(valor) => onCampoCommit(linha._id, 'centro', valor)}
          className={`w-24 ${classeInput}`}
        />
      </td>
      <td className="p-1.5">
        <CelulaTexto
          valor={linha.descricao}
          onCommit={(valor) => onCampoCommit(linha._id, 'descricao', valor)}
          className={`w-48 ${classeInput}`}
        />
      </td>
      <td className="p-1.5">
        <CelulaTexto
          valor={linha.codigo_filho}
          onCommit={(valor) => onCampoCommit(linha._id, 'codigo_filho', valor)}
          className={`w-40 ${classeInput}`}
        />
      </td>
      <td className="p-1.5">
        <CelulaTexto
          valor={linha.quantidade_de}
          onCommit={(valor) => onCampoCommit(linha._id, 'quantidade_de', valor)}
          numerico
          className={`w-28 ${classeInput}`}
        />
      </td>
      <td className="p-1.5">
        <CelulaTexto
          valor={linha.quantidade_para}
          onCommit={(valor) => onCampoCommit(linha._id, 'quantidade_para', valor)}
          numerico
          className={`w-28 ${classeInput}`}
        />
      </td>
      <td className="p-1.5 text-center">
        <button
          type="button"
          onClick={() => onRemover(linha._id)}
          className="text-ink-faint hover:text-red-600"
          aria-label="Remover linha"
        >
          ×
        </button>
      </td>
    </tr>
  )
})

export default function PreenchimentoListaTecnica({
  agenteConectado,
  onSujoChange,
}: {
  agenteConectado: boolean
  onSujoChange: (sujo: boolean) => void
}) {
  const { mongoId } = useParams<{ mongoId: string }>()
  const navigate = useNavigate()
  const [materiais, setMateriais] = useState<MaterialEditavel[]>([])
  const codigosExistentes = useMemo(
    () => [...new Set(materiais.map((m) => m.codigo_material.trim()).filter(Boolean))],
    [materiais],
  )
  const [linhas, setLinhas] = useState<LinhaListaTecnica[]>([linhaVazia()])
  const linhasRef = useRef(linhas)
  const [conteudoExistente, setConteudoExistente] = useState<Record<string, unknown>>({})
  const [carregando, setCarregando] = useState(true)
  const [salvando, setSalvando] = useState(false)
  const [erro, setErro] = useState<string | null>(null)
  const [salvoRecentemente, setSalvoRecentemente] = useState(false)
  const [selecionadas, setSelecionadas] = useState<Set<string>>(new Set())
  const { enviando, errosEnvio, bitinEnviado, enviar } = useEnviarBitin(mongoId)
  const { sujo, setSujo } = useAvisoSairSemSalvar()

  useEffect(() => {
    onSujoChange(sujo)
  }, [sujo, onSujoChange])

  useEffect(() => {
    if (bitinEnviado) navigate(`/bitins/${mongoId}`)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [bitinEnviado])

  useEffect(() => {
    if (!mongoId) return
    let cancelado = false
    api
      .get<Bitin>(`/bitins/${mongoId}`)
      .then((resp) => {
        if (cancelado) return
        setConteudoExistente(resp.data.content)
        const materiaisExistentes = ((resp.data.content.materiais as MaterialEditavel[] | undefined) ?? []).map(normalizarMaterial)
        setMateriais(materiaisExistentes)
        const linhasCarregadas = materiaisParaLinhas(materiaisExistentes)
        linhasRef.current = linhasCarregadas
        setLinhas(linhasCarregadas)
      })
      .catch(() => setErro('Não foi possível carregar os dados.'))
      .finally(() => setCarregando(false))
    return () => {
      cancelado = true
    }
  }, [mongoId])

  const atualizarCampo = useCallback((id: string, campo: keyof LinhaListaTecnicaBase, valor: string) => {
    linhasRef.current = linhasRef.current.map((l) => (l._id === id ? { ...l, [campo]: valor } : l))
    setLinhas(linhasRef.current)
    setSujo(true)
  }, [setSujo])

  const removerLinha = useCallback((id: string) => {
    linhasRef.current = linhasRef.current.filter((l) => l._id !== id)
    setLinhas(linhasRef.current)
    setSelecionadas((atual) => {
      if (!atual.has(id)) return atual
      const copia = new Set(atual)
      copia.delete(id)
      return copia
    })
    setSujo(true)
  }, [setSujo])

  const removerSelecionadas = useCallback(() => {
    const restantes = linhasRef.current.filter((l) => !selecionadas.has(l._id))
    linhasRef.current = restantes.length === 0 ? [linhaVazia()] : restantes
    setLinhas(linhasRef.current)
    setSelecionadas(new Set())
    setSujo(true)
  }, [selecionadas, setSujo])

  function limparTudo() {
    if (!window.confirm('Limpar toda a tabela? Essa ação não pode ser desfeita.')) return
    linhasRef.current = [linhaVazia()]
    setLinhas(linhasRef.current)
    setSelecionadas(new Set())
    setSujo(true)
  }

  const alternarSelecao = useCallback((id: string) => {
    setSelecionadas((atual) => {
      const copia = new Set(atual)
      if (copia.has(id)) copia.delete(id)
      else copia.add(id)
      return copia
    })
  }, [])

  function alternarSelecaoTodas() {
    setSelecionadas((atual) => (atual.size === linhas.length ? new Set() : new Set(linhas.map((l) => l._id))))
  }

  async function salvar() {
    if (document.activeElement instanceof HTMLElement) document.activeElement.blur()

    setErro(null)
    setSalvando(true)
    try {
      const linhasAtuais = linhasRef.current
      const linhasPreenchidas = linhasAtuais.filter((l) => l.codigo_pai.trim() !== '' && l.codigo_filho.trim() !== '')
      const normalizar = (s: string) => s.trim().toLowerCase()
      const grupos = new Map<
        string,
        { codigoDigitado: string; centro: string; descricao: string; itens: ItemListaTecnica[] }
      >()
      for (const l of linhasPreenchidas) {
        const { codigo_pai, centro, descricao, _id, ...item } = l
        const chave = normalizar(codigo_pai)
        const grupo = grupos.get(chave) ?? { codigoDigitado: codigo_pai.trim(), centro: '', descricao: '', itens: [] }
        if (!grupo.centro && centro.trim()) grupo.centro = centro.trim()
        if (!grupo.descricao && descricao.trim()) grupo.descricao = descricao.trim()
        grupo.itens.push({ ...item, operacao: derivarOperacao(item) })
        grupos.set(chave, grupo)
      }

      let materiaisAtualizados = materiais.map((m) => {
        const grupo = grupos.get(normalizar(m.codigo_material))
        return {
          ...m,
          centro: m.centro.trim() || grupo?.centro || m.centro,
          descricao_material: m.descricao_material.trim() || grupo?.descricao || m.descricao_material,
          alteracoes: { ...m.alteracoes, lista_tecnica: grupo?.itens ?? [] },
        }
      })
      for (const [chave, { codigoDigitado, centro, descricao, itens }] of grupos) {
        if (!materiaisAtualizados.some((m) => normalizar(m.codigo_material) === chave)) {
          materiaisAtualizados = [
            ...materiaisAtualizados,
            {
              ...materialVazio(),
              codigo_material: codigoDigitado,
              centro,
              descricao_material: descricao,
              alteracoes: { ...materialVazio().alteracoes, lista_tecnica: itens },
            },
          ]
        }
      }

      await api.post('/bitins/draft', {
        mongo_id: mongoId,
        content: { ...conteudoExistente, materiais: materiaisAtualizados },
      })
      setMateriais(materiaisAtualizados)
      const linhasRecarregadas = materiaisParaLinhas(materiaisAtualizados)
      linhasRef.current = linhasRecarregadas
      setLinhas(linhasRecarregadas)
      setSujo(false)
      setSalvoRecentemente(true)
      setTimeout(() => setSalvoRecentemente(false), 3000)
      return true
    } catch {
      setErro('Não foi possível salvar. Tente novamente.')
      return false
    } finally {
      setSalvando(false)
    }
  }

  async function handleEnviar() {
    await salvar()
    await enviar()
  }

  async function importar() {
    const ok = await salvar()
    if (ok) navigate(`/bitins/${mongoId}`)
  }

  if (carregando) {
    return <p className="text-sm text-ink-muted">Carregando...</p>
  }

  return (
    <>
      <div className="mt-3 flex flex-wrap items-center gap-3">
        <AjudaPopover titulo="Hint">
          <p>
            Cada linha é um componente filho -- <strong>Código pai</strong> é texto livre, não
            precisa existir ainda no BITin.
          </p>
          <p>
            Regra de preenchimento: preencha os dois campos de <strong>Quantidade</strong> (De/
            Para) numa alteração normal; pra excluir, deixe "Para" vazio; pra inserir, deixe
            "De" vazio.
          </p>
          <p>
            <strong>Salvar</strong> guarda sem sair da tela. <strong>Importar</strong> salva e já
            leva pra aba BITin.
          </p>
        </AjudaPopover>
        <div className="ml-auto flex gap-2">
          <button
            type="button"
            onClick={salvar}
            disabled={salvando || enviando}
            className="rounded-lg border border-line px-4 py-2 text-sm font-medium text-ink-muted transition-colors hover:bg-surface-alt disabled:cursor-not-allowed disabled:opacity-60"
          >
            {salvando ? 'Salvando...' : 'Salvar'}
          </button>
          <button
            type="button"
            onClick={importar}
            disabled={salvando || enviando}
            className="rounded-lg bg-brand-navy px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-brand-navy-dark disabled:cursor-not-allowed disabled:opacity-60"
          >
            Importar pra BITin
          </button>
        </div>
      </div>

      {erro && <p className="mt-3 text-sm text-red-600">{erro}</p>}
      {salvoRecentemente && !erro && <p className="mt-3 text-sm text-brand-green">Salvo.</p>}
      <ErrosEnvioBanner erros={errosEnvio} />

      <Card title="Lista técnica">
        <div className="mt-4 flex flex-wrap items-center gap-2 rounded-lg bg-surface-alt px-3 py-2">
          <span className="text-xs font-medium text-ink-muted">
            {selecionadas.size > 0 ? `${selecionadas.size} selecionada(s)` : 'Nenhuma linha selecionada'}
          </span>
          <button
            type="button"
            onClick={removerSelecionadas}
            disabled={selecionadas.size === 0}
            className="rounded-lg border border-red-600/40 px-3 py-1.5 text-xs font-medium text-red-600 transition-colors hover:bg-red-600/10 disabled:cursor-not-allowed disabled:opacity-40"
          >
            Excluir selecionadas
          </button>
          <button
            type="button"
            onClick={limparTudo}
            className="rounded-lg border border-line px-3 py-1.5 text-xs font-medium text-ink-muted transition-colors hover:bg-surface"
          >
            Limpar tudo
          </button>
          <button
            type="button"
            onClick={() => {
              linhasRef.current = [...linhasRef.current, linhaVazia()]
              setLinhas(linhasRef.current)
              setSujo(true)
            }}
            className="ml-auto rounded-lg border border-dashed border-line px-3 py-1.5 text-xs font-medium text-ink-muted hover:bg-surface"
          >
            + Nova linha
          </button>
        </div>

        <datalist id="lista-tecnica-codigos-pai">
          {codigosExistentes.map((c) => (
            <option key={c} value={c} />
          ))}
        </datalist>

        <div className="mt-2 overflow-x-auto rounded border border-line">
          <table className="w-full text-left text-sm">
            <thead>
              <tr className="bg-surface-alt text-xs uppercase tracking-wide text-ink-muted">
                <th className="w-8 px-3 py-2">
                  <input
                    type="checkbox"
                    checked={linhas.length > 0 && selecionadas.size === linhas.length}
                    onChange={alternarSelecaoTodas}
                    aria-label="Selecionar todas as linhas"
                  />
                </th>
                <th className="whitespace-nowrap px-3 py-2 font-medium">Código pai</th>
                <th className="whitespace-nowrap px-3 py-2 font-medium">Centro</th>
                <th className="whitespace-nowrap px-3 py-2 font-medium">Descrição</th>
                <th className="whitespace-nowrap px-3 py-2 font-medium">Código filho</th>
                <th className="whitespace-nowrap px-3 py-2 font-medium">Quantidade de</th>
                <th className="whitespace-nowrap px-3 py-2 font-medium">Quantidade para</th>
                <th className="w-10" />
              </tr>
            </thead>
            <tbody className="divide-y divide-line">
              {linhas.map((l) => (
                <LinhaTecnicaRow
                  key={l._id}
                  linha={l}
                  selecionada={selecionadas.has(l._id)}
                  onCampoCommit={atualizarCampo}
                  onRemover={removerLinha}
                  onToggleSelecao={alternarSelecao}
                />
              ))}
            </tbody>
          </table>
        </div>
      </Card>

      {mongoId && (
        <EdicaoBottomBar mongoId={mongoId} agenteConectado={agenteConectado} enviando={enviando || salvando} onEnviar={handleEnviar} />
      )}
    </>
  )
}
