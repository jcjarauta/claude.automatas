"""Masa e inercia de una pieza prismática, a partir de su polígono.

Todas las piezas del escribiente se cortan de plancha: son prismas rectos de
espesor constante. Para un prisma, la masa y el momento polar de inercia
salen **exactos** de integrales sobre el polígono de la base, sin mallar nada
y sin kernel de CAD. Son las fórmulas de Green de toda la vida:

    A   = (1/2)  * suma de (x[i]*y[i+1] - x[i+1]*y[i])
    Ix  = (1/12) * suma de (x[i]*y[i+1] - x[i+1]*y[i]) * (y[i]^2 + y[i]*y[i+1] + y[i+1]^2)
    Iy  = (1/12) * suma de (x[i]*y[i+1] - x[i+1]*y[i]) * (x[i]^2 + x[i]*x[i+1] + x[i+1]^2)
    J   = Ix + Iy

El momento polar es lo que pide C7 para dimensionar el volante, y la masa lo
que pide C6 para el presupuesto de par. Que salgan de aquí y no de un modelo
3-D tiene una ventaja que no es solo de dependencias: el número se calcula
sobre **el mismo polígono que se va a cortar**, así que no puede
desincronizarse del DXF.

Lo que esto no hace: piezas que no son prismas —un eje torneado, un tornillo—
y piezas con espesor variable. Para eso hará falta otra cosa, y llegará
cuando exista un bastidor que modelar.
"""

from __future__ import annotations

from typing import Final

import numpy as np
import numpy.typing as npt

from core.units import Espesor, KgM2, Kilogramos, Metros

Arreglo = npt.NDArray[np.float64]

DENSIDADES: Final[dict[str, float]] = {
    "POM": 1410.0,
    "PMMA": 1190.0,
    "contrachapado de abedul": 680.0,
    "DM": 750.0,
    "aluminio": 2700.0,
    "acero": 7850.0,
}
"""kg/m³ nominales de catálogo. En cuanto el banco pese una pieza de verdad,
el número medido manda y este queda de valor por defecto."""


def densidad_de(material: str) -> float:
    """Busca el material por su principio: «POM 5 mm» es POM.

    El campo `material` de una pieza lleva el espesor pegado porque es lo que
    se pide en la tienda, y aquí solo interesa de qué está hecha.
    """
    for nombre, valor in DENSIDADES.items():
        if material.lower().startswith(nombre.lower()):
            return valor
    raise KeyError(
        f"no hay densidad para '{material}'. Añádela a DENSIDADES o corrige el "
        f"nombre; los conocidos son {sorted(DENSIDADES)}."
    )


def _cruzados(poligono: Arreglo) -> tuple[Arreglo, Arreglo, Arreglo]:
    puntos = np.asarray(poligono, dtype=np.float64)
    if puntos.ndim != 2 or puntos.shape[1] != 2 or puntos.shape[0] < 3:
        raise ValueError("un polígono son al menos tres puntos de dos coordenadas")
    siguiente = np.roll(puntos, -1, axis=0)
    cruz = puntos[:, 0] * siguiente[:, 1] - siguiente[:, 0] * puntos[:, 1]
    return puntos, siguiente, cruz


def area(poligono: Arreglo) -> float:
    """Área en m². Siempre positiva: el sentido de giro no es asunto suyo."""
    _, _, cruz = _cruzados(poligono)
    return abs(float(np.sum(cruz))) / 2.0


def centroide(poligono: Arreglo) -> tuple[float, float]:
    puntos, siguiente, cruz = _cruzados(poligono)
    superficie = float(np.sum(cruz)) / 2.0
    if abs(superficie) < 1e-18:
        raise ValueError("un polígono de área nula no tiene centroide")
    x = float(np.sum((puntos[:, 0] + siguiente[:, 0]) * cruz)) / (6.0 * superficie)
    y = float(np.sum((puntos[:, 1] + siguiente[:, 1]) * cruz)) / (6.0 * superficie)
    return x, y


def momento_polar(poligono: Arreglo, eje: tuple[float, float] = (0.0, 0.0)) -> float:
    """∫(x²+y²)·dA respecto del eje dado, en m⁴.

    El eje por defecto es el origen porque es donde va el árbol: una leva se
    cala por su centro, no por su centroide.
    """
    puntos, siguiente, cruz = _cruzados(np.asarray(poligono) - np.asarray(eje))
    en_x = np.sum(
        cruz * (puntos[:, 1] ** 2 + puntos[:, 1] * siguiente[:, 1] + siguiente[:, 1] ** 2)
    )
    en_y = np.sum(
        cruz * (puntos[:, 0] ** 2 + puntos[:, 0] * siguiente[:, 0] + siguiente[:, 0] ** 2)
    )
    return abs(float(en_x + en_y)) / 12.0


def masa_de_prisma(poligono: Arreglo, espesor: Espesor, densidad: float) -> Kilogramos:
    return Kilogramos(area(poligono) * float(espesor) * densidad)


def inercia_de_prisma(
    poligono: Arreglo,
    espesor: Espesor,
    densidad: float,
    eje: tuple[float, float] = (0.0, 0.0),
) -> KgM2:
    """Momento de inercia respecto del eje de giro, en kg·m².

    Es el que entra en la energía cinética del árbol, ½·J·ω², y por tanto el
    que decide cuánto volante hace falta para que la manivela no vaya a
    tirones.
    """
    return KgM2(momento_polar(poligono, eje) * float(espesor) * densidad)


def descontar_taladro(
    poligono: Arreglo,
    centro: tuple[Metros, Metros],
    diametro: Metros,
    eje: tuple[float, float] = (0.0, 0.0),
) -> tuple[float, float]:
    """Lo que el taladro quita de área y de momento polar.

    Se resta en vez de mallar el agujero: un círculo tiene fórmula cerrada, y
    el error de aproximarlo por un polígono sería mayor que lo que se ahorra.
    Devuelve (área, momento polar) del agujero, para restarlos.
    """
    radio = float(diametro) / 2.0
    superficie = np.pi * radio**2
    distancia = float(np.hypot(float(centro[0]) - eje[0], float(centro[1]) - eje[1]))
    # Steiner: el momento propio del disco más el traslado al eje de giro.
    return superficie, np.pi * radio**4 / 2.0 + superficie * distancia**2


__all__ = [
    "DENSIDADES",
    "area",
    "centroide",
    "densidad_de",
    "descontar_taladro",
    "inercia_de_prisma",
    "masa_de_prisma",
    "momento_polar",
]
