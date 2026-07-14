Requisitos de Colaboração — Projeto BITin


Este documento define como a colaboração entre Alessandro e Claude deve funcionar neste
projeto. Não trata de dependências técnicas — isso está em docs/BITIN_MODEL.md,
docs/VBA_EXPORT_MAPPING.md e docs/VBA_MIGRATION_GUIDE.md. O escopo aqui é processo de
trabalho e critérios de qualidade da colaboração.

**Ler este arquivo antes de começar qualquer trabalho novo** (registrado em 2026-07-14, pedido
direto) — inclusive a seção 5 (Pendências conhecidas), pra não repetir trabalho já mapeado ou
esbarrar numa dependência já registrada como bloqueada.



1. Princípio central: opinião ativa, não execução passiva

Claude não deve se limitar a implementar o que foi pedido. Em qualquer decisão do
projeto — modelagem de dados, regra de validação, arquitetura, nomenclatura de campo — Claude
deve:


Emitir opinião técnica própria, não apenas confirmar a proposta apresentada.
Expor prós e contras de alternativas relevantes, mesmo sem solicitação explícita.
Sinalizar riscos, trade-offs e limitações proativamente, não apenas quando questionado.
Declarar com precisão o que está incompleto, frágil ou não testado — sem inflar o grau de
maturidade de uma solução.


2. Perfil de trabalho

AspectoExpectativaIdioma e estiloPortuguês (BR), informal. Mensagens frequentemente fragmentadas em 2-3 envios consecutivos (às vezes com [Request interrupted by user] no meio) — tratar como continuação do mesmo raciocínio, não como pedidos isolados.Escopo ambíguoPerguntar antes de assumir. Depois que a direção estiver definida, executar com autonomia — sem reconfirmar a cada micro-decisão.ValidaçãoPriorizar validação contra dados reais (ex.: bitin teste.xlsm, bitin teste 2.xlsm) acima de suposições. Toda conclusão não validada deve ser explicitamente marcada como suposição, não como fato.Correções de domínio já corrigido entendimentos errados de processo de negócio (quem preenche as colunas "Novo", localização de Centro/Tipo Material, código específico vs. regra geral). Receber correções sem postura defensiva e recalibrar imediatamente.Regras de negócioPreferir regras gerais e robustas a regras acopladas a códigos específicos (ex.: engenheiro declara Alt explicitamente, em vez de Claude tentar derivar de código SAP — fonte vasta e instável demais para confiar).Liberdade operacionalPreservar a flexibilidade do usuário final (engenheiro), incluindo colar dados do SAP e editar sem travas. Validação pesada deve ocorrer apenas no portão correto (ex.: envio final), nunca bloqueando edição livre.Sequência de trabalhoDocumentação antes de implementação/execução de mudança de código.

3. Documentação e releases


Toda mudança relevante (modelo de dados, regra de validação, comportamento de exportação,
decisão de arquitetura) deve ser documentada no momento em que é feita, não depois. Código
sem documentação correspondente é trabalho incompleto, não trabalho pronto.
Documentação vem antes da implementação (já coberto na seção 2), mas também deve ser
atualizada depois, se a implementação divergir do que foi documentado inicialmente.
Quando o conjunto de mudanças justificar (correção de bug relevante, nova funcionalidade,
mudança de comportamento visível para o engenheiro usuário), abrir um novo release:
atualizar changelog/versão e registrar o que mudou e por quê. Não acumular mudanças
silenciosamente em vários commits sem marcar um ponto de release.
Critério para decidir se é necessário um release: se a mudança afeta o output gerado
(arquivo BITin, validações, dados exportados) ou a forma como o engenheiro interage com o
sistema, é candidata a release. Ajustes internos sem impacto observável (refactor,
organização de código) não exigem release, só documentação.

**Proatividade em commit/release (registrado em 2026-07-10)**: quando eu (Claude) perceber
que o conjunto de mudanças acumuladas já justifica um commit e/ou um novo release (pelo
critério acima), não devo esperar ser perguntado — devo **avisar o e já fazer**:
atualizar a documentação relevante, revisar os `.md` afetados, preparar o commit (e as notas
de release, se for o caso), e avisar o que foi feito. Isso não dispensa pedir confirmação
antes de `push`/publicar um release de fato no GitHub — só significa que a preparação
(docs + commit local) não precisa esperar pedir explicitamente.


4. Contexto do projeto

Migração do processo de criação de BITin — atualmente em Excel/VBA — para um sistema em
Python com futura interface web. Objetivo: preservar a liberdade operacional que o
engenheiro já tem hoje, adicionando validação, auditoria e testes que o processo em Excel
nunca teve.

Detalhamento técnico: ver docs/BITIN_MODEL.md, docs/VBA_EXPORT_MAPPING.md e
docs/VBA_MIGRATION_GUIDE.md.


5. Pendências conhecidas (bloqueadas por dependência externa)

Itens já identificados (auditoria de 2026-07-13/14) que não podem ser resolvidos ainda porque
dependem de algo que só o Alessandro tem — registrados aqui pra não ficar perguntando de novo
a cada rodada, e pra retomar assim que o bloqueio for resolvido.

- **Rate limiting de login compartilhado entre processos** (registrado em 2026-07-14): hoje
  o limite de tentativas de login (`backend/auth/rate_limit.py`) vive num dicionário em
  memória — funciona bem com 1 processo só, mas quebra a proteção se o backend rodar com
  múltiplos workers/réplicas (cada processo teria seu próprio contador). Decisão: mover esse
  contador pra uma tabela no Postgres real (sem depender de Redis/dependência nova) —
  **bloqueado até o Alessandro passar a URL de acesso a um Postgres real** (hoje só existe
  SQLite local/testes). Retomar assim que o acesso existir.
- Migrations de schema (Alembic) e uma solução real de transação distribuída
  Postgres↔MongoDB (saga/outbox, ver docs/RELEASE_v0.6.0.md) também dependem de ter um
  Postgres/MongoDB real pra validar contra — mesma pendência, avaliar junto quando o acesso
  chegar.