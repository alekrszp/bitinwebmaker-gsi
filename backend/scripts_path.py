"""Coloca scripts/ no sys.path (mesmo padrão usado em tests/) e carrega os configs de
config/*.json uma única vez -- backend/ é só orquestração em cima da lógica de scripts/,
não duplica nada. Importar este módulo primeiro, antes de importar qualquer coisa de
scripts/, garante que o path já está pronto."""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = ROOT / "scripts"

if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

VBA_MAPPING_CONFIG_PATH = ROOT / "config" / "vba_mapping.json"
DOCUMENT_CONFIG_PATH = ROOT / "config" / "bitin_document_mapping.json"
LISTA_TECNICA_CONFIG_PATH = ROOT / "config" / "lista_tecnica_mapping.json"
