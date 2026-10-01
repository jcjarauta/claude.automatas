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

from emit.plataforma import Segmento, barra
from scripts.acotar import ESTILO, FLECHA, MM, auxiliar, contrato, cota_h, cota_v, radial

CABECERA = 44.0
PIE = 104.0

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
        "SIN DEFINIR: el apriete axial de los pernos, que depende de cuántas piezas se "
        "apilan en el codo y en la punta. Y FALTA UNA PIEZA: los dos ejes de pivote y el "
        "del elevador llevan la cara plana que casa con la del brazo, mecanizada a su "
        "calaje. Sin ese plano, el brazo cala contra nada."
    ),
}


def obround(cx: float, cy: float, largo: float, r0: float, r1: float, k: float) -> str:
    """El contorno, en coordenadas de la hoja.

    **La forma no se calcula aquí.** Sale de `emit.plataforma.barra`, que es
    la misma que escribe el DXF: si la hoja enseñara un contorno y el archivo
    otro, quien dibuja haría un tercero. Esto solo traslada y escala.
    """
    trozos = barra(largo, r0, r1)
    punto = lambda p: (cx + p[0] * k, cy - p[1] * k)  # noqa: E731
    d = []
    for e in trozos:
        if isinstance(e, Segmento):
            a, b = punto(e.a), punto(e.b)
            if not d:
                d.append(f"M {a[0]:.2f},{a[1]:.2f}")
            d.append(f"L {b[0]:.2f},{b[1]:.2f}")
        else:
            # La Y se invierte al pasar a coordenadas de pantalla, así que el
            # arco antihorario del perfil se dibuja horario en el SVG.
            fin = punto(
                (
                    e.centro[0] + e.radio * math.cos(e.hasta),
                    e.centro[1] + e.radio * math.sin(e.hasta),
                )
            )
            ini = punto(
                (
                    e.centro[0] + e.radio * math.cos(e.desde),
                    e.centro[1] + e.radio * math.sin(e.desde),
                )
            )
            grande = 1 if (e.hasta - e.desde) % (2 * math.pi) > math.pi else 0
            if not d:
                d.append(f"M {ini[0]:.2f},{ini[1]:.2f}")
            d.append(
                f"A {e.radio * k:.2f},{e.radio * k:.2f} 0 {grande} 0 {fin[0]:.2f},{fin[1]:.2f}"
            )
    return " ".join(d) + " Z"


def medidas(c: dict[str, float], cual: str) -> tuple[float, float, float, float, float]:
    """Largo entre centros, radios de los dos cubos y de los dos agujeros."""
    largo = c[f"brazo_{cual}"] * MM
    perno = c["brazo_perno_diametro"] * MM / 2.0
    extremo = c["brazo_extremo_diametro"] * MM / 2.0
    if cual == "distal":
        return largo, extremo, extremo, perno, perno
    eje = c["brazo_eje_diametro"] * MM / 2.0
    cubo = c["brazo_cubo_diametro"] * MM / 2.0
    return largo, cubo, extremo, eje, perno


COMUNES = [
    ("cota", "brazo_extremo_diametro_radio", "R del cubo del extremo libre"),
    ("cota", "brazo_perno_diametro", "agujero del perno, H7"),
    ("cota", "brazo_espesor", "espesor de la pletina"),
]
CALADAS = [
    ("cota", "brazo_eje_diametro", "agujero del eje, H7"),
    ("cota", "brazo_cubo_diametro_radio", "R del cubo que va al eje"),
    ("cota", "brazo_chaveta", "del eje al plano de la cara"),
    ("cota", "brazo_chaveta_cuerda", "cuerda de la cara plana"),
    ("angulo", "brazo_chaveta_angulo", "giro de la cara, 0 y no es libre"),
]

VARIABLES: dict[str, list[tuple[str, str, str]]] = {
    "proximal": [
        ("cota", "brazo_proximal", "entre centros · lo fija la cinemática"),
        *CALADAS,
        *COMUNES,
        ("angulo", "calaje_izquierdo", "a qué ángulo lo cala el eje"),
    ],
    "distal": [
        ("cota", "brazo_distal", "entre centros · lo fija la cinemática"),
        ("cota", "brazo_extremo_diametro_radio", "R de los DOS cubos: son iguales"),
        ("cota", "brazo_perno_diametro", "los dos agujeros, H7"),
        ("cota", "brazo_espesor", "espesor de la pletina"),
    ],
    "palanca": [
        ("cota", "brazo_palanca", "del eje al punto donde levanta"),
        *CALADAS,
        *COMUNES,
        ("angulo", "calaje_elevador", "a qué ángulo lo cala el eje"),
    ],
    "seccion": [
        ("cota", "brazo_extremo_diametro", "ancho de la barra en el extremo"),
        ("cota", "brazo_espesor", "altura de la extrusión"),
        ("cota", "brazo_perno_diametro", "el perno pasa, no se aloja"),
    ],
}
"""Lo que hay que teclear para dibujar cada brazo, y nada más.

Está aquí y no junto a cada flecha porque los nombres son largos: puestos
sobre el dibujo se montaban unos encima de otros y se salían del marco, y un
rótulo que se sale es peor que no ponerlo. Al pie se leen de corrido, que es
como se teclean.

**Los que acaban en `_radio` son los gemelos**, no cotas del contrato: el
contrato guarda `brazo_cubo_diametro` y el exportador saca su mitad. En un
arco de contorno el CAD pide radio, así que es el gemelo el que se teclea.
"""


def valor_de(c: dict[str, float], mapa: str, nombre: str) -> float:
    """El número que hay que ver al lado del rótulo, en la unidad del mapa.

    Resuelve el gemelo aquí mismo: si el nombre no está en el contrato pero
    sí lo está sin el sufijo, es la mitad o el doble. Así la tabla no puede
    decir un valor y el CSV otro.
    """
    if mapa == "angulo":
        return math.degrees(c[nombre])
    if nombre in c:
        return c[nombre] * MM
    if nombre.endswith("_radio"):
        return c[nombre.removesuffix("_radio")] * MM / 2.0
    if nombre.endswith("_diametro"):
        return c[nombre.removesuffix("_diametro")] * MM * 2.0
    raise KeyError(nombre)


def tabla(c: dict[str, float], cual: str, x: float, y: float, ancho: float) -> list[str]:
    """Las variables de la vista, al pie y en dos columnas."""
    filas = VARIABLES[cual]
    mitad = (len(filas) + 1) // 2
    d = [
        f'<text class="nota" x="{x + ancho / 2:.1f}" y="{y:.1f}">'
        "lo que se teclea en el croquis</text>"
    ]
    for i, (mapa, nombre, para_que) in enumerate(filas):
        col, fila = divmod(i, mitad) if mitad else (0, 0)
        cx = x + 6 + col * (ancho - 12) / 2
        cy = y + 9 + fila * 11.0
        valor = valor_de(c, mapa, nombre)
        numero = f"{valor:.3f}°" if mapa == "angulo" else f"{valor:g}"
        d += [
            f'<text class="varl" x="{cx:.1f}" y="{cy:.1f}">#{mapa}.{nombre}</text>',
            f'<text class="cotatxi" x="{cx + 3:.1f}" y="{cy + 4.8:.1f}">'
            f"{numero} · {para_que}</text>",
        ]
    return d


def frente(c: dict[str, float], cual: str, x: float, y: float, ancho: float, alto: float):
    titulo, bajo, calado = BRAZOS[cual]
    largo, r0, r1, a0, a1 = medidas(c, cual)
    chaveta = c["brazo_chaveta"] * MM
    k = min(ancho * 0.78 / (largo + r0 + r1), (alto - CABECERA - PIE) / (3.6 * r0))
    cx = x + ancho / 2 - (largo / 2) * k
    cy = y + CABECERA + (alto - CABECERA - PIE) * 0.42

    d = [
        f'<text class="vista" x="{x + ancho / 2:.1f}" y="{y + 14:.1f}">{titulo}</text>',
        f'<text class="nota" x="{x + ancho / 2:.1f}" y="{y + 23:.1f}">{bajo}</text>',
        f'<text class="nota" x="{x + ancho / 2:.1f}" y="{y + 31:.1f}">'
        f"pletina de latón de {c['brazo_espesor'] * MM:g} · escala {k:.2f}:1</text>",
        f'<path class="corte" d="{obround(cx, cy, largo, r0, r1, k)}"/>',
    ]
    media = c["brazo_chaveta_cuerda"] * MM * k / 2.0
    for i, (radio, agujero) in enumerate(((r0, a0), (r1, a1))):
        px = cx + i * largo * k
        if calado and i == 0:
            # El agujero del eje es una D, no un círculo con una raya: dibujarlo
            # redondo y cruzarlo con la cuerda se lee como un agujero redondo
            # con una marca, y entonces el brazo no cala.
            d.append(
                f'<path class="contorno" fill="#fff" '
                f'd="M {px + chaveta * k:.2f},{cy + media:.2f} '
                f"A {agujero * k:.2f},{agujero * k:.2f} 0 1 1 "
                f'{px + chaveta * k:.2f},{cy - media:.2f} Z"/>'
            )
        else:
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
        cuerda = c["brazo_chaveta_cuerda"] * MM
        plano = cx + chaveta * k
        # Fuera del cubo: dentro, la cota de la cuerda cae sobre el agujero y
        # el número se lee con lupa.
        fuera = cx + r0 * k + 16
        d += [
            auxiliar(plano, cy - cuerda * k / 2, fuera, cy - cuerda * k / 2),
            auxiliar(plano, cy + cuerda * k / 2, fuera, cy + cuerda * k / 2),
        ]
        d += cota_v(cy - cuerda * k / 2, cy + cuerda * k / 2, fuera - 3, f"{cuerda:g}")
        d += cota_h(cx, plano, cy - r0 * k - 9, f"{chaveta:g}")
        d.append(
            f'<text class="cotatx" x="{cx + 2 * chaveta * k:.2f}" '
            f'y="{cy - r0 * k - 17:.2f}">cara plana a '
            f"{math.degrees(c['brazo_chaveta_angulo']):g}° del eje del brazo</text>"
        )
    d.append(
        f'<line class="eje" x1="{cx - r0 * k - 8:.2f}" y1="{cy:.2f}" '
        f'x2="{cx + largo * k + r1 * k + 8:.2f}" y2="{cy:.2f}"/>'
    )
    d += cota_h(cx, cx + largo * k, cy + r0 * k + 22, f"{largo:g}")
    d += radial(cx, cy, a0 * k, math.radians(205), f"Ø{2 * a0:g} H7")
    d += radial(cx + largo * k, cy, a1 * k, math.radians(-25), f"Ø{2 * a1:g} H7")
    d += radial(cx, cy, r0 * k, math.radians(130), f"R{r0:g}")
    d += radial(cx + largo * k, cy, r1 * k, math.radians(50), f"R{r1:g}")
    d.append(
        f'<text class="aviso" x="{x + ancho / 2:.1f}" y="{y + 39:.1f}" '
        f'text-anchor="middle">importa {cual}.dxf · ancla con DOS coincidentes: '
        "el agujero del datum al origen y el otro centro al eje X</text>"
    )
    return d + tabla(c, cual, x, y + alto - PIE + 12, ancho)


def seccion(c: dict[str, float], x: float, y: float, ancho: float, alto: float):
    """El espesor, común a los tres, y la pila en un perno."""
    espesor = c["brazo_espesor"] * MM
    ancho_barra = c["brazo_extremo_diametro"] * MM
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
    )
    borde = cx + ancho_barra * k / 2
    d.append(auxiliar(borde, base, borde + 18, base))
    d.append(auxiliar(borde, base - espesor * k, borde + 18, base - espesor * k))
    d += cota_v(base - espesor * k, base, borde + 15, f"{espesor:g}")
    return d + tabla(c, "seccion", x, y + alto - PIE + 12, ancho)


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
    ancho, alto, borde = 248.0, 232.0, 12.0
    w, h = borde * 2 + 2 * ancho, 54 + 2 * alto + borde
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
        f'<text class="sub" x="{borde}" y="46">El DXF llega con el rasgo DATUM en el origen '
        "y el centro siguiente sobre +X: no hay nada que partir por la mitad. Después, acotar "
        "y comprobar que Onshape diga «totalmente definida».</text>",
        f'<text class="sub" x="{borde}" y="38">Del proximal se corta UNA y valen las dos: '
        "los calajes suman -180°, así que el derecho es el izquierdo volteado. El calaje no "
        "está en el brazo: está en la cara plana del EJE, que aún no tiene plano.</text>",
    ]
    for i, cual in enumerate(("proximal", "distal", "palanca", "seccion")):
        partes += panel(c, cual, borde + (i % 2) * ancho, 54 + (i // 2) * alto, ancho, alto)
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
