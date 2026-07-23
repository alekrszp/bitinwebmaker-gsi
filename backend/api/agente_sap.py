from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from backend.config import settings

router = APIRouter()


@router.get("/download")
def download_instalador() -> FileResponse:
    """Baixa o `Instalador.exe` do agente SAP local (ver sap-agent/README.md) -- Público (sem
    login), mesmo espírito de `subgrupos.list_subgrupos`: é só um binário de instalação, não
    dado nenhum do BITin, e a tela que oferece o botão (`InstalarAgenteCard.tsx`) usa um link
    `<a>` simples (sem o client axios autenticado), então exigir token aqui não teria como
    funcionar sem reimplementar o download via blob+header -- complexidade sem ganho real de
    segurança pra um instalador que qualquer engenheiro da empresa já teria acesso de outra
    forma (compartilhado por e-mail, pasta de rede, etc.)."""
    caminho = Path(settings.AGENTE_SAP_INSTALADOR_PATH)
    if not caminho.is_file():
        raise HTTPException(
            status_code=404,
            detail="Instalador ainda não foi gerado nesta instalação do BITin. "
            "Ver sap-agent/README.md para gerar (pyinstaller).",
        )
    return FileResponse(
        path=caminho,
        # Nome simples de propósito (2026-07-23, pedido explícito: "os nomes dos arquivos
        # deixe mais simples") -- bate 1:1 com o nome do executável gerado pelo PyInstaller
        # (`--name Instalador`, ver sap-agent/README.md), sem sufixo redundante.
        filename="Instalador.exe",
        media_type="application/vnd.microsoft.portable-executable",
    )
