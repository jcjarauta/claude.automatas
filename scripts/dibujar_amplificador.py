"""El cabestrante 8:1, acotado desde el contrato, para dibujarlo en el CAD.

    uv run python scripts/dibujar_amplificador.py --out build/amplificador.svg

**El sector y el tambor son piezas de la PLATAFORMA**, así que por el reparto
con Onshape se dibujan allí a mano y una sola vez; no los genera el
compilador. Lo que sale de aquí no es geometría de producción, es la hoja que
se tiene al lado mientras se dibujan: la planta con los dos ejes a escala, la
sección de cada pieza y el nombre entero de cada variable.

Todo sale de `docs/contratos.json`. Si un número de esta hoja no cuadra con
el CAD, el que manda es el contrato.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.exportar_para_cad import mapa_de

RAIZ = Path(__file__).resolve().parent.parent
CONTRATOS = RAIZ / "docs" / "contratos.json"
MM = 1000.0
CABECERA = 34.0
"""Lo que ocupan el título y los dos rótulos de arriba."""
PIE_SIN_LISTA = 34.0
"""Lo que hay que reservar bajo el dibujo aunque no haya lista de
variables: dos líneas de cota y el aviso. Sin reservarlo, el dibujo se sale
del panel y pisa al de abajo, que es justo lo que pasó la primera vez."""

ESTILO = """
text{font-family:Helvetica,Arial,sans-serif;fill:#1b1b1b}
.h1{font-size:11px;font-weight:bold}
.sub{font-size:5.8px;fill:#555}
.pieza{font-size:6.6px;font-weight:bold;text-anchor:middle}
.ref{font-size:5px;fill:#666;text-anchor:middle}
.var{font-size:4.9px;fill:#1b5fb0;font-family:monospace}
.val{font-size:5px;fill:#b03030;text-anchor:end}
.aviso{font-size:5px;fill:#8a4a00}
.nota{font-size:5px;fill:#2f6f4f}
.escala{font-size:5.2px;fill:#b03030}
.esq{text-anchor:end}
.raya{stroke:#e0e0e0;stroke-width:0.5}
.corte{fill:#d9e2ef;stroke:#1b1b1b;stroke-width:0.8}
.cinta{fill:none;stroke:#b03030;stroke-width:1.4;stroke-linecap:round}
.eje{stroke:#1b5fb0;stroke-width:0.6;stroke-dasharray:6 2 1 2}
.ref1{stroke:#999;stroke-width:0.5;stroke-dasharray:3 2}
.marco{fill:none;stroke:#ddd;stroke-width:0.6}
.cota{font-size:5px;fill:#b03030;text-anchor:middle}
"""


def contrato() -> dict[str, float]:
    """Todos los valores del contrato, por nombre, en unidades SI."""
    datos = json.loads(CONTRATOS.read_text(encoding="utf-8"))
    return {v["nombre"]: float(v["valor"]) for g in datos["contratos"] for v in g["valores"]}


def planta(c: dict[str, float], x: float, y: float, ancho: float, alto: float) -> list[str]:
    """Los dos ejes vistos desde arriba, con la cinta entre ellos.

    Es la vista que dice lo único que no se deduce de las secciones: que la
    cinta sale **tangente** de los dos y que el entre-ejes no lo fija ninguna
    relación de diámetros.
    """
    radio_s = c["amplificador_sector_radio"] * MM
    radio_t = c["amplificador_tambor_radio"] * MM
    entre = c["amplificador_entre_ejes"] * MM
    arriba, hueco = y + CABECERA, alto - CABECERA - PIE_SIN_LISTA
    k = min(ancho * 0.80 / (entre + radio_s + radio_t), hueco / (2 * radio_s))
    cx = x + ancho / 2 - (entre / 2) * k
    cy = arriba + hueco / 2
    tx = cx + entre * k

    # Tangente exterior común a dos circunferencias de radios distintos. El
    # radio al punto de tangencia es PERPENDICULAR a la cinta, así que cae a
    # 90° + gamma de la dirección al otro eje, con sin(gamma) = (R-r)/a — es
    # decir, DETRÁS del centro, no delante. Dibujarlo con acos lo pone en el
    # lado equivocado y hace parecer que basta un sector de ±25°, cuando la
    # tangencia está a ±126°.
    beta = math.pi / 2 + math.asin((radio_s - radio_t) / entre)
    d = [
        f'<text class="pieza" x="{x + ancho / 2:.1f}" y="{y + 12:.1f}">'
        "planta · el cabestrante entero</text>",
        f'<text class="ref" x="{x + ancho / 2:.1f}" y="{y + 20:.1f}">'
        f"sector R{radio_s:g} y tambor R{radio_t:g} de fibra neutra · "
        f"entre-ejes {entre:g} · relación {radio_s / radio_t:.0f}:1 exacta</text>",
        f'<circle class="corte" cx="{cx:.2f}" cy="{cy:.2f}" r="{radio_s * k:.2f}"/>',
        f'<circle class="corte" cx="{tx:.2f}" cy="{cy:.2f}" r="{radio_t * k:.2f}"/>',
        f'<line class="eje" x1="{cx - radio_s * k - 5:.2f}" y1="{cy:.2f}" '
        f'x2="{tx + radio_t * k + 5:.2f}" y2="{cy:.2f}"/>',
    ]
    for signo in (-1, 1):
        d.append(
            f'<line class="cinta" x1="{cx + radio_s * k * math.cos(beta):.2f}" '
            f'y1="{cy + signo * radio_s * k * math.sin(beta):.2f}" '
            f'x2="{tx + radio_t * k * math.cos(beta):.2f}" '
            f'y2="{cy + signo * radio_t * k * math.sin(beta):.2f}"/>'
        )
    pie = arriba + hueco
    d += [
        f'<text class="cota" x="{x + ancho / 2:.1f}" y="{pie + 9:.1f}">'
        f"entre-ejes {entre:g} — LIBRE, no lo fija la relación de radios</text>",
        f'<text class="cota" x="{x + ancho / 2:.1f}" y="{pie + 25:.1f}">'
        f"la cinta deja el sector a ±{math.degrees(beta):.1f}° de la línea de "
        f"centros, no por delante</text>",
        f'<text class="cota" x="{x + ancho / 2:.1f}" y="{pie + 17:.1f}">'
        f"vano libre de cinta {c['amplificador_vano_libre'] * MM:.1f}</text>",
    ]
    return d


def seccion(
    c: dict[str, float], cual: str, x: float, y: float, ancho: float, alto: float
) -> list[str]:
    """Media sección de una de las dos piezas, con la cinta sobre su canto."""
    es_sector = cual == "sector"
    neutra = c[f"amplificador_{cual}_radio"] * MM
    canto = c[f"amplificador_{cual}_radio_mecanizado"] * MM
    w = c["cinta_ancho"] * MM
    cota_agujero = "amplificador_sector_agujero_diametro" if es_sector else "brazo_eje_diametro"
    agujero = c[cota_agujero] * MM / 2.0
    arriba = y + CABECERA
    hueco = alto - CABECERA - PIE_SIN_LISTA - 9.0 * len(filas(c, cual))
    k = min(ancho * 0.42 / neutra, hueco / w, 8.0)
    cx, base = x + ancho / 2, arriba + (hueco + w * k) / 2

    d = [
        f'<text class="pieza" x="{cx:.1f}" y="{y + 12:.1f}">{cual} · sección</text>',
        f'<text class="ref" x="{cx:.1f}" y="{y + 20:.1f}">'
        + (
            "un disco de POM de 5, entero, en el poste del seguidor"
            if es_sector
            else "aluminio torneado, en el eje del brazo"
        )
        + "</text>",
        f'<text class="escala esq" x="{x + ancho - 5:.1f}" y="{y + 30:.1f}">'
        f"Ø{2 * canto:g} × {w:g} mm · escala {k:.2f}:1</text>",
    ]
    for signo in (1, -1):
        x0, x1 = cx + signo * agujero * k, cx + signo * canto * k
        d.append(
            f'<polygon class="corte" points="{x0:.2f},{base:.2f} {x1:.2f},{base:.2f} '
            f'{x1:.2f},{base - w * k:.2f} {x0:.2f},{base - w * k:.2f}"/>'
        )
        xc = cx + signo * neutra * k
        d.append(
            f'<line class="cinta" x1="{xc:.2f}" y1="{base:.2f}" '
            f'x2="{xc:.2f}" y2="{base - w * k:.2f}"/>'
        )
    d += [
        f'<line class="eje" x1="{cx:.1f}" y1="{base - w * k - 7:.1f}" '
        f'x2="{cx:.1f}" y2="{base + 7:.1f}"/>',
        f'<text class="cota" x="{cx:.1f}" y="{arriba + hueco + 6:.1f}">'
        f"la línea roja es la cinta: su fibra neutra, a R{neutra:g}, "
        f"medio espesor por fuera del canto</text>",
    ]
    return d


def filas(c: dict[str, float], cual: str) -> list[tuple[str, str]]:
    """Lo que se teclea en el CAD, con el prefijo del mapa que lo contiene."""
    cota, angulo = mapa_de("variables_cota"), mapa_de("variables_angulo")
    comunes = [
        (f"#{cota}.amplificador_{cual}_radio", f"{c[f'amplificador_{cual}_radio'] * MM:g}"),
        (
            f"#{cota}.amplificador_{cual}_radio_mecanizado",
            f"{c[f'amplificador_{cual}_radio_mecanizado'] * MM:g}",
        ),
        (f"#{cota}.cinta_ancho", f"{c['cinta_ancho'] * MM:g}"),
        (f"#{cota}.cinta_espesor", f"{c['cinta_espesor'] * MM:g}"),
    ]
    if cual == "sector":
        return [
            *comunes,
            (
                f"#{angulo}.amplificador_tangencia",
                f"{math.degrees(c['amplificador_tangencia']):g}",
            ),
            (
                f"#{cota}.amplificador_sector_agujero_diametro",
                f"{c['amplificador_sector_agujero_diametro'] * MM:g}",
            ),
        ]
    return [
        *comunes,
        (
            f"#{angulo}.amplificador_tambor_abrazado",
            f"{math.degrees(c['amplificador_tambor_abrazado']):g}",
        ),
        (f"#{cota}.brazo_eje_diametro", f"{c['brazo_eje_diametro'] * MM:g}"),
    ]


AVISOS = {
    "planta": ("El anclaje de la cinta y el tensor NO están acotados: son diseño de CAD."),
    "sector": (
        "Se mecaniza al canto, no a la fibra neutra: restar lo mismo a los dos "
        "radios no conserva su cociente."
    ),
    "tambor": (
        "R8 con cinta de 0,05 da r/t 160 y 603 MPa de flexión. Con la de 0,1 "
        "eran 80 y 1206, y por eso se cambió."
    ),
}


def panel(
    c: dict[str, float], cual: str, x: float, y: float, ancho: float, alto: float
) -> list[str]:
    d = [
        f'<rect class="marco" x="{x:.1f}" y="{y:.1f}" '
        f'width="{ancho:.1f}" height="{alto:.1f}" rx="3"/>'
    ]
    d += planta(c, x, y, ancho, alto) if cual == "planta" else seccion(c, cual, x, y, ancho, alto)
    if cual != "planta":
        fila = y + alto - 18.0 - 9.0 * len(filas(c, cual))
        d.append(
            f'<line class="raya" x1="{x + 4:.1f}" y1="{fila - 8:.1f}" '
            f'x2="{x + ancho - 4:.1f}" y2="{fila - 8:.1f}"/>'
        )
        for variable, valor in filas(c, cual):
            d.append(f'<text class="var" x="{x + 5:.1f}" y="{fila:.1f}">{variable}</text>')
            d.append(f'<text class="val" x="{x + ancho - 5:.1f}" y="{fila:.1f}">{valor}</text>')
            fila += 9.0
    d.append(f'<text class="aviso" x="{x + 5:.1f}" y="{y + alto - 7:.1f}">{AVISOS[cual]}</text>')
    return d


def hoja() -> str:
    c = contrato()
    ancho, alto, borde = 230.0, 196.0, 12.0
    w, h = borde * 2 + 2 * ancho, 48 + 2 * alto + borde
    partes = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{w * 2:.0f}" height="{h * 2:.0f}" '
        f'viewBox="0 0 {w:.0f} {h:.0f}">',
        f"<style>{ESTILO}</style>",
        f'<rect width="{w:.0f}" height="{h:.0f}" fill="#fff"/>',
        f'<text class="h1" x="{borde}" y="20">Amplificador 8:1 · cabestrante de cinta</text>',
        f'<text class="sub" x="{borde}" y="30">Generado desde docs/contratos.json con '
        "scripts/dibujar_amplificador.py. Piezas de PLATAFORMA: se dibujan a mano en el CAD, "
        "una vez, y no cambian entre pedidos.</text>",
        f'<text class="sub" x="{borde}" y="38">Una cinta anclada por los dos extremos no tiene '
        "juego, solo elasticidad: 0,046 mm en la punta, contra 1,98 de un par de "
        "engranajes.</text>",
    ]
    for i, cual in enumerate(("planta", "sector", "tambor")):
        partes += panel(c, cual, borde + (i % 2) * ancho, 48 + (i // 2) * alto, ancho, alto)
    partes.append("</svg>")
    return "\n".join(partes) + "\n"


def main(argv: list[str] | None = None) -> int:
    partes = argparse.ArgumentParser(description=__doc__)
    partes.add_argument("--out", type=Path, default=Path("build/amplificador.svg"))
    opciones = partes.parse_args(argv)
    opciones.out.parent.mkdir(parents=True, exist_ok=True)
    opciones.out.write_text(hoja(), encoding="utf-8")
    print(f"amplificador en {opciones.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
