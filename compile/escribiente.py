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
from core.cam.envelope import LimitesLeva, autointerseca, evaluar, radio_de_curvatura, recortar
from core.cam.synth import PerfilLeva, Seguidor, sintetizar
from core.escritura import (
    CANAL_X,
    CANAL_Y,
    CANAL_Z,
    Capacidad,
    Escritura,
    Tramo,
    Trazo,
    desviacion_de_lo_capturado,
    encajar,
    programa,
    remuestrear,
    repartir,
    suavizar,
)
from core.program import Programa
from core.units import TAU, Longitud, Metros, Radianes, a_mm, grados, mm
from core.verdict import Incidencia, Veredicto
from emit.pieza import Pieza, Polilinea, Taladro, Veta

Arreglo = npt.NDArray[np.float64]

SEGUIDORES = ("izquierdo", "derecho", "elevador")
"""Una leva por seguidor. El orden es el de los postes —el seguidor `i` va
en el poste a `i × 120°`— y el de la numeración L-001…L-003; el de la pila
es otro, `ORDEN_EN_LA_PILA`."""

ORDEN_EN_LA_PILA = ("elevador", "derecho", "izquierdo")
"""De abajo arriba. **La pila es escalonada**: cada leva es más pequeña que
la de debajo, porque el eje del rodillo de una leva baja desde el plano de
los seguidores pasando junto a todas las que tiene encima. Con las tres del
mismo tamaño ese eje atravesaba las de arriba casi 2 mm. El elevador va
abajo y conserva su radio porque tiene el recorrido más corto y de él cuelga
toda la cadena del levantamiento."""

UMBRAL_DE_APOYO = 5e-5
"""Metros. Por debajo, el lápiz está apoyado: 0,05 mm frente a los 3 del
levantamiento. Era 1e-9, y el spline oscila hasta una micra en los arranques
de cada trazo: veinte puntos que escribían contaban como vuelo y dejaban
huecos en la tinta. De ahí salían los 0,144 mm de error de «hola», que son
2,8 µm con el lápiz donde está."""

ERROR_DE_TRAZO_MAXIMO = 0.0005
"""Medio milímetro. Por encima de eso, la letra deja de parecerse."""

SOCAVADO_TOLERABLE = 0.00025
"""Un cuarto de milímetro en el papel. Una leva en la que el rodillo no
entra en algún tramo se corta igual —su envolvente, `core.cam.envelope.
recortar`— y en ese tramo redondea la letra. Si lo que redondea no pasa de
esto, la leva vale: es la mitad del trazo de un portaminas de 0,5, y queda
por debajo de lo que se ve. Por encima, la letra pierde las puntas."""

PASO_POR_MUESTRA = 0.0005
"""Metros de trazo, como mucho, entre una muestra de la leva y la siguiente.
Con 720 muestras y una frase densa la punta avanzaba más de medio milímetro
por muestra: más que los detalles de la letra, que la leva no veía. El
veredicto salía aprobado sobre una versión filtrada de la frase sin decir
cuánto (docs/propuesta_dimensionado.md, fase 2)."""

MUESTRAS_POSIBLES = (720, 1440, 2880)
"""Las resoluciones entre las que elige `muestras_para`. Múltiplos de 720
para que medio grado siga siendo una muestra exacta."""


def muestras_para(escritura: Escritura, capacidad: Capacidad) -> int:
    """Las muestras por vuelta que pide esta frase: las menos de
    `MUESTRAS_POSIBLES` con las que la punta no avanza más de
    `PASO_POR_MUESTRA` entre muestra y muestra mientras escribe."""
    tramos, _ = repartir(escritura, capacidad)
    arco = sum(float(t.arco) for t in tramos if t.clase == "trazo")
    tinta = 0.0
    for t in escritura.trazos:
        puntos = np.asarray(t.puntos, dtype=np.float64)
        tinta += float(np.sum(np.linalg.norm(np.diff(puntos, axis=0), axis=1)))
    if arco <= 0.0:
        return MUESTRAS_POSIBLES[0]
    for muestras in MUESTRAS_POSIBLES:
        if tinta / (muestras * arco / TAU) <= PASO_POR_MUESTRA:
            return muestras
    return MUESTRAS_POSIBLES[-1]


NO_ENTRA_EL_RODILLO = frozenset({"perfil_autointersecado", "curvatura_menor_que_rodillo"})
"""Las incidencias de C3 que dicen que el rodillo no entra en algún tramo.
No se rechazan solas: decide el error en el papel de la leva recortada."""

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
    caja_alto: Longitud = mm(24.0)
    """Eran 30 hasta el 2026-10-05, y con 30 «hola» tecleada no se podía
    fabricar: la relación de curvatura de la leva derecha caía a **1,07** y
    el perfil se autointersecaba sin dejarse recortar. Con 24 queda en 2,13.

    No es un techo —el veredicto no es monótono con el tamaño: 85 × 33,7
    pasa donde 75,7 × 30 falla— sino el punto donde la curvatura deja de ir
    justa. El papel no se mueve: el A7 sigue siendo 105 × 74 y lo único que
    cambia es el margen, de 22 a 25 delante y detrás."""
    caja_centro_y: Longitud = mm(100.0)
    """Altura del centro del papel sobre la línea de los dos pivotes."""

    # -- las levas -----------------------------------------------------------
    radio_base: Longitud = mm(55.0)
    brazo_seguidor: Longitud = mm(45.0)
    """Estos dos sitúan los postes: el pivote va a `hypot(radio_base,
    brazo_seguidor)` del árbol. Son también el radio y el brazo de la leva de
    abajo de la pila, la del elevador."""
    brazos_de_canal: tuple[Longitud, Longitud, Longitud] = (mm(55.0), mm(50.0), mm(45.0))
    """El brazo de cada seguidor, en el orden de `SEGUIDORES`. Con el poste
    fijo, un brazo más largo da una leva más pequeña (`Seguidor.en_el_poste`):
    así se escalona la pila sin mover el bastidor. Son los tres agujeros de
    rodillo de UNA sola pieza de seguidor.

    Van de 5 en 5 y no de 7 en 7 (eran 59/52/45) porque la capacidad la pone
    la leva más pequeña: la de arriba, la del canal izquierdo, pasa de radio
    base 39,6 a 45,8 y la tinta por vuelta sube un 16 %. Menos escalón ya no
    deja los 3 mm entre el eje del rodillo y la leva de al lado."""
    sentidos: tuple[int, int, int] = (-1, 1, 1)
    """A qué lado del poste cae cada rodillo. El izquierdo va al revés para
    que ningún rodillo quede en el pasillo por el que sale el cartucho, entre
    los postes 1 y 2."""
    radio_eje_rodillo: Longitud = mm(2.0)
    """El casquillo de Ø4 que baja el rodillo desde el seguidor hasta su
    leva. Es lo que pasa junto a las levas de encima."""
    holgura_eje_rodillo: Longitud = mm(3.0)
    """Lo mínimo entre ese casquillo y una leva que gira a su lado: la
    `holgura_minima` del contrato de bastidor."""
    tope_seguidor: float = float(grados(4.0))
    """Radianes que puede girar cada seguidor hacia dentro desde su punto de
    diseño antes de tocar el pasador de tope: `tope_giro` del contrato."""
    margen_al_tope: float = float(grados(0.5))
    """Lo que tiene que sobrar hasta el tope girando con una frase: el error
    de orientar el collar a mano son unos ±0,3 mm por grado a 20 del poste."""
    radio_maximo_cartucho: Longitud = mm(55.5)
    """Lo más que puede medir de radio una leva para que el cartucho salga
    entre los dos postes traseros: `cartucho_radio_maximo`."""
    radio_rodillo: Longitud = mm(3.0)
    """Ø6 mm: el exterior de un **MR63 (3×6×2,5)**, que es un rodamiento
    miniatura corriente y barato. Antes eran 2 mm, un diámetro para el que no
    existe rodamiento decente y que obligaba a un pasador rozando."""
    relacion: float = Field(default=8.0, ge=1.0, le=10.0)
    """Cuánto amplifica el varillaje entre seguidor y brazo.

    Con relación 1 el seguidor gira lo mismo que el brazo, y para que el
    ángulo de presión no pase de 30° con un barrido de 26° hace falta un
    radio base de 110 mm: levas de 240 mm de diámetro, tres apiladas. Con una
    relación de 3 el seguidor barre un tercio y la leva baja a 90 mm de
    diámetro.

    No es gratis: el varillaje amplifica por el mismo factor el error del
    perfil, el juego de los rodamientos y el desgaste. Es la cadena de
    tolerancias de C4, y es la que decide hasta dónde se puede subir.

    Es 8 y no 6 para escribir varias palabras por vuelta: con los brazos
    55/50/45, de 220 a 314 mm de tinta, a cambio de 1,78 mm de peor caso en
    la punta en vez de 1,35. El cabestrante que la da es un sector de R56 y
    un tambor de R7 (`relacion_varillaje` en el contrato de bastidor).

    Es la de los dos canales del cinco barras. El elevador no pasa por el
    cabestrante: lleva la suya, `relacion_elevador`."""
    relacion_elevador: float = Field(default=6.0, ge=1.0, le=10.0)
    """La del canal del levantamiento, que amplifica el balancín y no el
    cabestrante. Se queda en 6 cuando el cabestrante pasa a 8: la leva del
    elevador es la grande de la pila y no es la que limita la capacidad, y
    tocarla obligaría a rehacer el balancín."""
    taladro_eje: Longitud = mm(10.0)
    pasador_indice: Longitud = mm(3.0)
    radio_del_pasador: Longitud = mm(18.0)
    """El taladro del eje centra la leva pero no la orienta: un agujero
    redondo la deja girar a cualquier ángulo, y una leva calada donde no toca
    escribe basura. Con un segundo taladro fuera del centro solo hay **una**
    forma de montarla. Contrato de fase, `docs/contratos.md`."""
    espesor_leva: Longitud = mm(5.0)
    ajuste_de_los_taladros: str = "H8"
    """El del contrato de fase: deslizante en el POM, así que el plano lo
    rotula en los dos taladros de cada leva."""
    tolerancia_de_perfil: str = "±0,02"
    """La que se pide al taller para el contorno de cada leva. La misma que
    `compile.tolerancias.Holguras.error_de_perfil`."""
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

    @property
    def distancia_al_poste(self) -> float:
        """Del árbol al pivote de cualquier seguidor: los tres postes."""
        return float(np.hypot(float(self.radio_base), float(self.brazo_seguidor)))

    def radio_base_de(self, indice: int) -> float:
        return Seguidor.radio_base_en_el_poste(
            self.distancia_al_poste, float(self.brazos_de_canal[indice])
        )

    def relacion_de(self, nombre: str) -> float:
        """La relación seguidor → salida del canal: el cabestrante en los dos
        del cinco barras, el balancín en el elevador."""
        return self.relacion_elevador if nombre == "elevador" else self.relacion

    def seguidor(self, indice: int) -> Seguidor:
        """El seguidor de cada leva.

        Los tres pivotes van repartidos alrededor del eje para que los brazos
        no se estorben, todos a la misma distancia. Cada uno con su brazo y su
        sentido, perpendicular al radio en reposo, que es donde el ángulo de
        presión arranca en cero.
        """
        return Seguidor.en_el_poste(
            self.distancia_al_poste,
            float(self.brazos_de_canal[indice]),
            float(self.radio_rodillo),
            orientacion_pivote=indice * 2.0 * np.pi / len(SEGUIDORES),
            sentido=self.sentidos[indice],
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
        return np.asarray(self.puntos[self.altura <= UMBRAL_DE_APOYO], dtype=np.float64)


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


def _envolver(angulos: Arreglo) -> Arreglo:
    """Ángulos a (-π, π]."""
    return np.asarray(np.pi - np.mod(np.pi - angulos, 2.0 * np.pi), dtype=np.float64)


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


def distancias_a_la_tinta(
    escritura: Escritura, puntos: Arreglo, apoyado: npt.NDArray[np.bool_]
) -> list[float]:
    """Cuánto se aparta cada punto de lo pedido de la LÍNEA que escribe la
    máquina: los segmentos entre ángulos seguidos con el lápiz apoyado.

    Medía contra los puntos sueltos, y la distancia al punto más cercano se
    divide por dos cada vez que se dobla el muestreo: lo que daba era la
    separación entre muestras —144 µm en «hola»— y no la leva —14 µm—. Ese
    número decidía `trazo_infiel` y entraba en el presupuesto de tolerancias
    como «muestreo del modelo».
    """
    indices = np.arange(len(puntos))
    siguiente = np.roll(indices, -1)
    anterior = np.roll(indices, 1)
    tinta = apoyado & apoyado[siguiente]
    desde, hasta = puntos[tinta], puntos[siguiente][tinta]
    sueltos = puntos[apoyado & ~tinta & ~apoyado[anterior]]
    salida = []
    for trazo in escritura.trazos:
        for punto in remuestrear(trazo, 64):
            mejor = np.inf
            if len(desde):
                d = hasta - desde
                largo = np.einsum("ij,ij->i", d, d)
                t = np.einsum("ij,ij->i", punto - desde, d) / np.where(largo > 0, largo, 1.0)
                t = np.clip(t, 0.0, 1.0)
                mejor = float(np.min(np.linalg.norm(desde + t[:, None] * d - punto, axis=1)))
            if len(sueltos):
                mejor = min(mejor, float(np.min(np.linalg.norm(sueltos - punto, axis=1))))
            salida.append(mejor)
    return salida


def simular(
    perfiles: dict[str, PerfilLeva],
    calajes: dict[str, float],
    maquina: Escribiente,
    escritura: Escritura,
    muestras: int,
    por_contacto: frozenset[str] = frozenset(),
) -> Simulacion:
    """Recorre las levas y mira qué escribe la máquina.

    Se evalúa en más ángulos de los que tiene la leva a propósito: si el
    reparto de grados fuera demasiado grueso, el spline se inventaría la forma
    entre muestras y el error saldría aquí.

    Las levas de `por_contacto` se recorren apoyando el rodillo en el
    polígono que se corta en vez de deshacer la curva de paso: son las
    recortadas, en las que la curva de paso ya no es lo que el rodillo sigue.
    """
    from core.cam.contacto import psi_por_contacto

    thetas = np.linspace(0.0, 2.0 * np.pi, muestras, endpoint=False)
    psi = {
        nombre: (
            psi_por_contacto(perfiles[nombre].perfil, perfiles[nombre].seguidor, thetas)
            * maquina.relacion_de(nombre)
            + calajes[nombre]
            if nombre in por_contacto
            else _psi_desde_la_leva(
                perfiles[nombre], thetas, calajes[nombre], maquina.relacion_de(nombre)
            )
        )
        for nombre in SEGUIDORES
    }

    puntos = maquina.brazo.directa(np.column_stack([psi["izquierdo"], psi["derecho"]]))
    altura = maquina.palanca.directa(psi["elevador"][:, None])[:, 0]

    apoyado = altura <= UMBRAL_DE_APOYO
    if not apoyado.any():
        return Simulacion(thetas, puntos, altura, np.inf, np.inf)

    distancias = distancias_a_la_tinta(escritura, puntos, apoyado)
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
        try:
            por_contacto = psi_por_contacto(perfil.perfil, perfil.seguidor, thetas)
        except ValueError as fallo:
            # Una leva en la que el rodillo no llega a apoyar en algún ángulo
            # es una leva que no se puede montar: es un veredicto, no una
            # excepción que tumbe la compilación.
            incidencias.append(
                Incidencia(
                    gravedad="error",
                    codigo="contacto_perdido",
                    mensaje=f"leva {nombre}: {fallo}",
                    sugerencia="simplifica la frase o reduce la caja de escritura",
                )
            )
            continue
        desviacion = np.abs(por_contacto - perfil.psi[indices])
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
    grabado: str | None = None,
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
            Taladro(
                centro=(Metros(0.0), Metros(0.0)),
                diametro=maquina.taladro_eje,
                tolerancia=maquina.ajuste_de_los_taladros,
            ),
            Taladro(
                centro=(Metros(radio_pasador), Metros(0.0)),
                diametro=maquina.pasador_indice,
                tolerancia=maquina.ajuste_de_los_taladros,
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
        tolerancia_perfil=maquina.tolerancia_de_perfil,
        # El pedido y el número, al lado contrario del pasador: entre el eje y
        # el canto de la leva más pequeña caben de sobra.
        grabado=numero if grabado is None else grabado,
        grabado_en=(Metros(-0.030), Metros(-0.0015)),
    )


# ---------------------------------------------------------------------------
# El compilador
# ---------------------------------------------------------------------------


def holguras_de_los_ejes(
    perfiles: dict[str, PerfilLeva], maquina: Escribiente
) -> dict[tuple[str, str], float]:
    """Lo que el eje de cada rodillo libra de las levas que tiene encima.

    Las tres levas giran juntas, así que en el marco de la leva el eje del
    rodillo recorre su curva de paso. Basta con medir la distancia de esa
    curva al perfil de cada leva de encima y restar el radio del casquillo.
    Negativo si lo atraviesa.
    """
    from shapely import distance, points
    from shapely.geometry import Polygon

    resultado: dict[tuple[str, str], float] = {}
    for i, abajo in enumerate(ORDEN_EN_LA_PILA):
        if abajo not in perfiles:
            continue
        recorrido = points(np.asarray(perfiles[abajo].paso))
        for arriba in ORDEN_EN_LA_PILA[i + 1 :]:
            if arriba not in perfiles:
                continue
            leva = Polygon(np.asarray(perfiles[arriba].perfil))
            dentro = leva.contains(recorrido)
            d = np.where(dentro, -1.0, 1.0) * distance(recorrido, leva.exterior)
            resultado[(abajo, arriba)] = float(d.min()) - float(maquina.radio_eje_rodillo)
    return resultado


def compilar(
    escritura: Escritura,
    maquina: Escribiente | None = None,
    capacidad: Capacidad | None = None,
    limites: LimitesLeva | None = None,
    en_la_caja: bool = False,
    simular_el_trazo: bool = True,
) -> Compilacion:
    """De una frase a tres levas, con un solo veredicto al final.

    Sin `capacidad`, las muestras por vuelta las elige la frase
    (`muestras_para`); con ella, se respeta tal cual.

    Con `en_la_caja` la escritura ya viene colocada en el papel, en el marco
    de la máquina, y no se vuelve a encajar: es lo que hace un renglón, que
    tiene que caer donde lo puso la composición entera (`compile.renglones`).

    Sin `simular_el_trazo` se para antes de recorrer las levas y devuelve el
    veredicto hasta ahí, con `simulacion` a `None` y sin piezas. Es la vista
    previa: con «Gracias», lo que va delante tarda medio segundo y la
    simulación cuarenta y cinco. **No es el mismo camino con menos cosas: es
    el mismo camino parado**, para que la vista previa no pueda discrepar del
    pedido.
    """
    maquina = maquina or Escribiente()
    elegir_muestras = capacidad is None
    capacidad = capacidad or Capacidad()
    limites = limites or LimitesLeva()

    # Redondear **después** de encajar: el radio es una longitud absoluta y
    # encajar escala la frase, así que al revés el redondeo valdría una cosa
    # distinta en cada pedido. Y antes de `programa`, porque lo que se
    # redondea es lo que se fabrica: `Compilacion.escritura` es la de verdad.
    capturada = escritura if en_la_caja else encajar_en_la_caja(escritura, maquina)
    encajada = suavizar(capturada, capacidad.radio_de_esquina)
    if elegir_muestras:
        capacidad = capacidad.model_copy(update={"muestras": muestras_para(encajada, capacidad)})
    desviacion = desviacion_de_lo_capturado(encajada, capturada)
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
    # La desviación se envuelve a ±180° antes de dividir por la relación. El
    # brazo derecho apunta hacia la izquierda —los proximales se cruzan— y su
    # ángulo vive junto a ±180°: una letra que va lo bastante a la izquierda
    # hace saltar `arctan2` de +180° a -180°, y sin envolver ese salto de una
    # vuelta llegaba a la leva como 360°/8 = 45° de desviación. Lo destapó
    # «Feliz cumpleaños»: el seguidor contra el tope y 90° de presión.
    crudos = {
        nombre: _envolver(valores - calajes[nombre]) / maquina.relacion_de(nombre)
        for nombre, valores in crudos.items()
    }

    perfiles: dict[str, PerfilLeva] = {}
    recortadas: set[str] = set()
    for indice, nombre in enumerate(SEGUIDORES):
        funcion = desde_muestras(thetas, crudos[nombre], n=capacidad.muestras)
        perfil = sintetizar(funcion, maquina.seguidor(indice))
        parcial = evaluar(perfil, limites)
        if {i.codigo for i in parcial.incidencias} & NO_ENTRA_EL_RODILLO:
            recortado = recortar(perfil)
            if not autointerseca(recortado):
                # Se corta la envolvente; si vale o no lo dice el papel, más abajo.
                perfil = recortado
                recortadas.add(nombre)
                parcial = Veredicto(
                    incidencias=tuple(
                        i for i in parcial.incidencias if i.codigo not in NO_ENTRA_EL_RODILLO
                    ),
                    metricas=parcial.metricas,
                )
        perfiles[nombre] = perfil
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

    holguras = holguras_de_los_ejes(perfiles, maquina)
    for (abajo, arriba), holgura in holguras.items():
        if holgura < float(maquina.holgura_eje_rodillo):
            veredicto = veredicto.con(
                Incidencia(
                    gravedad="error",
                    codigo="eje_de_rodillo_contra_leva",
                    mensaje=(
                        f"el eje del rodillo {abajo} pasa a {a_mm(Metros(holgura)):.2f} mm "
                        f"de la leva {arriba}, que tiene encima"
                    ),
                    sugerencia="reduce la caja de escritura o escalona más la pila",
                )
            )
    for indice, nombre in enumerate(SEGUIDORES):
        if nombre not in perfiles:
            continue
        hacia = maquina.seguidor(indice).hacia_dentro
        dentro = float(np.max(hacia * np.asarray(perfiles[nombre].psi)))
        veredicto = Veredicto(
            incidencias=veredicto.incidencias,
            metricas={**veredicto.metricas, f"giro_hacia_dentro_{nombre}": dentro},
        )
        if dentro > maquina.tope_seguidor - maquina.margen_al_tope:
            veredicto = veredicto.con(
                Incidencia(
                    gravedad="error",
                    codigo="seguidor_contra_tope",
                    mensaje=(
                        f"el seguidor {nombre} gira {np.degrees(dentro):.2f}° hacia dentro y el "
                        f"tope está a {np.degrees(maquina.tope_seguidor):.1f}°"
                    ),
                    sugerencia="reduce la caja de escritura",
                )
            )
    mayor = max((float(p.radio_maximo) for p in perfiles.values()), default=0.0)
    if mayor > float(maquina.radio_maximo_cartucho):
        veredicto = veredicto.con(
            Incidencia(
                gravedad="error",
                codigo="cartucho_no_sale",
                mensaje=(
                    f"la leva mayor mide {a_mm(Metros(mayor)):.1f} mm de radio y el cartucho "
                    f"solo sale entre los postes hasta {a_mm(maquina.radio_maximo_cartucho):.1f}"
                ),
                sugerencia="reduce la caja de escritura",
            )
        )
    if holguras:
        veredicto = Veredicto(
            incidencias=veredicto.incidencias,
            metricas={**veredicto.metricas, "holgura_eje_rodillo_min": min(holguras.values())},
        )

    # Las recortadas no se comparan con la curva de paso: se apartan de ella a
    # propósito. Lo que vale para ellas es lo que escriben, y eso lo mide la
    # simulación por contacto de abajo.
    contacto, contacto_en_la_punta, incidencias_contacto = verificar_por_contacto(
        {n: p for n, p in perfiles.items() if n not in recortadas}, maquina
    )
    for incidencia in incidencias_contacto:
        veredicto = veredicto.con(incidencia)

    if not simular_el_trazo:
        # El camino corto de la vista previa. Con «Gracias», recorrer las
        # levas tarda 45 s y todo lo de arriba junto medio segundo: parar
        # aquí es lo que deja que saber si cabe cueste lo mismo que teclearlo.
        #
        # Y lo que falta no se calla. Una leva recortada escribe la letra
        # redondeada, y CUÁNTO solo lo dice la simulación; decir que cabe sin
        # ese número sería prometer lo que no se ha medido. De ahí que lo que
        # hace lenta la compilación y lo que hace incierto el veredicto sean
        # la misma cosa: sin recortes esto ya es la respuesta final.
        if recortadas:
            veredicto = veredicto.con(
                Incidencia(
                    gravedad="aviso",
                    codigo="falta_medir_el_trazo",
                    mensaje=(
                        f"el rodillo no entra en algún tramo de la leva "
                        f"{', '.join(sorted(recortadas))}: se corta su envolvente y la "
                        f"letra sale redondeada"
                    ),
                    sugerencia="haz el cartucho para medir cuánto se aparta; es lo que tarda",
                )
            )
        return Compilacion(
            escritura=encajada,
            programa=prog,
            tramos=tramos,
            perfiles=perfiles,
            calajes=calajes,
            piezas=[],
            simulacion=None,
            veredicto=Veredicto(
                incidencias=veredicto.incidencias,
                metricas={
                    **veredicto.metricas,
                    "levas_recortadas": float(len(recortadas)),
                    "error_contacto_rad": contacto,
                    "error_contacto_en_la_punta": contacto_en_la_punta,
                    "desviacion_de_lo_capturado": desviacion,
                    "radio_de_esquina": float(capacidad.radio_de_esquina),
                    "muestras": float(capacidad.muestras),
                },
            ),
        )

    simulacion = simular(
        perfiles,
        calajes,
        maquina,
        encajada,
        muestras=capacidad.muestras * 2,
        por_contacto=frozenset(recortadas),
    )
    if recortadas:
        lista = ", ".join(sorted(recortadas))
        if simulacion.error_maximo <= SOCAVADO_TOLERABLE:
            veredicto = veredicto.con(
                Incidencia(
                    gravedad="aviso",
                    codigo="socavado_tolerable",
                    mensaje=(
                        f"el rodillo no entra en algún tramo de la leva {lista}: se corta su "
                        f"envolvente, que redondea la letra hasta "
                        f"{simulacion.error_maximo * 1000:.2f} mm en el papel"
                    ),
                    sugerencia="nada que hacer: queda por debajo de lo que se ve",
                )
            )
        else:
            veredicto = veredicto.con(
                Incidencia(
                    gravedad="error",
                    codigo="perfil_autointersecado",
                    mensaje=(
                        f"el rodillo no entra en la leva {lista}, y la leva que sí se puede "
                        f"cortar se aparta {simulacion.error_maximo * 1000:.2f} mm de la letra "
                        f"(se admiten {SOCAVADO_TOLERABLE * 1000:.2f})"
                    ),
                    sugerencia="parte la frase en renglones, cada uno en su vuelta",
                )
            )
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
            "levas_recortadas": float(len(recortadas)),
            "error_contacto_rad": contacto,
            "error_contacto_en_la_punta": contacto_en_la_punta,
            "desviacion_de_lo_capturado": desviacion,
            "radio_de_esquina": float(capacidad.radio_de_esquina),
            "muestras": float(capacidad.muestras),
        },
    )

    piezas = [
        pieza_de_leva(
            perfiles[nombre],
            nombre=f"leva {nombre}",
            numero=f"L-{indice + 1:03d}",
            conjunto=f"cartucho {escritura.nombre}",
            maquina=maquina,
            grabado=f"{escritura.nombre} {indice + 1:03d}",
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
    "ORDEN_EN_LA_PILA",
    "SEGUIDORES",
    "UMBRAL_DE_APOYO",
    "Compilacion",
    "Escribiente",
    "Simulacion",
    "compilar",
    "distancias_a_la_tinta",
    "encajar_en_la_caja",
    "holguras_de_los_ejes",
    "pieza_de_leva",
    "simular",
    "verificar_por_contacto",
]
