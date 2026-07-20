import { useEffect, useRef, useState } from 'react'

// Aviso de alterações não salvas (2026-07-17, pedido explícito: "não salvei nada antes de
// sair? não salva automática ele da popup dizendo que não salvou e se deseja salvar") --
// usado em BitinDetail.tsx/CodigosSapPage.tsx/ListaTecnicaPage.tsx, as 3 telas de edição de
// BITin que salvam só sob demanda (botão "Salvar", nunca sozinhas). Cobre dois casos:
// (1) fechar a aba/atualizar a página -- `beforeunload` nativo do navegador;
// (2) clicar em "← Voltar..." dentro do app -- ver AvisoSairModal.tsx, cada página intercepta
// o clique do link e mostra o modal em vez de navegar direto.
// NÃO cobre navegação pelo menu lateral/topbar nem o botão "voltar" do navegador -- o app usa
// <Routes> simples (não um data router), então `useBlocker`/`unstable_usePrompt` do
// react-router não estão disponíveis; um guard genérico de rota ficou fora do escopo desta
// rodada.
export function useAvisoSairSemSalvar() {
  const [sujo, setSujo] = useState(false)
  const [mostrarModal, setMostrarModal] = useState(false)
  const sujoRef = useRef(sujo)
  sujoRef.current = sujo

  useEffect(() => {
    function handler(e: BeforeUnloadEvent) {
      if (!sujoRef.current) return
      e.preventDefault()
      e.returnValue = ''
    }
    window.addEventListener('beforeunload', handler)
    return () => window.removeEventListener('beforeunload', handler)
  }, [])

  // Chamar no onClick do link/botão "Voltar" -- devolve `true` se pode navegar direto
  // (nada sujo) ou `false` se abriu o modal (o clique original deve ser cancelado).
  function tentarSair(): boolean {
    if (!sujo) return true
    setMostrarModal(true)
    return false
  }

  return { sujo, setSujo, mostrarModal, setMostrarModal, tentarSair }
}
