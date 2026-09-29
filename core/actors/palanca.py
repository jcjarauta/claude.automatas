"""La palanca que levanta el lápiz: el tercer eje, el más simple.

El seguidor gira un ángulo y la punta del brazo sube. La altura es
`brazo · sin(psi)`, así que la inversa es un arcoseno.

El lápiz apoya por gravedad o con un muelle suave: la leva solo levanta. Así
el papel puede estar algo alabeado sin que el trazo se rompa, y el sistema
no puede clavar la punta contra la mesa.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import numpy.typing as npt

from core.errors import FueraDeAlcance

Arreglo = npt.NDArray[np.float64]

_TOLERANCIA_ALCANCE = 1e-9


@dataclass(frozen=True)
class PalancaElevadora:
    """`brazo` en metros: la longitud de la palanca que levanta la columna."""

    brazo: float

    def __post_init__(self) -> None:
        if self.brazo <= 0.0:
            raise ValueError(f"el brazo debe ser positivo, no {self.brazo}")

    @property
    def canales(self) -> tuple[str, ...]:
        return ("z",)

    @property
    def seguidores(self) -> tuple[str, ...]:
        return ("elevador",)

    def alcanzable(self, objetivo: Arreglo) -> npt.NDArray[np.bool_]:
        altura = np.atleast_2d(np.asarray(objetivo, dtype=np.float64))[:, 0]
        limite = self.brazo - _TOLERANCIA_ALCANCE
        return np.asarray(np.abs(altura) <= limite, dtype=np.bool_)

    def inversa(self, objetivo: Arreglo) -> Arreglo:
        alturas = np.atleast_2d(np.asarray(objetivo, dtype=np.float64))
        if alturas.shape[1] != 1:
            raise ValueError(f"el objetivo debe tener una columna (z), no {alturas.shape[1]}")
        fuera = ~self.alcanzable(alturas)
        if bool(fuera.any()):
            indice = int(np.argmax(fuera))
            raise FueraDeAlcance(
                f"la altura {alturas[indice, 0] * 1000:.1f} mm pasa de la palanca "
                f"de {self.brazo * 1000:.1f} mm. Alarga la palanca o baja el "
                f"levantamiento."
            )
        return np.asarray(np.arcsin(alturas / self.brazo), dtype=np.float64)

    def directa(self, psi: Arreglo) -> Arreglo:
        angulos = np.atleast_2d(np.asarray(psi, dtype=np.float64))
        return np.asarray(self.brazo * np.sin(angulos), dtype=np.float64)
