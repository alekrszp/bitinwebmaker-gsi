// Extrai mensagem de erro de uma resposta da API -- duas formas possíveis: {detail: string}
// (ex.: senha atual incorreta, backend/auth/routes.py::change_password) ou {detail: [{msg}]}
// (erro de validação do Pydantic, ex.: senha nova fraca, backend/auth/schemas.py::
// ChangePasswordRequest). Duck-typing (não usa axios.isAxiosError) -- extraído de
// Settings.tsx/DefinirSenha.tsx, que duplicavam essa função verbatim.
export function extrairErro(err: unknown, fallback: string): string {
  const detail = (err as { response?: { data?: { detail?: unknown } } })?.response?.data?.detail
  if (typeof detail === 'string') return detail
  if (Array.isArray(detail) && detail[0]?.msg) return String(detail[0].msg)
  return fallback
}
