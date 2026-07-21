import { NavLink } from 'react-router-dom'
import { version as appVersion } from '../../package.json'
import { useAuth } from '../hooks/useAuth'
import {
  SETOR_CADASTRO,
  SETOR_ENGENHARIA,
  SETOR_PROCESSOS,
  ehDoSetor,
  isAdmin,
  isGestor,
} from '../lib/permissions'
import { GridIcon, HomeIcon, InboxIcon, ListIcon, UsersIcon } from './icons'

export default function Sidebar({ open, onClose }: { open: boolean; onClose: () => void }) {
  const { user } = useAuth()
  // Identidade visual por papel (2026-07-16, ajustado depois que a 1ª versão -- cinza pro admin,
  // Light Blue pros outros -- ficou ruim visualmente. Decisão final do usuário: admin fica
  // exatamente como sempre foi (navy + logo.svg); só Gestor/Cadastro/Usuário mudam, pra branco
  // com a logo colorida. Ver Topbar.tsx (mesmo par cor/logo, pro cabeçalho combinar).
  const admin = isAdmin(user?.permission_level)
  // Gestão de usuários agora é só a conta fixa em backend/auth/security.py::CONTAS_SUPER_ADMIN
  // (2026-07-20, pedido explícito: "GESTÃO DE USUÁRIOS SÓ PARA ADMIN TOTAL (EU)") -- outro
  // admin (99) que existir no futuro não vê mais este item, mas continua vendo "Painel geral"
  // logo abaixo (esse sim é pra qualquer 99). Vem de UserOut.eh_super_admin (GET /users/me).
  const superAdmin = user?.eh_super_admin ?? false
  // 2ª revisão do modelo de permissões (2026-07-20, pedido explícito: "99 = ADMIN APENAS EU.
  // 88 = GESTOR: pode existir gestor de cadastro, processos e engenharia. 77 = cadastro,
  // processos, engenheiro.") -- Cadastro/Processos/Engenharia deixaram de ser NÍVEIS (eram
  // 88/89) e viraram Usuario.setor, cruzado com o rank (INDIVIDUAL/GESTOR/ADMIN). `ehDoSetor`
  // cobre TANTO Individual quanto Gestor do mesmo setor -- a fila de trabalho é idêntica pros
  // dois ranks (pedido explícito: "só ganha o painel de oversight, fila de trabalho continua
  // igual"), só muda quem ganha o grupo "Gestoria" abaixo.
  const souCadastro = ehDoSetor(user?.permission_level, user?.setor, SETOR_CADASTRO)
  const souProcessos = ehDoSetor(user?.permission_level, user?.setor, SETOR_PROCESSOS)
  const souEngenharia = ehDoSetor(user?.permission_level, user?.setor, SETOR_ENGENHARIA)
  const gestor = isGestor(user?.permission_level)
  // "Início" é sempre "Início" no menu (2026-07-20, pedido explícito: "Coloca apenas Início.
  // Não Início cadastro") -- mesma rota "/" pra todo mundo, Home.tsx decide o conteúdo certo
  // sozinho. O rótulo dinâmico "Início cadastro"/"Início processos" continua só dentro da
  // própria página (Home.tsx, título da tela), não no menu.
  const navItems = [{ to: '/', label: 'Início', icon: HomeIcon, end: true }]
  const logoSrc = admin ? '/logo.svg' : '/brand/gpt-color.png'
  const surfaceClass = admin ? 'bg-brand-navy' : 'bg-white border-r border-line'
  const textClass = admin ? 'text-white' : 'text-ink'
  const navActiveClass = admin ? 'bg-white/15 text-white' : 'bg-brand-navy/10 text-brand-navy'
  const navInactiveClass = admin
    ? 'text-white/70 hover:bg-white/10 hover:text-white'
    : 'text-ink-muted hover:bg-surface-alt hover:text-ink'
  const dividerClass = admin ? 'border-white/10' : 'border-line'
  const groupLabelClass = admin ? 'text-white/40' : 'text-ink-faint'
  const versionClass = admin ? 'text-white/50' : 'text-ink-faint'
  return (
    <>
      {/* Fundo escurecido atrás da sidebar no celular -- só existe quando ela está aberta,
          fecha ao clicar fora (mesma ideia de qualquer off-canvas menu). */}
      {open && (
        <div className="fixed inset-0 z-30 bg-black/40 md:hidden" onClick={onClose} aria-hidden="true" />
      )}

      <aside
        className={`fixed inset-y-0 left-0 z-40 flex w-60 shrink-0 flex-col ${surfaceClass} px-4 py-6 ${textClass} transition-transform md:sticky md:top-0 md:h-screen md:translate-x-0 ${
          open ? 'translate-x-0' : '-translate-x-full'
        }`}
      >
        {/* h-16 pro logo.svg original (admin); os PNGs de marca (gpt-color) são um lockup mais
            largo (~2.6:1), h-12 evita que fiquem colados nas bordas do menu de 240px. */}
        <div className="flex justify-center py-2">
          <img src={logoSrc} className={admin ? 'h-16 w-auto' : 'h-12 w-auto'} alt="Grain & Protein Technologies" />
        </div>

        <nav className="mt-8 flex flex-1 flex-col gap-1">
          {navItems.map(({ to, label, icon: Icon, end }) => (
            <NavLink
              key={to}
              to={to}
              end={end}
              onClick={onClose}
              className={({ isActive }) =>
                `flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors ${
                  isActive ? navActiveClass : navInactiveClass
                }`
              }
            >
              <Icon className="h-4 w-4 shrink-0" />
              {label}
            </NavLink>
          ))}

          {/* Engenharia (individual ou gestor) usa a mesma tela de sempre pros próprios BITins
              (MeusBitins.tsx / rota /bitins) -- link solto, sem grupo/divisor, mesmo padrão
              que "Início" acima (2026-07-20: sem esse link, Engenharia ficava sem jeito
              nenhum de chegar em /bitins pelo menu, já que o grupo "Processos" abaixo é só
              pra quem é DE Processos). */}
          {souEngenharia && (
            <NavLink
              to="/bitins"
              onClick={onClose}
              className={({ isActive }) =>
                `flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors ${
                  isActive ? navActiveClass : navInactiveClass
                }`
              }
            >
              <ListIcon className="h-4 w-4 shrink-0" />
              Meus Bitins
            </NavLink>
          )}

          {/* "Bitins" (2026-07-20, pedido explícito: "no meu caso de admin, coloca a pagina
              na sidebar 'Bitins' que é a tela que eu visualizo todos os Bitins") -- mesma
              rota /bitins de "Meus Bitins" acima, mas SÓ pra admin (nunca dispara junto com
              "Meus Bitins": `souEngenharia` exige rank INDIVIDUAL/GESTOR, admin é rank
              ADMIN, os dois nunca são true ao mesmo tempo). Admin não tinha NENHUM link fixo
              pra ver todos os BITins do sistema (só Painel geral, que é outra visão --
              agrupada por etapa, sem ações) -- esse link cobre a lacuna. */}
          {admin && (
            <NavLink
              to="/bitins"
              onClick={onClose}
              className={({ isActive }) =>
                `flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors ${
                  isActive ? navActiveClass : navInactiveClass
                }`
              }
            >
              <ListIcon className="h-4 w-4 shrink-0" />
              Bitins
            </NavLink>
          )}

          {/* Atalho pra tela de Cadastro (2026-07-17, reajustado 2026-07-20): admin SEMPRE vê
              -- "eu admin total" tem acesso aos dois setores, não só o próprio (pedido
              explícito: "tambem da pra mim a visão de processos (eu admin total)"). Quem é de
              Cadastro (Individual OU Gestor) também sempre vê -- é o link fixo pra própria
              fila, embaixo do Início (que agora é só o resumo). */}
          {(admin || souCadastro) && (
            <>
              <div className={`mt-3 border-t ${dividerClass} pt-3 text-xs font-semibold uppercase tracking-wide ${groupLabelClass}`}>
                Cadastro
              </div>
              <NavLink
                to="/cadastro"
                end
                onClick={onClose}
                className={({ isActive }) =>
                  `flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors ${
                    isActive ? navActiveClass : navInactiveClass
                  }`
                }
              >
                <InboxIcon className="h-4 w-4 shrink-0" />
                Cadastro
              </NavLink>
              {/* "Bitins Concluídos" saiu daqui (2026-07-21, pedido explícito: "aba de bitins
                  concluidos ainda junto de cadastro remove de lá e faz isso numa aba lá em
                  configurações só do admin") -- agora é a aba "Bitins Concluídos" dentro de
                  Settings.tsx, só admin, com opção de reverter (POST /reverter-windchill). */}
            </>
          )}

          {/* Atalho pra tela de Processos (2026-07-20, mesmo padrão do Cadastro acima) -- rota
              própria (ProcessosPage.tsx), reformulada no mesmo estilo do Painel geral (filtro
              de status + busca, ver comentário lá) em vez de reaproveitar MeusBitins.tsx
              genérico. Admin SEMPRE vê, mesmo motivo do grupo Cadastro acima. */}
          {(admin || souProcessos) && (
            <>
              <div className={`mt-3 border-t ${dividerClass} pt-3 text-xs font-semibold uppercase tracking-wide ${groupLabelClass}`}>
                Processos
              </div>
              <NavLink
                to="/processos"
                end
                onClick={onClose}
                className={({ isActive }) =>
                  `flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors ${
                    isActive ? navActiveClass : navInactiveClass
                  }`
                }
              >
                <ListIcon className="h-4 w-4 shrink-0" />
                Processos
              </NavLink>
              {/* Sem "Processos Concluídos" separado (2026-07-20, pedido explícito: "não
                  precisa de uma tela de processos concluídos") -- Processos não tem uma
                  pasta trancada como o Cadastro tem; "Revisado" é só mais uma opção de Etapa
                  dentro da própria ProcessosPage.tsx, sem link/restrição à parte. */}
            </>
          )}

          {/* Gestoria (2026-07-20, pedido explícito) -- só pra Gestor (88) "puro", não-admin.
              Único poder extra confirmado do Gestor: um painel de acompanhamento do PRÓPRIO
              setor (Cadastro/Processos: fila inteira do setor; Engenharia: colegas do mesmo
              Subgrupo) -- a fila de trabalho em si já apareceu acima, idêntica à de um
              Individual do mesmo setor. Reaproveita a mesma PainelGeral.tsx do admin -- o
              backend já devolve só os BITins que esse Gestor tem permissão de ver (ver
              backend/api/bitins.py::list_bitins), a página não precisa saber a diferença. */}
          {gestor && !admin && (
            <>
              <div className={`mt-3 border-t ${dividerClass} pt-3 text-xs font-semibold uppercase tracking-wide ${groupLabelClass}`}>
                Gestoria
              </div>
              <NavLink
                to="/painel-geral"
                end
                onClick={onClose}
                className={({ isActive }) =>
                  `flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors ${
                    isActive ? navActiveClass : navInactiveClass
                  }`
                }
              >
                <GridIcon className="h-4 w-4 shrink-0" />
                Painel geral
              </NavLink>
            </>
          )}

          {admin && (
            <>
              <div className={`mt-3 border-t ${dividerClass} pt-3 text-xs font-semibold uppercase tracking-wide ${groupLabelClass}`}>
                Administração
              </div>
              {/* Painel geral primeiro (2026-07-20, ordem pedida explicitamente) -- visão de
                  leitura do sistema inteiro (quem está com cada BITin, em que etapa), pra
                  QUALQUER admin (99). Ver PainelGeral.tsx. */}
              <NavLink
                to="/painel-geral"
                end
                onClick={onClose}
                className={({ isActive }) =>
                  `flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors ${
                    isActive ? navActiveClass : navInactiveClass
                  }`
                }
              >
                <GridIcon className="h-4 w-4 shrink-0" />
                Painel geral
              </NavLink>
              {/* Só a conta super-admin (ver comentário acima) -- outro 99 no futuro não
                  gerencia usuário nenhum. */}
              {superAdmin && (
                <NavLink
                  to="/usuarios"
                  end
                  onClick={onClose}
                  className={({ isActive }) =>
                    `flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors ${
                      isActive ? navActiveClass : navInactiveClass
                    }`
                  }
                >
                  <UsersIcon className="h-4 w-4 shrink-0" />
                  Gestão de usuários
                </NavLink>
              )}
            </>
          )}
        </nav>

        {/* Faixa de 3 cores -- mesma assinatura visual do login (painel de marca) e do
            cabeçalho antigo, pra dar continuidade entre as telas. Versão centralizada abaixo,
            com borda separando do resto (tirada de Configurações -- decisão do usuário,
            2026-07-14: um lugar só, não duplicado). */}
        <div className={`flex flex-col items-center gap-2 border-t ${dividerClass} pt-3`}>
          <div className="flex gap-1.5">
            <span className="h-1.5 w-8 rounded-full bg-brand-gold" />
            <span className="h-1.5 w-8 rounded-full bg-brand-green" />
            <span className="h-1.5 w-8 rounded-full bg-brand-orange" />
          </div>
          <span className={`text-xs ${versionClass}`}>v{appVersion}</span>
        </div>
      </aside>
    </>
  )
}
