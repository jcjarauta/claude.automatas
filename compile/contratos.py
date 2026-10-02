"""Los contratos congelados, como dato en vez de como prosa.

`docs/contratos.md` está escrito para leerlo y eso está bien: explica por qué
cada cota es la que es, que es lo que un número solo no dice. Pero los
números que contiene —Ø10 h7, el pasador a 18 mm, los postes a 71,1— los
necesita el compilador en Python **y** los necesita Onshape para dibujar la
plataforma, y hasta ahora se copiaban a mano en los dos sitios.

Copiar a mano es exactamente cómo la valona del casquillo acabó siendo Ø12
en tres documentos cuando el fabricante dice Ø15.

Así que los números viven en `docs/contratos.json`, validados aquí, y de ahí
salen a los dos lados: el compilador los lee, y `scripts/exportar_variables.py`
los convierte en la tabla de variables que se pega una vez en el Variable
Studio de Onshape. **Una fuente, una dirección de flujo.**

El markdown sigue siendo el sitio donde se explica el porqué y donde vive el
registro de cambios. Lo que deja de estar ahí es el número suelto.

Vive en `compile/` y no en `core/` porque lee un fichero, y el núcleo es
puro. El núcleo recibe parámetros; quien los va a buscar es el compilador.

**Un contrato tiene estado**, y no todos están congelados: el de bastidor
espera a que E4 diga si el modelo predice la realidad. Un valor `pendiente`
se puede usar para dibujar, pero no para prometer.
"""

from __future__ import annotations

import json
from enum import StrEnum
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from core.units import Metros

RUTA = Path("docs/contratos.json")


class Estado(StrEnum):
    CONGELADO = "congelado"
    """No se toca sin registrarlo en `docs/contratos.md`, con fecha y motivo."""
    PENDIENTE = "pendiente"
    """Se puede usar para dibujar; no se puede prometer. Espera a E4."""


class Valor(BaseModel):
    """Una cota del contrato, con lo que hace falta para usarla fuera.

    `unidad` no es decoración: el compilador trabaja en metros y radianes y
    Onshape en milímetros y grados, así que la conversión tiene que poder
    hacerse sin que nadie adivine qué es cada número. Es la regla 3 aplicada
    a la frontera con el CAD.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    nombre: str = Field(min_length=1, pattern=r"^[a-z][a-z0-9_]*$")
    """En minúsculas y con guion bajo: es un nombre de variable, y va a serlo
    en Python y en FeatureScript."""
    valor: float
    unidad: str = Field(min_length=1)
    """`m`, `rad`, `adimensional`."""
    descripcion: str = Field(min_length=1)
    tolerancia: str = ""

    @property
    def en_mm(self) -> float:
        """Para el CAD y para los rótulos. Falla si no es una longitud."""
        if self.unidad != "m":
            raise ValueError(f"'{self.nombre}' está en {self.unidad}, no en metros")
        return self.valor * 1000.0

    @property
    def metros(self) -> Metros:
        if self.unidad != "m":
            raise ValueError(f"'{self.nombre}' está en {self.unidad}, no en metros")
        return Metros(self.valor)

    @property
    def radianes(self) -> float:
        """La pareja de `metros`, que faltaba.

        Había accesor que comprueba la unidad para las longitudes y ninguno
        para los ángulos, así que un ángulo se leía como `.valor` a pelo —sin
        que nada dijera si estaba en radianes o en grados—, que es justo lo
        que la regla 3 existe para evitar.
        """
        if self.unidad != "rad":
            raise ValueError(f"'{self.nombre}' está en {self.unidad}, no en radianes")
        return self.valor


class Contrato(BaseModel):
    """Un grupo de cotas que se congelan juntas porque se usan juntas."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    nombre: str = Field(min_length=1)
    estado: Estado
    congelado_el: str = Field(default="", pattern=r"^(\d{4}-\d{2}-\d{2})?$")
    porque: str = Field(min_length=1)
    """Una línea. El desarrollo está en `docs/contratos.md`."""
    valores: list[Valor] = Field(min_length=1)

    def valor(self, nombre: str) -> Valor:
        for v in self.valores:
            if v.nombre == nombre:
                return v
        disponibles = ", ".join(v.nombre for v in self.valores)
        raise KeyError(f"el contrato '{self.nombre}' no define '{nombre}'. Tiene: {disponibles}")


class Contratos(BaseModel):
    """El fichero entero."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    version: str = Field(min_length=1)
    fecha: str = Field(min_length=1, pattern=r"^\d{4}-\d{2}-\d{2}$")
    contratos: list[Contrato] = Field(min_length=1)

    def contrato(self, nombre: str) -> Contrato:
        for c in self.contratos:
            if c.nombre == nombre:
                return c
        disponibles = ", ".join(c.nombre for c in self.contratos)
        raise KeyError(f"no hay contrato '{nombre}'. Hay: {disponibles}")

    def valor(self, contrato: str, nombre: str) -> Valor:
        return self.contrato(contrato).valor(nombre)

    @property
    def congelados(self) -> tuple[Contrato, ...]:
        return tuple(c for c in self.contratos if c.estado is Estado.CONGELADO)

    def variables(self) -> dict[str, Valor]:
        """Todas las cotas por su nombre, aplanadas.

        Es lo que se exporta a Onshape. Los nombres tienen que ser únicos
        entre contratos, porque en el Variable Studio comparten espacio.
        """
        planas: dict[str, Valor] = {}
        for contrato in self.contratos:
            for v in contrato.valores:
                if v.nombre in planas:
                    raise ValueError(
                        f"'{v.nombre}' está en dos contratos y las variables de Onshape "
                        "comparten un solo espacio de nombres"
                    )
                planas[v.nombre] = v
        return planas


def cargar(ruta: Path | str = RUTA) -> Contratos:
    return Contratos.model_validate(json.loads(Path(ruta).read_text(encoding="utf-8")))


__all__ = ["RUTA", "Contrato", "Contratos", "Estado", "Valor", "cargar"]
