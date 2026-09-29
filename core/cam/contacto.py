"""C3 · Recuperar ψ(θ) por contacto contra el perfil ya cortado.

La síntesis de C2 va de ψ(θ) al perfil pasando por la curva de paso. La
simulación de E5 deshace ese camino con las mismas fórmulas, así que
comprueba la aritmética pero **comparte las hipótesis**: si el offset por
radio de rodillo estuviera mal, o el perfil se cruzara consigo mismo, la ida
y la vuelta seguirían coincidiendo.

Aquí se va por otro sitio. Se coge el polígono que se va a cortar —solo eso,
ni curva de paso ni normales— se gira θ, y se busca el ángulo al que el
rodillo **apoya** sobre él sin penetrarlo. Es lo que hace el seguidor real
empujado por su muelle, y es una derivación independiente: si coincide con
ψ(θ), el desplazamiento por radio de rodillo está bien hecho; si el perfil
está socavado, el rodillo apoya donde no debe y se nota de lejos.

Qué sigue sin comprobar: el kerf y el desgaste, que son medidas del banco, y
el rozamiento, que no es geometría. Esto es cinemática de sólido rígido con
holgura cero, igual que el resto del núcleo.
"""

from __future__ import annotations

import numpy as np
import numpy.typing as npt
from scipy.optimize import brentq
from shapely import contains_xy
from shapely.geometry import Polygon

from core.cam.synth import Seguidor

Arreglo = npt.NDArray[np.float64]

MUESTRAS_DEL_BARRIDO = 61
"""Cuántas posiciones se prueban entre el seguidor suelto y el seguidor
hundido en la leva. Solo sirven para acorralar el contacto; el número fino
sale después de afinar el cero."""


def _distancia_al_borde(puntos: Arreglo, inicios: Arreglo, finales: Arreglo) -> Arreglo:
    """Distancia de cada punto al polígono, segmento a segmento.

    Vectorizado a propósito: se llama una vez por cada ángulo del ciclo y por
    cada candidato, y con `shapely` punto a punto esto tardaba minutos.
    """
    segmento = finales - inicios
    largo = np.einsum("ij,ij->i", segmento, segmento)
    largo = np.where(largo < 1e-24, 1e-24, largo)
    relativo = puntos[:, None, :] - inicios[None, :, :]
    t = np.clip(np.einsum("nij,ij->ni", relativo, segmento) / largo, 0.0, 1.0)
    cercano = inicios[None, :, :] + t[:, :, None] * segmento[None, :, :]
    return np.asarray(np.min(np.linalg.norm(puntos[:, None, :] - cercano, axis=2), axis=1))


class _Leva:
    """El perfil cortado, preparado para preguntarle distancias."""

    def __init__(self, perfil: Arreglo) -> None:
        self.puntos = np.asarray(perfil, dtype=np.float64)
        if self.puntos.shape[0] < 3 or self.puntos.shape[1] != 2:
            raise ValueError("el perfil debe ser un polígono cerrado de al menos tres puntos")
        self.inicios = self.puntos
        self.finales = np.roll(self.puntos, -1, axis=0)
        self.poligono = Polygon(self.puntos)

    def holgura(self, centros: Arreglo, radio: float) -> Arreglo:
        """Cuánto le sobra al rodillo. Negativo si penetra o si está dentro."""
        distancia = _distancia_al_borde(centros, self.inicios, self.finales)
        dentro = contains_xy(self.poligono, centros[:, 0], centros[:, 1])
        return np.where(dentro, -distancia - radio, distancia - radio)


def _centros(seguidor: Seguidor, psi: Arreglo, theta: float) -> Arreglo:
    """Centro del rodillo en el marco de la leva.

    En vez de girar el polígono θ se gira el seguidor -θ, que son dos puntos
    en lugar de setecientos. Es la misma inversión cinemática de C2, pero
    aplicada a la pregunta contraria.
    """
    angulo = seguidor.psi_cero + psi
    fijo = np.column_stack(
        (
            seguidor.pivote[0] + seguidor.brazo * np.cos(angulo),
            seguidor.pivote[1] + seguidor.brazo * np.sin(angulo),
        )
    )
    coseno, seno = np.cos(-theta), np.sin(-theta)
    return np.asarray(
        np.column_stack(
            (
                coseno * fijo[:, 0] - seno * fijo[:, 1],
                seno * fijo[:, 0] + coseno * fijo[:, 1],
            )
        )
    )


def _intervalo(seguidor: Seguidor) -> tuple[float, float]:
    """De ψ con el rodillo lo más lejos posible de la leva a ψ con el rodillo
    lo más metido posible.

    El centro del rodillo describe una circunferencia alrededor del pivote,
    así que su distancia al eje de la leva tiene un solo máximo y un solo
    mínimo: el brazo apuntando hacia fuera y hacia dentro. Entre los dos, la
    distancia baja de forma monótona, y recorrer ese tramo es exactamente lo
    que hace el seguidor cuando el muelle lo empuja contra la leva.

    De los dos tramos posibles se coge el que contiene ψ = 0, que es la
    posición de diseño del propio seguidor: eso es su ficha, no la respuesta.
    """
    alfa = float(np.arctan2(seguidor.pivote[1], seguidor.pivote[0]))
    lejos = (alfa - seguidor.psi_cero + np.pi) % (2.0 * np.pi) - np.pi
    for cerca in (lejos + np.pi, lejos - np.pi):
        if min(lejos, cerca) <= 0.0 <= max(lejos, cerca):
            return lejos, cerca
    return lejos, lejos + np.pi


def _apoyo(leva: _Leva, seguidor: Seguidor, theta: float, muestras: int) -> float:
    """El ángulo al que el rodillo toca la leva sin penetrarla.

    Se entra desde fuera y se para en el **primer** contacto. Buscar en vez
    de eso el mínimo global dejaría que el rodillo se colara por una hendidura
    del perfil y apoyara al otro lado, que es imposible: para llegar ahí
    tendría que atravesar material.
    """
    lejos, cerca = _intervalo(seguidor)
    candidatos = np.linspace(lejos, cerca, muestras)
    holgura = leva.holgura(_centros(seguidor, candidatos, theta), seguidor.radio_rodillo)

    tocados = np.flatnonzero(holgura < 0.0)
    if tocados.size == 0:
        raise ValueError(
            f"en θ = {np.degrees(theta):.1f}° el rodillo no llega a tocar la leva en "
            "ninguna posición del seguidor. O el perfil no es el que se cree, o el "
            "seguidor está montado donde no alcanza."
        )
    primero = int(tocados[0])
    if primero == 0:
        raise ValueError(
            f"en θ = {np.degrees(theta):.1f}° el rodillo ya penetra con el brazo del "
            "todo hacia fuera: la leva es mayor que el alcance del seguidor."
        )

    def holgura_en(psi: float) -> float:
        centro = _centros(seguidor, np.array([psi]), theta)
        return float(leva.holgura(centro, seguidor.radio_rodillo)[0])

    return float(
        brentq(
            holgura_en,
            float(candidatos[primero - 1]),
            float(candidatos[primero]),
            # Un nanorradián en el seguidor es un nanómetro en la punta: pedir
            # más solo gasta evaluaciones, y cada una recorre el polígono entero.
            xtol=1e-9,
        )
    )


def psi_por_contacto(
    perfil: Arreglo,
    seguidor: Seguidor,
    thetas: Arreglo,
    *,
    muestras: int = MUESTRAS_DEL_BARRIDO,
) -> Arreglo:
    """ψ en cada θ, deducido solo del polígono que se va a cortar.

    Cada ángulo se resuelve por su cuenta, sin apoyarse en el anterior: así
    un error en uno no arrastra a los demás, y el resultado no depende del
    orden en que se pregunten.
    """
    leva = _Leva(perfil)
    angulos = np.asarray(thetas, dtype=np.float64)
    return np.asarray(
        [_apoyo(leva, seguidor, float(theta), muestras) for theta in angulos],
        dtype=np.float64,
    )


def error_de_contacto(perfil: Arreglo, psi: Arreglo, seguidor: Seguidor, thetas: Arreglo) -> float:
    """Diferencia máxima, en radianes, entre el ψ sintetizado y el de contacto.

    Es la comprobación que la simulación de E5 no puede hacer: si el offset
    por radio de rodillo estuviera mal o el perfil se cruzara consigo mismo,
    aquí saldría y allí no.
    """
    recuperado = psi_por_contacto(perfil, seguidor, thetas)
    esperado = np.asarray(psi, dtype=np.float64)
    return float(np.max(np.abs(recuperado - esperado)))


__all__ = [
    "MUESTRAS_DEL_BARRIDO",
    "error_de_contacto",
    "psi_por_contacto",
]
