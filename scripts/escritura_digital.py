"""Escribe demo/hola_mundo_digital.json: «¡Hola Mundo!» en letra digital.

    uv run python scripts/escritura_digital.py

**Letra digital**: monolínea, recta sobre una rejilla, como la de un
visor: cada letra son tramos rectos y esquinas, sin curvas de mano ni
florituras. Las esquinas las redondea el suavizado (`SUAVIZADO`), que es lo
que la leva puede seguir.

**Todo en un juego de levas.** Cada levantamiento del lápiz se lleva 16° de
la vuelta, así que las letras de una palabra van enlazadas por la línea
base en un solo trazo, y donde una letra tiene que volver sobre sí misma
(el palo de la l, el de la d, el travesaño de la H) el lápiz desanda su
propia línea: el trazo se invierte, y eso la leva lo sigue porque cada
coordenada sigue siendo lisa. Los signos son palo y punto, como se
escriben.

Las letras son polilíneas en unidades de altura de x (la o mide 1, la l
1,6). Determinista: el mismo archivo cada vez.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

RAIZ = Path(__file__).resolve().parent.parent
DESTINO = RAIZ / "demo" / "hola_mundo_digital.json"

ESCALA = 10.0
"""mm por unidad de altura de x; el compilador encaja la frase en su caja."""

PASO = 0.25
"""mm de arco entre puntos del trazo."""

SUAVIZADO = 1.0
"""mm: un gaussiano ligero sobre el trazo ya redondeado, para que la
curvatura no salte al entrar y salir de cada arco."""

HUECO = 0.28
"""Entre letras, por la línea base."""

ANCHO_DE_PALO = 0.24
"""Ancho de los palos de ida y vuelta: donde una letra digital volvería
sobre su propia línea —el palo de la l, la d, la u, la H— el trazo sube por
un lado y baja por el otro. La leva no puede dar media vuelta en el sitio;
sí un lazo estrecho de este ancho, que se lee como un palo hueco."""

RADIO = 0.15
"""Radio de las esquinas, en altura de x. Es lo que la leva puede seguir."""

Polilinea = list[tuple[float, float]]


def letras(w: float = ANCHO_DE_PALO) -> dict[str, Polilinea]:
    """Cada letra, un camino sin vueltas atrás: entra por abajo a la
    izquierda (0, 0) y el último punto es por donde sale. Las que abren
    palabra (H, M) empiezan donde se empieza a escribirlas."""
    return {
        # H: empieza arriba con el palo izquierdo limpio, rodea abajo, sube al
        # travesaño y el palo derecho es hueco arriba
        "H": [
            (0, 1.5),
            (0, 0),
            (w, 0),
            (w, 0.75),
            (0.85, 0.75),
            (0.85, 1.5),
            (0.85 + w, 1.5),
            (0.85 + w, 0),
        ],
        "M": [(0, 0), (0, 1.5), (0.45, 0.55), (0.9, 1.5), (0.9, 0)],
        # o: la base dos veces, en el mismo sentido, para salir por la derecha
        "o": [(0, 0), (0.6, 0), (0.6, 1), (0, 1), (0, 0), (0.6, 0)],
        "l": [(0, 0), (0, 1.6), (w, 1.6), (w, 0)],
        # a de un piso: base, palo derecho hueco hasta la altura de x, techo
        # de la panza y lado izquierdo; acaba la palabra
        "a": [(0, 0), (0.6, 0), (0.6, 1), (0.6 + w, 1), (0.6 + w, 0.6), (0, 0.6), (0, 0)],
        "u": [(0, 0), (0, 1), (w, 1), (w, 0), (0.6, 0), (0.6, 1), (0.6 + w, 1), (0.6 + w, 0)],
        "n": [(0, 0), (0, 1), (0.6, 1), (0.6, 0)],
        # d: base, palo alto hueco, techo de la panza y lado izquierdo
        "d": [
            (0, 0),
            (0.6, 0),
            (0.6, 1.6),
            (0.6 + w, 1.6),
            (0.6 + w, 1),
            (0, 1),
            (0, 0),
            (0.6 + w, 0),
        ],
    }


def palabra(texto: str, x0: float, w: float = ANCHO_DE_PALO) -> tuple[Polilinea, float]:
    """Las letras de una palabra en un solo trazo: de la salida de una a la
    entrada de la siguiente, por la línea base. Devuelve el trazo y dónde
    acaba a la derecha."""
    formas = letras(w)
    puntos: Polilinea = []
    x = x0
    for letra in texto:
        forma = [(x + px, py) for px, py in formas[letra]]
        if puntos and puntos[-1] == forma[0]:
            forma = forma[1:]
        puntos += forma
        x = max(px for px, _ in forma) + HUECO
    return puntos, x - HUECO


def con_esquinas_redondas(puntos: Polilinea, radio: float) -> Polilinea:
    """Cada esquina, un arco de `radio` (en unidades de la letra) tangente a
    sus dos tramos; los tramos rectos siguen rectos. Así la letra conserva su
    forma, y la leva no ve ninguna esquina viva. Las letras no tienen vueltas
    atrás (`letras`): una media vuelta en el sitio no hay leva que la siga."""
    p = [np.array(q, dtype=float) for q in puntos]
    salida: list[np.ndarray] = [p[0]]
    for i in range(1, len(p) - 1):
        a, b, c = p[i - 1], p[i], p[i + 1]
        u, v = b - a, c - b
        lu, lv = float(np.linalg.norm(u)), float(np.linalg.norm(v))
        if lu < 1e-9 or lv < 1e-9:
            continue
        u, v = u / lu, v / lv
        giro = float(np.arctan2(u[0] * v[1] - u[1] * v[0], float(np.dot(u, v))))
        if abs(giro) < 1e-6:
            salida.append(b)
            continue
        if abs(giro) > np.pi - 1e-3:
            raise ValueError(f"vuelta atrás en {tuple(b)}: la letra tiene que rodear, no volver")
        # El arco tangente: retrocede d = r·tan(giro/2) por cada tramo.
        r = radio
        d = r * np.tan(abs(giro) / 2)
        d = min(d, lu / 2, lv / 2)
        r = d / np.tan(abs(giro) / 2)
        inicio = b - u * d
        normal = np.array([-u[1], u[0]]) * np.sign(giro)
        centro = inicio + normal * r
        a0 = np.arctan2(*(inicio - centro)[::-1])
        for t in np.linspace(0.0, giro, 9):
            salida.append(centro + r * np.array([np.cos(a0 + t), np.sin(a0 + t)]))
    salida.append(p[-1])
    return [(float(q[0]), float(q[1])) for q in salida]


def trazo(puntos: Polilinea, suavizado: float = SUAVIZADO) -> list[list[float]]:
    """La polilínea remuestreada cada `PASO` mm de arco y suavizada con un
    gaussiano de `suavizado` mm, con los extremos quietos. En mm."""
    from scipy.ndimage import gaussian_filter1d

    p = np.array(puntos, dtype=float) * ESCALA
    tramos = np.linalg.norm(np.diff(p, axis=0), axis=1)
    arco = np.concatenate([[0.0], np.cumsum(tramos)])
    s = np.arange(0.0, arco[-1] + 1e-9, PASO)
    linea = np.column_stack([np.interp(s, arco, p[:, 0]), np.interp(s, arco, p[:, 1])])
    if suavizado > 0 and len(s) > 3:
        liso = gaussian_filter1d(linea, suavizado / PASO, axis=0, mode="nearest")
        peso = np.clip(np.minimum(s, s[-1] - s) / (3 * suavizado), 0.0, 1.0)[:, None]
        linea = peso * liso + (1 - peso) * linea
    return [[round(float(x), 4), round(float(y), 4)] for x, y in linea]


SEGUNDA_LINEA = -2.05
"""Base de «Mundo!», en alturas de x bajo la de «¡Hola». En dos líneas la
letra sale en el papel un tercio mayor que en una (la caja es de 80 × 30),
y la esquina mínima que pide la leva pesa un tercio menos en cada letra."""


def pedido() -> dict[str, object]:
    """«¡Hola» y «Mundo!» en dos líneas, un solo juego de levas: seis trazos
    —los dos signos son palo y punto— y cinco vuelos."""
    abre = -0.55
    hola, _ = palabra("Hola", 0.0)
    mundo, fin_mundo = palabra("Mundo", 0.0)
    b = SEGUNDA_LINEA
    mundo = [(x, y + b) for x, y in mundo]
    cierra = fin_mundo + 0.45
    trazos = [
        [(abre, 1.0), (abre, 0.9)],  # punto de ¡
        [(abre, 0.65), (abre, -0.55)],  # palo de ¡
        hola,
        mundo,
        [(cierra, 1.5 + b), (cierra, 0.4 + b)],  # palo de !
        [(cierra, 0.1 + b), (cierra, b)],  # punto de !
    ]
    return {
        "nombre": "hola_mundo_digital",
        "trazos": [trazo(con_esquinas_redondas(t, RADIO)) for t in trazos],
    }


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[union-attr]
    datos = pedido()
    DESTINO.write_text(json.dumps(datos, indent=1) + "\n", encoding="utf-8", newline="\n")
    tinta = sum(
        float(np.sum(np.linalg.norm(np.diff(np.array(t), axis=0), axis=1)))
        for t in datos["trazos"]  # type: ignore[union-attr]
    )
    print(f"{DESTINO.relative_to(RAIZ)}: {len(datos['trazos'])} trazos, {tinta:.0f} mm de tinta")  # type: ignore[arg-type]
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
