import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import logo_agente


def test_gerar_logo_devolve_imagem_rgba_no_tamanho_pedido():
    imagem = logo_agente.gerar_logo(64)
    assert imagem.size == (64, 64)
    assert imagem.mode == "RGBA"


def test_gerar_logo_escala_pro_tamanho_pedido():
    imagem = logo_agente.gerar_logo(32)
    assert imagem.size == (32, 32)
