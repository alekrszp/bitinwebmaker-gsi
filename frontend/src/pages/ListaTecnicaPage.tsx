import { memo, useCallback, useEffect, useState } from 'react'
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
import type { Bitin, ItemListaTecnica, MaterialEditavel, OperacaoListaTecnica } from '../lib/types'

// Página própria (rota /bitins/:mongoId/lista-tecnica), mesma ideia de CodigosSapPage.tsx --
// reformulada em 2026-07-15 (decisão do usuário: "lista técnica não deve depender de
// materiais já registrados. ali vai ser a mesma ideia da ZBPP009 mas com estrutura de lista
// técnica") pra não exigir que o "código pai" já exista em materiais[] -- é uma grade plana
// (uma linha = um componente filho), com o código pai como campo de texto livre igual à
// ZBPP009, não um dropdown restrito ao que já foi cadastrado em BITin/Códigos SAP.
//
// No Salvar, as linhas são agrupadas por código pai e cada grupo vira o lista_tecnica[] do
// material correspondente em materiais[] (mesmo array compartilhado com as abas BITin e
// Códigos SAP). Se o código pai digitado não bate com nenhum material já existente, um
// material novo "vazio" é criado só pra ter onde anexar os componentes (mesmo materialVazio()
// usado em "+ Novo material"), preservando a regra de que nenhuma das três telas depende da
// outra pra existir.
interface LinhaListaTecnicaBase extends ItemListaTecnica {
  codigo_pai: string
}

// `_id` client-side estável por linha (2026-07-17, otimização de performance -- mesmo padrão
// de CodigosSapPage.tsx, ver GPT_Engineering_BITIN/frontend/src/components/CodeForm.jsx).
type LinhaListaTecnica = LinhaListaTecnicaBase & { _id: string }

function linhaVazia(): LinhaListaTecnica {
  return {
    codigo_pai: '',
    // "alterar" só como placeholder interno -- o valor de verdade é recalculado em
    // `derivarOperacao` na hora de salvar (ver comentário lá), não editado na UI.
    operacao: 'alterar',
    codigo_filho: '',
    quantidade_de: '',
    quantidade_para: '',
    _id: crypto.randomUUID(),
  }
}

// Campo "Operação" removido da UI (2026-07-17, pedido explícito: "tira o campo operação é
// desnecessário") -- mas o backend/export (scripts/lista_tecnica_export.py) ainda precisa dele
// pra validar (Inserir exige Quantidade para, Excluir exige Quantidade de) e marcar a coluna
// certa (X) na planilha Winshuttle. Deriva sozinho a partir de qual quantidade foi preenchida,
// em vez de pedir escolha manual -- mesma regra que a validação já usa, só invertida (a
// validação checa "se é Inserir, Quantidade para tem que estar preenchida"; aqui: "se só
// Quantidade para está preenchida, é Inserir"):
// - só "para" preenchido (De vazio) -- item novo, ainda não existia -- Inserir.
// - só "de" preenchido (Para vazio) -- item removido -- Excluir.
// - os dois preenchidos (ou nenhum, linha em branco filtrada antes de chegar aqui) -- Alterar.
function derivarOperacao(item: ItemListaTecnica): OperacaoListaTecnica {
  const temDe = item.quantidade_de.trim() !== ''
  const temPara = item.quantidade_para.trim() !== ''
  if (!temDe && temPara) return 'inserir'
  if (temDe && !temPara) return 'excluir'
  return 'alterar'
}

function materiaisParaLinhas(materiais: MaterialEditavel[]): LinhaListaTecnica[] {
  const linhas = materiais.flatMap((m) =>
    m.alteracoes.lista_tecnica.map((item) => ({ codigo_pai: m.codigo_material, ...item, _id: crypto.randomUUID() })),
  )
  // Sempre sobra uma linha em branco no final pra continuar preenchendo (mesmo padrão da
  // ZBPP009 -- não obriga clicar em "+ Nova linha" primeiro).
  return [...linhas, linhaVazia()]
}

// Célula de texto memoizada com estado local (2026-07-17, mesmo padrão de CodigosSapPage.tsx)
// -- digitar só propaga pro estado da linha no blur, não a cada tecla.
const CelulaTexto = memo(function CelulaTexto({
  valor,
  onCommit,
  numerico,
  className,
}: {
  valor: string
  onCommit: (novoValor: string) => void
  // Quantidade aceita só número (2026-07-17, pedido explícito: "deixa o campo aberto
  // aceitando só números"). `type="number"` (tentativa anterior) foi revertido -- pedido
  // explícito: "esse seletor aí ficou um lixo" (as setinhas de incremento/decremento do
  // input nativo, que nem fazem sentido pra um código de quantidade). `type="text"` +
  // filtro no onChange (só dígitos, um "." opcional pra quantidade fracionária) +
  // `inputMode="decimal"` -- mantém o teclado numérico no celular sem o visual de spinner.
  numerico?: boolean
  className: string
}) {
  const [local, setLocal] = useState(valor)
  useEffect(() => setLocal(valor), [valor])
  return (
    <input
      type="text"
      inputMode={numerico ? 'decimal' : undefined}
      value={local}
      onChange={(e) => setLocal(numerico ? e.target.value.replace(/[^0-9.]/g, '') : e.target.value)}
      onBlur={() => {
        if (local !== valor) onCommit(local)
      }}
      className={className}
    />
  )
})

// Linha memoizada (2026-07-17) -- `linha` só muda de referência quando ela mesma é editada.
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

export default function ListaTecnicaPage() {
  const { mongoId } = useParams<{ mongoId: string }>()
  const navigate = useNavigate()
  const [bitin, setBitin] = useState<Bitin | null>(null)
  const [materiais, setMateriais] = useState<MaterialEditavel[]>([])
  const [linhas, setLinhas] = useState<LinhaListaTecnica[]>([linhaVazia()])
  const [conteudoExistente, setConteudoExistente] = useState<Record<string, unknown>>({})
  const [carregando, setCarregando] = useState(true)
  const [salvando, setSalvando] = useState(false)
  const [erro, setErro] = useState<string | null>(null)
  // Seleção por _id estável, não índice (2026-07-17) -- mesmo motivo de CodigosSapPage.tsx.
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
        const materiaisExistentes = ((resp.data.content.materiais as MaterialEditavel[] | undefined) ?? []).map(normalizarMaterial)
        setMateriais(materiaisExistentes)
        setLinhas(materiaisParaLinhas(materiaisExistentes))
      })
      .catch(() => setErro('Não foi possível carregar os dados.'))
      .finally(() => setCarregando(false))
    return () => {
      cancelado = true
    }
  }, [mongoId])

  // useCallback (2026-07-17) -- identidade estável permite o React.memo de LinhaTecnicaRow/
  // CelulaTexto pular re-render de linhas não tocadas. Operam por `_id`, não índice.
  const atualizarCampo = useCallback((id: string, campo: keyof LinhaListaTecnicaBase, valor: string) => {
    setLinhas((atual) => {
      const copia = atual.map((l) => (l._id === id ? { ...l, [campo]: valor } : l))
      // Igual à ZBPP009: garante sempre uma linha em branco no final pra continuar digitando.
      if (copia.every((l) => l.codigo_pai.trim() !== '' || l.codigo_filho.trim() !== '')) copia.push(linhaVazia())
      return copia
    })
    setSujo(true)
  }, [setSujo])

  const removerLinha = useCallback((id: string) => {
    setLinhas((atual) => atual.filter((l) => l._id !== id))
    setSelecionadas((atual) => {
      if (!atual.has(id)) return atual
      const copia = new Set(atual)
      copia.delete(id)
      return copia
    })
    setSujo(true)
  }, [setSujo])

  // Mesma barra de ferramentas da ZBPP009 (CodigosSapPage.tsx), 2026-07-16 -- decisão do
  // usuário: "faz isso tb na lista técnica".
  const removerSelecionadas = useCallback(() => {
    setLinhas((atual) => {
      const restantes = atual.filter((l) => !selecionadas.has(l._id))
      if (restantes.length === 0) return [linhaVazia()]
      // Mesma regra de "sempre uma linha em branco no final" usada em atualizarCampo.
      if (restantes.every((l) => l.codigo_pai.trim() !== '' || l.codigo_filho.trim() !== '')) restantes.push(linhaVazia())
      return restantes
    })
    setSelecionadas(new Set())
    setSujo(true)
  }, [selecionadas, setSujo])

  function limparTudo() {
    if (!window.confirm('Limpar toda a tabela? Essa ação não pode ser desfeita.')) return
    setLinhas([linhaVazia()])
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
    // Força o commit do blur ANTES de ler o estado (2026-07-17, mesmo truque de
    // CodigosSapPage.tsx) -- células de texto só propagam pro estado da linha no blur.
    if (document.activeElement instanceof HTMLElement) document.activeElement.blur()
    await new Promise((resolve) => setTimeout(resolve, 0))

    setErro(null)
    setSalvando(true)
    try {
      let linhasAtuais: LinhaListaTecnica[] = []
      setLinhas((atual) => {
        linhasAtuais = atual
        return atual
      })

      // Linha sem código pai ou sem código filho não vira componente de verdade (mesma regra
      // de "linha em branco não persiste" da ZBPP009/BitinDetail).
      const linhasPreenchidas = linhasAtuais.filter((l) => l.codigo_pai.trim() !== '' && l.codigo_filho.trim() !== '')
      const grupos = new Map<string, ItemListaTecnica[]>()
      for (const l of linhasPreenchidas) {
        const { codigo_pai, _id, ...item } = l
        const chave = codigo_pai.trim()
        // Operação derivada aqui (2026-07-17, campo removido da UI) -- ver derivarOperacao.
        grupos.set(chave, [...(grupos.get(chave) ?? []), { ...item, operacao: derivarOperacao(item) }])
      }

      let materiaisAtualizados = materiais.map((m) => ({
        ...m,
        alteracoes: { ...m.alteracoes, lista_tecnica: grupos.get(m.codigo_material.trim()) ?? [] },
      }))
      for (const [codigoPai, itens] of grupos) {
        if (!materiaisAtualizados.some((m) => m.codigo_material.trim() === codigoPai)) {
          materiaisAtualizados = [
            ...materiaisAtualizados,
            {
              ...materialVazio(),
              codigo_material: codigoPai,
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
      setLinhas(materiaisParaLinhas(materiaisAtualizados))
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

  // "Importar" (2026-07-15): salva e volta direto pra aba BITin -- mesma ideia da ZBPP009
  // (decisão do usuário: "tudo oque ele fizeram ali faz a automação e completa direto la na
  // tela de BITin"). A checklist "Alteração lista técnica" é recalculada automaticamente lá.
  async function importar() {
    await salvar()
    navigate(`/bitins/${mongoId}`)
  }

  if (carregando) {
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
        {bitin && <StatusBadge status={bitin.status} />}
        <span className="text-sm text-ink-muted">— Lista Técnica</span>
        <AjudaPopover titulo="Como usar a Lista Técnica">
          <p>
            Cada linha é um componente filho -- <strong>Código pai</strong> é texto livre, não
            precisa existir ainda em BITin/ZBPP009 (se não existir, um material novo é criado
            automaticamente ao salvar, só com esse código, pra receber os componentes).
          </p>
          <p>
            Sem campo de <strong>Operação</strong> pra escolher -- é deduzido sozinho pelo que
            você preenche: só "Quantidade para" = item novo (Inserir); só "Quantidade de" =
            item removido (Excluir); os dois preenchidos = alteração normal (Alterar).
          </p>
          <p>
            <strong>Salvar</strong> guarda sem sair da tela. <strong>Importar</strong> salva e já
            leva pra aba BITin -- lá a checklist "Alteração lista técnica" é marcada
            automaticamente.
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
              setLinhas((atual) => [...atual, linhaVazia()])
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
                    checked={linhas.length > 0 && selecionadas.size === linhas.length}
                    onChange={alternarSelecaoTodas}
                    aria-label="Selecionar todas as linhas"
                  />
                </th>
                <th className="whitespace-nowrap px-3 py-2 font-medium">Código pai</th>
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

      {mongoId && <EdicaoBottomBar mongoId={mongoId} enviando={enviando || salvando} onEnviar={handleEnviar} />}
    </div>
  )
}
