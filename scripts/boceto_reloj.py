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

    La primera del reloj cuyo contorno **se genera** en vez de dibujarse: los
    treinta dientes salen del paso angular y de la inclinacion, asi que tocar
    `dientes_escape` los redibuja todos. Eso es lo que hace que la rueda sea
    parametrica de verdad y no un dibujo con un numero al lado.
    """
    r = c.contrato("rueda_escape")
    diam = r.valor("rueda_escape_diametro").en_mm
    fondo = r.valor("rueda_escape_diametro_fondo").en_mm
    altura = r.valor("rueda_escape_altura_diente").en_mm
    paso = r.valor("rueda_escape_paso_diente").en_mm
    espesor = r.valor("rueda_escape_espesor").en_mm
    cubo = r.valor("rueda_escape_cubo_diametro").en_mm
    eje = r.valor("rueda_escape_eje_diametro").en_mm
    inclinacion = r.valor("rueda_escape_inclinacion_diente").valor
    angular = r.valor("rueda_escape_paso_angular").valor
    dientes = int(c.valor("escape", "dientes_escape").valor)
    abarca = c.valor("escape", "abarque_ancora").valor

    e = 1.8
    p: list[str] = [CABEZA.format(cota=COTA, ancho=900, alto=700)]
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

    cx, cy = 300.0, 300.0
    rp, rf = diam * e / 2.0, fondo * e / 2.0

    def polar(radio: float, ang: float) -> tuple[float, float]:
        return cx + radio * math.cos(ang), cy + radio * math.sin(ang)

    # El contorno completo, diente a diente. Cada uno sale del fondo, sube a
    # la punta inclinada en el sentido de giro y vuelve al fondo del
    # siguiente: la cara de ataque es la corta, el dorso la larga.
    # La inclinacion es el angulo de la CARA con el radio, no un angulo
    # central: la punta se desplaza `altura x tan(inclinacion)` de arco, que
    # con 8 grados es 1 mm y no 6. Leerla como angulo central daba una cara a
    # 44 grados del radio, que es otro diente.
    desvio = altura * e * math.tan(inclinacion) / rp
    trozos: list[str] = []
    for i in range(dientes):
        a0 = i * angular
        x0, y0 = polar(rf, a0)
        x1, y1 = polar(rp, a0 + angular - desvio)
        x2, y2 = polar(rf, a0 + angular)
        trozos.append(f"{'M' if i == 0 else 'L'}{x0:.2f} {y0:.2f}")
        trozos.append(f"L{x1:.2f} {y1:.2f}")
        trozos.append(f"L{x2:.2f} {y2:.2f}")
    p.append(f'<path d="{" ".join(trozos)}Z" fill="none" stroke="{TINTA}" stroke-width="1.4"/>')
    for radio, trazo in ((rf, "3 3"), (cubo * e / 2.0, "4 2")):
        p.append(
            f'<circle cx="{cx}" cy="{cy}" r="{radio:.1f}" fill="none" stroke="{AUX}" '
            f'stroke-width="0.8" stroke-dasharray="{trazo}"/>'
        )
    p.append(
        f'<circle cx="{cx}" cy="{cy}" r="{eje * e / 2.0:.1f}" fill="none" stroke="{TINTA}" '
        f'stroke-width="1.4"/>'
    )
    for ang in (0.0, math.pi / 2.0):
        dx, dy = math.cos(ang) * (rp + 16), math.sin(ang) * (rp + 16)
        p.append(
            f'<path d="M{cx - dx:.1f} {cy - dy:.1f}L{cx + dx:.1f} {cy + dy:.1f}" '
            f'stroke="{AUX}" stroke-width="0.6" stroke-dasharray="10 3 2 3"/>'
        )

    # El sector que abarca el ancora, que es de donde sale su tamano.
    a_ini, a_fin = math.radians(-135.0), math.radians(-135.0) + abarca * angular
    xa, ya = polar(rp, a_ini)
    xb, yb = polar(rp, a_fin)
    p.append(
        f'<path d="M{cx} {cy}L{xa:.1f} {ya:.1f}A{rp:.1f} {rp:.1f} 0 0 1 {xb:.1f} {yb:.1f}Z" '
        f'fill="{COTA}" fill-opacity="0.08" stroke="{COTA}" stroke-width="0.9" '
        f'stroke-dasharray="5 3"/>'
    )
    xm, ym = polar(rp * 0.66, (a_ini + a_fin) / 2.0)
    p.append(_texto(xm, ym, f"{abarca:g} dientes", 8.5, COTA, peso="bold"))
    p.append(_texto(xm, ym + 11, "lo que abarca el \u00e1ncora", 7.5, COTA))
    p.append(_texto(xm, ym + 21, "#num.abarque_ancora", 7.5, AUX))

    # Sin decir desde donde se mira, un disco plano no tiene sentido de giro:
    # volteado, los dientes miran al otro lado.
    ra = rp + 30
    p.append(
        f'<path d="M{cx + ra * math.cos(math.radians(-60)):.1f} '
        f"{cy + ra * math.sin(math.radians(-60)):.1f}A{ra:.1f} {ra:.1f} 0 0 1 "
        f"{cx + ra * math.cos(math.radians(-20)):.1f} "
        f'{cy + ra * math.sin(math.radians(-20)):.1f}" stroke="{COTA}" stroke-width="1.4" '
        f'fill="none" marker-end="url(#f)"/>'
    )
    p.append(
        _texto(
            cx + ra * math.cos(math.radians(-40)) + 10,
            cy + ra * math.sin(math.radians(-40)),
            "giro",
            8,
            COTA,
            "start",
            "bold",
        )
    )
    p.append(_texto(cx - rp - 40, 92, "LA RUEDA \u00b7 escala 1,8:1", 9, TINTA, "start"))
    p.append(
        _texto(
            cx - rp - 40,
            105,
            f"{dientes} dientes generados del paso \u00b7 VISTA DESDE LA ESFERA",
            8,
            AUX,
            "start",
        )
    )
    p.append(
        _cota_v(
            cy - rp,
            cy + rp,
            cx - rp - 40,
            f"\u00d8{diam:.0f}",
            "#cota.rueda_escape_diametro",
            desde=cx - rp,
        )
    )
    p.append(
        _cota_v(
            cy - rf,
            cy + rf,
            cx + rp + 40,
            f"\u00d8{fondo:.0f}",
            "#cota.rueda_escape_diametro_fondo",
            desde=cx + rf,
            lado="der",
        )
    )
    p.append(
        _cota_h(
            cx - cubo * e / 2.0,
            cx + cubo * e / 2.0,
            cy + rp + 56,
            f"\u00d8{cubo:.0f}",
            "#cota.rueda_escape_cubo_diametro",
        )
    )
    p.append(
        f'<path d="M{cx - eje * e / 2.0:.1f} {cy:.1f}l-50 60h-30" stroke="{COTA}" '
        f'stroke-width="1" fill="none"/>'
    )
    p.append(
        _texto(cx - eje * e / 2.0 - 84, cy + 56, f"\u00d8{eje:.0f} H7", 9.5, COTA, "end", "bold")
    )
    p.append(
        _texto(cx - eje * e / 2.0 - 84, cy + 66, "#cota.rueda_escape_eje_diametro", 7.5, AUX, "end")
    )

    # ---- detalle del diente ----------------------------------------------
    dx0, dy0 = 720.0, 250.0
    f2 = 10.0
    p.append(_texto(dx0 - 40, 92, "UN DIENTE \u00b7 escala 10:1", 9, TINTA, "start"))
    p.append(_texto(dx0 - 40, 105, "el sentido de giro va a la derecha", 8, AUX, "start"))
    base = paso * f2
    alto = altura * f2
    # El dorso sube despacio desde el fondo hasta casi el siguiente fondo; la
    # cara cae en vertical, inclinada `inclinacion` del radio. Es el mismo
    # diente que genera la vista de planta, visto desenrollado.
    sesgo = math.tan(inclinacion) * alto
    p.append(
        f'<path d="M{dx0 - base:.1f} {dy0:.1f}L{dx0 - sesgo:.1f} {dy0 - alto:.1f}'
        f"L{dx0:.1f} {dy0:.1f}L{dx0 + base - sesgo:.1f} {dy0 - alto:.1f}"
        f'L{dx0 + base:.1f} {dy0:.1f}" fill="none" stroke="{TINTA}" stroke-width="1.6"/>'
    )
    p.append(
        f'<path d="M{dx0 - base - 20:.1f} {dy0:.1f}H{dx0 + base + 20:.1f}" stroke="{AUX}" '
        f'stroke-width="0.8" stroke-dasharray="4 2"/>'
    )
    p.append(_texto(dx0 + base + 24, dy0 + 3, "el fondo", 8, AUX, "start"))
    # El angulo se mide entre la cara de ataque y el radio, que en esta vista
    # es la vertical. Marcarlo en la punta y no en la base es lo que hace que
    # se entienda que lo que se inclina es la punta.
    xr = dx0
    p.append(
        f'<path d="M{xr:.1f} {dy0 + 14:.1f}V{dy0 - alto - 34:.1f}" stroke="{AUX}" '
        f'stroke-width="0.6" stroke-dasharray="6 3"/>'
    )
    p.append(
        f'<path d="M{xr:.1f} {dy0 - alto - 34:.1f}A34 34 0 0 0 '
        f"{xr - 34 * math.sin(inclinacion):.1f} "
        f'{dy0 - alto - 34 + 34 * (1 - math.cos(inclinacion)):.1f}" stroke="{COTA}" '
        f'stroke-width="1" fill="none"/>'
    )
    p.append(
        _texto(
            xr - 8,
            dy0 - alto - 40,
            f"{math.degrees(inclinacion):.0f}\u00b0 de la cara al radio",
            9.5,
            COTA,
            "end",
            "bold",
        )
    )
    p.append(
        _texto(
            xr - 8,
            dy0 - alto - 30,
            "#angulo.rueda_escape_inclinacion_diente",
            7.5,
            AUX,
            "end",
        )
    )
    p.append(_texto(xr - 6, dy0 + 16, "cara de ataque", 7.5, COTA, "end"))
    p.append(_texto(dx0 + base / 2.0, dy0 + 16, "el dorso, que no toca", 7.5, AUX))
    p.append(
        _cota_v(
            dy0 - alto,
            dy0,
            dx0 - base - 44,
            f"{altura:.0f}",
            "#cota.rueda_escape_altura_diente",
            desde=dx0 - base,
        )
    )
    p.append(_cota_h(dx0 - base, dx0, dy0 + 70, f"{paso:.1f}", "#cota.rueda_escape_paso_diente"))
    p.append(
        _texto(
            dx0 - base,
            dy0 + 108,
            "el paso es de ARCO, no de cuerda: se mide sobre el c\u00edrculo de punta",
            8,
            AUX,
            "start",
        )
    )
    p.append(
        _texto(
            dx0 - base,
            dy0 + 122,
            f"{math.degrees(angular):.0f}\u00b0 por diente \u00b7 "
            "#angulo.rueda_escape_paso_angular",
            8,
            AUX,
            "start",
        )
    )

    p.append(
        '<rect x="34" y="520" width="832" height="46" rx="4" fill="#fff4e5" '
        'stroke="#d98324" stroke-width="1"/>'
    )
    p.append(
        _texto(
            46,
            539,
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
            555,
            "Un disco plano se monta del rev\u00e9s sin que se note y los dientes miran "
            "al otro lado: si el escape no engancha, se voltea la rueda.",
            9,
            "#8a5200",
            "start",
        )
    )
    p.append(
        f'<rect x="34" y="584" width="832" height="52" fill="none" stroke="{TINTA}" '
        'stroke-width="1.2"/>'
    )
    campos = [
        ("N\u00famero", "2.1"),
        ("Material", "Abedul 4 mm"),
        ("Espesor", f"{espesor:.0f} mm"),
        ("Cantidad", "1"),
        ("Dientes", f"{dientes}"),
        ("Conjunto", "Escape \u00b7 banco R2"),
        ("Estado", "PENDIENTE \u00b7 R2"),
    ]
    celda = 832 / len(campos)
    for i, (k, val) in enumerate(campos):
        bx = 34 + i * celda
        p.append(
            f'<path d="M{bx:.1f} 584h{celda:.1f}v52h-{celda:.1f}z" fill="none" '
            f'stroke="{AUX}" stroke-width="0.6"/>'
        )
        p.append(_texto(bx + 10, 602, k.upper(), 7.5, AUX, "start"))
        p.append(_texto(bx + 10, 621, val, 10.5, TINTA, "start", "bold"))
    p.append("</svg>")
    return "\n".join(p)


PIEZAS = {
    "varilla": varilla,
    "lenteja": lenteja,
    "soporte": soporte,
    "muelle": muelle,
    "escuadra": escuadra,
    "rueda_escape": rueda_escape,
}

PREFIJOS = {
    "varilla": ("varilla_",),
    "lenteja": ("lenteja_",),
    "vastago": ("vastago_",),
    "soporte": ("soporte_", "anclaje_"),
    "muelle": ("muelle_",),
    "escuadra": ("escuadra_",),
    "rueda_escape": ("rueda_escape_",),
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
