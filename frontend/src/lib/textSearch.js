// Busca insensível a acento -- achado testando o painel de Detalhes: buscar "liquido" não
// encontrava "Peso Líquido" porque a comparação era string literal (í != i). Usuário digitando
// rápido em português raramente acentua a busca, então normaliza os dois lados (remove os
// marcadores de acentuação combinantes do Unicode e usa minúsculas) antes de comparar.
//
// Construído via String.fromCharCode (em vez de um literal /[̀-ͯ]/) de propósito:
// digitar esse intervalo como escape de regex nesta ferramenta de edição estava sendo
// silenciosamente convertido pro caractere combinante de verdade em vez do texto do escape,
// corrompendo o arquivo -- isso evita depender de digitar o escape literal.
const DIACRITICS_RANGE = String.fromCharCode(0x0300) + '-' + String.fromCharCode(0x036f)
const DIACRITICS_RE = new RegExp('[' + DIACRITICS_RANGE + ']', 'g')

export function normalizeForSearch(texto) {
  return (texto || '').normalize('NFD').replace(DIACRITICS_RE, '').toLowerCase()
}

export function matchesSearch(label, termo) {
  if (!termo) return true
  return normalizeForSearch(label).includes(normalizeForSearch(termo))
}
