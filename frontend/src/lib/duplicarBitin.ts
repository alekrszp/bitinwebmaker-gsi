import type { NavigateFunction } from 'react-router-dom'
import { api } from './api'

// "Duplicar" (2026-07-22, pedido explícito -- ideia de brainstorm: "se dois BITins costumam
// ser parecidos... começar do zero toda vez é retrabalho") -- cria um rascunho NOVO com os
// dados de conteúdo de um BITin existente (materiais, checklist, Ordem de Cliente, BITex),
// sem carregar nada do CICLO DE VIDA do original (número, status, datas de roteamento/
// cadastro/Windchill, histórico) -- mesmo espírito de `criarRascunhoENavegar` (lib/criarBitin.ts),
// só que pré-preenchido em vez de em branco. `solicitante`/`data_solicitacao` não são mandados
// de propósito -- o backend carimba a partir de quem está logado, igual a qualquer rascunho
// novo (não faz sentido "herdar" o solicitante de quem criou o original).
const CAMPOS_DUPLICAVEIS = [
  'produto', 'motivo', 'setor', 'materiais', 'ordem_cliente',
  'checklist_overrides', 'checklist_descricoes', 'bitex',
] as const

export async function duplicarBitinENavegar(mongoId: string, navigate: NavigateFunction): Promise<void> {
  const origem = await api.get(`/bitins/${mongoId}`)
  const conteudoOrigem = origem.data.content as Record<string, unknown>
  const content: Record<string, unknown> = {}
  for (const campo of CAMPOS_DUPLICAVEIS) {
    if (campo in conteudoOrigem) content[campo] = conteudoOrigem[campo]
  }
  // Sinaliza a cópia no próprio motivo -- evita 2 BITins com motivo idêntico se confundirem na
  // listagem antes do engenheiro editar (fica óbvio de onde veio, fácil de apagar depois).
  const motivoOriginal = String(conteudoOrigem.motivo ?? '')
  content.motivo = motivoOriginal ? `${motivoOriginal} (cópia)` : 'Cópia'

  const resp = await api.post('/bitins/draft', { content })
  navigate(`/bitins/${resp.data.mongo_id}`)
}
