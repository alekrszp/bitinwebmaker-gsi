# Release v0.5.0 — status: em revisão (reset da tela de Bitins)

## Nota importante (2026-07-13)

Este documento descrevia originalmente uma reconstrução completa da tela de cadastro de
Bitins, feita em 8 rodadas de feedback direto (resumo abaixo). Depois da 8ª rodada, o
resultado ainda estava "muito confuso" e o usuário pediu pra **apagar toda essa UI e
reconstruir do zero, incrementalmente** (login primeiro, depois Bitins parte por parte) — ver
`docs/CHANGELOG.md` (seção "Removed" do `[v0.5.0]`) e `docs/FRONTEND.md` ("Reset da tela de
Bitins").

**Consequência prática**: o conteúdo abaixo (rodadas 1-8) não corresponde mais ao código atual
— é mantido aqui só como registro histórico de decisões já tentadas (útil pra não repetir os
mesmos becos sem saída na reconstrução). Se a tag/release `v0.5.0` já foi publicada no GitHub
com este conteúdo, ela deve ser tratada como obsoleta; o próximo release de verdade deve
descrever o que sobreviveu ao reset (login/autenticação) + o que for reconstruído a partir daí,
não este histórico.

## Histórico (rodadas 1-8, código já removido)

- v1: colunas de material dirigidas por schema, sem navegação.
- v2: navegação/colar estilo Excel — mas "muito ruim" pra usar.
- v3: setas completas, painel de Detalhes, fidelidade visual com a aba `ZBPP009 + ALTERACAO`.
- v4: todos os ~30 campos visíveis por padrão ("a tela deve ser um excel enorme"), identidade
  visual da marca, tema claro/escuro.
- v5 (correção de rota): tela de cadastro reconstruída pra bater com a aba `Template
  apresentação` (cabeçalho em faixas, BITex, Setor, checklist de 22 itens, tabela de
  alterações com cabeçalho amarelo), não a `ZBPP009 + ALTERACAO` usada antes.
- v6: logo real substitui o wordmark; grade de materiais passou a ocupar a tela inteira, sem
  moldura de card.
- v7: checklist virou grade de 2-4 colunas; cabeçalho+checklist+grade passaram a compartilhar
  a mesma largura total.
- v8 (correção de rota): checklist voltou a ser `<table>` (a grade de cards da v7 ficava
  desigual); grade de materiais reduziu pra 10 colunas por padrão + 300 linhas em branco
  prontas.
- **Reset**: toda essa UI foi apagada. Tema/identidade visual (paleta, logo, toggle
  claro/escuro) e o shell de autenticação (`Login.jsx`, `AuthContext`, `RequireAuth`,
  `Layout.jsx`) sobreviveram — são a base pra reconstrução.

## O que sobrevive e vale como release de verdade, quando chegar a hora

- Backend inalterado durante toda essa fase: 158 testes automatizados, endpoints de
  materiais/checklist/schema continuam de pé e testados (`docs/BACKEND.md`).
- Frontend: login, logout, rota protegida, tema claro/escuro, identidade visual da marca.

Ver `docs/CHANGELOG.md` para a lista completa (incluindo o histórico das 8 rodadas) e
`docs/FRONTEND.md` para o estado atual da arquitetura.
