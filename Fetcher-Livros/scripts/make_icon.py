"""Gera book.ico (ícone de livro) em várias resoluções, sem assets externos."""

from pathlib import Path

from PIL import Image, ImageDraw

OUT = Path(__file__).resolve().parent.parent / "assets" / "book.ico"

# Paleta (tema da Biblioteca Astral: roxo escuro + dourado)
BG = (24, 16, 43, 0)         # transparente
COVER = (108, 74, 182)       # roxo
COVER_DK = (74, 48, 130)     # roxo escuro (lombada)
PAGES = (243, 240, 230)      # creme
LINE = (201, 162, 39)        # dourado
SPINE = (201, 162, 39)


def render(size: int) -> Image.Image:
    # desenha em alta resolução e reduz (antialias)
    S = size * 4
    img = Image.new("RGBA", (S, S), BG)
    d = ImageDraw.Draw(img)

    m = S * 0.16          # margem
    w = S - 2 * m
    h = S - 2 * m
    x0, y0 = m, m + h * 0.06
    x1, y1 = m + w, m + h * 0.94

    r = S * 0.06
    # capa
    d.rounded_rectangle([x0, y0, x1, y1], radius=r, fill=COVER)
    # lombada (faixa esquerda mais escura)
    spine_w = w * 0.18
    d.rounded_rectangle([x0, y0, x0 + spine_w, y1], radius=r, fill=COVER_DK)
    # bloco de páginas (lado direito)
    pad = S * 0.05
    px0 = x0 + spine_w + pad * 0.4
    d.rounded_rectangle([px0, y0 + pad, x1 - pad, y1 - pad], radius=r * 0.5, fill=PAGES)
    # linhas de texto
    lx0 = px0 + pad * 0.8
    lx1 = x1 - pad * 1.6
    lh = (y1 - y0 - 2 * pad) / 7
    lw = max(2, int(S * 0.012))
    for i in range(5):
        yy = y0 + pad * 1.8 + i * lh
        d.line([lx0, yy, lx1 if i % 2 == 0 else lx1 - (lx1 - lx0) * 0.3, yy],
               fill=LINE, width=lw)
    # estrela dourada (toque astral) no canto da capa
    cx, cy, rad = x0 + spine_w * 0.5, y0 + h * 0.16, S * 0.03
    d.ellipse([cx - rad, cy - rad, cx + rad, cy + rad], fill=LINE)

    return img.resize((size, size), Image.LANCZOS)


def main() -> None:
    sizes = [16, 24, 32, 48, 64, 128, 256]
    base = render(256)
    base.save(OUT, format="ICO", sizes=[(s, s) for s in sizes])
    # PNG p/ visualização/preview
    base.save(OUT.with_suffix(".png"))
    print("icone salvo:", OUT)


if __name__ == "__main__":
    main()
