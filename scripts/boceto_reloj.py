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

from compile.contratos import Contratos, Valor, cargar
from scripts.exportar_variables import (
    FACTOR_ONSHAPE,
    NOMBRE_MAPA,
    TIPO_EN_ONSHAPE,
    conversion_de,
    convertir,
)

RELOJ = Path("docs/reloj/contratos.json")

TINTA = "#1a1a1a"
COTA = "#0b63c5"
AUX = "#9aa0a6"

CABEZA = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 760 {alto}"
 font-family="Helvetica, Arial, sans-serif">
<defs><marker id="f" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7"
 orient="auto-start-reverse"><path d="M0 0L10 5L0 10z" fill="{cota}"/></marker></defs>
<rect x="0" y="0" width="760" height="{alto}" fill="#ffffff"/>"""
"""El alto es de cada hoja: el ancho de 760 no, porque lo fija el rotulo de
variable mas largo y ese es el mismo en todas."""


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


def _cota_v(
    y0: float,
    y1: float,
    x: float,
    etiqueta: str,
    variable: str,
    desde: float | None = None,
    lado: str = "izq",
) -> str:
    """Cota vertical. `desde` es el borde de la pieza, para que la linea de
    referencia llegue hasta ella en vez de quedarse en el aire.

    `lado` dice a que mano de la linea se escribe. Por defecto a la izquierda,
    que es lo normal; a la derecha cuando a la izquierda ya hay algo escrito.
    El rotulo de la variable es largo y se come medio dibujo si cae del lado
    equivocado."""
    a = x - 4 if desde is None else min(x - 4, desde)
    b = x + 22 if desde is None else max(x + 6, desde)
    tx = x - 7 if lado == "izq" else x + 7
    ancla = "end" if lado == "izq" else "start"
    # Una cota corta no tiene sitio entre sus dos lineas de referencia: el
    # rotulo de la variable sale por debajo y queda subrayado por la de
    # abajo. Cuando no cabe, el bloque de texto se saca por arriba.
    if y1 - y0 >= 40:
        y_eti, y_var = (y0 + y1) / 2 + 3, (y0 + y1) / 2 + 14
    else:
        y_eti, y_var = y0 - 15, y0 - 5
    return "".join(
        [
            f'<path d="M{a:.1f} {y0:.1f}H{b:.1f}" stroke="{AUX}" stroke-width="0.6"/>',
            f'<path d="M{a:.1f} {y1:.1f}H{b:.1f}" stroke="{AUX}" stroke-width="0.6"/>',
            f'<path d="M{x:.1f} {y0:.1f}V{y1:.1f}" stroke="{COTA}" stroke-width="1" '
            f'marker-start="url(#f)" marker-end="url(#f)"/>',
            _texto(tx, y_eti, etiqueta, 10, COTA, ancla=ancla, peso="bold"),
            _texto(tx, y_var, variable, 7.5, AUX, ancla=ancla),
        ]
    )


def varilla(c: Contratos) -> str:
    """La pieza 1.1: la primera que se corta, y la raiz de la cadena causal."""
    largo = c.valor("pendulo", "varilla_largo").en_mm
    ancho = c.valor("pendulo", "varilla_ancho").en_mm
    espesor = c.valor("pendulo", "varilla_espesor").en_mm
    vastago_d = c.valor("pendulo", "varilla_vastago_diametro").en_mm
    vastago_p = c.valor("pendulo", "varilla_vastago_profundidad").en_mm
    taladro = c.valor("pendulo", "varilla_taladro_diametro").en_mm
    cerca = c.valor("pendulo", "varilla_taladro_cerca").en_mm
    lejos = c.valor("pendulo", "varilla_taladro_lejos").en_mm
    nominal = c.valor("oscilador", "longitud_pendulo_nominal").en_mm
    flexion = c.valor("suspension", "muelle_flexion_a_varilla").en_mm
    # Lo que la varilla no cuenta: de su extremo de abajo al centro de masas
    # de la lenteja. Es la cadena entera y tiene que cerrar en el rotulo.
    al_centro = nominal - flexion - largo

    p: list[str] = [CABEZA.format(cota=COTA, alto=560)]
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
    # taladro del vastago, oculto: entra por el extremo de abajo
    p.append(
        f'<rect x="{x2 - vastago_p * e:.1f}" y="{yc - vastago_d * e / 2:.1f}" '
        f'width="{vastago_p * e:.1f}" height="{vastago_d * e:.1f}" fill="none" '
        f'stroke="{TINTA}" stroke-width="0.9" stroke-dasharray="4 2"/>'
    )
    p.append(_cota_h(x0, x2, yc + 46, f"{largo:.0f}", "#cota.varilla_largo"))
    p.append(
        _cota_h(
            x2 - vastago_p * e,
            x2,
            yc - 34,
            f"{vastago_p:.0f}",
            "#cota.varilla_vastago_profundidad",
        )
    )
    p.append(
        _texto(x2 + 8, yc - 40, f"\u00d8{vastago_d:.1f} para el v\u00e1stago M6", 8, AUX, "start")
    )
    p.append(_texto(x2 + 8, yc - 29, "#cota.varilla_vastago_diametro", 7.5, AUX, "start"))
    p.append(_texto(x0, yc + 78, "VISTA PRINCIPAL · escala 1:2 · con rotura", 9, TINTA, "start"))
    p.append(
        _texto(
            x0,
            yc + 91,
            f"{flexion:.0f} del punto de flexi\u00f3n al canto + {largo:.0f} de varilla "
            f"+ {al_centro:.0f} al centro de la lenteja = {nominal:.0f} mm de p\u00e9ndulo",
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


def lenteja(c: Contratos) -> str:
    """La pieza 1.2: disco de madera con nucleo de plomo.

    La masa no se teclea: sale de las cotas y de las densidades. Por eso el
    cajetin la lleva como derivada y no como dato.
    """
    diam = c.valor("lenteja", "lenteja_diametro").en_mm
    esp = c.valor("lenteja", "lenteja_espesor").en_mm
    cav_d = c.valor("lenteja", "lenteja_cavidad_diametro").en_mm
    cav_p = c.valor("lenteja", "lenteja_cavidad_profundidad").en_mm
    taladro = c.valor("lenteja", "lenteja_taladro_diametro").en_mm
    masa = c.valor("lenteja", "lenteja_masa").valor
    centro = c.valor("lenteja", "lenteja_centro_bajo_varilla").en_mm

    p: list[str] = [CABEZA.format(cota=COTA, alto=560)]
    p.append(_texto(34, 34, "1.2 \u00b7 LENTEJA", 15, TINTA, "start", "bold"))
    p.append(
        _texto(
            34,
            50,
            "Boceto de comprobaci\u00f3n \u00b7 cotas le\u00eddas de docs/reloj/contratos.json",
            9.5,
            AUX,
            "start",
        )
    )

    # ---- vista frontal, 1:1 ---------------------------------------------
    cx, cy = 160.0, 190.0
    p.append(_texto(cx - diam / 2, 92, "VISTA FRONTAL \u00b7 escala 1:1", 9, TINTA, "start"))
    p.append(
        f'<circle cx="{cx}" cy="{cy}" r="{diam / 2:.1f}" fill="none" stroke="{TINTA}" '
        f'stroke-width="1.4"/>'
    )
    p.append(
        f'<circle cx="{cx}" cy="{cy}" r="{cav_d / 2:.1f}" fill="{AUX}" fill-opacity="0.15" '
        f'stroke="{TINTA}" stroke-width="0.9" stroke-dasharray="5 3"/>'
    )
    p.append(
        f'<circle cx="{cx}" cy="{cy}" r="{taladro / 2:.2f}" fill="none" stroke="{TINTA}" '
        f'stroke-width="1.2"/>'
    )
    for dx, dy in ((diam / 2 + 10, 0), (0, diam / 2 + 10)):
        p.append(
            f'<path d="M{cx - dx:.1f} {cy - dy:.1f}L{cx + dx:.1f} {cy + dy:.1f}" '
            f'stroke="{AUX}" stroke-width="0.6" stroke-dasharray="8 3 2 3"/>'
        )
    p.append(
        _cota_h(
            cx - diam / 2,
            cx + diam / 2,
            cy + diam / 2 + 34,
            f"\u00d8{diam:.0f}",
            "#cota.lenteja_diametro",
        )
    )
    p.append(
        f'<path d="M{cx + 28:.1f} {cy - 28:.1f}l26 -26h56" stroke="{COTA}" stroke-width="1" '
        f'fill="none"/>'
    )
    p.append(
        _texto(cx + 58, cy - 58, f"\u00d8{cav_d:.0f} cavidad del plomo", 9.5, COTA, "start", "bold")
    )
    p.append(_texto(cx + 58, cy - 48, "#cota.lenteja_cavidad_diametro", 7.5, AUX, "start"))
    p.append(
        f'<path d="M{cx + 4:.1f} {cy + 4:.1f}l46 50h34" stroke="{COTA}" stroke-width="1" '
        f'fill="none"/>'
    )
    p.append(
        _texto(
            cx + 54,
            cy + 50,
            f"\u00d8{taladro:.1f} pasa sobre el v\u00e1stago",
            9.5,
            COTA,
            "start",
            "bold",
        )
    )
    p.append(_texto(cx + 54, cy + 61, "#cota.lenteja_taladro_diametro", 7.5, AUX, "start"))

    # ---- seccion A-A, 1:1 ------------------------------------------------
    sx, sy = 420.0, 190.0
    p.append(_texto(sx, 92, "SECCI\u00d3N A-A \u00b7 escala 1:1", 9, TINTA, "start"))
    alto = esp
    p.append(
        f'<path d="M{sx} {sy - alto / 2:.1f}h{diam:.1f}v{alto:.1f}h{-diam:.1f}z" fill="{AUX}" '
        f'fill-opacity="0.18" stroke="{TINTA}" stroke-width="1.4"/>'
    )
    cav_x = sx + (diam - cav_d) / 2
    p.append(
        f'<path d="M{cav_x:.1f} {sy - alto / 2:.1f}h{cav_d:.1f}v{cav_p:.1f}h{-cav_d:.1f}z" '
        f'fill="#ffffff" stroke="{TINTA}" stroke-width="1.2"/>'
    )
    p.append(_texto(sx + diam / 2, sy - alto / 2 + cav_p - 4, "plomo", 8, AUX))
    p.append(
        f'<path d="M{sx + diam / 2 - taladro / 2:.2f} {sy - alto / 2:.1f}v{alto:.1f}'
        f'M{sx + diam / 2 + taladro / 2:.2f} {sy - alto / 2:.1f}v{alto:.1f}" stroke="{TINTA}" '
        f'stroke-width="1.1"/>'
    )
    p.append(
        _cota_v(
            sy - alto / 2, sy + alto / 2, sx - 34, f"{esp:.0f}", "#cota.lenteja_espesor", desde=sx
        )
    )
    p.append(
        _cota_v(
            sy - alto / 2,
            sy - alto / 2 + cav_p,
            sx + diam + 72,
            f"{cav_p:.0f}",
            "#cota.lenteja_cavidad_profundidad",
            desde=sx + (diam + cav_d) / 2,
        )
    )
    p.append(
        _texto(
            sx,
            sy + 70,
            f"masa derivada de las cotas: {masa * 1000:.0f} g",
            9,
            TINTA,
            "start",
            "bold",
        )
    )
    for i, linea in enumerate(
        (
            "969 g de plomo y 63 de madera. No es una cota: sale del",
            "volumen y las densidades, y se pesa en R1",
            f"el centro va a {centro:.0f} mm bajo el extremo de la varilla,",
            "y lo mueve la tuerca de regulaci\u00f3n",
        )
    ):
        p.append(_texto(sx, sy + 83 + i * 12, linea, 8, AUX, "start"))

    p.append(
        '<rect x="34" y="372" width="692" height="30" rx="4" fill="#fff4e5" '
        'stroke="#d98324" stroke-width="1"/>'
    )
    p.append(
        _texto(
            46,
            391,
            "NO ES PLANTILLA DE CORTE. La cavidad se vac\u00eda antes de redondear el "
            "disco: redondeada ya no hay por donde amarrarla.",
            9.5,
            "#8a5200",
            "start",
            "bold",
        )
    )
    p.append(
        f'<rect x="34" y="420" width="692" height="104" fill="none" stroke="{TINTA}" '
        'stroke-width="1.2"/>'
    )
    campos = [
        ("N\u00famero", "1.2"),
        ("Pieza", "Lenteja"),
        ("Material", "Madera + plomo"),
        ("Espesor", f"{esp:.0f} mm"),
        ("Cantidad", "1"),
        ("Veta", "Indiferente"),
        ("Conjunto", "P\u00e9ndulo \u00b7 tanda 1"),
        ("Estado", "PENDIENTE \u00b7 se pesa en R1"),
    ]
    for i, (k, v) in enumerate(campos):
        bx = 34 + (i % 4) * 173
        by = 420 + (i // 4) * 52
        p.append(
            f'<path d="M{bx} {by}h173v52h-173z" fill="none" stroke="{AUX}" stroke-width="0.6"/>'
        )
        p.append(_texto(bx + 10, by + 18, k.upper(), 7.5, AUX, "start"))
        p.append(_texto(bx + 10, by + 37, v, 11, TINTA, "start", "bold"))
    p.append("</svg>")
    return "\n".join(p)


def soporte(c: Contratos) -> str:
    """La pieza 1.4: el bloque que amarra el muelle de suspension.

    Su canto de abajo es el datum del pendulo entero: de ahi empieza a contar
    el tramo libre del muelle, y a la mitad de ese tramo esta el punto de
    flexion del que cuelgan los 994 mm.
    """
    anc = c.valor("suspension", "soporte_ancho").en_mm
    alt = c.valor("suspension", "soporte_alto").en_mm
    esp = c.valor("suspension", "soporte_espesor").en_mm
    placa = c.valor("suspension", "soporte_placa_espesor").en_mm
    tor = c.valor("suspension", "soporte_tornillo_diametro").en_mm
    sep = c.valor("suspension", "soporte_tornillo_separacion").en_mm
    canto = c.valor("suspension", "soporte_tornillo_al_canto").en_mm
    libre = c.valor("suspension", "muelle_largo_libre").en_mm
    flexion = c.valor("suspension", "muelle_flexion_a_varilla").en_mm
    mu_anc = c.valor("suspension", "muelle_ancho").en_mm
    va_esp = c.valor("pendulo", "varilla_espesor").en_mm

    e = 2.0
    p: list[str] = [CABEZA.format(cota=COTA, alto=560)]
    p.append(_texto(34, 34, "1.4 \u00b7 SOPORTE DE SUSPENSI\u00d3N", 15, TINTA, "start", "bold"))
    p.append(
        _texto(
            34,
            50,
            "Boceto de comprobaci\u00f3n \u00b7 cotas le\u00eddas de docs/reloj/contratos.json",
            9.5,
            AUX,
            "start",
        )
    )

    # ---- vista frontal ---------------------------------------------------
    # Los rotulos de variable son largos (#cota.soporte_tornillo_separacion
    # son 33 caracteres) y mandan sobre la colocacion mas que la pieza.
    x0, y0 = 150.0, 140.0
    w, h = anc * e, alt * e
    p.append(_texto(x0 - 56, 92, "VISTA FRONTAL \u00b7 escala 2:1", 9, TINTA, "start"))
    cxm = x0 + w / 2
    yt = y0 + h - canto * e
    p.append(
        f'<rect x="{cxm - mu_anc * e / 2:.1f}" y="{y0 + 12:.1f}" width="{mu_anc * e:.1f}" '
        f'height="{h - 12 + 16:.1f}" fill="{COTA}" fill-opacity="0.12" stroke="{COTA}" '
        f'stroke-width="0.9" stroke-dasharray="4 2"/>'
    )
    p.append(
        f'<rect x="{x0}" y="{y0}" width="{w:.1f}" height="{h:.1f}" fill="none" '
        f'stroke="{TINTA}" stroke-width="1.4"/>'
    )
    for dx in (-sep * e / 2, sep * e / 2):
        p.append(
            f'<circle cx="{cxm + dx:.1f}" cy="{yt:.1f}" r="{tor * e / 2:.2f}" fill="none" '
            f'stroke="{TINTA}" stroke-width="1.2"/>'
        )
    p.append(_texto(cxm, y0 + h + 32, "el muelle, detr\u00e1s", 8, COTA))
    p.append(_cota_h(x0, x0 + w, y0 + h + 62, f"{anc:.0f}", "#cota.soporte_ancho"))
    p.append(
        _cota_h(
            cxm - sep * e / 2,
            cxm + sep * e / 2,
            y0 - 22,
            f"{sep:.0f}",
            "#cota.soporte_tornillo_separacion",
        )
    )
    p.append(_cota_v(y0, y0 + h, x0 - 30, f"{alt:.0f}", "#cota.soporte_alto", desde=x0))
    p.append(
        _cota_v(
            yt,
            y0 + h,
            x0 + w + 26,
            f"{canto:.0f}",
            "#cota.soporte_tornillo_al_canto",
            desde=x0 + w,
            lado="der",
        )
    )
    xd, yd = cxm + sep * e / 2, yt - 4
    p.append(
        f'<path d="M{xd:.1f} {yd:.1f}l20 -44h20" stroke="{COTA}" stroke-width="1" fill="none"/>'
    )
    p.append(_texto(xd + 44, yd - 48, f"2 \u00d7 \u00d8{tor:.1f}", 9.5, COTA, "start", "bold"))
    p.append(_texto(xd + 44, yd - 38, "#cota.soporte_tornillo_diametro", 7.5, AUX, "start"))

    # ---- vista lateral, el montaje --------------------------------------
    sx = 470.0
    p.append(
        _texto(sx - 90, 92, "VISTA LATERAL \u00b7 el montaje \u00b7 escala 2:1", 9, TINTA, "start")
    )
    p.append(
        f'<rect x="{sx}" y="{y0}" width="{esp * e:.1f}" height="{h:.1f}" fill="{AUX}" '
        f'fill-opacity="0.18" stroke="{TINTA}" stroke-width="1.4"/>'
    )
    xm = sx + esp * e
    p.append(
        f'<rect x="{xm + 2:.1f}" y="{y0}" width="{placa * e:.1f}" height="{h:.1f}" fill="{AUX}" '
        f'fill-opacity="0.18" stroke="{TINTA}" stroke-width="1.4"/>'
    )
    p.append(_texto(sx - 8, y0 + 14, "bloque", 8, AUX, "end"))
    p.append(_texto(xm + placa * e + 14, y0 + 12, "placa", 8, AUX, "start"))
    yc_canto = y0 + h
    yf = yc_canto + flexion * e
    ylib = yc_canto + libre * e
    p.append(f'<path d="M{xm:.1f} {y0:.1f}V{ylib + 44:.1f}" stroke="{COTA}" stroke-width="2"/>')
    p.append(
        f'<rect x="{xm - va_esp * e / 2:.1f}" y="{ylib:.1f}" width="{va_esp * e:.1f}" '
        f'height="44" fill="none" stroke="{TINTA}" stroke-width="1.4"/>'
    )
    p.append(_texto(xm + 26, ylib + 30, "varilla", 8, AUX, "start"))
    p.append(
        f'<path d="M{xm - 120:.1f} {yf:.1f}H{xm + 40:.1f}" stroke="{COTA}" stroke-width="1" '
        f'stroke-dasharray="6 3"/>'
    )
    p.append(
        f'<path d="M{xm - 120:.1f} {yf:.1f}V{ylib + 52:.1f}" stroke="{COTA}" stroke-width="1" '
        f'stroke-dasharray="6 3"/>'
    )
    p.append(
        _texto(
            xm - 120,
            ylib + 66,
            "PUNTO DE FLEXI\u00d3N \u00b7 de aqu\u00ed cuelgan los 994",
            9,
            COTA,
            "start",
            "bold",
        )
    )
    p.append(
        _cota_v(yc_canto, yf, sx - 42, f"{flexion:.0f}", "#cota.muelle_flexion_a_varilla", desde=sx)
    )
    p.append(
        _cota_v(
            yc_canto,
            ylib,
            xm + 50,
            f"{libre:.0f}",
            "#cota.muelle_largo_libre",
            desde=xm,
            lado="der",
        )
    )
    # El espesor se ve a lo ancho en esta vista: acotarlo en vertical era
    # medir el alto del bloque por segunda vez y con el numero equivocado.
    p.append(
        _cota_h(
            sx,
            xm + 2 + placa * e,
            y0 - 22,
            f"{esp:.0f} + {placa:.0f}",
            "#cota.soporte_espesor",
        )
    )

    p.append(
        '<rect x="34" y="384" width="692" height="30" rx="4" fill="#fff4e5" '
        'stroke="#d98324" stroke-width="1"/>'
    )
    p.append(
        _texto(
            46,
            403,
            "EL CANTO DE ABAJO DEL BLOQUE ES EL DATUM DEL P\u00c9NDULO. Si se monta "
            "1 mm m\u00e1s arriba, el reloj atrasa 43 s al d\u00eda.",
            9.5,
            "#8a5200",
            "start",
            "bold",
        )
    )
    p.append(
        f'<rect x="34" y="432" width="692" height="104" fill="none" stroke="{TINTA}" '
        'stroke-width="1.2"/>'
    )
    campos = [
        ("N\u00famero", "1.4"),
        ("Pieza", "Soporte de suspensi\u00f3n"),
        ("Material", "Madera dura"),
        ("Espesor", f"{esp:.0f} + {placa:.0f} mm"),
        ("Cantidad", "1 bloque + 1 placa"),
        ("Veta", "A lo ancho"),
        ("Conjunto", "P\u00e9ndulo \u00b7 tanda 1"),
        ("Estado", "PENDIENTE \u00b7 sin anclaje"),
    ]
    for i, (k, v) in enumerate(campos):
        bx = 34 + (i % 4) * 173
        by = 432 + (i // 4) * 52
        p.append(
            f'<path d="M{bx} {by}h173v52h-173z" fill="none" stroke="{AUX}" stroke-width="0.6"/>'
        )
        p.append(_texto(bx + 10, by + 18, k.upper(), 7.5, AUX, "start"))
        p.append(_texto(bx + 10, by + 37, v, 11, TINTA, "start", "bold"))
    p.append("</svg>")
    return "\n".join(p)


PIEZAS = {"varilla": varilla, "lenteja": lenteja, "soporte": soporte}

PREFIJOS = {
    "varilla": ("varilla_",),
    "lenteja": ("lenteja_",),
    "vastago": ("vastago_",),
    "soporte": ("soporte_",),
    "muelle": ("muelle_",),
}
"""Que cotas son de cada pieza. El prefijo del nombre decide, igual que
decide el gemelo de radio: asi se puede leer el contrato y saber de quien es
cada cota sin conocer el conjunto."""

INTERFACES = {
    "varilla": (
        "vastago_diametro",
        "longitud_pendulo_nominal",
        "muelle_flexion_a_varilla",
        "muelle_largo",
    ),
    "soporte": ("muelle_ancho", "muelle_espesor", "muelle_largo_libre"),
    "muelle": (
        "soporte_tornillo_al_canto",
        "varilla_ancho",
        "varilla_taladro_cerca",
        "varilla_taladro_lejos",
    ),
    "lenteja": ("vastago_diametro", "vastago_saliente", "longitud_pendulo_nominal"),
    "vastago": ("varilla_vastago_diametro", "varilla_vastago_profundidad"),
}
"""Cotas de OTRA pieza que esta toca. Van en la tabla aparte y rotuladas,
porque cambiarlas desde aqui rompe la pieza de al lado: una cota de junta
nombrada por un solo lado invita a cambiarla en un solo sitio."""


def _fila(valor: Valor) -> tuple[str, str, str, str, str]:
    """Una fila de la tabla, con la variable que le toca en Onshape.

    El tipo lo decide la misma tabla de conversion que escribe los CSV, para
    que la tabla no pueda prometer una variable que el Variable Studio no
    tiene: una masa no entra en el CAD, y aqui tiene que decirlo.
    """
    conversion = conversion_de(valor)
    cifra = f"{valor.valor * conversion.factor:g}"
    mapa = NOMBRE_MAPA.get(conversion.tipo)
    variable = f"`#{mapa}.{valor.nombre}`" if mapa else "**no entra en el CAD**"
    return (
        valor.nombre,
        f"{cifra} {conversion.simbolo}".strip(),
        variable,
        valor.tolerancia or "—",
        valor.descripcion,
    )


def tabla_de_cotas(c: Contratos, pieza: str) -> str:
    """La tabla de la pieza, en markdown, leida del contrato.

    No se teclea por la misma razon que no se teclea el boceto: una tabla
    escrita a mano se queda atras en cuanto el contrato cambia, y nadie se
    entera porque sigue pareciendo correcta.
    """
    propias: list[tuple[str, str, str, str, str]] = []
    vecinas: list[tuple[str, str, str, str, str]] = []
    for contrato in c.contratos:
        for valor in contrato.valores:
            if valor.nombre.startswith(PREFIJOS[pieza]):
                propias.append(_fila(valor))
            elif valor.nombre in INTERFACES[pieza]:
                vecinas.append(_fila(valor))

    lineas = [f"### Cotas de la pieza `{pieza}`", ""]
    lineas.append("| Cota | Valor | Variable | Tolerancia | De donde sale |")
    lineas.append("| --- | --- | --- | --- | --- |")
    for n, v, var, tol, desc in propias:
        lineas.append(f"| `{n}` | {v} | {var} | {tol} | {desc} |")
    if vecinas:
        lineas += [
            "",
            "**Cotas de interfaz**, de otras piezas que esta toca. Cambiarlas",
            "desde aqui rompe la pieza de al lado.",
            "",
            "| Cota | Valor | Variable | De donde sale |",
            "| --- | --- | --- | --- |",
        ]
        for n, v, var, _tol, desc in vecinas:
            lineas.append(f"| `{n}` | {v} | {var} | {desc} |")
    return "\n".join(lineas) + "\n"


def tabla_de_variables(c: Contratos, pieza: str) -> str:
    """Como se escribe cada cota de la pieza dentro del CAD.

    La tabla de cotas dice **que** mide la pieza; esta dice **de donde sale
    el numero** en Onshape: en que mapa esta, con que tipo se importo y con
    que factor de conversion. Son dos preguntas distintas y se hacen en dos
    momentos distintos: la primera al acotar el boceto, la segunda cuando una
    cota sale mal y hay que averiguar si el error esta en el contrato o en la
    importacion.

    El factor va por variable, no por tabla, y por eso hay un CSV por tipo:
    una sola importacion no puede dar milimetros a unas y grados a otras.
    """
    filas: list[tuple[str, str, str, str, str, str]] = []
    for contrato in c.contratos:
        for valor in contrato.valores:
            if not (valor.nombre.startswith(PREFIJOS[pieza]) or valor.nombre in INTERFACES[pieza]):
                continue
            cifra, conversion = convertir(valor)
            if not conversion.tipo.dimensiona:
                # Una REFERENCIA -segundos, kilos, newtons- no acota nada y
                # no sube al Variable Studio. Que aparezca aqui seria invitar
                # a usarla en un boceto.
                continue
            mapa = NOMBRE_MAPA[conversion.tipo]
            limpia = cifra.rstrip("0").rstrip(".") if "." in cifra else cifra
            filas.append(
                (
                    valor.nombre,
                    f"reloj_{mapa}.csv",
                    TIPO_EN_ONSHAPE[conversion.tipo],
                    FACTOR_ONSHAPE[conversion.tipo],
                    f"#{mapa}.{valor.nombre}",
                    f"{limpia} {conversion.simbolo}".strip(),
                )
            )

    lineas = [
        f"### Variables de Onshape de la pieza `{pieza}`",
        "",
        "Las cuatro primeras columnas son lo que hay configurado en el",
        "Variable Studio; la quinta es lo que se teclea al acotar.",
        "",
        "| Cota | CSV | Tipo de variable | Factor de conversion | Se escribe | Vale |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for nombre, csv_, tipo, factor, escribe, vale in filas:
        lineas.append(f"| `{nombre}` | `{csv_}` | {tipo} | `{factor}` | `{escribe}` | {vale} |")
    usados = ", ".join(f"`{u}`" for u in sorted({f[1] for f in filas}))
    cuantos = len({f[1] for f in filas})
    lineas += [
        "",
        f"**{len(filas)} variables**, en {cuantos} mapa(s): {usados}.",
        "Cada mapa es **una** variable importada con fila «Todos los valores»,",
        "tipo de resultado «Mapa» y la columna 0 como clave.",
    ]
    return "\n".join(lineas) + "\n"


def main(argv: list[str] | None = None) -> int:
    partes = argparse.ArgumentParser(prog="boceto_reloj", description=__doc__)
    partes.add_argument("--pieza", default="varilla", choices=sorted(PREFIJOS))
    partes.add_argument("--tabla", action="store_true", help="la tabla de cotas, en markdown")
    partes.add_argument(
        "--variables",
        action="store_true",
        help="la tabla de variables de Onshape de la pieza, en markdown",
    )
    partes.add_argument("--contratos", type=Path, default=RELOJ)
    partes.add_argument("--out", type=Path, default=None)
    opciones = partes.parse_args(argv)

    contratos = cargar(opciones.contratos)
    if opciones.variables:
        texto, sufijo = tabla_de_variables(contratos, opciones.pieza), "variables.md"
    elif opciones.tabla:
        texto, sufijo = tabla_de_cotas(contratos, opciones.pieza), "cotas.md"
    else:
        if opciones.pieza not in PIEZAS:
            print(f"no hay boceto de '{opciones.pieza}' todavia", file=sys.stderr)
            return 2
        texto, sufijo = PIEZAS[opciones.pieza](contratos), "boceto.svg"
    if opciones.out is None:
        print(texto)
        return 0
    opciones.out.mkdir(parents=True, exist_ok=True)
    nombre = f"{sufijo.split('.')[0]}-{opciones.pieza}.{sufijo.split('.')[1]}"
    ruta = opciones.out / nombre
    ruta.write_text(texto, encoding="utf-8")
    print(f"escrito {ruta}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
