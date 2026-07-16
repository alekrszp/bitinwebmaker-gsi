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
interface LinhaListaTecnica extends ItemListaTecnica {
  codigo_pai: string
}

function linhaVazia(): LinhaListaTecnica {
  return { codigo_pai: '', operacao: 'alterar', codigo_filho: '', quantidade_de: '', quantidade_para: '' }
}

function materiaisParaLinhas(materiais: MaterialEditavel[]): LinhaListaTecnica[] {
  const linhas = materiais.flatMap((m) =>
    m.alteracoes.lista_tecnica.map((item) => ({ codigo_pai: m.codigo_material, ...item })),
  )
  // Sempre sobra uma linha em branco no final pra continuar preenchendo (mesmo padrão da
  // ZBPP009 -- não obriga clicar em "+ Nova linha" primeiro).
  return [...linhas, linhaVazia()]
}

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
  const [selecionadas, setSelecionadas] = useState<Set<number>>(new Set())
  const { enviando, errosEnvio, bitinEnviado, enviar } = useEnviarBitin(mongoId)

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

  function atualizarLinha(index: number, campo: keyof LinhaListaTecnica, valor: string) {
    setLinhas((atual) => {
      const copia = atual.map((l, i) => (i === index ? { ...l, [campo]: valor } : l))
      // Igual à ZBPP009: garante sempre uma linha em branco no final pra continuar digitando.
      if (copia.every((l) => l.codigo_pai.trim() !== '' || l.codigo_filho.trim() !== '')) copia.push(linhaVazia())
      return copia
    })
  }

  function removerLinha(index: number) {
    setLinhas((atual) => atual.filter((_, i) => i !== index))
  }

  // Mesma barra de ferramentas da ZBPP009 (CodigosSapPage.tsx), 2026-07-16 -- decisão do
  // usuário: "faz isso tb na lista técnica". Seleção por índice; "Excluir selecionadas" filtra
  // numa única passada (não faz .splice em loop) pra não deslocar índices e apagar a linha
  // errada.
  function removerSelecionadas() {
    setLinhas((atual) => {
      const restantes = atual.filter((_, i) => !selecionadas.has(i))
      if (restantes.length === 0) return [linhaVazia()]
      // Mesma regra de "sempre uma linha em branco no final" usada em atualizarLinha.
      if (restantes.every((l) => l.codigo_pai.trim() !== '' || l.codigo_filho.trim() !== '')) restantes.push(linhaVazia())
      return restantes
    })
    setSelecionadas(new Set())
  }

  function limparTudo() {
    if (!window.confirm('Limpar toda a tabela? Essa ação não pode ser desfeita.')) return
    setLinhas([linhaVazia()])
    setSelecionadas(new Set())
  }

  function alternarSelecao(index: number) {
    setSelecionadas((atual) => {
      const copia = new Set(atual)
      if (copia.has(index)) copia.delete(index)
      else copia.add(index)
      return copia
    })
  }

  function alternarSelecaoTodas() {
    setSelecionadas((atual) => (atual.size === linhas.length ? new Set() : new Set(linhas.map((_, i) => i))))
  }

  async function salvar() {
    setErro(null)
    setSalvando(true)
    try {
      // Linha sem código pai ou sem código filho não vira componente de verdade (mesma regra
      // de "linha em branco não persiste" da ZBPP009/BitinDetail).
      const linhasPreenchidas = linhas.filter((l) => l.codigo_pai.trim() !== '' && l.codigo_filho.trim() !== '')
      const grupos = new Map<string, ItemListaTecnica[]>()
      for (const l of linhasPreenchidas) {
        const { codigo_pai, ...item } = l
        const chave = codigo_pai.trim()
        grupos.set(chave, [...(grupos.get(chave) ?? []), item])
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
      <Link to={`/bitins/${mongoId}`} className="text-sm text-ink-muted hover:text-ink hover:underline">
        ← Voltar pro BITin
      </Link>

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
            <strong>Operação</strong>: Inserir (novo, exige "Quantidade para"), Alterar (padrão,
            exige "Quantidade para") ou Excluir (exige "Quantidade de").
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
            onClick={() => setLinhas((atual) => [...atual, linhaVazia()])}
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
                <th className="whitespace-nowrap px-3 py-2 font-medium">Operação</th>
                <th className="whitespace-nowrap px-3 py-2 font-medium">Código filho</th>
                <th className="whitespace-nowrap px-3 py-2 font-medium">Quantidade de</th>
                <th className="whitespace-nowrap px-3 py-2 font-medium">Quantidade para</th>
                <th className="w-10" />
              </tr>
            </thead>
            <tbody className="divide-y divide-line">
              {linhas.map((l, i) => (
                <tr key={i}>
                  <td className="px-3 py-1.5 text-center">
                    <input
                      type="checkbox"
                      checked={selecionadas.has(i)}
                      onChange={() => alternarSelecao(i)}
                      aria-label={`Selecionar linha ${i + 1}`}
                    />
                  </td>
                  <td className="p-1.5">
                    <input
                      type="text"
                      value={l.codigo_pai}
                      onChange={(e) => atualizarLinha(i, 'codigo_pai', e.target.value)}
                      className="w-32 rounded border border-line bg-surface px-2 py-1.5 text-sm text-ink focus:border-brand-navy focus:outline-none"
                    />
                  </td>
                  <td className="p-1.5">
                    <select
                      value={l.operacao}
                      onChange={(e) => atualizarLinha(i, 'operacao', e.target.value as OperacaoListaTecnica)}
                      className="dark:[color-scheme:dark] [color-scheme:light] w-32 rounded border border-line bg-surface px-2 py-1.5 text-sm text-ink focus:border-brand-navy focus:outline-none"
                    >
                      <option value="inserir">Inserir</option>
                      <option value="alterar">Alterar</option>
                      <option value="excluir">Excluir</option>
                    </select>
                  </td>
                  <td className="p-1.5">
                    <input
                      type="text"
                      value={l.codigo_filho}
                      onChange={(e) => atualizarLinha(i, 'codigo_filho', e.target.value)}
                      className="w-40 rounded border border-line bg-surface px-2 py-1.5 text-sm text-ink focus:border-brand-navy focus:outline-none"
                    />
                  </td>
                  <td className="p-1.5">
                    <input
                      type="text"
                      value={l.quantidade_de}
                      onChange={(e) => atualizarLinha(i, 'quantidade_de', e.target.value)}
                      disabled={l.operacao === 'inserir'}
                      className="w-28 rounded border border-line bg-surface px-2 py-1.5 text-sm text-ink focus:border-brand-navy focus:outline-none disabled:opacity-40"
                    />
                  </td>
                  <td className="p-1.5">
                    <input
                      type="text"
                      value={l.quantidade_para}
                      onChange={(e) => atualizarLinha(i, 'quantidade_para', e.target.value)}
                      disabled={l.operacao === 'excluir'}
                      className="w-28 rounded border border-line bg-surface px-2 py-1.5 text-sm text-ink focus:border-brand-navy focus:outline-none disabled:opacity-40"
                    />
                  </td>
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
      </Card>

      {mongoId && <EdicaoBottomBar mongoId={mongoId} enviando={enviando || salvando} onEnviar={handleEnviar} />}
    </div>
  )
}
