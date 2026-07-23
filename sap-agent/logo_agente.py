#!/usr/bin/env python3
"""Logo do Agente SAP - BITin, desenhada em código (PIL) -- mesmo desenho do frontend
(`frontend/src/components/bitin/AgenteLogoIcon.tsx`, redesign v2 de 2026-07-23), pra não
depender de nenhum arquivo de imagem externo pra empacotar. Compartilhada entre `agente_app.py`
(ícone da bandeja/janela) e `instalador.py` (tela de instalação).

Simples e ESTÁTICO, por pedido explícito do usuário (2026-07-23, depois de testar várias
versões com braço/joinha e depois com 1 olho piscando: "ícone estático sem piscar, só por ele
sorrindo") -- continua assim mesmo no redesign v2 (que trouxe gradiente/visor/olhos em cápsula
pro lado web): crachá com gradiente navy, visor de vidro fosco, 2 olhos em cápsula sempre
abertos (sem piscar), antena laranja neutra (o Python nunca soube o status de conexão de si
mesmo pra colorir a antena -- isso é decisão do frontend), e um sorriso sempre SIMÉTRICO em
torno do centro do rosto (3 pontos espelhados, não um arco de elipse que pode enviesar
visualmente, achado real: "ta errado o sorriso... faz mais simétrico")."""

from pathlib import Path

from PIL import Image, ImageDraw

_NAVY_ESCURO = (36, 50, 55, 255)  # olhos/sorriso -- mesmo tom do frontend (#243237)
_CRACHA_TOPO = (61, 84, 92, 255)  # #3d545c
_CRACHA_BASE = (38, 52, 58, 255)  # #26343a
_VISOR_TOPO = (231, 237, 240, 255)  # #e7edf0
_VISOR_BASE = (199, 210, 214, 255)  # #c7d2d6
_ANTENA_TOPO = (243, 144, 46, 255)  # #f3902e
_ANTENA_BASE = (234, 118, 3, 255)  # #ea7603

_GRADE = 64  # grid de desenho (mesmo viewBox do SVG do frontend) -- escalado pro `tamanho` pedido


def _gradiente_vertical(largura: int, altura: int, cor_topo: tuple, cor_base: tuple) -> Image.Image:
    """Faixa RGBA com gradiente vertical linear -- PIL não desenha formas com gradiente nativo,
    então geramos a faixa à parte e usamos como fonte de cor via `Image.paste(..., mask=...)`."""
    faixa = Image.new("RGBA", (1, max(1, altura)))
    for y in range(altura):
        t = y / max(1, altura - 1)
        cor = tuple(round(cor_topo[i] + (cor_base[i] - cor_topo[i]) * t) for i in range(4))
        faixa.putpixel((0, y), cor)
    return faixa.resize((largura, altura))


def _rounded_rect_gradiente(
    imagem: Image.Image, bbox: tuple[float, float, float, float], radius: float, cor_topo: tuple, cor_base: tuple,
) -> None:
    """Desenha um retângulo arredondado preenchido com gradiente vertical, recortado pela
    própria forma (máscara alpha gerada com `rounded_rectangle`)."""
    x0, y0, x1, y1 = bbox
    largura, altura = max(1, round(x1 - x0)), max(1, round(y1 - y0))
    mascara = Image.new("L", (largura, altura), 0)
    ImageDraw.Draw(mascara).rounded_rectangle((0, 0, largura - 1, altura - 1), radius=radius, fill=255)
    gradiente = _gradiente_vertical(largura, altura, cor_topo, cor_base)
    imagem.paste(gradiente, (round(x0), round(y0)), mascara)


def gerar_logo(tamanho: int = 64) -> Image.Image:
    escala = tamanho / _GRADE

    def s(valor: float) -> float:
        return valor * escala

    imagem = Image.new("RGBA", (tamanho, tamanho), (0, 0, 0, 0))
    desenho = ImageDraw.Draw(imagem)

    # Crachá -- gradiente navy (mais volume que a cor chapada da v1).
    _rounded_rect_gradiente(imagem, (s(2), s(2), s(62), s(62)), s(18), _CRACHA_TOPO, _CRACHA_BASE)

    # Antena -- gradiente laranja, neutro (o ícone estático não tem noção de status de conexão).
    desenho.line((s(32), s(13), s(32), s(19)), fill=_ANTENA_BASE, width=max(1, round(s(2.6))))
    _rounded_rect_gradiente(imagem, (s(28.8), s(7.3), s(35.2), s(13.7)), s(3.2), _ANTENA_TOPO, _ANTENA_BASE)

    # Visor -- vidro fosco (gradiente claro) com sombra sutil por baixo, no lugar do retângulo
    # branco chapado da v1.
    desenho.rounded_rectangle((s(15), s(19), s(49), s(46)), radius=s(12), fill=(28, 40, 44, 46))
    _rounded_rect_gradiente(imagem, (s(16), s(20), s(48), s(45)), s(11), _VISOR_TOPO, _VISOR_BASE)

    # Olhos em cápsula (rounded rect vertical) -- mesmo desenho do frontend, sem piscar.
    desenho.rounded_rectangle((s(21.5), s(30.5), s(27.5), s(38.5)), radius=s(3), fill=_NAVY_ESCURO)
    desenho.rounded_rectangle((s(36.5), s(30.5), s(42.5), s(38.5)), radius=s(3), fill=_NAVY_ESCURO)

    # Boca -- sorriso SIMÉTRICO em torno do centro do rosto (x=32), pequeno e discreto
    # (achado real: "o sorriso ficou muito esquisito e grande" -- versão maior foi reduzida;
    # tentativa de tirar a boca de vez foi revertida, "mentira, ficou bom assim").
    desenho.line(
        [(s(25), s(40.5)), (s(32), s(43)), (s(39), s(40.5))],
        fill=_NAVY_ESCURO, width=max(1, round(s(2.4))), joint="curve",
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
