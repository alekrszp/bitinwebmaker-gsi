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

// Sugestão automática (2026-07-17, ver scripts/bitin_document.py::suggest_impactos) --
// derivada do código de Grupo de Mercadorias, NUNCA autoritativa (o campo que vale é sempre
// o que o engenheiro declarou em impactos_operacionais). `null` = código SAP desconhecido/
// não mapeado, não sugere nada -- não é erro. BitinDetail.tsx só aplica a sugestão quando o
// campo correspondente ainda está em branco ("-"), nunca sobrescreve o que já foi declarado.
export interface SugestoesImpactos {
  alt: string | null
  esp: string | null
  dwg_sat_acao: string | null
}

export interface MaterialResumo {
  codigo_material: string
  descricao_material: string
  centro: string
  tipo_material: string
  impactos_operacionais: Record<string, unknown>
  dados_basicos_alterados: CampoAlterado[]
  lista_tecnica: ItemListaTecnicaResumo[]
  sugestoes: SugestoesImpactos
  // Lembrete "REVISAR ROTEIRO" (Módulo4.bas) -- true quando o Alt declarado é "D/P" ou "-/P".
  // Não afeta checklist/setores, é só um aviso visual pro engenheiro revisar o roteiro de
  // fabricação (mesmo raciocínio da macro original).
  revisar_roteiro: boolean
}

export interface BitinResumo {
  bitin: string
  status: string
  data_envio: string | null
  // Fila do setor Cadastro (2026-07-17, ver scripts/bitin_lifecycle.py::encaminhar_para_roteiro)
  encaminhado_roteiro: boolean
  data_encaminhado_roteiro: string | null
  // Setor Processos (2026-07-17, ver scripts/bitin_lifecycle.py::concluir_processamento)
  processos_concluido: boolean
  data_processos_concluido: string | null
  setor: string
  produto: string
  motivo: string
  solicitante: string
  // "SIM"/"NÃO"/"" -- ver docs/BITIN_MODEL.md (campo bitex do cabeçalho)
  bitex: string
  materiais: MaterialResumo[]
  checklist: ChecklistItem[]
  setores_afetados: string[]
  ordem_cliente: OrdemClienteItem[]
  // Linha do tempo de eventos principais (2026-07-22, ver backend/api/bitins.py::
  // _evento_historico) -- criação, envio, cada passo de Processos/Cadastro/Windchill.
  historico: { usuario: string; data: string; acao: string }[]
}
