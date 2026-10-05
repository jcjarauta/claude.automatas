"""El catálogo de tarjetas, y la máquina que escribe en cada una.

Aquí vive el disco; la geometría la pone `core.tarjeta`, que es puro.

**Por qué un catálogo y no un par de números en el código.** El tamaño de
la tarjeta es la palanca de capacidad más grande que tiene esta máquina,
por encima del enlace y de los renglones: con la caja de 80 × 24
«Montserrat» hay que medirla y con una de 40 × 14 sale limpia. Una
decisión así se toma por pedido, y lo que se decide por pedido no puede
estar escrito en una constante.
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

from compile.escribiente import Escribiente
from core.tarjeta import Tarjeta
from core.units import Metros

RAIZ = Path(__file__).resolve().parent.parent
TARJETAS = RAIZ / "docs" / "tarjetas"


def tarjetas() -> list[str]:
    """Las del catálogo, por nombre."""
    return sorted(f.stem for f in TARJETAS.glob("*.json"))


@lru_cache(maxsize=16)
def cargar_tarjeta(nombre: str) -> Tarjeta:
    """Una tarjeta del catálogo, validada contra su modelo."""
    ruta = TARJETAS / f"{nombre}.json"
    if not ruta.exists():
        hay = ", ".join(tarjetas()) or "ninguna"
        raise FileNotFoundError(f"no hay tarjeta «{nombre}» en docs/tarjetas/. Hay: {hay}")
    return Tarjeta.model_validate(json.loads(ruta.read_text(encoding="utf-8")))


def maquina_para(tarjeta: Tarjeta, maquina: Escribiente | None = None) -> Escribiente:
    """La misma máquina, escribiendo en esa tarjeta.

    Cambia **solo la caja**: el centro en y no se toca, porque es dónde
    está el papel respecto de los pivotes y eso lo fija el bastidor, no el
    formato. Un papel más pequeño se centra en el mismo sitio.
    """
    base = maquina or Escribiente()
    return base.model_copy(
        update={
            "caja_ancho": Metros(tarjeta.caja_ancho),
            "caja_alto": Metros(tarjeta.caja_alto),
        }
    )


__all__ = ["cargar_tarjeta", "maquina_para", "tarjetas"]
