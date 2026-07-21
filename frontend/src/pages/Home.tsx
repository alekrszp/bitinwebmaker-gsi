import { useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import AjudaPopover from '../components/bitin/AjudaPopover'
import StatusBadge from '../components/bitin/StatusBadge'
import { useAuth } from '../hooks/useAuth'
import { api } from '../lib/api'
import { criarRascunhoENavegar } from '../lib/criarBitin'
import { SETOR_CADASTRO, SETOR_PROCESSOS, ehDoSetor, isAdmin, isGestor } from '../lib/permissions'
import type { Bitin, ResumoUsuario } from '../lib/types'

// Upgrade da Home (2026-07-14): "Meus Bitins" (listagem + detalhe + cadastro) já existe agora,
// então os dois motivos que antes seguravam recentes/ação rápida (nenhum lugar útil pra
// linkar) não valem mais -- ver docs/FRONTEND.md, decisão original da v0.7.1. Cartões de
// resumo viraram links pra listagem já filtrada por status; ganhou lista de recentes e botão
// "+ Novo BITin". Sem a faixa de 3 cores aqui -- fica só na sidebar e no login por enquanto
// (decisão do usuário, 2026-07-14).
//
// 2ª revisão do modelo de permissões (2026-07-20): Cadastro/Processos deixaram de ser NÍVEIS
// e viraram Usuario.setor, cruzado com o rank (INDIVIDUAL/GESTOR/ADMIN, ver
// lib/permissions.ts). `ehDoSetor` cobre tanto Individual quanto Gestor do mesmo setor.
//
// Regra do Início por papel (2026-07-20, pedido explícito: "na tela de início, pro admin e
// gestor pode por pro seu próprio setor tb o resumo. admin vê o resumo de todos os setores.
// gestor vê do seu setor."):
// - Individual de Cadastro/Processos: resumo da PRÓPRIA fila (2 cartões, como sempre foi).
// - Gestor de Cadastro/Processos: MESMO resumo de fila que o Individual (fila é idêntica,
//   único poder extra do Gestor é o Painel geral, ver Sidebar.tsx) -- `ehDoSetor` já cobre os
//   dois ranks juntos, não precisa de um caminho à parte.
// - Gestor de Engenharia: resumo do PRÓPRIO setor (rascunhos/enviados), mas escopado pros
//   colegas do mesmo Subgrupo -- GET /bitins/resumo-painel já escopa automaticamente (mesma
//   regra de list_bitins).
// - Individual de Engenharia: resumo dos PRÓPRIOS BITins (GET /bitins/resumo-usuario, como
//   sempre foi) -- "visão do que fez e o que foi feito", sem ver o setor inteiro.
// - Admin: resumo de TODOS os setores ao mesmo tempo (Cadastro + Processos + sistema).
//
// Performance (2026-07-20, pedido explícito: "otimiza velocidade de carregamento... tá muito
// lento") -- ANTES buscava até 7 listas completas de BITins em paralelo (GET /bitins?limit=
// 200/500 x7, cada uma trazendo o `content` inteiro de cada BITin só pra contar `.length`).
// Agora é 1 chamada só (GET /bitins/resumo-painel, $facet no servidor) pra admin/Cadastro/
// Processos/Gestor de Engenharia; só o Individual de Engenharia usa /resumo-usuario (também
// 1 chamada, já era assim). "BITins em aberto por usuário" saiu daqui -- já existe no Painel
// geral (link "Ver painel geral completo" abaixo), não precisa duplicar esse cálculo pesado
// aqui também.
export default function Home() {
  const { user } = useAuth()
  const navigate = useNavigate()
  const primeiroNome = user?.nome?.split(' ')[0]
  const admin = isAdmin(user?.permission_level)
  const gestor = isGestor(user?.permission_level)
  const souCadastro = ehDoSetor(user?.permission_level, user?.setor, SETOR_CADASTRO)
  const souProcessos = ehDoSetor(user?.permission_level, user?.setor, SETOR_PROCESSOS)
  // Nem souCadastro nem souProcessos, nem admin -- sobra Engenharia (Individual ou Gestor).
  const souEngenhariaGestor = gestor && !admin && !souCadastro && !souProcessos
  const [resumo, setResumo] = useState<ResumoUsuario | null>(null)
  const [painel, setPainel] = useState<{
    cadastro_aguardando: number
    cadastro_cadastrados: number
    processos_pendentes: number
    processos_concluidos: number
    geral_rascunhos: number
    geral_enviados: number
  } | null>(null)
  const [recentes, setRecentes] = useState<Bitin[] | null>(null)
  const [erroNovo, setErroNovo] = useState<string | null>(null)

  // "+ Novo BITin" cria o rascunho na hora e navega direto pro editor completo -- sem tela
  // intermediária em branco (ver lib/criarBitin.ts).
  async function novoBitin() {
    setErroNovo(null)
    try {
      await criarRascunhoENavegar(navigate)
    } catch {
      setErroNovo('Não foi possível criar um novo BITin. Tente novamente.')
    }
  }

  useEffect(() => {
    let cancelado = false

    if (souCadastro || souProcessos || souEngenhariaGestor || admin) {
      api
        .get('/bitins/resumo-painel')
        .then((resp) => {
          if (!cancelado) setPainel(resp.data)
        })
        .catch(() => {})
    } else {
      // Individual de Engenharia (ou fallback) -- só os próprios.
      api
        .get('/bitins/resumo-usuario')
        .then((resp) => {
          if (!cancelado) setResumo(resp.data)
        })
        .catch(() => {}) // falha silenciosa -- não é crítico o bastante pra mostrar erro numa tela de boas-vindas
    }

    api
      .get('/bitins', { params: { limit: 5 } })
      .then((resp) => {
        if (!cancelado) setRecentes(resp.data)
      })
      .catch(() => {})
    return () => {
      cancelado = true
    }
  }, [souCadastro, souProcessos, souEngenhariaGestor, admin])

  const titulo = souCadastro ? 'Início cadastro' : souProcessos ? 'Início processos' : null

  return (
    <div>
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <div className="flex flex-wrap items-center gap-3">
            <h1 className="text-2xl font-semibold text-ink text-balance sm:text-3xl">
              {titulo ?? (primeiroNome ? `Bem-vindo, ${primeiroNome}` : 'Bem-vindo')}
            </h1>
            <AjudaPopover titulo="Hint">
              <p>
                Os cartões abaixo são atalhos dos BITins em processo do seu próprio setor. Cada
                um já abre a lista certa, filtrada.
              </p>
              {/* Cada bloco só aparece pra quem tem acesso àquela fila -- Cadastro só vê a
                  explicação de Cadastro, Processos só a de Processos, e assim por diante
                  (mesmo padrão pros outros StatCard acima). Admin vê tudo, já que enxerga o
                  resumo de todos os setores. */}
              {(souCadastro || admin) && (
                <p>
                  Na fila de Cadastro: "Aguardando cadastro" (liberar no SAP) e "Pendência de
                  envio" (baixar PDF/mandar pro Windchill).
                </p>
              )}
              {(souProcessos || admin) && (
                <p>
                  Na fila de Processos: "Pendentes" (aguardando revisão de roteiro) e
                  "Revisados" (já devolvidos pro Cadastro).
                </p>
              )}
              {souEngenhariaGestor && <p>"Rascunhos" e "Enviados" contam os BITins do seu setor.</p>}
              {!souCadastro && !souProcessos && !souEngenhariaGestor && !admin && (
                <p>"Rascunhos" e "Enviados" contam os seus próprios BITins.</p>
              )}
              <p>"Recentes" lista os últimos BITins criados, mais recente primeiro.</p>
            </AjudaPopover>
          </div>
          <p className="mt-1 text-sm text-ink-muted">
            {souCadastro || souProcessos
              ? 'Resumo da fila e atividade recente.'
              : admin
                ? 'Resumo de todos os setores e atividade recente.'
                : souEngenhariaGestor
                  ? 'Resumo do seu setor e atividade recente.'
                  : 'Seu resumo de BITins e atividade recente.'}
          </p>
        </div>
        {!souCadastro && !souProcessos && (
          <button
            type="button"
            onClick={novoBitin}
            className="whitespace-nowrap rounded-lg bg-brand-navy px-4 py-2.5 text-sm font-medium text-white transition-colors hover:bg-brand-navy-dark"
          >
            + Novo BITin
          </button>
        )}
      </div>

      {erroNovo && <p className="mt-2 text-sm text-red-600">{erroNovo}</p>}

      <div className="mt-6 flex flex-wrap gap-4">
        {admin ? (
          <>
            <StatCard label="Cadastro: aguardando" value={painel?.cadastro_aguardando} to="/cadastro?status=enviado&etapa=aguardando_cadastro" />
            <StatCard label="Cadastro: pendência de envio" value={painel?.cadastro_cadastrados} to="/cadastro?status=enviado&etapa=pendencia_envio" />
            <StatCard label="Processos: pendentes" value={painel?.processos_pendentes} to="/processos?etapa=pendente" />
            <StatCard label="Processos: revisados" value={painel?.processos_concluidos} to="/processos?etapa=revisado" />
            <StatCard label="Rascunhos (sistema)" value={painel?.geral_rascunhos} to="/bitins?status=rascunho" />
            <StatCard label="Enviados (sistema)" value={painel?.geral_enviados} to="/bitins?status=enviado" />
          </>
        ) : souCadastro ? (
          <>
            <StatCard label="Aguardando cadastro" value={painel?.cadastro_aguardando} to="/cadastro?status=enviado&etapa=aguardando_cadastro" />
            <StatCard label="Pendência de envio" value={painel?.cadastro_cadastrados} to="/cadastro?status=enviado&etapa=pendencia_envio" />
          </>
        ) : souProcessos ? (
          // Sem restrição de admin aqui (2026-07-20, "não precisa de uma tela de processos
          // concluídos") -- "Revisado" é só mais uma etapa normal, aberta pra qualquer
          // Processos, ver ProcessosPage.tsx.
          <>
            <StatCard label="Pendentes" value={painel?.processos_pendentes} to="/processos?etapa=pendente" />
            <StatCard label="Revisados" value={painel?.processos_concluidos} to="/processos?etapa=revisado" />
          </>
        ) : souEngenhariaGestor ? (
          <>
            <StatCard label="Rascunhos (setor)" value={painel?.geral_rascunhos} to="/bitins?status=rascunho" />
            <StatCard label="Enviados (setor)" value={painel?.geral_enviados} to="/bitins?status=enviado" />
          </>
        ) : (
          <>
            <StatCard label="Rascunhos" value={resumo?.rascunhos} to="/bitins?status=rascunho" />
            <StatCard label="Enviados" value={resumo?.enviados} to="/bitins?status=enviado" />
          </>
        )}
      </div>

      {(admin || gestor) && (
        <p className="mt-3 text-sm">
          <Link to="/painel-geral" className="text-ink-muted hover:text-ink hover:underline">
            Ver painel geral completo
          </Link>
        </p>
      )}

      <div className="mt-8">
        <div className="flex items-center justify-between">
          <h2 className="text-sm font-semibold uppercase tracking-wide text-ink-muted">Recentes</h2>
          <Link
            to={souCadastro ? '/cadastro' : '/bitins'}
            className="text-sm text-ink-muted hover:text-ink hover:underline"
          >
            Ver todos
          </Link>
        </div>

        {!recentes && <p className="mt-3 text-sm text-ink-muted">Carregando...</p>}
        {recentes && recentes.length === 0 && (
          <p className="mt-3 text-sm text-ink-muted">
            {souProcessos
              ? 'Nenhum BITin na fila do Processos ainda.'
              : souCadastro
                ? 'Nenhum BITin na fila do Cadastro ainda.'
                : 'Nenhum BITin ainda -- crie o primeiro.'}
          </p>
        )}
        {recentes && recentes.length > 0 && (
          <div className="mt-3 overflow-hidden rounded-lg border border-line">
            <table className="w-full text-left text-sm">
              <tbody className="divide-y divide-line bg-surface">
                {recentes.map((b) => (
                  <tr key={b.mongo_id} className="hover:bg-surface-alt">
                    <td className="w-24 px-4 py-2.5 text-ink-muted">
                      <Link to={`/bitins/${b.mongo_id}`} className="block">
                        {b.codigo ?? '—'}
                      </Link>
                    </td>
                    <td className="px-4 py-2.5">
                      <Link to={`/bitins/${b.mongo_id}`} className="block text-ink hover:underline">
                        {String(b.content?.motivo ?? '—')}
                      </Link>
                    </td>
                    {/* Nome de quem fez o BITin (2026-07-20, pedido explícito) -- usa
                        content.solicitante (nome de verdade preenchido no formulário), não
                        criado_por (e-mail da conta) -- é o mesmo campo já mostrado como
                        "Solicitante" em CadastroPage.tsx/ProcessosPage.tsx. */}
                    <td className="px-4 py-2.5 text-ink-muted">
                      <Link to={`/bitins/${b.mongo_id}`} className="block">
                        {String(b.content?.solicitante ?? '—')}
                      </Link>
                    </td>
                    <td className="w-28 px-4 py-2.5">
                      <Link to={`/bitins/${b.mongo_id}`} className="block">
                        <StatusBadge status={b.status} windchillEnviado={b.windchill_enviado} />
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  )
}

function StatCard({ label, value, to }: { label: string; value: number | undefined; to: string }) {
  return (
    <Link
      to={to}
      className="min-w-[140px] rounded-lg border border-line bg-surface px-6 py-4 transition-colors hover:border-brand-navy/30 hover:bg-surface-alt"
    >
      <p className="text-3xl font-semibold text-ink">{value ?? '—'}</p>
      <p className="mt-1 text-xs font-medium uppercase tracking-wide text-ink-muted">{label}</p>
    </Link>
  )
}
