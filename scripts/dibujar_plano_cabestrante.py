"""Plano acotado del sector y del tambor, para copiarlo en el CAD.

    uv run python scripts/dibujar_plano_cabestrante.py --out build/plano.svg

La hoja de `dibujar_amplificador.py` explica **por qué** cada cota es la que
es. Esta no explica nada: es el plano que se tiene al lado para dibujar, con
dos vistas por pieza y las cotas con su línea, sus flechas y su número.

**Lo que acota es el contorno completo**, no solo las interfaces, porque un
contorno a medias no se puede copiar. Lo que sigue sin decidir —cómo se fija
el sector al brazo del seguidor y cómo se ancla la cinta— lleva su aviso y no
se inventa: depende de piezas que todavía no existen.

Todas las cotas salen de `docs/contratos.json`. Si una no cuadra con el CAD,
manda el contrato.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

RAIZ = Path(__file__).resolve().parent.parent
CONTRATOS = RAIZ / "docs" / "contratos.json"
MM = 1000.0

ESTILO = """
text{font-family:Helvetica,Arial,sans-serif;fill:#1b1b1b}
.h1{font-size:12px;font-weight:bold}
.sub{font-size:5.8px;fill:#555}
.vista{font-size:7px;font-weight:bold;text-anchor:middle}
.nota{font-size:5.2px;fill:#555;text-anchor:middle}
.aviso{font-size:5.2px;fill:#8a4a00}
.marco{fill:none;stroke:#ddd;stroke-width:0.6}
.corte{fill:#dde5ee;stroke:#1b1b1b;stroke-width:0.9}
.contorno{fill:none;stroke:#1b1b1b;stroke-width:0.9}
.cinta{fill:none;stroke:#b03030;stroke-width:1.6;stroke-linecap:round}
.eje{stroke:#1b5fb0;stroke-width:0.5;stroke-dasharray:7 2 1.2 2}
.aux{stroke:#9aa7b4;stroke-width:0.4}
.cotaln{stroke:#b03030;stroke-width:0.45}
.cotatx{font-size:5.4px;fill:#b03030;text-anchor:middle}
.cotatxi{font-size:5.4px;fill:#b03030}
.var{font-size:4.8px;fill:#1b5fb0;font-family:monospace;text-anchor:middle}
"""

FLECHA = (
    '<marker id="f" markerWidth="7" markerHeight="7" refX="6.4" refY="2.2" orient="auto">'
    '<path d="M0,0 L6.6,2.2 L0,4.4 z" fill="#b03030"/></marker>'
)


def contrato() -> dict[str, float]:
    datos = json.loads(CONTRATOS.read_text(encoding="utf-8"))
    return {v["nombre"]: float(v["valor"]) for g in datos["contratos"] for v in g["valores"]}


def cota_h(x0: float, x1: float, y: float, texto: str, variable: str = "") -> list[str]:
    """Cota horizontal: línea con flechas a los dos lados y el número encima."""
    d = [
        f'<line class="cotaln" marker-start="url(#f)" marker-end="url(#f)" '
        f'x1="{x0:.2f}" y1="{y:.2f}" x2="{x1:.2f}" y2="{y:.2f}"/>',
        f'<text class="cotatx" x="{(x0 + x1) / 2:.2f}" y="{y - 2.5:.2f}">{texto}</text>',
    ]
    if variable:
        d.append(f'<text class="var" x="{(x0 + x1) / 2:.2f}" y="{y + 6:.2f}">{variable}</text>')
    return d


def cota_v(y0: float, y1: float, x: float, texto: str) -> list[str]:
    """Cota vertical, con el número girado para que se lea de abajo arriba."""
    ym = (y0 + y1) / 2
    return [
        f'<line class="cotaln" marker-start="url(#f)" marker-end="url(#f)" '
        f'x1="{x:.2f}" y1="{y0:.2f}" x2="{x:.2f}" y2="{y1:.2f}"/>',
        f'<text class="cotatx" x="{x - 3:.2f}" y="{ym:.2f}" '
        f'transform="rotate(-90 {x - 3:.2f} {ym:.2f})">{texto}</text>',
    ]


def auxiliar(x0: float, y0: float, x1: float, y1: float) -> str:
    return f'<line class="aux" x1="{x0:.2f}" y1="{y0:.2f}" x2="{x1:.2f}" y2="{y1:.2f}"/>'


def radial(cx: float, cy: float, r: float, ang: float, texto: str) -> list[str]:
    """Cota de radio: una flecha desde el centro hasta el arco."""
    x1, y1 = cx + r * math.cos(ang), cy + r * math.sin(ang)
    xt, yt = cx + (r + 9) * math.cos(ang), cy + (r + 9) * math.sin(ang)
    return [
        f'<line class="cotaln" marker-end="url(#f)" x1="{cx:.2f}" y1="{cy:.2f}" '
        f'x2="{x1:.2f}" y2="{y1:.2f}"/>',
        f'<text class="cotatx" x="{xt:.2f}" y="{yt:.2f}">{texto}</text>',
    ]


def arco(cx: float, cy: float, r: float, a0: float, a1: float) -> str:
    x0, y0 = cx + r * math.cos(a0), cy + r * math.sin(a0)
    x1, y1 = cx + r * math.cos(a1), cy + r * math.sin(a1)
    grande = 1 if (a1 - a0) % (2 * math.pi) > math.pi else 0
    return f"M {x0:.2f},{y0:.2f} A {r:.2f},{r:.2f} 0 {grande} 1 {x1:.2f},{y1:.2f}"


# ---------------------------------------------------------------------------
# sector
# ---------------------------------------------------------------------------


def sector_frente(c: dict[str, float], x: float, y: float, ancho: float, alto: float) -> list[str]:
    """La vista que hay que dibujar en el croquis: el sector de frente."""
    radio = c["amplificador_sector_radio_mecanizado"] * MM
    neutra = c["amplificador_sector_radio"] * MM
    agujero = c["amplificador_sector_agujero"] * MM / 2.0
    semi = c["amplificador_sector_semiarco"]
    tang = c["amplificador_tangencia"]
    k = min(ancho * 0.72 / (2 * radio), (alto - 92.0) / (2 * radio))
    cx, cy = x + ancho * 0.44, y + 50.0 + (alto - 92.0) / 2

    # El sector lleva material donde la cinta lo toca, que es el arco
    # OPUESTO al tambor: ±semiarco alrededor de 180°, con la muesca mirando
    # al tambor. La tangencia, en cambio, se mide desde +X.
    eje = math.pi
    a0, a1 = eje - semi, eje + semi

    def polar(radio_: float, ang: float) -> tuple[float, float]:
        return cx + radio_ * k * math.cos(ang), cy + radio_ * k * math.sin(ang)

    camino = (
        "M {:.2f},{:.2f} ".format(*polar(agujero, a0))
        + "L {:.2f},{:.2f} ".format(*polar(radio, a0))
        + arco(cx, cy, radio * k, a0, a1).replace("M", "L", 1)
        + " L {:.2f},{:.2f} ".format(*polar(agujero, a1))
        + arco(cx, cy, agujero * k, a1, a0).replace("M", "L", 1)
        + " Z"
    )
    d = [
        f'<text class="vista" x="{x + ancho / 2:.1f}" y="{y + 14:.1f}">'
        "sector · vista de frente</text>",
        f'<text class="nota" x="{x + ancho / 2:.1f}" y="{y + 23:.1f}">'
        "una plancha de POM de 5 · x3 · el eje +X apunta al tambor</text>",
        f'<text class="nota" x="{x + ancho / 2:.1f}" y="{y + 31:.1f}">escala {k:.2f}:1</text>',
        f'<path class="corte" d="{camino}"/>',
        f'<circle class="contorno" cx="{cx:.2f}" cy="{cy:.2f}" r="{agujero * k:.2f}" fill="#fff"/>',
        f'<line class="eje" x1="{cx - radio * k - 8:.2f}" y1="{cy:.2f}" '
        f'x2="{cx + radio * k + 14:.2f}" y2="{cy:.2f}"/>',
        f'<line class="eje" x1="{cx:.2f}" y1="{cy - radio * k - 8:.2f}" '
        f'x2="{cx:.2f}" y2="{cy + radio * k + 8:.2f}"/>',
        f'<path class="cinta" fill="none" '
        f'd="{arco(cx, cy, neutra * k, tang, 2 * math.pi - tang)}"/>',
    ]
    d += radial(cx, cy, radio * k, math.radians(195), f"R{radio:g}")
    d += radial(cx, cy, agujero * k, math.radians(-60), f"R{agujero:g}")
    # Los dos cantos del sector, que es lo que hay que acotar para cortarlo.
    for ang in (a0, a1):
        ax, ay = polar(radio + 8, ang)
        d.append(auxiliar(cx, cy, ax, ay))
        d.append(
            f'<text class="cotatx" x="{ax:.2f}" y="{ay + (7 if ang > eje else -3):.2f}">'
            f"{math.degrees(semi):g}° del eje -X</text>"
        )
    # Y donde entra la cinta, que cae del lado del tambor aunque abrace el otro.
    for signo in (1, -1):
        d.append(auxiliar(cx, cy, *polar(neutra + 5, signo * tang)))
        tx, ty = polar(neutra + 11, signo * tang)
        d.append(
            f'<text class="cotatx" x="{tx:.2f}" y="{ty + (6 if signo > 0 else -2):.2f}">'
            f"{math.degrees(tang):.1f}°</text>"
        )
    d.append(
        f'<text class="nota" x="{x + ancho / 2:.1f}" y="{y + 39:.1f}">'
        f"la cinta abraza los {360 - 2 * math.degrees(tang):.0f}° del lado opuesto al "
        "tambor; la muesca mira al tambor</text>"
    )
    d += [
        f'<text class="var" x="{x + ancho / 2:.1f}" y="{y + alto - 30:.1f}">'
        "#cota.amplificador_sector_radio_mecanizado · #cota.amplificador_sector_agujero</text>",
        f'<text class="var" x="{x + ancho / 2:.1f}" y="{y + alto - 23:.1f}">'
        "#angulo.amplificador_sector_semiarco · #angulo.amplificador_tangencia</text>",
    ]
    return d


def sector_corte(c: dict[str, float], x: float, y: float, ancho: float, alto: float) -> list[str]:
    """La sección por el eje: lo que da el espesor y dónde corre la cinta."""
    radio = c["amplificador_sector_radio_mecanizado"] * MM
    neutra = c["amplificador_sector_radio"] * MM
    agujero = c["amplificador_sector_agujero"] * MM / 2.0
    w = c["cinta_ancho"] * MM
    k = min(ancho * 0.74 / (2 * radio), 2.4)
    cx, base = x + ancho / 2, y + 50.0 + (alto - 116.0) / 2 + w * k

    d = [
        f'<text class="vista" x="{cx:.1f}" y="{y + 14:.1f}">sector · sección A-A</text>',
        f'<text class="nota" x="{cx:.1f}" y="{y + 23:.1f}">'
        "el canto es liso: la cinta no lleva garganta, la retienen sus anclajes</text>",
        f'<text class="nota" x="{cx:.1f}" y="{y + 31:.1f}">escala {k:.2f}:1</text>',
    ]
    for signo in (1, -1):
        x0, x1 = cx + signo * agujero * k, cx + signo * radio * k
        d.append(
            f'<polygon class="corte" points="{x0:.2f},{base:.2f} {x1:.2f},{base:.2f} '
            f'{x1:.2f},{base - w * k:.2f} {x0:.2f},{base - w * k:.2f}"/>'
        )
        xc = cx + signo * neutra * k
        d.append(
            f'<line class="cinta" x1="{xc:.2f}" y1="{base:.2f}" '
            f'x2="{xc:.2f}" y2="{base - w * k:.2f}"/>'
        )
    d.append(
        f'<line class="eje" x1="{cx:.2f}" y1="{base - w * k - 9:.2f}" '
        f'x2="{cx:.2f}" y2="{base + 9:.2f}"/>'
    )
    for lado in (-1, 1):
        d.append(auxiliar(cx + lado * radio * k, base, cx + lado * radio * k, base + 22))
        d.append(auxiliar(cx + lado * agujero * k, base, cx + lado * agujero * k, base + 13))
    d += cota_h(cx - radio * k, cx + radio * k, base + 20, f"Ø{2 * radio:g}")
    d += cota_h(cx - agujero * k, cx + agujero * k, base + 11, f"Ø{2 * agujero:g}")
    d.append(auxiliar(cx + radio * k, base - w * k, cx + radio * k + 16, base - w * k))
    d.append(auxiliar(cx + radio * k, base, cx + radio * k + 16, base))
    d += cota_v(base - w * k, base, cx + radio * k + 13, f"{w:g}")
    d += [
        f'<text class="var" x="{cx:.1f}" y="{y + alto - 23:.1f}">'
        "#cota.cinta_ancho · la línea roja es la cinta, a R"
        f"{neutra:g} de fibra neutra</text>",
    ]
    return d


# ---------------------------------------------------------------------------
# tambor
# ---------------------------------------------------------------------------


def tambor_frente(c: dict[str, float], x: float, y: float, ancho: float, alto: float) -> list[str]:
    radio = c["amplificador_tambor_radio_mecanizado"] * MM
    pestana = c["amplificador_tambor_pestana_radio"] * MM
    agujero = c["brazo_eje_diametro"] * MM / 2.0
    abraza = c["amplificador_tambor_abrazado"]
    k = min(ancho * 0.60 / (2 * pestana), (alto - 92.0) / (2 * pestana))
    cx, cy = x + ancho * 0.46, y + 50.0 + (alto - 92.0) / 2

    d = [
        f'<text class="vista" x="{x + ancho / 2:.1f}" y="{y + 14:.1f}">'
        "tambor · vista de frente</text>",
        f'<text class="nota" x="{x + ancho / 2:.1f}" y="{y + 23:.1f}">'
        "aluminio torneado · x3 · el eje +X apunta al sector</text>",
        f'<text class="nota" x="{x + ancho / 2:.1f}" y="{y + 31:.1f}">escala {k:.2f}:1</text>',
        f'<circle class="contorno" cx="{cx:.2f}" cy="{cy:.2f}" r="{pestana * k:.2f}"/>',
        f'<circle class="corte" cx="{cx:.2f}" cy="{cy:.2f}" r="{radio * k:.2f}"/>',
        f'<circle class="contorno" cx="{cx:.2f}" cy="{cy:.2f}" r="{agujero * k:.2f}" fill="#fff"/>',
        f'<line class="eje" x1="{cx - pestana * k - 8:.2f}" y1="{cy:.2f}" '
        f'x2="{cx + pestana * k + 8:.2f}" y2="{cy:.2f}"/>',
        f'<line class="eje" x1="{cx:.2f}" y1="{cy - pestana * k - 8:.2f}" '
        f'x2="{cx:.2f}" y2="{cy + pestana * k + 8:.2f}"/>',
        f'<path class="cinta" fill="none" d="{arco(cx, cy, radio * k, -abraza / 2, abraza / 2)}"/>',
    ]
    d += radial(cx, cy, radio * k, math.radians(-125), f"R{radio:g}")
    d += radial(cx, cy, pestana * k, math.radians(-55), f"R{pestana:g}")
    d += radial(cx, cy, agujero * k, math.radians(145), f"Ø{2 * agujero:g} H7")
    d += [
        f'<text class="nota" x="{x + ancho / 2:.1f}" y="{y + 39:.1f}">'
        f"la cinta abraza {math.degrees(abraza):g}°, centrados en la dirección al "
        "sector</text>",
        f'<text class="var" x="{x + ancho / 2:.1f}" y="{y + alto - 30:.1f}">'
        "#cota.amplificador_tambor_radio_mecanizado · "
        "#cota.amplificador_tambor_pestana_radio</text>",
        f'<text class="var" x="{x + ancho / 2:.1f}" y="{y + alto - 23:.1f}">'
        "#cota.brazo_eje_diametro · #angulo.amplificador_tambor_abrazado</text>",
    ]
    return d


def tambor_corte(c: dict[str, float], x: float, y: float, ancho: float, alto: float) -> list[str]:
    radio = c["amplificador_tambor_radio_mecanizado"] * MM
    neutra = c["amplificador_tambor_radio"] * MM
    pestana = c["amplificador_tambor_pestana_radio"] * MM
    agujero = c["brazo_eje_diametro"] * MM / 2.0
    w = c["cinta_ancho"] * MM
    total = c["amplificador_tambor_ancho"] * MM
    ala = (total - w) / 2.0
    k = min(ancho * 0.60 / (2 * pestana), (alto - 120.0) / total, 7.0)
    cx = x + ancho / 2
    base = y + 50.0 + (alto - 126.0) / 2 + total * k

    d = [
        f'<text class="vista" x="{cx:.1f}" y="{y + 14:.1f}">tambor · sección B-B</text>',
        f'<text class="nota" x="{cx:.1f}" y="{y + 23:.1f}">'
        "las dos pestañas retienen la cinta; entre ellas, el canto útil</text>",
        f'<text class="nota" x="{cx:.1f}" y="{y + 31:.1f}">escala {k:.2f}:1</text>',
    ]
    for signo in (1, -1):
        xi = cx + signo * agujero * k
        xr = cx + signo * radio * k
        xp = cx + signo * pestana * k
        puntos = [
            (xi, base),
            (xp, base),
            (xp, base - ala * k),
            (xr, base - ala * k),
            (xr, base - (ala + w) * k),
            (xp, base - (ala + w) * k),
            (xp, base - total * k),
            (xi, base - total * k),
        ]
        d.append(
            '<polygon class="corte" points="'
            + " ".join(f"{px:.2f},{py:.2f}" for px, py in puntos)
            + '"/>'
        )
        xc = cx + signo * neutra * k
        d.append(
            f'<line class="cinta" x1="{xc:.2f}" y1="{base - ala * k:.2f}" '
            f'x2="{xc:.2f}" y2="{base - (ala + w) * k:.2f}"/>'
        )
    d.append(
        f'<line class="eje" x1="{cx:.2f}" y1="{base - total * k - 9:.2f}" '
        f'x2="{cx:.2f}" y2="{base + 9:.2f}"/>'
    )
    for lado in (-1, 1):
        d.append(auxiliar(cx + lado * pestana * k, base, cx + lado * pestana * k, base + 22))
        d.append(auxiliar(cx + lado * radio * k, base, cx + lado * radio * k, base + 13))
    d += cota_h(cx - pestana * k, cx + pestana * k, base + 20, f"Ø{2 * pestana:g}")
    d += cota_h(cx - radio * k, cx + radio * k, base + 11, f"Ø{2 * radio:g}")
    borde = cx + pestana * k
    for altura in (0.0, ala, ala + w, total):
        d.append(auxiliar(borde, base - altura * k, borde + 26, base - altura * k))
    d += cota_v(base - total * k, base, borde + 23, f"{total:g}")
    d += cota_v(base - (ala + w) * k, base - ala * k, borde + 12, f"{w:g}")
    d += [
        f'<text class="var" x="{cx:.1f}" y="{y + alto - 23:.1f}">'
        f"#cota.amplificador_tambor_ancho · #cota.cinta_ancho · "
        f"pestañas de {ala:g} a cada lado</text>",
    ]
    return d


AVISOS = {
    "sector_frente": (
        "SIN DEFINIR: cómo se fija al brazo del seguidor. Depende de una pieza que "
        "todavía no existe, así que no se inventa aquí."
    ),
    "sector_corte": (
        "El agujero de Ø16 es de PASO, no un ajuste: libra la valona de Ø15 del "
        "casquillo. Quien centra el sector es su fijación al brazo."
    ),
    "tambor_frente": (
        "SIN DEFINIR: el anclaje de los dos extremos de la cinta y el tensor. Van en "
        "el tambor y en el sector, y son diseño de CAD."
    ),
    "tambor_corte": (
        "R7,975 y no R8: el radio que da la relación 6 es el de la FIBRA NEUTRA de la "
        "cinta, medio espesor por fuera del canto torneado."
    ),
}

PANELES = {
    "sector_frente": sector_frente,
    "sector_corte": sector_corte,
    "tambor_frente": tambor_frente,
    "tambor_corte": tambor_corte,
}


def panel(c: dict[str, float], cual: str, x: float, y: float, ancho: float, alto: float):
    import textwrap

    d = [
        f'<rect class="marco" x="{x:.1f}" y="{y:.1f}" '
        f'width="{ancho:.1f}" height="{alto:.1f}" rx="3"/>'
    ]
    d += PANELES[cual](c, x, y, ancho, alto)
    for i, linea in enumerate(reversed(textwrap.wrap(AVISOS[cual], 76))):
        d.append(
            f'<text class="aviso" x="{x + 5:.1f}" y="{y + alto - 7 - 7.5 * i:.1f}">{linea}</text>'
        )
    return d


def hoja() -> str:
    c = contrato()
    ancho, alto, borde = 238.0, 214.0, 12.0
    w, h = borde * 2 + 2 * ancho, 46 + 2 * alto + borde
    partes = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{w * 2:.0f}" height="{h * 2:.0f}" '
        f'viewBox="0 0 {w:.0f} {h:.0f}">',
        f"<style>{ESTILO}</style><defs>{FLECHA}</defs>",
        f'<rect width="{w:.0f}" height="{h:.0f}" fill="#fff"/>',
        f'<text class="h1" x="{borde}" y="20">Cabestrante 6:1 · plano del sector y del '
        "tambor</text>",
        f'<text class="sub" x="{borde}" y="30">Cotas en mm, sacadas de docs/contratos.json '
        "con scripts/dibujar_plano_cabestrante.py. Tres de cada. El sector gira con el "
        "seguidor; el tambor, con el brazo.</text>",
        f'<text class="sub" x="{borde}" y="38">La relación 6:1 la dan los radios de FIBRA '
        f"NEUTRA —{c['amplificador_sector_radio'] * MM:g} y "
        f"{c['amplificador_tambor_radio'] * MM:g}—; lo que se mecaniza es medio espesor de "
        "cinta menos.</text>",
    ]
    for i, cual in enumerate(("sector_frente", "sector_corte", "tambor_frente", "tambor_corte")):
        partes += panel(c, cual, borde + (i % 2) * ancho, 46 + (i // 2) * alto, ancho, alto)
    partes.append("</svg>")
    return "\n".join(partes) + "\n"


def main(argv: list[str] | None = None) -> int:
    partes = argparse.ArgumentParser(description=__doc__)
    partes.add_argument("--out", type=Path, default=Path("build/plano_cabestrante.svg"))
    opciones = partes.parse_args(argv)
    opciones.out.parent.mkdir(parents=True, exist_ok=True)
    opciones.out.write_text(hoja(), encoding="utf-8")
    print(f"plano en {opciones.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
