import { useCallback, useEffect, useRef, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import AgenteConexaoToast from '../components/bitin/AgenteConexaoToast'
import AgenteGate from '../components/bitin/AgenteGate'
import AjudaPopover from '../components/bitin/AjudaPopover'
import AvisoSairModal from '../components/bitin/AvisoSairModal'
import DadosGeraisCard from '../components/bitin/DadosGeraisCard'
import EdicaoBottomBar from '../components/bitin/EdicaoBottomBar'
import ErrosEnvioBanner from '../components/bitin/ErrosEnvioBanner'
import HistoricoCard from '../components/bitin/HistoricoCard'
import InstalarAgenteCard from '../components/bitin/InstalarAgenteCard'
import MateriaisSection from '../components/bitin/MateriaisSection'
import OrdemClienteEditor from '../components/bitin/OrdemClienteEditor'
import OrdemClienteSection from '../components/bitin/OrdemClienteSection'
import StatusBadge from '../components/bitin/StatusBadge'
import { useAgenteSapConectado } from '../hooks/useAgenteSapConectado'
import { useAuth } from '../hooks/useAuth'
import { useAvisoSairSemSalvar } from '../hooks/useAvisoSairSemSalvar'
import { useFaviconAgente } from '../hooks/useFaviconAgente'
import { useVoltar } from '../hooks/useVoltar'
import { api } from '../lib/api'
import { materialVazio, normalizarMaterial } from '../lib/bitinDefaults'
import type { BitinResumo } from '../lib/bitinTypes'
import { duplicarBitinENavegar } from '../lib/duplicarBitin'
import { SETOR_ENGENHARIA, ehDoSetor, isAdmin } from '../lib/permissions'
import { bitinEscolheuManual, marcarBitinManual } from '../lib/preferenciasAgente'
import { identificarUsuarioNoAgente } from '../lib/sapAgent'
import { useEnviarBitin } from '../lib/useEnviarBitin'
import type { Bitin, MateriaisSchema, MaterialEditavel, OrdemClienteEditavel, Subgrupo } from '../lib/types'

// Visualização e edição são a mesma tela (decisão do usuário, 2026-07-14): "clicar num BITin
// em rascunho já abre editável, não é mais só visualização". Um BITin enviado usa a mesma
// estrutura, só que travada (sem inputs). Sempre chega aqui com mongoId -- "+ Novo BITin" já
// cria o rascunho antes de navegar (ver lib/criarBitin.ts); não existe mais um caminho "em
// branco" nesta página (2026-07-16, pedido do usuário: "quando tu clicka em novo bitin tem
// uma tela que não aparece as abas e nem checklist etc... tira essa tela de ter que salvar o
// bitin pra ele aparecer, quando clicka em novo bitin ja abre direto na aba que tem as 3
// telas etc.").
//
// GET /bitins/{mongo_id}/resumo (scripts/bitin_view.py::render_bitin_summary) continua sendo
// a fonte dos dados legíveis (checklist, setores acionados, indicadores, diffs) pro modo
// só-leitura -- não reimplementado aqui. GET /bitins/{mongo_id} traz o content bruto (editável)
// + pode_editar.
//
// Aba "BITin" (2026-07-15, renomeada de "Dados gerais"): mesma estrutura da visualização
// quando enviado, só que editável -- código/centro/descrição/indicadores/alteração de dados
// básicos ficam todos num bloco por material (MaterialEditorCard, via MateriaisSection). O
// engenheiro pode cadastrar um material inteiro à mão nesta aba ("+ Novo material") sem nunca
// abrir Códigos SAP -- as duas telas leem/escrevem o mesmo materiais[] do JSON, nenhuma
// depende da outra (decisão do usuário: "tudo se conecta, tudo se complementa, nada depende
// de um do outro"). Depois de salvar, checklist/setores acionados são recalculados a partir
// do que foi declarado.
//
// Esta página só cuida de estado + carregamento/salvamento -- o layout fica nos componentes
// de components/bitin/ (DadosGeraisCard, MateriaisSection, etc.), decisão do usuário
// (2026-07-15: "não ta nada componentizado o bitindetail, ajusta isso").
//
// `_id` client-side estável por material (2026-07-17, otimização de performance -- mesmo
// padrão de LinhaSap em CodigosSapPage.tsx). `key={index}`/callbacks fechados sobre o índice
// faziam QUALQUER edição em QUALQUER material re-renderizar todos os MaterialEditorCard (via
// MateriaisSection), porque a callback passada pra cada card era uma closure NOVA a cada
// render (`(m) => onChangeMaterial(i, m)`), quebrando o React.memo mesmo se ele existisse.
// Com `_id` estável + callbacks por id (useCallback) + MaterialEditorCard memoizado, editar o
// material 5 não re-renderiza os outros N-1.
type MaterialComId = MaterialEditavel & { _id: string }

export default function BitinDetail() {
  const { mongoId } = useParams<{ mongoId: string }>()
  const navigate = useNavigate()
  // "Voltar" volta pra tela de onde o usuário realmente veio (CadastroPage, ProcessosPage,
  // PainelGeral, Settings "Bitins Concluídos", MeusBitins...) em vez de sempre cair em
  // "/bitins" fixo (2026-07-21, revisão de navegação -- ver hooks/useVoltar.ts).
  const voltar = useVoltar('/bitins')
  const { user } = useAuth()
  const { enviando, errosEnvio, bitinEnviado, enviar } = useEnviarBitin(mongoId)
  // Aviso de alterações não salvas (2026-07-17, pedido explícito) -- ver
  // hooks/useAvisoSairSemSalvar.ts.
  const { setSujo, mostrarModal, setMostrarModal, tentarSair } = useAvisoSairSemSalvar()
  const { conectado: agenteConectado, verificado: agenteVerificado } = useAgenteSapConectado()
  useFaviconAgente(agenteVerificado ? (agenteConectado ? 'conectado' : 'desligado') : undefined)
  // Gate "Agente SAP não identificado, deseja realizar o BITin manualmente?" (2026-07-23,
  // pedido explícito) -- só faz sentido pra um rascunho recém-criado (ver `ehRascunhoVazio`
  // abaixo), nunca reaparece depois que o engenheiro já preencheu alguma coisa. Confirmar
  // "Sim" libera o resto da tela normalmente; `mostrarInstalacao` troca a tela inteira pelas
  // instruções (acessível tanto pelo gate quanto pelo link "Ativar agente?" no cabeçalho).
  //
  // Persistido em `localStorage` por BITin (2026-07-23, pedido explícito: "quando a pessoa
  // escolher fazer manualmente ele sempre vai abrir manual, não vai mais apitar a
  // notificação") -- antes era só estado de componente, então voltar pra "Meus Bitins" e abrir
  // o MESMO BITin de novo perguntava tudo de novo (remonta, estado zera). Inicializa lazy a
  // partir do valor já salvo pra este `mongoId` (useEffect abaixo resincroniza se `mongoId`
  // mudar sem remontar o componente, ver comentário no `gateFoiExibidoRef`).
  const [manualConfirmado, setManualConfirmado] = useState(() => (mongoId ? bitinEscolheuManual(mongoId) : false))
  const [mostrarInstalacao, setMostrarInstalacao] = useState(false)

  useEffect(() => {
    if (mongoId) setManualConfirmado(bitinEscolheuManual(mongoId))
  }, [mongoId])

  function confirmarManual() {
    if (mongoId) marcarBitinManual(mongoId)
    setManualConfirmado(true)
  }

  // "Com o agente aberto ele vai validar com o sistema... pegar a conta logada" (2026-07-23,
  // pedido explícito) -- manda quem está logado assim que o agente conecta (só exibição na
  // janela do agente, ver sap-agent/estado_agente.py; nunca autenticação de verdade).
  useEffect(() => {
    if (agenteConectado && user) {
      identificarUsuarioNoAgente({ nome: user.nome, email: user.email, setor: user.setor })
    }
  }, [agenteConectado, user])

  // Campos editáveis (dados gerais + materiais).
  const [produto, setProdutoBase] = useState('')
  const [motivo, setMotivoBase] = useState('')
  const [solicitante, setSolicitante] = useState('')
  const [setor, setSetorBase] = useState('')
  const [bitex, setBitexBase] = useState('')
  // Wrappers que marcam "sujo" (2026-07-17) -- passados pra baixo em vez dos setters puros,
  // pra saber que existe alteração ainda não salva.
  function setProduto(v: string) {
    setProdutoBase(v)
    setSujo(true)
  }
  function setMotivo(v: string) {
    setMotivoBase(v)
    setSujo(true)
  }
  function setSetor(v: string) {
    setSetorBase(v)
    setSujo(true)
  }
  function setBitex(v: string) {
    setBitexBase(v)
    setSujo(true)
  }
  const [materiais, setMateriais] = useState<MaterialComId[]>([])
  const [ordemCliente, setOrdemCliente] = useState<OrdemClienteEditavel[]>([])
  const [checklistOverrides, setChecklistOverrides] = useState<Record<string, boolean>>({})
  const [checklistDescricoes, setChecklistDescricoes] = useState<Record<string, string>>({})
  const [conteudoExistente, setConteudoExistente] = useState<Record<string, unknown>>({})
  const [schema, setSchema] = useState<MateriaisSchema | null>(null)
  const [subgrupos, setSubgrupos] = useState<Subgrupo[]>([])

  // Estado do documento (o que veio do backend).
  const [status, setStatus] = useState('rascunho')
  // Status "Concluído" (2026-07-20, ver lib/bitinEtapa.ts::statusDoBitin) -- StatusBadge
  // precisa disso além de `status` bruto pra distinguir Enviado de Concluído.
  const [windchillEnviado, setWindchillEnviado] = useState(false)
  const [podeEditar, setPodeEditar] = useState(true)
  const [codigo, setCodigo] = useState<string | null>(null)
  const [resumo, setResumo] = useState<BitinResumo | null>(null)

  const [carregando, setCarregando] = useState(true)
  const [bloqueado, setBloqueado] = useState(false)
  const [erro, setErro] = useState<string | null>(null)
  const [salvando, setSalvando] = useState(false)
  const [excluindo, setExcluindo] = useState(false)
  const [duplicando, setDuplicando] = useState(false)
  const [confirmacaoEnvio, setConfirmacaoEnvio] = useState<string | null>(null)

  // Confia 100% em `podeEditar` (o servidor decide, ver backend/api/bitins.py::_pode_editar)
  // -- desde 2026-07-17 isso pode ser `true` mesmo com status "enviado" (setor Processos
  // reeditando um BITin encaminhado pelo Cadastro, ver bitin_lifecycle.concluir_processamento).
  // Botões específicos de rascunho (Enviar, excluir rascunho) continuam checando
  // `status === 'rascunho'` diretamente, não `editavel`.
  const editavel = podeEditar
  const ehAdmin = isAdmin(user?.permission_level)
  // "Duplicar" (2026-07-22) -- só quem cria BITin de verdade pode (mesma regra de POST
  // /bitins/draft, ver backend/api/bitins.py::create_or_update_draft: Cadastro/Processos
  // recebem 403 tentando criar/editar rascunho -- não faz sentido mostrar o botão pra eles).
  const podeDuplicar = ehAdmin || ehDoSetor(user?.permission_level, user?.setor, SETOR_ENGENHARIA)
  // BITin "enviado" mas ainda editável só acontece no cenário Processos (ou admin fazendo a
  // mesma coisa) -- usado pra rotear salvar()/alternarChecklist() pra /atualizar-processos em
  // vez de /draft, e pra mostrar o botão "Concluir" (rótulo simplificado 2026-07-20, pedido
  // explícito: "em um bitin aberto coloca a parte de concluir processamento só concluir").
  const editandoComoProcessos = status === 'enviado' && editavel
  // "Ordem de cliente" só aparece quando faz sentido (2026-07-20, pedido explícito: "só
  // aparece quando coloca oc = x no código, se não tiver ativado essa aba não aparece") --
  // OU já existe alguma entrada preenchida (não esconde dado que já foi digitado se o
  // engenheiro voltar o OC pra "-" depois).
  const precisaOrdemCliente =
    materiais.some((m) => m.alteracoes.impactos_operacionais.oc === 'X') || ordemCliente.length > 0

  // Rascunho "recém-criado", sem nada preenchido ainda -- só nesse estado o gate de agente faz
  // sentido (2026-07-23): reabrir um BITin em andamento não deveria voltar a perguntar isso.
  // NÃO checa `setor` (achado real: o efeito abaixo auto-preenche o setor sozinho pra quem só
  // tem 1 subgrupo vinculado, quase na hora de abrir a tela -- isso não é o engenheiro tendo
  // preenchido nada, mas fazia o gate nunca aparecer pra esse grupo de usuários).
  const ehRascunhoVazio =
    status === 'rascunho' &&
    produto === '' &&
    motivo === '' &&
    bitex === '' &&
    materiais.length === 0
  // Gate NÃO deve sumir sozinho quando o agente conecta (2026-07-23, achado real: "quando eu
  // ativo o agente já ta abrindo direto o bitin" -- `mostrarGate` reagia direto a
  // `agenteConectado` ao vivo, então ativar o agente em outra janela fazia o gate desaparecer
  // e a tela normal aparecer sem o engenheiro ter clicado em nada aqui). Uma vez que as
  // condições pra mostrar o gate ficam verdadeiras, `gateFoiExibidoRef` trava em `true` e SÓ o
  // clique explícito em "Acessar bitin"/"Sim, fazer manualmente" (`manualConfirmado`) fecha o
  // gate -- "Verificar conexão" dentro do gate (AgenteGate.tsx) é o único jeito de confirmar
  // que o agente está ativo e liberar o botão "Acessar bitin". Reseta ao trocar de BITin.
  const gateFoiExibidoRef = useRef(false)
  // Dispensa só PARA ESTA VISITA (2026-07-23) -- diferente de `manualConfirmado` (persistido,
  // "sempre abre manual"), é o efeito do botão "Acessar bitin" (agente confirmado conectado
  // via "Verificar conexão" dentro do gate): fecha a tela sem marcar o BITin como manual.
  const [gateDispensadoTemporario, setGateDispensadoTemporario] = useState(false)
  useEffect(() => {
    gateFoiExibidoRef.current = false
    setGateDispensadoTemporario(false)
  }, [mongoId])
  if (!carregando && editavel && agenteVerificado && !agenteConectado && ehRascunhoVazio && !manualConfirmado) {
    gateFoiExibidoRef.current = true
  }
  const mostrarGate = gateFoiExibidoRef.current && !manualConfirmado && !gateDispensadoTemporario

  useEffect(() => {
    let cancelado = false
    api
      .get<Bitin>(`/bitins/${mongoId}`)
      .then((resp) => {
        if (cancelado) return
        const b = resp.data
        if (!b.pode_editar && b.status === 'rascunho') {
          setBloqueado(true)
          return
        }
        setStatus(b.status)
        setWindchillEnviado(b.windchill_enviado)
        setPodeEditar(b.pode_editar)
        setCodigo(b.codigo)
        const content = b.content
        // Setters BASE (não os wrappers que marcam "sujo") -- isto é carregar o BITin, não
        // uma edição do engenheiro.
        setProdutoBase(String(content.produto ?? ''))
        setMotivoBase(String(content.motivo ?? ''))
        setSolicitante(String(content.solicitante ?? user?.nome ?? ''))
        setSetorBase(String(content.setor ?? ''))
        setBitexBase(String(content.bitex ?? ''))
        setMateriais(
          ((content.materiais as MaterialEditavel[] | undefined) ?? []).map((m) => ({
            ...normalizarMaterial(m),
            _id: crypto.randomUUID(),
          })),
        )
        setChecklistOverrides((content.checklist_overrides as Record<string, boolean> | undefined) ?? {})
        setChecklistDescricoes((content.checklist_descricoes as Record<string, string> | undefined) ?? {})
        setOrdemCliente((content.ordem_cliente as OrdemClienteEditavel[] | undefined) ?? [])
        setConteudoExistente(content)
      })
      .catch(() => setErro('Não foi possível carregar este BITin.'))
      .finally(() => setCarregando(false))
    return () => {
      cancelado = true
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [mongoId])

  useEffect(() => {
    api
      .get<MateriaisSchema>('/bitins/schema/materiais')
      .then((resp) => setSchema(resp.data))
      .catch(() => {})
  }, [])

  useEffect(() => {
    api
      .get<Subgrupo[]>('/subgrupos')
      .then((resp) => setSubgrupos(resp.data))
      .catch(() => {})
  }, [])

  // Setor do BITin (2026-07-17, pedido explícito) -- restrito ao(s) Subgrupo(s) do usuário
  // logado: "a pessoa que é dos dois pode escolher qual setor ela quer fazer bitin. se ela
  // tiver só 1 setor vinculado só o do setor vinculado dela". Admin tem `subgrupo_ids` vazio
  // (único nível que pode ficar sem Subgrupo, ver NIVEIS_QUE_EXIGEM_SUBGRUPO) -- por isso
  // "sem subgrupo nenhum" cai pra "sem restrição" (todos os subgrupos cadastrados), não pra
  // lista vazia. Nome do subgrupo é literalmente o valor salvo em `content.setor` (P/A no
  // número sequencial, ver backend/bitin_number.py) -- não um conceito diferente.
  const setoresPermitidos =
    (user?.subgrupo_ids?.length ?? 0) === 0
      ? subgrupos.map((s) => s.nome)
      : subgrupos.filter((s) => user!.subgrupo_ids.includes(s.id)).map((s) => s.nome)

  // Só 1 subgrupo vinculado -- trava sozinho, sem exigir escolha manual. Só preenche se `setor`
  // ainda estiver vazio (não sobrescreve um rascunho já salvo com outro setor). setSetorBase
  // (não o wrapper) -- preenchimento automático não é uma edição do engenheiro, não deveria
  // marcar "sujo" sozinho ao abrir a tela.
  useEffect(() => {
    if (setor === '' && setoresPermitidos.length === 1) setSetorBase(setoresPermitidos[0])
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [setor, setoresPermitidos.join('|')])

  async function carregarResumo() {
    try {
      const resp = await api.get(`/bitins/${mongoId}/resumo`)
      setResumo(resp.data)
    } catch {
      // silencioso -- o resumo é complementar (checklist/setores), a tela principal já
      // funciona sem ele
    }
  }

  useEffect(() => {
    carregarResumo()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [mongoId])

  // Aplica sugestão automática de Alt/Esp/nota DWG-SAT (2026-07-17, pedido explícito: "coloca
  // os dois, códigos já existentes puxam mas o engenheiro pode mexer, mas tem que preencher
  // automatico sozinho tb") -- SÓ em campo ainda em branco ("-") e SÓ adiciona a nota DWG/SAT
  // se ela ainda não existir; nunca sobrescreve o que o engenheiro já declarou (mesmo espírito
  // de checklist_overrides: sugestão só preenche o vazio, não briga com escolha manual).
  // scripts/bitin_document.py::suggest_impactos é quem calcula -- aqui só decide SE aplica.
  function aplicarSugestoes(materiaisResumo: BitinResumo['materiais']) {
    for (const resumoMaterial of materiaisResumo) {
      if (!resumoMaterial.codigo_material) continue
      const local = materiais.find((m) => m.codigo_material === resumoMaterial.codigo_material)
      if (!local) continue
      const sugestoes = resumoMaterial.sugestoes
      const impactos = local.alteracoes.impactos_operacionais
      const novosImpactos = { ...impactos }
      let mudou = false
      if (impactos.alt === '-' && sugestoes.alt && sugestoes.alt !== '-') {
        novosImpactos.alt = sugestoes.alt
        mudou = true
      }
      if (impactos.esp === '-' && sugestoes.esp && sugestoes.esp !== '-') {
        novosImpactos.esp = sugestoes.esp
        mudou = true
      }
      let novosDadosBasicos = local.alteracoes.dados_basicos
      if (sugestoes.dwg_sat_acao && !Object.prototype.hasOwnProperty.call(novosDadosBasicos, sugestoes.dwg_sat_acao)) {
        novosDadosBasicos = { ...novosDadosBasicos, [sugestoes.dwg_sat_acao]: { de: '', para: '' } }
        mudou = true
      }
      if (mudou) {
        atualizarMaterial(local._id, {
          ...local,
          alteracoes: { ...local.alteracoes, impactos_operacionais: novosImpactos, dados_basicos: novosDadosBasicos },
        })
      }
    }
  }

  // Checklist/setores ao vivo (2026-07-17, pedido explícito: "eu quero que marque ao vivo
  // igual com os setores afetados") -- antes só recarregava depois de um Salvar de verdade.
  // POST /bitins/preview-resumo (backend/api/bitins.py::preview_resumo) calcula com o MESMO
  // código de GET /{id}/resumo a partir do que está na tela agora, sem persistir nada --
  // então não interfere com `sujo`/o aviso de "alterações não salvas". Debounce de 500ms
  // (não a cada tecla) porque os campos de texto (produto/motivo, dados_basicos das telas)
  // só propagam pro estado no blur mesmo, então uma pausa curta já é natural; o debounce aqui
  // é só pra não disparar 1 request por campo quando várias mudanças vêm juntas (ex.: colar
  // do SAP cria N materiais de uma vez).
  useEffect(() => {
    if (carregando || !editavel) return
    const id = setTimeout(() => {
      api
        .post('/bitins/preview-resumo', { content: montarConteudo() })
        .then((resp) => {
          setResumo(resp.data)
          aplicarSugestoes(resp.data.materiais)
        })
        .catch(() => {})
    }, 500)
    return () => clearTimeout(id)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [produto, motivo, setor, bitex, materiais, checklistOverrides, checklistDescricoes, carregando, editavel])

  // Pós-envio (2026-07-16, pedido do usuário: "coloque uma informação na tela de quando envia
  // bitin de confirmação que atualize a pagina e vai direto no bitin já enviado"). Mesma URL
  // (/bitins/:mongoId) antes e depois de enviar -- não navega, só troca o estado local pra
  // travar os campos (editavel passa a depender de status==='rascunho') e recarrega o resumo
  // (agora existe, já que o BITin está enviado). Banner de confirmação some sozinho.
  useEffect(() => {
    if (!bitinEnviado) return
    setStatus(bitinEnviado.status)
    setWindchillEnviado(bitinEnviado.windchill_enviado)
    setPodeEditar(bitinEnviado.pode_editar)
    setCodigo(bitinEnviado.codigo)
    setConteudoExistente(bitinEnviado.content)
    setMateriais(
      ((bitinEnviado.content.materiais as MaterialEditavel[] | undefined) ?? []).map((m) => ({
        ...normalizarMaterial(m),
        _id: crypto.randomUUID(),
      })),
    )
    setConfirmacaoEnvio(`BITin enviado com sucesso! Código: ${bitinEnviado.codigo ?? '—'}`)
    carregarResumo()
    const id = setTimeout(() => setConfirmacaoEnvio(null), 8000)
    return () => clearTimeout(id)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [bitinEnviado])

  // useCallback (2026-07-17) -- identidade estável entre renders é o que permite o
  // React.memo de MaterialEditorCard pular re-render de cards não tocados (ver comentário em
  // MaterialComId acima). Operam por `_id`, não índice.
  const atualizarMaterial = useCallback((id: string, atualizado: MaterialEditavel) => {
    setMateriais((atual) => atual.map((m) => (m._id === id ? { ...atualizado, _id: id } : m)))
    setSujo(true)
  }, [setSujo])

  const adicionarMaterial = useCallback(() => {
    setMateriais((atual) => [...atual, { ...materialVazio(), _id: crypto.randomUUID() }])
    setSujo(true)
  }, [setSujo])

  const removerMaterial = useCallback((id: string) => {
    setMateriais((atual) => atual.filter((m) => m._id !== id))
    setSujo(true)
  }, [setSujo])

  // Sempre parte do estado atual de TODOS os campos editáveis (não só `conteudoExistente`,
  // que só é atualizado depois de um POST bem-sucedido) -- salvar a checklist sozinha não
  // pode reverter um material que acabou de ser adicionado e ainda não foi salvo por aqui
  // (bug real encontrado em 2026-07-15: clicar na checklist logo após "+ Novo material"
  // apagava o material porque usava um `conteudoExistente` desatualizado).
  function montarConteudo(extra?: Record<string, unknown>): Record<string, unknown> {
    // Um "+ Novo material" clicado mas ainda não preenchido não vira material de verdade no
    // que é salvo -- só filtra o payload enviado, o card em branco continua na tela pro
    // engenheiro terminar de preencher (bug real encontrado em 2026-07-15 no mesmo padrão em
    // Códigos SAP: linha em branco virando "material fantasma" e disparando erros de
    // validação bobos no envio).
    const materiaisPreenchidos = materiais
      .filter((m) => m.codigo_material.trim() !== '')
      .map(({ _id, ...resto }) => resto)
    // Mesmo raciocínio de materiaisPreenchidos acima -- uma entrada sem código ainda não vira
    // "ordem_cliente fantasma" no payload; dentro de cada entrada com código, itens sem
    // codigo_material (linha em branco clicada mas não preenchida) também não vão.
    const ordemClientePreenchida = ordemCliente
      .filter((oc) => oc.codigo.trim() !== '')
      .map((oc) => ({
        ...oc,
        acrescentar_no_pedido: oc.acrescentar_no_pedido.filter((it) => it.codigo_material.trim() !== ''),
        retira_do_pedido: oc.retira_do_pedido.filter((it) => it.codigo_material.trim() !== ''),
      }))
    return {
      ...conteudoExistente,
      produto,
      motivo,
      solicitante,
      setor,
      bitex,
      materiais: materiaisPreenchidos,
      ordem_cliente: ordemClientePreenchida,
      checklist_overrides: checklistOverrides,
      checklist_descricoes: checklistDescricoes,
      ...extra,
    }
  }

  function alternarDescricaoChecklist(id: string, descricao: string) {
    setChecklistDescricoes((atual) => ({ ...atual, [id]: descricao }))
    setSujo(true)
  }

  // Roteia pro endpoint certo -- BITin "enviado" só é editável no cenário Processos
  // (editandoComoProcessos), e esse caminho NUNCA pode passar por /draft: o caminho de
  // atualização de /draft reverte status pra "rascunho" (ver backend/api/bitins.py::
  // create_or_update_draft), o que corromperia um BITin já enviado. /atualizar-processos só
  // troca o conteúdo, preservando status/número/histórico.
  async function salvarConteudo(content: Record<string, unknown>) {
    if (editandoComoProcessos) {
      return api.post(`/bitins/${mongoId}/atualizar-processos`, { content })
    }
    return api.post('/bitins/draft', { mongo_id: mongoId, content })
  }

  async function alternarChecklist(id: string, afeta: boolean) {
    const overridesAtualizados = { ...checklistOverrides, [id]: afeta }
    setChecklistOverrides(overridesAtualizados)
    try {
      const resp = await salvarConteudo(montarConteudo({ checklist_overrides: overridesAtualizados }))
      setConteudoExistente(resp.data.content)
      // montarConteudo() já bundla TODOS os campos editáveis (não só a checklist), então esse
      // POST salva tudo que estava pendente também -- reseta "sujo" igual ao salvar() normal.
      setSujo(false)
      await carregarResumo()
    } catch {
      setErro('Não foi possível salvar a checklist. Tente novamente.')
    }
  }

  async function salvar(): Promise<string | null> {
    setErro(null)
    setSalvando(true)
    try {
      const resp = await salvarConteudo(montarConteudo())
      const novoId = resp.data.mongo_id as string
      setConteudoExistente(resp.data.content)
      setSujo(false)
      await carregarResumo()
      return novoId
    } catch {
      setErro('Não foi possível salvar. Tente novamente.')
      return null
    } finally {
      setSalvando(false)
    }
  }

  async function handleEnviar() {
    const id = await salvar()
    if (id) await enviar()
  }

  // "Duplicar" (2026-07-22) -- cria um rascunho novo com os dados deste BITin (ver
  // lib/duplicarBitin.ts). Funciona em qualquer status (rascunho ou já enviado) -- é
  // justamente pra reaproveitar um BITin PRONTO como ponto de partida.
  async function handleDuplicar() {
    if (!mongoId) return
    setDuplicando(true)
    setErro(null)
    try {
      await duplicarBitinENavegar(mongoId, navigate)
    } catch {
      setErro('Não foi possível duplicar este BITin. Tente novamente.')
      setDuplicando(false)
    }
  }

  // Excluir um BITin já enviado é bem mais grave que excluir rascunho -- libera o número
  // sequencial (código pode ser reaproveitado por outro BITin depois), por isso o texto de
  // confirmação é mais explícito e só admin (isAdmin(permission_level)) vê o botão pra
  // BITin enviado (ver handleExcluirEnviado abaixo). Backend valida de novo (não confia só na
  // UI escondendo o botão).
  async function handleExcluir() {
    if (!mongoId) return
    if (!window.confirm('Excluir este rascunho? Essa ação não pode ser desfeita.')) return
    setExcluindo(true)
    setErro(null)
    try {
      await api.delete(`/bitins/${mongoId}`)
      navigate('/bitins', { replace: true })
    } catch {
      setErro('Não foi possível excluir. Tente novamente.')
      setExcluindo(false)
    }
  }

  async function handleExcluirEnviado() {
    if (!mongoId) return
    if (
      !window.confirm(
        `Excluir este BITin já enviado (código ${codigo ?? '—'})? Essa ação não pode ser desfeita e vai liberar o número sequencial.`,
      )
    )
      return
    setExcluindo(true)
    setErro(null)
    try {
      await api.delete(`/bitins/${mongoId}`)
      navigate('/bitins', { replace: true })
    } catch {
      setErro('Não foi possível excluir. Tente novamente.')
      setExcluindo(false)
    }
  }

  // Fecha a janela de reedição do Processos (2026-07-17) -- depois disso o BITin volta a
  // ficar travado, inclusive pra quem concluiu. Recarrega a página pra refletir o novo estado
  // só-leitura (mais simples e mais confiável do que tentar reconciliar todo o estado local).
  async function handleConcluirProcessos() {
    if (!mongoId) return
    if (!window.confirm('Concluir a revisão desse BITin?')) return
    setSalvando(true)
    setErro(null)
    try {
      await salvarConteudo(montarConteudo())
      await api.post(`/bitins/${mongoId}/concluir-processos`)
      window.location.reload()
    } catch {
      setErro('Não foi possível concluir o processamento. Tente novamente.')
      setSalvando(false)
    }
  }

  if (carregando) {
    return <p className="text-sm text-ink-muted">Carregando...</p>
  }

  if (mostrarInstalacao) {
    return (
      <div className="mx-auto max-w-[1600px] pb-24 pt-3">
        <InstalarAgenteCard onVoltar={() => setMostrarInstalacao(false)} />
      </div>
    )
  }

  if (mostrarGate) {
    return (
      <AgenteGate
        onConfirmarManual={confirmarManual}
        onAbrirInstalacao={() => setMostrarInstalacao(true)}
        onAcessarComAgente={() => setGateDispensadoTemporario(true)}
      />
    )
  }

  if (bloqueado) {
    return (
      <div className="mx-auto max-w-2xl">
        <p className="text-sm text-ink-muted">
          Este BITin já foi enviado ou você não tem permissão pra editá-lo.
        </p>
        <button
          type="button"
          onClick={voltar}
          className="mt-2 inline-block text-sm text-ink-muted hover:text-ink hover:underline"
        >
          ← Voltar
        </button>
      </div>
    )
  }

  return (
    <div className="mx-auto max-w-[1600px] pb-24">
      {/* Intercepta o clique se houver alteração não salva (2026-07-17, ver
          hooks/useAvisoSairSemSalvar.ts) -- botão em vez de Link, senão navegaria antes de
          dar chance de mostrar o modal. */}
      <button
        type="button"
        onClick={() => {
          if (tentarSair()) voltar()
        }}
        className="text-sm text-ink-muted hover:text-ink hover:underline"
      >
        ← Voltar
      </button>

      {mostrarModal && (
        <AvisoSairModal
          salvando={salvando}
          onCancelar={() => setMostrarModal(false)}
          onSairSemSalvar={voltar}
          onSalvarESair={async () => {
            const ok = await salvar()
            if (ok) voltar()
          }}
        />
      )}

      <div className="mt-3 flex flex-wrap items-center gap-3">
        <h1 className="text-2xl font-semibold text-ink">{codigo || 'Rascunho sem código'}</h1>
        <StatusBadge status={status} windchillEnviado={windchillEnviado} />
        {editavel && (
          <AjudaPopover titulo="Hint">
            <p>
              Preencha os dados gerais e, por material, marque os itens da checklist que se
              aplicam. Clicar num item sempre vale, mesmo que já venha marcado.
            </p>
            <p>
              Um material pode ser cadastrado inteiramente aqui ("+ Novo material"), incluindo a
              lista técnica de componentes, direto no card do material.
            </p>
            <p>Se algum item da checklist exigir descrição, preencha-a antes de enviar.</p>
          </AjudaPopover>
        )}

        {podeDuplicar && (
          <button
            type="button"
            onClick={handleDuplicar}
            disabled={duplicando}
            title="Cria um rascunho novo com os mesmos dados deste BITin"
            className="ml-auto rounded-lg border border-line px-4 py-2 text-sm font-medium text-ink-muted transition-colors hover:bg-surface-alt disabled:cursor-not-allowed disabled:opacity-60"
          >
            {duplicando ? 'Duplicando...' : 'Duplicar'}
          </button>
        )}

        {editavel && status === 'rascunho' && (
          <button
            type="button"
            onClick={handleExcluir}
            disabled={excluindo || salvando || enviando}
            className="rounded-lg border border-red-600/40 px-4 py-2 text-sm font-medium text-red-600 transition-colors hover:bg-red-600/10 disabled:cursor-not-allowed disabled:opacity-60"
          >
            {excluindo ? 'Excluindo...' : 'Excluir rascunho'}
          </button>
        )}

        {/* Excluir BITin já enviado (2026-07-16, pedido do usuário) -- só admin
            (isAdmin(permission_level), ver lib/permissions.ts) vê isto; usuário comum
            continua só com "Excluir rascunho" acima, igual sempre foi. */}
        {status === 'enviado' && ehAdmin && (
          <button
            type="button"
            onClick={handleExcluirEnviado}
            disabled={excluindo || salvando || enviando}
            className="rounded-lg border border-red-600/40 px-4 py-2 text-sm font-medium text-red-600 transition-colors hover:bg-red-600/10 disabled:cursor-not-allowed disabled:opacity-60"
          >
            {excluindo ? 'Excluindo...' : 'Excluir BITin enviado'}
          </button>
        )}

        {editavel && (
          <button
            type="button"
            onClick={salvar}
            disabled={salvando || enviando}
            className="rounded-lg border border-line px-4 py-2 text-sm font-medium text-ink-muted transition-colors hover:bg-surface-alt disabled:cursor-not-allowed disabled:opacity-60"
          >
            {salvando ? 'Salvando...' : 'Salvar'}
          </button>
        )}

        {/* Setor Processos (2026-07-17) -- fecha a janela de reedição aberta pelo Cadastro.
            Só aparece nesse cenário específico (enviado + editável = Processos/admin
            reeditando um BITin encaminhado, ver editandoComoProcessos). */}
        {editandoComoProcessos && (
          <button
            type="button"
            onClick={handleConcluirProcessos}
            disabled={salvando || enviando}
            className="rounded-lg bg-brand-navy px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-brand-navy-dark disabled:cursor-not-allowed disabled:opacity-60"
          >
            {salvando ? 'Salvando...' : 'Concluir'}
          </button>
        )}
      </div>

      {erro && <p className="mt-3 text-sm text-red-600">{erro}</p>}
      {confirmacaoEnvio && <p className="mt-3 text-sm text-green-600">{confirmacaoEnvio}</p>}
      <ErrosEnvioBanner erros={errosEnvio} />

      <DadosGeraisCard
        editavel={editavel}
        produto={produto}
        motivo={motivo}
        solicitante={solicitante}
        setor={setor}
        bitex={bitex}
        setoresPermitidos={setoresPermitidos}
        onProdutoChange={setProduto}
        onMotivoChange={setMotivo}
        onSetorChange={setSetor}
        onBitexChange={setBitex}
        resumo={resumo}
        onToggleChecklist={alternarChecklist}
        onChecklistDescricaoChange={alternarDescricaoChecklist}
      />

      {editavel
        ? precisaOrdemCliente && (
            <OrdemClienteEditor
              itens={ordemCliente}
              editavel={editavel}
              onChange={(itens) => {
                setOrdemCliente(itens)
                setSujo(true)
              }}
            />
          )
        : resumo && <OrdemClienteSection itens={resumo.ordem_cliente} />}

      <MateriaisSection
        editavel={editavel}
        schema={schema}
        materiais={materiais}
        onChangeMaterial={atualizarMaterial}
        onAddMaterial={adicionarMaterial}
        onRemoveMaterial={removerMaterial}
        materiaisResumo={resumo?.materiais ?? null}
      />

      {resumo && <HistoricoCard eventos={resumo.historico} />}

      {editavel && status === 'rascunho' && mongoId && (
        <EdicaoBottomBar
          mongoId={mongoId}
          agenteConectado={agenteConectado}
          onAgenteDesconectadoClick={() => setMostrarInstalacao(true)}
          enviando={enviando || salvando}
          onEnviar={handleEnviar}
        />
      )}
      {/* Sem toast quando o engenheiro já escolheu "fazer manualmente" pra este BITin
          (2026-07-23, pedido explícito: "não vai mais apitar a notificação") -- decisão
          persistida em `preferenciasAgente.ts`, não só desta visita. */}
      {!manualConfirmado && <AgenteConexaoToast conectado={agenteConectado} verificado={agenteVerificado} />}
    </div>
  )
}
