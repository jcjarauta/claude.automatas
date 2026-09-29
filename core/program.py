"""El programa: qué hace la máquina en cada grado del eje maestro.

Principio 1 de `docs/baseline.md`: **todo se indexa por ángulo, nunca por
tiempo**. Aquí no hay segundos ni velocidades. Un `Programa` describe una
vuelta completa del eje, y la máquina la recorre a la velocidad que quiera
quien la acciona.

Dos clases de pista, que se corresponden con las dos clases de memoria física:

- `PistaContinua` -> una leva. Alta resolución, un canal por leva apilada.
- `PistaEvento`   -> un tambor de púas o pasadores. Baja resolución, muchos
  canales.

El escribiente solo usa pistas continuas. Las de evento existen en el modelo
desde ahora para que añadirlas en E10 no obligue a migrar nada, pero nada las
consume todavía.
"""

from __future__ import annotations

from itertools import pairwise
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from core.units import TAU, AnguloCiclo, Arco

Unidad = Literal["m", "rad", "N", "binario"]
"""Qué magnitud lleva el valor de un canal. `binario` solo en pistas de evento."""


class _Base(BaseModel):
    """Configuración común: inmutable y sin campos de más."""

    model_config = ConfigDict(frozen=True, extra="forbid")


class PistaContinua(_Base):
    """Un canal cuyo valor es una función continua del ángulo.

    Las muestras se guardan como dos listas paralelas en vez de como pares:
    ocupa la mitad en JSON, convierte a numpy sin copiar y el invariante de
    longitud lo comprueba el validador.

    El punto final **no** se almacena. θ vive en [0, 2π) y el cierre del ciclo
    es implícito: guardar la muestra de 2π permitiría que contradijera a la de
    0, y no hay forma de que un valor así sea correcto.
    """

    tipo: Literal["continua"] = "continua"
    canal: str = Field(min_length=1)
    unidad: Unidad
    thetas: list[AnguloCiclo] = Field(min_length=2)
    valores: list[float] = Field(min_length=2)

    @model_validator(mode="after")
    def _comprobar(self) -> PistaContinua:
        if len(self.thetas) != len(self.valores):
            raise ValueError(
                f"canal '{self.canal}': {len(self.thetas)} ángulos frente a "
                f"{len(self.valores)} valores. Deben ser tantos de uno como de otro."
            )
        for anterior, siguiente in pairwise(self.thetas):
            if siguiente <= anterior:
                raise ValueError(
                    f"canal '{self.canal}': los ángulos deben crecer estrictamente; "
                    f"{siguiente} no es mayor que {anterior}."
                )
        if self.unidad == "binario":
            raise ValueError(
                f"canal '{self.canal}': una pista continua no puede ser binaria. "
                "Usa una pista de evento."
            )
        return self


class Evento(_Base):
    """Algo que ocurre en un punto del ciclo.

    `arco` es su duración angular. `None` significa instantáneo: una púa que
    pulsa un diente, un pasador que suelta un trinquete.
    """

    theta: AnguloCiclo
    arco: Arco | None = None

    @property
    def fin(self) -> float:
        """Dónde termina el evento. Puede pasar de 2π: el ciclo da la vuelta."""
        return float(self.theta) + (float(self.arco) if self.arco is not None else 0.0)


class PistaEvento(_Base):
    """Un canal binario: en cada θ, ocurre o no ocurre.

    Declarado en E1, sin consumidores hasta E10.
    """

    tipo: Literal["evento"] = "evento"
    canal: str = Field(min_length=1)
    eventos: list[Evento] = Field(min_length=1)

    @model_validator(mode="after")
    def _comprobar(self) -> PistaEvento:
        thetas = [e.theta for e in self.eventos]
        for anterior, siguiente in pairwise(thetas):
            if siguiente <= anterior:
                raise ValueError(
                    f"canal '{self.canal}': los eventos deben ir ordenados por ángulo "
                    f"y sin repetir; {siguiente} no es mayor que {anterior}."
                )
        return self


Pista = Annotated[PistaContinua | PistaEvento, Field(discriminator="tipo")]


class Programa(_Base):
    """Una vuelta completa del eje maestro, canal a canal."""

    nombre: str = Field(min_length=1)
    pistas: list[Pista] = Field(min_length=1)

    @model_validator(mode="after")
    def _canales_unicos(self) -> Programa:
        nombres = [p.canal for p in self.pistas]
        repetidos = sorted({n for n in nombres if nombres.count(n) > 1})
        if repetidos:
            raise ValueError(
                f"el programa '{self.nombre}' declara dos veces el canal "
                f"{repetidos}. Un canal tiene una sola pista."
            )
        return self

    @property
    def canales(self) -> frozenset[str]:
        return frozenset(p.canal for p in self.pistas)

    def pista(self, canal: str) -> PistaContinua | PistaEvento:
        for p in self.pistas:
            if p.canal == canal:
                return p
        raise KeyError(f"el programa '{self.nombre}' no tiene el canal '{canal}'")


__all__ = [
    "TAU",
    "Evento",
    "Pista",
    "PistaContinua",
    "PistaEvento",
    "Programa",
    "Unidad",
]
