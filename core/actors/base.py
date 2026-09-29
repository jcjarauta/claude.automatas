"""Catálogo de actuadores: C1, la cinemática inversa.

Un actuador convierte lo que queremos que pase —la punta del lápiz en (x, y),
el lápiz levantado 3 mm— en el ángulo que debe tener cada seguidor. Es la
primera etapa del compilador y la que decide qué perfil tendrá cada leva.

La ficha de un módulo nombra su cinemática por clave (`brazo_cinco_barras_v1`)
y aporta los parámetros que esa clave necesita. No se incrusta la función: una
función no se serializa, y el catálogo del proyecto es dato, no código.

Todas las operaciones van vectorizadas sobre las N muestras del ciclo. Nada
aquí conoce el tiempo: la entrada es el ángulo del eje maestro.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

import numpy as np
import numpy.typing as npt

Arreglo = npt.NDArray[np.float64]


@runtime_checkable
class Actuador(Protocol):
    """Lo que todo actuador sabe hacer.

    `inversa` va de objetivo a ángulos de seguidor; `directa` deshace el camino
    y es lo que permite comprobar que la inversa no miente.
    """

    @property
    def canales(self) -> tuple[str, ...]:
        """Los canales del programa que consume, en orden."""
        ...

    @property
    def seguidores(self) -> tuple[str, ...]:
        """Los seguidores que mueve, en orden. Uno por leva."""
        ...

    def alcanzable(self, objetivo: Arreglo) -> npt.NDArray[np.bool_]:
        """Qué puntos del objetivo (N, n_canales) están dentro del alcance."""
        ...

    def inversa(self, objetivo: Arreglo) -> Arreglo:
        """(N, n_canales) -> (N, n_seguidores), en radianes.

        La entrada es una **trayectoria en orden**, no un conjunto de puntos
        sueltos, y la salida viene desenrollada: sin saltos de 2π. Aguas abajo
        se interpola ψ con un spline y se deriva dos veces, y un salto haría
        que el perfil saliera con un pico donde no lo hay.

        Lanza `FueraDeAlcance` si algún punto no se alcanza. Comprueba antes
        con `alcanzable` si quieres un veredicto en vez de una excepción.
        """
        ...

    def directa(self, psi: Arreglo) -> Arreglo:
        """(N, n_seguidores) -> (N, n_canales). La inversa de `inversa`."""
        ...
