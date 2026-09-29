"""El cartucho montado: interferencias, pila y masa.

Hasta aquí cada leva se juzgaba sola. C3 dice si un perfil es fabricable y el
contacto dice si el rodillo apoya donde debe, pero **ninguno de los dos mira
el conjunto**: tres levas caladas en el mismo árbol, tres seguidores pivotando
en tres postes anclados al bastidor, y los postes atravesando los tres planos.

Lo que se comprueba aquí es geometría de montaje, y dos cosas de ella dependen
del pedido y no del diseño:

- **La leva crece con la frase.** Un barrido de seguidor mayor es un perfil de
  radio máximo mayor, y los postes de los otros dos seguidores están a una
  distancia fija. Una frase larga puede hacer que la leva roce el poste de al
  lado, y eso no lo dice ninguna envolvente de C3.
- **El rodillo se puede salir de su leva.** Si el perfil encoge por debajo de
  donde el seguidor lo busca, el rodillo cae al vacío y la máquina se para.

Y dos que no: la altura de la pila y la inercia del árbol, que salen de la
geometría y alimentan C6 y C7.

**Por qué no hay aquí un modelo 3-D.** Todas las piezas son prismas rectos de
plancha, así que su masa y su momento polar salen exactos del polígono —eso
está en `core/solido.py`— y las interferencias que importan ocurren en el
plano: los postes son columnas verticales que atraviesan todos los planos, de
modo que el choque de un brazo con un poste es un problema de dos
dimensiones. Un kernel de CAD no daría un número mejor; daría el mismo con
una dependencia de trescientos megas. Hará falta cuando exista bastidor.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from pydantic import BaseModel, ConfigDict

from compile.escribiente import SEGUIDORES, Compilacion, Escribiente
from core.solido import densidad_de, descontar_taladro, inercia_de_prisma, masa_de_prisma
from core.units import KgM2, Kilogramos, Longitud, Metros, a_mm, mm
from core.verdict import Incidencia, Veredicto
from emit.pieza import Pieza


class Cartucho(BaseModel):
    """Lo que rodea a las levas y no depende del pedido."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    radio_poste: Longitud = mm(8.0)
    """Los postes de los seguidores. Atraviesan los tres planos, así que
    estorban a las tres levas."""
    radio_eje: Longitud = mm(5.0)
    holgura_minima: Longitud = mm(3.0)
    """Lo que tiene que sobrar entre dos piezas que no se tocan. Por debajo
    de esto, la tolerancia de corte y el alabeo del tablero se lo comen."""
    separador: Longitud = mm(2.0)
    """Entre leva y leva, para que no se rocen al girar."""
    altura_maxima: Longitud = mm(80.0)
    """Lo que puede medir la pila sin que el cartucho deje de ser
    transportable."""


@dataclass(frozen=True)
class Montaje:
    """Los números del conjunto ya montado."""

    altura_pila: Metros
    masa: Kilogramos
    inercia: KgM2
    """Momento de inercia de las tres levas respecto del árbol. Es lo que
    entra en ½·J·ω² y lo que decide cuánto volante hace falta."""
    radio_maximo: Metros
    holgura_al_poste: Metros
    """Lo que sobra entre la leva más grande y el poste más cercano de otro
    seguidor. Negativo significa que se tocan."""


def _postes(maquina: Escribiente) -> list[tuple[float, float]]:
    """Dónde cae el pivote de cada seguidor, visto desde el árbol.

    Es la misma colocación que usa `Escribiente.seguidor`: repartidos a
    partes iguales alrededor del eje para que los brazos no se estorben.
    """
    return [maquina.seguidor(i).pivote for i in range(len(SEGUIDORES))]


def _propiedades(pieza: Pieza, maquina: Escribiente) -> tuple[float, float]:
    """Masa y momento de inercia de una pieza respecto del árbol.

    Se descuentan **todos** sus taladros, no solo el del eje: el pasador de
    índice también quita material, y una leva con dos agujeros y un solo
    descuento pesa de más.
    """
    densidad = densidad_de(maquina.material_leva)
    contorno = np.asarray(pieza.contorno, dtype=np.float64)
    masa = float(masa_de_prisma(contorno, maquina.espesor_leva, densidad))
    inercia = float(inercia_de_prisma(contorno, maquina.espesor_leva, densidad))
    for taladro in pieza.taladros:
        superficie, polar = descontar_taladro(contorno, taladro.centro, taladro.diametro)
        masa -= superficie * float(maquina.espesor_leva) * densidad
        inercia -= polar * float(maquina.espesor_leva) * densidad
    return masa, inercia


def montar(
    compilacion: Compilacion,
    maquina: Escribiente,
    cartucho: Cartucho | None = None,
) -> tuple[Montaje, Veredicto]:
    """Comprueba el conjunto y devuelve sus números.

    El veredicto se suma al de la compilación; aquí no se decide nada sobre
    las levas por separado, que ya tienen quien las juzgue.
    """
    cartucho = cartucho or Cartucho()
    if not compilacion.perfiles:
        raise ValueError("no hay levas que montar: la compilación no llegó a sintetizarlas")

    incidencias: list[Incidencia] = []
    postes = _postes(maquina)

    masa_total = 0.0
    inercia_total = 0.0
    radio_maximo = 0.0
    holgura_minima = np.inf

    for indice, nombre in enumerate(SEGUIDORES):
        perfil = compilacion.perfiles[nombre]
        masa, inercia = _propiedades(compilacion.piezas[indice], maquina)
        masa_total += masa
        inercia_total += inercia
        radio_maximo = max(radio_maximo, perfil.radio_maximo)

        # La leva de un seguidor gira bajo los postes de los otros dos.
        for otro, poste in enumerate(postes):
            if otro == indice:
                continue
            distancia = float(np.hypot(*poste))
            holgura = distancia - float(cartucho.radio_poste) - perfil.radio_maximo
            holgura_minima = min(holgura_minima, holgura)
            if holgura < 0.0:
                incidencias.append(
                    Incidencia(
                        gravedad="error",
                        codigo="leva_contra_poste",
                        mensaje=(
                            f"la leva {nombre} llega a {perfil.radio_maximo * 1000:.1f} mm de "
                            f"radio y el poste del seguidor {SEGUIDORES[otro]} está a "
                            f"{distancia * 1000:.1f} mm: se tocan"
                        ),
                        sugerencia=(
                            "acorta la frase, sube la relación del varillaje o separa los "
                            "postes del árbol"
                        ),
                    )
                )
            elif holgura < float(cartucho.holgura_minima):
                incidencias.append(
                    Incidencia(
                        gravedad="aviso",
                        codigo="poco_hueco_al_poste",
                        mensaje=(
                            f"entre la leva {nombre} y el poste de {SEGUIDORES[otro]} quedan "
                            f"{holgura * 1000:.1f} mm"
                        ),
                        sugerencia="por debajo de eso, la tolerancia de corte se lo come",
                    )
                )

        if perfil.radio_minimo <= float(cartucho.radio_eje) + float(cartucho.holgura_minima):
            incidencias.append(
                Incidencia(
                    gravedad="error",
                    codigo="leva_come_el_eje",
                    mensaje=(
                        f"la leva {nombre} baja a {perfil.radio_minimo * 1000:.1f} mm de radio "
                        f"y el eje mide {a_mm(cartucho.radio_eje) * 2:.0f} mm de diámetro"
                    ),
                    sugerencia="sube el radio base o baja el barrido del seguidor",
                )
            )

    altura = len(SEGUIDORES) * float(maquina.espesor_leva) + (len(SEGUIDORES) - 1) * float(
        cartucho.separador
    )
    if altura > float(cartucho.altura_maxima):
        incidencias.append(
            Incidencia(
                gravedad="aviso",
                codigo="pila_alta",
                mensaje=f"el cartucho mide {altura * 1000:.0f} mm de alto",
                sugerencia="levas más finas, o menos separación entre ellas",
            )
        )

    montaje = Montaje(
        altura_pila=Metros(altura),
        masa=Kilogramos(masa_total),
        inercia=KgM2(inercia_total),
        radio_maximo=Metros(radio_maximo),
        holgura_al_poste=Metros(float(holgura_minima)),
    )
    veredicto = Veredicto(
        incidencias=tuple(incidencias),
        metricas={
            "altura_pila": altura,
            "masa_cartucho": masa_total,
            "inercia_cartucho": inercia_total,
            "radio_maximo_leva": radio_maximo,
            "holgura_al_poste": float(holgura_minima),
        },
    )
    return montaje, veredicto


__all__ = ["Cartucho", "Montaje", "montar"]
