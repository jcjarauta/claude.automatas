"""La cadena del levantamiento: dónde cae lo que el contrato no puede elegir.

El seguidor 3 empuja un balancín por medio de una bieleta, el balancín gira el
eje que lleva la palanca del lápiz y la palanca baja la mesa por el tirante.
Tres cotas de esa cadena **no son elecciones**, salen de la geometría que ya
está fijada en otro sitio, y aquí se calculan para que el contrato no las
copie de memoria:

- **dónde está el pasador del seguidor 3**: en el agujero a
  `levantamiento_pasador_al_pivote` del pivote, a lo largo del brazo, con el
  seguidor en su punto de diseño. Se dio por hecho que caía en el eje de
  simetría del cinco barras y cae a 29 mm de él.
- **la bieleta isógona**: la dirección que hace que el balancín se mueva lo
  mismo que el pasador. La relación entre el seguidor y la palanca es
  entonces exactamente la del balancín, 6, sea cual sea el ángulo de la
  bieleta con cada movimiento. Una bieleta articulada en sus dos extremos
  trabaja a tracción o compresión puras con cualquier ángulo; lo que el
  ángulo cambia es la relación, y la isógona la deja en 1.
- **la x del eje del balancín**: la que pone el tirante en `tirante_x` con la
  palanca a ±calaje, no horizontal.

Todo en SI y en el marco del cinco barras. Lo que se cruza contra el
contrato está en `tests/compile/test_levantamiento.py`.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from compile.contratos import Contratos, cargar
from compile.escribiente import Escribiente
from core.escritura import Capacidad

SEGUIDOR_DEL_ELEVADOR = 2


def _m(c: Contratos, nombre: str) -> float:
    return float(c.variables()[nombre].valor)


def al_cinco_barras(c: Contratos, x: float, y: float) -> tuple[float, float]:
    """Del marco de la leva al del cinco barras: la inversa de la transformada
    del contrato (`brazo_origen_x/y`, `brazo_origen_giro`)."""
    g = _m(c, "brazo_origen_giro")
    x, y = x - _m(c, "brazo_origen_x"), y - _m(c, "brazo_origen_y")
    return (x * math.cos(g) + y * math.sin(g), -x * math.sin(g) + y * math.cos(g))


@dataclass(frozen=True)
class Bieleta:
    pivote: tuple[float, float]
    """El del seguidor 3, en el marco del cinco barras."""
    pasador: tuple[float, float]
    """El pasador del seguidor 3 en su punto de diseño."""
    ojo: tuple[float, float]
    """El pasador del balancín, a media altura de levantamiento."""
    direccion: tuple[float, float]
    """Unitaria, del pasador del seguidor al ojo del balancín."""
    factor: float
    """Lo que se mueve el ojo por cada metro del pasador. La isógona: 1."""

    @property
    def largo(self) -> float:
        return math.dist(self.pasador, self.ojo)


def calaje_elevador(c: Contratos, capacidad: Capacidad | None = None) -> float:
    """Radianes: la palanca a media altura de levantamiento."""
    capacidad = capacidad or Capacidad()
    return math.asin(float(capacidad.altura_levantamiento) / 2 / _m(c, "brazo_palanca"))


def eje_balancin_x(c: Contratos, capacidad: Capacidad | None = None) -> float:
    """La x del eje que pone el tirante en `tirante_x` con la palanca a ±calaje."""
    return _m(c, "tirante_x") - _m(c, "brazo_palanca") * math.cos(calaje_elevador(c, capacidad))


def bieleta_isogona(c: Contratos | None = None, maquina: Escribiente | None = None) -> Bieleta:
    c = c or cargar()
    maquina = maquina or Escribiente()
    seguidor = maquina.seguidor(SEGUIDOR_DEL_ELEVADOR)
    r = _m(c, "levantamiento_pasador_al_pivote")
    px, py = float(seguidor.pivote[0]), float(seguidor.pivote[1])
    psi = float(seguidor.psi_cero)
    pivote = al_cinco_barras(c, px, py)
    pasador = al_cinco_barras(c, px + r * math.cos(psi), py + r * math.sin(psi))

    # t: por donde se mueve el pasador con desviación positiva (perpendicular
    # al brazo). m: por donde se mueve el ojo del balancín, que apunta hacia
    # arriba, cuando el eje gira en el sentido de bajar la mesa: +X.
    bx, by = pasador[0] - pivote[0], pasador[1] - pivote[1]
    n = math.hypot(bx, by)
    t = (-by / n, bx / n)
    m = (1.0, 0.0)
    w = (t[0] - m[0], t[1] - m[1])
    nw = math.hypot(*w)
    u = (-w[1] / nw, w[0] / nw)
    if u[0] < 0:
        u = (-u[0], -u[1])

    x_eje = eje_balancin_x(c)
    ojo = (x_eje, pasador[1] + (x_eje - pasador[0]) * u[1] / u[0])
    factor = (t[0] * u[0] + t[1] * u[1]) / (m[0] * u[0] + m[1] * u[1])
    return Bieleta(pivote=pivote, pasador=pasador, ojo=ojo, direccion=u, factor=factor)


__all__ = ["Bieleta", "al_cinco_barras", "bieleta_isogona", "calaje_elevador", "eje_balancin_x"]
