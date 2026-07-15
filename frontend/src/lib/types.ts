// Espelha backend/auth/schemas.py::UserOut -- devolvido por GET /users/me.
export interface User {
  id: number
  email: string
  nome: string
  ativo: boolean
  permission_level: number
  network_id: string | null
  sector_id: number | null
  created_at: string
}

// Espelha backend/api/bitins.py::ResumoUsuarioResponse -- devolvido por
// GET /bitins/resumo-usuario. Escopado por criado_por ("só os meus", não o sistema
// inteiro) -- decisão registrada, ver docs/FRONTEND.md.
export interface ResumoUsuario {
  rascunhos: number
  enviados: number
}

// Espelha backend/auth/schemas.py::ChangePasswordRequest -- corpo de
// POST /auth/change-password (Settings.tsx, "Minha conta" -- Trocar senha).
export interface ChangePasswordRequest {
  senha_atual: string
  senha_nova: string
}

// Espelha backend/auth/schemas.py::SectorOut -- devolvido por GET /sectors (público).
export interface Sector {
  id: number
  nome: string
  descricao: string | null
}

// Espelha backend/api/bitins.py::BitinResponse -- devolvido por GET /bitins (lista, escopada
// pro próprio usuário -- "Meus Bitins", ver docs/FRONTEND.md) e GET /bitins/{mongo_id}.
export interface Bitin {
  mongo_id: string
  codigo: string | null
  status: string
  titulo: string | null
  content: Record<string, unknown>
  criado_por: string | null
  created_at: string
  updated_at: string
  pode_editar: boolean
}

// Espelha scripts/bitin_model.py::build_materiais_schema -- devolvido por
// GET /bitins/schema/materiais. Fonte única de verdade das colunas do grid de materiais
// (não hardcodar essa lista no frontend, ver docs/BACKEND.md "Grid de materiais dirigido por
// schema").
export interface CampoSchema {
  key: string
  label: string
  required?: boolean
  type?: 'text' | 'boolean'
  options?: string[]
  required_when?: { field: string; equals: string }
}

export interface MateriaisSchema {
  identificacao: CampoSchema[]
  dados_basicos: CampoSchema[]
  impactos_operacionais: CampoSchema[]
}

// Espelha materiais[] dentro de content (ver docs/BITIN_MODEL.md, "Estrutura"). De/Para de
// dados_basicos é um dict {campo: {de, para}} -- inclui campos livres fora do crosswalk
// (scripts/bitin_document.py::build_campo_alterado_diffs já trata isso na visualização).
//
// Códigos SAP (2026-07-15, idêntica à ZBPP009): preenche o "de" dos 30 campos de
// dados_basicos (colar do SAP ou digitar). A aba BITin só declara o "para" dos campos que
// realmente mudaram -- não existe mais um bloco "snapshot" separado (grupo_mercadorias_atual/
// tem_desenho/etc. eram campos inventados fora do JSON canônico, removidos do schema exposto
// pelo backend; os dois campos legados abaixo continuam no tipo só pelo parser antigo do
// colar-do-SAP, não são mais editados nem exibidos na tela).
// Espelha um item de materiais[].alteracoes.lista_tecnica[] (ver docs/BITIN_MODEL.md, "Export
// de lista_tecnica[]" e scripts/lista_tecnica_export.py::validate_lista_tecnica). O código pai
// é o próprio codigo_material do material, não repetido no item. `operacao` nunca aparece na
// visualização (só serve pro cadastro decidir a intenção) -- default "alterar" quando ausente.
export type OperacaoListaTecnica = 'inserir' | 'alterar' | 'excluir'

export interface ItemListaTecnica {
  operacao: OperacaoListaTecnica
  codigo_filho: string
  quantidade_de: string
  quantidade_para: string
}

// centro_custo/conta_razao saíram daqui (2026-07-15) -- viraram a descrição do item 22 da
// checklist ("Centro de custo (se tem sucata)"), não mais um campo por material (decisão do
// usuário: "isso é colocado no campo de descrição lá em cima na checklist ao lado do campo da
// checklist referente"). atualizar_dwg_sat continua no tipo por compatibilidade com BITins
// antigos, mas não tem mais input na tela -- o engenheiro marca o item 18 da checklist
// ("Atualizar DWG / SAT") manualmente quando precisa.
export interface MaterialEditavel {
  codigo_material: string
  descricao_material: string
  centro: string
  tipo_material: string
  grupo_mercadorias_atual?: string
  tem_desenho?: boolean
  alteracoes: {
    dados_basicos: Record<string, { de: string; para: string }>
    impactos_operacionais: {
      alt: string
      est: string
      esp: string
      lp: string
      pre: string
      oc: string
      of: string
      atualizar_dwg_sat: boolean
    }
    lista_tecnica: ItemListaTecnica[]
  }
}
