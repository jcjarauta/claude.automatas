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
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.acotar import ESTILO, FLECHA, MM, arco, auxiliar, contrato, cota_h, cota_v, radial

# ---------------------------------------------------------------------------
# sector
# ---------------------------------------------------------------------------


def sector_frente(c: dict[str, float], x: float, y: float, ancho: float, alto: float) -> list[str]:
    """El sector es un DISCO ENTERO, y eso hay que explicarlo.

    La cinta solo abraza 252°, así que durante un rato el sector se dibujó
    como un pac-man con una muesca de 80° mirando al tambor. La muesca no
    compra nada: el ramal sale **tangente** y se aleja, así que no roza el
    disco; el tambor queda a 10 mm del borde; y los discos vecinos se llevan
    27 mm. Lo único que ahorraba era un 22 % de plancha, a cambio de dos
    cantos rectos más que cortar y de una pieza que hay que orientar al
    montarla. Un disco con un agujero no tiene orientación.
    """
    radio = c["amplificador_sector_radio_mecanizado"] * MM
    neutra = c["amplificador_sector_radio"] * MM
    agujero = c["amplificador_sector_agujero"] * MM / 2.0
    tang = c["amplificador_tangencia"]
    k = min(ancho * 0.66 / (2 * radio), (alto - 92.0) / (2 * radio))
    cx, cy = x + ancho / 2, y + 50.0 + (alto - 92.0) / 2

    def polar(radio_: float, ang: float) -> tuple[float, float]:
        return cx + radio_ * k * math.cos(ang), cy + radio_ * k * math.sin(ang)

    d = [
        f'<text class="vista" x="{x + ancho / 2:.1f}" y="{y + 14:.1f}">'
        "sector · vista de frente</text>",
        f'<text class="nota" x="{x + ancho / 2:.1f}" y="{y + 23:.1f}">'
        "un disco de POM de 5, entero · x3 · el eje +X apunta al tambor</text>",
        f'<text class="nota" x="{x + ancho / 2:.1f}" y="{y + 31:.1f}">escala {k:.2f}:1</text>',
        f'<text class="nota" x="{x + ancho / 2:.1f}" y="{y + 39:.1f}">'
        f"la cinta abraza los {360 - 2 * math.degrees(tang):.0f}° del lado opuesto al "
        "tambor; el resto del canto va libre</text>",
        f'<circle class="corte" cx="{cx:.2f}" cy="{cy:.2f}" r="{radio * k:.2f}"/>',
        f'<circle class="contorno" cx="{cx:.2f}" cy="{cy:.2f}" r="{agujero * k:.2f}" fill="#fff"/>',
        f'<line class="eje" x1="{cx - radio * k - 9:.2f}" y1="{cy:.2f}" '
        f'x2="{cx + radio * k + 9:.2f}" y2="{cy:.2f}"/>',
        f'<line class="eje" x1="{cx:.2f}" y1="{cy - radio * k - 9:.2f}" '
        f'x2="{cx:.2f}" y2="{cy + radio * k + 9:.2f}"/>',
        f'<path class="cinta" fill="none" '
        f'd="{arco(cx, cy, neutra * k, tang, 2 * math.pi - tang)}"/>',
    ]
    d += radial(cx, cy, radio * k, math.radians(200), f"R{radio:g}")
    d += radial(cx, cy, agujero * k, math.radians(-60), f"Ø{2 * agujero:g}")
    for signo in (1, -1):
        d.append(auxiliar(cx, cy, *polar(radio + 6, signo * tang)))
        tx, ty = polar(radio + 12, signo * tang)
        d.append(
            f'<text class="cotatx" x="{tx + 6:.2f}" y="{ty + (6 if signo > 0 else -2):.2f}">'
            f"{math.degrees(tang):.1f}°</text>"
        )
    d += [
        f'<text class="var" x="{x + ancho / 2:.1f}" y="{y + alto - 41:.1f}">'
        "#cota.amplificador_sector_radio_mecanizado · #cota.amplificador_sector_agujero</text>",
        f'<text class="var" x="{x + ancho / 2:.1f}" y="{y + alto - 34:.1f}">'
        "#angulo.amplificador_tangencia</text>",
    ]
    return d


def sector_corte(c: dict[str, float], x: float, y: float, ancho: float, alto: float) -> list[str]:
    """La sección por el eje: lo que da el espesor y dónde corre la cinta."""
    radio = c["amplificador_sector_radio_mecanizado"] * MM
    neutra = c["amplificador_sector_radio"] * MM
    agujero = c["amplificador_sector_agujero"] * MM / 2.0
    espesor = c["amplificador_sector_espesor"] * MM
    w = c["cinta_ancho"] * MM
    k = min(ancho * 0.74 / (2 * radio), 2.4)
    cx, base = x + ancho / 2, y + 50.0 + (alto - 116.0) / 2 + espesor * k

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
            f'{x1:.2f},{base - espesor * k:.2f} {x0:.2f},{base - espesor * k:.2f}"/>'
        )
        xc = cx + signo * neutra * k
        d.append(
            f'<line class="cinta" x1="{xc:.2f}" y1="{base:.2f}" '
            f'x2="{xc:.2f}" y2="{base - espesor * k:.2f}"/>'
        )
    d.append(
        f'<line class="eje" x1="{cx:.2f}" y1="{base - espesor * k - 9:.2f}" '
        f'x2="{cx:.2f}" y2="{base + 9:.2f}"/>'
    )
    for lado in (-1, 1):
        d.append(auxiliar(cx + lado * radio * k, base, cx + lado * radio * k, base + 22))
        d.append(auxiliar(cx + lado * agujero * k, base, cx + lado * agujero * k, base + 13))
    d += cota_h(cx - radio * k, cx + radio * k, base + 20, f"Ø{2 * radio:g}")
    d += cota_h(cx - agujero * k, cx + agujero * k, base + 11, f"Ø{2 * agujero:g}")
    d.append(auxiliar(cx + radio * k, base - espesor * k, cx + radio * k + 16, base - espesor * k))
    d.append(auxiliar(cx + radio * k, base, cx + radio * k + 16, base))
    d += cota_v(base - espesor * k, base, cx + radio * k + 13, f"{espesor:g}")
    d += [
        f'<text class="var" x="{cx:.1f}" y="{y + alto - 34:.1f}">'
        f"#cota.amplificador_sector_espesor · la cinta, de {w:g}, va a "
        f"R{neutra:g} de fibra neutra</text>",
    ]
    return d


# ---------------------------------------------------------------------------
# tambor
# ---------------------------------------------------------------------------


def tambor_frente(c: dict[str, float], x: float, y: float, ancho: float, alto: float):
    radio = c["amplificador_tambor_radio_mecanizado"] * MM
    agujero = c["brazo_eje_diametro"] * MM / 2.0
    abraza = c["amplificador_tambor_abrazado"]
    k = min(ancho * 0.52 / (2 * radio), (alto - 92.0) / (2 * radio))
    cx, cy = x + ancho / 2, y + 50.0 + (alto - 92.0) / 2

    d = [
        f'<text class="vista" x="{x + ancho / 2:.1f}" y="{y + 14:.1f}">'
        "tambor · vista de frente</text>",
        f'<text class="nota" x="{x + ancho / 2:.1f}" y="{y + 23:.1f}">'
        "aluminio torneado · x3 · el eje +X apunta al sector</text>",
        f'<text class="nota" x="{x + ancho / 2:.1f}" y="{y + 31:.1f}">escala {k:.2f}:1</text>',
        f'<text class="nota" x="{x + ancho / 2:.1f}" y="{y + 39:.1f}">'
        f"la cinta abraza {math.degrees(abraza):g}°, centrados en la dirección al "
        "sector</text>",
        f'<circle class="corte" cx="{cx:.2f}" cy="{cy:.2f}" r="{radio * k:.2f}"/>',
        f'<circle class="contorno" cx="{cx:.2f}" cy="{cy:.2f}" r="{agujero * k:.2f}" fill="#fff"/>',
        f'<line class="eje" x1="{cx - radio * k - 9:.2f}" y1="{cy:.2f}" '
        f'x2="{cx + radio * k + 9:.2f}" y2="{cy:.2f}"/>',
        f'<line class="eje" x1="{cx:.2f}" y1="{cy - radio * k - 9:.2f}" '
        f'x2="{cx:.2f}" y2="{cy + radio * k + 9:.2f}"/>',
        f'<path class="cinta" fill="none" d="{arco(cx, cy, radio * k, -abraza / 2, abraza / 2)}"/>',
    ]
    d += radial(cx, cy, radio * k, math.radians(205), f"R{radio:g}")
    d += radial(cx, cy, agujero * k, math.radians(-65), f"Ø{2 * agujero:g} H7")
    d += [
        f'<text class="var" x="{x + ancho / 2:.1f}" y="{y + alto - 41:.1f}">'
        "#cota.amplificador_tambor_radio_mecanizado · #cota.brazo_eje_diametro</text>",
        f'<text class="var" x="{x + ancho / 2:.1f}" y="{y + alto - 34:.1f}">'
        "#angulo.amplificador_tambor_abrazado</text>",
    ]
    return d


def tambor_corte(c: dict[str, float], x: float, y: float, ancho: float, alto: float):
    """Un cilindro liso: ni garganta ni pestañas, igual que el sector.

    El tambor se dibujó con dos pestañas y el sector sin nada, y la pregunta
    obvia es por qué uno sí y el otro no. La respuesta es que **ninguno las
    necesita**: la cinta va anclada por los dos extremos, así que no puede
    andar axialmente sin estirarse. Lo que de verdad la mantiene en su sitio
    es que los dos asientos sean coplanarios, y una pestaña no arregla una
    desalineación, solo roza contra ella.
    """
    radio = c["amplificador_tambor_radio_mecanizado"] * MM
    neutra = c["amplificador_tambor_radio"] * MM
    agujero = c["brazo_eje_diametro"] * MM / 2.0
    w = c["cinta_ancho"] * MM
    total = c["amplificador_tambor_ancho"] * MM
    k = min(ancho * 0.55 / (2 * radio), (alto - 126.0) / total, 7.0)
    cx = x + ancho / 2
    base = y + 50.0 + (alto - 126.0) / 2 + total * k

    d = [
        f'<text class="vista" x="{cx:.1f}" y="{y + 14:.1f}">tambor · sección B-B</text>',
        f'<text class="nota" x="{cx:.1f}" y="{y + 23:.1f}">'
        "canto liso, sin pestañas: a la cinta la sujetan sus anclajes</text>",
        f'<text class="nota" x="{cx:.1f}" y="{y + 31:.1f}">escala {k:.2f}:1</text>',
    ]
    for signo in (1, -1):
        x0, x1 = cx + signo * agujero * k, cx + signo * radio * k
        d.append(
            f'<polygon class="corte" points="{x0:.2f},{base:.2f} {x1:.2f},{base:.2f} '
            f'{x1:.2f},{base - total * k:.2f} {x0:.2f},{base - total * k:.2f}"/>'
        )
        xc = cx + signo * neutra * k
        d.append(
            f'<line class="cinta" x1="{xc:.2f}" y1="{base - (total - w) / 2 * k:.2f}" '
            f'x2="{xc:.2f}" y2="{base - (total + w) / 2 * k:.2f}"/>'
        )
    d.append(
        f'<line class="eje" x1="{cx:.2f}" y1="{base - total * k - 10:.2f}" '
        f'x2="{cx:.2f}" y2="{base + 10:.2f}"/>'
    )
    for lado in (-1, 1):
        d.append(auxiliar(cx + lado * radio * k, base, cx + lado * radio * k, base + 22))
        d.append(auxiliar(cx + lado * agujero * k, base, cx + lado * agujero * k, base + 13))
    d += cota_h(cx - radio * k, cx + radio * k, base + 20, f"Ø{2 * radio:g}")
    d += cota_h(cx - agujero * k, cx + agujero * k, base + 11, f"Ø{2 * agujero:g} H7")
    borde = cx + radio * k
    for altura in (0.0, total):
        d.append(auxiliar(borde, base - altura * k, borde + 22, base - altura * k))
    d += cota_v(base - total * k, base, borde + 19, f"{total:g}")
    d.append(
        f'<text class="var" x="{cx:.1f}" y="{y + alto - 34:.1f}">'
        f"#cota.amplificador_tambor_ancho · la cinta, de {w:g}, centrada</text>"
    )
    return d


AVISOS = {
    "sector_frente": (
        "SIN DEFINIR: cómo se fija al brazo del seguidor. Depende de una pieza que "
        "todavía no existe, así que no se inventa aquí."
    ),
    "sector_corte": (
        "R47,975 y no R48: el radio que da la relación 6 es el de la FIBRA NEUTRA de la "
        "cinta, medio espesor por fuera del canto. El Ø16 es de paso, no un ajuste."
    ),
    "tambor_frente": (
        "SIN DEFINIR: el anclaje de los dos extremos de la cinta y el tensor. Van justo "
        "por fuera de los puntos de tangencia, y son diseño de CAD."
    ),
    "tambor_corte": (
        "Sin pestañas, igual que el sector: lo que sujeta la cinta son sus anclajes. Lo "
        "que hay que respetar es que los dos asientos queden coplanarios, 0,2 mm."
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
