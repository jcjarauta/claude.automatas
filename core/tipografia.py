"""Escribir un texto con una fuente monotrazo. C0 · la puerta de entrada.

**Qué problema resuelve.** El compilador quiere una `Escritura`: trazos
en orden, con el lápiz apoyado. Eso es justo lo que da un canvas y lo que
NO da una imagen ni una fuente normal —el contorno de una «o» son dos
círculos cerrados, y el trazo de la pluma es el anillo que hay entre
ellos—. Una fuente **monotrazo** es la excepción: sus glifos ya son
líneas centrales, dibujadas para recorrerlas con una pluma, que es
exactamente lo que hace esta máquina.

Así que escribir un texto no necesita visión por computador: necesita la
fuente correcta.

**Puro, como todo `core/`.** La fuente entra como dato ya cargado; de
leerla del disco se encarga quien llame. Y nada de modelos de lenguaje:
la regla 4 pide mismo input, misma geometría, byte a byte.

**Unidades.** La fuente viene en sus propias unidades enteras y con la y
hacia abajo, que es como se distribuye desde 1967. Aquí se convierte una
vez a metros con la y hacia arriba, y no se vuelve a tocar: SI dentro.
"""

from __future__ import annotations

import itertools
import math

from pydantic import BaseModel, ConfigDict, Field

from core.errors import LetraDesconocida
from core.escritura import Escritura, Trazo
from core.units import Longitud, Metros

PuntoDeFuente = tuple[int, int]

ENLACE = 0.5
"""Hasta dónde se enlazan dos trazos seguidos, en alturas de x.

**Medido sobre la fuente, no elegido.** En la Hershey cursiva los huecos
entre trazos consecutivos de una palabra caen en dos grupos separados:
los de 0 a 0,46 alturas de x —que son los enlaces que la letra inglesa
ya trae dibujados— y los de 0,8 en adelante, que son levantadas de
verdad: el punto de una i, el salto a otra palabra. Medio es el valle
entre los dos.

Importa más de lo que parece: **cada vuelo del lápiz se come grados de
la vuelta del árbol**, así que enlazar o no decide si una frase cabe.
"""


class Glifo(BaseModel):
    """Una letra en unidades de la fuente, con la y hacia abajo."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    lado_izquierdo: int
    """Dónde empieza el dibujo respecto del punto de inserción."""
    avance: int
    """Cuánto corre el cursor hasta la letra siguiente."""
    trazos: list[list[PuntoDeFuente]]
    """Vacío en el espacio, que avanza y no dibuja."""


class Fuente(BaseModel):
    """Una fuente monotrazo entera. Es dato: un JSON en `docs/fuentes/`."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    nombre: str = Field(min_length=1)
    procedencia: str = Field(min_length=1)
    """De dónde sale y con qué licencia. Va en la ficha del pedido."""
    linea_base: float
    """La y de la línea base en unidades de fuente. Hacia abajo, así que
    es positiva y las mayúsculas quedan por encima, en negativo."""
    altura_mayuscula: float
    altura_de_x: float
    glifos: dict[str, Glifo]

    def faltan(self, texto: str) -> list[str]:
        """Los caracteres distintos que esta fuente no sabe dibujar."""
        return sorted({c for c in texto if c not in self.glifos})


def _trazos_colocados(texto: str, fuente: Fuente, escala: float) -> list[list[tuple[float, float]]]:
    """Los glifos puestos en fila, ya en metros y con la y hacia arriba."""
    cursor, salida = 0.0, []
    for letra in texto:
        glifo = fuente.glifos[letra]
        for trazo in glifo.trazos:
            salida.append(
                [
                    ((x - glifo.lado_izquierdo + cursor) * escala, (fuente.linea_base - y) * escala)
                    for x, y in trazo
                ]
            )
        cursor += glifo.avance
    return salida


def _enlazar(
    trazos: list[list[tuple[float, float]]], hasta: float
) -> list[list[tuple[float, float]]]:
    """Une los trazos seguidos cuyo hueco no llega a `hasta`, en metros.

    Con `hasta` a cero no se une nada: es lo que se pide para ver la
    fuente tal cual, sin los enlaces de la letra inglesa.
    """
    if hasta <= 0.0 or not trazos:
        return trazos
    salida = [list(trazos[0])]
    for trazo in trazos[1:]:
        if math.dist(salida[-1][-1], trazo[0]) <= hasta:
            # El punto repetido no aporta nada y deja una cuerda de
            # longitud cero, que es lo que `redondear_esquinas` no sabe
            # mirar.
            salida[-1].extend(trazo[1:] if math.dist(salida[-1][-1], trazo[0]) == 0.0 else trazo)
        else:
            salida.append(list(trazo))
    return salida


def _vale(trazo: list[tuple[float, float]]) -> bool:
    """Un trazo de un punto o de longitud cero no se puede reparametrizar."""
    if len(trazo) < 2:
        return False
    return any(a != b for a, b in itertools.pairwise(trazo))


def escribir(
    texto: str,
    fuente: Fuente,
    altura_de_x: Longitud,
    enlace: float = ENLACE,
    nombre: str = "",
) -> Escritura:
    """El texto, como lo escribiría una pluma: trazos en orden y en metros.

    `altura_de_x` es lo que medirá una «o», y es la única escala que se
    da: el resto lo recoloca `encajar` cuando la frase entra en la caja de
    escritura. `enlace` va en alturas de x, no en metros, para que una
    frase grande y una pequeña se enlacen igual.
    """
    if not texto.strip():
        raise ValueError("el texto está vacío: no hay nada que escribir")
    if faltan := fuente.faltan(texto):
        raise LetraDesconocida(
            f"la fuente «{fuente.nombre}» no tiene "
            + ", ".join(f"«{c}»" for c in faltan)
            + ". Escríbelo con los caracteres que sí tiene, o añádelos a la fuente."
        )

    escala = float(altura_de_x) / fuente.altura_de_x
    trazos = _enlazar(_trazos_colocados(texto, fuente, escala), enlace * float(altura_de_x))
    buenos = [Trazo(puntos=[(Metros(x), Metros(y)) for x, y in t]) for t in trazos if _vale(t)]
    if not buenos:
        raise ValueError(f"«{texto}» no deja ni un trazo que dibujar")
    return Escritura(nombre=nombre or texto, trazos=buenos)


__all__ = ["ENLACE", "Fuente", "Glifo", "escribir"]
