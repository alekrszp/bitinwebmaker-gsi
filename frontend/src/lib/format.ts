// Helpers de formatação compartilhados. Criado em 2026-07-15 pro campo "Data de envio"
// (resumo.data_envio, string ISO vinda do backend) -- exibe DD.MM.YYYY (pontos, não barras),
// seguindo a convenção de datas do POP/SAP já usada no restante do documento (ver
// docs/BITIN_MODEL.md). Não usar em campos de dados_basicos da ZBPP009: aqueles são snapshot
// de texto livre do SAP, não datas parseadas.
export function formatarDataEnvio(iso: string | null | undefined): string | undefined {
  if (!iso) return undefined
  const data = new Date(iso)
  if (Number.isNaN(data.getTime())) return iso
  const dia = String(data.getDate()).padStart(2, '0')
  const mes = String(data.getMonth() + 1).padStart(2, '0')
  const ano = data.getFullYear()
  return `${dia}.${mes}.${ano}`
}
