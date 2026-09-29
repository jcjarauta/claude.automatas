"""C4 · Cadena de tolerancias: cuánto error llega a la punta del lápiz.

El error final no es la suma de las holguras: es la suma de cada holgura
**multiplicada por lo que la amplifica** el resto de la cadena. De ahí sale el
principio de diseño del proyecto: memoria grande, resultado pequeño. Un
pantógrafo que reduce cuatro veces divide por cuatro todo lo que venga de
antes.

Dos amplificaciones importan:

**Del perfil al seguidor.** Un error `δ` en el perfil desplaza el centro del
rodillo esa misma distancia en la dirección de la normal. Pero el rodillo solo
puede moverse por su arco, y la proyección del arco sobre la normal vale
`cos φ`. Hace falta recorrer `δ / cos φ` de arco para absorberlo, así que

    δψ = δ / (brazo · cos φ)

Es la segunda razón para vigilar el ángulo de presión: a 60° el error se
duplica; a 80°, se multiplica por seis.

**Del seguidor a la punta.** El jacobiano del actuador, calculado por
diferencias finitas porque así vale para cualquier cinemática del registro sin
tener que derivarla a mano.

Se dan dos totales. El **peor caso** suma los errores, y es lo que hay que
usar para prometer una tolerancia. El **cuadrático** los compone en raíz de la
suma de cuadrados, que es lo que se mide en la práctica cuando las holguras
son independientes y no conspiran todas en el mismo sentido.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np
import numpy.typing as npt

from core.actors.base import Actuador

Arreglo = npt.NDArray[np.float64]

_PASO_DERIVADA = 1e-7
"""Paso de las diferencias finitas, en radianes. Compromiso entre el error de
truncamiento y el de redondeo en coma flotante de doble precisión."""


@dataclass(frozen=True)
class Contribucion:
    """Una holgura y lo que la amplifica el resto de la cadena."""

    nombre: str
    magnitud: float
    """En metros o radianes, según de dónde venga."""
    amplificacion: float
    """Metros de error en la punta por unidad de magnitud."""

    def __post_init__(self) -> None:
        if self.magnitud < 0.0:
            raise ValueError(f"'{self.nombre}': la magnitud no puede ser negativa")
        if self.amplificacion < 0.0:
            raise ValueError(f"'{self.nombre}': la amplificación no puede ser negativa")

    @property
    def en_punta(self) -> float:
        """Lo que esta holgura sola aporta al error final, en metros."""
        return self.magnitud * self.amplificacion


@dataclass(frozen=True)
class CadenaTolerancias:
    contribuciones: tuple[Contribucion, ...]

    @property
    def peor_caso(self) -> float:
        """Todas las holguras conspirando en el mismo sentido."""
        return float(sum(c.en_punta for c in self.contribuciones))

    @property
    def cuadratica(self) -> float:
        """Holguras independientes, compuestas en cuadratura."""
        return math.sqrt(sum(c.en_punta**2 for c in self.contribuciones))

    @property
    def dominante(self) -> Contribucion | None:
        """La holgura que más aporta. Por dónde empezar a mejorar."""
        if not self.contribuciones:
            return None
        return max(self.contribuciones, key=lambda c: c.en_punta)


def amplificacion_perfil_a_seguidor(brazo: float, angulo_presion: float) -> float:
    """Radianes de giro del seguidor por metro de error en el perfil.

    Crece sin límite al acercarse el ángulo de presión a 90°, que es justo lo
    que significa esa singularidad: el contacto deja de poder mover al
    seguidor.
    """
    if brazo <= 0.0:
        raise ValueError(f"el brazo debe ser positivo, no {brazo}")
    coseno = math.cos(angulo_presion)
    if coseno <= 1e-9:
        return math.inf
    return 1.0 / (brazo * coseno)


def amplificacion_seguidor_a_punta(
    actuador: Actuador,
    psi: Arreglo,
    seguidor: int,
) -> float:
    """Metros de desplazamiento de la punta por radián del seguidor indicado.

    Por diferencias finitas centradas sobre la cinemática directa, así que
    funciona con cualquier actuador del registro sin derivarlo a mano.
    """
    base = np.atleast_2d(np.asarray(psi, dtype=np.float64))
    if base.shape[0] != 1:
        raise ValueError("se evalúa en una sola posición del ciclo")
    mas = base.copy()
    menos = base.copy()
    mas[0, seguidor] += _PASO_DERIVADA
    menos[0, seguidor] -= _PASO_DERIVADA
    delta = actuador.directa(mas) - actuador.directa(menos)
    return float(np.linalg.norm(delta) / (2.0 * _PASO_DERIVADA))


def cadena(
    actuador: Actuador,
    psi: Arreglo,
    *,
    brazos_seguidor: tuple[float, ...],
    angulos_presion: tuple[float, ...],
    error_perfil: float,
    holgura_pivote: float,
    reduccion: float = 1.0,
) -> CadenaTolerancias:
    """Monta la cadena completa en una posición del ciclo.

    `error_perfil` es lo que se desvía la pieza cortada, en metros: kerf mal
    compensado, imprecisión de la máquina, desgaste. `holgura_pivote` es el
    juego angular de cada articulación, en radianes. `reduccion` es lo que
    divide el pantógrafo, si lo hay: es el número que hace pequeño todo lo
    anterior.
    """
    if reduccion <= 0.0:
        raise ValueError(f"la reducción debe ser positiva, no {reduccion}")
    n = len(brazos_seguidor)
    if len(angulos_presion) != n:
        raise ValueError("hace falta un ángulo de presión por seguidor")

    contribuciones: list[Contribucion] = []
    for i in range(n):
        a_punta = amplificacion_seguidor_a_punta(actuador, psi, i) / reduccion
        de_perfil = amplificacion_perfil_a_seguidor(brazos_seguidor[i], angulos_presion[i])
        contribuciones.append(
            Contribucion(
                nombre=f"perfil del seguidor {i}",
                magnitud=error_perfil,
                amplificacion=de_perfil * a_punta,
            )
        )
        contribuciones.append(
            Contribucion(
                nombre=f"holgura del pivote {i}",
                magnitud=holgura_pivote,
                amplificacion=a_punta,
            )
        )
    return CadenaTolerancias(contribuciones=tuple(contribuciones))
