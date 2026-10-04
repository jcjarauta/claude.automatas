"""Escribe demo/feliz_cumpleanos.json: «Feliz cumpleaños» en letra inglesa
enlazada, rematada con un swash terminal.

    uv run python scripts/escritura_feliz_cumpleanos.py
    uv run --group cad python scripts/escritura_feliz_cumpleanos.py --vista build/feliz.png

**Las letras son de una fuente de plóter, no dibujadas a ojo.** Son los
glifos de la Hershey *cursive* (A. V. Hershey, U.S. National Bureau of
Standards, 1967; de uso libre con su atribución): una letra inglesa monolínea
diseñada precisamente para trazarla con una pluma, que es lo que hace el
escribiente. Van copiados aquí, en las unidades de la fuente —enteras, altura
de x 9, y hacia abajo—, para que el pedido salga igual en cada máquina sin
depender de un paquete.

**Lo que se añade a la fuente es lo que una fuente no sabe hacer**: enlazar
las letras sin levantar el lápiz, la tilde de la ñ y la floritura. Cada vuelo
del lápiz se lleva 16° de la vuelta, así que la frase va en cinco trazos:

1. la barra y el fuste de la F;
2. el travesaño de la F, que fluye a «eliz», como en la inglesa;
3. el punto de la i, en rasguillo corto (un punto es un giro de radio cero
   y la leva no lo puede seguir);
4. la tilde de la ñ, antes que su palabra: así cada vuelo es corto y el
   swash, que acaba abajo a la izquierda, deja el lápiz junto a la F para la
   vuelta siguiente;
5. «cumpleaños» con su swash.

**La floritura sigue las reglas del lettering** (docs/feliz_cumpleanos.md):
sale de la letra final y no se pega encima; se construye sobre el mismo
óvalo inclinado que las letras; se cruza consigo misma casi en ángulo recto;
y equilibra la capital de arriba a la izquierda con un remate abajo a la
derecha. Es además lo que la leva agradece: un óvalo amplio es un giro de
radio grande, y lo que socava una leva son los giros cerrados.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

from scripts.escritura_hola_mundo import trazo

RAIZ = Path(__file__).resolve().parent.parent
DESTINO = RAIZ / "demo" / "feliz_cumpleanos.json"

ALTURA_DE_X = 9.0
"""Unidades de la fuente Hershey por altura de x."""

X_POR_UNIDAD = 1.0 / ALTURA_DE_X
"""`trazo` trabaja en alturas de x —la o mide 1— y escala él a 10 mm por
altura de x: así su suavizado redondea lo mismo que en «Hola Mundo». Darle
milímetros lo dejaba diez veces más fino que la letra."""

Punto = tuple[float, float]

# Hershey *cursive*: por letra, (lado izquierdo, avance, trazos). Copiado de
# la fuente sin tocar un número.
GLIFOS: dict[str, tuple[int, int, list[list[Punto]]]] = {
    "F": (
        -10,
        20,
        [
            [
                (0, -6),
                (-2, -6),
                (-4, -7),
                (-5, -9),
                (-4, -11),
                (-1, -12),
                (2, -12),
                (6, -11),
                (9, -11),
                (11, -12),
            ],
            [
                (6, -11),
                (4, -4),
                (2, 2),
                (0, 6),
                (-2, 8),
                (-4, 9),
                (-6, 9),
                (-8, 8),
                (-9, 6),
                (-9, 4),
                (-8, 3),
                (-6, 3),
                (-4, 4),
            ],
            [(-1, -2), (8, -2)],
        ],
    ),
    "e": (
        -4,
        10,
        [
            [
                (-3, 7),
                (-1, 6),
                (0, 5),
                (1, 3),
                (1, 1),
                (0, 0),
                (-1, 0),
                (-3, 1),
                (-4, 3),
                (-4, 6),
                (-3, 8),
                (-1, 9),
                (1, 9),
                (3, 8),
                (4, 7),
                (6, 4),
            ]
        ],
    ),
    "l": (
        -3,
        8,
        [
            [
                (-3, 4),
                (-1, 1),
                (2, -4),
                (3, -6),
                (4, -9),
                (4, -11),
                (3, -12),
                (1, -11),
                (0, -9),
                (-1, -5),
                (-2, 2),
                (-2, 8),
                (-1, 9),
                (0, 9),
                (2, 8),
                (3, 7),
                (5, 4),
            ]
        ],
    ),
    "i": (
        -2,
        7,
        [
            [(1, -5), (1, -4), (2, -4), (2, -5), (1, -5)],
            [(-2, 4), (0, 0), (-2, 6), (-2, 8), (-1, 9), (0, 9), (2, 8), (3, 7), (5, 4)],
        ],
    ),
    "z": (
        -6,
        14,
        [
            [
                (-6, 4),
                (-4, 1),
                (-2, 0),
                (0, 0),
                (2, 2),
                (2, 4),
                (1, 6),
                (-1, 8),
                (-4, 9),
                (-2, 10),
                (-1, 12),
                (-1, 15),
                (-2, 18),
                (-3, 20),
                (-5, 21),
                (-6, 20),
                (-6, 18),
                (-5, 15),
                (-2, 12),
                (1, 10),
                (5, 7),
                (8, 4),
            ]
        ],
    ),
    "c": (
        -5,
        11,
        [
            [
                (2, 2),
                (2, 1),
                (1, 0),
                (-1, 0),
                (-3, 1),
                (-4, 2),
                (-5, 4),
                (-5, 6),
                (-4, 8),
                (-2, 9),
                (1, 9),
                (4, 7),
                (6, 4),
            ]
        ],
    ),
    "u": (
        -6,
        15,
        [
            [(-6, 4), (-4, 0), (-6, 6), (-6, 8), (-5, 9), (-3, 9), (-1, 8), (1, 6), (3, 3)],
            [(4, 0), (2, 6), (2, 8), (3, 9), (4, 9), (6, 8), (7, 7), (9, 4)],
        ],
    ),
    "m": (
        -13,
        25,
        [
            [(-13, 4), (-11, 1), (-9, 0), (-8, 1), (-8, 2), (-9, 6), (-10, 9)],
            [(-9, 6), (-8, 4), (-6, 1), (-4, 0), (-2, 0), (-1, 1), (-1, 2), (-2, 6), (-3, 9)],
            [
                (-2, 6),
                (-1, 4),
                (1, 1),
                (3, 0),
                (5, 0),
                (6, 1),
                (6, 3),
                (5, 6),
                (5, 8),
                (6, 9),
                (7, 9),
                (9, 8),
                (10, 7),
                (12, 4),
            ],
        ],
    ),
    "p": (
        -7,
        15,
        [
            [(-7, 4), (-5, 1), (-4, -1), (-5, 3), (-11, 21)],
            [(-5, 3), (-4, 1), (-2, 0), (0, 0), (2, 1), (3, 3), (3, 5), (2, 7), (1, 8), (-1, 9)],
            [(-5, 8), (-3, 9), (0, 9), (3, 8), (5, 7), (8, 4)],
        ],
    ),
    "a": (
        -6,
        16,
        [
            [
                (3, 3),
                (2, 1),
                (0, 0),
                (-2, 0),
                (-4, 1),
                (-5, 2),
                (-6, 4),
                (-6, 6),
                (-5, 8),
                (-3, 9),
                (-1, 9),
                (1, 8),
                (2, 6),
                (4, 0),
                (3, 5),
                (3, 8),
                (4, 9),
                (5, 9),
                (7, 8),
                (8, 7),
                (10, 4),
            ]
        ],
    ),
    "n": (
        -8,
        18,
        [
            [(-8, 4), (-6, 1), (-4, 0), (-3, 1), (-3, 2), (-4, 6), (-5, 9)],
            [
                (-4, 6),
                (-3, 4),
                (-1, 1),
                (1, 0),
                (3, 0),
                (4, 1),
                (4, 3),
                (3, 6),
                (3, 8),
                (4, 9),
                (5, 9),
                (7, 8),
                (8, 7),
                (10, 4),
            ],
        ],
    ),
    "o": (
        -6,
        14,
        [
            [
                (0, 0),
                (-2, 0),
                (-4, 1),
                (-5, 2),
                (-6, 4),
                (-6, 6),
                (-5, 8),
                (-3, 9),
                (-1, 9),
                (1, 8),
                (2, 7),
                (3, 5),
                (3, 3),
                (2, 1),
                (0, 0),
                (-1, 1),
                (-1, 3),
                (0, 5),
                (2, 6),
                (5, 6),
                (7, 5),
                (8, 4),
            ]
        ],
    ),
    "s": (
        -4,
        11,
        [
            [(-4, 4), (-2, 1), (-1, -1), (-1, 1), (1, 4), (2, 6), (2, 8), (0, 9)],
            [(-4, 8), (-2, 9), (2, 9), (4, 8), (5, 7), (7, 4)],
        ],
    ),
}

ENTRADA_POR_ARRIBA = {"c": (-1.0, -1.5), "a": (1.0, -0.5), "o": (-2.0, -0.5)}
"""Las letras de óvalo —c, a, o— empiezan en la fuente con el lápiz
levantado, arriba a la derecha del óvalo. A mano no se levanta: el enlace de
la letra anterior sube por encima del óvalo y entra por arriba. Es el punto
por el que pasa ese enlace, en el marco de la letra."""


def _palabra(texto: str, x: float, y: float) -> tuple[list[list[Punto]], list[Punto], float]:
    """Una palabra enlazada: devuelve los trazos que quedan sueltos (el punto
    de la i), el trazo continuo, y dónde acaba. Los trazos de una misma letra
    se unen por el camino corto, que en la inglesa es volver sobre el palo
    (la m, la n, la u) o cerrar el ojal (la p, la s)."""
    continuo: list[Punto] = []
    sueltos: list[list[Punto]] = []
    for letra in texto:
        izquierda, avance, trazos = GLIFOS[letra]
        origen = x - izquierda
        for k, t in enumerate(trazos):
            puntos = [(origen + px, y + py) for px, py in t]
            if letra == "i" and k == 0:
                # El punto de la fuente es un cuadradito: un rasguillo
                # inclinado en su lugar, que la leva puede seguir.
                cx, cy = origen + 1.5, y - 4.5
                sueltos.append([(cx - 0.8, cy + 1.0), (cx + 0.8, cy - 1.0)])
                continue
            if letra in ENTRADA_POR_ARRIBA and k == 0 and continuo:
                ex, ey = ENTRADA_POR_ARRIBA[letra]
                continuo.append((origen + ex, y + ey))
            continuo += puntos if not continuo or puntos[0] != continuo[-1] else puntos[1:]
        x += avance
    return sueltos, continuo, x


def _swash(fin: Punto, inicio_x: float, y: float) -> list[Punto]:
    """El swash terminal: sale de la s subiendo, gira sobre un óvalo
    inclinado hasta bajo la línea de base, vuelve subrayando la palabra y
    remata con un lazo bajo la c que cruza el subrayado casi en recto.

    El último rizo acaba **subiendo**, hacia la F. No es solo de lettering:
    el vuelo de vuelta al principio de la frase copia la tangente con que
    acaba el trazo, y con una cola hacia la izquierda se salía de la caja,
    donde el cinco barras se acerca a su límite y la leva derecha llegaba a
    90° de presión."""
    fx, fy = fin
    return [
        (fx + 3, fy - 3),
        (fx + 5, fy - 4),
        (fx + 6, fy - 1),
        (fx + 4, fy + 6),
        (fx - 2, fy + 11),
        (fx - 14, fy + 13.5),
        (inicio_x + 30, y + 14.0),
        (inicio_x + 8, y + 14.0),
        (inicio_x - 1, y + 13.0),
        (inicio_x - 4, y + 10.5),
        (inicio_x - 1, y + 8.8),
        (inicio_x + 2, y + 10.5),
        (inicio_x + 1, y + 15.0),
        (inicio_x - 5, y + 19.0),
        (inicio_x - 11, y + 18.5),
        (inicio_x - 14, y + 15.5),
        (inicio_x - 12, y + 12.5),
    ]


SANGRIA = 22.0
"""Cuánto entra «cumpleaños» respecto de «Feliz»: la composición en dos
líneas escalonadas, la capital arriba a la izquierda y el swash abajo a la
derecha, es la diagonal que equilibra la tarjeta."""

LAZO_BAJO = "cump"
"""Bajo qué letra cierra el swash su lazo: lo que va delante de ella queda
sin subrayar."""

INTERLINEA = 26.0
"""De línea de base a línea de base: deja pasar la z por debajo y la l y la
p sin tocarse."""


def trazos_en_unidades() -> list[list[Punto]]:
    """Los cinco trazos, en unidades de la fuente (y hacia abajo)."""
    _, _, f = GLIFOS["F"]
    origen_f = 0.0 - GLIFOS["F"][0]
    barra_y_fuste = [(origen_f + x, y) for x, y in f[0]] + [(origen_f + x, y) for x, y in f[1]]
    travesano = [(origen_f + x, y) for x, y in f[2]]
    sueltos, eliz, _ = _palabra("eliz", float(GLIFOS["F"][1]), 0.0)
    feliz = travesano + eliz

    y2 = INTERLINEA
    _, cumple, _ = _palabra("cumpleanos", SANGRIA, y2)
    swash = _swash(cumple[-1], SANGRIA + sum(GLIFOS[c][1] for c in LAZO_BAJO), y2)
    x_n = SANGRIA + sum(GLIFOS[c][1] for c in "cumplea") - GLIFOS["n"][0]
    tilde = [(x_n - 3.5, y2 - 3.0), (x_n - 1.5, y2 - 4.5), (x_n + 1.0, y2 - 3.0)]
    tilde += [(x_n + 3.0, y2 - 4.5)]
    return [barra_y_fuste, feliz, *sueltos, tilde, cumple + swash]


def pedido() -> dict[str, object]:
    trazos = []
    for t in trazos_en_unidades():
        # Y hacia arriba, y en mm con la x de 10.
        trazos.append(trazo([(x * X_POR_UNIDAD, -y * X_POR_UNIDAD) for x, y in t]))
    return {"nombre": "feliz_cumpleanos", "trazos": trazos}


def vista(ruta: Path, datos: dict[str, object], escala: float = 6.0) -> None:
    """Un PNG del pedido, para mirarlo antes de compilarlo."""
    from PIL import Image, ImageDraw

    trazos = [np.array(t) for t in datos["trazos"]]  # type: ignore[attr-defined]
    todos = np.vstack(trazos)
    minimo, maximo = todos.min(0) - 6.0, todos.max(0) + 6.0
    ancho, alto = ((maximo - minimo) * escala).astype(int)
    imagen = Image.new("RGB", (int(ancho), int(alto)), "white")
    lapiz = ImageDraw.Draw(imagen)
    for t in trazos:
        xy = [((x - minimo[0]) * escala, alto - (y - minimo[1]) * escala) for x, y in t]
        lapiz.line(xy, fill=(18, 38, 110), width=3, joint="curve")
    ruta.parent.mkdir(parents=True, exist_ok=True)
    imagen.save(ruta)


def main(argv: list[str] | None = None) -> int:
    sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[union-attr]
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--vista", type=Path, help="guarda además un PNG del pedido")
    op = p.parse_args(argv)
    datos = pedido()
    DESTINO.write_text(json.dumps(datos, indent=1) + "\n", encoding="utf-8", newline="\n")
    print(f"{DESTINO.relative_to(RAIZ)}: {len(datos['trazos'])} trazos")  # type: ignore[arg-type]
    if op.vista:
        vista(op.vista, datos)
        print(f"vista en {op.vista}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
