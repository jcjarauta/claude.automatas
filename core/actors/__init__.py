"""Registro de actuadores: C1.

La ficha de un módulo nombra su cinemática por clave y aporta los parámetros.
Aquí se resuelve la clave. Si no existe, falla pronto y con nombre.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping

from core.actors.base import Actuador
from core.actors.cinco_barras import BrazoCincoBarras
from core.actors.palanca import PalancaElevadora
from core.errors import ActuadorDesconocido

_REGISTRO: dict[str, Callable[..., Actuador]] = {
    "brazo_cinco_barras_v1": BrazoCincoBarras,
    "palanca_elevadora_v1": PalancaElevadora,
}


def claves() -> tuple[str, ...]:
    """Las cinemáticas disponibles, ordenadas."""
    return tuple(sorted(_REGISTRO))


def construir(clave: str, parametros: Mapping[str, float]) -> Actuador:
    """Resuelve una clave de ficha a un actuador con sus parámetros."""
    fabrica = _REGISTRO.get(clave)
    if fabrica is None:
        raise ActuadorDesconocido(
            f"no hay ninguna cinemática llamada '{clave}'. Disponibles: {list(claves())}."
        )
    try:
        return fabrica(**parametros)
    except TypeError as exc:
        raise ActuadorDesconocido(
            f"los parámetros {dict(parametros)} no encajan con '{clave}': {exc}"
        ) from exc


__all__ = [
    "Actuador",
    "BrazoCincoBarras",
    "PalancaElevadora",
    "claves",
    "construir",
]
