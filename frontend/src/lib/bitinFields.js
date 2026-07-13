// Helpers de leitura/escrita imutável do formato materiais[] do BITin (ver
// docs/BITIN_MODEL.md). Mantidos separados do componente de grid porque o mesmo formato
// também é usado pela tela de resumo/visualização.

export function blankMaterial() {
  return {
    codigo_material: '',
    descricao_material: '',
    centro: '',
    tipo_material: '',
    grupo_mercadorias_atual: '',
    tem_desenho: false,
    desenho_aprovado: false,
    ncm_aprovado_fiscal: false,
    alteracoes: { dados_basicos: {}, impactos_operacionais: {} },
  }
}

export function getDadosBasico(material, campo, sub) {
  return material.alteracoes?.dados_basicos?.[campo]?.[sub] ?? ''
}

export function setDadosBasico(material, campo, sub, valor) {
  const atual = material.alteracoes?.dados_basicos?.[campo] ?? { de: '', para: '' }
  return {
    ...material,
    alteracoes: {
      ...material.alteracoes,
      dados_basicos: {
        ...material.alteracoes?.dados_basicos,
        [campo]: { ...atual, [sub]: valor },
      },
    },
  }
}

export function getImpacto(material, campo) {
  return material.alteracoes?.impactos_operacionais?.[campo] ?? ''
}

export function setImpacto(material, campo, valor) {
  return {
    ...material,
    alteracoes: {
      ...material.alteracoes,
      impactos_operacionais: {
        ...material.alteracoes?.impactos_operacionais,
        [campo]: valor,
      },
    },
  }
}

// Colar do SAP devolve só identificação + snapshot atual (ver sap_paste_parser.py) --
// completa com a estrutura de alteracoes vazia pra virar uma linha editável do grid.
export function materialFromSapPaste(parsed) {
  return { ...blankMaterial(), ...parsed }
}
