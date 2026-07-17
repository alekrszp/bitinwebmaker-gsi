import type { NavigateFunction } from 'react-router-dom'
import { api } from './api'

// "+ Novo BITin" cria o rascunho na hora e já abre o editor completo -- não existe mais uma
// tela intermediária em branco sem abas/checklist (decisão do usuário, 2026-07-16: "quando tu
// clicka em novo bitin tem uma tela que não aparece as abas e nem checklist etc... tira essa
// tela de ter que salvar o bitin pra ele aparecer, quando clicka em novo bitin ja abre direto
// na aba que tem as 3 telas etc."). Usado tanto em Home.tsx quanto MeusBitins.tsx -- os dois
// lugares com botão "+ Novo BITin". `solicitante` não é mandado aqui -- o backend carimba a
// partir do usuário logado (create_or_update_draft, backend/api/bitins.py).
export async function criarRascunhoENavegar(navigate: NavigateFunction): Promise<void> {
  const resp = await api.post('/bitins/draft', {
    content: { produto: '', motivo: '', setor: '', materiais: [] },
  })
  navigate(`/bitins/${resp.data.mongo_id}`)
}
