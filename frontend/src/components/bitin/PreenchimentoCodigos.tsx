import { Fragment, memo, useCallback, useEffect, useMemo, useRef, useState, type ClipboardEvent } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import Card from '../Card'
import AjudaPopover from './AjudaPopover'
import EdicaoBottomBar from './EdicaoBottomBar'
import ErrosEnvioBanner from './ErrosEnvioBanner'
import { useAvisoSairSemSalvar } from '../../hooks/useAvisoSairSemSalvar'
import { api } from '../../lib/api'
import { materialVazio, normalizarMaterial } from '../../lib/bitinDefaults'
import { erroDominioCampo, erroParIncompleto } from '../../lib/dadosBasicosValidacao'
import { normalizar } from '../../lib/texto'
import { useEnviarBitin } from '../../lib/useEnviarBitin'
import type { Bitin, CampoSchema, MateriaisSchema, MaterialEditavel } from '../../lib/types'

// Grade de preenchimento em massa dos códigos de alteração (identificação + ~30 campos de
// dados_basicos, De/Para lado a lado) -- sub-aba "Códigos de alteração" dentro da aba
// "Preenchimento" (2026-07-23, só existe no modo manual, sem agente conectado; ver
// PreenchimentoPage.tsx). Herdada quase sem mudança da antiga página própria
// (CodigosSapPage.tsx/"ZBPP009", removida quando as 3 telas viraram uma só) -- o pedido do
// usuário foi trazer de volta o preenchimento em massa como uma aba dedicada, não reimplementar
// a lógica do zero. Colar do SAP, filtro de campos visíveis e o resto do comportamento são
// idênticos à versão antiga.
const COLUNAS_IDENTIFICACAO_OCULTAS = new Set<string>(['descricao_material'])

const GENERO_NOVO: Record<string, 'novo' | 'nova'> = {
  descricao: 'nova',
  grupo_mercadorias: 'novo',
  status: 'novo',
  hierarquia: 'nova',
  peso_bruto: 'novo',
  peso_liquido: 'novo',
  unidade_peso: 'nova',
  volume: 'novo',
  unidade_volume: 'nova',
  desenho: 'novo',
  nivel_revisao: 'novo',
  documento: 'novo',
  material_substituto: 'novo',
  status_bloqueio_vendas: 'novo',
  data_bloqueio_vendas: 'nova',
  ncm: 'novo',
  grupo_compradores: 'novo',
  planejador: 'novo',
  tipo_suprimento: 'novo',
  tipo_suprimento_especial: 'novo',
  deposito_producao: 'novo',
  deposito_suprimento_externo: 'novo',
  prazo_entrega: 'novo',
  responsavel_controle_producao: 'novo',
  perfil_producao: 'novo',
  utilizacao_material: 'nova',
  origem_material: 'nova',
  producao_interna: 'nova',
  texto_pedidos_compras: 'novo',
  marcacao_eliminar_nivel_mandante: 'nova',
}

type LinhaSap = MaterialEditavel & { _id: string }

function novaLinhaSap(): LinhaSap {
  return { ...materialVazio(), tipo_material: '', _id: crypto.randomUUID() }
}

function paraMaterialEditavel(bruto: Partial<MaterialEditavel> & { dados_basicos_atual?: Record<string, string> }): LinhaSap {
  const { dados_basicos_atual, ...identificacao } = bruto
  const dadosBasicos = Object.fromEntries(
    Object.entries(dados_basicos_atual ?? {})
      .filter(([, valor]) => valor !== '')
      .map(([campo, de]) => [campo, { de, para: '' }]),
  )
  return {
    ...materialVazio(),
    ...identificacao,
    alteracoes: { ...materialVazio().alteracoes, dados_basicos: dadosBasicos },
    _id: crypto.randomUUID(),
  }
}

const CelulaTexto = memo(function CelulaTexto({
  valor,
  onCommit,
  onPaste,
  erro,
}: {
  valor: string
  onCommit: (novoValor: string) => void
  onPaste?: (e: ClipboardEvent<HTMLInputElement>) => void
  erro?: string | null
}) {
  const [local, setLocal] = useState(valor)

  useEffect(() => {
    setLocal(valor)
  }, [valor])

  return (
    <div>
      <input
        type="text"
        value={local}
        onChange={(e) => setLocal(e.target.value)}
        onBlur={() => {
          if (local !== valor) onCommit(local)
        }}
        onPaste={onPaste}
        className={`w-full min-w-[5rem] rounded border bg-surface px-2 py-1.5 text-sm text-ink focus:outline-none ${erro ? 'border-red-600 focus:border-red-600' : 'border-line focus:border-brand-navy'}`}
      />
      {erro && <p className="mt-0.5 text-xs text-red-600">{erro}</p>}
    </div>
  )
})

const LinhaSapRow = memo(function LinhaSapRow({
  linha,
  selecionada,
  camposIdentificacao,
  camposDadosBasicos,
  onIdentificacaoCommit,
  onDadoBasicoDeCommit,
  onDadoBasicoParaCommit,
  onRemover,
  onToggleSelecao,
  onColar,
}: {
  linha: LinhaSap
  selecionada: boolean
  camposIdentificacao: CampoSchema[]
  camposDadosBasicos: CampoSchema[]
  onIdentificacaoCommit: (id: string, campo: keyof MaterialEditavel, valor: string) => void
  onDadoBasicoDeCommit: (id: string, campo: string, valor: string) => void
  onDadoBasicoParaCommit: (id: string, campo: string, valor: string) => void
  onRemover: (id: string) => void
  onToggleSelecao: (id: string) => void
  onColar: (id: string, texto: string) => Promise<boolean>
}) {
  async function handlePaste(e: ClipboardEvent<HTMLInputElement>) {
    const texto = e.clipboardData.getData('text')
    if (await onColar(linha._id, texto)) e.preventDefault()
  }

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
      {camposIdentificacao.map((campo) => {
        const valor = String(linha[campo.key as keyof MaterialEditavel] ?? '')
        const erro = campo.key === 'centro' && valor !== '' && valor !== '2001' && valor !== '2005'
          ? 'Centro esperado: 2001 ou 2005'
          : null
        return (
          <td key={campo.key} className="p-1.5">
            <CelulaTexto
              valor={valor}
              onCommit={(valor) => onIdentificacaoCommit(linha._id, campo.key as keyof MaterialEditavel, valor)}
              onPaste={handlePaste}
              erro={erro}
            />
          </td>
        )
      })}
      {camposDadosBasicos.map((campo) => {
        const valorDe = linha.alteracoes.dados_basicos[campo.key]?.de ?? ''
        const valorPara = linha.alteracoes.dados_basicos[campo.key]?.para ?? ''
        return (
          <Fragment key={campo.key}>
            <td className="p-1.5">
              <CelulaTexto
                valor={valorDe}
                onCommit={(valor) => onDadoBasicoDeCommit(linha._id, campo.key, valor)}
                onPaste={handlePaste}
                erro={erroDominioCampo(campo.key, valorDe) ?? erroParIncompleto(valorDe, valorPara, 'de')}
              />
            </td>
            <td className="p-1.5">
              <CelulaTexto
                valor={valorPara}
                onCommit={(valor) => onDadoBasicoParaCommit(linha._id, campo.key, valor)}
                erro={erroDominioCampo(campo.key, valorPara) ?? erroParIncompleto(valorDe, valorPara, 'para')}
              />
            </td>
          </Fragment>
        )
      })}
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

export default function PreenchimentoCodigos({
  agenteConectado,
  onSujoChange,
}: {
  agenteConectado: boolean
  onSujoChange: (sujo: boolean) => void
}) {
  const { mongoId } = useParams<{ mongoId: string }>()
  const navigate = useNavigate()
  const [schema, setSchema] = useState<MateriaisSchema | null>(null)
  const [materiais, setMateriais] = useState<LinhaSap[]>([])
  const materiaisRef = useRef(materiais)
  const [conteudoExistente, setConteudoExistente] = useState<Record<string, unknown>>({})
  const [carregando, setCarregando] = useState(true)
  const [salvando, setSalvando] = useState(false)
  const [erro, setErro] = useState<string | null>(null)
  const [camposSelecionados, setCamposSelecionados] = useState<Set<string>>(new Set())
  const [buscaCampoDropdown, setBuscaCampoDropdown] = useState('')
  const [dropdownCamposAberto, setDropdownCamposAberto] = useState(false)
  const dropdownCamposRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (!dropdownCamposAberto) return
    function aoClicarFora(e: MouseEvent) {
      if (dropdownCamposRef.current && !dropdownCamposRef.current.contains(e.target as Node)) {
        setDropdownCamposAberto(false)
      }
    }
    document.addEventListener('mousedown', aoClicarFora)
    return () => document.removeEventListener('mousedown', aoClicarFora)
  }, [dropdownCamposAberto])
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
        const materiaisExistentes = ((resp.data.content.materiais as MaterialEditavel[] | undefined) ?? []).map(
          (m) => ({ ...normalizarMaterial(m), _id: crypto.randomUUID() }),
        )
        const temLinhaBranca = materiaisExistentes.some((m) => m.codigo_material === '')
        const carregados = temLinhaBranca ? materiaisExistentes : [...materiaisExistentes, novaLinhaSap()]
        materiaisRef.current = carregados
        setMateriais(carregados)
      })
      .catch(() => setErro('Não foi possível carregar os dados.'))
      .finally(() => setCarregando(false))
    return () => {
      cancelado = true
    }
  }, [mongoId])

  useEffect(() => {
    api
      .get<MateriaisSchema>('/bitins/schema/materiais')
      .then((resp) => {
        setSchema(resp.data)
        // Todos os campos visíveis por padrão (2026-07-23, pedido explícito: "nos filtros,
        // deixe sempre como padrão todos os filtros ativados") -- antes começava vazio (só
        // identificação), o engenheiro tinha que abrir o dropdown e marcar campo por campo
        // antes de colar/ver qualquer coisa preenchida.
        setCamposSelecionados(new Set(resp.data.dados_basicos.map((c) => c.key)))
      })
      .catch(() => {})
  }, [])

  const atualizarIdentificacao = useCallback((id: string, campo: keyof MaterialEditavel, valor: string) => {
    materiaisRef.current = materiaisRef.current.map((m) => (m._id === id ? { ...m, [campo]: valor } : m))
    setMateriais(materiaisRef.current)
    setSujo(true)
  }, [setSujo])

  const atualizarDadoBasicoDe = useCallback((id: string, campo: string, de: string) => {
    materiaisRef.current = materiaisRef.current.map((m) => {
      if (m._id !== id) return m
      const existente = m.alteracoes.dados_basicos[campo]
      return {
        ...m,
        alteracoes: {
          ...m.alteracoes,
          dados_basicos: { ...m.alteracoes.dados_basicos, [campo]: { de, para: existente?.para ?? '' } },
        },
      }
    })
    setMateriais(materiaisRef.current)
    setSujo(true)
  }, [setSujo])

  const atualizarDadoBasicoPara = useCallback((id: string, campo: string, para: string) => {
    materiaisRef.current = materiaisRef.current.map((m) => {
      if (m._id !== id) return m
      const existente = m.alteracoes.dados_basicos[campo]
      return {
        ...m,
        alteracoes: {
          ...m.alteracoes,
          dados_basicos: { ...m.alteracoes.dados_basicos, [campo]: { de: existente?.de ?? '', para } },
        },
      }
    })
    setMateriais(materiaisRef.current)
    setSujo(true)
  }, [setSujo])

  const removerLinha = useCallback((id: string) => {
    materiaisRef.current = materiaisRef.current.filter((m) => m._id !== id)
    setMateriais(materiaisRef.current)
    setSelecionadas((atual) => {
      if (!atual.has(id)) return atual
      const copia = new Set(atual)
      copia.delete(id)
      return copia
    })
    setSujo(true)
  }, [setSujo])

  const removerSelecionadas = useCallback(() => {
    const restantes = materiaisRef.current.filter((m) => !selecionadas.has(m._id))
    materiaisRef.current = restantes.length > 0 ? restantes : [novaLinhaSap()]
    setMateriais(materiaisRef.current)
    setSelecionadas(new Set())
    setSujo(true)
  }, [selecionadas, setSujo])

  function limparTudo() {
    if (!window.confirm('Limpar toda a tabela? Essa ação não pode ser desfeita.')) return
    materiaisRef.current = [novaLinhaSap()]
    setMateriais(materiaisRef.current)
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
    setSelecionadas((atual) => (atual.size === materiais.length ? new Set() : new Set(materiais.map((m) => m._id))))
  }

  const colarNaLinha = useCallback(async (id: string, texto: string) => {
    const pareceGradeSap = /  /.test(texto) || texto.trim().split(' ').length >= 10
    if (!texto.includes('\t') && !texto.includes('\n') && !pareceGradeSap) return false
    setErro(null)
    try {
      const resp = await api.post('/bitins/parse-sap-paste', { raw_text: texto })
      const brutos = resp.data.materiais as Array<
        Partial<MaterialEditavel> & { dados_basicos_atual?: Record<string, string> }
      >
      const novosMateriais = brutos.map(paraMaterialEditavel)
      if (novosMateriais.length > 0) {
        const indice = materiaisRef.current.findIndex((m) => m._id === id)
        if (indice !== -1) {
          const copia = [...materiaisRef.current]
          copia.splice(indice, 1, ...novosMateriais)
          if (copia.every((m) => m.codigo_material !== '')) copia.push(novaLinhaSap())
          materiaisRef.current = copia
          setMateriais(materiaisRef.current)
          setSujo(true)
        }
      }
    } catch {
      setErro('Não foi possível interpretar o texto colado.')
    }
    return true
  }, [setSujo])

  async function salvar() {
    if (document.activeElement instanceof HTMLElement) document.activeElement.blur()

    setErro(null)
    setSalvando(true)
    try {
      const materiaisAtuais = materiaisRef.current
      const materiaisPreenchidos = materiaisAtuais.filter((m) => m.codigo_material.trim() !== '')
      const payload = materiaisPreenchidos.map(({ _id, ...resto }) => resto)
      await api.post('/bitins/draft', {
        mongo_id: mongoId,
        content: { ...conteudoExistente, materiais: payload },
      })
      materiaisRef.current = [...materiaisPreenchidos, novaLinhaSap()]
      setMateriais(materiaisRef.current)
      setSujo(false)
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
    await salvar()
    navigate(`/bitins/${mongoId}`)
  }

  const camposIdentificacao = useMemo(
    () => (schema ? schema.identificacao.filter((campo) => !COLUNAS_IDENTIFICACAO_OCULTAS.has(campo.key)) : []),
    [schema],
  )

  const camposDadosBasicosFiltrados = useMemo(
    () => schema?.dados_basicos.filter((campo) => camposSelecionados.has(campo.key)) ?? [],
    [schema, camposSelecionados],
  )
  const buscaDropdownNormalizada = normalizar(buscaCampoDropdown.trim())
  const opcoesDropdown = useMemo(
    () =>
      buscaDropdownNormalizada
        ? (schema?.dados_basicos.filter((campo) => normalizar(campo.label).includes(buscaDropdownNormalizada)) ?? [])
        : (schema?.dados_basicos ?? []),
    [schema, buscaDropdownNormalizada],
  )

  if (carregando || !schema) {
    return <p className="text-sm text-ink-muted">Carregando...</p>
  }

  return (
    <>
      <div className="mt-3 flex flex-wrap items-center gap-3">
        <AjudaPopover titulo="Hint">
          <p>Cole em qualquer célula da linha o valor que vem da ZBPP009.</p>
          <p>
            Cada campo tem 2 colunas lado a lado -- ex. <strong>Descrição</strong> (como está
            hoje no SAP) e <strong>Descrição nova</strong> (o que muda). Os dois continuam
            editáveis também na aba BITin, nenhuma tela depende da outra.
          </p>
          <p>
            <strong>Salvar</strong> grava sem sair da tela. <strong>Importar pra BITin</strong>{' '}
            salva e leva direto pra aba BITin, com os materiais já prontos.
          </p>
          <p>O campo de busca acima da tabela filtra as colunas pelo nome, pra achar mais rápido entre os ~30 campos.</p>
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
      <ErrosEnvioBanner erros={errosEnvio} />

      <Card title="Materiais">
        <div className="mt-4 flex flex-wrap items-center gap-2 rounded-lg bg-surface-alt px-3 py-2">
          <div ref={dropdownCamposRef} className="relative">
            <button
              type="button"
              onClick={() => setDropdownCamposAberto((v) => !v)}
              className="rounded-lg border border-line bg-surface px-3 py-1.5 text-sm text-ink hover:bg-surface-alt"
            >
              Campos visíveis {camposSelecionados.size > 0 ? `(${camposSelecionados.size})` : ''}
            </button>
            {dropdownCamposAberto && (
              <div className="absolute left-0 top-9 z-30 w-72 rounded-lg border border-line bg-surface p-2 shadow-lg">
                <input
                  type="text"
                  value={buscaCampoDropdown}
                  onChange={(e) => setBuscaCampoDropdown(e.target.value)}
                  placeholder="Achar campo (ex.: nível revisão)..."
                  className="mb-2 w-full rounded border border-line bg-surface px-2 py-1 text-sm text-ink placeholder:text-ink-faint"
                />
                <div className="max-h-72 overflow-y-auto">
                  {opcoesDropdown.length === 0 && (
                    <p className="px-1 py-1 text-sm text-ink-faint">Nenhum campo encontrado.</p>
                  )}
                  {opcoesDropdown.map((campo) => (
                    <label key={campo.key} className="flex items-center gap-2 rounded px-1 py-1 text-sm text-ink hover:bg-surface-alt">
                      <input
                        type="checkbox"
                        checked={camposSelecionados.has(campo.key)}
                        onChange={(e) =>
                          setCamposSelecionados((atual) => {
                            const novo = new Set(atual)
                            if (e.target.checked) novo.add(campo.key)
                            else novo.delete(campo.key)
                            return novo
                          })
                        }
                        className="rounded border-line text-brand-navy focus:ring-brand-navy/20"
                      />
                      {campo.label}
                    </label>
                  ))}
                </div>
                <div className="mt-2 flex gap-2">
                  <button
                    type="button"
                    onClick={() => setCamposSelecionados(new Set(schema?.dados_basicos.map((c) => c.key) ?? []))}
                    className="flex-1 rounded border border-line px-2 py-1 text-xs font-medium text-ink-muted hover:bg-surface-alt"
                  >
                    Selecionar todos
                  </button>
                  {camposSelecionados.size > 0 && (
                    <button
                      type="button"
                      onClick={() => setCamposSelecionados(new Set())}
                      className="flex-1 rounded border border-line px-2 py-1 text-xs font-medium text-ink-muted hover:bg-surface-alt"
                    >
                      Limpar seleção
                    </button>
                  )}
                </div>
              </div>
            )}
          </div>
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
              materiaisRef.current = [...materiaisRef.current, novaLinhaSap()]
              setMateriais(materiaisRef.current)
              setSujo(true)
            }}
            className="ml-auto rounded-lg border border-dashed border-line px-3 py-1.5 text-xs font-medium text-ink-muted hover:bg-surface"
          >
            + Nova linha
          </button>
        </div>

        <div className="mt-2 overflow-x-auto rounded border border-line">
          <table className="w-full text-left text-sm">
            <thead>
              <tr className="bg-surface-alt text-xs uppercase tracking-wide text-ink-muted">
                <th className="w-8 px-3 py-2">
                  <input
                    type="checkbox"
                    checked={materiais.length > 0 && selecionadas.size === materiais.length}
                    onChange={alternarSelecaoTodas}
                    aria-label="Selecionar todas as linhas"
                  />
                </th>
                {camposIdentificacao.map((campo) => (
                  <th key={campo.key} className="whitespace-nowrap px-3 py-2 font-medium">
                    {campo.label}
                  </th>
                ))}
                {camposDadosBasicosFiltrados.map((campo) => (
                  <Fragment key={campo.key}>
                    <th className="whitespace-nowrap px-3 py-2 font-medium">{campo.label}</th>
                    <th className="whitespace-nowrap px-3 py-2 font-medium">
                      {campo.label} {GENERO_NOVO[campo.key] ?? 'novo'}
                    </th>
                  </Fragment>
                ))}
                <th className="w-10" />
              </tr>
            </thead>
            <tbody className="divide-y divide-line">
              {materiais.map((linha) => (
                <LinhaSapRow
                  key={linha._id}
                  linha={linha}
                  selecionada={selecionadas.has(linha._id)}
                  camposIdentificacao={camposIdentificacao}
                  camposDadosBasicos={camposDadosBasicosFiltrados}
                  onIdentificacaoCommit={atualizarIdentificacao}
                  onDadoBasicoDeCommit={atualizarDadoBasicoDe}
                  onDadoBasicoParaCommit={atualizarDadoBasicoPara}
                  onRemover={removerLinha}
                  onToggleSelecao={alternarSelecao}
                  onColar={colarNaLinha}
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
