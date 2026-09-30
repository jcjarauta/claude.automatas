"""La ficha de una pieza que se compra hecha.

La regla 6 dice que ningún módulo entra en una máquina sin ficha. Las piezas
comerciales son el tercer tipo de módulo —ni las genera el compilador como el
cartucho, ni se dibujan a mano como la plataforma— y hasta ahora no tenían la
suya: vivían como una línea en una tabla de precios y como un STEP bajado del
fabricante.

**Lo que esta ficha guarda son las cotas de interfaz**, que son las que otra
pieza toca. Del casquillo interesan el agujero, el exterior y el diámetro de
la valona; no interesa el chaflán. Del engranaje, módulo, dientes, ancho y
agujero. Todo lo demás es asunto del fabricante.

**Por qué la ficha manda sobre el modelo 3-D y no al revés.** Un STEP de
catálogo viene simplificado, a veces con el sólido equivocado, y cambia
cuando al fabricante le parece. Si el conjunto se construye alrededor de él,
un cambio de proveedor rompe la geometría en silencio. Aquí la cota vive con
su fuente y su fecha, el modelo se importa para mirar, y si los dos no
coinciden es un fallo que hay que investigar y no una cota que se acepta.

El coste de no tener esto ya se pagó: la valona del casquillo igus se anotó
como Ø12 leyendo mal un catálogo, acabó copiada en tres documentos y en el
cálculo del hueco al poste, y el fabricante dice Ø15. Una cota con fuente y
un test que la compruebe habría dejado el error en un sitio.
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field

from core.units import LongitudConCero


class FamiliaComercial(StrEnum):
    """Para qué sirve, que es como se busca en el despiece."""

    RODAMIENTO = "rodamiento"
    CASQUILLO = "casquillo"
    EJE = "eje"
    PASADOR = "pasador"
    MUELLE = "muelle"
    ENGRANAJE = "engranaje"
    SEPARADOR = "separador"
    FIJACION = "fijacion"
    INSTRUMENTO = "instrumento"
    MATERIAL = "material"


class Fuente(BaseModel):
    """De dónde sale la cota, para poder volver a mirarla.

    Sin esto, dentro de seis meses no hay forma de saber si un número se leyó
    en la ficha del fabricante o lo puso alguien de memoria.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    proveedor: str = Field(min_length=1)
    referencia: str = Field(min_length=1)
    url: str = Field(min_length=1)
    fecha: str = Field(min_length=1, pattern=r"^\d{4}-\d{2}-\d{2}$")
    verificado: bool = True
    """False cuando la cota no se ha podido leer en la página del fabricante
    y está pendiente de confirmar."""


class Cota(BaseModel):
    """Una medida de interfaz, en metros, con su tolerancia si la tiene."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    nombre: str = Field(min_length=1)
    valor: LongitudConCero
    tolerancia: str = ""
    """Como la escribe el fabricante: «h6», «±0,1», «d13». Texto y no número
    porque una tolerancia ISO no es un número."""
    critica: bool = False
    """True cuando otra pieza del diseño depende de esta cota. La valona del
    casquillo lo es: decide el hueco de la leva al poste."""


class PiezaComercial(BaseModel):
    """Una referencia de catálogo, con lo que el diseño necesita de ella."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    nombre: str = Field(min_length=1)
    """Cómo se le llama en el despiece, no cómo lo llama el fabricante."""
    familia: FamiliaComercial
    designacion: str = Field(min_length=1)
    """La referencia tal cual se pide: «MR63ZZ», «igus GFM-0810-06»."""
    cantidad: int = Field(ge=1)
    """Cuántas lleva una máquina."""
    fuente: Fuente
    cotas: list[Cota] = Field(min_length=1)
    material: str = ""
    nota: str = ""
    """Lo que hay que saber y no cabe en una cota: por qué esta referencia y
    no otra, qué pasa si se sustituye."""
    sustitutos: list[str] = Field(default_factory=list)
    """Otras referencias que valdrían, por si una se descataloga."""
    pedir: str = ""
    """Qué hay que preguntar al proveedor cuando la ficha está incompleta.
    Va aquí y no en un cuaderno aparte para que la duda viaje pegada a la
    cota que la tiene."""

    def cota(self, nombre: str) -> Cota:
        """La cota por su nombre. Falla si no está, en vez de devolver cero."""
        for c in self.cotas:
            if c.nombre == nombre:
                return c
        disponibles = ", ".join(c.nombre for c in self.cotas)
        raise KeyError(f"{self.nombre} no declara la cota '{nombre}'. Tiene: {disponibles}")

    @property
    def criticas(self) -> tuple[Cota, ...]:
        """Las cotas de las que depende algo del diseño."""
        return tuple(c for c in self.cotas if c.critica)


__all__ = ["Cota", "FamiliaComercial", "Fuente", "PiezaComercial"]
