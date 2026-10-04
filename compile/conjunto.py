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

from collections.abc import Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

import numpy as np
from pydantic import BaseModel, ConfigDict

from compile.escribiente import (
    SEGUIDORES,
    Compilacion,
    Escribiente,
    _psi_desde_la_leva,
)
from core.solido import densidad_de, descontar_taladro, inercia_de_prisma, masa_de_prisma
from core.units import KgM2, Kilogramos, Longitud, Metros, a_mm, mm
from core.verdict import Incidencia, Veredicto

if TYPE_CHECKING:  # pragma: no cover
    from emit.montaje import Estado
from emit.pieza import Pieza


class Cartucho(BaseModel):
    """Lo que rodea a las levas y no depende del pedido."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    radio_poste: Longitud = mm(7.5)
    """El **obstáculo** que ve la leva al girar bajo el poste de otro
    seguidor, no el radio del poste.

    Es una distinción que costó una sorpresa: un poste necesita casquillo, y
    los casquillos con valona tienen la valona bastante mayor que el eje. Con
    postes de Ø16 y casquillo de bronce con valona de Ø28, el hueco caía de
    9,0 mm a 3,0 y saltaba el aviso.

    El valor por defecto es la valona del **igus GFM-0810**, que mide Ø15
    —no Ø12, como se anotó primero leyendo mal el catálogo— sobre un poste
    de Ø8. Da 9,5 mm de hueco. El Ø16 nunca estuvo justificado: con 0,7 N de
    fuerza tangencial, un poste de Ø8 sobra por dos órdenes de magnitud."""
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


# ---------------------------------------------------------------------------
# El barrido en tres dimensiones
# ---------------------------------------------------------------------------


def estados(compilacion: Compilacion, maquina: Escribiente, thetas: Any) -> list[Estado]:
    """La máquina en cada ángulo del árbol, leyendo las levas sintetizadas.

    **Hacen falta al menos ocho ángulos de golpe**, y no es un capricho de
    esta función: `_psi_desde_la_leva` reconstruye el spline de la curva de
    paso con tantos nudos como ángulos se le piden. Pedir uno solo no da la
    máquina en ese ángulo, da un error.

    Los dos números que salen de aquí son distintos y confundirlos es la
    trampa del calaje: la **desviación** del seguidor es para lo que se
    sintetiza la leva, y el **ángulo absoluto** del brazo lleva además la
    relación y el calaje. Se leen con la misma función y distintos
    argumentos, para que no puedan separarse al tocar una.
    """
    from compile.contratos import cargar
    from compile.levantamiento import bieleta_isogona, caida_de_la_mesa, giro_del_eje
    from emit.montaje import Estado

    contratos = cargar()
    bieleta = bieleta_isogona(contratos, maquina)
    thetas = np.asarray(thetas, dtype=np.float64)
    crudo = {n: _psi_desde_la_leva(compilacion.perfiles[n], thetas) for n in SEGUIDORES}
    brazo = {
        n: _psi_desde_la_leva(
            compilacion.perfiles[n], thetas, compilacion.calajes[n], maquina.relacion
        )
        for n in SEGUIDORES
    }
    return [
        Estado(
            theta=float(theta),
            desviaciones=(
                float(crudo["izquierdo"][i]),
                float(crudo["derecho"][i]),
                float(crudo["elevador"][i]),
            ),
            psi_izquierdo=float(brazo["izquierdo"][i]),
            psi_derecho=float(brazo["derecho"][i]),
            giro_balancin=giro,
            caida_mesa=caida_de_la_mesa(giro, contratos),
        )
        for i, theta in enumerate(thetas)
        for giro in (giro_del_eje(float(crudo["elevador"][i]), contratos, bieleta),)
    ]


def piezas_en(
    compilacion: Compilacion, maquina: Escribiente | None = None, theta: float = 0.0
) -> list[Any]:
    """Todas las piezas colocadas en 3D en el ángulo más cercano a `theta`.

    Se evalúa sobre una rejilla de un grado porque la máquina no se puede
    leer en un ángulo suelto (ver `estados`). Para mirarla en pantalla eso
    sobra; para barrer el ciclo está `barrer`, que no redondea nada.
    """
    from emit.montaje import colocar

    maquina = maquina or Escribiente()
    thetas = np.linspace(0.0, 2.0 * np.pi, 360, endpoint=False)
    indice = int(np.argmin(np.abs(np.angle(np.exp(1j * (thetas - theta))))))
    return colocar(
        list(compilacion.piezas),
        [maquina.seguidor(i) for i in range(len(SEGUIDORES))],
        estados(compilacion, maquina, thetas)[indice],
    )


@dataclass(frozen=True)
class Roce:
    """Lo más cerca que llegan dos piezas durante el barrido."""

    una: str
    otra: str
    holgura: float
    """En milímetros. Negativa si se solapan."""
    theta: float


def _separacion_de_cajas(una: Any, otra: Any) -> float:
    """Lo MENOS que pueden distar dos sólidos, por sus cajas envolventes.

    Es una cota inferior barata: si las cajas distan 40 mm, los sólidos
    distan al menos 40. Sirve para no pagar la distancia exacta —que es lo
    caro— en los pares que ni se acercan.
    """
    hueco = 0.0
    for eje in ("X", "Y", "Z"):
        a0, a1 = getattr(una.min, eje), getattr(una.max, eje)
        b0, b1 = getattr(otra.min, eje), getattr(otra.max, eje)
        hueco += max(b0 - a1, a0 - b1, 0.0) ** 2
    return float(np.sqrt(hueco))


def barrer(
    compilacion: Compilacion,
    maquina: Escribiente | None = None,
    pasos: int = 24,
    entre: Callable[[str, str], bool] | None = None,
    cerca: float = 25.0,
) -> list[Roce]:
    """Recorre el ciclo y mide lo que se acerca cada par de piezas.

    **Esto es lo que no hace nadie más.** `holguras()` mira en el plano y
    solo mira las levas contra los postes; Onshape tiene detección de
    interferencias pero es estática, hay que congelar θ y repetir a mano.
    Aquí es un bucle, y por tanto puede ser un test.

    Solo se miran los pares con **al menos una pieza móvil**: dos piezas
    quietas o se tocan siempre o no se tocan nunca, y eso ya lo dice un
    único montaje.

    `cerca` es **lo que importa**, en milímetros: un par cuyas cajas
    envolventes nunca se acercan tanto no aparece en el resultado. La
    distancia exacta entre dos sólidos de OCCT es lo caro de todo esto, y
    sin este filtro el barrido pasa de segundos a media hora —es decir, de
    un test que se ejecuta a uno que se desactiva—. Lo que sí aparece
    lleva su distancia **exacta**.

    Devuelve un `Roce` por par, ordenado de menos holgura a más, así que
    el primero es el que decide.
    """
    from emit.montaje import colocar, taller

    maquina = maquina or Escribiente()
    hecho = taller()
    seguidores = [maquina.seguidor(i) for i in range(len(SEGUIDORES))]
    levas = list(compilacion.piezas)
    thetas = np.linspace(0.0, 2.0 * np.pi, max(pasos, 8), endpoint=False)
    peor: dict[tuple[str, str], Roce] = {}
    for estado in estados(compilacion, maquina, thetas):
        theta = estado.theta
        piezas = colocar(levas, seguidores, estado, piezas_base=hecho)
        cajas = [p.solido.bounding_box() for p in piezas]
        for i, una in enumerate(piezas):
            for j, otra in enumerate(piezas[i + 1 :], start=i + 1):
                if not (una.movil or otra.movil):
                    continue
                if _separacion_de_cajas(cajas[i], cajas[j]) > cerca:
                    continue
                # El filtro se prueba en los dos sentidos: el orden del par
                # lo decide cómo se montó la lista, y quien filtra no tiene
                # por qué saberlo.
                if entre is not None and not (
                    entre(una.nombre, otra.nombre) or entre(otra.nombre, una.nombre)
                ):
                    continue
                clave = (una.nombre, otra.nombre)
                holgura = float(una.solido.distance_to(otra.solido))
                if clave not in peor or holgura < peor[clave].holgura:
                    peor[clave] = Roce(una.nombre, otra.nombre, holgura, float(theta))
    return sorted(peor.values(), key=lambda r: r.holgura)
