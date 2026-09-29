"""La ficha de módulo y la máquina que los reúne.

Un módulo declara lo que pide y lo que da. La app comprueba que el conjunto
encaje: es la regla 6 de CLAUDE.md, «ningún módulo sin ficha».

La ficha es del **tipo**, no de la instalación. El desfase y la bahía
pertenecen al montaje, no al catálogo: una estación de pedal no tiene fase,
su instalación sí. Por eso `ModuloMontado` envuelve a `FichaModulo`.

Los canales son cables. Cada uno tiene exactamente un módulo que lo produce
—la leva o el tambor que lo almacena— y uno o varios que lo consumen aguas
abajo. `Maquina` comprueba ese cableado.
"""

from __future__ import annotations

from enum import StrEnum
from itertools import pairwise
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from core.program import Programa, Unidad
from core.units import (
    Angulo,
    Arco,
    Energia,
    Fuerza,
    Inercia,
    Longitud,
    LongitudConCero,
    Par,
)


class Familia(StrEnum):
    """Las cinco capas de la ontología, más la estructura."""

    FUENTE_HUMANA = "fuente_humana"
    ACUMULADOR = "acumulador"
    MEMORIA = "memoria"
    TRANSMISION = "transmision"
    ACTUADOR = "actuador"
    ESTRUCTURA = "estructura"


class ModoFallo(StrEnum):
    """Qué hace el módulo cuando falta energía o algo lo bloquea."""

    PARA_EN_SECO = "para_en_seco"
    CEDE_BLANDO = "cede_blando"
    SE_LIBERA = "se_libera"


class Proceso(StrEnum):
    LASER = "laser"
    CNC = "cnc"
    IMPRESION_3D = "impresion_3d"
    PLANTILLA = "plantilla"
    COMERCIAL = "comercial"


class _Base(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class Identidad(_Base):
    nombre: str = Field(min_length=1)
    familia: Familia
    version: str = Field(min_length=1)
    contrato: str | None = None
    """Qué contrato mecánico cumple. Ver `docs/contratos.md`."""


class InterfazMecanica(_Base):
    """Dónde y cómo se monta."""

    bahia: str | None = None
    eje: str | None = None
    anclaje: str | None = None
    ancho: Longitud
    alto: Longitud
    fondo: Longitud


class Fase(_Base):
    """Qué parte del ciclo ocupa el módulo.

    `arco = None` significa que trabaja durante toda la vuelta, que es el caso
    de cualquier módulo continuo. Un módulo de evento ocupa una porción, y dos
    que compitan por el mismo espacio físico no pueden solaparse.
    """

    arco: Arco | None = None
    cero_relativo: Angulo = Angulo(0.0)


class Canal(_Base):
    """Un canal visto desde un módulo.

    `rol` dice de qué lado está: la leva **produce** el canal, el seguidor lo
    **consume**. Es lo que permite encadenar módulos sin inventar un grafo
    aparte.
    """

    nombre: str = Field(min_length=1)
    rol: Literal["produce", "consume"]
    tipo: Literal["continuo", "evento"]
    unidad: Unidad
    minimo: float | None = None
    maximo: float | None = None

    @model_validator(mode="after")
    def _rango_coherente(self) -> Canal:
        if self.minimo is not None and self.maximo is not None and self.minimo >= self.maximo:
            raise ValueError(
                f"canal '{self.nombre}': el mínimo ({self.minimo}) no es menor "
                f"que el máximo ({self.maximo})."
            )
        return self


class Balance(_Base):
    """Lo que el módulo pide o aporta al eje maestro.

    El signo es lo que hace que la suma funcione sin casos especiales: una
    estación de pedal aporta, una sierra consume, y el presupuesto de par (C6)
    los suma igual.
    """

    signo: Literal["aporta", "consume"]
    par_pico: Par
    par_medio: Par
    energia_ciclo: Energia
    inercia: Inercia = Inercia(0.0)

    @model_validator(mode="after")
    def _signo_coherente(self) -> Balance:
        esperado_negativo = self.signo == "aporta"
        for campo, valor in (
            ("par_pico", float(self.par_pico)),
            ("par_medio", float(self.par_medio)),
            ("energia_ciclo", float(self.energia_ciclo)),
        ):
            if valor == 0.0:
                continue
            if esperado_negativo != (valor < 0.0):
                raise ValueError(
                    f"{campo} = {valor} no cuadra con signo='{self.signo}'. "
                    "Lo que aporta va en negativo; lo que consume, en positivo."
                )
        return self


class EnvolventePropia(_Base):
    """Los límites del módulo, distintos de los de la clase de máquina."""

    recorrido_max: LongitudConCero | None = None
    velocidad_max: float | None = Field(default=None, gt=0.0)
    fuerza_max: Fuerza | None = None
    radio_rodillo: Longitud | None = None
    """Solo seguidores. C3 lo necesita para el offset y para la curvatura."""


class Ergonomia(_Base):
    """Solo para `FUENTE_HUMANA`.

    `curva_fuerza` es la fuerza que una persona puede dar en cada punto del
    recorrido, normalizado de 0 a 1. No es un número: el cuerpo es mucho más
    fuerte en unos ángulos que en otros, y ajustar la resistencia a esa curva
    es un problema de diseño de levas (C9).
    """

    postura: str = Field(min_length=1)
    recorrido: Longitud
    curva_fuerza: list[tuple[float, Fuerza]] = Field(min_length=2)
    ciclo_trabajo: str = Field(min_length=1)

    @model_validator(mode="after")
    def _curva_normalizada(self) -> Ergonomia:
        posiciones = [p for p, _ in self.curva_fuerza]
        if posiciones[0] != 0.0 or posiciones[-1] != 1.0:
            raise ValueError(
                "curva_fuerza: la posición va normalizada de 0,0 a 1,0 y debe "
                f"empezar en 0,0 y acabar en 1,0; empieza en {posiciones[0]} y "
                f"acaba en {posiciones[-1]}."
            )
        for anterior, siguiente in pairwise(posiciones):
            if siguiente <= anterior:
                raise ValueError(
                    f"curva_fuerza: las posiciones deben crecer; {siguiente} no "
                    f"es mayor que {anterior}."
                )
        return self


class Fabricacion(_Base):
    material: str = Field(min_length=1)
    proceso: Proceso
    n_piezas: int = Field(ge=1)
    coste_estimado: float | None = Field(default=None, ge=0.0)
    minutos_montaje: float | None = Field(default=None, ge=0.0)


class FichaModulo(_Base):
    """Un módulo del catálogo. Mismo formulario a cualquier escala."""

    identidad: Identidad
    interfaz: InterfazMecanica
    fase: Fase = Fase()
    canales: list[Canal] = Field(default_factory=list)
    cinematica: str | None = None
    """Clave en el registro de `core/actors/`. No se incrusta la función:
    una función no se serializa, y el catálogo es dato, no código."""
    balance: Balance
    envolvente: EnvolventePropia = EnvolventePropia()
    modo_fallo: ModoFallo
    ergonomia: Ergonomia | None = None
    fabricacion: Fabricacion

    @model_validator(mode="after")
    def _coherencia(self) -> FichaModulo:
        es_humana = self.identidad.familia is Familia.FUENTE_HUMANA
        if es_humana and self.ergonomia is None:
            raise ValueError(
                f"'{self.identidad.nombre}' es una fuente humana y no declara "
                "ergonomía. Sin curva de fuerza no se puede dimensionar."
            )
        if not es_humana and self.ergonomia is not None:
            raise ValueError(
                f"'{self.identidad.nombre}' no es una fuente humana, así que la ergonomía sobra."
            )
        nombres = [c.nombre for c in self.canales]
        repetidos = sorted({n for n in nombres if nombres.count(n) > 1})
        if repetidos:
            raise ValueError(f"'{self.identidad.nombre}' declara dos veces el canal {repetidos}.")
        return self

    def canales_por_rol(self, rol: Literal["produce", "consume"]) -> frozenset[str]:
        return frozenset(c.nombre for c in self.canales if c.rol == rol)


class ModuloMontado(_Base):
    """Una instancia concreta de un módulo dentro de una máquina."""

    ficha: FichaModulo
    desfase: Angulo = Angulo(0.0)
    bahia: str | None = None

    @property
    def nombre(self) -> str:
        return self.ficha.identidad.nombre


class Maquina(_Base):
    """Un conjunto de módulos montados sobre un eje, con su programa."""

    nombre: str = Field(min_length=1)
    modulos: list[ModuloMontado] = Field(min_length=1)
    programa: Programa

    @model_validator(mode="after")
    def _cableado(self) -> Maquina:
        producidos: dict[str, list[str]] = {}
        consumidos: dict[str, list[str]] = {}
        for m in self.modulos:
            for canal in m.ficha.canales_por_rol("produce"):
                producidos.setdefault(canal, []).append(m.nombre)
            for canal in m.ficha.canales_por_rol("consume"):
                consumidos.setdefault(canal, []).append(m.nombre)

        for canal, quienes in sorted(producidos.items()):
            if len(quienes) > 1:
                raise ValueError(
                    f"el canal '{canal}' lo producen {sorted(quienes)}. "
                    "Un canal tiene un solo productor."
                )

        huerfanos = sorted(set(consumidos) - set(producidos))
        if huerfanos:
            raise ValueError(
                f"canales consumidos que nadie produce: {huerfanos}. "
                "Falta la memoria que los almacena."
            )

        del_programa = self.programa.canales
        sin_pista = sorted(set(producidos) - del_programa)
        if sin_pista:
            raise ValueError(f"módulos que producen canales sin pista en el programa: {sin_pista}.")
        sin_productor = sorted(del_programa - set(producidos))
        if sin_productor:
            raise ValueError(
                f"pistas del programa que ningún módulo produce: {sin_productor}. "
                "Añade la leva o el tambor que las almacena."
            )
        return self


__all__ = [
    "Balance",
    "Canal",
    "EnvolventePropia",
    "Ergonomia",
    "Fabricacion",
    "Familia",
    "Fase",
    "FichaModulo",
    "Identidad",
    "InterfazMecanica",
    "Maquina",
    "ModoFallo",
    "ModuloMontado",
    "Proceso",
]
