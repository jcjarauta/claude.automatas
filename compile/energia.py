"""¿Puede una persona girar esto, y sale la letra limpia?

Junta C6, C7 y C9 sobre un cartucho ya compilado y contesta tres preguntas
que hasta ahora no tenían número:

1. **¿Llega la mano?** El par disponible en la manivela tiene que cubrir al
   pedido **en cada grado**, no de media. Si no llega, la respuesta no es
   apretar más: es un reductor, y el informe dice de cuánto.
2. **¿Va suave?** Lo que sobra en unos grados y falta en otros lo guarda la
   inercia. Si el propio cartucho no basta, hace falta volante, y el informe
   dice cuánto.
3. **¿Cuánto trabajo cuesta una vuelta?** Es lo que se nota en el brazo
   después de veinte frases.

Dos avisos sobre lo que hay debajo. Las cargas del seguidor —muelle,
rozamiento, inercia— **no están medidas**: son valores de partida
plausibles, y el banco de E4 los sustituirá. Y la curva de fuerza de la
manivela es un modelo, no una medida. Así que estos números sirven para
decidir la arquitectura —si hace falta reductor, si hace falta volante— y no
para prometerle a nadie un par concreto.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from pydantic import BaseModel, ConfigDict, Field

from compile.escribiente import SEGUIDORES, Compilacion
from core.cam.curves import derivada_ciclica
from core.energy.budget import CargaSeguidor, PresupuestoPar, presupuesto
from core.energy.flywheel import (
    FLUCTUACION_RECOMENDADA,
    Fluctuacion,
    desde_vueltas_por_minuto,
    fluctuacion,
    inercia_necesaria,
    referir,
    vueltas_por_minuto,
)
from core.energy.humano import Manivela, Transmision, relacion_minima
from core.units import TAU, Inercia, Julios, KgM2, Radianes
from core.verdict import Incidencia, Veredicto

MARGEN_DE_PAR = 1.3
"""Cuánto tiene que sobrar el par disponible sobre el pedido. Girar una
manivela al límite de lo que uno puede no es girarla: es forcejear, y el
forcejeo sale en el papel."""


class Accionamiento(BaseModel):
    """Cómo se mueve la máquina y qué se le resiste."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    manivela: Manivela = Field(default_factory=Manivela)
    transmision: Transmision = Field(default_factory=Transmision)
    vueltas_por_minuto: float = Field(default=30.0, gt=0.0, le=300.0)
    """A cuánto se piensa girar. No cambia lo que se escribe —el programa es
    función de θ— pero decide cuánta inercia hace falta para que se note
    suave y cuánto pesa el término inercial del par."""
    coeficiente_fluctuacion: float = Field(default=FLUCTUACION_RECOMENDADA, gt=0.0, le=1.0)
    carga: CargaSeguidor = Field(default_factory=CargaSeguidor)
    """La misma para los tres seguidores mientras no haya medidas propias.
    Está referida al **eje del seguidor**, no al del brazo."""
    inercia_en_la_manivela: Inercia = KgM2(0.0)
    """Lo que ya gira en el eje rápido: el piñón, la manivela y el volante si
    se pone ahí. Cuenta multiplicado por la relación al cuadrado."""
    inercia_en_el_arbol: Inercia = KgM2(0.0)
    """Lo que ya gira en el eje de levas además del cartucho: la rueda grande
    de la reducción. Cuenta tal cual."""

    @property
    def omega(self) -> float:
        return desde_vueltas_por_minuto(self.vueltas_por_minuto)


@dataclass(frozen=True)
class Energia:
    """Lo que cuesta girar el cartucho, y con qué hay que girarlo."""

    presupuesto: PresupuestoPar
    fluctuacion: Fluctuacion
    disponible: np.ndarray
    par_medio: float
    par_maximo: float
    trabajo_por_vuelta: Julios
    inercia_del_cartucho: KgM2
    inercia_disponible: KgM2
    """Todo lo que gira, referido al eje de levas: cartucho, rueda grande y
    lo que haya en la manivela multiplicado por la relación al cuadrado."""
    inercia_necesaria: KgM2
    volante_que_falta: KgM2
    volante_en_la_manivela: KgM2
    """Lo mismo, pero puesto en el eje de la manivela. Si la manivela gira n
    veces por vuelta del árbol, allí la velocidad es n veces mayor y hace
    falta n² veces menos inercia. Es el sitio donde poner un volante."""
    relacion_minima: float | None
    """La relación de manivela más pequeña que cubre el par pedido, o `None`
    si ni con la máxima llega."""


def analizar(
    compilacion: Compilacion,
    inercia_del_cartucho: KgM2,
    accionamiento: Accionamiento | None = None,
) -> tuple[Energia, Veredicto]:
    """El presupuesto de par y energía de un cartucho ya compilado."""
    accionamiento = accionamiento or Accionamiento()
    if not compilacion.perfiles:
        raise ValueError("no hay levas: la compilación no llegó a sintetizarlas")

    canales: dict[str, tuple[np.ndarray, np.ndarray, np.ndarray]] = {}
    for nombre in SEGUIDORES:
        perfil = compilacion.perfiles[nombre]
        paso = TAU / len(perfil)
        canales[nombre] = (perfil.psi, perfil.psi_prima, derivada_ciclica(perfil.psi_prima, paso))

    thetas = compilacion.perfiles[SEGUIDORES[0]].thetas
    cargas = {nombre: accionamiento.carga for nombre in SEGUIDORES}
    presupuestado = presupuesto(thetas, canales, cargas)

    omega = accionamiento.omega
    pedido = presupuestado.total(omega)
    disponible = accionamiento.transmision.disponible(accionamiento.manivela, thetas)

    incidencias: list[Incidencia] = []
    falta = disponible < MARGEN_DE_PAR * pedido
    minima = relacion_minima(
        accionamiento.manivela,
        pedido,
        thetas,
        rendimiento=accionamiento.transmision.rendimiento,
        margen=MARGEN_DE_PAR,
    )
    if bool(falta.any()):
        peor = int(np.argmax(MARGEN_DE_PAR * pedido - disponible))
        sugerencia = (
            f"monta un reductor de {minima:.0f}:1 entre la manivela y el árbol"
            if minima is not None
            else "ni con un reductor de 50:1 llega: baja el muelle o el rozamiento"
        )
        incidencias.append(
            Incidencia(
                gravedad="error",
                codigo="par_insuficiente",
                mensaje=(
                    f"a {np.degrees(thetas[peor]):.0f}° el árbol pide "
                    f"{pedido[peor]:.2f} N·m y la manivela da {disponible[peor]:.2f} N·m"
                ),
                theta=Radianes(float(thetas[peor])),
                sugerencia=sugerencia,
            )
        )

    variacion = fluctuacion(thetas, pedido)
    hace_falta = inercia_necesaria(variacion.energia, omega, accionamiento.coeficiente_fluctuacion)
    # Todo referido al eje de levas. Lo que gira en la manivela cuenta
    # multiplicado por la relación al cuadrado: ahí está el truco.
    disponible_total = (
        float(inercia_del_cartucho)
        + float(accionamiento.inercia_en_el_arbol)
        + float(referir(accionamiento.inercia_en_la_manivela, accionamiento.transmision.relacion))
    )
    falta_volante = max(0.0, float(hace_falta) - disponible_total)
    # La inercia necesaria va con 1/ω², así que en un eje que gira n veces
    # más deprisa hace falta n² veces menos. Un volante pequeño en la
    # manivela hace el trabajo de uno enorme en el árbol.
    en_la_manivela = falta_volante / accionamiento.transmision.relacion**2
    if falta_volante > 0.0:
        incidencias.append(
            Incidencia(
                gravedad="aviso",
                codigo="volante_necesario",
                mensaje=(
                    f"para que la velocidad no varíe más de un "
                    f"{accionamiento.coeficiente_fluctuacion:.0%} hacen falta "
                    f"{float(hace_falta) * 1e4:.1f} × 10⁻⁴ kg·m² y lo que ya gira aporta "
                    f"{disponible_total * 1e4:.1f}"
                ),
                sugerencia=(
                    f"un volante de {falta_volante * 1e4:.1f} × 10⁻⁴ kg·m² en el árbol, o "
                    f"—mucho mejor— uno de {en_la_manivela * 1e4:.1f} en el eje de la "
                    "manivela: la inercia que hace falta baja con el cuadrado de la "
                    "velocidad, y ahí se gira más deprisa"
                ),
            )
        )

    energia = Energia(
        presupuesto=presupuestado,
        fluctuacion=variacion,
        disponible=disponible,
        par_medio=presupuestado.medio(omega),
        par_maximo=presupuestado.maximo(omega),
        trabajo_por_vuelta=Julios(presupuestado.trabajo(omega)),
        inercia_del_cartucho=inercia_del_cartucho,
        inercia_disponible=KgM2(disponible_total),
        inercia_necesaria=hace_falta,
        volante_que_falta=KgM2(falta_volante),
        volante_en_la_manivela=KgM2(en_la_manivela),
        relacion_minima=minima,
    )
    veredicto = Veredicto(
        incidencias=tuple(incidencias),
        metricas={
            "par_medio": energia.par_medio,
            "par_maximo": energia.par_maximo,
            "trabajo_por_vuelta": float(energia.trabajo_por_vuelta),
            "energia_de_fluctuacion": float(variacion.energia),
            "inercia_necesaria": float(hace_falta),
            "inercia_disponible": disponible_total,
            "volante_que_falta": falta_volante,
            "volante_en_la_manivela": en_la_manivela,
            "vueltas_por_minuto": vueltas_por_minuto(omega),
            "relacion_minima": float(minima) if minima is not None else float("nan"),
        },
    )
    return energia, veredicto


__all__ = ["MARGEN_DE_PAR", "Accionamiento", "Energia", "analizar"]
