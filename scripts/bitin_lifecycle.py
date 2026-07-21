#!/usr/bin/env python3
"""Ciclo de vida do BITin: rascunho (editável, sem validação) -> enviado (travado).

Decisão de produto: o engenheiro tem liberdade total pra editar um BITin em rascunho --
toda a validação (estrutural + lista técnica + regras de negócio do POP + regras gerais)
só roda de uma vez, no envio. Depois de enviado, o BITin fica travado (nenhuma edição).
Ver docs/BITIN_MODEL.md, seção "Ciclo de vida do BITin".
"""

from datetime import datetime
from typing import Any

import bitin_business_rules
import bitin_document
import bitin_model
import lista_tecnica_export
from bitin_errors import BitinError, make_error

STATUS_RASCUNHO = "rascunho"
STATUS_ENVIADO = "enviado"


def is_editable(bitin: dict[str, Any]) -> bool:
    return bitin.get("status", STATUS_RASCUNHO) != STATUS_ENVIADO


def require_editable(bitin: dict[str, Any]) -> None:
    """Guarda a ser chamada por qualquer função que vá mutar um BITin (adicionar/remover
    material, editar campo). Nenhuma edição deve contornar essa checagem."""
    if not is_editable(bitin):
        raise ValueError(f"BITin {bitin.get('bitin', '?')} já foi enviado — não pode ser editado")


def enviar_bitin(
    bitin: dict[str, Any],
    vba_mapping_config: dict[str, Any],
    document_config: dict[str, Any],
) -> tuple[bool, list[BitinError]]:
    """Roda toda a validação de uma vez. Se passar, marca status=enviado e carimba
    data_envio (muta o bitin recebido). Se falhar, bitin continua "rascunho".

    Roteamento automático (2026-07-20, pedido explícito: "se for pra processo vai DIRETO pra
    processo. se não for necessário o pessoal de processo vai direto para aguardando
    cadastro. não precisa da tela de recebidos do cadastro e enviados para roteiro") --
    substitui a triagem manual que o Cadastro fazia antes (clicar "Encaminhar para roteiro"
    ou "Não precisa de roteiro" na aba "Recebidos", ver CadastroPage.tsx). Agora o envio já
    decide sozinho, com a mesma regra de sempre (bitin_document.precisa_roteiro, Alt em
    {"D/P","D/-","-/P"}): precisa de roteiro -> encaminhar_para_roteiro (vai direto pra
    Processos); não precisa -> concluir_sem_roteiro (vai direto pra "Aguardando cadastro").
    Cadastro só volta a ver o BITin quando o Processos concluir (concluir_processamento) ou
    quando ele já chega sem precisar de roteiro nenhum -- nunca mais numa fila de triagem."""
    if bitin.get("status", STATUS_RASCUNHO) == STATUS_ENVIADO:
        return False, [make_error(
            "status", "already_sent",
            f"BITin {bitin.get('bitin', '?')} já foi enviado anteriormente",
        )]

    errors = list(bitin_model.validate_bitin(bitin, vba_mapping_config))
    errors += lista_tecnica_export.validate_lista_tecnica(bitin)
    errors += bitin_business_rules.validate_business_rules(bitin, document_config)

    if errors:
        return False, errors

    bitin["status"] = STATUS_ENVIADO
    bitin["data_envio"] = datetime.now().strftime("%Y-%m-%d")

    if bitin_document.precisa_roteiro(bitin):
        encaminhar_para_roteiro(bitin)
    else:
        concluir_sem_roteiro(bitin)

    return True, []


def encaminhar_para_roteiro(bitin: dict[str, Any]) -> None:
    """Substitui o e-mail automático que o Módulo12.bas disparava ao enviar o BITin
    (romeu.maia/gustavo.goldshmith, "Segue BITin para cadastro/liberação") -- em vez de
    e-mail, o setor Cadastro tem uma fila própria (ver frontend CadastroPage.tsx) e marca
    aqui quando termina de processar e encaminha pro setor Roteiro (próxima etapa que já
    existia na macro original como aviso "REVISAR ROTEIRO", Módulo4.bas).

    Não é um terceiro status -- `encaminhado_roteiro` é um campo à parte que só faz sentido
    depois de `enviado` (mantém a checagem binária `is_editable` intacta em todo o resto do
    backend)."""
    if bitin.get("status", STATUS_RASCUNHO) != STATUS_ENVIADO:
        raise ValueError(f"BITin {bitin.get('bitin', '?')} ainda não foi enviado — nada para encaminhar")
    if bitin.get("encaminhado_roteiro", False):
        raise ValueError(f"BITin {bitin.get('bitin', '?')} já foi encaminhado para o roteiro")

    bitin["encaminhado_roteiro"] = True
    bitin["data_encaminhado_roteiro"] = datetime.now().strftime("%Y-%m-%d")


def concluir_processamento(bitin: dict[str, Any]) -> None:
    """Fecha o ciclo aberto por `encaminhar_para_roteiro` -- enquanto `encaminhado_roteiro`
    é True e isto ainda não rodou, o setor Processos pode reeditar o BITin (única exceção à
    regra geral de que "enviado" é travado pra sempre, ver
    backend/api/bitins.py::_pode_editar). Marcar como concluído tranca de novo, inclusive
    pra Processos -- ninguém edita depois disso."""
    if not bitin.get("encaminhado_roteiro", False):
        raise ValueError(f"BITin {bitin.get('bitin', '?')} ainda não foi encaminhado para o Processos")
    if bitin.get("processos_concluido", False):
        raise ValueError(f"BITin {bitin.get('bitin', '?')} já foi concluído pelo Processos")

    bitin["processos_concluido"] = True
    bitin["data_processos_concluido"] = datetime.now().strftime("%Y-%m-%d")


def concluir_sem_roteiro(bitin: dict[str, Any]) -> None:
    """Atalho pro Cadastro quando o BITin NÃO precisa passar pelo setor Processos (2026-07-17,
    pedido explícito: "coloca essa opção, do cadastro não precisar enviar pra processos,
    quando não houver: D/P, D/- ou -/P" -- ver bitin_document.precisa_roteiro pra regra
    exata). Chega direto no mesmo estado final de `concluir_processamento` (aba "Aguardando
    cadastro" em CadastroPage.tsx), sem passar pela janela de reedição do Processos --
    `sem_necessidade_roteiro` só existe pra distinguir os dois caminhos na hora de
    auditar/exibir, não muda nenhum filtro (CadastroPage.tsx já lê só `processos_concluido`).
    PDF só libera depois de `concluir_bitin`, abaixo."""
    if bitin.get("status", STATUS_RASCUNHO) != STATUS_ENVIADO:
        raise ValueError(f"BITin {bitin.get('bitin', '?')} ainda não foi enviado")
    if bitin.get("encaminhado_roteiro", False):
        raise ValueError(f"BITin {bitin.get('bitin', '?')} já foi encaminhado para o roteiro")

    agora = datetime.now().strftime("%Y-%m-%d")
    bitin["encaminhado_roteiro"] = True
    bitin["data_encaminhado_roteiro"] = agora
    bitin["processos_concluido"] = True
    bitin["data_processos_concluido"] = agora
    bitin["sem_necessidade_roteiro"] = True


def concluir_bitin(bitin: dict[str, Any]) -> None:
    """Último passo do fluxo (2026-07-20, pedido explícito): o Cadastro clica "Concluir
    BITIN" depois de já ter feito o cadastro/liberação de verdade no SAP -- aba "Aguardando
    cadastro" (CadastroPage.tsx) vira aba "Pendência de envio", e só a partir daqui o PDF fica
    disponível pra baixar e mandar pro Windchill (ver scripts/bitin_pdf.py). Roda tanto pra
    quem passou pelo Processos quanto pra quem foi concluído direto via
    `concluir_sem_roteiro` -- os dois já setam `processos_concluido=True`, que é a única
    pré-condição aqui."""
    if not bitin.get("processos_concluido", False):
        raise ValueError(f"BITin {bitin.get('bitin', '?')} ainda não passou pelo roteiro/Processos")
    if bitin.get("bitin_cadastrado", False):
        raise ValueError(f"BITin {bitin.get('bitin', '?')} já foi concluído")

    bitin["bitin_cadastrado"] = True
    bitin["data_cadastrado"] = datetime.now().strftime("%Y-%m-%d")


def enviar_windchill(bitin: dict[str, Any]) -> None:
    """Última etapa de todas (2026-07-20, pedido explícito: "coloca uma ultima etapa na
    parte de cadastro que é: enviado pro windchill ai deixa o bitin com status concluido")
    -- o Cadastro confirma que já baixou o PDF (liberado por `concluir_bitin` acima) e
    mandou de verdade pro Windchill. Não muda o campo `status` em si (continua "enviado" --
    esse campo já é usado em todo filtro `status=enviado` do sistema, mudar o valor quebraria
    CadastroPage/MeusBitins/Painel geral silenciosamente); "concluído" vira um ESTADO
    derivado (windchill_enviado=True), do mesmo jeito que bitin_cadastrado/
    processos_concluido já são -- ver PainelGeral.tsx::etapaDe, que já lê os campos
    derivados pra mostrar a etapa, nunca o `status` bruto."""
    if not bitin.get("bitin_cadastrado", False):
        raise ValueError(f"BITin {bitin.get('bitin', '?')} ainda não foi cadastrado")
    if bitin.get("windchill_enviado", False):
        raise ValueError(f"BITin {bitin.get('bitin', '?')} já foi enviado pro Windchill")

    bitin["windchill_enviado"] = True
    bitin["data_windchill_enviado"] = datetime.now().strftime("%Y-%m-%d")


def reverter_windchill(bitin: dict[str, Any]) -> None:
    """"Voltar BITin" (2026-07-20, pedido explícito: "lista dos bitins concluidos com opções
    de voltar bitin etc.") -- desfaz `enviar_windchill` acima, único jeito de sair da pasta de
    Bitins Concluídos (backend/api/users.py::NIVEL_ADMIN -- reservado ao admin, ver
    backend/api/bitins.py::reverter_windchill_endpoint, check_permission em vez de
    check_setor, nem Cadastro comum chama isso). Volta pra "Pendência de envio" -- não mexe em
    `bitin_cadastrado`/`processos_concluido`, só desfaz o último passo."""
    if not bitin.get("windchill_enviado", False):
        raise ValueError(f"BITin {bitin.get('bitin', '?')} ainda não foi enviado pro Windchill")

    bitin["windchill_enviado"] = False
    bitin["data_windchill_enviado"] = None
