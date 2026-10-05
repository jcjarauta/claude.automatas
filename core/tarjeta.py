"""El papel donde escribe la máquina, y la caja que queda dentro.

**La tarjeta no es la caja de escritura.** La tarjeta es lo que el cliente
se lleva; la caja es el rectángulo que la punta recorre dentro de ella. El
contrato ya lo tenía así para el único formato que había —un A7 apaisado de
105 × 74 con 12,5 de margen a los lados y 22 delante y detrás, que dejan los
80 × 30 de caja— pero los tres números vivían sueltos y nada decía que el
tercero saliera de los dos primeros.

Aquí el margen es el dato y **la caja se deriva**. Declarar las dos cosas
permitiría que se contradijeran, que es el fallo del que este repositorio ya
tiene media docena de entradas: dos sitios con el mismo número se separan.

**Qué NO declara esta ficha: si la máquina puede escribirla.** Eso no es una
propiedad del papel, es el veredicto del compilador, y aquí no hay ninguno.
La tentación era guardar un techo —«hasta 24 mm de alto escrito»— y resulta
que ese número **no existe**: medido un eje cada vez, una caja de 75,7 × 30
falla con «hola» tecleada y una de 85 × 33,7, más grande, pasa. Lo que
decide es la relación de curvatura de la leva, que depende de la frase
tanto como de la caja. Así que el catálogo no promete nada por escrito y lo
cruza `tests/compile/test_tarjetas.py`, compilando. Un número copiado aquí
se quedaría viejo el día que cambie el rodillo, y en silencio.
"""

from __future__ import annotations

from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, computed_field, model_validator

from core.units import Metros

LadoDeTarjeta = Annotated[Metros, Field(gt=0.005, le=0.5)]
"""De cinco milímetros a medio metro. Más estrecho que `Longitud`, que
llega a diez metros: el rango ancho no caza el error de magnitud, y aquí el
error fácil es teclear 105 en vez de 0,105."""

MargenDeTarjeta = Annotated[Metros, Field(ge=0.0, le=0.2)]
"""Admite cero —una tarjeta escrita a sangre— y se queda en veinte
centímetros."""


class Tarjeta(BaseModel):
    """Un formato del catálogo: el papel, sus márgenes y la caja que queda.

    Es dato, no código: un JSON por formato en `docs/tarjetas/`. Añadir un
    formato no es programar, igual que añadir una fuente o una pieza
    comercial.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    nombre: str = Field(min_length=1)
    descripcion: str = Field(min_length=1)
    """Para qué es y de dónde sale la medida. Va en el informe del pedido."""
    papel_ancho: LadoDeTarjeta
    """A lo ancho de la máquina, que es como se coloca el papel. Un
    marcapáginas se pone tumbado, así que su lado largo es este."""
    papel_alto: LadoDeTarjeta
    """En profundidad, alejándose de quien escribe."""
    margen_lados: MargenDeTarjeta
    margen_fondo: MargenDeTarjeta
    procedencia: str = Field(min_length=1)
    """De dónde sale el tamaño del papel: una norma, un uso comercial o una
    decisión nuestra. Sin esto, dentro de un año nadie sabe si los 85 × 55
    son una norma o algo que alguien escribió un martes."""

    @model_validator(mode="after")
    def _la_caja_tiene_que_existir(self) -> Tarjeta:
        """Dos márgenes que se comen el papel dejan una caja de lado cero o
        negativo. Pasaría la validación de cada campo por separado y daría
        una división por cero al encajar."""
        if 2.0 * float(self.margen_lados) >= float(self.papel_ancho):
            raise ValueError(
                f"«{self.nombre}»: los márgenes de los lados se comen el ancho del papel"
            )
        if 2.0 * float(self.margen_fondo) >= float(self.papel_alto):
            raise ValueError(f"«{self.nombre}»: los márgenes del fondo se comen el alto del papel")
        return self

    @computed_field  # type: ignore[prop-decorator]
    @property
    def caja_ancho(self) -> float:
        """Lo que queda del papel a lo ancho, en metros."""
        return float(self.papel_ancho) - 2.0 * float(self.margen_lados)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def caja_alto(self) -> float:
        """Lo que queda del papel en profundidad, en metros."""
        return float(self.papel_alto) - 2.0 * float(self.margen_fondo)


__all__ = ["LadoDeTarjeta", "MargenDeTarjeta", "Tarjeta"]
