"""El veredicto de la envolvente.

Regla 5 de CLAUDE.md: **un fallo de envolvente no es una excepción**. Que una
frase no quepa en el cartucho o que un ángulo de presión se pase de 30° es un
resultado legítimo del cálculo, no un error del programa. Se devuelve, se
enseña al usuario y se le dice qué cambiar.

Cada incidencia lleva el ángulo donde ocurre, cuando lo hay, para poder
señalarlo sobre el dibujo en lugar de soltar un mensaje suelto.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, computed_field, model_validator

from core.units import AnguloCiclo

Gravedad = Literal["error", "aviso"]
"""`error` impide fabricar. `aviso` deja pasar pero conviene mirarlo."""


class Incidencia(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    gravedad: Gravedad
    codigo: str = Field(min_length=1)
    """Identificador estable, para poder traducirlo y contarlo.
    Por ejemplo `angulo_presion_excedido` o `capacidad_superada`."""
    mensaje: str = Field(min_length=1)
    theta: AnguloCiclo | None = None
    sugerencia: str | None = None
    """Qué puede hacer quien lo recibe. Sin esto, el veredicto solo frustra."""


class Veredicto(BaseModel):
    """Resultado de pasar algo por su envolvente."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    @model_validator(mode="before")
    @classmethod
    def _descartar_apto_entrante(cls, datos: object) -> object:
        """`apto` sale en el JSON pero nunca entra.

        Es un campo calculado: se serializa para que quien lea el JSON no tenga
        que deducirlo, y se descarta al deserializar porque la única verdad son
        las incidencias. Así la ida y vuelta funciona y, a la vez, no existe
        forma de guardar un veredicto que se contradiga. El resto de campos
        desconocidos siguen fallando: un nombre mal escrito no pasa en silencio.
        """
        if isinstance(datos, dict):
            return {k: v for k, v in datos.items() if k != "apto"}
        return datos

    incidencias: tuple[Incidencia, ...] = ()
    metricas: dict[str, float] = Field(default_factory=dict)
    """Lo medido, para poder enseñarlo y compararlo entre versiones:
    ángulo de presión máximo, radio de curvatura mínimo, error de trazo."""

    @computed_field  # type: ignore[prop-decorator]
    @property
    def apto(self) -> bool:
        """Calculado, nunca almacenado: así no puede contradecir a la lista."""
        return not any(i.gravedad == "error" for i in self.incidencias)

    @property
    def errores(self) -> tuple[Incidencia, ...]:
        return tuple(i for i in self.incidencias if i.gravedad == "error")

    @property
    def avisos(self) -> tuple[Incidencia, ...]:
        return tuple(i for i in self.incidencias if i.gravedad == "aviso")

    def con(self, *incidencias: Incidencia) -> Veredicto:
        """Devuelve un veredicto nuevo con más incidencias. No muta."""
        return Veredicto(
            incidencias=self.incidencias + incidencias,
            metricas=self.metricas,
        )


__all__ = ["Gravedad", "Incidencia", "Veredicto"]
