import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import estado_agente


def test_definir_e_obter_usuario():
    estado_agente.definir_usuario({"nome": "Fulano", "email": "fulano@empresa.com", "setor": "engenharia"})
    assert estado_agente.obter_usuario() == {"nome": "Fulano", "email": "fulano@empresa.com", "setor": "engenharia"}


def test_limpar_usuario():
    estado_agente.definir_usuario({"nome": "Fulano", "email": "fulano@empresa.com", "setor": "engenharia"})
    estado_agente.limpar_usuario()
    assert estado_agente.obter_usuario() is None


def test_obter_usuario_sem_ninguem_definido():
    estado_agente.limpar_usuario()
    assert estado_agente.obter_usuario() is None
