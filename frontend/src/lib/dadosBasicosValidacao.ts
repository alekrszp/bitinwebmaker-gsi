// Domínio de valores válidos por campo de dados_basicos (2026-07-21, pedido explícito: "faz o
// seguinte, pega as informações de campo que tu já tem, e aplica essa validação em cima dos
// campos") -- aviso em tempo real, nunca bloqueia a digitação (mesmo espírito de
// bitin_business_rules.py::validate_business_rules, que só barra no envio). Campo vazio nunca
// é erro (ainda não foi preenchido); só valida o que já tem valor.
//
// nivel_revisao: letra de revisão SAP, sempre 1 maiúscula (ex. "C" -> "D", visto em BITin
// real). Os 3 campos abaixo são marcações tipo "X"/"-" (mesmo domínio já usado por Esp em
// impactos_operacionais, ANEXO A do POP) -- suspeitos pelo nome (flag de produção interna,
// flag de eliminação em nível mandante/centro), confirmados como os únicos 3 campos booleanos
// desta rodada. Todo o resto continua string livre, sem validação.
const _NIVEL_REVISAO_RE = /^[A-Z]$/
const _CAMPOS_BOOLEAN_X_TRACO = new Set(['producao_interna', 'marcacao_eliminar_nivel_mandante', 'marcacao_eliminar_nivel_centro'])

export function erroDominioCampo(campo: string, valor: string): string | null {
  if (valor === '') return null
  if (campo === 'nivel_revisao') {
    return _NIVEL_REVISAO_RE.test(valor) ? null : 'Deve ser 1 letra maiúscula (A-Z)'
  }
  if (_CAMPOS_BOOLEAN_X_TRACO.has(campo)) {
    return valor === 'X' || valor === '-' ? null : 'Valores aceitos: X ou -'
  }
  return null
}
