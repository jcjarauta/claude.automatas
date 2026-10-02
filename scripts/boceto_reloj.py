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
import math
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

CABEZA = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {ancho} {alto}"
 font-family="Helvetica, Arial, sans-serif">
<defs><marker id="f" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7"
 orient="auto-start-reverse"><path d="M0 0L10 5L0 10z" fill="{cota}"/></marker></defs>
<rect x="0" y="0" width="{ancho}" height="{alto}" fill="#ffffff"/>"""
"""Cada hoja declara su tamano. Lo que lo fija no es la pieza -el soporte cabe
en una tarjeta- sino cuantas vistas hay y lo largo que es el rotulo de
variable mas largo, que ronda los ciento veinte pixeles."""


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


def _cota_h(
    x0: float, x1: float, y: float, etiqueta: str, variable: str, fuera: bool = False
) -> str:
    """Cota horizontal con sus lineas de referencia.

    `fuera` saca el bloque de texto por la izquierda, para una cota corta: el
    rotulo de la variable mide mas de cien pixeles y una cota de seis
    milimetros no tiene donde ponerlo entre sus dos flechas."""
    if fuera:
        tx, ancla = x0 - 6, "end"
    else:
        tx, ancla = (x0 + x1) / 2, "middle"
    return "".join(
        [
            f'<path d="M{x0:.1f} {y - 22:.1f}V{y + 4:.1f}" stroke="{AUX}" stroke-width="0.6"/>',
            f'<path d="M{x1:.1f} {y - 22:.1f}V{y + 4:.1f}" stroke="{AUX}" stroke-width="0.6"/>',
            f'<path d="M{x0:.1f} {y:.1f}H{x1:.1f}" stroke="{COTA}" stroke-width="1" '
            f'marker-start="url(#f)" marker-end="url(#f)"/>',
            _texto(tx, y - 5, etiqueta, 10, COTA, ancla=ancla, peso="bold"),
            _texto(tx, y + 13, variable, 7.5, AUX, ancla=ancla),
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

    p: list[str] = [CABEZA.format(cota=COTA, ancho=760, alto=560)]
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

    p: list[str] = [CABEZA.format(cota=COTA, ancho=760, alto=560)]
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

    Tres vistas y no dos: el bloque, la placa de apriete -que es otra pieza,
    aunque se taladre con el- y el montaje. La placa en la vista frontal del
    bloque no se ve, y era justo donde faltaban cotas.
    """
    anc = c.valor("suspension", "soporte_ancho").en_mm
    alt = c.valor("suspension", "soporte_alto").en_mm
    esp = c.valor("suspension", "soporte_espesor").en_mm
    placa = c.valor("suspension", "soporte_placa_espesor").en_mm
    placa_anc = c.valor("suspension", "soporte_placa_ancho").en_mm
    placa_alt = c.valor("suspension", "soporte_placa_alto").en_mm
    tor = c.valor("suspension", "soporte_tornillo_diametro").en_mm
    sep = c.valor("suspension", "soporte_tornillo_separacion").en_mm
    canto = c.valor("suspension", "soporte_tornillo_al_canto").en_mm
    lado = c.valor("suspension", "soporte_tornillo_al_lado").en_mm
    al_datum = c.valor("anclaje", "anclaje_al_datum").en_mm
    libre = c.valor("suspension", "muelle_largo_libre").en_mm
    flexion = c.valor("suspension", "muelle_flexion_a_varilla").en_mm
    mu_anc = c.valor("suspension", "muelle_ancho").en_mm
    va_esp = c.valor("pendulo", "varilla_espesor").en_mm

    e = 2.0
    p: list[str] = [CABEZA.format(cota=COTA, ancho=1200, alto=570)]
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

    def taladros(cx: float, y: float) -> list[str]:
        return [
            f'<circle cx="{cx + dx:.1f}" cy="{y:.1f}" r="{tor * e / 2:.2f}" fill="none" '
            f'stroke="{TINTA}" stroke-width="1.2"/>'
            for dx in (-sep * e / 2, sep * e / 2)
        ]

    # ---- vista 1, el bloque ---------------------------------------------
    # El muelle no se dibuja aqui: en la frontal queda detras y lo unico que
    # hacia era tapar el sitio donde van las cotas de los taladros.
    x0, y0 = 150.0, 140.0
    w, h = anc * e, alt * e
    cxm, yt = x0 + w / 2, y0 + h - canto * e
    p.append(
        _texto(x0 - 56, 92, "EL BLOQUE \u00b7 vista frontal \u00b7 escala 2:1", 9, TINTA, "start")
    )
    # La razon de que la separacion sea 24 con un fleje de 12 no se ve en el
    # dibujo, porque el fleje queda detras: va escrita.
    p.append(
        _texto(
            x0 - 56,
            105,
            f"el fleje de {mu_anc:.0f} pasa entre los dos tornillos",
            8,
            AUX,
            "start",
        )
    )
    p.append(
        f'<rect x="{x0}" y="{y0}" width="{w:.1f}" height="{h:.1f}" fill="none" '
        f'stroke="{TINTA}" stroke-width="1.4"/>'
    )
    p += taladros(cxm, yt)
    # Los dos de arriba son los que amarran el bloque al bastidor. Misma
    # broca, misma separacion y misma linea vertical que los de abajo: una
    # plantilla de taladrado y no dos.
    y_anclaje = y0 + h - al_datum * e
    p += taladros(cxm, y_anclaje)
    p.append(
        _cota_h(
            cxm - sep * e / 2,
            cxm + sep * e / 2,
            y0 - 22,
            f"{sep:.0f}",
            "#cota.soporte_tornillo_separacion",
        )
    )
    p.append(
        _cota_v(
            y_anclaje,
            y0 + h,
            x0 + w + 158,
            f"{al_datum:.0f}",
            "#cota.anclaje_al_datum",
            desde=x0 + w,
            lado="der",
        )
    )
    p.append(_texto(x0 + w + 10, y_anclaje + 18, "AL BASTIDOR", 8.5, COTA, "start", "bold"))
    p.append(
        _cota_h(
            x0,
            cxm - sep * e / 2,
            y0 + h + 30,
            f"{lado:.0f}",
            "#cota.soporte_tornillo_al_lado",
            fuera=True,
        )
    )
    p.append(_cota_h(x0, x0 + w, y0 + h + 62, f"{anc:.0f}", "#cota.soporte_ancho"))
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
    xd, yd = cxm + sep * e / 2, y_anclaje - 4
    p.append(
        f'<path d="M{xd:.1f} {yd:.1f}l26 -26h34" stroke="{COTA}" stroke-width="1" fill="none"/>'
    )
    p.append(_texto(xd + 64, yd - 30, f"4 \u00d7 \u00d8{tor:.1f}", 9.5, COTA, "start", "bold"))
    p.append(_texto(xd + 64, yd - 20, "#cota.soporte_tornillo_diametro", 7.5, AUX, "start"))

    # ---- vista 2, la placa de apriete ------------------------------------
    px, pw, ph = 520.0, placa_anc * e, placa_alt * e
    py = y0 + h - ph  # al ras del canto de apriete, que es el datum
    pcx = px + pw / 2
    p.append(_texto(px, 92, "LA PLACA \u00b7 escala 2:1", 9, TINTA, "start"))
    p.append(_texto(px, 105, "se taladra con el bloque", 8, AUX, "start"))
    p.append(
        f'<rect x="{px}" y="{py:.1f}" width="{pw:.1f}" height="{ph:.1f}" fill="{AUX}" '
        f'fill-opacity="0.12" stroke="{TINTA}" stroke-width="1.4"/>'
    )
    p += taladros(pcx, y0 + h - canto * e)
    p.append(_cota_h(px, px + pw, y0 + h + 62, f"{placa_anc:.0f}", "#cota.soporte_placa_ancho"))
    p.append(
        _cota_v(
            py,
            y0 + h,
            px + pw + 26,
            f"{placa_alt:.0f}",
            "#cota.soporte_placa_alto",
            desde=px + pw,
            lado="der",
        )
    )

    # ---- vista 3, el montaje --------------------------------------------
    sx = 860.0
    p.append(
        _texto(sx - 60, 92, "EL MONTAJE \u00b7 vista lateral \u00b7 escala 2:1", 9, TINTA, "start")
    )
    p.append(
        f'<rect x="{sx}" y="{y0}" width="{esp * e:.1f}" height="{h:.1f}" fill="{AUX}" '
        f'fill-opacity="0.18" stroke="{TINTA}" stroke-width="1.4"/>'
    )
    xm = sx + esp * e
    p.append(
        f'<rect x="{xm + 2:.1f}" y="{py:.1f}" width="{placa * e:.1f}" height="{ph:.1f}" '
        f'fill="{AUX}" fill-opacity="0.18" stroke="{TINTA}" stroke-width="1.4"/>'
    )
    p.append(_texto(sx - 8, y0 + 16, "bloque", 8, AUX, "end"))
    p.append(_texto(xm + placa * e + 14, py + 14, "placa", 8, AUX, "start"))
    p.append(
        _cota_h(
            sx,
            xm + 2 + placa * e,
            y0 - 22,
            f"{esp:.0f} + {placa:.0f}",
            "#cota.soporte_espesor",
        )
    )
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
        _cota_v(
            yc_canto,
            yf,
            xm + 50,
            f"{flexion:.0f}",
            "#cota.muelle_flexion_a_varilla",
            desde=xm,
            lado="der",
        )
    )
    p.append(
        _cota_v(
            yc_canto,
            ylib,
            xm + 150,
            f"{libre:.0f}",
            "#cota.muelle_largo_libre",
            desde=xm,
            lado="der",
        )
    )

    ancho_hoja = 1200 - 68
    p.append(
        f'<rect x="34" y="390" width="{ancho_hoja}" height="30" rx="4" fill="#fff4e5" '
        'stroke="#d98324" stroke-width="1"/>'
    )
    p.append(
        _texto(
            46,
            409,
            "EL CANTO DE ABAJO DEL BLOQUE ES EL DATUM DEL P\u00c9NDULO. Si se monta "
            "1 mm m\u00e1s arriba, el reloj atrasa 43 s al d\u00eda.",
            9.5,
            "#8a5200",
            "start",
            "bold",
        )
    )
    p.append(
        f'<rect x="34" y="438" width="{ancho_hoja}" height="104" fill="none" stroke="{TINTA}" '
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
        ("Estado", "Anclaje congelado"),
    ]
    celda = ancho_hoja / 4
    for i, (k, v) in enumerate(campos):
        bx = 34 + (i % 4) * celda
        by = 438 + (i // 4) * 52
        p.append(
            f'<path d="M{bx:.1f} {by}h{celda:.1f}v52h-{celda:.1f}z" fill="none" '
            f'stroke="{AUX}" stroke-width="0.6"/>'
        )
        p.append(_texto(bx + 10, by + 18, k.upper(), 7.5, AUX, "start"))
        p.append(_texto(bx + 10, by + 37, v, 11, TINTA, "start", "bold"))
    p.append("</svg>")
    return "\n".join(p)


def muelle(c: Contratos) -> str:
    """La pieza 1.3: el fleje de suspension.

    La unica de la tanda que no es de madera, y la unica cuyo dibujo manda
    sobre donde NO se puede taladrar. El fleje se rompe por donde flexa, asi
    que sus dos agujeros tienen que caer enteros en el tramo que solo tira.
    """
    v = c.contrato("suspension")
    largo = v.valor("muelle_largo").en_mm
    ancho = v.valor("muelle_ancho").en_mm
    espesor = v.valor("muelle_espesor").en_mm
    empotrado = v.valor("muelle_empotrado").en_mm
    libre = v.valor("muelle_largo_libre").en_mm
    solape = v.valor("muelle_solape").en_mm
    flexion = v.valor("muelle_flexion_a_varilla").en_mm
    taladro = v.valor("muelle_taladro_diametro").en_mm
    cerca = v.valor("muelle_taladro_cerca").en_mm
    lejos = v.valor("muelle_taladro_lejos").en_mm

    e = 2.0
    p: list[str] = [CABEZA.format(cota=COTA, ancho=760, alto=680)]
    p.append(_texto(34, 34, "1.3 \u00b7 FLEJE DE SUSPENSI\u00d3N", 15, TINTA, "start", "bold"))
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

    x0, y0 = 200.0, 140.0
    w, h = ancho * e, largo * e
    cx = x0 + w / 2
    y_empotrado = y0 + empotrado * e
    y_libre = y_empotrado + libre * e
    p.append(_texto(x0 - 56, 92, "EL FLEJE \u00b7 escala 2:1", 9, TINTA, "start"))
    p.append(
        _texto(x0 - 56, 105, f"espesor {espesor:.1f} \u00b7 #cota.muelle_espesor", 8, AUX, "start")
    )

    # Las tres zonas, sombreadas: lo que hace util este dibujo no es el
    # contorno -es una tira- sino donde empieza y acaba cada tramo.
    for y_ini, y_fin, relleno in (
        (y0, y_empotrado, 0.18),
        (y_empotrado, y_libre, 0.0),
        (y_libre, y0 + h, 0.18),
    ):
        p.append(
            f'<rect x="{x0}" y="{y_ini:.1f}" width="{w:.1f}" height="{y_fin - y_ini:.1f}" '
            f'fill="{AUX}" fill-opacity="{relleno}" stroke="none"/>'
        )
    p.append(
        f'<rect x="{x0}" y="{y0}" width="{w:.1f}" height="{h:.1f}" fill="none" '
        f'stroke="{TINTA}" stroke-width="1.4"/>'
    )
    for y_corte in (y_empotrado, y_libre):
        p.append(
            f'<path d="M{x0:.1f} {y_corte:.1f}H{x0 + w:.1f}" stroke="{AUX}" stroke-width="0.8" '
            f'stroke-dasharray="4 2"/>'
        )
    for y_taladro in (y0 + cerca * e, y0 + lejos * e):
        p.append(
            f'<circle cx="{cx:.1f}" cy="{y_taladro:.1f}" r="{taladro * e / 2:.2f}" fill="none" '
            f'stroke="{TINTA}" stroke-width="1.2"/>'
        )

    p.append(_texto(x0 + w + 8, y0 + 22, "dentro del soporte", 8, AUX, "start"))
    p.append(
        _texto(
            x0 + w + 8,
            y_libre - 5,
            "FLEXA \u00b7 aqu\u00ed no se taladra",
            8.5,
            COTA,
            "start",
            "bold",
        )
    )
    p.append(_texto(x0 + w + 8, y_libre + 52, "sobre la varilla", 8, AUX, "start"))

    # El punto de flexion, que es de donde cuelgan los 994 y no esta en
    # ningun canto de ninguna pieza.
    y_flexion = y_empotrado + flexion * e
    p.append(
        f'<path d="M{x0 - 4:.1f} {y_flexion:.1f}H{x0 + w + 6:.1f}" stroke="{COTA}" '
        f'stroke-width="1" stroke-dasharray="6 3"/>'
    )
    p.append(_texto(x0 + w + 8, y_flexion + 3, "punto de flexi\u00f3n", 8.5, COTA, "start", "bold"))

    p.append(_cota_v(y0, y_empotrado, 170, f"{empotrado:.0f}", "#cota.muelle_empotrado", desde=x0))
    p.append(
        _cota_v(y_empotrado, y_libre, 170, f"{libre:.0f}", "#cota.muelle_largo_libre", desde=x0)
    )
    p.append(_cota_v(y_libre, y0 + h, 170, f"{solape:.0f}", "#cota.muelle_solape", desde=x0))
    p.append(
        _cota_v(
            y0,
            y0 + cerca * e,
            x0 + w + 106,
            f"{cerca:.0f}",
            "#cota.muelle_taladro_cerca",
            desde=x0 + w,
            lado="der",
        )
    )
    p.append(
        _cota_v(
            y0,
            y0 + lejos * e,
            x0 + w + 236,
            f"{lejos:.0f}",
            "#cota.muelle_taladro_lejos",
            desde=x0 + w,
            lado="der",
        )
    )
    p.append(
        _cota_v(
            y0,
            y0 + h,
            x0 + w + 366,
            f"{largo:.0f}",
            "#cota.muelle_largo",
            desde=x0 + w,
            lado="der",
        )
    )
    p.append(_cota_h(x0, x0 + w, y0 + h + 40, f"{ancho:.0f}", "#cota.muelle_ancho"))
    p.append(
        f'<path d="M{cx - taladro * e / 2 - 4:.1f} {y0 + lejos * e + 3:.1f}l-20 20h-30" '
        f'stroke="{COTA}" stroke-width="1" fill="none"/>'
    )
    p.append(
        _texto(
            cx - taladro * e / 2 - 58,
            y0 + lejos * e + 19,
            f"2 \u00d7 \u00d8{taladro:.1f}",
            9.5,
            COTA,
            "end",
            "bold",
        )
    )
    p.append(
        _texto(
            cx - taladro * e / 2 - 58,
            y0 + lejos * e + 29,
            "#cota.muelle_taladro_diametro",
            7.5,
            AUX,
            "end",
        )
    )

    notas = [
        "Se corta de una galga de espesores o de una regla de acero. "
        "No hace falta proveedor ni plazo.",
        "Con tijera de chapa, no con tijera de papel: la de papel lo riza, "
        "y un fleje rizado flexa torcido.",
        "Los dos taladros se hacen con la varilla puesta, de una pasada: as\u00ed "
        "caen donde caigan, pero los dos coinciden.",
        "Arandela ancha bajo cada cabeza. Contra la varilla no hay placa, y "
        "una cabeza de M4 sobre un fleje de 0,1 lo pellizca y lo desgarra.",
        "Sin rebabas en los cantos del tramo libre. Una rebaba es una entalla, "
        "y ah\u00ed es donde el fleje trabaja.",
    ]
    p.append(_texto(34, 412, "C\u00d3MO SE CORTA", 8.5, AUX, "start", "bold"))
    for i, nota in enumerate(notas):
        p.append(_texto(34, 430 + i * 15, f"\u00b7 {nota}", 8.5, TINTA, "start"))

    p.append(
        '<rect x="34" y="506" width="692" height="30" rx="4" fill="#fff4e5" '
        'stroke="#d98324" stroke-width="1"/>'
    )
    p.append(
        _texto(
            46,
            525,
            "NO TALADRAR EN EL TRAMO LIBRE. Un agujero donde el fleje flexa es la "
            "l\u00ednea por la que va a romper; donde solo tira, no pasa nada.",
            9.5,
            "#8a5200",
            "start",
            "bold",
        )
    )
    p.append(
        f'<rect x="34" y="554" width="692" height="104" fill="none" stroke="{TINTA}" '
        'stroke-width="1.2"/>'
    )
    campos = [
        ("N\u00famero", "1.3"),
        ("Pieza", "Fleje de suspensi\u00f3n"),
        ("Material", "Acero de muelle"),
        ("Espesor", f"{espesor:.1f} mm"),
        ("Cantidad", "1 \u00b7 y una de repuesto"),
        ("Veta", "No aplica"),
        ("Conjunto", "P\u00e9ndulo \u00b7 tanda 1"),
        ("Estado", "PENDIENTE \u00b7 lo mide R1"),
    ]
    for i, (k, val) in enumerate(campos):
        bx = 34 + (i % 4) * 173
        by = 554 + (i // 4) * 52
        p.append(
            f'<path d="M{bx} {by}h173v52h-173z" fill="none" stroke="{AUX}" stroke-width="0.6"/>'
        )
        p.append(_texto(bx + 10, by + 18, k.upper(), 7.5, AUX, "start"))
        p.append(_texto(bx + 10, by + 37, val, 11, TINTA, "start", "bold"))
    p.append("</svg>")
    return "\n".join(p)


def escuadra(c: Contratos) -> str:
    """La pieza 1.6: la tabla del banco R1.

    No es una pieza del reloj: es el utillaje que permite medir el periodo y
    el Q antes de que exista bastidor. Se dibuja igual porque sin esa medida
    el escape se dimensiona a ojo.

    Lo que la hace util es que **respeta el contrato de anclaje**: el bloque
    se atornilla aqui con el mismo patron con el que se atornillara al
    bastidor, asi que pasa de uno a otro sin volver a taladrarlo.

    Dos vistas, y la lateral no es decorativa: lo que esta pieza tiene que
    dejar claro es la **pila** -tabla, bloque, fleje, placa- porque de ella
    sale a que distancia de la tabla cuelga la varilla, y si roza, no se mide
    el Q del pendulo sino el de la tabla.
    """
    b = c.contrato("banco_pendulo")
    anc = b.valor("escuadra_ancho").en_mm
    alt = b.valor("escuadra_alto").en_mm
    esp = b.valor("escuadra_espesor").en_mm
    al_canto = b.valor("escuadra_bloque_al_canto").en_mm
    guia = b.valor("escuadra_taladro_diametro").en_mm
    t_canto = b.valor("escuadra_taladro_al_canto").en_mm
    t_lado = b.valor("escuadra_taladro_al_lado").en_mm
    mordaza = b.valor("escuadra_mordaza_libre").en_mm
    sep = c.valor("anclaje", "anclaje_tornillo_separacion").en_mm
    bl_anc = c.valor("suspension", "soporte_ancho").en_mm
    bl_alt = c.valor("suspension", "soporte_alto").en_mm
    bl_esp = c.valor("suspension", "soporte_espesor").en_mm
    placa = c.valor("suspension", "soporte_placa_espesor").en_mm
    placa_alt = c.valor("suspension", "soporte_placa_alto").en_mm
    fleje = c.valor("suspension", "muelle_largo").en_mm
    empotrado = c.valor("suspension", "muelle_empotrado").en_mm
    va_esp = c.valor("pendulo", "varilla_espesor").en_mm

    e = 1.0
    p: list[str] = [CABEZA.format(cota=COTA, ancho=900, alto=700)]
    p.append(_texto(34, 34, "1.6 \u00b7 ESCUADRA DEL BANCO R1", 15, TINTA, "start", "bold"))
    p.append(
        _texto(
            34,
            50,
            "Utillaje, no pieza del reloj \u00b7 cotas le\u00eddas de docs/reloj/contratos.json",
            9.5,
            AUX,
            "start",
        )
    )

    # ---- vista 1, la tabla de frente -------------------------------------
    x0, y0 = 230.0, 150.0
    w, h = anc * e, alt * e
    cx = x0 + w / 2
    y_taladro = y0 + t_canto * e
    y_canto = y0 + al_canto * e
    p.append(_texto(x0 - 56, 88, "LA TABLA \u00b7 de frente \u00b7 escala 1:1", 9, TINTA, "start"))
    p.append(_texto(x0 - 56, 101, "tablero de 18, veta a lo largo", 8, AUX, "start"))
    p.append(
        f'<rect x="{x0}" y="{y0}" width="{w:.1f}" height="{h:.1f}" fill="none" '
        f'stroke="{TINTA}" stroke-width="1.4"/>'
    )
    for lado in (0.0, w - mordaza * e):
        p.append(
            f'<rect x="{x0 + lado:.1f}" y="{y0}" width="{mordaza * e:.1f}" '
            f'height="{h:.1f}" fill="{AUX}" fill-opacity="0.15" stroke="none"/>'
        )
    p.append(
        f'<rect x="{cx - bl_anc * e / 2:.1f}" y="{y_canto - bl_alt * e:.1f}" '
        f'width="{bl_anc * e:.1f}" height="{bl_alt * e:.1f}" fill="{COTA}" '
        f'fill-opacity="0.10" stroke="{COTA}" stroke-width="0.9" stroke-dasharray="4 2"/>'
    )
    p.append(
        f'<rect x="{cx - 9:.1f}" y="{y_canto:.1f}" width="18" '
        f'height="{(fleje - empotrado) * e:.1f}" fill="{COTA}" fill-opacity="0.10" '
        f'stroke="{COTA}" stroke-width="0.9" stroke-dasharray="4 2"/>'
    )
    for dx in (-sep * e / 2, sep * e / 2):
        p.append(
            f'<circle cx="{cx + dx:.1f}" cy="{y_taladro:.1f}" r="{guia * e / 2:.2f}" '
            f'fill="none" stroke="{TINTA}" stroke-width="1.2"/>'
        )
    p.append(
        f'<path d="M{x0 - 10:.1f} {y_canto:.1f}H{x0 + w + 10:.1f}" stroke="{COTA}" '
        f'stroke-width="1" stroke-dasharray="6 3"/>'
    )
    p.append(_texto(x0 + w + 14, y_canto + 3, "EL DATUM", 8.5, COTA, "start", "bold"))
    p.append(_texto(x0 - 46, y_canto - bl_alt * e + 14, "el bloque, detr\u00e1s", 8, COTA, "end"))
    p.append(
        _cota_h(
            cx - sep * e / 2,
            cx + sep * e / 2,
            y0 - 26,
            f"{sep:.0f}",
            "#cota.anclaje_tornillo_separacion",
        )
    )
    p.append(
        _cota_h(
            x0,
            cx - sep * e / 2,
            y0 + h + 40,
            f"{t_lado:.0f}",
            "#cota.escuadra_taladro_al_lado",
        )
    )
    p.append(_cota_h(x0, x0 + w, y0 + h + 72, f"{anc:.0f}", "#cota.escuadra_ancho"))
    p.append(
        _cota_h(
            x0,
            x0 + mordaza * e,
            y0 + h + 104,
            f"{mordaza:.0f}",
            "#cota.escuadra_mordaza_libre",
        )
    )
    p.append(_cota_v(y0, y0 + h, x0 - 36, f"{alt:.0f}", "#cota.escuadra_alto", desde=x0))
    p.append(
        _cota_v(
            y0,
            y_taladro,
            x0 + w + 96,
            f"{t_canto:.0f}",
            "#cota.escuadra_taladro_al_canto",
            desde=x0 + w,
            lado="der",
        )
    )
    p.append(
        _cota_v(
            y0,
            y_canto,
            x0 + w + 210,
            f"{al_canto:.0f}",
            "#cota.escuadra_bloque_al_canto",
            desde=x0 + w,
            lado="der",
        )
    )
    xg = cx - sep * e / 2
    p.append(
        f'<path d="M{xg - guia * e / 2 - 4:.1f} {y_taladro:.1f}l-30 -30h-40" '
        f'stroke="{COTA}" stroke-width="1" fill="none"/>'
    )
    p.append(
        _texto(
            xg - 76, y_taladro - 38, f"2 \u00d7 \u00d8{guia:.1f} pasante", 9.5, COTA, "end", "bold"
        )
    )
    p.append(_texto(xg - 76, y_taladro - 28, "#cota.escuadra_taladro_diametro", 7.5, AUX, "end"))

    # ---- vista 2, la pila -------------------------------------------------
    # Lo que no se ve de frente y decide si el pendulo roza: cuanto sale
    # hacia delante cada cosa.
    sx = 700.0
    p.append(_texto(sx - 40, 88, "LA PILA \u00b7 de lado \u00b7 escala 1:1", 9, TINTA, "start"))
    p.append(_texto(sx - 40, 101, "lo que sobresale hacia delante", 8, AUX, "start"))
    p.append(
        f'<rect x="{sx}" y="{y0}" width="{esp * e:.1f}" height="{h:.1f}" fill="{AUX}" '
        f'fill-opacity="0.18" stroke="{TINTA}" stroke-width="1.4"/>'
    )
    xb = sx + esp * e
    p.append(
        f'<rect x="{xb:.1f}" y="{y_canto - bl_alt * e:.1f}" width="{bl_esp * e:.1f}" '
        f'height="{bl_alt * e:.1f}" fill="{COTA}" fill-opacity="0.10" stroke="{COTA}" '
        f'stroke-width="1" stroke-dasharray="4 2"/>'
    )
    xp = xb + bl_esp * e
    p.append(
        f'<rect x="{xp + 1:.1f}" y="{y_canto - placa_alt * e:.1f}" width="{placa * e:.1f}" '
        f'height="{placa_alt * e:.1f}" fill="{COTA}" fill-opacity="0.10" stroke="{COTA}" '
        f'stroke-width="1" stroke-dasharray="4 2"/>'
    )
    p.append(
        f'<path d="M{xp:.1f} {y_canto - bl_alt * e:.1f}V{y_canto + (fleje - empotrado) * e:.1f}" '
        f'stroke="{COTA}" stroke-width="1.6"/>'
    )
    y_var = y_canto + (fleje - empotrado) * e
    p.append(
        f'<rect x="{xp - va_esp * e / 2:.1f}" y="{y_var:.1f}" width="{va_esp * e:.1f}" '
        f'height="40" fill="none" stroke="{TINTA}" stroke-width="1.4"/>'
    )
    p.append(_texto(sx - 8, y0 + 16, "tabla", 8, AUX, "end"))
    p.append(_texto(xp + 14, y_canto - bl_alt * e + 12, "bloque + placa", 8, COTA, "start"))
    p.append(_texto(xp + 14, y_var + 26, "la varilla, al aire", 8, AUX, "start"))
    p.append(_cota_h(sx, xb, y0 - 26, f"{esp:.0f}", "#cota.escuadra_espesor"))
    p.append(
        _cota_h(
            xb,
            xp + 1 + placa * e,
            y0 + h + 40,
            f"{bl_esp:.0f} + {placa:.0f}",
            "#cota.soporte_espesor",
        )
    )
    p.append(
        f'<path d="M{xp:.1f} {y_var + 52:.1f}H{sx:.1f}" stroke="{AUX}" stroke-width="0.6" '
        f'stroke-dasharray="3 2"/>'
    )
    p.append(
        _texto(
            sx - 6,
            y_var + 55,
            f"la varilla cuelga a {esp + bl_esp:.0f} mm de la cara de la tabla",
            8,
            AUX,
            "end",
        )
    )

    notas = [
        "El tornillo ROSCA en la tabla: el agujero es gu\u00eda de 3,4, no paso de 4,2. "
        "Si se taladra a 4,2 el bloque queda suelto y el p\u00e9ndulo baila.",
        "Las dos franjas sombreadas son para la mordaza del banco. Si la mordaza "
        "pisa un tornillo, la tabla se monta torcida y el datum se inclina.",
        "Se monta con la tabla a plomo y el canto de arriba a nivel, comprobado "
        "con un nivel de burbuja: el datum es un canto horizontal.",
        "Lo que se mide: 100 oscilaciones -deben ser 200,0 s-, cu\u00e1ntas tarda la "
        "amplitud en caer a la mitad, y la varilla en una balanza.",
    ]
    p.append(_texto(34, 500, "C\u00d3MO SE USA", 8.5, AUX, "start", "bold"))
    for i, nota in enumerate(notas):
        p.append(_texto(34, 518 + i * 15, f"\u00b7 {nota}", 8.5, TINTA, "start"))

    p.append(
        '<rect x="34" y="572" width="832" height="30" rx="4" fill="#fff4e5" '
        'stroke="#d98324" stroke-width="1"/>'
    )
    p.append(
        _texto(
            46,
            591,
            "ES UTILLAJE, NO ENTRA EN EL RELOJ. Pero su patr\u00f3n de taladros es el del "
            "bastidor: el bloque pasa de aqu\u00ed a la m\u00e1quina sin volver a taladrarlo.",
            9.5,
            "#8a5200",
            "start",
            "bold",
        )
    )
    p.append(
        f'<rect x="34" y="620" width="832" height="52" fill="none" stroke="{TINTA}" '
        'stroke-width="1.2"/>'
    )
    campos = [
        ("N\u00famero", "1.6"),
        ("Material", "Tablero"),
        ("Espesor", f"{esp:.0f} mm"),
        ("Cantidad", "1"),
        ("Veta", "A lo largo"),
        ("Conjunto", "Utillaje \u00b7 R1"),
        ("Estado", "Lista para cortar"),
    ]
    celda = 832 / len(campos)
    for i, (k, val) in enumerate(campos):
        bx = 34 + i * celda
        p.append(
            f'<path d="M{bx:.1f} 620h{celda:.1f}v52h-{celda:.1f}z" fill="none" '
            f'stroke="{AUX}" stroke-width="0.6"/>'
        )
        p.append(_texto(bx + 10, 638, k.upper(), 7.5, AUX, "start"))
        p.append(_texto(bx + 10, 657, val, 10.5, TINTA, "start", "bold"))
    p.append("</svg>")
    return "\n".join(p)


def rueda_escape(c: Contratos) -> str:
    """La pieza 2.1: la rueda de escape.

    Tres paneles. La rueda entera con sus radios, **un diente acotado para
    trazarlo** -que es lo que faltaba: los angulos de la punta no se pueden
    teclear en un boceto, hay que convertirlos a angulos de centro- y el
    engrane con el ancora, que es donde se ve para que sirve el perfil.
    """
    r = c.contrato("rueda_escape")
    a = c.contrato("ancora")
    diam = r.valor("rueda_escape_diametro").en_mm
    fondo = r.valor("rueda_escape_diametro_fondo").en_mm
    altura = r.valor("rueda_escape_altura_diente").en_mm
    paso = r.valor("rueda_escape_paso_diente").en_mm
    espesor = r.valor("rueda_escape_espesor").en_mm
    cubo = r.valor("rueda_escape_cubo_diametro").en_mm
    eje = r.valor("rueda_escape_eje_diametro").en_mm
    socavado = r.valor("rueda_escape_socavado").valor
    incluido = r.valor("rueda_escape_angulo_incluido").valor
    dorso_inc = r.valor("rueda_escape_dorso_inclinacion").valor
    espesor_punta = r.valor("rueda_escape_espesor_punta").valor
    angular = r.valor("rueda_escape_paso_angular").valor
    adelanto = r.valor("rueda_escape_punta_adelanto").valor
    retraso = r.valor("rueda_escape_dorso_retraso").valor
    hueco = r.valor("rueda_escape_hueco_angular").valor
    radios = int(r.valor("rueda_escape_radios").valor)
    ancho_radio = r.valor("rueda_escape_radio_ancho").en_mm
    cuerda = r.valor("rueda_escape_cuerda_diente").en_mm
    cuerda5 = r.valor("rueda_escape_cuerda_cinco").en_mm
    dientes = int(c.valor("escape", "dientes_escape").valor)
    abarca = c.valor("escape", "abarque_ancora").valor
    entre = a.valor("ancora_entre_centros").en_mm
    brazo = a.valor("ancora_brazo").en_mm
    abierto = a.valor("ancora_angulo_brazos").valor
    arco_e = a.valor("ancora_arco_entrada").en_mm
    arco_s = a.valor("ancora_arco_salida").en_mm
    reposo = a.valor("ancora_reposo").valor

    p: list[str] = [CABEZA.format(cota=COTA, ancho=1180, alto=1020)]
    p.append(_texto(34, 34, "2.1 \u00b7 RUEDA DE ESCAPE", 15, TINTA, "start", "bold"))
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

    def perfil(cx: float, cy: float, e: float, desde: float = 0.0) -> str:
        """El contorno de los 30 dientes. Cuatro puntos por diente y el hueco."""
        rp, rf = diam * e / 2.0, fondo * e / 2.0

        def pol(rad: float, ang: float) -> tuple[float, float]:
            return cx + rad * math.cos(ang + desde), cy + rad * math.sin(ang + desde)

        trozos: list[str] = []
        for i in range(dientes):
            a0 = i * angular
            puntos = [
                pol(rf, a0),
                pol(rp, a0 + retraso),
                pol(rp, a0 + retraso + espesor_punta),
                pol(rf, a0 + retraso + espesor_punta + adelanto),
                pol(rf, a0 + angular),
            ]
            for n, (xx, yy) in enumerate(puntos):
                trozos.append(f"{'M' if i == 0 and n == 0 else 'L'}{xx:.2f} {yy:.2f}")
        return " ".join(trozos) + "Z"

    # ---- panel 1, la rueda -----------------------------------------------
    e1 = 1.6
    cx, cy = 280.0, 330.0
    rp1, rf1 = diam * e1 / 2.0, fondo * e1 / 2.0
    p.append(_texto(cx - rp1 - 40, 92, "LA RUEDA \u00b7 escala 1,6:1", 9, TINTA, "start"))
    p.append(
        _texto(
            cx - rp1 - 40, 105, f"{dientes} dientes \u00b7 VISTA DESDE LA ESFERA", 8, AUX, "start"
        )
    )
    p.append(f'<path d="{perfil(cx, cy, e1)}" fill="none" stroke="{TINTA}" stroke-width="1.4"/>')
    for radio, trazo in ((rf1, "3 3"), (cubo * e1 / 2.0, "4 2")):
        p.append(
            f'<circle cx="{cx}" cy="{cy}" r="{radio:.1f}" fill="none" stroke="{AUX}" '
            f'stroke-width="0.8" stroke-dasharray="{trazo}"/>'
        )
    for k in range(radios):
        ang = k * 2.0 * math.pi / radios + math.pi / 6.0
        p.append(
            f'<path d="M{cx + cubo * e1 / 2.0 * math.cos(ang):.1f} '
            f"{cy + cubo * e1 / 2.0 * math.sin(ang):.1f}"
            f'L{cx + (rf1 - 3) * math.cos(ang):.1f} {cy + (rf1 - 3) * math.sin(ang):.1f}" '
            f'stroke="{TINTA}" stroke-width="{ancho_radio * e1:.1f}" stroke-linecap="round" '
            f'fill="none" opacity="0.3"/>'
        )
    p.append(
        f'<circle cx="{cx}" cy="{cy}" r="{eje * e1 / 2.0:.1f}" fill="none" stroke="{TINTA}" '
        f'stroke-width="1.4"/>'
    )
    ra = rp1 + 28
    p.append(
        f'<path d="M{cx + ra * math.cos(math.radians(-62)):.1f} '
        f"{cy + ra * math.sin(math.radians(-62)):.1f}A{ra:.1f} {ra:.1f} 0 0 1 "
        f"{cx + ra * math.cos(math.radians(-22)):.1f} "
        f'{cy + ra * math.sin(math.radians(-22)):.1f}" stroke="{COTA}" stroke-width="1.4" '
        f'fill="none" marker-end="url(#f)"/>'
    )
    p.append(
        _texto(
            cx + ra * math.cos(math.radians(-42)) + 10,
            cy + ra * math.sin(math.radians(-42)),
            "giro",
            8,
            COTA,
            "start",
            "bold",
        )
    )
    p.append(
        _cota_v(
            cy - rp1,
            cy + rp1,
            cx - rp1 - 40,
            f"\u00d8{diam:.0f}",
            "#cota.rueda_escape_diametro",
            desde=cx - rp1,
        )
    )
    p.append(
        _cota_v(
            cy - rf1,
            cy + rf1,
            cx + rp1 + 40,
            f"\u00d8{fondo:.0f}",
            "#cota.rueda_escape_diametro_fondo",
            desde=cx + rf1,
            lado="der",
        )
    )
    p.append(
        _cota_h(
            cx - cubo * e1 / 2.0,
            cx + cubo * e1 / 2.0,
            cy + rp1 + 60,
            f"\u00d8{cubo:.0f}",
            "#cota.rueda_escape_cubo_diametro",
        )
    )
    p.append(
        f'<path d="M{cx - eje * e1 / 2.0:.1f} {cy:.1f}l-46 56h-30" stroke="{COTA}" '
        f'stroke-width="1" fill="none"/>'
    )
    p.append(
        _texto(cx - eje * e1 / 2.0 - 80, cy + 52, f"\u00d8{eje:.0f} H7", 9.5, COTA, "end", "bold")
    )
    p.append(
        _texto(
            cx - eje * e1 / 2.0 - 80, cy + 62, "#cota.rueda_escape_eje_diametro", 7.5, AUX, "end"
        )
    )
    ang_r = math.pi / 6.0
    p.append(
        f'<path d="M{cx + (rf1 * 0.6) * math.cos(ang_r) + 10:.1f} '
        f'{cy + (rf1 * 0.6) * math.sin(ang_r) + 10:.1f}l40 40h30" stroke="{COTA}" '
        f'stroke-width="1" fill="none"/>'
    )
    p.append(
        _texto(
            cx + rf1 * 0.6 * math.cos(ang_r) + 84,
            cy + rf1 * 0.6 * math.sin(ang_r) + 46,
            f"{radios} radios de {ancho_radio:.0f}",
            9.5,
            COTA,
            "start",
            "bold",
        )
    )
    p.append(
        _texto(
            cx + rf1 * 0.6 * math.cos(ang_r) + 84,
            cy + rf1 * 0.6 * math.sin(ang_r) + 56,
            "#num.rueda_escape_radios \u00b7 #cota.rueda_escape_radio_ancho",
            7.5,
            AUX,
            "start",
        )
    )

    # ---- panel 2, un diente, acotado para trazarlo ------------------------
    # El socavado y el dorso se miden EN LA PUNTA; el boceto se construye
    # desde el centro. Las dos conversiones son lo que se teclea, y por eso
    # este panel las lleva las dos.
    e2 = 12.0
    dcx, dcy = 840.0, 690.0
    rp2, rf2 = diam * e2 / 2.0, fondo * e2 / 2.0
    p.append(
        _texto(
            620, 92, "UN DIENTE \u00b7 escala 12:1 \u00b7 acotado para trazarlo", 9, TINTA, "start"
        )
    )
    p.append(
        _texto(
            620,
            105,
            "los \u00e1ngulos de la punta y los de centro: no son los mismos",
            8,
            AUX,
            "start",
        )
    )

    def pol2(rad: float, ang: float) -> tuple[float, float]:
        return dcx + rad * math.cos(ang - math.pi / 2.0), dcy + rad * math.sin(ang - math.pi / 2.0)

    base = -angular * 0.55
    pts = [
        pol2(rf2, base),
        pol2(rp2, base + retraso),
        pol2(rp2, base + retraso + espesor_punta),
        pol2(rf2, base + retraso + espesor_punta + adelanto),
        pol2(rf2, base + angular),
        pol2(rp2, base + angular + retraso),
    ]
    p.append(
        '<path d="'
        + " ".join(f"{'M' if i == 0 else 'L'}{x:.1f} {y:.1f}" for i, (x, y) in enumerate(pts))
        + f'" fill="none" stroke="{TINTA}" stroke-width="1.8"/>'
    )
    for rad, trazo, rot in ((rp2, "6 3", "punta"), (rf2, "3 3", "fondo")):
        x0, y0 = pol2(rad, base - 0.012)
        x1, y1 = pol2(rad, base + angular + 0.03)
        p.append(
            f'<path d="M{x0:.1f} {y0:.1f}A{rad:.1f} {rad:.1f} 0 0 1 {x1:.1f} {y1:.1f}" '
            f'fill="none" stroke="{AUX}" stroke-width="0.8" stroke-dasharray="{trazo}"/>'
        )
        p.append(_texto(x1 + 8, y1 + 3, f"c\u00edrculo de {rot}", 7.5, AUX, "start"))
    # Los radios al centro: son las lineas de construccion de verdad, porque
    # un boceto se traza por angulos de centro y no por angulos de punta.
    for ang in (
        base,
        base + retraso,
        base + retraso + espesor_punta,
        base + retraso + espesor_punta + adelanto,
        base + angular,
    ):
        x1, y1 = pol2(rf2 - 26, ang)
        x2, y2 = pol2(rp2 + 16, ang)
        p.append(
            f'<path d="M{x1:.1f} {y1:.1f}L{x2:.1f} {y2:.1f}" stroke="{AUX}" stroke-width="0.6" '
            f'stroke-dasharray="8 3 2 3"/>'
        )
    # El paso, dibujado y no solo sumado: es la primera pregunta que hace
    # cualquiera al ver la rueda, y la respuesta es 360 entre los dientes.
    x1, y1 = pol2(rp2 + 34, base)
    x2, y2 = pol2(rp2 + 34, base + angular)
    p.append(
        f'<path d="M{x1:.1f} {y1:.1f}A{rp2 + 34:.1f} {rp2 + 34:.1f} 0 0 1 {x2:.1f} {y2:.1f}" '
        f'fill="none" stroke="{COTA}" stroke-width="1.2" marker-start="url(#f)" '
        f'marker-end="url(#f)"/>'
    )
    xm, ym = pol2(rp2 + 48, base + angular / 2.0)
    p.append(
        _texto(
            xm, ym, f"{math.degrees(angular):.0f}\u00b0 = 360 / {dientes}", 10, COTA, peso="bold"
        )
    )
    p.append(_texto(xm, ym + 11, "#angulo.rueda_escape_paso_angular", 7.5, AUX))
    p.append(
        _texto(
            640,
            250,
            "Los cuatro radios acotan, acumulados desde el pie del dorso:",
            8.5,
            TINTA,
            "start",
        )
    )
    for i, (rotulo, grados, clave) in enumerate(
        (
            ("retraso del dorso", math.degrees(retraso), "#angulo.rueda_escape_dorso_retraso"),
            (
                "espesor de la punta",
                math.degrees(espesor_punta),
                "#angulo.rueda_escape_espesor_punta",
            ),
            ("adelanto de la punta", math.degrees(adelanto), "#angulo.rueda_escape_punta_adelanto"),
            ("hueco para la sierra", math.degrees(hueco), "#angulo.rueda_escape_hueco_angular"),
        )
    ):
        p.append(_texto(656, 270 + i * 16, f"{grados:5.2f}\u00b0", 9.5, COTA, "start", "bold"))
        p.append(_texto(710, 270 + i * 16, rotulo, 8.5, TINTA, "start"))
        p.append(_texto(850, 270 + i * 16, clave, 7.5, AUX, "start"))
    p.append(
        _texto(
            640,
            350,
            f"Suman {math.degrees(angular):.0f}\u00b0, el paso. El diente ocupa "
            f"{math.degrees(retraso + espesor_punta + adelanto):.2f}\u00b0 y el hueco el resto:",
            8.5,
            TINTA,
            "start",
        )
    )
    p.append(
        _texto(
            640,
            365,
            f"{fondo / 2.0 * hueco:.2f} mm de arco en el fondo, tres veces y media la hoja de la "
            "segueta.",
            8.5,
            TINTA,
            "start",
        )
    )
    p.append(
        _texto(
            640, 394, "Los \u00e1ngulos medidos EN LA PUNTA, de donde salen:", 8.5, TINTA, "start"
        )
    )
    for i, (rotulo, grados, clave) in enumerate(
        (
            ("socavado de la cara", math.degrees(socavado), "#angulo.rueda_escape_socavado"),
            (
                "inclinaci\u00f3n del dorso",
                math.degrees(dorso_inc),
                "#angulo.rueda_escape_dorso_inclinacion",
            ),
            (
                "cu\u00f1a de la punta",
                math.degrees(incluido),
                "#angulo.rueda_escape_angulo_incluido",
            ),
        )
    ):
        p.append(_texto(656, 414 + i * 16, f"{grados:5.1f}\u00b0", 9.5, COTA, "start", "bold"))
        p.append(_texto(710, 414 + i * 16, rotulo, 8.5, TINTA, "start"))
        p.append(_texto(850, 414 + i * 16, clave, 7.5, AUX, "start"))
    p.append(
        _texto(
            640,
            510,
            f"VERIFICAR: {cuerda5:.2f} mm de punta a punta saltando CINCO dientes.",
            9,
            COTA,
            "start",
            "bold",
        )
    )
    p.append(
        _texto(
            640,
            524,
            f"Cinco pasos son 60\u00b0 y la cuerda de 60\u00b0 vale el radio. Entre dos puntas "
            f"contiguas son {cuerda:.2f},",
            8.5,
            TINTA,
            "start",
        )
    )
    p.append(
        _texto(
            640,
            538,
            "que no es el paso de arco: el pie de rey mide la CUERDA. "
            "#cota.rueda_escape_cuerda_cinco",
            8.5,
            TINTA,
            "start",
        )
    )
    p.append(
        _texto(
            640,
            482,
            f"altura {altura:.0f} \u00b7 #cota.rueda_escape_altura_diente \u00b7 "
            f"paso de arco {paso:.2f} \u00b7 #cota.rueda_escape_paso_diente",
            8.5,
            AUX,
            "start",
        )
    )

    # ---- panel 3, el engrane ----------------------------------------------
    e3 = 2.0
    gx, gy = 300.0, 800.0
    ax, ay = gx, gy - entre * e3
    p.append(_texto(60, 620, "EL ENGRANE \u00b7 escala 2:1 \u00b7 en el reposo", 9, TINTA, "start"))
    p.append(
        _texto(
            60, 633, "para qu\u00e9 sirve el perfil: el diente apoya en el ARCO", 8, AUX, "start"
        )
    )
    p.append(
        f'<path d="{perfil(gx, gy, e3, desde=-math.pi / 2.0 - 0.02)}" fill="none" '
        f'stroke="{TINTA}" stroke-width="1.2"/>'
    )
    p.append(
        f'<circle cx="{gx}" cy="{gy}" r="{fondo * e3 / 2.0:.1f}" fill="none" stroke="{AUX}" '
        f'stroke-width="0.8" stroke-dasharray="3 3"/>'
    )
    for signo, arco, rotulo in ((-1.0, arco_e, "entrada"), (1.0, arco_s, "salida")):
        ang = math.pi / 2.0 + signo * abierto / 2.0
        ux, uy = math.cos(ang), math.sin(ang)
        p.append(
            f'<path d="M{ax:.1f} {ay:.1f}L{ax + brazo * e3 * ux:.1f} '
            f'{ay + brazo * e3 * uy:.1f}" stroke="{TINTA}" stroke-width="1.6"/>'
        )
        # El arco de reposo, centrado en el eje del ancora: esto es el deadbeat
        r3 = arco * e3
        a1, a2 = ang - reposo * 1.6, ang + reposo * 1.6
        p.append(
            f'<path d="M{ax + r3 * math.cos(a1):.1f} {ay + r3 * math.sin(a1):.1f}'
            f"A{r3:.1f} {r3:.1f} 0 0 1 {ax + r3 * math.cos(a2):.1f} "
            f'{ay + r3 * math.sin(a2):.1f}" fill="none" stroke="{COTA}" stroke-width="2.6"/>'
        )
        p.append(
            _texto(
                ax + r3 * math.cos(ang) + signo * 96,
                ay + r3 * math.sin(ang) + 34,
                f"arco de {rotulo}",
                7.5,
                COTA,
                "start" if signo > 0 else "end",
                "bold",
            )
        )
        p.append(
            _texto(
                ax + r3 * math.cos(ang) + signo * 96,
                ay + r3 * math.sin(ang) + 44,
                f"R{arco:.2f}",
                9,
                COTA,
                "start" if signo > 0 else "end",
                "bold",
            )
        )
    p.append(
        f'<circle cx="{ax:.1f}" cy="{ay:.1f}" r="{eje * e3 / 2.0:.1f}" fill="none" '
        f'stroke="{TINTA}" stroke-width="1.6"/>'
    )
    p.append(_texto(ax, ay - 14, "eje del \u00e1ncora", 8, AUX))
    p.append(
        f'<path d="M{ax:.1f} {ay:.1f}L{gx:.1f} {gy:.1f}" stroke="{AUX}" stroke-width="0.6" '
        f'stroke-dasharray="8 3 2 3"/>'
    )
    p.append(
        _cota_v(
            ay,
            gy,
            gx - diam * e3 / 2.0 - 54,
            f"{entre:.2f}",
            "#cota.ancora_entre_centros",
            desde=gx - diam * e3 / 2.0,
        )
    )
    p.append(
        _texto(
            620,
            660,
            "LOS DOS ARCOS EST\u00c1N CENTRADOS EN EL EJE DEL \u00c1NCORA, y en eso",
            8.5,
            COTA,
            "start",
            "bold",
        )
    )
    for i, linea in enumerate(
        [
            "consiste el deadbeat: mientras el diente apoya en el arco, el \u00e1ncora",
            "gira y la rueda no se mueve. En un retroceso la cara es un plano y la",
            "rueda retrocede. Los dos radios difieren en la profundidad del impulso,",
            f"{arco_s - arco_e:.2f} mm, que es lo que el diente empuja.",
        ]
    ):
        p.append(_texto(620, 676 + i * 14, linea, 8.5, TINTA, "start"))
    p.append(
        _texto(620, 750, f"abarque {abarca:g} dientes \u00b7 #num.abarque_ancora", 8, AUX, "start")
    )
    p.append(_texto(620, 764, f"brazo {brazo:.0f} \u00b7 #cota.ancora_brazo", 8, AUX, "start"))

    p.append(
        '<rect x="34" y="904" width="1112" height="46" rx="4" fill="#fff4e5" '
        'stroke="#d98324" stroke-width="1"/>'
    )
    p.append(
        _texto(
            46,
            923,
            "NO ES PLANTILLA DE CORTE, Y ESTA MENOS QUE NINGUNA: el perfil del diente decide el "
            "reposo del escape.",
            9.5,
            "#8a5200",
            "start",
            "bold",
        )
    )
    p.append(
        _texto(
            46,
            939,
            "Un disco plano se monta del rev\u00e9s sin que se note y los dientes miran al otro "
            "lado: si el escape no engancha, se voltea la rueda.",
            9,
            "#8a5200",
            "start",
        )
    )
    p.append(
        f'<rect x="34" y="956" width="1112" height="52" fill="none" stroke="{TINTA}" '
        'stroke-width="1.2"/>'
    )
    campos = [
        ("N\u00famero", "2.1"),
        ("Material", "Abedul 4 mm"),
        ("Espesor", f"{espesor:.0f} mm"),
        ("Cantidad", "1"),
        ("Dientes", f"{dientes}"),
        ("Radios", f"{radios}"),
        ("Conjunto", "Escape \u00b7 R2"),
        ("Estado", "PENDIENTE \u00b7 R2"),
    ]
    celda = 1112 / len(campos)
    for i, (k, val) in enumerate(campos):
        bx = 34 + i * celda
        p.append(
            f'<path d="M{bx:.1f} 956h{celda:.1f}v52h-{celda:.1f}z" fill="none" '
            f'stroke="{AUX}" stroke-width="0.6"/>'
        )
        p.append(_texto(bx + 10, 974, k.upper(), 7.5, AUX, "start"))
        p.append(_texto(bx + 10, 993, val, 10.5, TINTA, "start", "bold"))
    p.append("</svg>")
    return "\n".join(p)


def ancora(c: Contratos) -> str:
    """La pieza 2.2: el cuerpo del ancora.

    Tres vistas, y cada una existe por una razon distinta:

    - **El escape montado**, porque la cota que manda -`ancora_entre_centros`-
      no esta en el ancora sino entre las dos piezas, y en un dibujo de la
      pieza sola no se ve.
    - **El cuerpo**, que es la pieza que se corta: dos ovalos y un circulo
      unidos, con la ranura situada desde el eje.
    - **El canto**, porque la paleta va atornillada sobre la cara y eso solo
      se entiende de lado.

    Lo que NO lleva es el reposo ni el impulso: son cotas de puesta a punto,
    se buscan en R2 moviendo la paleta en su ranura, y ponerlas en un plano
    seria prometer una precision que la madera no da.
    """
    a = c.contrato("ancora")
    entre = a.valor("ancora_entre_centros").en_mm
    brazo = a.valor("ancora_brazo").en_mm
    material = a.valor("ancora_brazo_material").en_mm
    abierto = a.valor("ancora_angulo_brazos").valor
    recorrido = a.valor("ancora_recorrido").valor
    reposo = a.valor("ancora_reposo").valor
    espesor = a.valor("ancora_espesor").en_mm
    ancho = a.valor("ancora_brazo_ancho").en_mm
    eje = a.valor("ancora_eje_diametro").en_mm
    cubo = a.valor("ancora_cubo_diametro").en_mm
    ranura_l = a.valor("ancora_ranura_largo").en_mm
    ranura_a = a.valor("ancora_ranura_ancho").en_mm
    ranura_eje = a.valor("ancora_ranura_al_eje").en_mm
    hueco = a.valor("ancora_hueco_a_la_rueda").en_mm
    caja_an = a.valor("ancora_caja_ancho").en_mm
    caja_al = a.valor("ancora_caja_alto").en_mm
    rueda = c.valor("rueda_escape", "rueda_escape_diametro").en_mm / 2.0
    fondo = c.valor("rueda_escape", "rueda_escape_diametro_fondo").en_mm / 2.0

    p: list[str] = [CABEZA.format(cota=COTA, ancho=1180, alto=900)]
    p.append(_texto(34, 34, "2.2 \u00b7 \u00c1NCORA", 15, TINTA, "start", "bold"))
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

    def brazos(cx: float, cy: float, e: float, largo: float) -> list[tuple[float, float]]:
        return [
            (
                cx + largo * e * math.cos(math.pi / 2.0 + s2 * abierto / 2.0),
                cy + largo * e * math.sin(math.pi / 2.0 + s2 * abierto / 2.0),
            )
            for s2 in (-1.0, 1.0)
        ]

    # ---- vista 1, el escape montado --------------------------------------
    e1 = 1.5
    rx, ry = 250.0, 380.0
    ax, ay = rx, ry - entre * e1
    p.append(_texto(100, 92, "EL ESCAPE MONTADO \u00b7 escala 1,5:1", 9, TINTA, "start"))
    p.append(
        _texto(100, 105, "la rueda va detr\u00e1s; el \u00e1ncora es la pieza", 8, AUX, "start")
    )
    for radio, trazo in ((rueda * e1, "6 3"), (fondo * e1, "3 3")):
        p.append(
            f'<circle cx="{rx}" cy="{ry}" r="{radio:.1f}" fill="none" stroke="{AUX}" '
            f'stroke-width="0.9" stroke-dasharray="{trazo}"/>'
        )
    contactos = brazos(ax, ay, e1, brazo)
    for (cxp, cyp), (mxp, myp) in zip(contactos, brazos(ax, ay, e1, material), strict=True):
        p.append(
            f'<path d="M{ax:.1f} {ay:.1f}L{mxp:.1f} {myp:.1f}" stroke="{TINTA}" '
            f'stroke-width="{ancho * e1:.1f}" stroke-linecap="round" opacity="0.2"/>'
        )
        p.append(
            f'<path d="M{mxp:.1f} {myp:.1f}L{cxp:.1f} {cyp:.1f}" stroke="{COTA}" '
            f'stroke-width="{ancho * e1:.1f}" stroke-linecap="round" opacity="0.45"/>'
        )
        p.append(
            f'<path d="M{rx:.1f} {ry:.1f}L{cxp:.1f} {cyp:.1f}" stroke="{COTA}" '
            f'stroke-width="0.9" stroke-dasharray="5 3"/>'
        )
    p.append(
        f'<circle cx="{ax:.1f}" cy="{ay:.1f}" r="{cubo * e1 / 2.0:.1f}" fill="#ffffff" '
        f'stroke="{TINTA}" stroke-width="1.2"/>'
    )
    p.append(
        f'<circle cx="{ax:.1f}" cy="{ay:.1f}" r="{eje * e1 / 2.0:.1f}" fill="none" '
        f'stroke="{TINTA}" stroke-width="1.4"/>'
    )
    p.append(_texto(rx, ry + rueda * e1 + 18, "la rueda de escape", 8, AUX))
    cxp, cyp = contactos[1]
    p.append(
        f'<path d="M{cxp - 9:.1f} {cyp - 9:.1f}l9 9l-9 9" fill="none" stroke="{COTA}" '
        f'stroke-width="1"/>'
    )
    p.append(_texto(cxp + 30, cyp + 64, "90\u00b0 por construcci\u00f3n", 8, COTA, "start", "bold"))
    p.append(_texto(cxp + 30, cyp + 75, "el brazo es tangente a la rueda", 7.5, AUX, "start"))
    p.append(_texto(contactos[0][0] - 14, contactos[0][1] + 20, "la paleta", 7.5, COTA, "end"))
    p.append(
        _cota_v(
            ay,
            ry,
            rx - rueda * e1 - 48,
            f"{entre:.1f}",
            "#cota.ancora_entre_centros",
            desde=rx - rueda * e1,
        )
    )
    p.append(
        _texto(
            rx - rueda * e1 - 55,
            (ay + ry) / 2.0 + 26,
            "LA COTA CR\u00cdTICA",
            8,
            COTA,
            "end",
            "bold",
        )
    )
    p.append(
        _cota_v(
            ay + cubo * e1 / 2.0,
            ry - rueda * e1,
            rx + rueda * e1 + 40,
            f"{hueco:.1f}",
            "#cota.ancora_hueco_a_la_rueda",
            desde=rx + rueda * e1 * 0.4,
            lado="der",
        )
    )

    # ---- vista 2, el cuerpo ----------------------------------------------
    e2 = 2.4
    bx, by = 690.0, 200.0
    p.append(_texto(bx - 120, 92, "EL CUERPO \u00b7 escala 2,4:1", 9, TINTA, "start"))
    p.append(_texto(bx - 120, 105, "dos \u00f3valos y un c\u00edrculo, unidos", 8, AUX, "start"))
    puntas = brazos(bx, by, e2, material)
    for mxp, myp in puntas:
        p.append(
            f'<path d="M{bx:.1f} {by:.1f}L{mxp:.1f} {myp:.1f}" stroke="{TINTA}" '
            f'stroke-width="{ancho * e2:.1f}" stroke-linecap="round" fill="none" '
            f'opacity="0.14"/>'
        )
        p.append(
            f'<path d="M{bx:.1f} {by:.1f}L{mxp:.1f} {myp:.1f}" stroke="{TINTA}" '
            f'stroke-width="{ancho * e2:.1f}" stroke-linecap="round" fill="none" '
            f'stroke-opacity="1" opacity="0.0"/>'
        )
    # El contorno: cada ovalo y el circulo del cubo, que es como se construye.
    for mxp, myp in puntas:
        ux, uy = (mxp - bx), (myp - by)
        largo = math.hypot(ux, uy)
        ux, uy = ux / largo, uy / largo
        nx, ny = -uy * ancho * e2 / 2.0, ux * ancho * e2 / 2.0
        r2 = ancho * e2 / 2.0
        p.append(
            f'<path d="M{bx + nx:.1f} {by + ny:.1f}L{mxp + nx:.1f} {myp + ny:.1f}'
            f"A{r2:.1f} {r2:.1f} 0 0 1 {mxp - nx:.1f} {myp - ny:.1f}"
            f'L{bx - nx:.1f} {by - ny:.1f}" fill="none" stroke="{TINTA}" stroke-width="1.4"/>'
        )
        # La ranura, situada desde el eje y acabada en la punta del brazo.
        r1x, r1y = bx + ux * ranura_eje * e2, by + uy * ranura_eje * e2
        p.append(
            f'<path d="M{r1x:.1f} {r1y:.1f}L{mxp:.1f} {myp:.1f}" stroke="{COTA}" '
            f'stroke-width="{ranura_a * e2:.1f}" stroke-linecap="round" fill="none" '
            f'opacity="0.55"/>'
        )
    p.append(
        f'<circle cx="{bx:.1f}" cy="{by:.1f}" r="{cubo * e2 / 2.0:.1f}" fill="none" '
        f'stroke="{TINTA}" stroke-width="1.4"/>'
    )
    p.append(
        f'<circle cx="{bx:.1f}" cy="{by:.1f}" r="{eje * e2 / 2.0:.1f}" fill="none" '
        f'stroke="{TINTA}" stroke-width="1.4"/>'
    )
    for ang in (0.0, math.pi / 2.0):
        dxx, dyy = math.cos(ang) * (cubo * e2 / 2.0 + 14), math.sin(ang) * (cubo * e2 / 2.0 + 14)
        p.append(
            f'<path d="M{bx - dxx:.1f} {by - dyy:.1f}L{bx + dxx:.1f} {by + dyy:.1f}" '
            f'stroke="{AUX}" stroke-width="0.6" stroke-dasharray="10 3 2 3"/>'
        )
    mxp, myp = puntas[1]
    ux, uy = (mxp - bx) / (material * e2), (myp - by) / (material * e2)
    p.append(
        f'<path d="M{bx + ux * ranura_eje * e2 + 12:.1f} {by + uy * ranura_eje * e2 - 12:.1f}'
        f'l30 -56h40" stroke="{COTA}" stroke-width="1" fill="none"/>'
    )
    p.append(
        _texto(
            bx + ux * ranura_eje * e2 + 86,
            by + uy * ranura_eje * e2 - 72,
            f"ranura {ranura_l:.0f} \u00d7 \u00d8{ranura_a:.1f}",
            9.5,
            COTA,
            "start",
            "bold",
        )
    )
    p.append(
        _texto(
            bx + ux * ranura_eje * e2 + 86,
            by + uy * ranura_eje * e2 - 62,
            "#cota.ancora_ranura_largo \u00b7 #cota.ancora_ranura_ancho",
            7.5,
            AUX,
            "start",
        )
    )
    p.append(
        _cota_v(
            by,
            by + uy * ranura_eje * e2,
            bx + 150,
            f"{ranura_eje:.0f}",
            "#cota.ancora_ranura_al_eje",
            desde=bx + ux * ranura_eje * e2,
            lado="der",
        )
    )
    p.append(
        _cota_v(
            by,
            by + uy * material * e2,
            bx + 280,
            f"{material:.0f}",
            "#cota.ancora_brazo_material",
            desde=mxp,
            lado="der",
        )
    )
    p.append(
        _cota_h(
            bx - caja_an * e2 / 2.0,
            bx + caja_an * e2 / 2.0,
            by + caja_al * e2 + 40,
            f"{caja_an:.1f}",
            "#cota.ancora_caja_ancho",
        )
    )
    p.append(
        _cota_v(
            by - cubo * e2 / 2.0,
            by + caja_al * e2 - cubo * e2 / 2.0,
            bx - caja_an * e2 / 2.0 - 40,
            f"{caja_al:.1f}",
            "#cota.ancora_caja_alto",
            desde=bx - caja_an * e2 / 2.0,
        )
    )
    p.append(
        f'<path d="M{bx - cubo * e2 / 2.0 - 10:.1f} {by:.1f}l-34 -40h-40" stroke="{COTA}" '
        f'stroke-width="1" fill="none"/>'
    )
    p.append(
        _texto(
            bx - cubo * e2 / 2.0 - 88,
            by - 46,
            f"\u00d8{eje:.0f} H7 en \u00d8{cubo:.0f}",
            9.5,
            COTA,
            "end",
            "bold",
        )
    )
    p.append(
        _texto(
            bx - cubo * e2 / 2.0 - 88,
            by - 36,
            "#cota.ancora_eje_diametro \u00b7 #cota.ancora_cubo_diametro",
            7.5,
            AUX,
            "end",
        )
    )
    p.append(
        _texto(
            bx,
            by - cubo * e2 / 2.0 - 54,
            f"{math.degrees(abierto):.0f}\u00b0 entre brazos",
            9,
            COTA,
            peso="bold",
        )
    )
    p.append(_texto(bx, by - cubo * e2 / 2.0 - 44, "#angulo.ancora_angulo_brazos", 7.5, AUX))

    # ---- vista 3, el canto ------------------------------------------------
    e3 = 3.2
    kx, ky = 700.0, 600.0
    p.append(_texto(kx - 60, 550, "EL CANTO \u00b7 escala 3,2:1", 9, TINTA, "start"))
    largo_k = 150.0
    p.append(
        f'<rect x="{kx:.1f}" y="{ky:.1f}" width="{largo_k:.1f}" height="{espesor * e3:.1f}" '
        f'fill="{AUX}" fill-opacity="0.18" stroke="{TINTA}" stroke-width="1.4"/>'
    )
    p.append(
        f'<rect x="{kx + largo_k - 70:.1f}" y="{ky - espesor * e3:.1f}" width="86" '
        f'height="{espesor * e3:.1f}" fill="{COTA}" fill-opacity="0.18" stroke="{COTA}" '
        f'stroke-width="1.2" stroke-dasharray="4 2"/>'
    )
    p.append(
        f'<path d="M{kx + largo_k - 40:.1f} {ky - espesor * e3 - 10:.1f}'
        f'V{ky + espesor * e3 + 10:.1f}" stroke="{COTA}" stroke-width="1.6"/>'
    )
    p.append(_texto(kx - 6, ky + espesor * e3 / 2.0 + 3, "el brazo", 8, AUX, "end"))
    p.append(_texto(kx + largo_k + 10, ky - espesor * e3 / 2.0 + 3, "la paleta", 8, COTA, "start"))
    p.append(_texto(kx + largo_k - 40, ky + espesor * e3 + 26, "M4 por la ranura", 7.5, COTA))
    p.append(
        _cota_v(
            ky,
            ky + espesor * e3,
            kx - 46,
            f"{espesor:.0f}",
            "#cota.ancora_espesor",
            desde=kx,
        )
    )
    p.append(
        _texto(
            kx,
            ky + espesor * e3 + 56,
            "La paleta va SOBRE la cara, no en el canto: por eso el brazo acaba",
            8.5,
            TINTA,
            "start",
        )
    )
    p.append(
        _texto(
            kx,
            ky + espesor * e3 + 70,
            f"{brazo - material:.0f} mm antes del contacto y la paleta salva el resto.",
            8.5,
            TINTA,
            "start",
        )
    )

    # ---- el presupuesto angular -------------------------------------------
    px, py = 90.0, 580.0
    p.append(_texto(px, 550, "EL PRESUPUESTO ANGULAR", 9, TINTA, "start"))
    total = math.degrees(recorrido)
    rep = math.degrees(reposo)
    barra = 250.0
    xx = px
    for rotulo, grados, color in (
        ("reposo", rep, COTA),
        ("impulso y ca\u00edda", total - 2.0 * rep, AUX),
        ("reposo", rep, COTA),
    ):
        w = barra * grados / total
        p.append(
            f'<rect x="{xx:.1f}" y="{py}" width="{w:.1f}" height="26" fill="{color}" '
            f'fill-opacity="0.25" stroke="{color}" stroke-width="1"/>'
        )
        p.append(_texto(xx + w / 2.0, py + 17, f"{grados:.1f}\u00b0", 9, TINTA, peso="bold"))
        p.append(_texto(xx + w / 2.0, py + 40, rotulo, 7.5, AUX))
        xx += w
    p.append(_cota_h(px, px + barra, py + 74, f"{total:.0f}\u00b0", "#angulo.ancora_recorrido"))
    for i, linea in enumerate(
        [
            "El recorrido del \u00e1ncora es el del p\u00e9ndulo: la horquilla los ata, y de",
            "esos 4\u00b0 salen reposo, impulso y ca\u00edda. No se suman a ellos.",
            f"Por abajo: {rep:.1f}\u00b0 sobre un brazo de {brazo:.0f} son "
            f"{brazo * reposo:.2f} mm,",
            "contra los \u00b10,3 que se le piden al corte de la rueda.",
        ]
    ):
        p.append(_texto(px, py + 116 + i * 15, linea, 8.5, TINTA, "start"))

    p.append(
        '<rect x="34" y="768" width="1112" height="46" rx="4" fill="#fff4e5" '
        'stroke="#d98324" stroke-width="1"/>'
    )
    p.append(
        _texto(
            46,
            787,
            "EL REPOSO Y EL IMPULSO NO EST\u00c1N EN ESTA HOJA, Y NO ES UN OLVIDO.",
            9.5,
            "#8a5200",
            "start",
            "bold",
        )
    )
    p.append(
        _texto(
            46,
            803,
            "Se buscan en el banco R2 moviendo las paletas en su ranura, y se anotan como "
            "cotas de puesta a punto en el dossier.",
            9,
            "#8a5200",
            "start",
        )
    )
    p.append(
        f'<rect x="34" y="832" width="1112" height="52" fill="none" stroke="{TINTA}" '
        'stroke-width="1.2"/>'
    )
    campos = [
        ("N\u00famero", "2.2"),
        ("Material", "Abedul 4 mm"),
        ("Espesor", f"{espesor:.0f} mm"),
        ("Cantidad", "1 cuerpo"),
        ("Paletas", "2, postizas"),
        ("Tablero", f"{caja_an:.0f} \u00d7 {caja_al:.0f}"),
        ("Conjunto", "Escape \u00b7 R2"),
        ("Estado", "PENDIENTE \u00b7 R2"),
    ]
    celda = 1112 / len(campos)
    for i, (k, val) in enumerate(campos):
        bxx = 34 + i * celda
        p.append(
            f'<path d="M{bxx:.1f} 832h{celda:.1f}v52h-{celda:.1f}z" fill="none" '
            f'stroke="{AUX}" stroke-width="0.6"/>'
        )
        p.append(_texto(bxx + 10, 850, k.upper(), 7.5, AUX, "start"))
        p.append(_texto(bxx + 10, 869, val, 10.5, TINTA, "start", "bold"))
    p.append("</svg>")
    return "\n".join(p)


PIEZAS = {
    "varilla": varilla,
    "lenteja": lenteja,
    "soporte": soporte,
    "muelle": muelle,
    "escuadra": escuadra,
    "rueda_escape": rueda_escape,
    "ancora": ancora,
}

PREFIJOS = {
    "varilla": ("varilla_",),
    "lenteja": ("lenteja_",),
    "vastago": ("vastago_",),
    "soporte": ("soporte_", "anclaje_"),
    "muelle": ("muelle_",),
    "escuadra": ("escuadra_",),
    "rueda_escape": ("rueda_escape_",),
    "ancora": ("ancora_",),
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
        "soporte_placa_alto",
        "varilla_taladro_diametro",
        "varilla_ancho",
        "varilla_taladro_cerca",
        "varilla_taladro_lejos",
    ),
    "lenteja": ("vastago_diametro", "vastago_saliente", "longitud_pendulo_nominal"),
    "rueda_escape": ("dientes_escape", "abarque_ancora", "eje_diametro", "vuelta_rueda_escape"),
    "ancora": (
        "rueda_escape_diametro",
        "rueda_escape_diametro_fondo",
        "abarque_ancora",
        "amplitud_nominal",
    ),
    "escuadra": (
        "anclaje_tornillo_separacion",
        "anclaje_tornillo_diametro",
        "anclaje_al_datum",
        "soporte_ancho",
        "soporte_alto",
    ),
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
