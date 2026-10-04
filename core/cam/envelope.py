"""C3 · La envolvente geométrica: ¿se puede fabricar esta leva?

Tres comprobaciones, todas evaluadas en cada grado del ciclo contra un límite.
Es el patrón que se repetirá en todas las clases de máquina: cambia la física,
no la forma del cálculo.

**Ángulo de presión.** El ángulo entre la fuerza que la leva transmite —que va
por la normal común— y la dirección en que el rodillo se mueve. Cuanto mayor,
más fuerza se pierde empujando de lado y más riesgo de que el seguidor se
atasque. Norton admite hasta unos ±30° con seguidor de traslación y unos ±35°
con seguidor oscilante; aquí el límite por defecto es 30°, más prudente porque
las holguras de madera y plástico se comen el margen.

**Radio de curvatura.** Si la curva de paso se cierra más de lo que mide el
rodillo, el perfil desplazado se cruza consigo mismo: es el *undercutting*, y
la pieza no existe. La regla habitual pide que el radio mínimo sea entre dos y
tres veces el del rodillo.

**Autointersección.** La comprobación definitiva, hecha sobre el perfil ya
calculado. La curvatura dice *dónde* y *por qué*; esto dice *sí o no*.

Los valores de `metricas` van en SI, como todo el núcleo. Los mensajes son
prosa para una persona y usan grados y milímetros: obligar al SI dentro de una
frase solo la haría peor.
"""

from __future__ import annotations

from dataclasses import replace

import numpy as np
import numpy.typing as npt
from pydantic import BaseModel, ConfigDict, Field
from shapely.geometry import LinearRing, Point

from core.cam.curves import derivada_ciclica, orientacion
from core.cam.synth import PerfilLeva
from core.units import TAU, Longitud, Radianes, a_grados, a_mm, grados
from core.verdict import Incidencia, Veredicto

Arreglo = npt.NDArray[np.float64]


class LimitesLeva(BaseModel):
    """Dónde está la frontera. Es el «juez enchufable» de esta clase de máquina."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    angulo_presion_max: Radianes = grados(30.0)
    ratio_curvatura_aviso: float = Field(default=2.5, gt=1.0)
    """Por debajo de este múltiplo del radio del rodillo, aviso."""
    radio_leva_max: Longitud | None = None
    """Lo que cabe en el cartucho. `None` mientras el contrato no esté fijado."""


def angulo_de_presion(perfil: PerfilLeva) -> Arreglo:
    """El ángulo entre la normal de contacto y el movimiento del rodillo.

    En un reposo el rodillo no se mueve y el ángulo no está definido: no hace
    falta fuerza para no moverse, así que se toma cero.
    """
    seguidor = perfil.seguidor
    angulo_brazo = seguidor.psi_cero + perfil.psi

    # El centro del rodillo describe un arco: su velocidad es perpendicular al
    # brazo, con el signo y la magnitud de ψ'.
    velocidad = (
        seguidor.brazo
        * perfil.psi_prima[:, None]
        * np.column_stack((-np.sin(angulo_brazo), np.cos(angulo_brazo)))
    )
    rapidez = np.linalg.norm(velocidad, axis=1)
    en_reposo = rapidez < 1e-12
    direccion = np.divide(
        velocidad,
        np.where(en_reposo, 1.0, rapidez)[:, None],
        dtype=np.float64,
    )

    # La normal se calcula en el marco de la leva; hay que llevarla al fijo.
    coseno = np.cos(perfil.thetas)
    seno = np.sin(perfil.thetas)
    normal_fija = np.column_stack(
        (
            coseno * perfil.normales[:, 0] - seno * perfil.normales[:, 1],
            seno * perfil.normales[:, 0] + coseno * perfil.normales[:, 1],
        )
    )

    coseno_angulo = np.abs(np.sum(normal_fija * direccion, axis=1))
    angulos = np.arccos(np.clip(coseno_angulo, 0.0, 1.0))
    return np.asarray(np.where(en_reposo, 0.0, angulos), dtype=np.float64)


def radio_de_curvatura(perfil: PerfilLeva) -> Arreglo:
    """Radio de curvatura con signo de convexidad, sobre la curva de paso.

    Positivo donde la curva es convexa hacia fuera, que es donde el
    desplazamiento hacia dentro puede cruzarse. Negativo en los valles, donde
    el desplazamiento nunca da problemas. Infinito en los tramos rectos.
    """
    paso = TAU / len(perfil)
    primera = derivada_ciclica(perfil.paso, paso)
    segunda = derivada_ciclica(primera, paso)
    numerador = primera[:, 0] * segunda[:, 1] - primera[:, 1] * segunda[:, 0]
    denominador = np.linalg.norm(primera, axis=1) ** 3
    curvatura = orientacion(perfil.paso) * np.divide(
        numerador,
        np.where(denominador < 1e-18, 1.0, denominador),
        dtype=np.float64,
    )
    with np.errstate(divide="ignore"):
        return np.asarray(
            np.where(np.abs(curvatura) < 1e-12, np.inf, 1.0 / curvatura),
            dtype=np.float64,
        )


def autointerseca(perfil: PerfilLeva) -> bool:
    """La comprobación definitiva: ¿el perfil se cruza consigo mismo?"""
    anillo = LinearRing(np.vstack((perfil.perfil, perfil.perfil[:1])))
    return not bool(anillo.is_simple)


def _area_con_signo(puntos: Arreglo) -> float:
    x, y = puntos[:, 0], puntos[:, 1]
    return 0.5 * float(np.sum(x * np.roll(y, -1) - np.roll(x, -1) * y))


INTERFERENCIA_TOLERADA = 1e-5
"""Metros. Un punto del perfil que queda a menos del radio del rodillo de la
curva de paso, por más de esto, es un punto que el rodillo atravesaría. Diez
micras: por debajo, la cuerda del polígono de la curva de paso ya se acerca
al perfil más que eso en las curvas cerradas, y no es interferencia."""


def envolvente(perfil: PerfilLeva) -> Arreglo:
    """El contorno que de verdad se corta cuando el perfil se cruza.

    Un perfil socavado no es una pieza: es un contorno con lazos donde el
    radio de curvatura no llega al del rodillo. La pieza que sí existe es la
    que deja el propio rodillo al recorrer la curva de paso: **el interior de
    la curva de paso erosionado en el radio del rodillo**. Su borde no tiene
    lazos, y en ese tramo el rodillo no sigue la curva de paso: la redondea,
    como una pluma redondea la punta de una vuelta. **Cuánto la redondea es
    una medida, no un juicio**, y se hace en el papel (`compile`).

    Devuelve los mismos N puntos y en el mismo orden, porque todo
    `PerfilLeva` vive en la misma rejilla de θ. Solo se mueven los puntos
    que el rodillo atravesaría —los del lazo y sus vecinos—, repartidos por
    el borde erosionado entre los dos puntos sanos que los rodean. Un perfil
    sano sale tal cual.
    """
    from shapely.geometry import LineString, Polygon

    puntos = np.asarray(perfil.perfil, dtype=np.float64)
    if LinearRing(np.vstack((puntos, puntos[:1]))).is_simple:
        return puntos

    radio = float(perfil.seguidor.radio_rodillo)
    paso = LinearRing(np.vstack((perfil.paso, perfil.paso[:1])))
    malos = np.array(
        [paso.distance(Point(x, y)) < radio - INTERFERENCIA_TOLERADA for x, y in puntos]
    )
    if not malos.any() or malos.all():
        return puntos

    region = Polygon(perfil.paso).buffer(-radio, quad_segs=64)
    trozos = [region] if region.geom_type == "Polygon" else list(getattr(region, "geoms", []))
    mayor = max(trozos, key=lambda g: g.area)
    borde = np.asarray(mayor.exterior.coords, dtype=np.float64)[:-1]
    if np.sign(_area_con_signo(borde)) != np.sign(_area_con_signo(puntos)):
        borde = borde[::-1]
    contorno = LineString(np.vstack((borde, borde[:1])))
    largo = float(contorno.length)

    salida = puntos.copy()
    n = len(puntos)
    # Se empieza en un punto sano para que ningún tramo malo quede partido.
    inicio = int(np.flatnonzero(~malos)[0])
    k = 0
    while k < n:
        i = (inicio + k) % n
        if not malos[i]:
            k += 1
            continue
        tramo = []
        while k < n and malos[(inicio + k) % n]:
            tramo.append((inicio + k) % n)
            k += 1
        antes, despues = puntos[(tramo[0] - 1) % n], puntos[(tramo[-1] + 1) % n]
        sa = contorno.project(Point(*antes))
        sb = contorno.project(Point(*despues))
        if sb <= sa:
            sb += largo
        for m, indice in enumerate(tramo, start=1):
            q = contorno.interpolate(float((sa + (sb - sa) * m / (len(tramo) + 1)) % largo))
            salida[indice] = (q.x, q.y)
    if LinearRing(np.vstack((salida, salida[:1]))).is_simple:
        return salida

    # Quedan lazos de interferencia menor que la tolerada: los que deja un
    # muestreo fino en las vueltas más cerradas de la letra. Proyectar punto a
    # punto no vale ahí —junto a un cuello estrecho un punto cae en la otra
    # orilla y desordena todo lo que viene detrás—, así que se toma el borde
    # erosionado entero, que es simple por construcción, en N puntos a paso
    # constante desde el primero. Lo que viene después del recorte solo usa
    # el polígono —el contacto, el DXF, el radio máximo—, no su rejilla.
    s0 = contorno.project(Point(*puntos[0]))
    for i in range(n):
        q = contorno.interpolate(float((s0 + largo * i / n) % largo))
        salida[i] = (q.x, q.y)
    return salida


def recortar(perfil: PerfilLeva) -> PerfilLeva:
    """El mismo perfil con su contorno cambiado por la envolvente que se corta."""
    return replace(perfil, perfil=envolvente(perfil))


def evaluar(perfil: PerfilLeva, limites: LimitesLeva | None = None) -> Veredicto:
    """Pasa un perfil por su envolvente y devuelve el veredicto.

    Que falle es un resultado legítimo, no una excepción: quien lo recibe
    necesita saber qué pasa, dónde y qué puede cambiar.
    """
    limites = limites or LimitesLeva()
    radio_rodillo = perfil.seguidor.radio_rodillo

    presion = angulo_de_presion(perfil)
    indice_presion = int(np.argmax(presion))
    presion_max = float(presion[indice_presion])

    curvatura = radio_de_curvatura(perfil)
    convexo = curvatura > 0.0
    if bool(convexo.any()):
        radios_convexos = np.where(convexo, curvatura, np.inf)
        indice_curvatura = int(np.argmin(radios_convexos))
        curvatura_min = float(radios_convexos[indice_curvatura])
    else:
        indice_curvatura = 0
        curvatura_min = float("inf")
    ratio = curvatura_min / radio_rodillo

    cruzado = autointerseca(perfil)

    incidencias: list[Incidencia] = []

    if presion_max > float(limites.angulo_presion_max):
        incidencias.append(
            Incidencia(
                gravedad="error",
                codigo="angulo_presion_excedido",
                mensaje=(
                    f"El ángulo de presión llega a {a_grados(Radianes(presion_max)):.1f}°, "
                    f"por encima del límite de "
                    f"{a_grados(limites.angulo_presion_max):.0f}°. El seguidor puede "
                    f"atascarse."
                ),
                theta=perfil.thetas[indice_presion],
                sugerencia=(
                    "Agranda el círculo base, acorta el brazo del seguidor o "
                    "reparte más grados de leva en ese tramo."
                ),
            )
        )

    if cruzado:
        incidencias.append(
            Incidencia(
                gravedad="error",
                codigo="perfil_autointersecado",
                mensaje=(
                    "El perfil se cruza consigo mismo: con este rodillo la pieza "
                    "no existe. Es undercutting."
                ),
                theta=perfil.thetas[indice_curvatura],
                sugerencia=(
                    f"Usa un rodillo menor de "
                    f"{a_mm(Longitud(max(curvatura_min, 0.0))):.1f} mm o suaviza "
                    f"la trayectoria en ese tramo."
                ),
            )
        )
    elif curvatura_min <= radio_rodillo:
        incidencias.append(
            Incidencia(
                gravedad="error",
                codigo="curvatura_menor_que_rodillo",
                mensaje=(
                    f"El radio de curvatura baja a "
                    f"{a_mm(Longitud(curvatura_min)):.1f} mm, por debajo del rodillo "
                    f"de {a_mm(Longitud(radio_rodillo)):.1f} mm."
                ),
                theta=perfil.thetas[indice_curvatura],
                sugerencia="Usa un rodillo menor o suaviza la trayectoria.",
            )
        )
    elif ratio < limites.ratio_curvatura_aviso:
        incidencias.append(
            Incidencia(
                gravedad="aviso",
                codigo="curvatura_justa",
                mensaje=(
                    f"El radio de curvatura mínimo es {ratio:.1f} veces el del "
                    f"rodillo. Lo recomendable son {limites.ratio_curvatura_aviso:.1f}."
                ),
                theta=perfil.thetas[indice_curvatura],
                sugerencia="Funcionará, pero con poco margen ante el desgaste.",
            )
        )

    if limites.radio_leva_max is not None and perfil.radio_maximo > float(limites.radio_leva_max):
        incidencias.append(
            Incidencia(
                gravedad="error",
                codigo="leva_demasiado_grande",
                mensaje=(
                    f"La leva mide {a_mm(Longitud(perfil.radio_maximo)):.1f} mm de "
                    f"radio y el cartucho admite "
                    f"{a_mm(limites.radio_leva_max):.1f} mm."
                ),
                sugerencia="Acorta la frase o reduce la escala de la escritura.",
            )
        )

    return Veredicto(
        incidencias=tuple(incidencias),
        metricas={
            "angulo_presion_max": presion_max,
            "theta_angulo_presion_max": float(perfil.thetas[indice_presion]),
            "radio_curvatura_min": curvatura_min,
            "ratio_curvatura": ratio,
            "radio_leva_max": perfil.radio_maximo,
            "radio_leva_min": perfil.radio_minimo,
        },
    )
