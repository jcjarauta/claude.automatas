"""C7 · Volante: cuánta inercia hace falta para que no vaya a tirones.

Una manivela entrega par de forma desigual y las levas lo piden de forma
desigual, y los dos desajustes no coinciden. Lo que sobra en unos grados y
falta en otros se guarda y se devuelve con inercia: eso es el volante.

El cálculo es el de libro, y es todo geometría del par a lo largo de la
vuelta, sin tiempo:

1. Par medio: el que de verdad hay que dar, `T̄ = (1/2π)∫T dθ`.
2. Se integra `T - T̄` a lo largo del ciclo. Donde esa integral sube, el
   árbol acelera; donde baja, frena.
3. La **fluctuación de energía** es la diferencia entre el máximo y el
   mínimo de esa integral. Es lo que el volante tiene que tragar y soltar.
4. Y de ahí la inercia: `J = ΔE / (Cs · ω̄²)`.

`Cs` es el coeficiente de fluctuación de velocidad, o sea cuánto se permite
que varíe la velocidad respecto de la media. Es lo único que hay que elegir,
y para un escribiente movido a mano no es un capricho: la velocidad del
árbol no cambia el trazo —el programa es función de θ, no de t— pero sí
cambia la sensación en la mano, y una manivela que se agarrota y se suelta
se acaba girando a golpes, que es lo que sí estropea la letra.

La cuenta tiene una salvedad honrada: usa ω̄ constante para pasar de energía
a inercia, que es la aproximación clásica y vale mientras Cs sea pequeño.
Con Cs de 0,2 el error es de un 10 % y conviene saberlo.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import numpy.typing as npt

from core.units import TAU, Julios, KgM2

Arreglo = npt.NDArray[np.float64]

FLUCTUACION_RECOMENDADA = 0.15
"""Cuánto se deja variar la velocidad respecto de la media. En maquinaria
lenta movida a mano se admite bastante; por debajo de 0,1 el volante se
vuelve grande y pesado para lo que se gana."""


@dataclass(frozen=True)
class Fluctuacion:
    """Lo que sobra y lo que falta a lo largo de la vuelta."""

    thetas: Arreglo
    acumulada: Arreglo
    """Energía acumulada respecto de la media, en julios. Sube donde el árbol
    acelera y baja donde frena."""
    energia: Julios
    """Diferencia entre el máximo y el mínimo: lo que el volante debe guardar."""
    theta_maximo: float
    theta_minimo: float
    """Dónde ocurren. Sirven para señalarlos sobre el diagrama de la vuelta."""


def fluctuacion(thetas: Arreglo, par: Arreglo) -> Fluctuacion:
    """Integra el exceso de par a lo largo del ciclo.

    Se integra con la regla del trapecio cerrando el ciclo: θ vive en
    [0, 2π) sin repetir el extremo, así que la muestra que falta es la de 0
    otra vez.
    """
    angulos = np.asarray(thetas, dtype=np.float64)
    valores = np.asarray(par, dtype=np.float64)
    if angulos.size != valores.size or angulos.size < 3:
        raise ValueError("hacen falta tantos pares como ángulos, y al menos tres")

    cerrado_x = np.append(angulos, TAU)
    cerrado_y = np.append(valores, valores[0])
    medio = float(np.trapezoid(cerrado_y, cerrado_x)) / TAU
    exceso = cerrado_y - medio

    acumulada = np.concatenate(
        [[0.0], np.cumsum(np.diff(cerrado_x) * (exceso[:-1] + exceso[1:]) / 2.0)]
    )
    energia = float(np.max(acumulada) - np.min(acumulada))
    return Fluctuacion(
        thetas=cerrado_x,
        acumulada=acumulada,
        energia=Julios(energia),
        theta_maximo=float(cerrado_x[int(np.argmax(acumulada))]),
        theta_minimo=float(cerrado_x[int(np.argmin(acumulada))]),
    )


def inercia_necesaria(
    energia: Julios,
    omega_media: float,
    coeficiente: float = FLUCTUACION_RECOMENDADA,
) -> KgM2:
    """J = ΔE / (Cs · ω̄²), en kg·m².

    `omega_media` en rad/s. Es el único sitio del núcleo donde entra una
    velocidad, y entra como condición de servicio: el programa sigue siendo
    función de θ y girar más despacio no cambia lo que se escribe, solo
    cuánto volante hace falta para que se note suave.
    """
    if omega_media <= 0.0:
        raise ValueError(f"la velocidad media debe ser positiva, no {omega_media}")
    if not 0.0 < coeficiente <= 1.0:
        raise ValueError(f"el coeficiente de fluctuación va entre 0 y 1, no {coeficiente}")
    return KgM2(float(energia) / (coeficiente * omega_media**2))


def fluctuacion_con(inercia: KgM2, energia: Julios, omega_media: float) -> float:
    """El camino inverso: con la inercia que ya hay, cuánto varía la velocidad.

    Sirve para saber si el propio cartucho ya hace de volante. Tres levas de
    POM en un árbol no son mucha inercia, pero tampoco son cero, y la
    pregunta que importa es si hace falta **añadir** algo.
    """
    if float(inercia) <= 0.0 or omega_media <= 0.0:
        raise ValueError("la inercia y la velocidad media deben ser positivas")
    return float(energia) / (float(inercia) * omega_media**2)


def vueltas_por_minuto(omega: float) -> float:
    """Para poder hablar de la manivela en unidades de persona."""
    return omega * 60.0 / TAU


def desde_vueltas_por_minuto(rpm: float) -> float:
    return rpm * TAU / 60.0


__all__ = [
    "FLUCTUACION_RECOMENDADA",
    "Fluctuacion",
    "desde_vueltas_por_minuto",
    "fluctuacion",
    "fluctuacion_con",
    "inercia_necesaria",
    "vueltas_por_minuto",
]
