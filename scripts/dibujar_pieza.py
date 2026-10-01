"""La hoja de una pieza de la plataforma: vistas, cotas y tabla de variables.

    uv run python scripts/dibujar_pieza.py mordaza eje_pivote --out build/

Es el tercero de los tres artefactos que `docs/metodologia.md` §2d pide por
pieza —el DXF, la tabla y el boceto— y **se genera desde el mismo perfil que
escribe el DXF**. Escribir una hoja a mano por pieza era lo que había, y con
tres ya empezaban a divergir: un contorno dibujado y otro cortado es la forma
más cara de descubrir una cota.

Lo que dibuja sale de dos sitios y de ninguno más:

- la **forma**, de `emit.plataforma`, que es la que va al DXF;
- **qué acotar**, de `FICHAS` en `scripts/comparar_dxf.py`, que es lo que el
  comparador va a mirar después.

Esa segunda procedencia es la que importa: **la hoja enseña exactamente lo que
se va a verificar**. Si una cota no está en la ficha no aparece en el dibujo, y
entonces se ve que falta antes de cortar nada.
"""

from __future__ import annotations

import argparse
import math
import sys
import textwrap
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from emit.plataforma import LISTADO, Arco, Perfil, Segmento, contrato_mm, eje_pivote, mordaza
from emit.plataforma import brazo as brazo_de
from scripts.acotar import ESTILO, FLECHA, auxiliar, cota_h, radial
from scripts.comparar_dxf import FICHAS, cotas_en_mm
from scripts.listado_piezas import tabla_markdown  # noqa: F401  (se usa en el test)

CABECERA, PIE = 60.0, 112.0

PERFIL_DE = {
    "brazo_proximal": lambda c: brazo_de("brazo_proximal", c),
    "brazo_distal": lambda c: brazo_de("brazo_distal", c),
    "palanca_lapiz": lambda c: brazo_de("palanca_lapiz", c),
    "mordaza": mordaza,
    "eje_pivote": eje_pivote,
}
"""De dónde sale la forma de cada pieza. El sector y el tambor no están porque
son discos y su hoja es `dibujar_plano_cabestrante.py`, que lleva secciones."""


def caja(perfil: Perfil) -> tuple[float, float, float, float]:
    xs: list[float] = []
    ys: list[float] = []
    for e in perfil:
        if isinstance(e, Segmento):
            xs += [e.a[0], e.b[0]]
            ys += [e.a[1], e.b[1]]
        else:
            xs += [e.centro[0] - e.radio, e.centro[0] + e.radio]
            ys += [e.centro[1] - e.radio, e.centro[1] + e.radio]
    return min(xs), min(ys), max(xs), max(ys)


def camino(perfil: Perfil, k: float, ox: float, oy: float) -> list[str]:
    """El perfil en coordenadas de hoja. Cada entidad por separado: así un
    agujero se ve como agujero y no como parte del contorno."""

    def p(x: float, y: float) -> tuple[float, float]:
        return ox + x * k, oy - y * k

    d = []
    for e in perfil:
        if isinstance(e, Segmento):
            a, b = p(*e.a), p(*e.b)
            d.append(
                f'<line class="contorno" x1="{a[0]:.2f}" y1="{a[1]:.2f}" '
                f'x2="{b[0]:.2f}" y2="{b[1]:.2f}"/>'
            )
        elif abs(e.hasta - e.desde - 2 * math.pi) < 1e-9:
            cx, cy = p(*e.centro)
            d.append(
                f'<circle class="contorno" cx="{cx:.2f}" cy="{cy:.2f}" r="{e.radio * k:.2f}"/>'
            )
        else:
            # La Y se invierte al pasar a pantalla, así que el arco
            # antihorario del perfil se dibuja horario en el SVG.
            ini = p(
                e.centro[0] + e.radio * math.cos(e.desde),
                e.centro[1] + e.radio * math.sin(e.desde),
            )
            fin = p(
                e.centro[0] + e.radio * math.cos(e.hasta),
                e.centro[1] + e.radio * math.sin(e.hasta),
            )
            grande = 1 if (e.hasta - e.desde) % (2 * math.pi) > math.pi else 0
            d.append(
                f'<path class="contorno" d="M {ini[0]:.2f},{ini[1]:.2f} '
                f'A {e.radio * k:.2f},{e.radio * k:.2f} 0 {grande} 0 {fin[0]:.2f},{fin[1]:.2f}"/>'
            )
    return d


def _nombre_del_radio(ficha, cotas: dict[str, float], radio: float, tol: float = 1e-6) -> str:
    for nombre in ficha.radios:
        if abs(cotas[nombre] - radio) <= tol:
            return nombre
    return ""


def vista(nombre: str, c: dict[str, float], x: float, y: float, ancho: float, alto: float):
    perfil = PERFIL_DE[nombre](c)
    ficha, lista, cotas = FICHAS[nombre], LISTADO[nombre], cotas_en_mm()
    x0, y0, x1, y1 = caja(perfil)
    hueco_alto = alto - CABECERA - PIE
    # Se deja sitio abajo para la línea de cota entre centros.
    k = min(ancho * 0.60 / max(x1 - x0, 1e-6), hueco_alto * 0.62 / max(y1 - y0, 1e-6), 7.0)
    ox = x + ancho / 2 - ((x0 + x1) / 2) * k
    oy = y + CABECERA + hueco_alto * 0.42 + ((y0 + y1) / 2) * k

    d = [
        f'<text class="vista" x="{x + ancho / 2:.1f}" y="{y + 14:.1f}">'
        f"{nombre} · x{lista.cantidad}</text>",
        f'<text class="nota" x="{x + ancho / 2:.1f}" y="{y + 23:.1f}">{lista.forma}</text>',
        f'<text class="nota" x="{x + ancho / 2:.1f}" y="{y + 31:.1f}">escala {k:.2f}:1</text>',
    ]
    d += camino(perfil, k, ox, oy)

    # El datum, que es lo que hay que anclar.
    d += [
        f'<line class="eje" x1="{ox - 14:.2f}" y1="{oy:.2f}" x2="{ox + 14:.2f}" y2="{oy:.2f}"/>',
        f'<line class="eje" x1="{ox:.2f}" y1="{oy - 14:.2f}" x2="{ox:.2f}" y2="{oy + 14:.2f}"/>',
        f'<text class="var" x="{ox:.2f}" y="{oy + 22:.2f}">DATUM · al origen</text>',
    ]

    # Un radio por cada rasgo circular declarado en la ficha, y solo esos.
    puestos: set[str] = set()
    angulos = (210.0, 150.0, -30.0, 30.0, 110.0, -110.0)
    for e in perfil:
        if not isinstance(e, Arco):
            continue
        cota = _nombre_del_radio(ficha, cotas, e.radio)
        if not cota or cota in puestos:
            continue
        ang = math.radians(angulos[len(puestos) % len(angulos)])
        cx, cy = ox + e.centro[0] * k, oy - e.centro[1] * k
        lleno = abs(e.hasta - e.desde - 2 * math.pi) < 1e-9
        texto = f"Ø{2 * e.radio:g}" if lleno else f"R{e.radio:g}"
        d += radial(cx, cy, e.radio * k, ang, texto)
        puestos.add(cota)

    # La distancia entre centros, que es lo que fija la pieza.
    for cota in ficha.entre_centros:
        largo = cotas[cota]
        centros = sorted({e.centro[0] for e in perfil if isinstance(e, Arco)})
        if len(centros) < 2:
            continue
        a, b = ox + centros[0] * k, ox + centros[-1] * k
        # Dentro del hueco de dibujo: más abajo se monta sobre el porqué, que
        # es texto largo y no se puede recortar.
        base = y + CABECERA + hueco_alto - 4
        d += [auxiliar(a, oy, a, base + 3), auxiliar(b, oy, b, base + 3)]
        d += cota_h(a, b, base, f"{largo:g}")

    d += pie(nombre, c, x, y + alto - PIE + 8, ancho)
    return d


def pie(nombre: str, c: dict[str, float], x: float, y: float, ancho: float):
    """El porqué y la tabla de variables, que es lo que se teclea."""
    from emit.plataforma import _valor

    lista = LISTADO[nombre]
    d = []
    for i, linea in enumerate(textwrap.wrap(lista.porque, 84)):
        d.append(f'<text class="aviso" x="{x + 6:.1f}" y="{y + 6 * i:.1f}">{linea}</text>')
    y += 6 * len(textwrap.wrap(lista.porque, 84)) + 8
    d.append(
        f'<text class="nota" x="{x + ancho / 2:.1f}" y="{y:.1f}">'
        "lo que se teclea en el croquis</text>"
    )
    filas = lista.variables
    mitad = (len(filas) + 1) // 2
    for i, v in enumerate(filas):
        col, fila = divmod(i, mitad)
        cx = x + 6 + col * (ancho - 12) / 2
        cy = y + 9 + fila * 11.0
        valor = _valor(c, v)
        unidad = "°" if v.mapa == "angulo" else ""
        marca = "" if v.en_el_perfil else "  (no está en el DXF)"
        d += [
            f'<text class="varl" x="{cx:.1f}" y="{cy:.1f}">#{v.mapa}.{v.nombre}</text>',
            f'<text class="cotatxi" x="{cx + 3:.1f}" y="{cy + 4.8:.1f}">'
            f"{valor}{unidad} · {v.etiqueta}{(' ' + v.sufijo) if v.sufijo else ''}{marca}</text>",
        ]
    return d


def hoja(piezas: list[str] | None = None) -> str:
    piezas = list(PERFIL_DE) if piezas is None else piezas
    c = contrato_mm()
    ancho, alto, borde = 250.0, 250.0, 12.0
    filas = (len(piezas) + 1) // 2
    w = borde * 2 + min(len(piezas), 2) * ancho
    h = 0.0  # se calcula tras envolver el encabezado
    partes = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{w * 2:.0f}" height="{h * 2:.0f}" '
        f'viewBox="0 0 {w:.0f} {h:.0f}">',
        f"<style>{ESTILO}</style><defs>{FLECHA}</defs>",
        f'<rect width="{w:.0f}" height="{h:.0f}" fill="#fff"/>',
        f'<text class="h1" x="{borde}" y="20">Plataforma · {" · ".join(piezas)}</text>',
    ]
    # El encabezado se envuelve al ancho de la hoja: con una sola pieza la
    # hoja es la mitad de ancha y el texto se salía por la derecha. Recortar
    # un rótulo obligatorio no es una opción.
    encabezado = (
        "Cotas en mm, sacadas de docs/contratos.json. La forma es la misma que escribe "
        "el DXF y las cotas son las que mira scripts/comparar_dxf.py: lo que se dibuja "
        "aquí es lo que se verifica. El DXF llega con el rasgo DATUM en el origen: ancla "
        "con DOS coincidentes, acota con las variables de abajo y comprueba que Onshape "
        "diga «totalmente definida». Después exporta el croquis y pásalo por "
        "scripts/comparar_dxf.py. Si algo no cuadra se toca el CONTRATO y se regenera, "
        "nunca el croquis a mano."
    )
    anchura = int((w - 2 * borde) / 2.45)
    lineas = textwrap.wrap(encabezado, anchura)
    for i, linea in enumerate(lineas):
        partes.append(f'<text class="sub" x="{borde}" y="{30 + 8 * i}">{linea}</text>')
    cabecera = 30 + 8 * len(lineas) + 6

    for i, nombre in enumerate(piezas):
        px, py = borde + (i % 2) * ancho, cabecera + (i // 2) * alto
        partes.append(
            f'<rect class="marco" x="{px:.1f}" y="{py:.1f}" '
            f'width="{ancho:.1f}" height="{alto:.1f}" rx="3"/>'
        )
        partes += vista(nombre, c, px, py, ancho, alto)
    partes.append("</svg>")
    h = cabecera + filas * alto + borde
    partes[1] = (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{w * 2:.0f}" height="{h * 2:.0f}" '
        f'viewBox="0 0 {w:.0f} {h:.0f}">'
    )
    partes[3] = f'<rect width="{w:.0f}" height="{h:.0f}" fill="#fff"/>'
    return "\n".join(partes) + "\n"


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("piezas", nargs="*", choices=list(PERFIL_DE), metavar="pieza")
    p.add_argument("--out", type=Path, default=Path("build/pieza.svg"))
    op = p.parse_args(argv)
    op.out.parent.mkdir(parents=True, exist_ok=True)
    op.out.write_text(hoja(op.piezas or None), encoding="utf-8")
    print(f"hoja en {op.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
