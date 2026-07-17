// Extraído de CriarUsuarioForm.tsx (2026-07-17) -- GestaoUsuarios.tsx passou a precisar do
// mesmo rascunho de e-mail na reativação de usuário (POST /users/{id}/reativar também gera
// senha temporária nova agora, mesmo padrão de cadastro), duplicar essa string dava dois
// lugares pra manter o texto em sincronia.
export function montarMailtoSenhaTemporaria(destino: { nome: string; senha: string; email: string }): string {
  return `mailto:${destino.email}?subject=${encodeURIComponent(
    `Acesso ao sistema BITin / senha temporária`,
  )}&body=${encodeURIComponent(
    `Olá, ${destino.nome},\n\n` +
      `Sua conta no BITin foi criada. Use a senha temporária abaixo para o seu primeiro login:\n\n` +
      `Senha temporária: ${destino.senha}\n\n` +
      `Acesse com seu e-mail corporativo.\n\n` +
      `No primeiro login você será obrigado(a) a definir uma senha só sua.\n\n` +
      `A nova senha precisa ter pelo menos 8 caracteres e incluir pelo menos 3 destes 4 tipos: ` +
      `letra maiúscula, letra minúscula, número, caractere especial.`,
  )}`
}
