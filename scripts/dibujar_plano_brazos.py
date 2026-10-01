"""Plano acotado de los tres brazos, para copiarlo en el CAD.

    uv run python scripts/dibujar_plano_brazos.py --out build/plano_brazos.svg

Mismo papel que `dibujar_plano_cabestrante.py`: no explica por qué, acota para
que se pueda dibujar. Los tres son pletinas planas de latón con dos agujeros,
así que de cada uno basta la vista de frente; el espesor va en una sección
común, porque es el mismo para los tres.

**El proximal es una sola pieza para los dos lados.** Los dos calajes suman
exactamente -180 grados, así que el brazo derecho es el izquierdo en espejo — y el
espejo de una chapa plana es la misma chapa, volteada. Se corta una, se
compran dos.

**El calaje lo cala una cara plana en el agujero, no un prisionero.** Un
agujero redondo con tornillo deja montar el brazo a cualquier ángulo, y
montarlo a otro ángulo escribe basura; con la cara plana solo entra de una
manera. Es el patrón del pasador de índice del cartucho: no hacer el error
improbable, hacerlo imposible.
"""

from __future__ import annotations

import argparse
import math
import sys
import textwrap
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.acotar import ESTILO, FLECHA, MM, auxiliar, contrato, cota_h, cota_v, radial

CABECERA = 50.0
PIE = 46.0

BRAZOS = {
    "proximal": ("brazo proximal · x2", "entre el eje del pivote y el codo", True),
    "distal": ("brazo distal · x2", "entre el codo y la punta: flota, dos pernos", False),
    "palanca": ("palanca del lápiz · x1", "entre el eje del tercer canal y el lápiz", True),
}

AVISOS = {
    "proximal": (
        "Se corta UNA y valen las dos: los calajes suman -180°, así que el brazo "
        "derecho es este volteado. La cara plana del agujero es lo que lo cala."
    ),
    "distal": (
        "Sin cara plana y sin calaje: es una biela, gira libre en los dos pernos. "
        "Por eso los dos extremos son iguales."
    ),
    "palanca": (
        "Su error no desplaza el trazo, lo levanta antes o después. Aun así va calada: "
        "con la palanca girada, el lápiz no apoya donde debe."
    ),
    "seccion": (
        "SIN DEFINIR: el apriete axial de los pernos. Depende de cuántas piezas se "
        "apilan en el codo y en la punta, que es cosa del montaje."
    ),
}


def obround(cx: float, cy: float, largo: float, r0: float, r1: float, k: float) -> str:
    """Contorno de una barra de dos cubos: dos círculos y sus tangentes.

    Los dos cubos pueden tener radios distintos —el que va al eje es mayor
    porque tiene que dejar pared sobre un agujero de Ø10—, así que las
    tangentes no son paralelas. El ángulo sale de la misma condición de
    perpendicularidad que la cinta del cabestrante: `cos t = (r0-r1)/largo`.
    """
    t = math.acos((r0 - r1) / largo)
    x0, x1 = cx, cx + largo * k
    p = [
        (x0 + r0 * k * math.cos(t), cy - r0 * k * math.sin(t)),
        (x1 + r1 * k * math.cos(t), cy - r1 * k * math.sin(t)),
        (x1 + r1 * k * math.cos(t), cy + r1 * k * math.sin(t)),
        (x0 + r0 * k * math.cos(t), cy + r0 * k * math.sin(t)),
    ]
    return (
        f"M {p[0][0]:.2f},{p[0][1]:.2f} L {p[1][0]:.2f},{p[1][1]:.2f} "
        f"A {r1 * k:.2f},{r1 * k:.2f} 0 1 1 {p[2][0]:.2f},{p[2][1]:.2f} "
        f"L {p[3][0]:.2f},{p[3][1]:.2f} "
        f"A {r0 * k:.2f},{r0 * k:.2f} 0 1 1 {p[0][0]:.2f},{p[0][1]:.2f} Z"
    )


def medidas(c: dict[str, float], cual: str) -> tuple[float, float, float, float, float]:
    """Largo entre centros, radios de los dos cubos y de los dos agujeros."""
    largo = c[f"brazo_{cual}"] * MM
    perno = c["brazo_perno_diametro"] * MM / 2.0
    ancho = c["brazo_ancho"] * MM / 2.0
    if cual == "distal":
        return largo, ancho, ancho, perno, perno
    eje = c["brazo_eje_diametro"] * MM / 2.0
    cubo = c["brazo_cubo_diametro"] * MM / 2.0
    return largo, cubo, ancho, eje, perno


def frente(c: dict[str, float], cual: str, x: float, y: float, ancho: float, alto: float):
    titulo, bajo, calado = BRAZOS[cual]
    largo, r0, r1, a0, a1 = medidas(c, cual)
    chaveta = c["brazo_chaveta"] * MM
    k = min(ancho * 0.78 / (largo + r0 + r1), (alto - CABECERA - PIE) / (3.2 * r0))
    cx = x + ancho / 2 - (largo / 2) * k
    cy = y + CABECERA + (alto - CABECERA - PIE) / 2

    d = [
        f'<text class="vista" x="{x + ancho / 2:.1f}" y="{y + 14:.1f}">{titulo}</text>',
        f'<text class="nota" x="{x + ancho / 2:.1f}" y="{y + 23:.1f}">{bajo}</text>',
        f'<text class="nota" x="{x + ancho / 2:.1f}" y="{y + 31:.1f}">'
        f"pletina de latón de {c['brazo_espesor'] * MM:g} · escala {k:.2f}:1</text>",
        f'<path class="corte" d="{obround(cx, cy, largo, r0, r1, k)}"/>',
    ]
    for i, (radio, agujero) in enumerate(((r0, a0), (r1, a1))):
        px = cx + i * largo * k
        d.append(
            f'<circle class="contorno" cx="{px:.2f}" cy="{cy:.2f}" '
            f'r="{agujero * k:.2f}" fill="#fff"/>'
        )
        d.append(
            f'<line class="eje" x1="{px:.2f}" y1="{cy - radio * k - 6:.2f}" '
            f'x2="{px:.2f}" y2="{cy + radio * k + 6:.2f}"/>'
        )
        d.append(auxiliar(px, cy, px, cy + radio * k + 24))
    # La cara plana del agujero del eje: lo que cala el brazo.
    if calado:
        media = math.sqrt(max(a0**2 - chaveta**2, 0.0))
        d += [
            f'<line class="contorno" x1="{cx + chaveta * k:.2f}" y1="{cy - media * k:.2f}" '
            f'x2="{cx + chaveta * k:.2f}" y2="{cy + media * k:.2f}"/>',
            f'<text class="cotatx" x="{cx:.2f}" y="{cy - r0 * k - 9:.2f}">'
            f"cara plana a {chaveta:g} del eje, cuerda {2 * media:g}</text>",
        ]
    d.append(
        f'<line class="eje" x1="{cx - r0 * k - 8:.2f}" y1="{cy:.2f}" '
        f'x2="{cx + largo * k + r1 * k + 8:.2f}" y2="{cy:.2f}"/>'
    )
    d += cota_h(cx, cx + largo * k, cy + r0 * k + 22, f"{largo:g}", f"#cota.brazo_{cual}")
    d += radial(cx, cy, a0 * k, math.radians(205), f"Ø{2 * a0:g} H7")
    d += radial(cx + largo * k, cy, a1 * k, math.radians(-25), f"Ø{2 * a1:g} H7")
    d += radial(cx, cy, r0 * k, math.radians(130), f"R{r0:g}")
    d += radial(cx + largo * k, cy, r1 * k, math.radians(50), f"R{r1:g}")
    if calado:
        d.append(
            f'<text class="var" x="{x + ancho / 2:.1f}" y="{y + alto - 32:.1f}">'
            f"#angulo.calaje_{'elevador' if cual == 'palanca' else 'izquierdo'} = "
            f"{math.degrees(c['calaje_' + ('elevador' if cual == 'palanca' else 'izquierdo')]):.3f}"
            "°</text>"
        )
    return d


def seccion(c: dict[str, float], x: float, y: float, ancho: float, alto: float):
    """El espesor, común a los tres, y la pila en un perno."""
    espesor = c["brazo_espesor"] * MM
    ancho_barra = c["brazo_ancho"] * MM
    perno = c["brazo_perno_diametro"] * MM
    k = min(ancho * 0.5 / ancho_barra, (alto - CABECERA - PIE) / (4.0 * espesor), 9.0)
    cx = x + ancho / 2
    base = y + CABECERA + (alto - CABECERA - PIE) / 2

    d = [
        f'<text class="vista" x="{cx:.1f}" y="{y + 14:.1f}">los tres · sección C-C</text>',
        f'<text class="nota" x="{cx:.1f}" y="{y + 23:.1f}">'
        "el espesor es el mismo en los tres: una pletina y tres contornos</text>",
        f'<text class="nota" x="{cx:.1f}" y="{y + 31:.1f}">escala {k:.2f}:1</text>',
    ]
    # El perno ATRAVIESA el espesor, así que en sección es un hueco de Ø6
    # en la pletina, no un círculo: dibujarlo redondo lo sacaba por arriba y
    # por abajo de una chapa de 3.
    for lado in (-1, 1):
        x0 = cx + lado * perno * k / 2
        x1 = cx + lado * ancho_barra * k / 2
        d.append(
            f'<polygon class="corte" points="{x0:.2f},{base:.2f} {x1:.2f},{base:.2f} '
            f'{x1:.2f},{base - espesor * k:.2f} {x0:.2f},{base - espesor * k:.2f}"/>'
        )
    d += [
        f'<line class="eje" x1="{cx:.2f}" y1="{base - espesor * k - 10:.2f}" '
        f'x2="{cx:.2f}" y2="{base + 10:.2f}"/>',
        f'<text class="cotatx" x="{cx:.2f}" y="{base - espesor * k - 14:.2f}">'
        f"Ø{perno:g} H7, pasante</text>",
    ]
    for lado in (-1, 1):
        d.append(
            auxiliar(
                cx + lado * ancho_barra * k / 2, base, cx + lado * ancho_barra * k / 2, base + 14
            )
        )
    d += cota_h(
        cx - ancho_barra * k / 2,
        cx + ancho_barra * k / 2,
        base + 18,
        f"{ancho_barra:g}",
        "#cota.brazo_ancho",
    )
    borde = cx + ancho_barra * k / 2
    d.append(auxiliar(borde, base, borde + 18, base))
    d.append(auxiliar(borde, base - espesor * k, borde + 18, base - espesor * k))
    d += cota_v(base - espesor * k, base, borde + 15, f"{espesor:g}")
    d.append(
        f'<text class="var" x="{cx:.1f}" y="{y + alto - 32:.1f}">'
        "#cota.brazo_espesor · #cota.brazo_perno_diametro</text>"
    )
    return d


def panel(c: dict[str, float], cual: str, x: float, y: float, ancho: float, alto: float):
    d = [
        f'<rect class="marco" x="{x:.1f}" y="{y:.1f}" '
        f'width="{ancho:.1f}" height="{alto:.1f}" rx="3"/>'
    ]
    d += seccion(c, x, y, ancho, alto) if cual == "seccion" else frente(c, cual, x, y, ancho, alto)
    for i, linea in enumerate(reversed(textwrap.wrap(AVISOS[cual], 76))):
        d.append(
            f'<text class="aviso" x="{x + 5:.1f}" y="{y + alto - 7 - 7.5 * i:.1f}">{linea}</text>'
        )
    return d


def hoja() -> str:
    c = contrato()
    ancho, alto, borde = 238.0, 196.0, 12.0
    w, h = borde * 2 + 2 * ancho, 46 + 2 * alto + borde
    partes = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{w * 2:.0f}" height="{h * 2:.0f}" '
        f'viewBox="0 0 {w:.0f} {h:.0f}">',
        f"<style>{ESTILO}</style><defs>{FLECHA}</defs>",
        f'<rect width="{w:.0f}" height="{h:.0f}" fill="#fff"/>',
        f'<text class="h1" x="{borde}" y="20">Cinco barras · plano de los tres brazos</text>',
        f'<text class="sub" x="{borde}" y="30">Cotas en mm, sacadas de docs/contratos.json '
        "con scripts/dibujar_plano_brazos.py. Pletina de latón de 3: una tira y tres "
        "contornos. Lo que la cinemática fija es la distancia entre centros.</text>",
        f'<text class="sub" x="{borde}" y="38">Del proximal se corta UNA y valen las dos: '
        "los dos calajes suman -180°, así que el derecho es el izquierdo volteado.</text>",
    ]
    for i, cual in enumerate(("proximal", "distal", "palanca", "seccion")):
        partes += panel(c, cual, borde + (i % 2) * ancho, 46 + (i // 2) * alto, ancho, alto)
    partes.append("</svg>")
    return "\n".join(partes) + "\n"


def main(argv: list[str] | None = None) -> int:
    partes = argparse.ArgumentParser(description=__doc__)
    partes.add_argument("--out", type=Path, default=Path("build/plano_brazos.svg"))
    opciones = partes.parse_args(argv)
    opciones.out.parent.mkdir(parents=True, exist_ok=True)
    opciones.out.write_text(hoja(), encoding="utf-8")
    print(f"plano en {opciones.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
