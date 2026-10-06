"""C12c · el contacto del escape Graham, en función del ángulo del áncora.

`core/reloj/graham.py` contesta si el escape funciona: gira el áncora y deja
avanzar la rueda hasta que toca. La dinámica del regulador necesita saber
algo más, y es lo que da este módulo, **sin una sola magnitud de tiempo**
(regla 1):

- **La ligadura.** Para cada paleta, a qué ángulo `φ` de la rueda toca el
  diente que le toca a esa paleta, con el áncora a `θ`. Mientras el diente
  apoya en el arco de reposo, `φ(θ)` es plana; mientras desliza por el plano
  de impulso, sube o baja con `θ`. Donde el diente ya ha pasado la esquina y
  no puede tocar, no está definida: eso es la caída.
- **La normal y el punto de contacto**, que dan los brazos sobre cada eje y,
  con ellos, cuánto par pasa de la rueda al péndulo y cuánto se queda en el
  rozamiento.

**De dónde sale la normal.** De la geometría que se corta, no de un ángulo
tecleado: se busca el par de puntos más cercanos entre diente y paleta y se
toma la normal del lado de la paleta donde cae el contacto. En el arco de
reposo es radial desde el eje del áncora, y por eso un Graham no empuja ni
frena al péndulo mientras bloquea: lo frena solo el rozamiento.

**Comprobación cruzada.** La pendiente de la ligadura, buscando el contacto,
y la que sale de los brazos (`-h_áncora / h_rueda`) son el mismo número por
dos caminos. `tests/reloj/test_contacto.py` exige que coincidan.

Convenios, los de `graham.py`: rueda en el origen girando en horario con
`φ > 0`; áncora en `(0, entre_centros)` con `θ > 0` antihorario.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Final

import numpy as np
import numpy.typing as npt
from shapely import prepare, transform
from shapely.geometry import Polygon
from shapely.ops import nearest_points

from core.reloj.graham import AncoraGraham, Lado, RuedaGraham, dientes, nariz, paleta
from core.units import Radianes, grados

Arreglo = npt.NDArray[np.float64]

TOLERANCIA_ARCO: Final[float] = 2.0e-5
"""m. Un contacto a menos de esto del radio del arco de reposo está en el arco:
su normal es radial desde el eje del áncora, exacta, y no la de la cuerda del
polígono que aproxima el arco."""

BISECCIONES: Final[int] = 40

PASO_DE_REJILLA: Final[Radianes] = grados(0.02)
"""Paso de θ de la tabla por defecto: 0,016 mm de recorrido de paleta."""


@dataclass(frozen=True)
class TablaDeContacto:
    """La ligadura de una paleta sobre una rejilla de `θ`.

    `phi` es el ángulo de la rueda al que toca el diente de referencia; `nan`
    donde ya no puede tocar. `punto` y `normal` (de la paleta hacia el
    diente) están en el marco del mundo, en metros.
    """

    lado: Lado
    theta: Arreglo
    phi: Arreglo
    punto: Arreglo
    normal: Arreglo
    eje_ancora: tuple[float, float]
    paso_rueda: Radianes


def _girar(geometria: Polygon, angulo: float, centro: tuple[float, float]) -> Polygon:
    c, s = math.cos(angulo), math.sin(angulo)
    giro = np.array([[c, -s], [s, c]])
    o = np.array(centro)
    return transform(geometria, lambda xy: np.asarray((xy - o) @ giro.T + o, dtype=np.float64))


def _diente_de(rueda: RuedaGraham, ancora: AncoraGraham, lado: Lado) -> tuple[Polygon, float]:
    """El diente que llega a esta paleta con la rueda en `φ = 0`, y el ángulo
    `φ` alrededor del cual la toca. Es el primero que, girando en horario,
    alcanza el punto de reposo de la nariz."""
    n = nariz(ancora, lado)
    beta = math.atan2(n.reposo[1], n.reposo[0])
    mejor: tuple[float, Polygon] | None = None
    for a, g in dientes(rueda):
        delante = (a - beta) % (2 * math.pi)
        if mejor is None or delante < mejor[0]:
            mejor = (delante, g)
    assert mejor is not None
    return mejor[1], mejor[0]


def _normal(
    pal: Polygon,
    diente: Polygon,
    en_paleta: tuple[float, float],
    en_diente: tuple[float, float],
    eje: tuple[float, float],
    radio_reposo: float,
) -> npt.NDArray[np.float64]:
    """Normal unitaria en el contacto, de la paleta hacia el diente."""
    p = np.array(en_paleta)
    hacia_diente = np.array(en_diente) - p
    if abs(math.hypot(p[0] - eje[0], p[1] - eje[1]) - radio_reposo) < TOLERANCIA_ARCO:
        n = p - np.array(eje)
        n = n / np.linalg.norm(n)
    else:
        n = _normal_de_lado(pal, p)
        if n is None:
            # La esquina de la paleta contra el flanco del diente: manda el
            # flanco, y su normal sale del diente.
            m = _normal_de_lado(diente, np.array(en_diente))
            n = -m if m is not None else hacia_diente
    if float(np.dot(n, hacia_diente)) < 0 or (
        np.linalg.norm(hacia_diente) < 1e-12
        and float(np.dot(n, np.array(diente.centroid.coords[0]) - p)) < 0
    ):
        n = -n
    return np.asarray(n / np.linalg.norm(n), dtype=np.float64)


def _normal_de_lado(poligono: Polygon, punto: npt.NDArray[np.float64]) -> Arreglo | None:
    """La normal del lado del contorno sobre el que cae `punto`, si cae en el
    interior de un lado; `None` si cae en un vértice."""
    xy = np.asarray(poligono.exterior.coords, dtype=np.float64)
    a, b = xy[:-1], xy[1:]
    d = b - a
    largo2 = np.einsum("ij,ij->i", d, d)
    t = np.clip(np.einsum("ij,ij->i", punto - a, d) / np.maximum(largo2, 1e-30), 0.0, 1.0)
    proyectado = a + d * t[:, None]
    distancia = np.linalg.norm(proyectado - punto, axis=1)
    i = int(np.argmin(distancia))
    if not 1e-3 < t[i] < 1 - 1e-3:
        return None
    lado = d[i] / math.sqrt(float(largo2[i]))
    return np.array([-lado[1], lado[0]])


def tabla_de_contacto(
    rueda: RuedaGraham,
    ancora: AncoraGraham,
    lado: Lado,
    amplitud: Radianes,
    paso: Radianes = PASO_DE_REJILLA,
) -> TablaDeContacto:
    """La ligadura de la paleta `lado` en `θ ∈ [-amplitud, amplitud]`.

    Para cada `θ` se busca por bisección el primer `φ` al que el diente de
    referencia toca la paleta, avanzando la rueda en horario desde donde
    todavía no puede tocarla. Si en todo el recorrido posible no la toca, el
    diente ya ha pasado: `nan`.
    """
    eje = ancora.eje_ancora
    pal0 = paleta(ancora, lado)
    diente, centro = _diente_de(rueda, ancora, lado)
    prepare(diente)
    radio_reposo = float(nariz(ancora, lado).radio_reposo)
    desde = centro - 0.55 * rueda.paso
    hasta = centro + 0.55 * rueda.paso

    thetas = np.arange(-amplitud, amplitud + paso / 2, paso)
    phi = np.full(len(thetas), np.nan)
    puntos = np.full((len(thetas), 2), np.nan)
    normales = np.full((len(thetas), 2), np.nan)
    for i, th in enumerate(thetas):
        pal = _girar(pal0, float(th), eje)

        def toca(f: float, pal: Polygon = pal) -> bool:
            # Girar la rueda -f es girar la paleta +f alrededor del centro.
            return bool(diente.intersects(_girar(pal, f, (0.0, 0.0))))

        if toca(desde):
            continue
        a, b = desde, None
        f = desde
        while f < hasta:
            f += rueda.paso / 200
            if toca(f):
                b = f
                break
            a = f
        if b is None:
            continue
        for _ in range(BISECCIONES):
            m = (a + b) / 2
            if toca(m):
                b = m
            else:
                a = m
        phi[i] = a
        # El contacto, en el marco del mundo: la rueda girada -a.
        diente_mundo = _girar(diente, -a, (0.0, 0.0))
        en_diente, en_paleta = nearest_points(diente_mundo, pal)
        pd, pp = (en_diente.x, en_diente.y), (en_paleta.x, en_paleta.y)
        puntos[i] = ((pd[0] + pp[0]) / 2, (pd[1] + pp[1]) / 2)
        normales[i] = _normal(pal, diente_mundo, pp, pd, eje, radio_reposo)
    return TablaDeContacto(
        lado=lado,
        theta=np.asarray(thetas, dtype=np.float64),
        phi=phi,
        punto=puntos,
        normal=normales,
        eje_ancora=eje,
        paso_rueda=rueda.paso,
    )


def brazos(tabla: TablaDeContacto, eje_ancora: tuple[float, float]) -> tuple[Arreglo, Arreglo]:
    """(h_rueda, h_áncora): el brazo de la normal sobre cada eje, con signo
    `(r × n)_z`. Multiplicados por la fuerza normal dan el par antihorario
    sobre cada uno."""
    c, n = tabla.punto, tabla.normal
    a = c - np.array(eje_ancora)
    h_rueda = c[:, 0] * n[:, 1] - c[:, 1] * n[:, 0]
    h_ancora = a[:, 0] * n[:, 1] - a[:, 1] * n[:, 0]
    return np.asarray(h_rueda, dtype=np.float64), np.asarray(h_ancora, dtype=np.float64)


def angulo_de_presion(tabla: TablaDeContacto) -> Arreglo:
    """Entre la normal y la dirección en que se mueve el punto del diente
    cuando la rueda gira: cero es empujar de frente; cuanto mayor, más fuerza
    se va en apretar contra el eje y menos en mover el áncora."""
    c, n = tabla.punto, tabla.normal
    # La rueda gira en horario: el punto del diente va en (y, -x).
    v = np.stack([c[:, 1], -c[:, 0]], axis=1)
    v = v / np.linalg.norm(v, axis=1)[:, None]
    coseno = np.abs(np.einsum("ij,ij->i", v, n))
    return np.asarray(np.arccos(np.clip(coseno, 0.0, 1.0)), dtype=np.float64)


__all__ = ["TablaDeContacto", "angulo_de_presion", "brazos", "tabla_de_contacto"]
