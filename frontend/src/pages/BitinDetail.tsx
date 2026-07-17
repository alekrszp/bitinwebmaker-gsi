import { useEffect, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import AjudaPopover from '../components/bitin/AjudaPopover'
import DadosGeraisCard from '../components/bitin/DadosGeraisCard'
import EdicaoBottomBar from '../components/bitin/EdicaoBottomBar'
import ErrosEnvioBanner from '../components/bitin/ErrosEnvioBanner'
import MateriaisSection from '../components/bitin/MateriaisSection'
import OrdemClienteSection from '../components/bitin/OrdemClienteSection'
import StatusBadge from '../components/bitin/StatusBadge'
import { useAuth } from '../hooks/useAuth'
import { api } from '../lib/api'
import { materialVazio, normalizarMaterial } from '../lib/bitinDefaults'
import type { BitinResumo } from '../lib/bitinTypes'
import { useEnviarBitin } from '../lib/useEnviarBitin'
import type { Bitin, MateriaisSchema, MaterialEditavel } from '../lib/types'

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
// Mesmo nível usado em Settings.tsx e backend/api/bitins.py::ADMIN_LEVEL -- só espelhado aqui
// pra decidir se mostra "Excluir BITin enviado" (2026-07-16).
const ADMIN_LEVEL = 99

export default function BitinDetail() {
  const { mongoId } = useParams<{ mongoId: string }>()
  const navigate = useNavigate()
  const { user } = useAuth()
  const { enviando, errosEnvio, bitinEnviado, enviar } = useEnviarBitin(mongoId)

  // Campos editáveis (dados gerais + materiais).
  const [produto, setProduto] = useState('')
  const [motivo, setMotivo] = useState('')
  const [solicitante, setSolicitante] = useState('')
  const [setor, setSetor] = useState('')
  const [materiais, setMateriais] = useState<MaterialEditavel[]>([])
  const [checklistOverrides, setChecklistOverrides] = useState<Record<string, boolean>>({})
  const [checklistDescricoes, setChecklistDescricoes] = useState<Record<string, string>>({})
  const [conteudoExistente, setConteudoExistente] = useState<Record<string, unknown>>({})
  const [schema, setSchema] = useState<MateriaisSchema | null>(null)

  // Estado do documento (o que veio do backend).
  const [status, setStatus] = useState('rascunho')
  const [podeEditar, setPodeEditar] = useState(true)
  const [codigo, setCodigo] = useState<string | null>(null)
  const [resumo, setResumo] = useState<BitinResumo | null>(null)

  const [carregando, setCarregando] = useState(true)
  const [bloqueado, setBloqueado] = useState(false)
  const [erro, setErro] = useState<string | null>(null)
  const [salvando, setSalvando] = useState(false)
  const [excluindo, setExcluindo] = useState(false)
  const [confirmacaoEnvio, setConfirmacaoEnvio] = useState<string | null>(null)

  const editavel = status === 'rascunho' && podeEditar
  const ehAdmin = (user?.permission_level ?? 0) >= ADMIN_LEVEL

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
        setPodeEditar(b.pode_editar)
        setCodigo(b.codigo)
        const content = b.content
        setProduto(String(content.produto ?? ''))
        setMotivo(String(content.motivo ?? ''))
        setSolicitante(String(content.solicitante ?? user?.nome ?? ''))
        setSetor(String(content.setor ?? ''))
        setMateriais(((content.materiais as MaterialEditavel[] | undefined) ?? []).map(normalizarMaterial))
        setChecklistOverrides((content.checklist_overrides as Record<string, boolean> | undefined) ?? {})
        setChecklistDescricoes((content.checklist_descricoes as Record<string, string> | undefined) ?? {})
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

  // Pós-envio (2026-07-16, pedido do usuário: "coloque uma informação na tela de quando envia
  // bitin de confirmação que atualize a pagina e vai direto no bitin já enviado"). Mesma URL
  // (/bitins/:mongoId) antes e depois de enviar -- não navega, só troca o estado local pra
  // travar os campos (editavel passa a depender de status==='rascunho') e recarrega o resumo
  // (agora existe, já que o BITin está enviado). Banner de confirmação some sozinho.
  useEffect(() => {
    if (!bitinEnviado) return
    setStatus(bitinEnviado.status)
    setPodeEditar(bitinEnviado.pode_editar)
    setCodigo(bitinEnviado.codigo)
    setConteudoExistente(bitinEnviado.content)
    setMateriais(((bitinEnviado.content.materiais as MaterialEditavel[] | undefined) ?? []).map(normalizarMaterial))
    setConfirmacaoEnvio(`BITin enviado com sucesso! Código: ${bitinEnviado.codigo ?? '—'}`)
    carregarResumo()
    const id = setTimeout(() => setConfirmacaoEnvio(null), 8000)
    return () => clearTimeout(id)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [bitinEnviado])

  function atualizarMaterial(index: number, atualizado: MaterialEditavel) {
    setMateriais((atual) => atual.map((m, i) => (i === index ? atualizado : m)))
  }

  function adicionarMaterial() {
    setMateriais((atual) => [...atual, materialVazio()])
  }

  function removerMaterial(index: number) {
    setMateriais((atual) => atual.filter((_, i) => i !== index))
  }

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
    const materiaisPreenchidos = materiais.filter((m) => m.codigo_material.trim() !== '')
    return {
      ...conteudoExistente,
      produto,
      motivo,
      solicitante,
      setor,
      materiais: materiaisPreenchidos,
      checklist_overrides: checklistOverrides,
      checklist_descricoes: checklistDescricoes,
      ...extra,
    }
  }

  function alternarDescricaoChecklist(id: string, descricao: string) {
    setChecklistDescricoes((atual) => ({ ...atual, [id]: descricao }))
  }

  async function alternarChecklist(id: string, afeta: boolean) {
    const overridesAtualizados = { ...checklistOverrides, [id]: afeta }
    setChecklistOverrides(overridesAtualizados)
    try {
      const resp = await api.post('/bitins/draft', {
        mongo_id: mongoId,
        content: montarConteudo({ checklist_overrides: overridesAtualizados }),
      })
      setConteudoExistente(resp.data.content)
      await carregarResumo()
    } catch {
      setErro('Não foi possível salvar a checklist. Tente novamente.')
    }
  }

  async function salvar(): Promise<string | null> {
    setErro(null)
    setSalvando(true)
    try {
      const resp = await api.post('/bitins/draft', {
        mongo_id: mongoId,
        content: montarConteudo(),
      })
      const novoId = resp.data.mongo_id as string
      setConteudoExistente(resp.data.content)
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

  // Excluir um BITin já enviado é bem mais grave que excluir rascunho -- libera o número
  // sequencial (código pode ser reaproveitado por outro BITin depois), por isso o texto de
  // confirmação é mais explícito e só admin (permission_level >= ADMIN_LEVEL) vê o botão pra
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

  if (carregando) {
    return <p className="text-sm text-ink-muted">Carregando...</p>
  }

  if (bloqueado) {
    return (
      <div className="mx-auto max-w-2xl">
        <p className="text-sm text-ink-muted">
          Este BITin já foi enviado ou você não tem permissão pra editá-lo.
        </p>
        <Link to="/bitins" className="mt-2 inline-block text-sm text-ink-muted hover:text-ink hover:underline">
          Voltar pra Meus Bitins
        </Link>
      </div>
    )
  }

  return (
    <div className="mx-auto max-w-[1600px] pb-24">
      <Link to="/bitins" className="text-sm text-ink-muted hover:text-ink hover:underline">
        ← Voltar pra Meus Bitins
      </Link>

      <div className="mt-3 flex flex-wrap items-center gap-3">
        <h1 className="text-2xl font-semibold text-ink">{codigo || 'Rascunho sem código'}</h1>
        <StatusBadge status={status} />
        {editavel && (
          <AjudaPopover titulo="Como usar a aba BITin">
            <p>
              A checklist é inteiramente manual -- nada é marcado automaticamente a partir dos
              materiais. Um material pode ser cadastrado inteiramente aqui ("+ Novo material") ou
              importado da tela ZBPP009; as duas telas operam sobre os mesmos dados e nenhuma
              depende da outra.
            </p>
            <p>
              Lembretes de envio: qualquer item da checklist marcado "Sim" que exija descrição
              precisa dela preenchida (Nota 8). Aprovação de desenho técnico e de NCM não são
              verificadas pelo sistema -- é responsabilidade do engenheiro confirmar antes de
              enviar.
            </p>
          </AjudaPopover>
        )}

        {editavel && (
          <button
            type="button"
            onClick={handleExcluir}
            disabled={excluindo || salvando || enviando}
            className="ml-auto rounded-lg border border-red-600/40 px-4 py-2 text-sm font-medium text-red-600 transition-colors hover:bg-red-600/10 disabled:cursor-not-allowed disabled:opacity-60"
          >
            {excluindo ? 'Excluindo...' : 'Excluir rascunho'}
          </button>
        )}

        {/* Excluir BITin já enviado (2026-07-16, pedido do usuário) -- só admin
            (permission_level >= ADMIN_LEVEL, mesmo nível de Settings.tsx/backend/api/
            bitins.py::ADMIN_LEVEL) vê isto; usuário comum continua só com "Excluir rascunho"
            acima, igual sempre foi. */}
        {status === 'enviado' && ehAdmin && (
          <button
            type="button"
            onClick={handleExcluirEnviado}
            disabled={excluindo || salvando || enviando}
            className="ml-auto rounded-lg border border-red-600/40 px-4 py-2 text-sm font-medium text-red-600 transition-colors hover:bg-red-600/10 disabled:cursor-not-allowed disabled:opacity-60"
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
        onProdutoChange={setProduto}
        onMotivoChange={setMotivo}
        onSetorChange={setSetor}
        resumo={resumo}
        onToggleChecklist={alternarChecklist}
        onChecklistDescricaoChange={alternarDescricaoChecklist}
      />

      {resumo && <OrdemClienteSection itens={resumo.ordem_cliente} />}

      <MateriaisSection
        editavel={editavel}
        schema={schema}
        materiais={materiais}
        onChangeMaterial={atualizarMaterial}
        onAddMaterial={adicionarMaterial}
        onRemoveMaterial={removerMaterial}
        materiaisResumo={resumo?.materiais ?? null}
        mongoId={mongoId}
      />

      {editavel && mongoId && (
        <EdicaoBottomBar mongoId={mongoId} enviando={enviando || salvando} onEnviar={handleEnviar} />
      )}
    </div>
  )
}
