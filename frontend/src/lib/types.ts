// Espelha backend/auth/schemas.py::UserOut -- devolvido por GET /users/me.
export interface User {
  id: number
  email: string
  nome: string
  ativo: boolean
  permission_level: number
  network_id: string | null
  // Lista de ids de Subgrupo (2026-07-15, era sector_id único -- "um usuário poder ser tanto
  // armazenagem tanto quanto proteina"). Espelha backend/auth/schemas.py::UserOut.subgrupo_ids.
  subgrupo_ids: number[]
  // Rótulo de papel (2026-07-16, NOVO, desacoplado de permission_level e de subgrupo_ids --
  // admin define os três independentemente, sem vínculo automático). Espelha
  // backend/auth/schemas.py::UserOut.setor.
  setor: string
  created_at: string
  // Espelha Usuario.senha_temporaria (backend/auth/models.py) -- True quando a senha atual foi
  // gerada por um admin (POST /users) e ainda não foi trocada pelo dono da conta.
  // RequireAuth.tsx usa isso pra forçar a rota /definir-senha antes de liberar o resto do app.
  senha_temporaria: boolean
  // Espelha UserOut.eh_super_admin (2026-07-20) -- só a conta fixa em
  // backend/auth/security.py::CONTAS_SUPER_ADMIN tem true aqui. Usado só pra decidir se
  // "Gestão de usuários" aparece no menu (Sidebar.tsx); a checagem que protege de verdade
  // fica no backend.
  eh_super_admin: boolean
}

// Espelha backend/auth/schemas.py::AdminUserCreate -- corpo de POST /users (cadastro de
// usuário SÓ POR ADMIN, 2026-07-15, Settings.tsx -- GestaoUsuarios).
export interface AdminUserCreateRequest {
  email: string
  nome: string
  numero_eng: string | null
  subgrupo_ids: number[]
  permission_level: number
  // Rótulo de papel (2026-07-16, NOVO) -- 'cadastro' | 'gestor' | 'usuario'. Independente de
  // permission_level e subgrupo_ids, admin escolhe os três separadamente.
  setor: string
  // Senha do PRÓPRIO admin que está cadastrando (2026-07-16, pedido explícito: reconfirmar
  // identidade antes de criar conta) -- espelha backend/auth/schemas.py::AdminUserCreate.
  senha_admin: string
}

// Espelha backend/auth/schemas.py::UserUpdateSubgrupos -- corpo de
// PATCH /users/{id}/subgrupos (Settings.tsx -- GestaoUsuarios, reatribuição de subgrupo de
// usuário já cadastrado, 2026-07-16).
export interface UserUpdateSubgruposRequest {
  subgrupo_ids: number[]
}

// Espelha backend/auth/schemas.py -- corpo de PATCH /users/{id}/setor (2026-07-16, NOVO,
// admin-only) pra trocar só o rótulo de papel do usuário depois de cadastrado.
export interface UserUpdateSetorRequest {
  setor: string
}

// Espelha backend/auth/schemas.py::AdminUserCreateOut -- resposta de POST /users. Inclui a
// senha temporária em texto puro, devolvida UMA ÚNICA VEZ (não fica recuperável depois).
export interface AdminUserCreateResponse extends User {
  senha_temporaria_gerada: string
}

// Espelha backend/auth/schemas.py::UserReactivate -- corpo de POST /users/{id}/reativar
// (2026-07-17, NOVO). Resposta é o mesmo shape de AdminUserCreateResponse -- reativar sempre
// gera senha nova, mesmo padrão de cadastro.
export interface UserReactivateRequest {
  email: string
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

// Espelha backend/auth/schemas.py::SubgrupoOut -- devolvido por GET /subgrupos (público).
export interface Subgrupo {
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
  // Fila do setor Cadastro (2026-07-17, ver scripts/bitin_lifecycle.py::encaminhar_para_roteiro)
  encaminhado_roteiro: boolean
  data_encaminhado_roteiro: string | null
  // Setor Processos (2026-07-17, ver scripts/bitin_lifecycle.py::concluir_processamento)
  processos_concluido: boolean
  data_processos_concluido: string | null
  // true quando chegou ao estado final sem passar pela reedição do Processos (ver
  // scripts/bitin_lifecycle.py::concluir_sem_roteiro) -- só pra exibição/auditoria, os
  // filtros continuam lendo processos_concluido.
  sem_necessidade_roteiro: boolean
  // Calculado por requisição (ver scripts/bitin_document.py::precisa_roteiro) -- decide se
  // CadastroPage.tsx mostra "Encaminhar para roteiro" ou "Não precisa de roteiro".
  precisa_roteiro: boolean
  // Penúltimo passo do fluxo (2026-07-20, ver scripts/bitin_lifecycle.py::concluir_bitin) --
  // só depois disso o PDF fica disponível na aba "Cadastrados" de CadastroPage.tsx.
  bitin_cadastrado: boolean
  data_cadastrado: string | null
  // Última etapa de todas (2026-07-20, ver scripts/bitin_lifecycle.py::enviar_windchill).
  windchill_enviado: boolean
  data_windchill_enviado: string | null
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

// Editável -- espelha scripts/bitin_model.py::validate_ordem_cliente (codigo obrigatório,
// pelo menos 1 item em acrescentar_no_pedido OU retira_do_pedido). Achado em 2026-07-20: o
// campo já era validado no envio (POP Nota 10: material com OC="X" exige entrada
// correspondente aqui) mas não existia NENHUM formulário editável na tela -- só uma exibição
// só-leitura (OrdemClienteSection.tsx, ver bitinTypes.ts::OrdemClienteItem) alimentada pelo
// resumo calculado. Sem isso, era impossível enviar um BITin com OC="X" pela UI.
export interface ItemPedidoEditavel {
  codigo_material: string
  quantidade: string
}

export interface OrdemClienteEditavel {
  codigo: string
  descricao: string
  acrescentar_no_pedido: ItemPedidoEditavel[]
  retira_do_pedido: ItemPedidoEditavel[]
}
