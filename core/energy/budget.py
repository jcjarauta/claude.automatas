"""C6 · Par y energía: cuánto cuesta girar el árbol, grado a grado.

La relación que lo sostiene todo sale de igualar potencias. Si la leva gira
un ángulo dθ y el seguidor responde girando dψ, el trabajo que entra por el
árbol es el que sale por el seguidor:

    T_arbol · dθ  =  T_seguidor · dψ
    T_arbol(θ)    =  T_seguidor(ψ) · ψ'(θ)

No hay tiempo en esa cuenta, y por eso encaja con la regla 1: **ψ' es la
derivada respecto de θ**, no respecto de t. Un seguidor parado en un reposo
tiene ψ' = 0 y no pide par por mucho que apriete su muelle, que es justo lo
que uno nota al girar una manivela.

El único término que sí necesita una velocidad es el de inercia, porque
acelerar el seguidor cuesta ψ''·ω². Se devuelve **aparte**, como coeficiente
que multiplica a ω²: así el núcleo sigue dando funciones de θ y quien decida
a qué velocidad se gira es el compilador, que para eso es quien decide.

Qué se le resiste al seguidor:

- **El muelle**, que es lo que mantiene el rodillo pegado a la leva. Sin él
  el seguidor despega en cuanto la leva baja deprisa, y entonces vuelve a
  caer de golpe: eso es el golpeteo que rompe las levas de madera.
- **El rozamiento** del pivote y del rodillo.
- **La carga útil**: el lápiz apoyado en el papel, lo que sea que mueva.
- **Su propia inercia**, que solo cuenta a velocidad apreciable.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import numpy.typing as npt
from pydantic import BaseModel, ConfigDict, Field

from core.units import TAU, Inercia, KgM2, NewtonMetro, Par

Arreglo = npt.NDArray[np.float64]

ROZAMIENTO_DEL_ARBOL: Par = NewtonMetro(0.02)
"""Lo que se llevan los rodamientos del árbol y el contacto de los tres
rodillos, medido en el propio árbol. Sin medir: se corrige en E4."""


class CargaSeguidor(BaseModel):
    """Lo que se le resiste a un seguidor, visto desde su pivote.

    Todo en el eje del seguidor: newton·metro y kg·m². Lo que pasa más allá
    —el varillaje, el lápiz— se trae aquí reducido, que es como se suman
    cosas que giran a distinta velocidad.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    par_muelle: Par = NewtonMetro(0.05)
    """Precarga: el par que el muelle hace ya en reposo. Es lo que impide que
    el rodillo despegue."""
    rigidez: float = Field(default=0.0, ge=0.0)
    """N·m por radián. Cero es un muelle de fuerza constante, que es lo ideal
    y casi nunca lo que hay."""
    rozamiento: Par = NewtonMetro(0.01)
    """Lo que se lleva el pivote y el rodillo, con signo contrario al giro."""
    inercia: Inercia = KgM2(1.0e-5)
    """Del brazo del seguidor y de lo que arrastre, reducido a su eje."""


@dataclass(frozen=True)
class PresupuestoPar:
    """El par en el árbol a lo largo de una vuelta, y de dónde sale."""

    thetas: Arreglo
    estatico: Arreglo
    """N·m que hay que hacer aunque se gire infinitamente despacio."""
    por_inercia: Arreglo
    """Coeficiente de ω²: el par inercial es `por_inercia · ω²`, en N·m·s²."""

    def total(self, omega: float) -> Arreglo:
        """El par pedido a una velocidad de giro dada, en N·m."""
        return np.asarray(self.estatico + self.por_inercia * omega**2)

    def medio(self, omega: float = 0.0) -> float:
        """Par medio de la vuelta. Es el que fija el trabajo por vuelta."""
        return float(np.mean(self.total(omega)))

    def maximo(self, omega: float = 0.0) -> float:
        return float(np.max(self.total(omega)))

    def trabajo(self, omega: float = 0.0) -> float:
        """Julios por vuelta. Lo que hay que poner con la mano."""
        return self.medio(omega) * TAU


def par_de_un_canal(
    psi: Arreglo,
    psi_prima: Arreglo,
    psi_segunda: Arreglo,
    carga: CargaSeguidor,
) -> tuple[Arreglo, Arreglo]:
    """Lo que un seguidor le pide al árbol: parte estática y parte inercial.

    El rozamiento va con el signo contrario al movimiento del seguidor, así
    que siempre resta trabajo; el muelle devuelve el suyo cuando el seguidor
    baja, y por eso su par cambia de signo a lo largo de la vuelta.
    """
    par_resistente = float(carga.par_muelle) + carga.rigidez * psi
    rozamiento = float(carga.rozamiento) * np.sign(psi_prima)
    estatico = (par_resistente + rozamiento) * psi_prima
    inercial = float(carga.inercia) * psi_segunda * psi_prima
    return np.asarray(estatico), np.asarray(inercial)


def presupuesto(
    thetas: Arreglo,
    canales: dict[str, tuple[Arreglo, Arreglo, Arreglo]],
    cargas: dict[str, CargaSeguidor],
    rozamiento_arbol: Par = ROZAMIENTO_DEL_ARBOL,
) -> PresupuestoPar:
    """Suma lo que piden todos los seguidores, más lo que cuesta el árbol.

    `canales` lleva, por nombre, la terna (ψ, ψ', ψ'') sobre la misma rejilla
    de θ: tres levas caladas en el mismo eje se leen en el mismo ángulo, así
    que sus pares se suman sin más.
    """
    if not canales:
        raise ValueError("no hay canales de los que presupuestar par")

    estatico = np.full_like(np.asarray(thetas, dtype=np.float64), float(rozamiento_arbol))
    inercial = np.zeros_like(estatico)
    for nombre, (psi, psi_prima, psi_segunda) in canales.items():
        parcial, parcial_inercial = par_de_un_canal(
            psi, psi_prima, psi_segunda, cargas.get(nombre, CargaSeguidor())
        )
        estatico = estatico + parcial
        inercial = inercial + parcial_inercial

    return PresupuestoPar(
        thetas=np.asarray(thetas, dtype=np.float64),
        estatico=estatico,
        por_inercia=inercial,
    )


__all__ = [
    "ROZAMIENTO_DEL_ARBOL",
    "CargaSeguidor",
    "PresupuestoPar",
    "par_de_un_canal",
    "presupuesto",
]
