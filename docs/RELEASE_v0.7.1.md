# Release v0.7.1 — Shell autenticado: sidebar, topbar e Home de boas-vindas

Release criado a partir da tag `v0.7.1`.

## Resumo

- Objetivo: primeira mudança de UI visível pro engenheiro desde a v0.5.0 (a v0.6.0 e a v0.7.0
  foram só robustez de backend e infraestrutura interna, sem nada novo pra ver na tela).
  Pedido direto: montar a "página principal" do site — sidebar de navegação, topbar, e uma
  Home de boas-vindas — sem inventar uma linguagem visual nova, seguindo exatamente o padrão
  já estabelecido na tela de login.
- Status: shell pronto, mas ainda pequeno de propósito — a área autenticada tem só "Início"
  (boas-vindas) e "Configurações" (placeholder). A tela de Bitins (listagem/cadastro), que é
  o próximo passo natural pra sidebar ganhar mais itens de navegação, continua sendo
  reconstruída à parte.

## O que fecha nesta versão

- **`Sidebar.tsx`** (novo): painel fixo à esquerda, mesma linguagem visual do painel de marca
  do login (`bg-brand-navy`, logo em pílula branca, faixa de 3 cores no rodapé). Navegação a
  partir de um array extensível (`NAV_ITEMS`) — só "Início" existe hoje. Off-canvas no
  celular: escondida por padrão, abre via botão de menu no topbar, com um overlay escurecido
  atrás que fecha ao clicar fora.
- **`Topbar.tsx`** (novo): barra fixa no topo do conteúdo — botão de menu (só no celular),
  toggle de tema, botão de configurações, e-mail do usuário, botão sair.
- **`pages/Home.tsx`** reescrita: de placeholder de texto ("Login funcionando.") pra boas-
  vindas de verdade — título com o primeiro nome do usuário + subtítulo discreto + faixa de 3
  cores, mesma hierarquia tipográfica do "Entrar" da tela de login.
- **`pages/Settings.tsx`** (novo, placeholder): o botão de configurações no topbar precisa
  levar a algum lugar real, não um link morto — ainda não há nada configurável de fato.
- **`components/icons.tsx`** (novo): ícones SVG inline (Home, Configurações, Sair, Menu,
  Fechar) compartilhados entre Sidebar/Topbar — mesmo padrão sem lib externa já usado no
  login, só que num módulo próprio porque mais de um componente usa os mesmos ícones agora.
- **Tema claro por padrão, escolha do usuário persiste**: comportamento que já existia desde
  a v0.5.0, só confirmado/preservado nesta rodada (não alterado).

## Validação

- Playwright ad-hoc (não faz parte da suíte automatizada ainda — ver "O que NÃO está" em
  `docs/FRONTEND.md`): desktop e mobile, tema claro e escuro, navegação entre Início e
  Configurações, abrir/fechar sidebar no celular via hambúrguer, logout. Zero erro de
  console.
- `npm run typecheck`, `npx oxlint src`, `npm run test` (4/4, suíte existente do login, sem
  regressão), `npm run build` — todos limpos.

## Como reproduzir

```powershell
# backend
.venv/Scripts/python.exe -m uvicorn backend.main:app --reload

# frontend (outro terminal)
cd frontend
npm install
npm run dev
```

## Notas

- Próximo incremento: listagem "Meus Bitins" — quando existir, ganha um item na sidebar
  (`Sidebar.tsx`, array `NAV_ITEMS`) sem precisar mexer no resto do componente.
- Sem suíte de testes automatizada pro shell ainda (só `Login.tsx` tem `Login.test.tsx`) —
  registrado como lacuna conhecida, não escondida, em `docs/FRONTEND.md`.
- Ver `CHANGELOG.md` para a lista completa e `docs/FRONTEND.md` para arquitetura e decisões
  registradas.
