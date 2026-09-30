"""El compilador del escribiente: de una frase a tres levas y su veredicto.

Aquí se encadena lo que el núcleo ya sabe hacer por separado, en el orden que
manda `CLAUDE.md`:

    captura -> front-end -> C1 -> C2 -> C3 -> simulación -> piezas

Esta capa **decide**. Puede leer y escribir, elige la geometría concreta de la
máquina y traduce lo que el núcleo devuelve a un veredicto único que se le
puede enseñar a alguien. El núcleo sigue sin saber que existe un archivo.

Una regla que se nota en todo el módulo: **nada de esto lanza excepciones por
un resultado físico**. Que la frase no quepa, que el brazo no llegue o que el
ángulo de presión se pase son veredictos con motivo y sugerencia. Solo es
excepción lo que no tiene sentido pedir: una ficha mal cableada, un actuador
que no existe.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import numpy.typing as npt
from pydantic import BaseModel, ConfigDict, Field

from core.actors.cinco_barras import BrazoCincoBarras
from core.actors.palanca import PalancaElevadora
from core.cam.contacto import psi_por_contacto
from core.cam.curves import desde_muestras
from core.cam.envelope import LimitesLeva, evaluar, radio_de_curvatura
from core.cam.synth import PerfilLeva, Seguidor, sintetizar
from core.escritura import (
    CANAL_X,
    CANAL_Y,
    CANAL_Z,
    Capacidad,
    Escritura,
    Tramo,
    Trazo,
    encajar,
    programa,
    remuestrear,
    repartir,
    suavizar,
)
from core.program import Programa
from core.units import Longitud, Metros, Radianes, a_mm, mm
from core.verdict import Incidencia, Veredicto
from emit.pieza import Pieza, Polilinea, Taladro, Veta

Arreglo = npt.NDArray[np.float64]

SEGUIDORES = ("izquierdo", "derecho", "elevador")
"""Una leva por seguidor, en el orden en que se apilan en el eje."""

ERROR_DE_TRAZO_MAXIMO = 0.0005
"""Medio milímetro. Por encima de eso, la letra deja de parecerse."""

MUESTRAS_DE_CONTACTO = 24
"""Ángulos repartidos por el ciclo en los que se apoya el rodillo. Son pocos
porque cada uno cuesta, y para lo que sirven bastan: un error de signo o un
desplazamiento del revés se ve en cualquier ángulo, no hay que buscarlo."""

MUESTRAS_EN_LA_CURVA_CERRADA = 12
"""Y estos, apretados donde el radio de curvatura es mínimo. Ahí es donde un
rodillo demasiado grande socava el perfil, y el socavado es local: con
muestreo uniforme se pasa entre dos ángulos sin que nadie lo vea."""

ERROR_DE_CONTACTO_AVISO = 1e-3
ERROR_DE_CONTACTO_GRAVE = 1e-2
"""Radianes de desviación entre el ψ sintetizado y el que sale de apoyar el
rodillo en el perfil. Un décimo de grado ya no es discretización: o el
desplazamiento por radio de rodillo está mal, o la pieza está socavada."""


class Escribiente(BaseModel):
    """La geometría de la máquina. Todo en metros, como manda la regla 3.

    Los valores por defecto son los del primer prototipo: un brazo de cinco
    barras con los dos pivotes anclados al bastidor y las tres levas apiladas
    en el eje vertical.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    # -- brazo de cinco barras ----------------------------------------------
    separacion: Longitud = mm(120.0)
    proximal: Longitud = mm(90.0)
    distal: Longitud = mm(110.0)

    # -- palanca del lápiz ---------------------------------------------------
    brazo_palanca: Longitud = mm(40.0)

    # -- dónde se escribe ----------------------------------------------------
    caja_ancho: Longitud = mm(80.0)
    caja_alto: Longitud = mm(30.0)
    caja_centro_y: Longitud = mm(100.0)
    """Altura del centro del papel sobre la línea de los dos pivotes."""

    # -- las levas -----------------------------------------------------------
    radio_base: Longitud = mm(55.0)
    brazo_seguidor: Longitud = mm(45.0)
    radio_rodillo: Longitud = mm(3.0)
    """Ø6 mm: el exterior de un **MR63 (3×6×2,5)**, que es un rodamiento
    miniatura corriente y barato. Antes eran 2 mm, un diámetro para el que no
    existe rodamiento decente y que obligaba a un pasador rozando."""
    relacion: float = Field(default=6.0, ge=1.0, le=10.0)
    """Cuánto amplifica el varillaje entre seguidor y brazo.

    Con relación 1 el seguidor gira lo mismo que el brazo, y para que el
    ángulo de presión no pase de 30° con un barrido de 26° hace falta un
    radio base de 110 mm: levas de 240 mm de diámetro, tres apiladas. Con una
    relación de 3 el seguidor barre un tercio y la leva baja a 90 mm de
    diámetro.

    No es gratis: el varillaje amplifica por el mismo factor el error del
    perfil, el juego de los rodamientos y el desgaste. Es la cadena de
    tolerancias de C4, y es la que decide hasta dónde se puede subir."""
    taladro_eje: Longitud = mm(10.0)
    pasador_indice: Longitud = mm(3.0)
    radio_del_pasador: Longitud = mm(18.0)
    """El taladro del eje centra la leva pero no la orienta: un agujero
    redondo la deja girar a cualquier ángulo, y una leva calada donde no toca
    escribe basura. Con un segundo taladro fuera del centro solo hay **una**
    forma de montarla. Contrato de fase, `docs/contratos.md`."""
    espesor_leva: Longitud = mm(5.0)
    material_leva: str = Field(default="POM 5 mm", min_length=1)

    @property
    def brazo(self) -> BrazoCincoBarras:
        return BrazoCincoBarras(
            separacion=float(self.separacion),
            proximal=float(self.proximal),
            distal=float(self.distal),
        )

    @property
    def palanca(self) -> PalancaElevadora:
        return PalancaElevadora(brazo=float(self.brazo_palanca))

    def calajes(self, altura_levantamiento: Longitud) -> dict[str, float]:
        """A qué ángulo se cala cada brazo sobre el eje de su seguidor.

        **Es una constante de la máquina, no un resultado del pedido**, y eso
        es lo que permite que el brazo sea pieza de stock: se cala una vez,
        en el diseño, y se monta igual en todas las unidades.

        La referencia es el **centro de la caja de escritura** para los dos
        brazos, y **media altura de levantamiento** para la palanca. No es
        arbitraria: es donde la punta pasa más tiempo, así que el barrido del
        seguidor queda repartido a los dos lados.

        Antes se calculaba como la media de los ángulos a lo largo del ciclo,
        que minimiza el barrido de la leva. Minimizaba bien —la leva salía lo
        más pequeña posible— pero la media depende de por dónde escriba el
        cliente: se movía 3,3° entre frases, y sobre 90 mm de brazo proximal
        eso son 5 mm de trazo desplazado si el brazo se monta al calaje de
        otra. Con la referencia fija la leva crece unas décimas de milímetro
        y el brazo vuelve a ser pieza de catálogo. Es un cambio barato a
        favor de lo que el producto necesita.

        Contrato de calaje, `docs/contratos.md`.
        """
        centro = np.array([[0.0, float(self.caja_centro_y)]], dtype=np.float64)
        psi = self.brazo.inversa(centro)
        media = np.array([[float(altura_levantamiento) / 2.0]], dtype=np.float64)
        elevador = self.palanca.inversa(media)
        return {
            "izquierdo": float(psi[0, 0]),
            "derecho": float(psi[0, 1]),
            "elevador": float(elevador[0, 0]),
        }

    def seguidor(self, indice: int) -> Seguidor:
        """El seguidor de cada leva.

        Los tres pivotes van repartidos alrededor del eje para que los brazos
        no se estorben. `bien_puesto` los coloca con el brazo perpendicular al
        radio, que es donde el ángulo de presión arranca en cero.
        """
        return Seguidor.bien_puesto(
            radio_base=float(self.radio_base),
            brazo=float(self.brazo_seguidor),
            radio_rodillo=float(self.radio_rodillo),
            orientacion_pivote=indice * 2.0 * np.pi / len(SEGUIDORES),
        )


@dataclass(frozen=True)
class Simulacion:
    """El resultado de recorrer las levas ya sintetizadas.

    **Qué comprueba**: que la cadena entera —reparto de θ, cinemática inversa,
    muestreo de la leva, interpolación entre muestras y cinemática directa—
    devuelve la letra que entró. Caza ramas cambiadas, geometría equivocada y
    un reparto de grados demasiado grueso.

    **Qué no comprueba**: el desplazamiento por el radio del rodillo y el
    socavado, que son cosa de la envolvente (C3), y el kerf, que es de E4. La
    simulación lee la curva de paso, que es por donde va el centro del
    rodillo, no el filo del corte.
    """

    thetas: Arreglo
    puntos: Arreglo
    """Dónde pasa la punta en cada θ, (M, 2)."""
    altura: Arreglo
    """Cuánto está levantada, (M,)."""
    error_maximo: float
    error_medio: float

    @property
    def escritos(self) -> Arreglo:
        """Solo los puntos con el lápiz apoyado: lo que queda en el papel."""
        return np.asarray(self.puntos[self.altura <= 1e-9], dtype=np.float64)


@dataclass(frozen=True)
class Compilacion:
    """Todo lo que sale de compilar un pedido."""

    escritura: Escritura
    """Ya encajada en la caja de escritura, que es lo que se fabrica."""
    programa: Programa
    tramos: list[Tramo]
    perfiles: dict[str, PerfilLeva]
    calajes: dict[str, float]
    """Ángulo al que va calado cada brazo sobre su seguidor, en radianes.

    El seguidor oscila alrededor de su punto de diseño, donde el brazo queda
    perpendicular al radio base. El brazo de la máquina, en cambio, trabaja
    donde le toca: el derecho ronda los -177°. La leva sintetiza la
    **desviación** y el calaje es la diferencia, que se marca en el montaje.
    Sin esto la leva se diseñaría para un ángulo de presión que no es el que
    va a tener."""
    piezas: list[Pieza]
    simulacion: Simulacion | None
    veredicto: Veredicto


# ---------------------------------------------------------------------------
# Encajar en la caja de escritura
# ---------------------------------------------------------------------------


def encajar_en_la_caja(escritura: Escritura, maquina: Escribiente) -> Escritura:
    """Normaliza la frase y la sube al papel.

    `encajar` centra en una caja que empieza en el origen; el papel está a
    `caja_centro_y` por encima de los pivotes, así que hay que subirla.
    """
    encajada = encajar(escritura, ancho=maquina.caja_ancho, alto=maquina.caja_alto)
    dx = -float(maquina.caja_ancho) / 2.0
    dy = float(maquina.caja_centro_y) - float(maquina.caja_alto) / 2.0

    return Escritura(
        nombre=encajada.nombre,
        trazos=[
            Trazo(puntos=[(Metros(float(x) + dx), Metros(float(y) + dy)) for x, y in t.puntos])
            for t in encajada.trazos
        ],
    )


# ---------------------------------------------------------------------------
# Simulación inversa
# ---------------------------------------------------------------------------


def _psi_desde_la_leva(
    perfil: PerfilLeva, thetas: Arreglo, calaje: float = 0.0, relacion: float = 1.0
) -> Arreglo:
    """Recupera el ángulo del seguidor leyendo la leva ya fabricada.

    La leva es una curva rígida. Girarla θ y ver dónde queda el centro del
    rodillo es deshacer la inversión cinemática:

        F(θ) = R(θ) · C(θ)          ψ = ang(F - pivote) - ψ₀

    `C` se interpola con el mismo spline periódico que el resto del núcleo, y
    ahí está la gracia: entre muestra y muestra la leva real tampoco tiene
    información, así que evaluar en ángulos intermedios es exactamente lo que
    hace el rodillo.
    """
    cx = desde_muestras(perfil.thetas, perfil.paso[:, 0], n=len(thetas))
    cy = desde_muestras(perfil.thetas, perfil.paso[:, 1], n=len(thetas))
    coseno, seno = np.cos(thetas), np.sin(thetas)
    fx = coseno * cx.valores - seno * cy.valores
    fy = seno * cx.valores + coseno * cy.valores
    pivote = perfil.seguidor.pivote
    return np.asarray(
        (np.unwrap(np.arctan2(fy - pivote[1], fx - pivote[0])) - perfil.seguidor.psi_cero)
        * relacion
        + calaje,
        dtype=np.float64,
    )


def simular(
    perfiles: dict[str, PerfilLeva],
    calajes: dict[str, float],
    maquina: Escribiente,
    escritura: Escritura,
    muestras: int,
) -> Simulacion:
    """Recorre las levas y mira qué escribe la máquina.

    Se evalúa en más ángulos de los que tiene la leva a propósito: si el
    reparto de grados fuera demasiado grueso, el spline se inventaría la forma
    entre muestras y el error saldría aquí.
    """
    thetas = np.linspace(0.0, 2.0 * np.pi, muestras, endpoint=False)
    psi = {
        nombre: _psi_desde_la_leva(perfiles[nombre], thetas, calajes[nombre], maquina.relacion)
        for nombre in SEGUIDORES
    }

    puntos = maquina.brazo.directa(np.column_stack([psi["izquierdo"], psi["derecho"]]))
    altura = maquina.palanca.directa(psi["elevador"][:, None])[:, 0]

    apoyados = puntos[altura <= 1e-9]
    if apoyados.size == 0:
        return Simulacion(thetas, puntos, altura, np.inf, np.inf)

    distancias = []
    for trazo in escritura.trazos:
        for punto in remuestrear(trazo, 64):
            distancias.append(float(np.min(np.linalg.norm(apoyados - punto, axis=1))))
    return Simulacion(
        thetas=thetas,
        puntos=np.asarray(puntos, dtype=np.float64),
        altura=np.asarray(altura, dtype=np.float64),
        error_maximo=max(distancias),
        error_medio=float(np.mean(distancias)),
    )


# ---------------------------------------------------------------------------
# Las piezas
# ---------------------------------------------------------------------------


def verificar_por_contacto(
    perfiles: dict[str, PerfilLeva],
    maquina: Escribiente,
    muestras: int = MUESTRAS_DE_CONTACTO,
) -> tuple[float, float, list[Incidencia]]:
    """Comprueba el perfil **cortado** apoyando el rodillo, sin usar la curva
    de paso ni las normales.

    La simulación del trazo deshace la síntesis con sus mismas fórmulas, así
    que un error **sistemático** —el desplazamiento por radio de rodillo del
    revés, un signo cambiado— se le escaparía: la ida y la vuelta
    coincidirían igual. Esto va por otro camino y por eso lo ve.

    Lo que **no** es: un detector de socavado. El socavado es local, pasa en
    un puñado de grados, y cazarlo por contacto exigiría muestrear todo el
    ciclo, que cuesta diez veces más de lo que este paso puede gastar. Quien
    rechaza un perfil socavado es la envolvente, que lo calcula exacto y
    gratis. Aquí se muestrea también alrededor de la curvatura mínima, y el
    número sube cuando hay socavado, pero el juez es C3.

    Devuelve la desviación en radianes del seguidor, su equivalente
    aproximado en la punta del lápiz, y las incidencias.
    """
    peor = 0.0
    incidencias: list[Incidencia] = []
    for nombre, perfil in perfiles.items():
        uniformes = np.linspace(0, len(perfil) - 1, muestras, dtype=int)
        critico = int(np.argmin(np.abs(radio_de_curvatura(perfil))))
        apretados = (
            critico
            + np.arange(-MUESTRAS_EN_LA_CURVA_CERRADA // 2, MUESTRAS_EN_LA_CURVA_CERRADA // 2)
        ) % len(perfil)
        indices = np.unique(np.concatenate([uniformes, apretados]))
        thetas = perfil.thetas[indices]
        desviacion = np.abs(
            psi_por_contacto(perfil.perfil, perfil.seguidor, thetas) - perfil.psi[indices]
        )
        maxima = float(np.max(desviacion))
        peor = max(peor, maxima)
        if maxima > ERROR_DE_CONTACTO_GRAVE:
            incidencias.append(
                Incidencia(
                    gravedad="error",
                    codigo="contacto_discrepante",
                    mensaje=(
                        f"leva {nombre}: apoyando el rodillo en el perfil cortado, el "
                        f"seguidor queda a {np.degrees(maxima):.2f}° de donde lo puso la "
                        "síntesis. La pieza que se cortaría no es la que se calculó"
                    ),
                    sugerencia="baja el radio del rodillo o sube el radio base",
                )
            )
        elif maxima > ERROR_DE_CONTACTO_AVISO:
            incidencias.append(
                Incidencia(
                    gravedad="aviso",
                    codigo="contacto_justo",
                    mensaje=(
                        f"leva {nombre}: el rodillo apoya a {np.degrees(maxima):.3f}° de lo "
                        "previsto, más de lo que explica el muestreo del perfil"
                    ),
                    sugerencia="sube las muestras por vuelta",
                )
            )
    # El varillaje amplifica: lo que el seguidor pierde llega a la punta
    # multiplicado por la relación y por el brazo proximal.
    en_la_punta = peor * maquina.relacion * float(maquina.proximal)
    return peor, en_la_punta, incidencias


def pieza_de_leva(
    perfil: PerfilLeva,
    nombre: str,
    numero: str,
    conjunto: str,
    maquina: Escribiente,
) -> Pieza:
    """El perfil, su taladro de eje, su pasador de índice y su marca de fase.

    **Una sola referencia de fase, y es física.** El taladro del eje centra la
    leva pero la deja girar; el pasador la orienta, y solo hay una manera de
    meter los dos. Va en el eje +X del marco de la leva, que es θ=0 del árbol
    maestro, **igual en las tres levas**: por eso las tres quedan caladas
    entre sí sin que nadie tenga que alinearlas.

    La marca grabada no es una segunda referencia: apunta al pasador. Dos
    referencias que puedan discrepar son peores que ninguna.
    """
    contorno = [(Metros(float(x)), Metros(float(y))) for x, y in perfil.perfil]
    radio_pasador = float(maquina.radio_del_pasador)

    # El punto del contorno que cae sobre +X. La marca sale de ahí hacia
    # dentro, hasta el pasador, para que se lean como una sola cosa.
    # Sin desenrollar: `arctan2` ya devuelve el ángulo en (-π, π], así que el
    # de módulo más pequeño es el que cae sobre +X. Desenrollarlo antes daría
    # el punto equivocado en cuanto el perfil no empiece cerca de ese eje.
    angulos = np.arctan2(perfil.perfil[:, 1], perfil.perfil[:, 0])
    fase = perfil.perfil[int(np.argmin(np.abs(angulos)))]

    return Pieza(
        nombre=nombre,
        numero=numero,
        conjunto=conjunto,
        material=maquina.material_leva,
        espesor=maquina.espesor_leva,
        cantidad=1,
        veta=Veta.INDIFERENTE,
        contorno=contorno,
        taladros=[
            Taladro(centro=(Metros(0.0), Metros(0.0)), diametro=maquina.taladro_eje),
            Taladro(
                centro=(Metros(radio_pasador), Metros(0.0)),
                diametro=maquina.pasador_indice,
            ),
        ],
        referencias=[
            Polilinea(
                puntos=[
                    (Metros(radio_pasador + float(maquina.pasador_indice)), Metros(0.0)),
                    (Metros(float(fase[0]) * 0.92), Metros(float(fase[1]) * 0.92)),
                ]
            )
        ],
        marca_fase=(Metros(float(fase[0])), Metros(float(fase[1]))),
    )


# ---------------------------------------------------------------------------
# El compilador
# ---------------------------------------------------------------------------


def compilar(
    escritura: Escritura,
    maquina: Escribiente | None = None,
    capacidad: Capacidad | None = None,
    limites: LimitesLeva | None = None,
) -> Compilacion:
    """De una frase a tres levas, con un solo veredicto al final."""
    maquina = maquina or Escribiente()
    capacidad = capacidad or Capacidad()
    limites = limites or LimitesLeva()

    # Redondear **después** de encajar: el radio es una longitud absoluta y
    # encajar escala la frase, así que al revés el redondeo valdría una cosa
    # distinta en cada pedido. Y antes de `programa`, porque lo que se
    # redondea es lo que se fabrica: `Compilacion.escritura` es la de verdad.
    encajada = suavizar(
        encajar_en_la_caja(escritura, maquina),
        capacidad.radio_de_esquina,
    )
    prog, veredicto = programa(encajada, capacidad)
    tramos, _ = repartir(encajada, capacidad)

    thetas = np.array(prog.pista(CANAL_X).thetas)  # type: ignore[union-attr]
    objetivo = np.column_stack(
        [
            np.array(prog.pista(CANAL_X).valores),  # type: ignore[union-attr]
            np.array(prog.pista(CANAL_Y).valores),  # type: ignore[union-attr]
        ]
    )
    altura = np.array(prog.pista(CANAL_Z).valores)[:, None]  # type: ignore[union-attr]

    fuera = ~maquina.brazo.alcanzable(objetivo)
    if bool(fuera.any()):
        # Es un límite de diseño, no geometría imposible: veredicto, no excepción.
        indice = int(np.argmax(fuera))
        x, y = objetivo[indice]
        return Compilacion(
            escritura=encajada,
            programa=prog,
            tramos=tramos,
            perfiles={},
            piezas=[],
            calajes={},
            simulacion=None,
            veredicto=veredicto.con(
                Incidencia(
                    gravedad="error",
                    codigo="fuera_de_alcance",
                    mensaje=(
                        f"la punta tendría que llegar a ({a_mm(Metros(x)):.1f}, "
                        f"{a_mm(Metros(y)):.1f}) mm y el brazo no da"
                    ),
                    theta=Radianes(float(thetas[indice])),
                    sugerencia="reduce la caja de escritura o alarga los eslabones",
                )
            ),
        )

    psi_brazo = maquina.brazo.inversa(objetivo)
    psi_palanca = maquina.palanca.inversa(altura)
    crudos = {
        "izquierdo": psi_brazo[:, 0],
        "derecho": psi_brazo[:, 1],
        "elevador": psi_palanca[:, 0],
    }
    # Cada leva se sintetiza para la **desviación** del seguidor respecto de
    # su punto de diseño, no para el ángulo absoluto del brazo. El resto es
    # el calaje: a qué ángulo se monta el brazo sobre el eje del seguidor.
    #
    # El calaje lo pone la máquina, no la frase. Si saliera de esta
    # compilación —por ejemplo como la media de los ángulos del ciclo— el
    # brazo habría que calarlo en cada pedido y dejaría de ser pieza de
    # stock. Ver `Escribiente.calajes`.
    calajes = maquina.calajes(capacidad.altura_levantamiento)
    crudos = {
        nombre: (valores - calajes[nombre]) / maquina.relacion for nombre, valores in crudos.items()
    }

    perfiles: dict[str, PerfilLeva] = {}
    for indice, nombre in enumerate(SEGUIDORES):
        funcion = desde_muestras(thetas, crudos[nombre], n=capacidad.muestras)
        perfil = sintetizar(funcion, maquina.seguidor(indice))
        perfiles[nombre] = perfil
        parcial = evaluar(perfil, limites)
        for incidencia in parcial.incidencias:
            veredicto = veredicto.con(
                incidencia.model_copy(update={"mensaje": f"leva {nombre}: {incidencia.mensaje}"})
            )
        veredicto = Veredicto(
            incidencias=veredicto.incidencias,
            metricas={
                **veredicto.metricas,
                **{f"{k}_{nombre}": v for k, v in parcial.metricas.items()},
            },
        )

    contacto, contacto_en_la_punta, incidencias_contacto = verificar_por_contacto(perfiles, maquina)
    for incidencia in incidencias_contacto:
        veredicto = veredicto.con(incidencia)

    simulacion = simular(perfiles, calajes, maquina, encajada, muestras=capacidad.muestras * 2)
    if simulacion.error_maximo > ERROR_DE_TRAZO_MAXIMO:
        veredicto = veredicto.con(
            Incidencia(
                gravedad="error",
                codigo="trazo_infiel",
                mensaje=(
                    f"al recorrer las levas la punta se desvía hasta "
                    f"{simulacion.error_maximo * 1000:.2f} mm de la escritura original"
                ),
                sugerencia="sube las muestras por vuelta o simplifica la frase",
            )
        )
    veredicto = Veredicto(
        incidencias=veredicto.incidencias,
        metricas={
            **veredicto.metricas,
            "error_trazo_maximo": simulacion.error_maximo,
            "error_trazo_medio": simulacion.error_medio,
            "error_contacto_rad": contacto,
            "error_contacto_en_la_punta": contacto_en_la_punta,
        },
    )

    piezas = [
        pieza_de_leva(
            perfiles[nombre],
            nombre=f"leva {nombre}",
            numero=f"L-{indice + 1:03d}",
            conjunto=f"cartucho {escritura.nombre}",
            maquina=maquina,
        )
        for indice, nombre in enumerate(SEGUIDORES)
    ]

    return Compilacion(
        escritura=encajada,
        programa=prog,
        tramos=tramos,
        perfiles=perfiles,
        calajes=calajes,
        piezas=piezas,
        simulacion=simulacion,
        veredicto=veredicto,
    )


__all__ = [
    "ERROR_DE_CONTACTO_AVISO",
    "ERROR_DE_CONTACTO_GRAVE",
    "ERROR_DE_TRAZO_MAXIMO",
    "MUESTRAS_DE_CONTACTO",
    "SEGUIDORES",
    "Compilacion",
    "Escribiente",
    "Simulacion",
    "compilar",
    "encajar_en_la_caja",
    "pieza_de_leva",
    "simular",
    "verificar_por_contacto",
]
