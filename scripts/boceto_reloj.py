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
from scripts.exportar_variables import NOMBRE_MAPA, conversion_de

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


def _cota_v(
    y0: float, y1: float, x: float, etiqueta: str, variable: str, desde: float | None = None
) -> str:
    """Cota vertical. `desde` es el borde de la pieza, para que la linea de
    referencia llegue hasta ella en vez de quedarse en el aire."""
    medio = (y0 + y1) / 2
    a = x - 4 if desde is None else min(x - 4, desde)
    b = x + 22 if desde is None else max(x + 6, desde)
    return "".join(
        [
            f'<path d="M{a:.1f} {y0:.1f}H{b:.1f}" stroke="{AUX}" stroke-width="0.6"/>',
            f'<path d="M{a:.1f} {y1:.1f}H{b:.1f}" stroke="{AUX}" stroke-width="0.6"/>',
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
    vastago_d = c.valor("pendulo", "varilla_vastago_diametro").en_mm
    vastago_p = c.valor("pendulo", "varilla_vastago_profundidad").en_mm
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
            f"40 sobre el punto de flexión + 950 de varilla + 44 al centro de la "
            f"lenteja = {nominal:.0f} mm de péndulo",
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

    p: list[str] = [CABEZA.format(cota=COTA)]
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


PIEZAS = {"varilla": varilla, "lenteja": lenteja}

PREFIJOS = {"varilla": ("varilla_",), "lenteja": ("lenteja_",), "vastago": ("vastago_",)}
"""Que cotas son de cada pieza. El prefijo del nombre decide, igual que
decide el gemelo de radio: asi se puede leer el contrato y saber de quien es
cada cota sin conocer el conjunto."""

INTERFACES = {
    "varilla": ("vastago_diametro", "longitud_pendulo_nominal"),
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


def main(argv: list[str] | None = None) -> int:
    partes = argparse.ArgumentParser(prog="boceto_reloj", description=__doc__)
    partes.add_argument("--pieza", default="varilla", choices=sorted(PREFIJOS))
    partes.add_argument("--tabla", action="store_true", help="la tabla de cotas, en markdown")
    partes.add_argument("--contratos", type=Path, default=RELOJ)
    partes.add_argument("--out", type=Path, default=None)
    opciones = partes.parse_args(argv)

    contratos = cargar(opciones.contratos)
    if opciones.tabla:
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
    nombre = (
        f"boceto-{opciones.pieza}.svg" if sufijo == "boceto.svg" else f"cotas-{opciones.pieza}.md"
    )
    ruta = opciones.out / nombre
    ruta.write_text(texto, encoding="utf-8")
    print(f"escrito {ruta}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
