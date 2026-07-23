#!/usr/bin/env python3
"""Logo do Agente SAP - BITin, desenhada em código (PIL) -- mesmo desenho do frontend
(`frontend/src/components/bitin/AgenteLogoIcon.tsx`), pra não depender de nenhum arquivo de
imagem externo pra empacotar. Compartilhada entre `agente_app.py` (ícone da bandeja) e
`instalador.py` (tela de instalação).

Simples e ESTÁTICO, por pedido explícito do usuário (2026-07-23, depois de testar várias
versões com braço/joinha e depois com 1 olho piscando: "ícone estático sem piscar, só por ele
sorrindo"): crachá navy, rosto de robô com antena, 2 olhos abertos, e um sorriso sempre
SIMÉTRICO em torno do centro do rosto (3 pontos espelhados, não um arco de elipse que pode
enviesar visualmente, achado real: "ta errado o sorriso... faz mais simétrico")."""

from pathlib import Path

from PIL import Image, ImageDraw

_NAVY = (50, 70, 77, 255)
_BRANCO = (255, 255, 255, 255)
_LARANJA = (234, 118, 3, 255)

_GRADE = 64  # grid de desenho (mesmo viewBox do SVG do frontend) -- escalado pro `tamanho` pedido


def gerar_logo(tamanho: int = 64) -> Image.Image:
    escala = tamanho / _GRADE

    def s(valor: float) -> float:
        return valor * escala

    imagem = Image.new("RGBA", (tamanho, tamanho), (0, 0, 0, 0))
    desenho = ImageDraw.Draw(imagem)

    desenho.rounded_rectangle((s(2), s(2), s(62), s(62)), radius=s(16), fill=_NAVY)
    desenho.line((s(32), s(14), s(32), s(20)), fill=_LARANJA, width=max(1, round(s(3))))
    desenho.ellipse((s(28.5), s(7.5), s(35.5), s(14.5)), fill=_LARANJA)
    desenho.rounded_rectangle((s(16), s(20), s(48), s(46)), radius=s(10), fill=_BRANCO)

    # Os 2 olhos abertos (círculos) -- sem piscar (pedido explícito).
    desenho.ellipse((s(21.5), s(29.5), s(28.5), s(36.5)), fill=_NAVY)
    desenho.ellipse((s(35.5), s(29.5), s(42.5), s(36.5)), fill=_NAVY)

    # Boca -- sorriso SIMÉTRICO em torno do centro do rosto (x=32), pequeno e discreto
    # (achado real: "o sorriso ficou muito esquisito e grande" -- versão maior foi reduzida;
    # tentativa de tirar a boca de vez foi revertida, "mentira, ficou bom assim").
    desenho.line(
        [(s(26), s(40)), (s(32), s(42)), (s(38), s(40))],
        fill=_NAVY, width=max(1, round(s(2.2))), joint="curve",
    )

    return imagem


def gerar_ico(caminho: Path, tamanhos: tuple[int, ...] = (16, 32, 48, 128, 256)) -> None:
    """Gera o `.ico` (múltiplos tamanhos embutidos, padrão Windows) a partir da mesma logo --
    usado como `--icon` no PyInstaller (2026-07-23, pedido explícito: "ajusta os ícones dos
    executáveis") pra `AgenteSAP.exe`/`Instalador.exe` não usarem mais o ícone padrão do
    Python no Explorer/barra de tarefas."""
    base = gerar_logo(max(tamanhos))
    base.save(caminho, format="ICO", sizes=[(t, t) for t in tamanhos])


if __name__ == "__main__":
    gerar_ico(Path(__file__).resolve().parent / "icone.ico")
