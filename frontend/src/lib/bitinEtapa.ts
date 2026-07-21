import type { Bitin } from './types'

// Vocabulário compartilhado (2026-07-20, pedido explícito: "não confunde status com etapa...
// a tela de painel geral e a tela de cadastro e processos devem conversar na mesma língua
// tudo") -- PainelGeral.tsx, CadastroPage.tsx e ProcessosPage.tsx importam DAQUI em vez de
// cada um calcular por conta própria, pra nunca mais divergir.
//
// STATUS: o estado geral do BITin (aparece no StatusBadge, é a mesma coisa em qualquer
// tela). NÃO é o campo `status` bruto do Mongo (que só tem "rascunho"/"enviado", ver
// backend/api/bitins.py -- mudar esse valor quebraria todo filtro `status=enviado` existente
// no sistema) -- "Concluído" é um 3º valor calculado a partir de `windchill_enviado`, exibido
// como se fosse status pro usuário mesmo sem mexer no campo bruto internamente.
export type StatusBitin = 'Rascunho' | 'Enviado' | 'Concluído'

export function statusDoBitin(b: Pick<Bitin, 'status' | 'windchill_enviado'>): StatusBitin {
  if (b.status !== 'enviado') return 'Rascunho'
  if (b.windchill_enviado) return 'Concluído'
  return 'Enviado'
}

// ETAPA: aonde o BITin está parado DENTRO de um setor específico -- só existe enquanto o
// Status é "Enviado" (rascunho não tem etapa nenhuma, é só do engenheiro; "Concluído" também
// não tem mais etapa, já terminou o fluxo e mora numa pasta separada, ver CadastroPage.tsx).
//
// Sem "Recebido (Cadastro)" (2026-07-21, pedido explícito, removido por não servir mais pra
// nada) -- essa etapa representava o intervalo entre "enviado" e o roteamento pro Processos,
// de quando o Cadastro triava manualmente ("Encaminhar para roteiro"/"Não precisa de
// roteiro"). Desde 2026-07-20, `enviar_bitin` já decide e roteia sozinho, na mesma requisição
// do envio (`encaminhar_para_roteiro`/`concluir_sem_roteiro` chamados sincronamente) -- então
// `encaminhado_roteiro` já vem `True` assim que o BITin vira "Enviado", tornando essa etapa
// inatingível na prática (só aparecia em BITins antigos, enviados antes do roteamento
// automático existir, já corrigidos manualmente).
export type Etapa = 'Com Processos' | 'Aguardando cadastro' | 'Pendência de envio'

export function etapaDoBitin(b: Pick<Bitin, 'status' | 'windchill_enviado' | 'bitin_cadastrado' | 'processos_concluido' | 'encaminhado_roteiro'>): Etapa | null {
  if (statusDoBitin(b) !== 'Enviado') return null
  if (b.bitin_cadastrado) return 'Pendência de envio'
  if (b.processos_concluido) return 'Aguardando cadastro'
  return 'Com Processos'
}

export const ETAPAS: Etapa[] = ['Com Processos', 'Aguardando cadastro', 'Pendência de envio']

// Setor responsável por cada etapa -- quem tem o BITin em mãos agora.
export const RESPONSAVEL_POR_ETAPA: Record<Etapa, string> = {
  'Com Processos': 'Processos',
  'Aguardando cadastro': 'Cadastro',
  'Pendência de envio': 'Cadastro',
}
