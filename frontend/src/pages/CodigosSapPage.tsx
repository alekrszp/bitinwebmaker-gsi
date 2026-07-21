import { Fragment, memo, useCallback, useEffect, useMemo, useRef, useState, type ClipboardEvent } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import Card from '../components/Card'
import AjudaPopover from '../components/bitin/AjudaPopover'
import AvisoSairModal from '../components/bitin/AvisoSairModal'
import EdicaoBottomBar from '../components/bitin/EdicaoBottomBar'
import ErrosEnvioBanner from '../components/bitin/ErrosEnvioBanner'
import StatusBadge from '../components/bitin/StatusBadge'
import { useAvisoSairSemSalvar } from '../hooks/useAvisoSairSemSalvar'
import { api } from '../lib/api'
import { materialVazio, normalizarMaterial } from '../lib/bitinDefaults'
import { useEnviarBitin } from '../lib/useEnviarBitin'
import type { Bitin, CampoSchema, MateriaisSchema, MaterialEditavel } from '../lib/types'

// Página própria (rota /bitins/:mongoId/codigos-sap, nome exibido "ZBPP009" desde 2026-07-15
// -- "vai ajudar o pessoal" a reconhecer, decisão do usuário) -- idêntica à aba ZBPP009 do
// documento original: uma tabela com TODOS os campos do material (identificação + os 30
// campos de dados_basicos, cada um com De E Para -- ver comentário em LinhaSapRow), pra colar
// do SAP ou digitar na mão. Colunas vêm do schema do backend (GET /bitins/schema/materiais),
// não hardcodadas (fonte única de verdade, ver docs/BACKEND.md).
//
// Colar do SAP (2026-07-15, reformulado; heurística de detecção ampliada em 2026-07-16): não
// é uma aba/painel separado -- o engenheiro cola em QUALQUER célula de uma linha em branco
// (não precisa ser a primeira), igual copiando/colando dentro do próprio Excel. Se o texto
// colado tem TAB (grade colada via Excel, célula por célula), várias linhas, ou "parece" uma
// linha da ZBPP009 colada direto do SAP GUI (sem TAB -- ver heurística em `colarNaLinha`), a
// colagem padrão do navegador é interceptada e o texto vai pro parser
// (`POST /bitins/parse-sap-paste`, reaproveita `sap_paste_parser.py` já testado) que já sabe a
// posição de cada campo -- 1 linha colada vira 1 material preenchido, N linhas coladas de uma
// vez viram N materiais, cada campo já cai na coluna certa (decisão do usuário: "ele cola em 1
// cria varias e já pega a posição certa de cada um, tem o mapeamento dos campos"). Colar um
// valor só e curto num campo isolado continua funcionando normal, sem interceptar nada.
// O parser só preenche o "de" (colar é sempre snapshot do SAP) -- o "para" fica em branco até
// o engenheiro digitar aqui do lado (ver campo De/Para abaixo).
//
// De/Para direto aqui (2026-07-17, pedido explícito: "coloca um campo do lado de cada campo
// que tem alteração") -- cada coluna de dados_basicos agora tem 2 inputs lado a lado. Antes só
// o "de" existia aqui (snapshot do SAP) e o "para" só podia ser declarado na aba BITin
// (MaterialEditorCard); as duas telas continuam operando sobre o MESMO
// materiais[].alteracoes.dados_basicos, nenhuma depende da outra -- só que agora dá pra
// declarar os dois direto na ZBPP009 também, sem precisar trocar de tela.
// "Tipo Material" fica visível aqui (2026-07-15, decisão do usuário: "na ZBPP009 pode
// deixar") -- só some no bloco da aba BITin (MaterialEditorCard), que é a tela que reflete a
// visualização enviada; aqui é a réplica da grade real do SAP, então o campo tem que aparecer
// igual à ZBPP009 de verdade.
// "descricao_material" oculto aqui (2026-07-17, achado revisando o grid De/Para: "descrição
// também pode ser alterada... descrição vai tanto quanto pra descrição do item e tanto quanto
// pra mostrar a alteração") -- `schema.dados_basicos` já tem um campo "descricao" próprio (De/
// Para, ver DADOS_BASICOS_LABELS em scripts/bitin_model.py), então a ZBPP009 mostrava DUAS
// colunas "Descrição" ao mesmo tempo (uma de identificação, sem par, e o "de" do par De/Para) --
// grade desigual/confusa. O par "Descrição"/"Descrição nova" abaixo passa a cobrir os dois
// papéis sozinho (a "de" É a descrição atual do item, exibida/identificada por ela mesma). O
// campo `descricao_material` continua existindo no modelo (usado como título do card na aba
// BITin, MaterialEditorCard.tsx) -- só não aparece mais como coluna própria aqui.
const COLUNAS_IDENTIFICACAO_OCULTAS = new Set<string>(['descricao_material'])

// Concordância de gênero pro sufixo da coluna "nova"/"novo" (2026-07-17, pedido explícito: "e
// ajeita quando é nova ou novo") -- "Descrição nova" está certo (feminino), mas "Volume nova"/
// "Documento nova" não (masculinos); um sufixo fixo pra todos os ~29 campos de dados_basicos
// erra a concordância na maioria deles. Mapeado campo a campo (mesmas chaves de
// scripts/bitin_model.py::DADOS_BASICOS_LABELS) pelo gênero do substantivo núcleo do rótulo em
// português; fallback "novo" (masculino, mais comum na lista) pra campo novo que apareça no
// crosswalk sem entrada aqui ainda.
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

// Grade de ~30+ colunas × N linhas -- otimização de performance (2026-07-17, pedido explícito:
// "usa como base o frontend antigo que tinha uma otimização feita", ver
// GPT_Engineering_BITIN/frontend/src/components/CodeForm.jsx). Cada linha ganha um `_id`
// client-side estável (nunca enviado ao backend, ver `salvar` abaixo) -- antes a tabela usava
// `key={i}` (índice), que perde a identidade da linha a cada remoção/colagem (splice), forçando
// remount de linhas que na verdade não mudaram. Com `_id` estável + `React.memo` na linha, uma
// tecla digitada numa célula só re-renderiza AQUELA linha, não a tabela inteira.
type LinhaSap = MaterialEditavel & { _id: string }

function novaLinhaSap(): LinhaSap {
  // tipo_material fica em branco aqui (2026-07-17, pedido explícito: "tira halb lá de padrão
  // na primeira linha, deixa tudo em branco") -- materialVazio() preenche "HALB" por padrão
  // pra atender ao campo obrigatório no envio (bitin_model.py) já que a aba BITin não tem
  // controle nenhum pra digitá-lo, mas aqui na ZBPP009 o campo aparece editável na coluna
  // "Tipo Material" (ver comentário acima), então não faz sentido pré-preencher um valor que
  // o engenheiro nunca pediu.
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

// Célula de texto memoizada com estado local (2026-07-17, mesmo padrão de CodeTableCell no
// CodeForm.jsx antigo) -- digitar não propaga pro estado da linha/tabela a cada tecla, só no
// blur (`onCommit`). Comparador padrão do React.memo (shallow) já resolve: só re-renderiza se
// `valor` mudar de fora (ex.: colagem de SAP substituindo a linha inteira) -- os callbacks são
// estáveis via useCallback no componente pai, então não disparam re-render por identidade nova.
const CelulaTexto = memo(function CelulaTexto({
  valor,
  onCommit,
  onPaste,
}: {
  valor: string
  onCommit: (novoValor: string) => void
  onPaste?: (e: ClipboardEvent<HTMLInputElement>) => void
}) {
  const [local, setLocal] = useState(valor)

  // Sincroniza se o valor mudar por outro meio que não digitação nesta célula (ex.: colagem de
  // SAP substitui a linha inteira, incluindo esta célula).
  useEffect(() => {
    setLocal(valor)
  }, [valor])

  return (
    <input
      type="text"
      value={local}
      onChange={(e) => setLocal(e.target.value)}
      onBlur={() => {
        if (local !== valor) onCommit(local)
      }}
      onPaste={onPaste}
      // w-full + min-w (2026-07-17, pedido explícito: "ta muito espaçado as células, se o nome
      // do campo for longo aumenta a célula junto") -- antes era largura fixa (w-28/112px)
      // pra TODA célula, então uma coluna com rótulo curto ("OC") ficava larga igual a uma com
      // rótulo longo ("Marcação eliminar nível mandante") só porque o cabeçalho (sem quebra de
      // linha) forçava a coluna a crescer, sobrando espaço vazio ao redor do input. Sem
      // largura fixa, o input preenche a coluna inteira (que já cresce/encolhe sozinha
      // acompanhando o texto do cabeçalho) -- min-w só evita ficar pequeno demais pra digitar.
      className="w-full min-w-[5rem] rounded border border-line bg-surface px-2 py-1.5 text-sm text-ink focus:border-brand-navy focus:outline-none"
    />
  )
})

// Linha memoizada (2026-07-17, mesmo padrão de CodeTableRow no CodeForm.jsx antigo). `linha` só
// muda de referência quando ELA MESMA é editada (atualizarIdentificacao/atualizarDadoBasicoDe/
// atualizarDadoBasicoPara usam `.map` que preserva a referência das linhas não tocadas) --
// então editar a linha 5 não re-renderiza as linhas 1-4 e 6-N, mesmo a tabela tendo centenas
// de linhas.
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
      {/* Centro voltou a ser texto livre aqui (2026-07-17, pedido explícito: "tem uma dropbar
          no centro? tira isso") -- a restrição a 2001/2005 continua valendo na aba BITin
          (MaterialEditorCard.tsx), mas a ZBPP009 é a réplica da grade real do SAP, então o
          campo aqui aceita qualquer coisa que o engenheiro cole/digite, igual antes. */}
      {camposIdentificacao.map((campo) => (
        <td key={campo.key} className="p-1.5">
          <CelulaTexto
            valor={String(linha[campo.key as keyof MaterialEditavel] ?? '')}
            onCommit={(valor) => onIdentificacaoCommit(linha._id, campo.key as keyof MaterialEditavel, valor)}
            onPaste={handlePaste}
          />
        </td>
      ))}
      {/* De/Para lado a lado (2026-07-17) -- ver comentário no topo do arquivo. */}
      {camposDadosBasicos.map((campo) => (
        <Fragment key={campo.key}>
          <td className="p-1.5">
            <CelulaTexto
              valor={linha.alteracoes.dados_basicos[campo.key]?.de ?? ''}
              onCommit={(valor) => onDadoBasicoDeCommit(linha._id, campo.key, valor)}
              onPaste={handlePaste}
            />
          </td>
          <td className="p-1.5">
            <CelulaTexto
              valor={linha.alteracoes.dados_basicos[campo.key]?.para ?? ''}
              onCommit={(valor) => onDadoBasicoParaCommit(linha._id, campo.key, valor)}
            />
          </td>
        </Fragment>
      ))}
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

export default function CodigosSapPage() {
  const { mongoId } = useParams<{ mongoId: string }>()
  const navigate = useNavigate()
  const [bitin, setBitin] = useState<Bitin | null>(null)
  const [schema, setSchema] = useState<MateriaisSchema | null>(null)
  const [materiais, setMateriais] = useState<LinhaSap[]>([])
  // Espelho síncrono de `materiais` (2026-07-21, mesmo bug real corrigido em
  // ListaTecnicaPage.tsx): `salvar()` lia o estado via um "capturar dentro do updater do
  // setState" logo após forçar o blur do campo focado -- não é garantido rodar a tempo (achado
  // ao vivo com Playwright: `POST /bitins/draft` saía sem o material que tinha acabado de ser
  // editado). `materiaisRef.current` é escrito direto em cada mutador abaixo, então está
  // sempre correto no instante em que `salvar()` lê.
  const materiaisRef = useRef(materiais)
  const [conteudoExistente, setConteudoExistente] = useState<Record<string, unknown>>({})
  const [carregando, setCarregando] = useState(true)
  const [salvando, setSalvando] = useState(false)
  const [erro, setErro] = useState<string | null>(null)
  // Seleção por _id estável, não índice (2026-07-17) -- índice desloca a cada remoção/colagem,
  // podia selecionar a linha errada depois de uma edição.
  const [selecionadas, setSelecionadas] = useState<Set<string>>(new Set())
  const { enviando, errosEnvio, bitinEnviado, enviar } = useEnviarBitin(mongoId)
  // Aviso de alterações não salvas (2026-07-17, pedido explícito) -- ver
  // hooks/useAvisoSairSemSalvar.ts.
  const { setSujo, mostrarModal, setMostrarModal, tentarSair } = useAvisoSairSemSalvar()

  // Envio bem-sucedido navega direto pra aba BITin, já travada em modo enviado (2026-07-16,
  // mesma ideia de "Importar pra BITin" -- useEnviarBitin não navega mais sozinho, ver
  // lib/useEnviarBitin.ts).
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
        setBitin(resp.data)
        setConteudoExistente(resp.data.content)
        const materiaisExistentes = ((resp.data.content.materiais as MaterialEditavel[] | undefined) ?? []).map(
          (m) => ({ ...normalizarMaterial(m), _id: crypto.randomUUID() }),
        )
        // Sempre sobra pelo menos uma linha em branco no FINAL pra colar -- não obriga clicar
        // em "+ Nova linha" primeiro, e principalmente não deixa colar em cima de um material
        // que já existe (bug real encontrado em 2026-07-15: colar na "primeira célula" com
        // materiais já salvos sobrescrevia o primeiro material em vez de criar um novo,
        // porque não havia linha em branco nenhuma pra receber a colagem).
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
      .then((resp) => setSchema(resp.data))
      .catch(() => {})
  }, [])

  // useCallback (2026-07-17) -- identidade estável entre renders é o que permite o
  // React.memo de LinhaSapRow/CelulaTexto pular re-render de linhas não tocadas (ver
  // comentário em LinhaSapRow acima). Todas operam por `_id`, não índice.
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

  // Barra de ferramentas acima da tabela (2026-07-16, decisão do usuário: "esse X ta muito
  // longe, coloca ali no cabeçalho em cima da tabela uma barra de ferramentas de manipulação")
  // -- seleção múltipla via checkbox por linha substitui ter que clicar em cada "×" um por um
  // pra remover vários materiais.
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

  // Cole em QUALQUER célula da linha (não precisa ser a primeira -- corrigido em 2026-07-15,
  // bug real: o interceptador só estava plugado na 1ª coluna de identificação, mas essa deixou
  // de ser "Tipo Material" quando o campo foi reordenado, então colar em "Tipo Material" (hoje a
  // última coluna de identificação) caía no paste padrão do navegador e despejava o texto
  // inteiro, cru, num campo só -- "mapeamento errado, vai tudo errado"). Se o texto tem TAB
  // (grade colada via Excel), várias linhas, ou parece uma linha da ZBPP009 colada direto do
  // SAP GUI sem TAB (heurística de espaço, ver abaixo, bug real 2026-07-16: cola direta do SAP
  // GUI não tem TAB nenhum), vira N materiais prontos, cada campo já na posição certa;
  // substitui a linha onde colou e mantém uma linha em branco no final pra continuar colando.
  // Colar um valor único curto não intercepta nada -- o navegador cola normal, célula a célula.
  const colarNaLinha = useCallback(async (id: string, texto: string) => {
    // Cola direta do SAP GUI (sem passar pelo Excel) não tem TAB nenhum -- caso real do
    // usuário, 2026-07-16: as 36 colunas da ZBPP009 vêm separadas por espaço simples numa
    // única linha (sem \n também, se for só 1 material). Sem TAB/\n pra detectar, a
    // heurística usada é: 2+ espaços consecutivos (colunas em branco entre valores, típico
    // de grade tabular) OU 10+ tokens separados por espaço simples (uma linha real da
    // ZBPP009 tem ~36 campos; um texto digitado à mão num campo só dificilmente chega
    // nisso). Trade-off aceito: uma colagem legítima de texto livre longo (10+ palavras)
    // num campo só seria mal-interpretada como colagem de SAP -- risco baixo pra este
    // formulário (campos são todos curtos/códigos), e o pior caso é o texto ir pro parser
    // e a linha ficar com poucas colunas preenchidas, não uma perda de dado silenciosa.
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
    // Força o commit do blur ANTES de ler o estado -- células de texto só propagam pro estado
    // da linha no blur (ver CelulaTexto acima). `materiaisRef.current` (2026-07-21, mesmo bug
    // real corrigido em ListaTecnicaPage.tsx -- ver comentário na declaração do ref acima) é
    // escrito direto pelos mutadores, então já está atualizado assim que o blur síncrono roda.
    if (document.activeElement instanceof HTMLElement) document.activeElement.blur()

    setErro(null)
    setSalvando(true)
    try {
      const materiaisAtuais = materiaisRef.current

      // A linha em branco no final é só espaço pra continuar colando/digitando -- nunca é
      // persistida como material de verdade (bug real encontrado em 2026-07-15: virava um
      // "material fantasma" sem código, disparando erros de validação bobos no envio).
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

  // "Importar" (2026-07-15): salva e volta direto pra aba BITin, onde os materiais colados/
  // digitados aqui já aparecem prontos (checklist/setores recalculados) -- decisão do
  // usuário: "tudo oque ele fizeram ali faz a automação e completa direto la na tela de
  // BITin". "Salvar" continua existindo pra quem quer ficar nesta tela colando mais linhas.
  async function importar() {
    await salvar()
    navigate(`/bitins/${mongoId}`)
  }

  // useMemo (2026-07-17) -- antes recalculado com .filter() inline no JSX a cada render
  // (2 vezes: cabeçalho e cada linha), sem depender de nada que muda por digitação. Também dá
  // ao React.memo de LinhaSapRow uma referência estável de array pra comparar.
  const camposIdentificacao = useMemo(
    () => (schema ? schema.identificacao.filter((campo) => !COLUNAS_IDENTIFICACAO_OCULTAS.has(campo.key)) : []),
    [schema],
  )

  if (carregando || !schema) {
    return <p className="text-sm text-ink-muted">Carregando...</p>
  }

  return (
    <div className="mx-auto max-w-[1600px] pb-24">
      {/* Intercepta o clique se houver alteração não salva (2026-07-17, ver
          hooks/useAvisoSairSemSalvar.ts) -- botão em vez de Link, senão navegaria antes de
          dar chance de mostrar o modal. */}
      <button
        type="button"
        onClick={() => {
          if (tentarSair()) navigate(`/bitins/${mongoId}`)
        }}
        className="text-sm text-ink-muted hover:text-ink hover:underline"
      >
        ← Voltar pro BITin
      </button>

      {mostrarModal && (
        <AvisoSairModal
          salvando={salvando}
          onCancelar={() => setMostrarModal(false)}
          onSairSemSalvar={() => navigate(`/bitins/${mongoId}`)}
          onSalvarESair={async () => {
            const ok = await salvar()
            if (ok) navigate(`/bitins/${mongoId}`)
          }}
        />
      )}

      <div className="mt-3 flex flex-wrap items-center gap-3">
        <h1 className="text-2xl font-semibold text-ink">{bitin?.codigo || 'Rascunho sem código'}</h1>
        {bitin && <StatusBadge status={bitin.status} windchillEnviado={bitin.windchill_enviado} />}
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
            Cada campo tem 2 colunas lado a lado -- ex. <strong>Descrição</strong> (como está
            hoje no SAP) e <strong>Descrição nova</strong> (o que muda). Os dois continuam
            editáveis também na aba BITin, nenhuma tela depende da outra.
          </p>
          <p>
            <strong>Salvar</strong> grava sem sair da tela. <strong>Importar pra BITin</strong>{' '}
            salva e leva direto pra aba BITin, com os materiais já prontos.
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
              {/* Cabeçalho de 1 linha só (2026-07-17, revisado -- era 2 linhas com "De"/"Para"
                  genérico embaixo, trocado a pedido do usuário): cada campo de dados_basicos
                  vira 2 colunas com nome próprio, ex. "Descrição" e "Descrição nova", em vez de
                  um rótulo agrupado + sub-rótulo. */}
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
                {schema.dados_basicos.map((campo) => (
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
                  camposDadosBasicos={schema.dados_basicos}
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

      {mongoId && <EdicaoBottomBar mongoId={mongoId} enviando={enviando || salvando} onEnviar={handleEnviar} />}
    </div>
  )
}
