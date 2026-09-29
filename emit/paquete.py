"""El paquete de fabricación: qué archivos salen y qué lleva cada uno.

Una máquina no se entrega como un DXF ni como un PDF, sino como un juego de
documentos con reglas distintas:

| | Plantillas de corte | Dossier de montaje |
| --- | --- | --- |
| Para quién | El carpintero, sobre el tablero | Quien monta, sobre la mesa |
| Escala | 1:1 exacta, siempre | Libre, con la escala rotulada |
| Vida | Se pega, se corta y se tira | Se guarda con la máquina |
| Cuadro | Sí, en cada hoja | No |

Son dos archivos y no dos secciones del mismo, y la separación no es de orden:
un papel con una vista a escala libre al lado de un contorno a tamaño real
acaba con alguien cortando por la vista. `escribir_pdf` se niega a mezclar
escalas en un documento; aquí se decide qué va en cuál.

El dossier se construye en E6. Hasta entonces `Paquete.dossier` es `None`, que
es la forma honesta de decir que todavía no existe.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from emit.calibracion import PerfilImpresora, aplicar
from emit.layout import Formato, Lamina, formato_minimo_juego, maquetar_juego
from emit.pieza import Pieza
from emit.template import escribir_pdf

FORMATO_POR_DEFECTO = Formato.A3
"""Cuando ninguna hoja admite todas las piezas enteras hay que trocear igual,
y entonces más vale la hoja que cualquier copistería tiene a mano."""


@dataclass(frozen=True)
class Paquete:
    """Lo que se le entrega a quien va a fabricar."""

    plantillas: Path
    formato: Formato
    hojas: int
    dossier: Path | None = None
    perfil: str | None = None
    """Nombre de la impresora para la que se corrigió, si se corrigió."""


def formato_del_pedido(piezas: Sequence[Pieza], pedido: Formato | None = None) -> Formato:
    """El formato lo elige el pedido, no la pieza.

    Si quien pide no dice nada, se busca la hoja **más pequeña** donde todo
    quepa entero: trocear y pegar es lo que de verdad estropea una plantilla,
    y una hoja grande de más solo cuesta dinero.
    """
    if pedido is not None:
        return pedido
    return formato_minimo_juego(piezas) or FORMATO_POR_DEFECTO


def escribir_paquete(
    piezas: Sequence[Pieza],
    destino: Path | str,
    *,
    formato: Formato | None = None,
    perfil: PerfilImpresora | None = None,
) -> Paquete:
    """Escribe `plantillas.pdf` en `destino` y dice qué ha escrito.

    Con `perfil`, las hojas salen predeformadas para esa impresora. El cuadro
    de calibración se escala con ellas: compensar no es verificar, y quien las
    reciba tiene que poder seguir comprobando la escala.
    """
    if not piezas:
        raise ValueError("un paquete sin piezas no es un paquete")

    elegido = formato_del_pedido(piezas, formato)
    laminas: list[Lamina] = maquetar_juego(piezas, elegido)
    if perfil is not None:
        laminas = [aplicar(lamina, perfil) for lamina in laminas]

    carpeta = Path(destino)
    ruta = escribir_pdf(laminas, carpeta / "plantillas.pdf")

    return Paquete(
        plantillas=ruta,
        formato=elegido,
        hojas=len(laminas),
        dossier=None,
        perfil=perfil.nombre if perfil is not None else None,
    )


__all__ = ["FORMATO_POR_DEFECTO", "Paquete", "escribir_paquete", "formato_del_pedido"]
