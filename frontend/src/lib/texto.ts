// Ignora acento/maiúscula pra busca tolerante (2026-07-16, criada em MaterialEditorCard.tsx
// pro combobox "+ Campo alterado"; extraída pra cá em 2026-07-21 pra ser reaproveitada também
// pelo filtro de campos da ZBPP009, CodigosSapPage.tsx -- mesma necessidade: achar "Nível
// Revisão" digitando "ni", sem o acento atrapalhar o match).
export function normalizar(s: string): string {
  return s.normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase()
}
