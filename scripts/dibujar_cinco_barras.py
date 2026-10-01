"""El cinco barras y la palanca del lápiz, acotados desde el contrato.

    uv run python scripts/dibujar_cinco_barras.py --out build/cinco_barras.svg

Como el cabestrante, son piezas de **plataforma**: se dibujan a mano en el CAD,
una vez, y no cambian entre pedidos. Lo que sale de aquí es la hoja que se
tiene al lado mientras se dibujan.

**Lo que esta hoja acota son las distancias entre ejes, no el contorno.** Un
brazo de cinco barras es, para la cinemática, una distancia entre dos
agujeros: lo demás —ancho, espesor, material, cómo se alivia— es diseño y no
cambia ni un número de los que calcula el compilador. Donde el contorno hace
falta y no está decidido, el panel lo dice en vez de inventarlo.

Se dibuja la postura con la punta en el **centro de la caja**, que no es una
postura cualquiera: es la referencia del calaje, el ángulo al que se monta
cada brazo sobre su eje. Montarlo a otro ángulo escribe basura.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
import textwrap
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np

from compile.escribiente import Escribiente
from scripts.exportar_para_cad import mapa_de

RAIZ = Path(__file__).resolve().parent.parent
CONTRATOS = RAIZ / "docs" / "contratos.json"
MM = 1000.0
CABECERA = 34.0
PIE = 44.0
"""Lo que se reserva bajo el dibujo: las cotas y el aviso, que puede ir a dos
líneas. Un rótulo obligatorio no se recorta: o se envuelve o se le hace
sitio."""
ANCHO_AVISO = 74
"""Caracteres por línea del aviso, para el cuerpo de 5 px en un panel de 230."""

ESTILO = """
text{font-family:Helvetica,Arial,sans-serif;fill:#1b1b1b}
.h1{font-size:11px;font-weight:bold}
.sub{font-size:5.8px;fill:#555}
.pieza{font-size:6.6px;font-weight:bold;text-anchor:middle}
.ref{font-size:5px;fill:#666;text-anchor:middle}
.var{font-size:4.9px;fill:#1b5fb0;font-family:monospace}
.val{font-size:5px;fill:#b03030;text-anchor:end}
.aviso{font-size:5px;fill:#8a4a00}
.raya{stroke:#e0e0e0;stroke-width:0.5}
.marco{fill:none;stroke:#ddd;stroke-width:0.6}
.cota{font-size:5px;fill:#b03030;text-anchor:middle}
.rotulo{font-size:5px;fill:#1b5fb0;text-anchor:middle}
.rotuloi{font-size:5px;fill:#1b5fb0;text-anchor:end}
.barra{stroke:#1b1b1b;stroke-width:2.2;stroke-linecap:round}
.barra2{stroke:#6a86a8;stroke-width:2.2;stroke-linecap:round}
.caja{fill:none;stroke:#b03030;stroke-width:0.7;stroke-dasharray:4 2}
.perno{fill:#fff;stroke:#1b1b1b;stroke-width:0.9}
.anclado{fill:#1b1b1b}
.corte{fill:#d9e2ef;stroke:#1b1b1b;stroke-width:0.8}
.eje{stroke:#1b5fb0;stroke-width:0.6;stroke-dasharray:6 2 1 2}
"""


def contrato() -> dict[str, float]:
    datos = json.loads(CONTRATOS.read_text(encoding="utf-8"))
    return {v["nombre"]: float(v["valor"]) for g in datos["contratos"] for v in g["valores"]}


def postura(maquina: Escribiente) -> dict[str, np.ndarray]:
    """Los cinco puntos del varillaje con la punta en el centro de la caja.

    Es la postura del calaje: la referencia con la que se monta cada brazo
    sobre su eje. Sale de la cinemática del propio compilador, no de medir
    sobre un dibujo, para que no puedan discrepar.
    """
    brazo = maquina.brazo
    centro = np.array([[0.0, float(maquina.caja_centro_y)]])
    psi = brazo.inversa(centro)
    codos = [
        pivote + float(maquina.proximal) * np.array([np.cos(psi[0, i]), np.sin(psi[0, i])])
        for i, pivote in enumerate((brazo.pivote_izquierdo, brazo.pivote_derecho))
    ]
    return {
        "pivote_izq": brazo.pivote_izquierdo,
        "pivote_der": brazo.pivote_derecho,
        "codo_izq": codos[0],
        "codo_der": codos[1],
        "punta": centro[0],
    }


def varillaje(
    c: dict[str, float], maquina: Escribiente, x: float, y: float, ancho: float, alto: float
) -> list[str]:
    """La planta del cinco barras en la postura de calaje."""
    p = postura(maquina)
    xs = [v[0] * MM for v in p.values()]
    ys = [v[1] * MM for v in p.values()]
    media_caja = c["caja_ancho"] * MM / 2.0
    minx, maxx = min(xs) - media_caja, max(xs) + media_caja
    miny, maxy = min(ys), max(ys) + c["caja_alto"] * MM
    hueco = alto - CABECERA - PIE
    k = min(ancho * 0.86 / (maxx - minx), hueco / (maxy - miny))
    ox = x + ancho / 2 - (minx + maxx) / 2 * k
    oy = y + CABECERA + hueco / 2 + (miny + maxy) / 2 * k

    def pt(v: np.ndarray) -> tuple[float, float]:
        return ox + v[0] * MM * k, oy - v[1] * MM * k

    d = [
        f'<text class="pieza" x="{x + ancho / 2:.1f}" y="{y + 12:.1f}">'
        "cinco barras · postura de calaje</text>",
        f'<text class="ref" x="{x + ancho / 2:.1f}" y="{y + 20:.1f}">'
        "la punta en el centro de la caja, que es la referencia con la que se "
        f"monta cada brazo · escala {k:.2f}:1</text>",
    ]
    cx, cy = pt(p["punta"])
    d.append(
        f'<rect class="caja" x="{cx - media_caja * k:.2f}" '
        f'y="{cy - c["caja_alto"] * MM * k / 2:.2f}" '
        f'width="{c["caja_ancho"] * MM * k:.2f}" height="{c["caja_alto"] * MM * k:.2f}"/>'
    )
    for a, b, clase in (
        ("pivote_izq", "codo_izq", "barra"),
        ("pivote_der", "codo_der", "barra"),
        ("codo_izq", "punta", "barra2"),
        ("codo_der", "punta", "barra2"),
    ):
        (x0, y0), (x1, y1) = pt(p[a]), pt(p[b])
        d.append(f'<line class="{clase}" x1="{x0:.2f}" y1="{y0:.2f}" x2="{x1:.2f}" y2="{y1:.2f}"/>')
    for nombre, clase in (
        ("pivote_izq", "anclado"),
        ("pivote_der", "anclado"),
        ("codo_izq", "perno"),
        ("codo_der", "perno"),
        ("punta", "perno"),
    ):
        px, py = pt(p[nombre])
        d.append(f'<circle class="{clase}" cx="{px:.2f}" cy="{py:.2f}" r="2.6"/>')

    izq, der = pt(p["pivote_izq"]), pt(p["pivote_der"])
    codo = pt(p["codo_izq"])
    d += [
        f'<text class="cota" x="{(izq[0] + der[0]) / 2:.1f}" y="{izq[1] + 11:.1f}">'
        f"separación {c['brazo_separacion'] * MM:g} entre los dos pivotes anclados</text>",
        f'<text class="cota" x="{x + ancho / 2:.1f}" y="{izq[1] + 19:.1f}">'
        "los puntos negros son los dos ejes anclados al bastidor</text>",
        # Los dos proximales SE CRUZAN —codos hacia fuera—, así que el punto
        # medio de uno cae encima del otro. El rótulo va fuera del varillaje.
        f'<text class="rotuloi" x="{izq[0] - 6:.1f}" y="{izq[1] - 6:.1f}">'
        f"proximal {c['brazo_proximal'] * MM:g}</text>",
        f'<text class="rotulo" x="{(cx + codo[0]) / 2 - 12:.1f}" '
        f'y="{(cy + codo[1]) / 2:.1f}">distal {c["brazo_distal"] * MM:g}</text>',
        f'<text class="cota" x="{cx:.1f}" y="{cy - c["caja_alto"] * MM * k / 2 - 5:.1f}">'
        f"caja {c['caja_ancho'] * MM:g} × {c['caja_alto'] * MM:g}, "
        f"centro a {c['caja_centro_y'] * MM:g} sobre la línea de pivotes</text>",
    ]
    return d


def barra(
    c: dict[str, float], cual: str, x: float, y: float, ancho: float, alto: float
) -> list[str]:
    """Una barra: dos agujeros a una distancia, y el contorno sin definir."""
    largo = c[f"brazo_{cual}"] * MM
    agujeros = {
        "proximal": (c["brazo_eje_diametro"] * MM, 6.0),
        "distal": (6.0, 6.0),
        "palanca": (c["brazo_eje_diametro"] * MM, 6.0),
    }[cual]
    titulos = {
        "proximal": ("brazo proximal · x2", "va calado en el eje del pivote anclado"),
        "distal": ("brazo distal · x2", "flota entre el codo y la punta: dos pernos y ya"),
        "palanca": ("palanca del lápiz · x1", "levanta la punta; su eje es el del tercer canal"),
    }[cual]
    hueco = alto - CABECERA - PIE - 9.0 * len(filas(c, cual))
    k = min(ancho * 0.80 / largo, hueco / max(agujeros) / 2.2, 3.0)
    cy = y + CABECERA + hueco / 2
    x0 = x + ancho / 2 - largo * k / 2
    ancho_barra = min(max(agujeros) * 1.7 * k, hueco * 0.5)

    d = [
        f'<text class="pieza" x="{x + ancho / 2:.1f}" y="{y + 12:.1f}">{titulos[0]}</text>',
        f'<text class="ref" x="{x + ancho / 2:.1f}" y="{y + 20:.1f}">{titulos[1]}</text>',
        f'<rect class="corte" x="{x0 - ancho_barra / 2:.2f}" y="{cy - ancho_barra / 2:.2f}" '
        f'width="{largo * k + ancho_barra:.2f}" height="{ancho_barra:.2f}" '
        f'rx="{ancho_barra / 2:.2f}"/>',
    ]
    for i, diametro in enumerate(agujeros):
        px = x0 + i * largo * k
        d += [
            f'<circle class="perno" cx="{px:.2f}" cy="{cy:.2f}" r="{diametro * k / 2:.2f}"/>',
            f'<line class="eje" x1="{px:.2f}" y1="{cy - ancho_barra:.2f}" '
            f'x2="{px:.2f}" y2="{cy + ancho_barra:.2f}"/>',
            f'<text class="cota" x="{px:.1f}" y="{cy + ancho_barra + 8:.1f}">Ø{diametro:g}</text>',
        ]
    d.append(
        f'<text class="cota" x="{x + ancho / 2:.1f}" y="{cy + ancho_barra + 17:.1f}">'
        f"entre centros {largo:g}</text>"
    )
    return d


def filas(c: dict[str, float], cual: str) -> list[tuple[str, str]]:
    """Lo que se teclea en el CAD, con el prefijo del mapa que lo contiene."""
    cota, angulo = mapa_de("variables_cota"), mapa_de("variables_angulo")
    comun = [(f"#{cota}.brazo_{cual}", f"{c[f'brazo_{cual}'] * MM:g}")]
    if cual == "proximal":
        return [
            *comun,
            (f"#{cota}.brazo_eje_diametro", f"{c['brazo_eje_diametro'] * MM:g}"),
            (f"#{angulo}.calaje_izquierdo", f"{math.degrees(c['calaje_izquierdo']):.3f}"),
            (f"#{angulo}.calaje_derecho", f"{math.degrees(c['calaje_derecho']):.3f}"),
        ]
    if cual == "palanca":
        return [
            *comun,
            (f"#{cota}.brazo_eje_diametro", f"{c['brazo_eje_diametro'] * MM:g}"),
            (f"#{angulo}.calaje_elevador", f"{math.degrees(c['calaje_elevador']):.3f}"),
        ]
    return comun


AVISOS = {
    "varillaje": (
        "Las dos ramas tienen dos soluciones por punto: los codos van HACIA FUERA, "
        "y esa elección se mantiene todo el ciclo."
    ),
    "proximal": (
        "El calaje no es una preferencia de montaje: con otro ángulo la máquina "
        "escribe basura. Está congelado."
    ),
    "distal": (
        "Ancho, espesor y material SIN DEFINIR: no cambian ningún número del "
        "compilador. Los agujeros de Ø6 tampoco están en el contrato."
    ),
    "palanca": (
        "El tercer canal solo sube y baja el lápiz: su error no desplaza el trazo, "
        "lo levanta antes o después."
    ),
}


def panel(
    c: dict[str, float],
    maquina: Escribiente,
    cual: str,
    x: float,
    y: float,
    ancho: float,
    alto: float,
) -> list[str]:
    d = [
        f'<rect class="marco" x="{x:.1f}" y="{y:.1f}" '
        f'width="{ancho:.1f}" height="{alto:.1f}" rx="3"/>'
    ]
    if cual == "varillaje":
        d += varillaje(c, maquina, x, y, ancho, alto)
    else:
        d += barra(c, cual, x, y, ancho, alto)
        fila = y + alto - 18.0 - 9.0 * len(filas(c, cual))
        d.append(
            f'<line class="raya" x1="{x + 4:.1f}" y1="{fila - 8:.1f}" '
            f'x2="{x + ancho - 4:.1f}" y2="{fila - 8:.1f}"/>'
        )
        for variable, valor in filas(c, cual):
            d.append(f'<text class="var" x="{x + 5:.1f}" y="{fila:.1f}">{variable}</text>')
            d.append(f'<text class="val" x="{x + ancho - 5:.1f}" y="{fila:.1f}">{valor}</text>')
            fila += 9.0
    lineas = textwrap.wrap(AVISOS[cual], ANCHO_AVISO)
    for i, linea in enumerate(reversed(lineas)):
        d.append(
            f'<text class="aviso" x="{x + 5:.1f}" y="{y + alto - 7 - 7.5 * i:.1f}">{linea}</text>'
        )
    return d


def hoja() -> str:
    c, maquina = contrato(), Escribiente()
    ancho, alto, borde = 230.0, 196.0, 12.0
    w, h = borde * 2 + 2 * ancho, 48 + 2 * alto + borde
    partes = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{w * 2:.0f}" height="{h * 2:.0f}" '
        f'viewBox="0 0 {w:.0f} {h:.0f}">',
        f"<style>{ESTILO}</style>",
        f'<rect width="{w:.0f}" height="{h:.0f}" fill="#fff"/>',
        f'<text class="h1" x="{borde}" y="20">Cinco barras y palanca · piezas de plataforma</text>',
    ]
    intro = (
        "Generado desde docs/contratos.json con scripts/dibujar_cinco_barras.py. Se acotan "
        "las DISTANCIAS ENTRE EJES; el contorno de cada barra es diseño y no cambia ningún "
        "número del compilador. El marco del varillaje va en "
        f"({c['brazo_origen_x'] * MM:.3f}, {c['brazo_origen_y'] * MM:.3f}) y girado "
        f"{math.degrees(c['brazo_orientacion']):g}° respecto del marco de la leva."
    )
    for i, linea in enumerate(textwrap.wrap(intro, 150)):
        partes.append(f'<text class="sub" x="{borde}" y="{30 + 8 * i}">{linea}</text>')
    for i, cual in enumerate(("varillaje", "proximal", "distal", "palanca")):
        partes += panel(
            c, maquina, cual, borde + (i % 2) * ancho, 48 + (i // 2) * alto, ancho, alto
        )
    partes.append("</svg>")
    return "\n".join(partes) + "\n"


def main(argv: list[str] | None = None) -> int:
    partes = argparse.ArgumentParser(description=__doc__)
    partes.add_argument("--out", type=Path, default=Path("build/cinco_barras.svg"))
    opciones = partes.parse_args(argv)
    opciones.out.parent.mkdir(parents=True, exist_ok=True)
    opciones.out.write_text(hoja(), encoding="utf-8")
    print(f"cinco barras en {opciones.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
