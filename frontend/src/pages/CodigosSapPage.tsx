import { useEffect, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import Card from '../components/Card'
import AjudaPopover from '../components/bitin/AjudaPopover'
import EdicaoBottomBar from '../components/bitin/EdicaoBottomBar'
import ErrosEnvioBanner from '../components/bitin/ErrosEnvioBanner'
import StatusBadge from '../components/bitin/StatusBadge'
import { api } from '../lib/api'
import { materialVazio, normalizarMaterial } from '../lib/bitinDefaults'
import { useEnviarBitin } from '../lib/useEnviarBitin'
import type { Bitin, MateriaisSchema, MaterialEditavel } from '../lib/types'

// Página própria (rota /bitins/:mongoId/codigos-sap, nome exibido "ZBPP009" desde 2026-07-15
// -- "vai ajudar o pessoal" a reconhecer, decisão do usuário) -- idêntica à aba ZBPP009 do
// documento original: uma tabela com TODOS os campos do material (identificação + os 30
// campos de dados_basicos), pra colar do SAP ou digitar na mão -- sem indicadores nem De/Para
// aqui. Colunas vêm do schema do backend (GET /bitins/schema/materiais), não hardcodadas
// (fonte única de verdade, ver docs/BACKEND.md).
//
// Colar do SAP (2026-07-15, reformulado): não é uma aba/painel separado -- o engenheiro cola
// em QUALQUER célula de uma linha em branco (não precisa ser a primeira), igual copiando/
// colando dentro do próprio Excel. Se o texto colado tem TAB (grade real do SAP GUI, célula por
// célula) ou várias linhas, a colagem padrão do navegador é interceptada e o texto vai pro
// parser (`POST /bitins/parse-sap-paste`, reaproveita `sap_paste_parser.py` já testado) que
// já sabe a posição de cada campo -- 1 linha colada vira 1 material preenchido, N linhas
// coladas de uma vez viram N materiais, cada campo já cai na coluna certa (decisão do
// usuário: "ele cola em 1 cria varias e já pega a posição certa de cada um, tem o mapeamento
// dos campos"). Colar um valor só (sem TAB) num campo isolado funciona normal, sem interceptar
// nada.
//
// O que é colado/digitado aqui vira o "de" de materiais[].alteracoes.dados_basicos -- o
// snapshot atual do material, exatamente como está no SAP. O "para" (o que muda) só é
// declarado depois, na aba "BITin", material por material -- as duas telas operam sobre o
// mesmo materiais[] do JSON, nenhuma depende da outra.
// "Tipo Material" fica visível aqui (2026-07-15, decisão do usuário: "na ZBPP009 pode
// deixar") -- só some no bloco da aba BITin (MaterialEditorCard), que é a tela que reflete a
// visualização enviada; aqui é a réplica da grade real do SAP, então o campo tem que aparecer
// igual à ZBPP009 de verdade.
const COLUNAS_IDENTIFICACAO_OCULTAS = new Set<string>([])

function paraMaterialEditavel(bruto: Partial<MaterialEditavel> & { dados_basicos_atual?: Record<string, string> }): MaterialEditavel {
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
  }
}

export default function CodigosSapPage() {
  const { mongoId } = useParams<{ mongoId: string }>()
  const navigate = useNavigate()
  const [bitin, setBitin] = useState<Bitin | null>(null)
  const [schema, setSchema] = useState<MateriaisSchema | null>(null)
  const [materiais, setMateriais] = useState<MaterialEditavel[]>([])
  const [conteudoExistente, setConteudoExistente] = useState<Record<string, unknown>>({})
  const [carregando, setCarregando] = useState(true)
  const [salvando, setSalvando] = useState(false)
  const [erro, setErro] = useState<string | null>(null)
  const { enviando, errosEnvio, enviar } = useEnviarBitin(mongoId)

  useEffect(() => {
    if (!mongoId) return
    let cancelado = false
    api
      .get<Bitin>(`/bitins/${mongoId}`)
      .then((resp) => {
        if (cancelado) return
        setBitin(resp.data)
        setConteudoExistente(resp.data.content)
        const materiaisExistentes = ((resp.data.content.materiais as MaterialEditavel[] | undefined) ?? []).map(normalizarMaterial)
        // Sempre sobra pelo menos uma linha em branco no FINAL pra colar -- não obriga clicar
        // em "+ Nova linha" primeiro, e principalmente não deixa colar em cima de um material
        // que já existe (bug real encontrado em 2026-07-15: colar na "primeira célula" com
        // materiais já salvos sobrescrevia o primeiro material em vez de criar um novo,
        // porque não havia linha em branco nenhuma pra receber a colagem).
        const temLinhaBranca = materiaisExistentes.some((m) => m.codigo_material === '')
        setMateriais(temLinhaBranca ? materiaisExistentes : [...materiaisExistentes, materialVazio()])
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
      .then((resp) => setSchema(resp.data))
      .catch(() => {})
  }, [])

  function atualizarIdentificacao(index: number, campo: keyof MaterialEditavel, valor: string) {
    setMateriais((atual) => atual.map((m, i) => (i === index ? { ...m, [campo]: valor } : m)))
  }

  function atualizarDadoBasicoDe(index: number, campo: string, de: string) {
    setMateriais((atual) =>
      atual.map((m, i) => {
        if (i !== index) return m
        const existente = m.alteracoes.dados_basicos[campo]
        return {
          ...m,
          alteracoes: {
            ...m.alteracoes,
            dados_basicos: { ...m.alteracoes.dados_basicos, [campo]: { de, para: existente?.para ?? '' } },
          },
        }
      }),
    )
  }

  function removerLinha(index: number) {
    setMateriais((atual) => atual.filter((_, i) => i !== index))
  }

  // Cole em QUALQUER célula da linha (não precisa ser a primeira -- corrigido em 2026-07-15,
  // bug real: o interceptador só estava plugado na 1ª coluna de identificação, mas essa deixou
  // de ser "Tipo Material" quando o campo foi reordenado, então colar em "Tipo Material" (hoje a
  // última coluna de identificação) caía no paste padrão do navegador e despejava o texto
  // inteiro, cru, num campo só -- "mapeamento errado, vai tudo errado"). Se o texto tem TAB
  // (grade do SAP GUI colada célula por célula) ou várias linhas, vira N materiais prontos,
  // cada campo já na posição certa; substitui a linha onde colou e mantém uma linha em branco
  // no final pra continuar colando. Colar um valor único (sem TAB) não intercepta nada -- o
  // navegador cola normal, célula a célula.
  async function colarNaLinha(index: number, texto: string) {
    if (!texto.includes('\t') && !texto.includes('\n')) return false
    setErro(null)
    try {
      const resp = await api.post('/bitins/parse-sap-paste', { raw_text: texto })
      const brutos = resp.data.materiais as Array<
        Partial<MaterialEditavel> & { dados_basicos_atual?: Record<string, string> }
      >
      const novosMateriais = brutos.map(paraMaterialEditavel)
      if (novosMateriais.length > 0) {
        setMateriais((atual) => {
          const copia = [...atual]
          copia.splice(index, 1, ...novosMateriais)
          if (copia.every((m) => m.codigo_material !== '')) copia.push(materialVazio())
          return copia
        })
      }
    } catch {
      setErro('Não foi possível interpretar o texto colado.')
    }
    return true
  }

  async function salvar() {
    setErro(null)
    setSalvando(true)
    try {
      // A linha em branco no final é só espaço pra continuar colando/digitando -- nunca é
      // persistida como material de verdade (bug real encontrado em 2026-07-15: virava um
      // "material fantasma" sem código, disparando erros de validação bobos no envio).
      const materiaisPreenchidos = materiais.filter((m) => m.codigo_material.trim() !== '')
      await api.post('/bitins/draft', {
        mongo_id: mongoId,
        content: { ...conteudoExistente, materiais: materiaisPreenchidos },
      })
      setMateriais([...materiaisPreenchidos, materialVazio()])
    } catch {
      setErro('Não foi possível salvar. Tente novamente.')
    } finally {
      setSalvando(false)
    }
  }

  async function handleEnviar() {
    await salvar()
    await enviar()
  }

  // "Importar" (2026-07-15): salva e volta direto pra aba BITin, onde os materiais colados/
  // digitados aqui já aparecem prontos (checklist/setores recalculados) -- decisão do
  // usuário: "tudo oque ele fizeram ali faz a automação e completa direto la na tela de
  // BITin". "Salvar" continua existindo pra quem quer ficar nesta tela colando mais linhas.
  async function importar() {
    await salvar()
    navigate(`/bitins/${mongoId}`)
  }

  if (carregando || !schema) {
    return <p className="text-sm text-ink-muted">Carregando...</p>
  }

  return (
    <div className="mx-auto max-w-[1600px] pb-24">
      <Link to={`/bitins/${mongoId}`} className="text-sm text-ink-muted hover:text-ink hover:underline">
        ← Voltar pro BITin
      </Link>

      <div className="mt-3 flex flex-wrap items-center gap-3">
        <h1 className="text-2xl font-semibold text-ink">{bitin?.codigo || 'Rascunho sem código'}</h1>
        {bitin && <StatusBadge status={bitin.status} />}
        <span className="text-sm text-ink-muted">— ZBPP009</span>
        <AjudaPopover titulo="Como usar a ZBPP009">
          <p>
            Cole em <strong>qualquer célula</strong> da linha um trecho copiado do SAP -- se tiver
            TAB ou várias linhas, o sistema reconhece e distribui cada valor na coluna certa
            automaticamente (não precisa colar na primeira célula). Colar um valor isolado se
            comporta como colar normal, só naquele campo. Sempre sobra uma linha em branco no
            final pra continuar colando; "+ Nova linha" adiciona espaço extra.
          </p>
          <p>
            <strong>Salvar</strong> grava sem sair da tela. <strong>Importar pra BITin</strong>{' '}
            salva e leva direto pra aba BITin, com os materiais já prontos. A grade é
            compartilhada entre as duas telas -- nenhuma depende da outra.
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
      <ErrosEnvioBanner erros={errosEnvio} />

      <Card title="Materiais">
        <div className="mt-4 overflow-x-auto rounded border border-line">
          <table className="w-full text-left text-sm">
            <thead>
              <tr className="bg-surface-alt text-xs uppercase tracking-wide text-ink-muted">
                {schema.identificacao
                  .filter((campo) => !COLUNAS_IDENTIFICACAO_OCULTAS.has(campo.key))
                  .map((campo) => (
                    <th key={campo.key} className="whitespace-nowrap px-3 py-2 font-medium">
                      {campo.label}
                    </th>
                  ))}
                {schema.dados_basicos.map((campo) => (
                  <th key={campo.key} className="whitespace-nowrap px-3 py-2 font-medium">
                    {campo.label}
                  </th>
                ))}
                <th className="w-10" />
              </tr>
            </thead>
            <tbody className="divide-y divide-line">
              {materiais.map((m, i) => (
                <tr key={i}>
                  {schema.identificacao
                    .filter((campo) => !COLUNAS_IDENTIFICACAO_OCULTAS.has(campo.key))
                    .map((campo) => (
                      <td key={campo.key} className="p-1.5">
                        <input
                          type="text"
                          value={String(m[campo.key as keyof MaterialEditavel] ?? '')}
                          onChange={(e) => atualizarIdentificacao(i, campo.key as keyof MaterialEditavel, e.target.value)}
                          onPaste={async (e) => {
                            const texto = e.clipboardData.getData('text')
                            if (await colarNaLinha(i, texto)) e.preventDefault()
                          }}
                          className="w-32 rounded border border-line bg-surface px-2 py-1.5 text-sm text-ink focus:border-brand-navy focus:outline-none"
                        />
                      </td>
                    ))}
                  {schema.dados_basicos.map((campo) => (
                    <td key={campo.key} className="p-1.5">
                      <input
                        type="text"
                        value={m.alteracoes.dados_basicos[campo.key]?.de ?? ''}
                        onChange={(e) => atualizarDadoBasicoDe(i, campo.key, e.target.value)}
                        onPaste={async (e) => {
                          const texto = e.clipboardData.getData('text')
                          if (await colarNaLinha(i, texto)) e.preventDefault()
                        }}
                        className="w-32 rounded border border-line bg-surface px-2 py-1.5 text-sm text-ink focus:border-brand-navy focus:outline-none"
                      />
                    </td>
                  ))}
                  <td className="p-1.5 text-center">
                    <button
                      type="button"
                      onClick={() => removerLinha(i)}
                      className="text-ink-faint hover:text-red-600"
                      aria-label="Remover linha"
                    >
                      ×
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <button
          type="button"
          onClick={() => setMateriais((atual) => [...atual, materialVazio()])}
          className="mt-3 rounded-lg border border-dashed border-line px-4 py-2 text-sm font-medium text-ink-muted hover:bg-surface-alt"
        >
          + Nova linha
        </button>
      </Card>

      {mongoId && <EdicaoBottomBar mongoId={mongoId} enviando={enviando || salvando} onEnviar={handleEnviar} />}
    </div>
  )
}
