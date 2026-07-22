#!/usr/bin/env python3
"""Parser do texto colado do SAP (ZBPP009/relatório equivalente) direto na interface web.

Duas origens de colagem, confirmadas com dados reais:

1. Cópia via Excel (o Excel intermedeia a grade do SAP GUI): usa caracteres TAB reais entre
   células. Nesse caso o parser separa por TAB, o que lida corretamente com campos de texto
   livre que têm espaços internos (ex.: descrição 'TUBO MENOR 1/2"') sem ambiguidade nenhuma.

2. Cópia direta da grade do SAP GUI (sem passar pelo Excel) -- caso real do usuário,
   2026-07-16: NÃO tem TAB nenhum. Duas rodadas de investigação com os dados reais do usuário
   (material 8661, "TUBO MENOR 1/2\"", centros 2001/2003/2005/2006):

   - 1ª tentativa (descartada): assumir espaço único como separador de coluna em toda a
     linha, ancorando prefixo/sufixo por CONTAGEM DE TOKENS. Quebrou porque colunas depois
     da 22ª (GCm em diante -- campos raramente usados: grupo compradores, planejador,
     depósito, etc.) têm largura de verdade VARIÁVEL entre linhas (ex.: "1" vs "000001" na
     mesma coluna) -- contagem de tokens não é estável ali.
   - 2ª investigação (a que ficou): as colunas 1-22 (tipo até NCM) são de LARGURA FIXA de
     verdade -- confirmado medindo a posição de caractere onde cada valor conhecido começa
     em várias linhas reais com conteúdo diferente (ex.: "TUBO" sempre no caractere 18,
     "REVISADO" sempre no 94, "8479.90.90" sempre no 128, não importa o quanto os campos
     anteriores variem) -- é exportação de largura fixa típica de grade SAP GUI, cada coluna
     ocupa um número fixo de caracteres preenchido com espaço. Da coluna 23 em diante, a
     largura já não é fixa (valores reais variam de tamanho), então usa separação por espaço
     simples ali (mesma lógica de ancoramento por token de antes, só que restrita ao final
     da linha -- risco aceito de desalinhamento ocasional nesses campos pouco usados, bem
     menor que perder dado nas colunas 1-22, que são as que o engenheiro realmente vê/usa).

Cada linha colada vira uma linha de Plan1 (ZBPP009) -- mesma estrutura de 36 colunas que
scripts/vba_port_export.py lê do arquivo .xlsm real -- e alimenta diretamente os campos de
snapshot "atual" do material no BITin (ver docs/BITIN_MODEL.md).

3ª origem de colagem (2026-07-22, pedido explícito: "o mapeamento da zbpp009 deve funcionar
de qualquer copia e cola que o usuário faz, independente da ordem") -- uma planilha de
terceiro (ex.: cópia de outra ZBPP009/BITin já em formato De/Novo, colunas em ordem
diferente da grade oficial do SAP). SEM cabeçalho reconhecível, não tem como saber com
segurança o que cada valor solto significa (ex.: "2001" pode ser Centro ou qualquer outro
número de 4 dígitos) -- inventar uma heurística de conteúdo pra adivinhar isso silenciaria um
erro real com um valor errado, pior que travar (ver requirements.md, "preferir regra robusta a
heurística acoplada a algo instável"). O que É seguro: se a colagem TEM uma linha de
cabeçalho com nomes de campo reconhecíveis (mesmos rótulos de `bitin_model.DADOS_BASICOS_LABELS`,
com ou sem acento/maiúscula, sufixo "Novo"/"Nova" pro lado "para") -- nesse caso o mapeamento
independe de ordem/posição, cada valor casa pelo NOME da coluna, não por onde está. Sem
cabeçalho reconhecível, cai no parser posicional de sempre (acima) -- nunca inventa.
"""

import unicodedata
from typing import Any

import bitin_model

TOTAL_COLUNAS_PLAN1 = 36

# Offsets de caractere (início, fim exclusivo) das colunas 1-22 -- medidos contra dados reais
# do usuário (2026-07-16), estáveis em toda a amostra (4 centros diferentes, conteúdo de
# hierarquia/data/NCM idêntico entre linhas, mas a posição de início de cada campo bate
# sempre no mesmo caractere independente do que vem antes). Coluna 3 (UMB) e colunas
# 17/18 (Mat.Substitut/St) não têm mapeamento em `plan1_identificacao_columns`/
# `plan1_dados_basicos_columns` hoje, mas os offsets ficam registrados aqui mesmo assim
# pra não perder a análise se um dia precisarem ser expostos.
OFFSETS_COLUNAS_FIXAS: dict[int, tuple[int, int]] = {
    1: (0, 4),      # TMat
    2: (5, 9),      # Material
    3: (10, 12),    # UMB (não mapeado no crosswalk hoje)
    4: (13, 17),    # Cen.
    5: (18, 34),    # TxtBreveMaterial (descrição) -- única coluna com espaço interno real
    6: (34, 40),    # GrpMercads.
    7: (40, 44),    # L/E (status)
    8: (44, 63),    # Hierarq.produtos
    9: (63, 69),    # Peso bruto
    10: (69, 74),   # Peso líquido
    11: (74, 78),   # Un. (unidade peso)
    12: (78, 84),   # Volume
    13: (84, 88),   # UVl (unidade volume)
    14: (88, 91),   # Desenho (SIM/NAO)
    15: (91, 94),   # Nível Rev.
    16: (94, 114),  # Doc.
    19: (114, 125), # Vál.desde (data bloqueio vendas)
    20: (125, 128), # EM
    22: (128, 138), # Céd.controle (NCM)
}
FIM_REGIAO_FIXA = 138  # a partir daqui, largura variável de verdade -- cai pra token simples
PRIMEIRA_COLUNA_VARIAVEL = 23


def _parse_linha_espaco(line: str) -> dict[int, str]:
    """Cola direta do SAP GUI (sem TAB): colunas 1-22 por posição fixa de caractere
    (`OFFSETS_COLUNAS_FIXAS`), colunas 23-36 por separação de espaço simples no restante da
    linha (largura real variável ali, ver docstring do módulo)."""
    campos: dict[int, str] = {}
    for col, (inicio, fim) in OFFSETS_COLUNAS_FIXAS.items():
        campos[col] = line[inicio:fim].strip() if len(line) > inicio else ""

    # Coluna 1 (tipo_material) sempre vem preenchida numa linha real de material -- se veio
    # vazia, a linha não segue o layout de largura fixa esperado (achado real: uma linha de
    # SOMA de planilha colada junto, com espaços à esquerda empurrando os números de total
    # pra dentro da faixa de caractere onde o código do material era esperado, virando um
    # "material fantasma" com código errado). Descarta a linha inteira nesse caso -- mesmo
    # tratamento de linha em branco, ver `parse_sap_paste`.
    if not campos.get(1):
        return {}

    resto = line[FIM_REGIAO_FIXA:]
    tokens_resto = [t for t in resto.split(" ") if t != ""] if resto.strip() else []
    # Colunas 23-36 (14 colunas) por token, na ordem em que aparecem -- best-effort: se a
    # linha real tiver menos valores preenchidos que tokens (colunas vazias no meio), a
    # correspondência col->valor pode desalinhar a partir daí. Aceito de propósito (ver
    # docstring do módulo) -- são campos raramente usados, e as colunas 1-22 (as que
    # importam de verdade pro engenheiro) já saíram corretas pela posição fixa acima.
    for offset, valor in enumerate(tokens_resto):
        col = PRIMEIRA_COLUNA_VARIAVEL + offset
        if col > TOTAL_COLUNAS_PLAN1:
            break
        campos[col] = valor

    return campos


def parse_sap_paste(raw_text: str) -> list[dict[int, str]]:
    """Cada linha colada -> dict {coluna (1-indexada): valor}. Linhas em branco são
    ignoradas. Linhas mais curtas que o esperado ficam só com as colunas presentes
    (não preenche com vazio o que não veio).

    Detecta a origem da colagem por linha: se tem TAB, usa o caminho TAB (Excel); senão,
    usa o ancoramento por espaço (SAP GUI direto, ver docstring do módulo)."""
    rows: list[dict[int, str]] = []
    for line in raw_text.splitlines():
        if line.strip() == "":
            continue
        if "\t" in line:
            fields = line.split("\t")
            rows.append({col: value.strip() for col, value in enumerate(fields, start=1)})
        else:
            rows.append(_parse_linha_espaco(line))
    return rows


def plan1_row_to_material_atual(plan1_row: dict[int, str], vba_mapping_config: dict[str, Any]) -> dict[str, Any]:
    """Extrai os campos de identificação + o snapshot 'atual' completo (todos os campos de
    dados_basicos, colados direto da ZBPP009) -- a tela Códigos SAP é idêntica à ZBPP009
    (decisão do usuário, 2026-07-15): lista TODOS os campos SAP do material, não um recorte.
    O 'de' de cada campo de dados_basicos vem daqui; o 'para' fica em branco até o engenheiro
    declarar a alteração na aba BITin."""
    cols = vba_mapping_config["plan1_identificacao_columns"]
    dados_basicos_cols = vba_mapping_config["plan1_dados_basicos_columns"]
    return {
        "tipo_material": plan1_row.get(cols["tipo_material"], ""),
        "codigo_material": plan1_row.get(cols["codigo_material"], ""),
        "centro": plan1_row.get(cols["centro"], ""),
        "descricao_material": plan1_row.get(cols["descricao_material"], ""),
        "grupo_mercadorias_atual": plan1_row.get(cols["grupo_mercadorias_atual"], ""),
        "tem_desenho": plan1_row.get(cols["tem_desenho_col"], "") == "SIM",
        "dados_basicos_atual": {
            campo: plan1_row.get(col, "")
            for campo, col in dados_basicos_cols.items()
        },
    }


def _normalizar_rotulo(texto: str) -> str:
    """Ignora acento/maiúscula (mesmo espírito de normalizar() em frontend/src/lib/texto.ts)
    -- planilha de terceiro pode escrever "Nível Revisão" com capitalização/acentuação um
    pouco diferente da nossa, mas ainda reconhecível."""
    sem_acento = "".join(
        c for c in unicodedata.normalize("NFD", texto) if unicodedata.category(c) != "Mn"
    )
    return sem_acento.strip().lower()


# Campos de identificação que não têm par "De/Novo" na planilha (sempre um valor só) --
# extra em relação a DADOS_BASICOS_LABELS, que só cobre os campos que TÊM par.
_ROTULOS_IDENTIFICACAO = {
    "tipo material": "tipo_material",
    "centro": "centro",
    "codigo": "codigo_material",
    "material": "codigo_material",
}
_SUFIXOS_LADO_PARA = (" novo", " nova")
_CAMPOS_SEM_PAR_DE_NOVO = frozenset(_ROTULOS_IDENTIFICACAO.values())


def _mapa_rotulos_conhecidos() -> dict[str, str]:
    mapa = {_normalizar_rotulo(label): campo for campo, label in bitin_model.DADOS_BASICOS_LABELS.items()}
    mapa.update(_ROTULOS_IDENTIFICACAO)
    return mapa


def detectar_cabecalho(primeira_linha: str) -> dict[int, tuple[str, str]] | None:
    """Tenta reconhecer a primeira linha colada como CABEÇALHO (nomes de campo por coluna,
    não dado de material) -- ver docstring do módulo. Só considera colagem via TAB (mesma
    origem "via Excel" já documentada acima) -- cabeçalho sem TAB não dá pra separar em
    colunas com segurança. Cada coluna reconhecida vira (campo, "de"|"para") -- sufixo "Novo"/
    "Nova" no rótulo indica o lado "para". Devolve None com menos de 3 colunas reconhecidas
    (provavelmente não é cabeçalho, é dado de verdade que por acaso bateu com algum rótulo)."""
    if "\t" not in primeira_linha:
        return None
    mapa = _mapa_rotulos_conhecidos()
    resultado: dict[int, tuple[str, str]] = {}
    for idx, token in enumerate(primeira_linha.split("\t"), start=1):
        normalizado = _normalizar_rotulo(token)
        if not normalizado:
            continue
        lado = "de"
        base = normalizado
        for sufixo in _SUFIXOS_LADO_PARA:
            if normalizado.endswith(sufixo):
                base = normalizado[: -len(sufixo)].strip()
                lado = "para"
                break
        campo = mapa.get(base)
        if campo:
            resultado[idx] = (campo, lado)
    return resultado if len(resultado) >= 3 else None


def parse_com_cabecalho(raw_text: str) -> list[dict[str, Any]] | None:
    """Cola COM cabeçalho reconhecível -> materiais já com 'de' E 'para' preenchidos (a
    planilha de origem já tem os dois, diferente do parser posicional acima, que só preenche
    'de' porque o dump bruto do SAP não tem 'para' nenhum). None se a 1ª linha não parecer
    cabeçalho -- quem chama cai pro parser posicional (`parse_sap_paste_to_materiais`)."""
    linhas = [linha for linha in raw_text.splitlines() if linha.strip() != ""]
    if not linhas:
        return None
    mapa_colunas = detectar_cabecalho(linhas[0])
    if mapa_colunas is None:
        return None

    materiais: list[dict[str, Any]] = []
    for linha in linhas[1:]:
        identificacao: dict[str, str] = {}
        dados_de: dict[str, str] = {}
        dados_para: dict[str, str] = {}
        for idx, token in enumerate(linha.split("\t"), start=1):
            par = mapa_colunas.get(idx)
            if not par:
                continue
            campo, lado = par
            valor = token.strip()
            if campo in _CAMPOS_SEM_PAR_DE_NOVO:
                if lado == "de":  # identificação nunca tem coluna "Novo" de verdade
                    identificacao[campo] = valor
                continue
            (dados_de if lado == "de" else dados_para)[campo] = valor

        # Linha sem código de material -- provavelmente linha em branco/total de planilha
        # colada junto (mesmo cuidado do parser posicional, ver _parse_linha_espaco acima).
        if not identificacao.get("codigo_material"):
            continue

        materiais.append({
            "tipo_material": identificacao.get("tipo_material", ""),
            "codigo_material": identificacao.get("codigo_material", ""),
            "centro": identificacao.get("centro", ""),
            # descricao_material/grupo_mercadorias_atual/tem_desenho derivam do lado "de" de
            # dados_basicos -- mesmo padrão de plan1_row_to_material_atual acima (são a MESMA
            # coluna na planilha real, ver config/vba_mapping.json: descricao_material e
            # dados_basicos.descricao apontam pro mesmo índice de coluna).
            "descricao_material": dados_de.get("descricao", ""),
            "grupo_mercadorias_atual": dados_de.get("grupo_mercadorias", ""),
            "tem_desenho": dados_de.get("desenho", "").strip().upper() == "SIM",
            "dados_basicos_atual": dados_de,
            "dados_basicos_novo": dados_para,
        })
    return materiais


def parse_sap_paste_to_materiais(raw_text: str, vba_mapping_config: dict[str, Any]) -> list[dict[str, Any]]:
    """Cola do SAP -> lista de materiais (campos de identificação + snapshot atual),
    prontos para virar materiais[] no BITin (o engenheiro completa alteracoes.* depois).

    Tenta primeiro `parse_com_cabecalho` (2026-07-22) -- se a colagem tiver uma linha de
    cabeçalho reconhecível, o mapeamento independe de ordem/posição (cada valor casa pelo
    NOME da coluna). Sem cabeçalho reconhecível (`None`), cai no parser posicional de sempre
    (ordem fixa da grade real da ZBPP009, ver docstring do módulo)."""
    materiais_com_cabecalho = parse_com_cabecalho(raw_text)
    if materiais_com_cabecalho is not None:
        return materiais_com_cabecalho
    return [
        plan1_row_to_material_atual(row, vba_mapping_config)
        for row in parse_sap_paste(raw_text)
    ]
