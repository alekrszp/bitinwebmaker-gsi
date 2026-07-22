import { etapaDoBitin, type Etapa } from './bitinEtapa'
import type { Bitin } from './types'

// Indicador de "tempo parado" (2026-07-22, pedido explícito -- ideia levantada numa sessão de
// brainstorm sobre features pro Cadastro: "não dá pra saber se um BITin está há 2 horas ou 2
// semanas esperando"). A data de "entrada" na etapa atual já é gravada pelo backend em cada
// passo do roteamento (data_encaminhado_roteiro/data_processos_concluido/data_cadastrado) --
// só falta ler o campo certo pra cada etapa e formatar.
type CamposData = Pick<
  Bitin,
  | 'status' | 'windchill_enviado' | 'bitin_cadastrado' | 'processos_concluido' | 'encaminhado_roteiro'
  | 'data_encaminhado_roteiro' | 'data_processos_concluido' | 'data_cadastrado'
>

export function inicioDaEtapa(b: CamposData): string | null {
  const etapa: Etapa | null = etapaDoBitin(b)
  if (etapa === 'Com Processos') return b.data_encaminhado_roteiro
  if (etapa === 'Aguardando cadastro') return b.data_processos_concluido
  if (etapa === 'Pendência de envio') return b.data_cadastrado
  return null
}

// "5 min" / "3 h" / "12 d" -- granularidade única (não "1d 3h"), suficiente pra dar uma noção
// de urgência de relance numa lista, sem virar um relógio de precisão.
export function tempoDecorrido(dataIso: string | null): string | null {
  if (!dataIso) return null
  const inicio = new Date(dataIso).getTime()
  if (Number.isNaN(inicio)) return null
  const ms = Math.max(0, Date.now() - inicio)
  const minutos = Math.floor(ms / 60_000)
  if (minutos < 60) return `${minutos} min`
  const horas = Math.floor(minutos / 60)
  if (horas < 24) return `${horas} h`
  const dias = Math.floor(horas / 24)
  return `${dias} d`
}

// Destaque visual pra quem está parado há muito tempo (2 dias+) -- limiar simples, ajustável
// depois se o time achar cedo/tarde demais na prática.
export function paradoHaMuitoTempo(dataIso: string | null): boolean {
  if (!dataIso) return false
  const inicio = new Date(dataIso).getTime()
  if (Number.isNaN(inicio)) return false
  return Date.now() - inicio > 2 * 24 * 60 * 60 * 1000
}
