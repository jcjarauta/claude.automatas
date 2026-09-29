"""Lo que hay que cortar: la pieza y sus metadatos.

Este modelo lo comparten los tres emisores de fabricación —DXF para corte
digital, plantilla en papel para copistería y dossier de montaje— porque los
tres describen la misma pieza por vías distintas.

**La geometría llega en metros**, como sale del núcleo. La conversión a
milímetros ocurre al maquetar, en un solo sitio, y no antes.

Los siete metadatos son obligatorios y no hay valor por defecto para ninguno.
Una plantilla impresa sin material ni espesor obliga a preguntar, y quien la
recibe suele estar en otro taller y en otro momento.
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, model_validator

from core.units import Espesor, Longitud, Metros

Punto = tuple[Metros, Metros]
"""Un punto en metros, en el sistema de la propia pieza."""


class Veta(StrEnum):
    """Hacia dónde debe ir la veta de la madera.

    En contrachapado y en DM importa: una pieza estrecha cortada a
    contraveta se parte por donde no toca.
    """

    INDIFERENTE = "indiferente"
    LARGO = "largo"
    ANCHO = "ancho"


class Taladro(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    centro: Punto
    diametro: Longitud


class Polilinea(BaseModel):
    """Una línea auxiliar: ejes, marcas de alineación, contornos ocultos."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    puntos: list[Punto] = Field(min_length=2)
    cerrada: bool = False


class Pieza(BaseModel):
    """Una pieza a cortar, con todo lo que hace falta para fabricarla."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    # -- los siete metadatos obligatorios ------------------------------------
    nombre: str = Field(min_length=1)
    numero: str = Field(min_length=1)
    conjunto: str = Field(min_length=1)
    material: str = Field(min_length=1)
    espesor: Espesor
    cantidad: int = Field(ge=1)
    veta: Veta

    # -- geometría, en metros ------------------------------------------------
    contorno: list[Punto] = Field(min_length=3)
    """Cerrado de forma implícita: el último punto no repite al primero."""
    taladros: list[Taladro] = Field(default_factory=list)
    referencias: list[Polilinea] = Field(default_factory=list)
    marca_fase: Punto | None = None
    """Dónde está el cero del cartucho. Sin esto, una leva se monta desfasada
    y la máquina escribe basura."""

    @model_validator(mode="after")
    def _contorno_sin_repetir_el_cierre(self) -> Pieza:
        primero = self.contorno[0]
        ultimo = self.contorno[-1]
        if abs(primero[0] - ultimo[0]) < 1e-12 and abs(primero[1] - ultimo[1]) < 1e-12:
            raise ValueError(
                f"'{self.nombre}': el contorno repite el punto de cierre. Es "
                "cerrado de forma implícita, como las pistas del programa."
            )
        return self

    @property
    def limites(self) -> tuple[Metros, Metros, Metros, Metros]:
        """Caja envolvente en metros: x mínimo, y mínimo, x máximo, y máximo.

        Incluye taladros y referencias: un taladro que se salga del contorno
        sigue habiendo que dibujarlo.
        """
        xs = [p[0] for p in self.contorno]
        ys = [p[1] for p in self.contorno]
        for taladro in self.taladros:
            radio = taladro.diametro / 2.0
            xs += [Metros(taladro.centro[0] - radio), Metros(taladro.centro[0] + radio)]
            ys += [Metros(taladro.centro[1] - radio), Metros(taladro.centro[1] + radio)]
        for referencia in self.referencias:
            xs += [p[0] for p in referencia.puntos]
            ys += [p[1] for p in referencia.puntos]
        return Metros(min(xs)), Metros(min(ys)), Metros(max(xs)), Metros(max(ys))

    @property
    def ancho(self) -> Metros:
        x0, _, x1, _ = self.limites
        return Metros(x1 - x0)

    @property
    def alto(self) -> Metros:
        _, y0, _, y1 = self.limites
        return Metros(y1 - y0)


__all__ = ["Pieza", "Polilinea", "Punto", "Taladro", "Veta"]
