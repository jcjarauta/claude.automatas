"""C2 · Síntesis del perfil de leva para un seguidor oscilante.

El método es la **inversión cinemática**: en vez de girar la leva y ver por
dónde pasa el rodillo, se fija la leva y se hace girar al seguidor a su
alrededor. El rastro del centro del rodillo es la *curva de paso*, y el perfil
real es esa curva desplazada hacia dentro el radio del rodillo.

    curva de paso  =  R(-θ) · [ Q + l·(cos(ψ₀+ψ(θ)), sen(ψ₀+ψ(θ))) ]
    perfil         =  curva de paso - r_rodillo · n̂

donde Q es el pivote del seguidor visto desde el centro de la leva, l la
longitud del brazo del seguidor y n̂ la normal exterior de la curva de paso.

Nada de esto sabe a qué velocidad gira el eje, ni puede saberlo: θ es la
variable independiente y el tiempo no aparece.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import numpy.typing as npt

from core.cam.curves import (
    FuncionPeriodica,
    derivada_ciclica,
    orientacion,
)

Arreglo = npt.NDArray[np.float64]


@dataclass(frozen=True)
class Seguidor:
    """Geometría del seguidor oscilante, en metros y radianes.

    `pivote` es la posición del pivote del seguidor **vista desde el centro de
    la leva**. `psi_cero` es hacia dónde apunta el brazo cuando ψ vale cero.
    """

    pivote: tuple[float, float]
    brazo: float
    radio_rodillo: float
    psi_cero: float = 0.0

    def __post_init__(self) -> None:
        if self.brazo <= 0.0:
            raise ValueError(f"el brazo del seguidor debe ser positivo, no {self.brazo}")
        if self.radio_rodillo <= 0.0:
            raise ValueError(f"el radio del rodillo debe ser positivo, no {self.radio_rodillo}")

    @property
    def distancia_pivote(self) -> float:
        """Separación entre el centro de la leva y el pivote del seguidor."""
        return float(np.hypot(*self.pivote))

    @classmethod
    def bien_puesto(
        cls,
        radio_base: float,
        brazo: float,
        radio_rodillo: float,
        orientacion_pivote: float = 0.0,
    ) -> Seguidor:
        """Coloca el pivote donde el ángulo de presión arranca en cero.

        Es la regla de trazado de un seguidor oscilante: el brazo debe quedar
        **perpendicular al radio** de la leva en la posición de reposo. Si en
        vez de eso el pivote se alinea con el centro de la leva, el rodillo
        acaba sobre la recta que los une, la fuerza de contacto pasa por el
        pivote y el momento es cero: ángulo de presión de 90° y el seguidor no
        se mueve. Es el error de trazado clásico y no se ve hasta que se
        calcula.

        Con el brazo perpendicular al radio, el triángulo centro-pivote-rodillo
        es rectángulo en el rodillo, así que el pivote va a
        `hypot(radio_base, brazo)` del centro.
        """
        if radio_base <= 0.0 or brazo <= 0.0:
            raise ValueError("el radio base y el brazo deben ser positivos")
        distancia = float(np.hypot(radio_base, brazo))
        pivote = (
            distancia * float(np.cos(orientacion_pivote)),
            distancia * float(np.sin(orientacion_pivote)),
        )
        # Dónde toca el rodillo en reposo, resolviendo las dos circunferencias.
        x = radio_base**2 / distancia
        y = radio_base * brazo / distancia
        contacto = np.array(
            [
                x * np.cos(orientacion_pivote) - y * np.sin(orientacion_pivote),
                x * np.sin(orientacion_pivote) + y * np.cos(orientacion_pivote),
            ]
        )
        hacia_contacto = contacto - np.array(pivote)
        psi_cero = float(np.arctan2(hacia_contacto[1], hacia_contacto[0]))
        return cls(
            pivote=pivote,
            brazo=brazo,
            radio_rodillo=radio_rodillo,
            psi_cero=psi_cero,
        )


@dataclass(frozen=True)
class PerfilLeva:
    """El resultado de sintetizar una leva. Todo sobre la misma rejilla de θ."""

    thetas: Arreglo
    psi: Arreglo
    """Ángulo del seguidor en cada θ."""
    psi_prima: Arreglo
    """Su derivada respecto de θ. Cero en un reposo."""
    paso: Arreglo
    """Curva de paso en el marco de la leva, (N, 2)."""
    perfil: Arreglo
    """Perfil real, (N, 2). Es lo que se corta."""
    normales: Arreglo
    """Normal exterior de la curva de paso en cada punto, (N, 2)."""
    seguidor: Seguidor

    def __len__(self) -> int:
        return int(self.thetas.size)

    @property
    def radio_maximo(self) -> float:
        """Lo que mide la leva. Decide si cabe en el cartucho."""
        return float(np.max(np.linalg.norm(self.perfil, axis=1)))

    @property
    def radio_minimo(self) -> float:
        return float(np.min(np.linalg.norm(self.perfil, axis=1)))


def curva_de_paso(psi: FuncionPeriodica, seguidor: Seguidor) -> Arreglo:
    """El rastro del centro del rodillo en el marco de la leva.

    En el marco fijo el centro del rodillo describe un arco alrededor del
    pivote. Al girar el conjunto -θ se obtiene lo que ve la leva.
    """
    angulo_brazo = seguidor.psi_cero + psi.valores
    centro_fijo = np.column_stack(
        (
            seguidor.pivote[0] + seguidor.brazo * np.cos(angulo_brazo),
            seguidor.pivote[1] + seguidor.brazo * np.sin(angulo_brazo),
        )
    )
    coseno = np.cos(-psi.thetas)
    seno = np.sin(-psi.thetas)
    return np.asarray(
        np.column_stack(
            (
                coseno * centro_fijo[:, 0] - seno * centro_fijo[:, 1],
                seno * centro_fijo[:, 0] + coseno * centro_fijo[:, 1],
            )
        ),
        dtype=np.float64,
    )


def tangente_de_paso(psi: FuncionPeriodica, seguidor: Seguidor) -> Arreglo:
    """dC/dθ de la curva de paso, analítica.

    Se podría sacar por diferencias finitas, pero la normal que sale de esta
    tangente es la que desplaza el perfil que se va a cortar: un error de
    discretización aquí se convierte en material de más o de menos. Como el
    spline ya da ψ y ψ', la derivada exacta sale sin coste.

    Dos términos: lo que se mueve el seguidor y lo que gira la leva bajo él.

        C(θ) = R(-θ)·F(θ)
        C'   = R(-θ)·F' + [dR(-θ)/dθ]·F
    """
    angulo_brazo = seguidor.psi_cero + psi.valores
    fijo = np.column_stack(
        (
            seguidor.pivote[0] + seguidor.brazo * np.cos(angulo_brazo),
            seguidor.pivote[1] + seguidor.brazo * np.sin(angulo_brazo),
        )
    )
    fijo_prima = (
        seguidor.brazo
        * psi.primera[:, None]
        * np.column_stack((-np.sin(angulo_brazo), np.cos(angulo_brazo)))
    )
    c = np.cos(psi.thetas)
    s = np.sin(psi.thetas)
    return np.asarray(
        np.column_stack(
            (
                c * fijo_prima[:, 0] + s * fijo_prima[:, 1] - s * fijo[:, 0] + c * fijo[:, 1],
                -s * fijo_prima[:, 0] + c * fijo_prima[:, 1] - c * fijo[:, 0] - s * fijo[:, 1],
            )
        ),
        dtype=np.float64,
    )


def normales_desde_tangente(tangente: Arreglo, curva: Arreglo) -> Arreglo:
    """Normal unitaria exterior, a partir de una tangente ya calculada."""
    modulo = np.linalg.norm(tangente, axis=1)
    if bool(np.any(modulo < 1e-12)):
        raise ValueError(
            "la curva de paso tiene un punto de retroceso: la tangente se anula. "
            "El movimiento pedido al seguidor no es realizable con esta geometría."
        )
    unitaria = tangente / modulo[:, None]
    signo = orientacion(curva)
    return np.asarray(
        signo * np.column_stack((unitaria[:, 1], -unitaria[:, 0])),
        dtype=np.float64,
    )


def normales_exteriores(curva: Arreglo, paso: float) -> Arreglo:
    """Normal unitaria que apunta hacia fuera de la curva cerrada.

    Se deduce del sentido de giro en vez de suponer que el centro de la leva
    queda dentro: una leva muy excéntrica puede no encerrar su propio eje.
    """
    tangente = derivada_ciclica(curva, paso)
    modulo = np.linalg.norm(tangente, axis=1)
    if bool(np.any(modulo < 1e-12)):
        raise ValueError(
            "la curva de paso tiene un punto de retroceso: la tangente se anula. "
            "El movimiento pedido al seguidor no es realizable con esta geometría."
        )
    unitaria = tangente / modulo[:, None]
    signo = orientacion(curva)
    return np.asarray(
        signo * np.column_stack((unitaria[:, 1], -unitaria[:, 0])),
        dtype=np.float64,
    )


def sintetizar(psi: FuncionPeriodica, seguidor: Seguidor) -> PerfilLeva:
    """De ψ(θ) al perfil que hay que cortar."""
    curva = curva_de_paso(psi, seguidor)
    normales = normales_desde_tangente(tangente_de_paso(psi, seguidor), curva)
    perfil = curva - seguidor.radio_rodillo * normales
    return PerfilLeva(
        thetas=psi.thetas,
        psi=psi.valores,
        psi_prima=psi.primera,
        paso=curva,
        perfil=np.asarray(perfil, dtype=np.float64),
        normales=normales,
        seguidor=seguidor,
    )
