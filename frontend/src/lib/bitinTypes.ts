// Espelha o formato de GET /bitins/{mongo_id}/resumo (scripts/bitin_view.py::
// render_bitin_summary) -- usado tanto pelo modo só-leitura quanto pelo modo edição de
// BitinDetail.tsx (checklist/setores acionados são sempre calculados pelo backend, nunca
// reimplementados no frontend). Extraído pra fora de BitinDetail.tsx pra ser reaproveitado
// pelos componentes de bitin/ sem cada um redeclarar os mesmos tipos.
// `descricao` (2026-07-15): anotação livre por item, digitada pelo engenheiro -- usada
// principalmente no item 22 ("Centro de custo (se tem sucata)") pra registrar centro de
// custo/conta razão do sucateamento (POP Nota 8), decisão do usuário: "isso é colocado no
// campo de descrição lá em cima na checklist ao lado do campo da checklist referente".
export interface ChecklistItem {
  id: string
  etapa: string
  afeta: boolean
  manual: boolean
  descricao: string
}

export interface ItemPedido {
  codigo_material: string
  quantidade: string
}

export interface OrdemClienteItem {
  codigo: string
  descricao: string
  acrescentar_no_pedido: ItemPedido[]
  retira_do_pedido: ItemPedido[]
}

export interface CampoAlterado {
  campo: string
  de: string
  para: string
  livre: boolean
}

export interface ItemListaTecnicaResumo {
  codigo_filho: string
  quantidade_de: string
  quantidade_para: string
}

export interface MaterialResumo {
  codigo_material: string
  descricao_material: string
  centro: string
  tipo_material: string
  impactos_operacionais: Record<string, unknown>
  dados_basicos_alterados: CampoAlterado[]
  lista_tecnica: ItemListaTecnicaResumo[]
}

export interface BitinResumo {
  bitin: string
  status: string
  data_envio: string | null
  setor: string
  produto: string
  motivo: string
  solicitante: string
  materiais: MaterialResumo[]
  checklist: ChecklistItem[]
  setores_afetados: string[]
  ordem_cliente: OrdemClienteItem[]
}
