"""Lo que cuesta un escribiente: lo que se compra y lo que se corta.

Dos partidas que se calculan de forma distinta y por eso no se mezclan.

**Lo que se compra** es dato. Vive en `bench/precios.json` con fecha, fuente
y un enlace por línea, igual que el kerf y los perfiles de impresora. Aquí
solo se suma y se normaliza a IVA incluido.

**Lo que se corta** no tiene precio de catálogo, y esa es la conclusión más
útil de haberlo buscado: ni una sola plataforma de mecanizado online ni un
solo taller de Barcelona publica lo que cuesta esta pieza. Todos piden subir
el archivo. Lo único publicado son tarifas por hora. Así que el corte no se
copia de una tabla: **se calcula** a partir de la geometría real de la leva
—que el compilador ya conoce— y de unos parámetros de corte declarados.

El número que sale de aquí no es un presupuesto. Es lo que permite discutir
uno: saber que el tiempo de máquina de las tres levas son minutos, y que por
tanto lo que se está pagando es la preparación y el mínimo de facturación,
cambia por completo con quién hay que hablar y qué hay que pedirle.

**Por qué el IVA se suma y no se descuenta.** Arrels Fundació no repercute
IVA en la mayor parte de su actividad, así que el IVA soportado no es un
anticipo que se recupera: es coste. Un catálogo que da el precio sin IVA y
otro que lo da con IVA, sumados tal cual, mienten un 21 % en la parte que no
se ve.
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from pydantic import BaseModel, ConfigDict, Field

from compile.escribiente import Compilacion, Escribiente
from core.solido import densidad_de
from core.units import Espesor, Longitud, Metros, mm
from emit.pieza import Pieza

IVA = 0.21
"""El tipo general español. Vive aquí y no en el JSON de precios porque es
una regla, no una medida."""

SEGUNDOS_POR_HORA = 3600.0
SEGUNDOS_POR_MINUTO = 60.0


def con_iva(precio: float, *, iva_incluido: bool) -> float:
    """Lleva cualquier precio al mismo terreno. Ver la cabecera."""
    return precio if iva_incluido else precio * (1.0 + IVA)


# ---------------------------------------------------------------------------
# Los parámetros de corte
# ---------------------------------------------------------------------------


class Fresado(BaseModel):
    """Cómo se corta, declarado.

    Ninguno de estos números está medido: son valores corrientes para POM-C
    con fresa de metal duro de dos filos, del orden de lo que recomienda
    cualquier tabla de plásticos técnicos. El POM se mecaniza bien y admite
    bastante más; se ha elegido la parte conservadora del rango porque un
    presupuesto que sale corto es peor que uno que sale largo.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    diametro_fresa: Longitud = mm(3.0)
    """Ø3 porque el taladro más pequeño de la leva es Ø3 y porque los radios
    interiores del perfil no admiten mucho más."""
    dientes: int = Field(default=2, ge=1, le=6)
    revoluciones_por_minuto: float = Field(default=15000.0, gt=0.0, le=60000.0)
    avance_por_diente: Longitud = mm(0.04)
    profundidad_por_pasada: Espesor = mm(1.8)
    """Con fresa de Ø3 en POM se puede bajar más, pero a plena ranura el
    problema no es la fuerza: es sacar la viruta."""
    factor_de_acabado: float = Field(default=0.5, gt=0.0, le=1.0)
    """La pasada de acabado va más despacio. El canto de la leva es LA
    superficie funcional de la máquina: es donde rueda el seguidor."""
    rendimiento: float = Field(default=0.6, gt=0.0, le=1.0)
    """Lo que queda del avance nominal después de esquinas, entradas,
    salidas, rápidos y aceleraciones. Una máquina pequeña no alcanza su
    avance programado en un perfil ondulado."""

    @property
    def avance(self) -> float:
        """Avance de desbaste, en metros por segundo."""
        por_minuto = float(self.avance_por_diente) * self.dientes * self.revoluciones_por_minuto
        return por_minuto / SEGUNDOS_POR_MINUTO


class Tarifa(BaseModel):
    """Lo que cobra quien corta.

    La preparación se paga **una vez por lote**, no por pieza: es lo que
    decide si las tres levas de un pedido salen de un amarre o de tres, y en
    una pieza cuyo tiempo de corte son minutos, es la partida mayor.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    euros_por_hora: float = Field(default=55.0, gt=0.0)
    preparacion_minutos: float = Field(default=15.0, ge=0.0)
    minimo_facturable: float = Field(default=0.0, ge=0.0)

    def coste(self, segundos: float) -> float:
        """Lo que cuesta un lote que tarda esos segundos en cortarse."""
        horas = (segundos + self.preparacion_minutos * SEGUNDOS_POR_MINUTO) / SEGUNDOS_POR_HORA
        return max(horas * self.euros_por_hora, self.minimo_facturable)


@dataclass(frozen=True)
class Recorrido:
    """Cuánto camino hace la herramienta, en metros, por concepto.

    `contorno` y `taladros` son **por pasada**: son geometría y no dependen
    del proceso. Cuántas pasadas hacen falta sí depende, y por eso va en un
    campo aparte en vez de estar multiplicado dentro.
    """

    contorno: float
    taladros: float
    pinchazos: float
    """Bajadas en vertical, que van a avance reducido y por eso se cuentan
    aparte. Esta sí es la profundidad entera, porque se hace de una vez."""
    pasadas: int
    """Las de desbaste. El acabado va siempre y se cuenta en el tiempo, que
    es donde se nota: va más despacio, no más lejos."""


def _perimetro(contorno: list[tuple[Metros, Metros]]) -> float:
    puntos = np.asarray(contorno, dtype=np.float64)
    lados = np.diff(np.vstack([puntos, puntos[:1]]), axis=0)
    return float(np.hypot(lados[:, 0], lados[:, 1]).sum())


def recorrido(pieza: Pieza, espesor: Espesor, fresado: Fresado) -> Recorrido:
    """El camino que recorre la fresa para sacar esta pieza.

    **La fresa no va por el contorno de la pieza: va por fuera**, desplazada
    su radio. En una curva cerrada eso alarga el camino en 2·pi·r_fresa
    exactamente, sea cual sea la forma. Presupuestar con el perímetro de la
    pieza se queda corto, poco pero siempre.

    Un taladro mayor que la fresa se interpola dando vueltas; uno del mismo
    diámetro se pincha. Son tiempos de orden muy distinto.
    """
    radio = float(fresado.diametro_fresa) / 2.0
    pasadas = math.ceil(float(espesor) / float(fresado.profundidad_por_pasada))

    contorno = _perimetro(pieza.contorno) + 2.0 * math.pi * radio

    taladros = 0.0
    pinchazos = 0.0
    for taladro in pieza.taladros:
        diametro = float(taladro.diametro)
        if diametro > float(fresado.diametro_fresa) * 1.2:
            taladros += math.pi * (diametro - 2.0 * radio)  # helicoidal
        else:
            pinchazos += float(espesor)

    return Recorrido(contorno=contorno, taladros=taladros, pinchazos=pinchazos, pasadas=pasadas)


def tiempo_de_fresado(piezas: list[Pieza], espesor: Espesor, fresado: Fresado) -> float:
    """Segundos de máquina, sin contar la preparación.

    Desbaste a avance pleno, y una pasada de acabado más, a avance reducido,
    sobre contorno y taladros: el canto de la leva es la superficie sobre la
    que rueda el seguidor y no se deja como salga del desbaste.
    """
    avance = fresado.avance * fresado.rendimiento
    acabado = avance * fresado.factor_de_acabado
    segundos = 0.0
    for pieza in piezas:
        camino = recorrido(pieza, espesor, fresado)
        perfil = camino.contorno + camino.taladros
        segundos += perfil * camino.pasadas / avance
        segundos += perfil / acabado
        segundos += camino.pinchazos / (avance / 3.0)
    return segundos


# ---------------------------------------------------------------------------
# Los precios, que son dato
# ---------------------------------------------------------------------------


class Linea(BaseModel):
    """Una línea del despiece, tal como está en el catálogo del proveedor."""

    model_config = ConfigDict(extra="allow")

    concepto: str
    precio: float = Field(ge=0.0)
    cantidad: float = Field(default=1.0, ge=0.0)
    iva_incluido: bool = True
    verificado: bool = True
    url: str = Field(min_length=1)
    pedir: str | None = None
    """Qué hay que preguntar si el precio no está verificado."""

    @property
    def importe(self) -> float:
        return con_iva(self.precio, iva_incluido=self.iva_incluido) * self.cantidad


class Precios(BaseModel):
    """El fichero entero, validado."""

    model_config = ConfigDict(extra="allow")

    fecha: str = Field(min_length=1)
    cartucho: list[Linea]
    plataforma: list[Linea]


def cargar_precios(ruta: Path | str = Path("bench/precios.json")) -> Precios:
    return Precios.model_validate(json.loads(Path(ruta).read_text(encoding="utf-8")))


def _precio_de_plancha(precios: Precios) -> float:
    for linea in precios.cartucho:
        if "plancha" in linea.concepto.lower() or "POM" in linea.concepto:
            return con_iva(linea.precio, iva_incluido=linea.iva_incluido)
    raise KeyError("no hay precio de plancha en el fichero de precios")


# ---------------------------------------------------------------------------
# La valoración
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Valoracion:
    """Lo que cuesta un escribiente, desglosado por dónde se decide."""

    material_del_cartucho: float
    comercial_del_cartucho: float
    mecanizado: float
    plataforma: float
    segundos_de_maquina: float
    levas_por_plancha: int
    sin_verificar: tuple[str, ...]

    @property
    def cartucho(self) -> float:
        """Lo que cuesta la parte personalizada, que se rehace en cada pedido."""
        return self.material_del_cartucho + self.comercial_del_cartucho + self.mecanizado

    @property
    def total(self) -> float:
        return self.cartucho + self.plataforma

    def pedidos_para_amortizar(self, precio_de_la_maquina: float) -> int:
        """Cuántos cartuchos hay que cortar para que salga a cuenta comprar
        la fresadora en vez de encargar el corte.

        El ahorro por pedido es todo el mecanizado: con máquina propia el
        tiempo de taller sigue existiendo, pero en un taller ocupacional esa
        hora **es el producto**, no un coste que se evita.
        """
        if self.mecanizado <= 0.0:
            raise ValueError("sin coste de mecanizado no hay nada que amortizar")
        return math.ceil(precio_de_la_maquina / self.mecanizado)


def valorar(
    compilacion: Compilacion,
    maquina: Escribiente,
    precios: Precios,
    fresado: Fresado | None = None,
    tarifa: Tarifa | None = None,
) -> Valoracion:
    """Pone precio a un pedido ya compilado.

    Las tres levas se cortan **en un solo amarre**: son del mismo material y
    del mismo espesor, caben juntas en la plancha y comparten programa. Por
    eso la preparación se paga una vez, y por eso cortarlas de una en una
    triplicaría la partida mayor del cartucho.
    """
    fresado = fresado or Fresado()
    tarifa = tarifa or Tarifa()
    espesor = maquina.espesor_leva

    segundos = tiempo_de_fresado(compilacion.piezas, espesor, fresado)
    mecanizado = tarifa.coste(segundos)

    # Cuántas levas salen de una plancha: reparto por estantes con el lado
    # de la caja envolvente más el diámetro de la fresa, que es el sitio que
    # hay que dejar para que pase entre dos piezas.
    lado = 0.0
    for pieza in compilacion.piezas:
        puntos = np.asarray(pieza.contorno, dtype=np.float64)
        lado = max(lado, float(np.ptp(puntos[:, 0])), float(np.ptp(puntos[:, 1])))
    paso = lado + float(fresado.diametro_fresa) * 2.0
    por_lado = int(1.0 / paso)
    levas_por_plancha = por_lado * por_lado
    material = _precio_de_plancha(precios) / levas_por_plancha * len(compilacion.piezas)

    comercial_cartucho = sum(
        linea.importe for linea in precios.cartucho if "plancha" not in linea.concepto.lower()
    )
    plataforma = sum(linea.importe for linea in precios.plataforma)

    sin_verificar = tuple(
        linea.concepto for linea in precios.cartucho + precios.plataforma if not linea.verificado
    )

    # La densidad se consulta para que un material sin ficha falle aquí y no
    # más tarde, al pesar el cartucho.
    densidad_de(maquina.material_leva)

    return Valoracion(
        material_del_cartucho=material,
        comercial_del_cartucho=comercial_cartucho,
        mecanizado=mecanizado,
        plataforma=plataforma,
        segundos_de_maquina=segundos,
        levas_por_plancha=levas_por_plancha,
        sin_verificar=sin_verificar,
    )


__all__ = [
    "IVA",
    "Fresado",
    "Linea",
    "Precios",
    "Recorrido",
    "Tarifa",
    "Valoracion",
    "cargar_precios",
    "con_iva",
    "recorrido",
    "tiempo_de_fresado",
    "valorar",
]
