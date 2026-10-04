"""Qué escriben las levas que se van a cortar: recorridas por el perfil.

`compile.escribiente.simular` recorre las levas por la **curva de paso**
(`_psi_desde_la_leva`): gira la trayectoria del centro del rodillo que
calculó la propia síntesis y lee el ángulo del seguidor. Es rápido y sirve
para lo que sirve —que el reparto de θ, la cinemática y el spline devuelven
la letra—, pero deshace la síntesis con sus mismas fórmulas: si el
desplazamiento por el radio del rodillo estuviera del revés, la ida y la
vuelta coincidirían igual.

Aquí se recorre el **perfil cortado**: el polígono que sale en el DXF, con
el rodillo apoyado en él en cada θ (`core.cam.contacto.psi_por_contacto`).
Es leer la pieza que se va a fabricar y no el diseño, y por eso es lo que
se dibuja cuando se quiere ver qué escribe una leva. Cuesta un segundo por
canal y vuelta de 360 ángulos.

Lo que **sigue sin ver**: el kerf real, el juego y la elasticidad. Eso es del
banco (E4) y de `compile.tolerancias`.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import numpy.typing as npt

from compile.escribiente import (
    SEGUIDORES,
    UMBRAL_DE_APOYO,
    Compilacion,
    Escribiente,
    distancias_a_la_tinta,
)
from core.cam.contacto import psi_por_contacto

Arreglo = npt.NDArray[np.float64]


@dataclass(frozen=True)
class Recorrido:
    """La máquina recorriendo sus levas cortadas, en cada θ."""

    thetas: Arreglo
    puntos: Arreglo
    """Dónde pasa la punta, (M, 2), en metros del marco del cinco barras."""
    altura: Arreglo
    """Cuánto está levantada, (M,)."""
    error_maximo: float
    error_medio: float
    camino: str = "perfil cortado (contacto)"

    @property
    def apoyado(self) -> npt.NDArray[np.bool_]:
        return np.asarray(self.altura <= UMBRAL_DE_APOYO)

    @property
    def escritos(self) -> Arreglo:
        """Solo los puntos con el lápiz apoyado: lo que queda en el papel."""
        return np.asarray(self.puntos[self.apoyado], dtype=np.float64)

    def tramos(self) -> tuple[int, int]:
        """Cuántos trazos y cuántos vuelos hay en la vuelta: tramos seguidos
        de θ con el lápiz abajo y con el lápiz arriba. La vuelta es cerrada,
        así que el último tramo y el primero son el mismo si coinciden."""
        a = self.apoyado
        if a.all():
            return 1, 0
        if not a.any():
            return 0, 1
        cambios = np.flatnonzero(a != np.roll(a, 1))
        abajo = sum(1 for i in cambios if a[i])
        return abajo, len(cambios) - abajo

    @property
    def fraccion_escribiendo(self) -> float:
        return float(np.mean(self.apoyado))


def recorrer(
    compilacion: Compilacion, maquina: Escribiente | None = None, muestras: int = 720
) -> Recorrido:
    """Recorre las tres levas por su perfil cortado y mide lo que escriben
    contra la escritura del pedido, igual que `simular`."""
    maquina = maquina or Escribiente()
    if not compilacion.perfiles:
        raise ValueError("no hay levas que recorrer: la compilación no llegó a sintetizarlas")
    thetas = np.linspace(0.0, 2.0 * np.pi, muestras, endpoint=False)
    psi = {
        nombre: psi_por_contacto(
            compilacion.perfiles[nombre].perfil, compilacion.perfiles[nombre].seguidor, thetas
        )
        * maquina.relacion
        + compilacion.calajes[nombre]
        for nombre in SEGUIDORES
    }
    puntos = maquina.brazo.directa(np.column_stack([psi["izquierdo"], psi["derecho"]]))
    altura = maquina.palanca.directa(psi["elevador"][:, None])[:, 0]
    apoyado = altura <= UMBRAL_DE_APOYO
    if not apoyado.any():
        return Recorrido(thetas, puntos, altura, np.inf, np.inf)
    distancias = distancias_a_la_tinta(compilacion.escritura, puntos, apoyado)
    return Recorrido(
        thetas=thetas,
        puntos=np.asarray(puntos, dtype=np.float64),
        altura=np.asarray(altura, dtype=np.float64),
        error_maximo=max(distancias),
        error_medio=float(np.mean(distancias)),
    )


def segundos_por_vuelta(rpm_manivela: float, reduccion: float) -> float:
    """Lo que tarda una vuelta del árbol, que es la frase entera."""
    return 60.0 * reduccion / rpm_manivela


__all__ = ["UMBRAL_DE_APOYO", "Recorrido", "recorrer", "segundos_por_vuelta"]
