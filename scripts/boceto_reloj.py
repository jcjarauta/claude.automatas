"""Boceto acotado de una pieza del reloj, leyendo las cotas del contrato.

    uv run python scripts/boceto_reloj.py --pieza varilla --out build/

**Provisional, y a proposito.** El emisor de verdad es `emit/reloj/` y llega
en R4, con `emit/layout.py` detras y plantillas 1:1 con cuadro de
calibracion. Esto es la prueba de que la cadena cierra: contrato -> CSV ->
variables de Onshape -> boceto, sin teclear un numero por el camino.

**No es una plantilla de corte.** Las vistas van a escalas distintas y
rotuladas, que es lo que `docs/metodologia.md` permite en el dossier y
prohibe en la plantilla. Quien corte por esta hoja corta mal.

Cada cota lleva debajo el nombre de la variable de la que sale, para que se
pueda cruzar con el Variable Studio de un vistazo. Esa anotacion no es de
norma: esta porque el objeto de esta hoja es comprobar el enlace, no fabricar.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from compile.contratos import Contratos, cargar

RELOJ = Path("docs/reloj/contratos.json")

TINTA = "#1a1a1a"
COTA = "#0b63c5"
AUX = "#9aa0a6"

CABEZA = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 760 560"
 font-family="Helvetica, Arial, sans-serif">
<defs><marker id="f" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7"
 orient="auto-start-reverse"><path d="M0 0L10 5L0 10z" fill="{cota}"/></marker></defs>
<rect x="0" y="0" width="760" height="560" fill="#ffffff"/>"""


def _texto(
    x: float,
    y: float,
    s: str,
    tam: float = 9.5,
    color: str = TINTA,
    ancla: str = "middle",
    peso: str = "normal",
) -> str:
    return (
        f'<text x="{x:.1f}" y="{y:.1f}" font-size="{tam}" fill="{color}" '
        f'text-anchor="{ancla}" font-weight="{peso}">{s}</text>'
    )


def _cota_h(x0: float, x1: float, y: float, etiqueta: str, variable: str) -> str:
    """Cota horizontal con sus lineas de referencia."""
    medio = (x0 + x1) / 2
    return "".join(
        [
            f'<path d="M{x0:.1f} {y - 22:.1f}V{y + 4:.1f}" stroke="{AUX}" stroke-width="0.6"/>',
            f'<path d="M{x1:.1f} {y - 22:.1f}V{y + 4:.1f}" stroke="{AUX}" stroke-width="0.6"/>',
            f'<path d="M{x0:.1f} {y:.1f}H{x1:.1f}" stroke="{COTA}" stroke-width="1" '
            f'marker-start="url(#f)" marker-end="url(#f)"/>',
            _texto(medio, y - 5, etiqueta, 10, COTA, peso="bold"),
            _texto(medio, y + 13, variable, 7.5, AUX),
        ]
    )


def _cota_v(y0: float, y1: float, x: float, etiqueta: str, variable: str) -> str:
    medio = (y0 + y1) / 2
    return "".join(
        [
            f'<path d="M{x - 4:.1f} {y0:.1f}H{x + 22:.1f}" stroke="{AUX}" stroke-width="0.6"/>',
            f'<path d="M{x - 4:.1f} {y1:.1f}H{x + 22:.1f}" stroke="{AUX}" stroke-width="0.6"/>',
            f'<path d="M{x:.1f} {y0:.1f}V{y1:.1f}" stroke="{COTA}" stroke-width="1" '
            f'marker-start="url(#f)" marker-end="url(#f)"/>',
            _texto(x - 7, medio + 3, etiqueta, 10, COTA, ancla="end", peso="bold"),
            _texto(x - 7, medio + 14, variable, 7.5, AUX, ancla="end"),
        ]
    )


def varilla(c: Contratos) -> str:
    """La pieza 1.1: la primera que se corta, y la raiz de la cadena causal."""
    largo = c.valor("pendulo", "varilla_largo").en_mm
    ancho = c.valor("pendulo", "varilla_ancho").en_mm
    espesor = c.valor("pendulo", "varilla_espesor").en_mm
    sobrante = c.valor("pendulo", "varilla_sobrante").en_mm
    taladro = c.valor("pendulo", "varilla_taladro_diametro").en_mm
    cerca = c.valor("pendulo", "varilla_taladro_cerca").en_mm
    lejos = c.valor("pendulo", "varilla_taladro_lejos").en_mm
    nominal = c.valor("oscilador", "longitud_pendulo_nominal").en_mm

    p: list[str] = [CABEZA.format(cota=COTA)]
    p.append(_texto(34, 34, "1.1 · VARILLA DEL PÉNDULO", 15, TINTA, "start", "bold"))
    p.append(
        _texto(
            34,
            50,
            "Boceto de comprobación · cotas leídas de docs/reloj/contratos.json",
            9.5,
            AUX,
            "start",
        )
    )

    # ---- vista principal, horizontal, 1:2, con rotura -------------------
    e = 0.5
    x0, yc = 70.0, 120.0
    alto = ancho * e
    izq = 240.0 * e
    der = 140.0 * e
    hueco = 30.0
    xr = x0 + izq
    x1 = xr + hueco
    x2 = x1 + der
    p.append(
        f'<rect x="{x0}" y="{yc - alto / 2:.1f}" width="{izq:.1f}" height="{alto:.1f}" '
        f'fill="none" stroke="{TINTA}" stroke-width="1.4"/>'
    )
    p.append(
        f'<rect x="{x1:.1f}" y="{yc - alto / 2:.1f}" width="{der:.1f}" height="{alto:.1f}" '
        f'fill="none" stroke="{TINTA}" stroke-width="1.4"/>'
    )
    # rotura
    p.append(
        f'<path d="M{xr:.1f} {yc - alto / 2 - 4:.1f}l6 4l-6 4l6 4l-6 4" fill="none" '
        f'stroke="{TINTA}" stroke-width="1"/>'
    )
    p.append(
        f'<path d="M{x1:.1f} {yc - alto / 2 - 4:.1f}l-6 4l6 4l-6 4l6 4" fill="none" '
        f'stroke="{TINTA}" stroke-width="1"/>'
    )
    for cx in (x0 + cerca * e, x0 + lejos * e):
        p.append(
            f'<circle cx="{cx:.1f}" cy="{yc:.1f}" r="{taladro * e / 2:.2f}" fill="none" '
            f'stroke="{TINTA}" stroke-width="1"/>'
        )
    # sobrante, rayado
    p.append(
        f'<rect x="{x2 - sobrante * e:.1f}" y="{yc - alto / 2:.1f}" width="{sobrante * e:.1f}" '
        f'height="{alto:.1f}" fill="{AUX}" fill-opacity="0.25" stroke="{AUX}" '
        f'stroke-width="0.8" stroke-dasharray="3 2"/>'
    )
    p.append(_cota_h(x0, x2, yc + 46, f"{largo:.0f}", "#cota.varilla_largo"))
    p.append(_cota_h(x2 - sobrante * e, x2, yc - 34, f"{sobrante:.0f}", "#cota.varilla_sobrante"))
    p.append(_texto(x2 + 10, yc - 38, "sobrante: se recorta al regular", 8, AUX, "start"))
    p.append(_texto(x0, yc + 78, "VISTA PRINCIPAL · escala 1:2 · con rotura", 9, TINTA, "start"))
    p.append(
        _texto(
            x0,
            yc + 91,
            f"longitud de péndulo nominal {nominal:.0f} mm, más 40 sobre el "
            f"punto de flexión y 46 bajo el centro de la lenteja",
            8,
            AUX,
            "start",
        )
    )

    # ---- detalle A, extremo de arriba, 2:1 ------------------------------
    d = 2.0
    ax, ay = 470.0, 150.0
    ah = ancho * d
    p.append(_texto(ax, 78, "DETALLE A · extremo superior · escala 2:1", 9, TINTA, "start"))
    p.append(
        f'<rect x="{ax}" y="{ay - ah / 2:.1f}" width="{60 * d:.1f}" height="{ah:.1f}" '
        f'fill="none" stroke="{TINTA}" stroke-width="1.4"/>'
    )
    for pos in (cerca, lejos):
        cx = ax + pos * d
        p.append(
            f'<circle cx="{cx:.1f}" cy="{ay:.1f}" r="{taladro * d / 2:.2f}" fill="none" '
            f'stroke="{TINTA}" stroke-width="1.2"/>'
        )
        p.append(
            f'<path d="M{cx:.1f} {ay - ah / 2 - 6:.1f}V{ay + ah / 2 + 6:.1f}" stroke="{AUX}" '
            f'stroke-width="0.6" stroke-dasharray="4 2"/>'
        )
    p.append(_cota_h(ax, ax + cerca * d, ay + 44, f"{cerca:.0f}", "#cota.varilla_taladro_cerca"))
    p.append(_cota_h(ax, ax + lejos * d, ay + 76, f"{lejos:.0f}", "#cota.varilla_taladro_lejos"))
    p.append(
        f'<path d="M{ax + cerca * d:.1f} {ay - ah / 2 - 10:.1f}l16 -16h40" stroke="{COTA}" '
        f'stroke-width="1" fill="none"/>'
    )
    p.append(
        _texto(
            ax + cerca * d + 20, ay - ah / 2 - 30, f"2 × Ø{taladro:.1f}", 10, COTA, "start", "bold"
        )
    )
    p.append(
        _texto(
            ax + cerca * d + 20,
            ay - ah / 2 - 20,
            "#cota.varilla_taladro_diametro",
            7.5,
            AUX,
            "start",
        )
    )

    # ---- seccion B-B ----------------------------------------------------
    s = 4.0
    sx, sy = 470.0, 300.0
    p.append(_texto(sx, sy - 44, "SECCIÓN B-B · escala 4:1", 9, TINTA, "start"))
    p.append(
        f'<rect x="{sx}" y="{sy - espesor * s / 2:.1f}" width="{ancho * s:.1f}" '
        f'height="{espesor * s:.1f}" fill="{AUX}" fill-opacity="0.18" stroke="{TINTA}" '
        f'stroke-width="1.4"/>'
    )
    p.append(_cota_h(sx, sx + ancho * s, sy + 42, f"{ancho:.0f}", "#cota.varilla_ancho"))
    p.append(
        _cota_v(
            sy - espesor * s / 2,
            sy + espesor * s / 2,
            sx - 30,
            f"{espesor:.0f}",
            "#cota.varilla_espesor",
        )
    )
    p.append(
        f'<path d="M{sx + 8:.1f} {sy - espesor * s / 2 + 5:.1f}h{ancho * s - 16:.1f}" '
        f'stroke="{TINTA}" stroke-width="0.8"/>'
    )
    p.append(_texto(sx + ancho * s / 2, sy - espesor * s / 2 - 8, "veta a lo largo", 8, AUX))

    # ---- aviso y cajetin -------------------------------------------------
    p.append(
        '<rect x="34" y="372" width="692" height="30" rx="4" fill="#fff4e5" stroke="#d98324" '
        'stroke-width="1"/>'
    )
    p.append(
        _texto(
            46,
            391,
            "NO ES PLANTILLA DE CORTE. Las vistas van a escalas distintas y "
            "rotuladas. La plantilla 1:1 con cuadro de calibración llega en R4.",
            9.5,
            "#8a5200",
            "start",
            "bold",
        )
    )

    p.append(
        f'<rect x="34" y="420" width="692" height="104" fill="none" stroke="{TINTA}" '
        f'stroke-width="1.2"/>'
    )
    campos = [
        ("Número", "1.1"),
        ("Pieza", "Varilla del péndulo"),
        ("Material", "Listón de madera"),
        ("Espesor", f"{espesor:.0f} mm"),
        ("Cantidad", "1"),
        ("Veta", "A lo largo"),
        ("Conjunto", "Péndulo · tanda 1"),
        ("Estado", "PENDIENTE · lo mide R1"),
    ]
    for i, (k, v) in enumerate(campos):
        cx = 34 + (i % 4) * 173
        cy = 420 + (i // 4) * 52
        p.append(
            f'<path d="M{cx} {cy}h173v52h-173z" fill="none" stroke="{AUX}" stroke-width="0.6"/>'
        )
        p.append(_texto(cx + 10, cy + 18, k.upper(), 7.5, AUX, "start"))
        p.append(_texto(cx + 10, cy + 37, v, 11, TINTA, "start", "bold"))
    p.append("</svg>")
    return "\n".join(p)


PIEZAS = {"varilla": varilla}


def main(argv: list[str] | None = None) -> int:
    partes = argparse.ArgumentParser(prog="boceto_reloj", description=__doc__)
    partes.add_argument("--pieza", default="varilla", choices=sorted(PIEZAS))
    partes.add_argument("--contratos", type=Path, default=RELOJ)
    partes.add_argument("--out", type=Path, default=None)
    opciones = partes.parse_args(argv)

    svg = PIEZAS[opciones.pieza](cargar(opciones.contratos))
    if opciones.out is None:
        print(svg)
        return 0
    opciones.out.mkdir(parents=True, exist_ok=True)
    ruta = opciones.out / f"boceto-{opciones.pieza}.svg"
    ruta.write_text(svg, encoding="utf-8")
    print(f"escrito {ruta}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
