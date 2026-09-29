"""Funciones periódicas del ángulo del eje, con sus derivadas.

Todo en el núcleo es función de θ y se cierra al dar la vuelta. Aquí se
convierte una pista muestreada en una función continua que se puede derivar,
y se remuestrea sobre una rejilla uniforme.

Por qué uniforme: con paso constante las derivadas por diferencias centradas
con envolvente cíclica son exactas en el cierre, sin casos especiales en los
extremos. El ciclo no tiene extremos.

Por qué el spline es periódico y no simplemente cúbico: un spline natural
impone segunda derivada nula en los bordes, que en un ciclo cerrado es una
condición falsa y mete un artefacto justo en θ=0.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import numpy.typing as npt
from scipy.interpolate import CubicSpline

from core.units import TAU

Arreglo = npt.NDArray[np.float64]

MUESTRAS_POR_DEFECTO = 720
"""Medio grado de resolución. Suficiente para el escribiente y barato."""


@dataclass(frozen=True)
class FuncionPeriodica:
    """Una magnitud y sus dos primeras derivadas sobre una rejilla uniforme."""

    thetas: Arreglo
    valores: Arreglo
    primera: Arreglo
    segunda: Arreglo

    def __len__(self) -> int:
        return int(self.thetas.size)

    @property
    def paso(self) -> float:
        """Separación entre muestras, en radianes."""
        return TAU / len(self)


def rejilla(n: int = MUESTRAS_POR_DEFECTO) -> Arreglo:
    """n ángulos repartidos por igual en [0, 2π). El extremo no se incluye."""
    if n < 8:
        raise ValueError(f"hacen falta al menos 8 muestras, no {n}")
    return np.linspace(0.0, TAU, n, endpoint=False, dtype=np.float64)


def desde_muestras(
    thetas: Arreglo,
    valores: Arreglo,
    n: int = MUESTRAS_POR_DEFECTO,
) -> FuncionPeriodica:
    """Interpola muestras de una pista en una función periódica derivable.

    `thetas` viene en [0, 2π) y sin el extremo, que es como las guarda
    `PistaContinua`. Aquí se cierra el ciclo añadiendo θ=2π con el valor de
    θ=0: como el extremo nunca se almacenó, no hay forma de que contradiga
    al inicio.
    """
    x = np.asarray(thetas, dtype=np.float64)
    y = np.asarray(valores, dtype=np.float64)
    if x.shape != y.shape:
        raise ValueError(f"{x.size} ángulos frente a {y.size} valores")
    if x.size < 3:
        raise ValueError("un spline periódico necesita al menos tres muestras")

    cerrado_x = np.append(x, TAU)
    cerrado_y = np.append(y, y[0])
    spline = CubicSpline(cerrado_x, cerrado_y, bc_type="periodic")

    malla = rejilla(n)
    return FuncionPeriodica(
        thetas=malla,
        valores=np.asarray(spline(malla), dtype=np.float64),
        primera=np.asarray(spline(malla, 1), dtype=np.float64),
        segunda=np.asarray(spline(malla, 2), dtype=np.float64),
    )


def derivada_ciclica(valores: Arreglo, paso: float) -> Arreglo:
    """Diferencias centradas con envolvente. Exacta en el cierre del ciclo.

    Vale para escalares (N,) y para curvas (N, 2).
    """
    return np.asarray(
        (np.roll(valores, -1, axis=0) - np.roll(valores, 1, axis=0)) / (2.0 * paso),
        dtype=np.float64,
    )


def orientacion(curva: Arreglo) -> float:
    """+1 si la curva cerrada gira en sentido antihorario, -1 si horario.

    Es el signo del área por la fórmula del zapatero. Sirve para saber hacia
    dónde apunta la normal exterior sin suponer que el origen queda dentro.
    """
    x = curva[:, 0]
    y = curva[:, 1]
    area = float(np.sum(x * np.roll(y, -1) - np.roll(x, -1) * y)) / 2.0
    return 1.0 if area >= 0.0 else -1.0
