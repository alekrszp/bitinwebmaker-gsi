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
export type Etapa = 'Recebido (Cadastro)' | 'Com Processos' | 'Aguardando cadastro' | 'Pendência de envio'

export function etapaDoBitin(b: Pick<Bitin, 'status' | 'windchill_enviado' | 'bitin_cadastrado' | 'processos_concluido' | 'encaminhado_roteiro'>): Etapa | null {
  if (statusDoBitin(b) !== 'Enviado') return null
  if (b.bitin_cadastrado) return 'Pendência de envio'
  if (b.processos_concluido) return 'Aguardando cadastro'
  if (b.encaminhado_roteiro) return 'Com Processos'
  return 'Recebido (Cadastro)'
}

export const ETAPAS: Etapa[] = ['Recebido (Cadastro)', 'Com Processos', 'Aguardando cadastro', 'Pendência de envio']

// Setor responsável por cada etapa -- quem tem o BITin em mãos agora.
export const RESPONSAVEL_POR_ETAPA: Record<Etapa, string> = {
  'Recebido (Cadastro)': 'Cadastro',
  'Com Processos': 'Processos',
  'Aguardando cadastro': 'Cadastro',
  'Pendência de envio': 'Cadastro',
}
