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


def giro_del_eje(
    desviacion: float,
    c: Contratos | None = None,
    bieleta: Bieleta | None = None,
) -> float:
    """Radianes que gira el eje del balancín con el seguidor 3 desviado
    `desviacion` de su punto de diseño. Positivo es bajar la mesa.

    Cierra el lazo de la bieleta: el pasador del seguidor en su arco, el ojo
    del balancín en el suyo —arriba del eje, en x = x_eje + entrada·sen(giro)—
    y la varilla rígida entre los dos. Bisección: el seguidor se mueve
    décimas de grado y la función es monótona en ese tramo.
    """
    c = c or cargar()
    b = bieleta or bieleta_isogona(c)
    r = _m(c, "levantamiento_pasador_al_pivote")
    e = _m(c, "balancin_entrada")
    psi0 = math.atan2(b.pasador[1] - b.pivote[1], b.pasador[0] - b.pivote[0])
    sx = b.pivote[0] + r * math.cos(psi0 + desviacion)
    sy = b.pivote[1] + r * math.sin(psi0 + desviacion)
    x_eje = b.ojo[0]

    def resto(g: float) -> float:
        return math.hypot(x_eje + e * math.sin(g) - sx, b.ojo[1] - sy) - b.largo

    a, z = -0.5, 0.5
    for _ in range(80):
        medio = (a + z) / 2
        a, z = (medio, z) if (resto(medio) > 0) == (resto(a) > 0) else (a, medio)
    return (a + z) / 2


def caida_de_la_mesa(giro: float, c: Contratos | None = None) -> float:
    """Metros que baja la mesa desde la posición de escritura. La palanca va
    a -calaje escribiendo, así que su perno baja palanca·(sen giro + sen calaje)."""
    c = c or cargar()
    palanca = _m(c, "brazo_palanca")
    return palanca * (math.sin(giro) + math.sin(calaje_elevador(c)))


@dataclass(frozen=True)
class Pila:
    """Las alturas de la cadena, en metros sobre la cara alta de la base."""

    seguidores: float
    """Cara baja del plano de seguidores."""
    eje_balancin: float
    """Eje del balancín: el cubo del balancín libra los seguidores con
    `holgura_minima`, porque el balancín apunta hacia arriba."""
    ojo: float
    """Pasador del balancín, a media altura de levantamiento."""
    plato2_abajo: float


def pila(c: Contratos | None = None) -> Pila:
    c = c or cargar()
    plato1_arriba = _m(c, "base_al_plato") + _m(c, "platina_espesor")
    seguidores = plato1_arriba + _m(c, "leva_sobre_plato") + _m(c, "seguidor_plano_z")
    eje = (
        seguidores
        + _m(c, "seguidor_espesor")
        + _m(c, "holgura_minima")
        + _m(c, "balancin_cubo_diametro") / 2
    )
    return Pila(
        seguidores=seguidores,
        eje_balancin=eje,
        ojo=eje + _m(c, "balancin_entrada"),
        plato2_abajo=plato1_arriba + _m(c, "poste_vano"),
    )


def apoyo_balancin_alto(c: Contratos | None = None) -> float:
    """De la cara baja del plato 2 a `apoyo_balancin_bajo_eje` bajo el eje."""
    c = c or cargar()
    p = pila(c)
    return p.plato2_abajo - (p.eje_balancin - _m(c, "apoyo_balancin_bajo_eje"))


def bieleta_pata_seguidor(c: Contratos | None = None) -> float:
    """La pata vertical de la bieleta: del ojo a la cara baja del seguidor."""
    p = pila(c or cargar())
    return p.ojo - p.seguidores


def tirante_largo(c: Contratos | None = None) -> float:
    """Del perno de la palanca, con la mesa arriba, al eje móvil trasero; más
    el radio del bulón por arriba y 2 bajo el ojo por abajo."""
    c = c or cargar()
    perno = pila(c).eje_balancin + _m(c, "brazo_palanca") * math.sin(calaje_elevador(c))
    return perno - _m(c, "mesa_bisagra_z") + _m(c, "brazo_perno_diametro") / 2 + 0.002


__all__ = [
    "Bieleta",
    "Pila",
    "al_cinco_barras",
    "apoyo_balancin_alto",
    "bieleta_isogona",
    "bieleta_pata_seguidor",
    "caida_de_la_mesa",
    "calaje_elevador",
    "eje_balancin_x",
    "giro_del_eje",
    "pila",
    "tirante_largo",
]
