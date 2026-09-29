"""Unidades del proyecto: SI dentro, milímetros y grados solo en los bordes.

Regla 3 de CLAUDE.md. Hay dos capas de defensa, porque protegen de dos errores
distintos:

1. `NewType` hace que mypy distinga `Metros` de `Radianes` y rechace un `float`
   desnudo donde se espera una magnitud. Coste en tiempo de ejecución: ninguno.
2. Los alias validados (`Longitud`, `AnguloCiclo`, ...) llevan rangos de
   plausibilidad. Cazan el error que de verdad ocurre: alguien escribe `80`
   pensando en milímetros donde el campo espera metros, o `90` pensando en
   grados donde espera radianes. Ochenta metros y noventa radianes no son
   valores de este dominio, así que el validador los rechaza.

La conversión a unidades humanas vive aquí y en ningún otro sitio de `core/`.
"""

from __future__ import annotations

import math
from typing import Annotated, Final, NewType

from pydantic import Field

TAU: Final[float] = 2.0 * math.pi
"""Una vuelta completa del eje maestro, en radianes."""

# ---------------------------------------------------------------------------
# Magnitudes
# ---------------------------------------------------------------------------

Metros = NewType("Metros", float)
Radianes = NewType("Radianes", float)
Newtons = NewType("Newtons", float)
NewtonMetro = NewType("NewtonMetro", float)
Julios = NewType("Julios", float)
Kilogramos = NewType("Kilogramos", float)
KgM2 = NewType("KgM2", float)

# ---------------------------------------------------------------------------
# Constructores desde unidades humanas
# ---------------------------------------------------------------------------


def mm(valor: float) -> Metros:
    """Milímetros a metros. `mm(80)` son 0,08 m."""
    return Metros(valor / 1000.0)


def grados(valor: float) -> Radianes:
    """Grados a radianes. `grados(30)` son 0,5236 rad."""
    return Radianes(math.radians(valor))


def vueltas(valor: float) -> Radianes:
    """Vueltas de eje a radianes. `vueltas(0.25)` es un cuarto de vuelta."""
    return Radianes(valor * TAU)


def a_mm(valor: Metros) -> float:
    """Metros a milímetros. Solo para emisores e interfaz."""
    return float(valor) * 1000.0


def a_grados(valor: Radianes) -> float:
    """Radianes a grados. Solo para emisores e interfaz."""
    return math.degrees(float(valor))


def a_vueltas(valor: Radianes) -> float:
    """Radianes a vueltas de eje."""
    return float(valor) / TAU


# ---------------------------------------------------------------------------
# Alias validados
#
# Los límites no son físicos, son de plausibilidad: marcan dónde acaba este
# dominio. Una máquina de mesa no tiene piezas de diez metros ni pares de diez
# kilonewton-metro. Un valor fuera de rango casi siempre es una conversión mal
# hecha, no un diseño ambicioso.
# ---------------------------------------------------------------------------

Longitud = Annotated[Metros, Field(gt=0.0, le=10.0)]
"""Longitud positiva, de una décima de milímetro a diez metros."""

LongitudConCero = Annotated[Metros, Field(ge=0.0, le=10.0)]
"""Como `Longitud`, pero admite cero: desplazamientos, holguras, offsets."""

AnguloCiclo = Annotated[Radianes, Field(ge=0.0, lt=TAU)]
"""Posición dentro de una vuelta. Cerrado en 0, abierto en 2π: el punto final
no se almacena nunca, porque sería el mismo que el inicial."""

Arco = Annotated[Radianes, Field(gt=0.0, le=TAU)]
"""Duración angular. Positiva y como mucho una vuelta entera."""

Angulo = Annotated[Radianes, Field(ge=-TAU, le=TAU)]
"""Ángulo con signo, para desfases y recorridos de palanca."""

Fuerza = Annotated[Newtons, Field(ge=-1.0e5, le=1.0e5)]
"""Fuerza con signo. Negativa cuando el módulo aporta en lugar de consumir."""

Par = Annotated[NewtonMetro, Field(ge=-1.0e4, le=1.0e4)]
"""Par con signo. Negativo cuando el módulo aporta."""

Energia = Annotated[Julios, Field(ge=-1.0e6, le=1.0e6)]
"""Energía por ciclo, con signo."""

Masa = Annotated[Kilogramos, Field(gt=0.0, le=1.0e4)]

Inercia = Annotated[KgM2, Field(ge=0.0, le=1.0e3)]
"""Momento de inercia que el módulo aporta al conjunto. Cero si es despreciable."""
