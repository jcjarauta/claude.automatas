"""El brazo de cinco barras que lleva el lápiz.

Dos pivotes anclados al bastidor, uno a cada lado del origen. De cada uno sale
un eslabón proximal, y de cada codo un eslabón distal; los dos distales se
juntan en la punta del lápiz.

    A ---- C1                 C2 ---- B
      \\      \\              /      /
       l1      l2          l2      l1
                 \\        /
                    P (lápiz)

Por qué cinco barras y no un brazo serie hombro-codo: con las levas apiladas
en un eje vertical, los seguidores pivotan en postes fijos del bastidor. Eso
obliga a que los dos ejes motrices estén anclados a tierra. En un brazo serie
el codo va montado sobre el hombro y accionarlo desde un poste fijo exige un
varillaje añadido; aquí cada seguidor mueve su pivote directamente.

La cinemática inversa tiene **dos ramas** por brazo, codo dentro o codo fuera.
Hay que elegir una y no cambiarla en todo el ciclo: un cambio de rama a mitad
de vuelta sale en la leva como un salto, y la leva con un salto no se puede
fabricar.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import numpy.typing as npt

from core.errors import FueraDeAlcance

Arreglo = npt.NDArray[np.float64]

_TOLERANCIA_ALCANCE = 1e-9


@dataclass(frozen=True)
class BrazoCincoBarras:
    """Parámetros en metros. `rama` fija el codo de cada lado.

    Por defecto los codos van hacia fuera, que es la configuración que más
    lejos queda de la singularidad del brazo estirado.
    """

    separacion: float
    """Distancia entre los dos pivotes anclados, `d`."""
    proximal: float
    """Longitud del eslabón que sale del pivote, `l1`."""
    distal: float
    """Longitud del eslabón que llega al lápiz, `l2`."""
    rama_izquierda: int = -1
    rama_derecha: int = 1

    def __post_init__(self) -> None:
        for nombre, valor in (
            ("separacion", self.separacion),
            ("proximal", self.proximal),
            ("distal", self.distal),
        ):
            if valor <= 0.0:
                raise ValueError(f"{nombre} debe ser positivo, no {valor}")
        for nombre, valor in (
            ("rama_izquierda", self.rama_izquierda),
            ("rama_derecha", self.rama_derecha),
        ):
            if valor not in (-1, 1):
                raise ValueError(f"{nombre} solo puede ser -1 o 1, no {valor}")

    # -- geometría -----------------------------------------------------------

    @property
    def pivote_izquierdo(self) -> Arreglo:
        return np.array([-self.separacion / 2.0, 0.0])

    @property
    def pivote_derecho(self) -> Arreglo:
        return np.array([self.separacion / 2.0, 0.0])

    @property
    def canales(self) -> tuple[str, ...]:
        return ("x", "y")

    @property
    def seguidores(self) -> tuple[str, ...]:
        return ("izquierdo", "derecho")

    # -- alcance -------------------------------------------------------------

    def _distancias(self, objetivo: Arreglo) -> tuple[Arreglo, Arreglo]:
        puntos = np.atleast_2d(np.asarray(objetivo, dtype=np.float64))
        izq = np.linalg.norm(puntos - self.pivote_izquierdo, axis=1)
        der = np.linalg.norm(puntos - self.pivote_derecho, axis=1)
        return izq, der

    def alcanzable(self, objetivo: Arreglo) -> npt.NDArray[np.bool_]:
        """Un punto se alcanza si cae en la corona de los dos brazos."""
        minimo = abs(self.proximal - self.distal) + _TOLERANCIA_ALCANCE
        maximo = self.proximal + self.distal - _TOLERANCIA_ALCANCE
        izq, der = self._distancias(objetivo)
        dentro = (izq >= minimo) & (izq <= maximo) & (der >= minimo) & (der <= maximo)
        return np.asarray(dentro, dtype=np.bool_)

    # -- cinemática ----------------------------------------------------------

    def _angulo_de_un_brazo(self, pivote: Arreglo, puntos: Arreglo, rama: int) -> Arreglo:
        """Intersección de dos circunferencias: la del proximal y la del distal.

        El codo está en uno de los dos puntos de corte; `rama` elige cuál.
        """
        v = puntos - pivote
        r = np.linalg.norm(v, axis=1)
        # Proyección del codo sobre la recta pivote-punta, y separación perpendicular.
        a = (r**2 + self.proximal**2 - self.distal**2) / (2.0 * r)
        h2 = self.proximal**2 - a**2
        h = np.sqrt(np.maximum(h2, 0.0))
        unitario = v / r[:, None]
        perpendicular = np.column_stack((-unitario[:, 1], unitario[:, 0]))
        codo = pivote + unitario * a[:, None] + rama * perpendicular * h[:, None]
        brazo = codo - pivote
        return np.asarray(np.arctan2(brazo[:, 1], brazo[:, 0]), dtype=np.float64)

    def inversa(self, objetivo: Arreglo) -> Arreglo:
        puntos = np.atleast_2d(np.asarray(objetivo, dtype=np.float64))
        if puntos.shape[1] != 2:
            raise ValueError(f"el objetivo debe tener dos columnas (x, y), no {puntos.shape[1]}")
        fuera = ~self.alcanzable(puntos)
        if bool(fuera.any()):
            indice = int(np.argmax(fuera))
            x, y = puntos[indice]
            raise FueraDeAlcance(
                f"el punto {indice} ({x * 1000:.1f}, {y * 1000:.1f}) mm queda fuera "
                f"del alcance del brazo. Reduce el tamaño de la escritura o alarga "
                f"los eslabones."
            )
        izq = self._angulo_de_un_brazo(self.pivote_izquierdo, puntos, self.rama_izquierda)
        der = self._angulo_de_un_brazo(self.pivote_derecho, puntos, self.rama_derecha)
        # `arctan2` salta 2π al cruzar ±π. Aguas abajo se interpola ψ con un
        # spline y se deriva dos veces, así que un salto así destrozaría el
        # perfil. Se desenrolla: la entrada es una trayectoria en orden, no un
        # conjunto de puntos sueltos.
        return np.asarray(np.column_stack((np.unwrap(izq), np.unwrap(der))), dtype=np.float64)

    def directa(self, psi: Arreglo) -> Arreglo:
        """Dónde acaba el lápiz dados los dos ángulos.

        Existe para poder comprobar la inversa contra ella: si la ida y la
        vuelta no coinciden, una de las dos está mal.
        """
        angulos = np.atleast_2d(np.asarray(psi, dtype=np.float64))
        codo_izq = self.pivote_izquierdo + self.proximal * np.column_stack(
            (np.cos(angulos[:, 0]), np.sin(angulos[:, 0]))
        )
        codo_der = self.pivote_derecho + self.proximal * np.column_stack(
            (np.cos(angulos[:, 1]), np.sin(angulos[:, 1]))
        )
        # La punta está en la intersección de las dos circunferencias distales.
        # Se elige el corte de abajo, que es donde trabaja el brazo.
        entre = codo_der - codo_izq
        d = np.linalg.norm(entre, axis=1)
        a = d / 2.0
        h = np.sqrt(np.maximum(self.distal**2 - a**2, 0.0))
        unitario = entre / d[:, None]
        perpendicular = np.column_stack((-unitario[:, 1], unitario[:, 0]))
        medio = codo_izq + unitario * a[:, None]
        return np.asarray(medio - perpendicular * h[:, None], dtype=np.float64)
