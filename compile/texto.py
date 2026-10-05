"""De un texto a una `Escritura`. El front-end de la captura por teclado.

Es la primera etapa del patrón de compilación —captura, front-end,
núcleo, envolvente, emisores— para el camino más barato de todos: en vez
de dibujar la frase, se teclea.

Aquí vive el disco; la geometría la pone `core.tipografia`, que es puro.
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

from core.escritura import Escritura
from core.tipografia import ENLACE, Composicion, Fuente, componer
from core.tipografia import huecos as _huecos
from core.units import Longitud, mm

RAIZ = Path(__file__).resolve().parent.parent
FUENTES = RAIZ / "docs" / "fuentes"

ALTURA_DE_X = mm(10.0)
"""Lo que mide una «o» antes de encajarla en la caja.

Es una escala de partida y no una cota: `encajar` recoloca la frase en la
caja de escritura y la deja del tamaño que quepa. Importa, aun así,
porque `redondear_esquinas` redondea a un radio en milímetros, y lo que
ese radio significa depende de lo grande que venga la letra.
"""


def fuentes() -> list[str]:
    """Las que hay en `docs/fuentes/`, por nombre."""
    return sorted(f.stem for f in FUENTES.glob("*.json"))


@lru_cache(maxsize=8)
def cargar_fuente(nombre: str = "cursiva") -> Fuente:
    """Una fuente del repositorio, validada contra su modelo.

    En caché porque la lee cada pedido y son cien glifos que no cambian
    dentro de una ejecución.
    """
    ruta = FUENTES / f"{nombre}.json"
    if not ruta.exists():
        hay = ", ".join(fuentes()) or "ninguna"
        raise FileNotFoundError(f"no hay fuente «{nombre}» en docs/fuentes/. Hay: {hay}")
    return Fuente.model_validate(json.loads(ruta.read_text(encoding="utf-8")))


def composicion_de(
    texto: str,
    fuente: str = "cursiva",
    altura_de_x: Longitud = ALTURA_DE_X,
    enlace: float = ENLACE,
    nombre: str = "",
) -> Composicion:
    """El texto con esa fuente, repartido en renglones por sus saltos de
    línea. Un renglón es un cartucho.

    `nombre` es el del pedido —va grabado en cada leva—; sin él se usa el
    propio texto, que es lo que quiere un cliente.
    """
    return componer(
        texto, cargar_fuente(fuente), altura_de_x=altura_de_x, enlace=enlace, nombre=nombre
    )


def huecos_de(
    texto: str,
    fuente: str = "cursiva",
    altura_de_x: Longitud = ALTURA_DE_X,
) -> tuple[tuple[float, ...], ...]:
    """Qué separa cada trazo del siguiente, en alturas de x, por renglón.
    Es lo que el enlace decide unir o no."""
    return _huecos(texto, cargar_fuente(fuente), altura_de_x=altura_de_x)


def escritura_de(
    texto: str,
    fuente: str = "cursiva",
    altura_de_x: Longitud = ALTURA_DE_X,
    enlace: float = ENLACE,
    nombre: str = "",
) -> Escritura:
    """El texto escrito con esa fuente, listo para compilar de una tirada."""
    return composicion_de(texto, fuente, altura_de_x, enlace, nombre).escritura


__all__ = [
    "ALTURA_DE_X",
    "cargar_fuente",
    "composicion_de",
    "escritura_de",
    "fuentes",
    "huecos_de",
]
