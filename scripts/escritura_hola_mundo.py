"""Escribe demo/hola_mundo.json: «Hola Mundo» en cursiva enlazada, con
florituras.

    uv run python scripts/escritura_hola_mundo.py

Es el pedido de prueba de las tolerancias y las medidas nuevas: mucha más
curva que «hola», lazos en la H, la l y la d, y una rúbrica que sale de la
última o y vuelve subrayando las dos palabras con un lazo al final.

**Dos trazos y nada más.** La capacidad la pone la vuelta: cada trazo se
lleva al menos 6° y cada vuelo reserva 16° para subir y bajar el lápiz. Así
que una frase con florituras se escribe como se escribe a mano, enlazada:
«Hola» de un tirón y «Mundo» con su rúbrica de otro.

Las letras son puntos de control a mano, en unidades de altura de x (la o
mide 1, la l mide 2), y las une un spline cúbico por longitud de cuerda: así
el trazo es liso y el compilador no tiene que redondear más que las puntas
que de verdad lo son. Determinista: el mismo archivo cada vez.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
from scipy.interpolate import CubicSpline

RAIZ = Path(__file__).resolve().parent.parent
DESTINO = RAIZ / "demo" / "hola_mundo.json"
SIN_RUBRICA = RAIZ / "demo" / "hola_mundo_sin_rubrica.json"

ESCALA = 10.0
"""mm por unidad de altura de x. El compilador encaja la frase en la caja de
escritura, así que solo fija las proporciones."""

MUESTRAS_POR_TRAMO = 24

HOLA = [
    # rizo de entrada
    (-0.45, 1.4),
    (-0.4, 1.75),
    (-0.15, 2.0),
    (0.12, 1.95),
    (0.22, 1.7),
    # palo izquierdo de la H, y giro en U abajo hacia la subida fina
    (0.2, 1.2),
    (0.16, 0.5),
    (0.12, 0.15),
    (0.2, 0.02),
    (0.36, 0.06),
    (0.48, 0.35),
    # subida al palo derecho, giro en U arriba y bajada
    (0.62, 1.3),
    (0.72, 1.82),
    (0.82, 2.0),
    (0.94, 1.9),
    (0.9, 1.5),
    (0.86, 1.0),
    (0.84, 0.4),
    (0.88, 0.12),
    # giro abajo y travesaño en lazo, que enlaza con la o
    (0.98, 0.02),
    (1.12, 0.12),
    (1.12, 0.45),
    (0.95, 0.8),
    (0.62, 1.0),
    (0.4, 0.95),
    (0.36, 0.84),
    (0.5, 0.75),
    (0.82, 0.82),
    (1.16, 0.9),
    # o, y su lazo de enlace arriba
    (1.42, 1.0),
    (1.22, 0.86),
    (1.13, 0.45),
    (1.28, 0.05),
    (1.55, 0.04),
    (1.72, 0.4),
    (1.66, 0.85),
    (1.48, 1.0),
    (1.36, 0.92),
    (1.44, 0.79),
    (1.66, 0.8),
    (1.9, 0.88),
    # l, lazo alto ancho
    (2.08, 1.2),
    (2.22, 1.72),
    (2.3, 1.98),
    (2.2, 2.08),
    (2.05, 1.96),
    (2.02, 1.6),
    (2.06, 0.9),
    (2.12, 0.3),
    (2.24, 0.04),
    (2.42, 0.06),
    (2.58, 0.36),
    # a: el óvalo, la subida, giro arriba y la bajada con su salida
    (2.98, 0.86),
    (2.84, 0.99),
    (2.62, 0.86),
    (2.55, 0.45),
    (2.68, 0.07),
    (2.9, 0.08),
    (3.04, 0.42),
    (3.08, 0.84),
    (3.16, 1.0),
    (3.26, 0.92),
    (3.24, 0.55),
    (3.24, 0.2),
    (3.32, 0.03),
    (3.5, 0.06),
    (3.66, 0.34),
]

MUNDO = [
    # M: tres arcos, y entre ellos giros en U abajo
    (3.95, 0.0),
    (4.03, 0.55),
    (4.1, 0.9),
    (4.2, 1.03),
    (4.3, 0.9),
    (4.34, 0.5),
    (4.36, 0.2),
    (4.42, 0.04),
    (4.5, 0.0),
    (4.58, 0.04),
    (4.64, 0.2),
    (4.68, 0.55),
    (4.72, 0.9),
    (4.8, 1.03),
    (4.9, 0.9),
    (4.94, 0.5),
    (4.96, 0.2),
    (5.02, 0.04),
    (5.1, 0.0),
    (5.18, 0.04),
    (5.24, 0.2),
    (5.28, 0.55),
    (5.32, 0.9),
    (5.4, 1.03),
    (5.5, 0.9),
    (5.54, 0.5),
    (5.56, 0.2),
    (5.62, 0.04),
    (5.72, 0.02),
    (5.84, 0.15),
    # u: giros en U arriba y abajo
    (5.94, 0.55),
    (6.0, 0.9),
    (6.08, 1.0),
    (6.15, 0.92),
    (6.14, 0.5),
    (6.16, 0.2),
    (6.24, 0.03),
    (6.36, 0.0),
    (6.48, 0.08),
    (6.56, 0.35),
    (6.6, 0.75),
    (6.66, 0.97),
    (6.74, 1.02),
    (6.8, 0.92),
    (6.78, 0.5),
    (6.8, 0.15),
    (6.88, 0.02),
    (7.0, 0.02),
    (7.1, 0.15),
    # n
    (7.16, 0.6),
    (7.2, 0.94),
    (7.28, 1.02),
    (7.35, 0.94),
    (7.33, 0.5),
    (7.32, 0.15),
    (7.37, 0.03),
    (7.46, 0.04),
    (7.52, 0.25),
    (7.58, 0.7),
    (7.68, 0.98),
    (7.83, 1.0),
    (7.93, 0.8),
    (7.96, 0.4),
    (7.98, 0.12),
    (8.06, 0.02),
    (8.18, 0.03),
    (8.28, 0.15),
    # d: óvalo, palo alto con su lazo y salida
    (8.6, 0.9),
    (8.46, 1.0),
    (8.28, 0.86),
    (8.24, 0.45),
    (8.36, 0.06),
    (8.56, 0.06),
    (8.7, 0.35),
    (8.74, 0.8),
    (8.8, 1.4),
    (8.86, 1.9),
    (8.82, 2.05),
    (8.7, 2.0),
    (8.68, 1.7),
    (8.72, 1.2),
    (8.76, 0.6),
    (8.78, 0.2),
    (8.86, 0.03),
    (9.0, 0.04),
    (9.12, 0.2),
    # o y su lazo de enlace
    (9.38, 1.0),
    (9.2, 0.86),
    (9.14, 0.45),
    (9.27, 0.05),
    (9.5, 0.05),
    (9.62, 0.4),
    (9.57, 0.85),
    (9.42, 1.0),
    (9.31, 0.92),
    (9.39, 0.8),
    (9.62, 0.82),
    # la rúbrica: sale de la o, baja y vuelve subrayando hasta debajo de la H
    (9.87, 0.74),
    (10.06, 0.44),
    (10.0, -0.15),
    (9.6, -0.42),
    (7.0, -0.52),
    (4.0, -0.5),
    (1.5, -0.42),
    (0.4, -0.3),
    # y el lazo final
    (0.0, -0.1),
    (0.15, 0.08),
    (0.5, -0.05),
    (0.65, -0.4),
    (0.4, -0.68),
    (0.1, -0.55),
    (0.2, -0.38),
    (0.8, -0.45),
    (2.0, -0.7),
    (3.6, -0.68),
]


PASO = 0.25
"""mm de arco entre puntos del trazo."""

SUAVIZADO = 1.6
"""mm. El sigma del filtro gaussiano a lo largo del trazo: cada pico de la
letra se convierte en una curva de radio de ese orden. Sin él, los fondos de
la M, la u y la n tenían radios de centésimas de milímetro, la leva más
pequeña de la pila salía con 1,3 mm de radio de curvatura contra un rodillo
de 3 y el compilador la rechazaba por socavada. El redondeo de esquinas del
compilador no lo arregla: busca ángulos entre segmentos, y en un spline
denso cada segmento gira poco. Es el mínimo con el que el pedido es apto,
para no comerse más floritura de la necesaria."""


def trazo(puntos: list[tuple[float, float]], suavizado: float = SUAVIZADO) -> list[list[float]]:
    """Los puntos de control por un spline cúbico parametrizado por la
    longitud de cuerda, remuestreado cada `PASO` mm de arco y suavizado con un
    gaussiano de `suavizado` mm, con los dos extremos quietos. En mm."""
    from scipy.ndimage import gaussian_filter1d

    p = np.array(puntos, dtype=float) * ESCALA
    cuerda = np.concatenate([[0.0], np.cumsum(np.linalg.norm(np.diff(p, axis=0), axis=1))])
    sx, sy = CubicSpline(cuerda, p[:, 0]), CubicSpline(cuerda, p[:, 1])
    t = np.linspace(0.0, cuerda[-1], (len(p) - 1) * MUESTRAS_POR_TRAMO * 4 + 1)
    denso = np.column_stack([sx(t), sy(t)])
    arco = np.concatenate([[0.0], np.cumsum(np.linalg.norm(np.diff(denso, axis=0), axis=1))])
    s = np.arange(0.0, arco[-1], PASO)
    linea = np.column_stack([np.interp(s, arco, denso[:, 0]), np.interp(s, arco, denso[:, 1])])
    if suavizado > 0:
        sigma = suavizado / PASO
        liso = gaussian_filter1d(linea, sigma, axis=0, mode="nearest")
        # Los extremos, donde empieza y acaba la tinta, no se mueven.
        peso = np.clip(np.minimum(s, s[-1] - s) / (3 * suavizado), 0.0, 1.0)[:, None]
        linea = peso * liso + (1 - peso) * linea
    return [[round(float(x), 4), round(float(y), 4)] for x, y in linea]


FIN_DE_LA_O = MUNDO.index((9.62, 0.82)) + 1
"""Donde acaba la o de «Mundo» y empieza la rúbrica."""


def pedido() -> dict[str, object]:
    return {"nombre": "hola_mundo", "trazos": [trazo(HOLA), trazo(MUNDO)]}


def pedido_sin_rubrica() -> dict[str, object]:
    """Las mismas dos palabras con sus lazos, sin la rúbrica: 342 mm de tinta.
    Es lo que cabe en una vuelta con el cabestrante 8:1; con la rúbrica son
    451 y la leva de arriba sale socavada."""
    return {
        "nombre": "hola_mundo_sin_rubrica",
        "trazos": [trazo(HOLA), trazo(MUNDO[:FIN_DE_LA_O])],
    }


EXCLAMACION = RAIZ / "demo" / "hola_mundo_exclamacion.json"

ABRE = (
    [(-0.85, 1.02), (-0.86, 0.94), (-0.87, 0.86)],
    [(-0.86, 0.62), (-0.9, 0.0), (-0.95, -0.6)],
)
"""«¡»: el punto arriba, a la altura de x, y el palo que baja por debajo de
la línea. Primero el punto, como se escribe."""

CIERRA = (
    [(9.98, 2.0), (9.94, 1.2), (9.9, 0.42)],
    [(9.89, 0.16), (9.88, 0.08), (9.87, 0.0)],
)
"""«!»: el palo desde la altura de la l y el punto sobre la línea."""


def pedido_exclamacion() -> dict[str, object]:
    """«¡Hola Mundo!»: las dos palabras sin la rúbrica, que no cabe, y los
    dos signos como trazos sueltos —palo y punto—, que es como se escriben.
    Los puntos son trazos de un milímetro: la máquina no sabe tocar y
    levantar sin moverse, sabe escribir un trazo corto.

    En una vuelta no cabe: seis trazos son cinco vuelos de 16°, la tinta se
    aprieta en lo que queda y dos levas salen socavadas. Va en dos renglones
    en la misma línea del papel —«¡Hola» y «Mundo!»—, un cartucho por
    vuelta, que es lo que propone la propia envolvente."""
    return {
        "nombre": "hola_mundo_exclamacion",
        "trazos": [
            *(trazo(t, suavizado=0.0) for t in ABRE),
            trazo(HOLA),
            trazo(MUNDO[:FIN_DE_LA_O]),
            *(trazo(t, suavizado=0.0) for t in CIERRA),
        ],
        "renglones": [[0, 1, 2], [3, 4, 5]],
    }


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[union-attr]
    for destino, datos in (
        (DESTINO, pedido()),
        (SIN_RUBRICA, pedido_sin_rubrica()),
        (EXCLAMACION, pedido_exclamacion()),
    ):
        destino.write_text(json.dumps(datos, indent=1) + "\n", encoding="utf-8", newline="\n")
        print(f"{destino.relative_to(RAIZ)}: {len(datos['trazos'])} trazos")  # type: ignore[arg-type]
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
