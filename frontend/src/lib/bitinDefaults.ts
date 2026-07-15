import type { MaterialEditavel } from './types'

// Material em branco -- usado tanto na aba "BITin" ("+ Novo material", cadastro direto à mão)
// quanto em Códigos SAP ("+ Nova linha") -- as duas telas operam sobre o mesmo materiais[] do
// JSON do BITin, nenhuma depende da outra pra criar um material (decisão do usuário,
// 2026-07-15: "tudo se conecta, tudo se complementa, nada depende de um do outro").
export function materialVazio(): MaterialEditavel {
  return {
    codigo_material: '',
    descricao_material: '',
    centro: '',
    // "HALB" (semiacabado) como padrão -- campo obrigatório (REQUIRED_MATERIAL_FIELDS em
    // bitin_model.py) mas o input dele saiu da UI (decisão do usuário, 2026-07-15: "tirar o
    // campo tipo de material ali do bloco do código, deixa isso escondido"), então precisa de
    // um valor não-vazio pra não travar a validação de envio. "HALB" é o valor mais comum nos
    // dados reais/fixtures de teste do projeto (A263326.xlsm); ajustável depois se algum fluxo
    // real precisar de outro tipo (não há hoje campo de UI pra corrigir isso manualmente).
    tipo_material: 'HALB',
    alteracoes: {
      dados_basicos: {},
      impactos_operacionais: {
        alt: '-', est: '-', esp: '-', lp: '-', pre: '-', oc: '-', of: '-',
        atualizar_dwg_sat: false,
      },
      lista_tecnica: [],
    },
  }
}

// Materiais salvos antes de um campo existir no modelo (ex.: BITins criados antes de
// "lista_tecnica" ganhar tela própria) chegam do backend sem esse campo -- normaliza pra
// nunca quebrar a tela com "Cannot read properties of undefined" (bug real encontrado em
// 2026-07-15: Lista Técnica ficava em branco/travada pra qualquer BITin salvo antes dessa
// tela existir). Sempre rodar isso ao carregar materiais[] do backend, nas 3 telas de edição.
export function normalizarMaterial(m: MaterialEditavel): MaterialEditavel {
  return {
    ...m,
    alteracoes: {
      ...m.alteracoes,
      dados_basicos: m.alteracoes?.dados_basicos ?? {},
      lista_tecnica: m.alteracoes?.lista_tecnica ?? [],
      impactos_operacionais: {
        ...materialVazio().alteracoes.impactos_operacionais,
        ...m.alteracoes?.impactos_operacionais,
      },
    },
  }
}
