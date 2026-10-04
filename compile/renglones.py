"""Una frase larga en renglones: un cartucho por renglón, todos a la misma escala.

La capacidad la pone la vuelta, no el tamaño de la máquina
(docs/propuesta_dimensionado.md): una vuelta da para un renglón de unas
diecisiete letras de inglesa. Un texto más largo se escribe en varias
vueltas, una por renglón, cambiando el cartucho entre una y otra.

**La composición se encaja una sola vez, entera.** Si cada renglón se
encajara por su cuenta, cada uno saldría a la escala que llenara la caja y
las letras de «Feliz» no medirían lo que las de «cumpleaños». Así que la
frase completa se coloca en la caja como si fuera de una vuelta, y cada
renglón se compila con sus trazos **donde quedaron** (`compilar(...,
en_la_caja=True)`).

**Los calajes no se tocan.** Son de la máquina (contrato de calaje,
congelado): todos los cartuchos de un pedido, y de todos los pedidos, se
montan sobre los mismos brazos.

El pedido dice qué trazos van en cada renglón:

    {"nombre": "...", "trazos": [...], "renglones": [[0, 1, 2], [3, 4]]}

Sin `renglones` es un pedido de una vuelta, como siempre.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from compile.escribiente import Compilacion, Escribiente, compilar, encajar_en_la_caja
from core.cam.envelope import LimitesLeva
from core.escritura import Capacidad, Escritura, Trazo
from core.units import mm

Renglones = tuple[tuple[int, ...], ...]


@dataclass(frozen=True)
class Pedido:
    escritura: Escritura
    renglones: Renglones | None
    """Qué trazos van en cada renglón, de arriba abajo. `None`: una vuelta."""


def leer_pedido(ruta: Path | str) -> Pedido:
    """Lee el JSON del pedido. Coordenadas en **milímetros**; a metros se
    pasa aquí, en la frontera."""
    ruta = Path(ruta)
    datos = json.loads(ruta.read_text(encoding="utf-8"))
    escritura = Escritura(
        nombre=datos.get("nombre", ruta.stem),
        trazos=[
            Trazo(puntos=[(mm(float(x)), mm(float(y))) for x, y in t]) for t in datos["trazos"]
        ],
    )
    crudos = datos.get("renglones")
    renglones = None if crudos is None else tuple(tuple(int(i) for i in r) for r in crudos)
    if renglones is not None:
        comprobar(renglones, len(escritura.trazos))
    return Pedido(escritura=escritura, renglones=renglones)


def comprobar(renglones: Renglones, trazos: int) -> None:
    """Los renglones reparten los trazos: cada uno en un renglón y solo en
    uno, y ningún renglón vacío. Un trazo que falta no se escribiría; uno
    repetido se escribiría dos veces, en dos cartuchos."""
    if not renglones or any(not r for r in renglones):
        raise ValueError("cada renglón tiene que llevar al menos un trazo")
    todos = [i for r in renglones for i in r]
    if sorted(todos) != list(range(trazos)):
        faltan = sorted(set(range(trazos)) - set(todos))
        repetidos = sorted({i for i in todos if todos.count(i) > 1})
        fuera = sorted({i for i in todos if not 0 <= i < trazos})
        raise ValueError(
            f"los renglones no reparten los {trazos} trazos: faltan {faltan}, "
            f"repetidos {repetidos}, fuera de rango {fuera}"
        )


def compilar_por_renglones(
    escritura: Escritura,
    renglones: Renglones,
    maquina: Escribiente | None = None,
    capacidad: Capacidad | None = None,
    limites: LimitesLeva | None = None,
) -> list[Compilacion]:
    """Un cartucho por renglón. Cada uno con su veredicto: que un renglón no
    quepa no es una excepción, es lo que hay que contarle al cliente."""
    maquina = maquina or Escribiente()
    comprobar(renglones, len(escritura.trazos))
    colocada = encajar_en_la_caja(escritura, maquina)
    return [
        compilar(
            Escritura(
                nombre=f"{escritura.nombre}_{numero}",
                trazos=[colocada.trazos[i] for i in indices],
            ),
            maquina,
            capacidad,
            limites,
            en_la_caja=True,
        )
        for numero, indices in enumerate(renglones, start=1)
    ]


__all__ = ["Pedido", "Renglones", "compilar_por_renglones", "comprobar", "leer_pedido"]
