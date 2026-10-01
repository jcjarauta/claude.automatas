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
from scripts.acotar import ESTILO, FLECHA, auxiliar, cota_h, cota_v, radial
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


def _horizontales(perfil: Perfil, largo: float, tol: float = 1e-6):
    """Segmentos horizontales de esa longitud, de abajo arriba."""
    return sorted(
        (
            e
            for e in perfil
            if isinstance(e, Segmento)
            and abs(e.a[1] - e.b[1]) <= tol
            and abs(abs(e.a[0] - e.b[0]) - largo) <= tol
        ),
        key=lambda e: e.a[1],
    )


def _verticales(perfil: Perfil, largo: float, tol: float = 1e-6):
    return sorted(
        (
            e
            for e in perfil
            if isinstance(e, Segmento)
            and abs(e.a[0] - e.b[0]) <= tol
            and abs(abs(e.a[1] - e.b[1]) - largo) <= tol
        ),
        key=lambda e: e.a[0],
    )


def planta(nombre: str, c: dict[str, float], x: float, y: float, ancho: float, alto: float):
    """La vista de frente, con TODAS las cotas que la ficha declara.

    Acotar solo algunas era el agujero de la primera versión: lo que no
    aparece dibujado se teclea leyéndolo de la tabla sin saber a qué rasgo
    corresponde, y entonces la hoja no sirve para dibujar, solo para
    recordar.
    """
    perfil = PERFIL_DE[nombre](c)
    ficha, cotas = FICHAS[nombre], cotas_en_mm()
    x0, y0, x1, y1 = caja(perfil)
    hueco = alto - CABECERA

    # **El hueco del dibujo sale del número de cotas, no al revés.** Cada cota
    # horizontal come 15 px bajo la pieza; con una proporción fija, la quinta
    # se metía en el porqué. Se cuentan antes y se reparte lo que quede.
    cuantas = (
        bool(ficha.voladizo)
        + len(ficha.entre_centros)
        + bool(ficha.ranura)
        + bool(ficha.cara_plana)
        + sum(1 for cota in ficha.segmentos if _horizontales(perfil, cotas[cota]))
    )
    pila = 16 + 15 * cuantas
    k = min(
        ancho * 0.46 / max(x1 - x0, 1e-6),
        max(hueco - pila - 24, 20.0) / max(y1 - y0, 1e-6),
        7.0,
    )
    ox = x + ancho / 2 - ((x0 + x1) / 2) * k
    oy = y + CABECERA + 14 + (y1 - (y0 + y1) / 2) * k
    abajo, derecha = oy + (y1 - (y0 + y1) / 2) * k, ox + (x1 - (x0 + x1) / 2) * k

    d = [
        f'<text class="vista" x="{x + ancho / 2:.1f}" y="{y + 12:.1f}">'
        f"planta · escala {k:.2f}:1</text>"
    ]
    d += camino(perfil, k, ox, oy)
    d += [
        f'<line class="eje" x1="{ox - 13:.2f}" y1="{oy:.2f}" x2="{ox + 13:.2f}" y2="{oy:.2f}"/>',
        f'<line class="eje" x1="{ox:.2f}" y1="{oy - 13:.2f}" x2="{ox:.2f}" y2="{oy + 13:.2f}"/>',
        f'<text class="var" x="{ox:.2f}" y="{oy - 17:.2f}">DATUM</text>',
    ]

    puestos: set[str] = set()
    angulos = (210.0, 150.0, -35.0, 35.0, 115.0, -115.0)
    for e in perfil:
        if not isinstance(e, Arco):
            continue
        cota = _nombre_del_radio(ficha, cotas, e.radio)
        if not cota or cota in puestos:
            continue
        ang = math.radians(angulos[len(puestos) % len(angulos)])
        cx, cy = ox + e.centro[0] * k, oy - e.centro[1] * k
        lleno = abs(e.hasta - e.desde - 2 * math.pi) < 1e-9
        d += radial(cx, cy, e.radio * k, ang, f"Ø{2 * e.radio:g}" if lleno else f"R{e.radio:g}")
        puestos.add(cota)

    # Cotas horizontales, apiladas hacia abajo para que no se monten.
    nivel = abajo + 16
    centros = sorted({e.centro[0] for e in perfil if isinstance(e, Arco)})

    def horizontal(xa: float, xb: float, cota: str):
        nonlocal nivel
        a, b = ox + xa * k, ox + xb * k
        d.extend([auxiliar(a, oy, a, nivel + 3), auxiliar(b, oy, b, nivel + 3)])
        d.extend(cota_h(a, b, nivel, f"{cotas[cota]:g}"))
        d.append(
            f'<text class="cotavar" x="{min(a, b):.2f}" y="{nivel + 9:.2f}">#cota.{cota}</text>'
        )
        nivel += 15

    if ficha.voladizo:
        # Del datum al borde: es lo único que sitúa el contorno, y sin ella
        # el que dibuja tiene que deducir dónde empieza el bloque.
        horizontal(-cotas[ficha.voladizo], 0.0, ficha.voladizo)
    for cota in ficha.entre_centros:
        if len(centros) >= 2:
            horizontal(centros[0], centros[-1], cota)
    if ficha.ranura:
        radio = cotas[ficha.ranura[1]]
        extremos = sorted(
            e.centro[0] for e in perfil if isinstance(e, Arco) and abs(e.radio - radio) < 1e-6
        )
        if len(extremos) >= 2:
            horizontal(extremos[0], extremos[-1], ficha.ranura[0])
    if ficha.cara_plana:
        horizontal(0.0, cotas[ficha.cara_plana], ficha.cara_plana)
    for cota, _ in ficha.segmentos.items():
        iguales = _horizontales(perfil, cotas[cota])
        if iguales:
            e = iguales[0]
            horizontal(min(e.a[0], e.b[0]), max(e.a[0], e.b[0]), cota)

    if ficha.simetrico:
        # La otra mitad de situar el contorno: a lo alto no hay cota, hay una
        # simetría. Dibujarla y decirlo es más barato que una cota derivada.
        d += [
            f'<line class="eje" x1="{ox + (x0 - 2) * k:.2f}" y1="{oy:.2f}" '
            f'x2="{ox + (x1 + 2) * k:.2f}" y2="{oy:.2f}"/>',
            f'<text class="cotavar" x="{ox + x0 * k:.2f}" '
            f'y="{oy - (y1 - (y0 + y1) / 2) * k - 14:.2f}">'
            "simétrico respecto de este eje · el DATUM está sobre él</text>",
        ]

    # Y las verticales, a la derecha.
    lado = derecha + 22
    for cota, _ in ficha.segmentos.items():
        iguales = _verticales(perfil, cotas[cota])
        if not iguales:
            continue
        e = iguales[-1]
        ya, yb = oy - e.a[1] * k, oy - e.b[1] * k
        d.extend(
            [
                auxiliar(ox + e.a[0] * k, ya, lado + 3, ya),
                auxiliar(ox + e.a[0] * k, yb, lado + 3, yb),
            ]
        )
        d.extend(cota_v(min(ya, yb), max(ya, yb), lado, f"{cotas[cota]:g}"))
        d.append(
            f'<text class="cotavar" x="{lado + 5:.2f}" y="{(ya + yb) / 2:.2f}" '
            f'transform="rotate(-90 {lado + 5:.2f} {(ya + yb) / 2:.2f})">#cota.{cota}</text>'
        )
        lado += 22
    return d


def segunda_vista(nombre: str, c: dict[str, float], x: float, y: float, ancho: float, alto: float):
    """La tercera dimensión: sección si es plancha, alzado si es barra.

    Es lo que convierte un contorno en una pieza. Sin ella el espesor vive
    solo en la tabla, y un espesor que no se ve en el dibujo se extruye al
    que tenga puesto el CAD por defecto.
    """
    clase, cota = LISTADO[nombre].solido
    perfil = PERFIL_DE[nombre](c)
    x0, _, x1, y1 = caja(perfil)
    grueso = c[cota]
    largo = (x1 - x0) if clase == "plancha" else grueso
    altura = grueso if clase == "plancha" else 2 * y1
    k = min(ancho * 0.52 / max(largo, 1e-6), (alto - CABECERA) * 0.30 / max(altura, 1e-6), 7.0)
    cx, cy = x + ancho / 2, y + CABECERA + (alto - CABECERA) * 0.20

    titulo = "sección A-A" if clase == "plancha" else "alzado"
    d = [
        f'<text class="vista" x="{cx:.1f}" y="{y + 12:.1f}">{titulo} · escala {k:.2f}:1</text>',
        f'<text class="nota" x="{cx:.1f}" y="{y + 21:.1f}">'
        + (
            "se extruye el contorno: el espesor no está en el DXF"
            if clase == "plancha"
            else "barra de stock cortada a medida, la cara plana recorre todo el largo"
        )
        + "</text>",
    ]
    w, h = largo * k, altura * k
    d.append(
        f'<rect class="corte" x="{cx - w / 2:.2f}" y="{cy - h / 2:.2f}" '
        f'width="{w:.2f}" height="{h:.2f}"/>'
    )
    if clase == "barra":
        # La cara plana, que recorre el largo entero.
        plano = cy - c["brazo_chaveta"] * k
        d.append(
            f'<line class="contorno" x1="{cx - w / 2:.2f}" y1="{plano:.2f}" '
            f'x2="{cx + w / 2:.2f}" y2="{plano:.2f}"/>'
        )
        d.append(f'<text class="cotatx" x="{cx:.2f}" y="{plano - 3:.2f}">cara plana</text>')
    borde = cx + w / 2
    d.append(auxiliar(borde, cy - h / 2, borde + 18, cy - h / 2))
    d.append(auxiliar(borde, cy + h / 2, borde + 18, cy + h / 2))
    if clase == "plancha":
        d += cota_v(cy - h / 2, cy + h / 2, borde + 14, f"{grueso:g}")
        d.append(
            f'<text class="cotavar" x="{borde + 19:.2f}" y="{cy:.2f}" '
            f'transform="rotate(-90 {borde + 19:.2f} {cy:.2f})">#cota.{cota}</text>'
        )
    else:
        d.append(auxiliar(cx - w / 2, cy + h / 2, cx - w / 2, cy + h / 2 + 18))
        d.append(auxiliar(cx + w / 2, cy + h / 2, cx + w / 2, cy + h / 2 + 18))
        d += cota_h(cx - w / 2, cx + w / 2, cy + h / 2 + 14, f"{grueso:g}")
        d.append(
            f'<text class="cotavar" x="{cx - w / 2:.2f}" '
            f'y="{cy + h / 2 + 23:.2f}">#cota.{cota}</text>'
        )
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
    # Un panel por pieza y a lo ancho: lleva dos vistas, su porqué y su
    # tabla, y partido en dos columnas no cabe ninguna de las tres.
    vista_ancho, alto, borde = 230.0, 330.0, 12.0
    ancho = 2 * vista_ancho
    filas = len(piezas)
    w = borde * 2 + ancho
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
    anchura = int((w - 2 * borde) / 2.65)
    lineas = textwrap.wrap(encabezado, anchura)
    for i, linea in enumerate(lineas):
        partes.append(f'<text class="sub" x="{borde}" y="{30 + 8 * i}">{linea}</text>')
    cabecera = 30 + 8 * len(lineas) + 6

    for i, nombre in enumerate(piezas):
        px, py = borde, cabecera + i * alto
        lista = LISTADO[nombre]
        partes += [
            f'<rect class="marco" x="{px:.1f}" y="{py:.1f}" '
            f'width="{ancho:.1f}" height="{alto:.1f}" rx="3"/>',
            f'<text class="h1" x="{px + 8:.1f}" y="{py + 16:.1f}">'
            f"{nombre} · x{lista.cantidad}</text>",
            f'<text class="notal" x="{px + 8:.1f}" y="{py + 25:.1f}">{lista.forma}</text>',
        ]
        # +30 y no +14: el rótulo de la vista caía sobre el subtítulo de la
        # pieza, que es texto largo y no se puede recortar.
        # El alto que se les pasa descuenta el desplazamiento: si no, la vista
        # cree que llega hasta py+alto-PIE y en realidad empieza 30 más abajo,
        # así que la última cota se metía en el porqué.
        partes += planta(nombre, c, px, py + 30, vista_ancho, alto - PIE - 30)
        partes += segunda_vista(nombre, c, px + vista_ancho, py + 30, vista_ancho, alto - PIE - 30)
        partes += pie(nombre, c, px, py + alto - PIE + 8, ancho)
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
