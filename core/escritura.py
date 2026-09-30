"""Front-end de escritura: de una frase a mano a las tres pistas del eje.

Es el paso 2 del patrón de compilación: normalizar, reparametrizar por
longitud de arco, repartir los grados de θ y comprobar la capacidad. Lo que
entra es **solo geometría** —regla 7: ni tiempo, ni presión, ni velocidad— y
lo que sale es un `Programa` indexado por θ, que es lo único que el resto del
núcleo sabe leer.

Las tres ideas que lo sostienen:

**Reparametrizar por arco.** La mano escribe despacio en las curvas y deprisa
en las rectas, y eso no se captura. Si se repartiera θ por número de puntos,
un tramo con muestras juntas saldría lento y uno con muestras separadas
saldría a saltos. Repartiendo por longitud de arco, la punta avanza a
velocidad constante en θ y las tres levas quedan suaves.

**Repartir θ por longitud, no por trazo.** Una vuelta son 360° y hay que
gastarlos en lo que se ve. Cada trazo recibe ángulo en proporción a lo que
mide, con un mínimo para que un punto sobre una i no se quede sin grados. Los
vuelos —el lápiz levantado entre trazo y trazo— reciben menos: no se ven, y
el ángulo que se les quita se lo queda el papel.

**Que la frase no quepa es un veredicto.** Si los mínimos ya suman más de una
vuelta, no hay reparto posible. Eso no es una excepción: es un resultado que
se le enseña al cliente con lo que tendría que cambiar.

No confundir `Trazo` de aquí —un trazo de escritura, con el lápiz apoyado—
con `emit.layout.Trazo`, que es una primitiva de dibujo.
"""

from __future__ import annotations

from typing import Literal

import numpy as np
import numpy.typing as npt
from pydantic import BaseModel, ConfigDict, Field, model_validator
from scipy.interpolate import CubicSpline

from core.cam.curves import cicloidal, rejilla
from core.program import PistaContinua, Programa
from core.units import TAU, AnguloCiclo, Arco, Longitud, LongitudConCero, Metros, grados, mm
from core.verdict import Incidencia, Veredicto

Arreglo = npt.NDArray[np.float64]
Punto = tuple[Metros, Metros]

CANAL_X = "punta.x"
CANAL_Y = "punta.y"
CANAL_Z = "levantamiento"

MUESTRAS_MINIMAS_POR_TRAMO = 8

TANGENTE_MAXIMA_DEL_VUELO = 1.5
"""Tope de la tangente del vuelo, en múltiplos del salto. Por encima de uno
y medio la Hermite se abomba hasta formar un lazo, y un lazo es una cúspide:
la misma esquina que se quería quitar, movida de sitio."""

FRACCION_TANGENTE_DEL_VUELO = 1.0 / 3.0
"""Cuánto se estiran las tangentes del vuelo, como fracción del salto.

Un tercio es el valor corriente de una Hermite cúbica. Más curva más y
aleja más el lápiz del papel; menos deja la esquina a medio quitar."""
"""Por debajo de esto, un tramo queda descrito por tan pocas muestras que el
spline de la leva se inventa la forma entre ellas."""


class _Base(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


# ---------------------------------------------------------------------------
# Lo que se captura
# ---------------------------------------------------------------------------


class Trazo(_Base):
    """Un trazo continuo: el lápiz baja, recorre y sube.

    Puntos en metros, en el orden en que se escribieron. Nada más: ni cuándo
    ni con cuánta presión.
    """

    puntos: list[Punto] = Field(min_length=2)

    @model_validator(mode="after")
    def _con_longitud(self) -> Trazo:
        if float(self.longitud) <= 0.0:
            raise ValueError(
                "un trazo de longitud cero no se puede reparametrizar. Para un "
                "punto sobre una i, dale la longitud que de verdad tiene."
            )
        return self

    @property
    def coordenadas(self) -> Arreglo:
        return np.asarray(self.puntos, dtype=np.float64)

    @property
    def longitud(self) -> Metros:
        """Suma de las cuerdas. Es la longitud que se reparte en θ."""
        return Metros(float(np.sum(np.linalg.norm(np.diff(self.coordenadas, axis=0), axis=1))))

    @property
    def inicio(self) -> Arreglo:
        return np.asarray(self.coordenadas[0], dtype=np.float64)

    @property
    def fin(self) -> Arreglo:
        return np.asarray(self.coordenadas[-1], dtype=np.float64)


class Escritura(_Base):
    """Lo que escribió el cliente: una lista de trazos, en orden."""

    nombre: str = Field(min_length=1)
    trazos: list[Trazo] = Field(min_length=1)

    @property
    def limites(self) -> tuple[Metros, Metros, Metros, Metros]:
        todos = np.vstack([t.coordenadas for t in self.trazos])
        return (
            Metros(float(todos[:, 0].min())),
            Metros(float(todos[:, 1].min())),
            Metros(float(todos[:, 0].max())),
            Metros(float(todos[:, 1].max())),
        )

    @property
    def ancho(self) -> Metros:
        x0, _, x1, _ = self.limites
        return Metros(x1 - x0)

    @property
    def alto(self) -> Metros:
        _, y0, _, y1 = self.limites
        return Metros(y1 - y0)


# ---------------------------------------------------------------------------
# Reparametrizar
# ---------------------------------------------------------------------------


def _acumulada(coordenadas: Arreglo) -> Arreglo:
    """Longitud de arco acumulada en cada punto, empezando en cero."""
    pasos = np.linalg.norm(np.diff(coordenadas, axis=0), axis=1)
    return np.concatenate([[0.0], np.cumsum(pasos)])


PUNTOS_PARA_SPLINE = 4
"""Por debajo de esto no hay curva que ajustar y se interpola recto. Con
tres puntos una cúbica natural ya funciona, pero con tan pocos datos el
sobrepaso es mayor que la curva que describe."""


def interpolar(trazo: Trazo, fracciones: Arreglo) -> Arreglo:
    """Puntos del trazo a las fracciones dadas de su longitud de arco.

    `fracciones` va de 0 a 1. Devuelve un array (n, 2) en metros.

    **Interpola con una cúbica C2, no con cuerdas rectas.** Es lo que cierra
    el agujero que tenía la envolvente: con interpolación lineal, un trazo es
    una polilínea y tiene una esquina —curvatura infinita— en cada vértice.
    Remuestrear más fino no revelaba la curva, revelaba las esquinas, y el
    radio de curvatura mínimo **se dividía por dos cada vez que se doblaba
    `Capacidad.muestras`**. El veredicto de fabricabilidad dependía así de un
    parámetro de cálculo que no tiene nada que ver con la física.

    Con una C2 la curvatura tiende a la de la curva y el veredicto converge.

    La curva **pasa por los puntos capturados**: es interpolación y no
    aproximación, porque lo que el cliente escribió no se negocia. Lo que sí
    se negocia es lo que pasa entre punto y punto, y ahí una cúbica natural
    es la elección estándar.

    **Una cúbica sobrepasa en los giros cerrados**, así que el orden importa:
    primero `redondear_esquinas`, que acota la curvatura de la intención, y
    después esto, que la reproduce sin volver a trocearla. Al revés, el
    spline ondularía alrededor de un pico que no puede seguir.

    El parámetro es la longitud de cuerda acumulada. La longitud real de la
    curva es algo mayor, así que el reparto por arco queda ligeramente
    desigual dentro del trazo; con puntos de captura razonablemente juntos la
    diferencia es de milésimas y no llega al papel.
    """
    coordenadas = trazo.coordenadas
    acumulada = _acumulada(coordenadas)
    objetivo = np.asarray(fracciones, dtype=np.float64) * acumulada[-1]

    if len(coordenadas) < PUNTOS_PARA_SPLINE:
        return np.column_stack(
            [
                np.interp(objetivo, acumulada, coordenadas[:, 0]),
                np.interp(objetivo, acumulada, coordenadas[:, 1]),
            ]
        )

    curva = CubicSpline(acumulada, coordenadas, axis=0, bc_type="natural")
    puntos = np.asarray(curva(np.clip(objetivo, 0.0, acumulada[-1])), dtype=np.float64)
    # Los extremos, exactos: el vuelo enlaza con ellos y un salto de coma
    # flotante ahí se vería como un escalón en la leva.
    en_cero = np.isclose(objetivo, 0.0)
    en_uno = np.isclose(objetivo, acumulada[-1])
    puntos[en_cero] = coordenadas[0]
    puntos[en_uno] = coordenadas[-1]
    return puntos


def remuestrear(trazo: Trazo, n: int) -> Arreglo:
    """`n` puntos repartidos por igual **en longitud de arco**, extremos
    incluidos."""
    if n < 2:
        raise ValueError(f"hacen falta al menos dos muestras, no {n}")
    return interpolar(trazo, np.linspace(0.0, 1.0, n))


def encajar(escritura: Escritura, ancho: Longitud, alto: Longitud) -> Escritura:
    """Escala la escritura para llenar la caja y la centra.

    Se conserva la proporción: una letra estirada en un eje deja de parecerse
    a la del cliente, y eso es justo lo que se vende.
    """
    x0, y0, x1, y1 = escritura.limites
    actual_ancho, actual_alto = float(x1 - x0), float(y1 - y0)
    candidatos = [
        float(ancho) / actual_ancho if actual_ancho > 0.0 else np.inf,
        float(alto) / actual_alto if actual_alto > 0.0 else np.inf,
    ]
    factor = min(candidatos)
    if not np.isfinite(factor):
        raise ValueError("una escritura sin extensión en ningún eje no se puede encajar")

    dx = float(ancho) / 2.0 - factor * (float(x0) + float(x1)) / 2.0
    dy = float(alto) / 2.0 - factor * (float(y0) + float(y1)) / 2.0
    return Escritura(
        nombre=escritura.nombre,
        trazos=[
            Trazo(
                puntos=[
                    (Metros(factor * float(px) + dx), Metros(factor * float(py) + dy))
                    for px, py in trazo.puntos
                ]
            )
            for trazo in escritura.trazos
        ],
    )


# ---------------------------------------------------------------------------
# Repartir los grados
# ---------------------------------------------------------------------------


class Capacidad(_Base):
    """Cuánto ángulo hay y cómo de fino se puede picar.

    Son los límites de la máquina, no de la frase: la misma capacidad juzga
    cualquier escritura.
    """

    muestras: int = Field(default=720, ge=8, le=20_000)
    """Muestras por vuelta de cada pista. Media vuelta de grado por defecto."""
    arco_minimo_trazo: Arco = grados(6.0)
    """Lo que recibe el trazo más corto pase lo que pase."""
    arco_levantamiento: Arco = grados(8.0)
    """Lo que tarda el lápiz en subir, y otro tanto en bajar. Todo vuelo
    reserva el doble."""
    altura_levantamiento: Longitud = mm(3.0)
    """Cuánto sube la punta. Suficiente para no arrastrar sobre el papel."""
    peso_vuelo: float = Field(default=0.5, gt=0.0, le=1.0)
    """Cuánto ángulo recibe un vuelo respecto a un trazo de la misma
    longitud. Menos de uno porque un vuelo no se ve: puede ir más deprisa y
    devolverle grados a lo que sí queda en el papel."""
    radio_de_esquina: LongitudConCero = mm(0.5)
    """A qué radio se redondea el pico más agudo del trazo. **Es una cota
    del pedido, no un ajuste**: el pico se le quita al cliente, así que el
    número tiene que poder decirse en el informe.

    Medio milímetro no es una preferencia, es un codo medido. Con «hola» el
    radio de curvatura mínimo del perfil va, al doblar las muestras de 720 a
    5.760: sin redondear 13,5 → 1,9 mm (se divide por dos cada vez, que es la
    firma de una esquina); a 0,2 mm llega a 6,8; a 0,3 mm a 9,6; **y a 0,5 mm
    se queda en 12,96, que ya no es el trazo sino el elevador**, que siempre
    convergió. Por encima de 0,5 no mejora nada y solo cuesta fidelidad.

    Y redondear **no** cuesta fidelidad aquí, la compra: `interpolar` es una
    cúbica por los puntos capturados y con una polilínea escasa se pasa de
    largo —2,47 mm en el trazo de cinco puntos de «hola»—. Redondear
    densifica el trazo donde gira, y la desviación baja a 0,15 mm.

    Cero desactiva el redondeo. Sirve para comparar y para reproducir un
    pedido antiguo; no para fabricar."""


class Tramo(_Base):
    """Un trozo del ciclo: o se escribe, o se vuela."""

    clase: Literal["trazo", "vuelo"]
    indice: int = Field(ge=0)
    """Qué trazo es, o de qué trazo sale el vuelo."""
    inicio: AnguloCiclo
    arco: Arco


def _longitudes(escritura: Escritura) -> tuple[list[float], list[float]]:
    """Longitud de cada trazo y de cada vuelo, en el orden del ciclo.

    El último vuelo es el de regreso, del final de la frase al principio: sin
    él el ciclo no cerraría y la segunda vuelta empezaría desplazada.
    """
    trazos = [float(t.longitud) for t in escritura.trazos]
    vuelos = []
    for i, trazo in enumerate(escritura.trazos):
        siguiente = escritura.trazos[(i + 1) % len(escritura.trazos)]
        vuelos.append(float(np.linalg.norm(siguiente.inicio - trazo.fin)))
    return trazos, vuelos


def repartir(escritura: Escritura, capacidad: Capacidad) -> tuple[list[Tramo], Veredicto]:
    """Reparte los 360° entre trazos y vuelos, y dice si caben.

    Primero se sirven los mínimos, que son intocables; el resto se reparte en
    proporción a la longitud. Si los mínimos ya no caben, se devuelven
    igualmente unos tramos proporcionales —para poder enseñar el resultado— y
    un veredicto negativo que dice cuánto se pasa.
    """
    trazos, vuelos = _longitudes(escritura)
    minimo_trazo = float(capacidad.arco_minimo_trazo)
    minimo_vuelo = 2.0 * float(capacidad.arco_levantamiento)

    minimos: list[float] = []
    pesos: list[float] = []
    clases: list[Literal["trazo", "vuelo"]] = []
    indices: list[int] = []
    for i, (largo_trazo, largo_vuelo) in enumerate(zip(trazos, vuelos, strict=True)):
        minimos += [minimo_trazo, minimo_vuelo]
        pesos += [largo_trazo, largo_vuelo * capacidad.peso_vuelo]
        clases += ["trazo", "vuelo"]
        indices += [i, i]

    necesario = sum(minimos)
    incidencias: list[Incidencia] = []
    if necesario >= TAU:
        incidencias.append(
            Incidencia(
                gravedad="error",
                codigo="capacidad_superada",
                mensaje=(
                    f"los mínimos de {len(trazos)} trazos suman "
                    f"{np.degrees(necesario):.0f}°, más de una vuelta"
                ),
                sugerencia=(
                    "acorta la frase, únela en menos trazos, o reparte la escritura "
                    "en más de un cartucho"
                ),
            )
        )
        # Sin holgura que repartir, el reparto se hace solo por proporción,
        # para que al menos se pueda enseñar cómo quedaría.
        arcos = [TAU * p / sum(pesos) for p in pesos]
    else:
        holgura = TAU - necesario
        total = sum(pesos)
        arcos = [m + holgura * p / total for m, p in zip(minimos, pesos, strict=True)]

    # El último arco se cierra por diferencia: así la suma es exactamente una
    # vuelta y no una vuelta más el error de redondeo acumulado.
    arcos[-1] = TAU - sum(arcos[:-1])

    if min(arcos) * capacidad.muestras / TAU < MUESTRAS_MINIMAS_POR_TRAMO:
        incidencias.append(
            Incidencia(
                gravedad="aviso",
                codigo="resolucion_justa",
                mensaje=(
                    f"el tramo más corto ocupa {np.degrees(min(arcos)):.1f}° y con "
                    f"{capacidad.muestras} muestras por vuelta le tocan "
                    f"{min(arcos) * capacidad.muestras / TAU:.0f}"
                ),
                sugerencia="sube las muestras por vuelta",
            )
        )

    tramos: list[Tramo] = []
    inicio = 0.0
    for clase, indice, arco in zip(clases, indices, arcos, strict=True):
        tramos.append(
            Tramo(
                clase=clase,
                indice=indice,
                inicio=AnguloCiclo(min(inicio, TAU * (1.0 - 1e-15))),
                arco=Arco(arco),
            )
        )
        inicio += arco

    return tramos, Veredicto(
        incidencias=tuple(incidencias),
        metricas={
            "arco_minimo_necesario": necesario,
            "arco_mas_corto": min(arcos),
            "longitud_trazada": sum(trazos),
            "longitud_volada": sum(vuelos),
        },
    )


# ---------------------------------------------------------------------------
# El programa
# ---------------------------------------------------------------------------


PUNTOS_POR_ARCO = 12
"""Con cuántos segmentos se aproxima cada esquina redondeada. Doce deja la
flecha del polígono en menos de un 1 % del radio, muy por debajo de lo que
el muestreo de la leva resuelve."""

ANGULO_DE_ESQUINA = grados(3.0)
"""Por debajo de este giro, un vértice no es una esquina: es el muestreo de
una curva suave, y tocarlo sería estropear el trazo del cliente."""


def redondear_esquinas(trazo: Trazo, radio: Longitud) -> Trazo:
    """Sustituye cada pico del trazo por un arco del radio que se pida.

    **Por qué hace falta.** Un trazo capturado es una polilínea, y una
    polilínea tiene una esquina en cada vértice. Una esquina es curvatura
    infinita; la leva la hereda, y el offset por el radio del rodillo se
    autointerseca: socavado, y la pieza no se puede fabricar.

    Sin esto el problema no desaparecía, se escondía: el muestreo redondeaba
    la esquina por accidente y el radio de curvatura mínimo **se dividía por
    dos cada vez que se doblaba `Capacidad.muestras`**, de 13,4 mm a 360
    muestras a 0,65 a 11.520. Un veredicto de fabricabilidad que depende de
    un parámetro de cálculo no es un veredicto.

    **Esto sí cuesta fidelidad**, al revés que suavizar el vuelo: el pico se
    lo quitamos al cliente. Por eso el radio es una cota declarada y no un
    efecto secundario, y por eso se puede decir en el informe cuánto se ha
    redondeado la esquina más aguda de su firma.

    Un vértice que gira menos de `ANGULO_DE_ESQUINA` no se toca: es el
    muestreo de una curva suave, no un pico. Y si el arco no cabe en los
    segmentos que lo rodean, se reduce el radio en esa esquina antes que
    pasarse de largo y cruzar el trazo.
    """
    puntos = trazo.coordenadas
    if len(puntos) < 3:
        return trazo

    r = float(radio)
    salida: list[Arreglo] = [puntos[0]]
    for i in range(1, len(puntos) - 1):
        previo, vertice, siguiente = puntos[i - 1], puntos[i], puntos[i + 1]
        entra, sale = vertice - previo, siguiente - vertice
        n_entra, n_sale = float(np.linalg.norm(entra)), float(np.linalg.norm(sale))
        if n_entra <= 0.0 or n_sale <= 0.0:
            continue
        u, v = entra / n_entra, sale / n_sale

        giro = float(np.arccos(np.clip(float(np.dot(u, v)), -1.0, 1.0)))
        if giro < float(ANGULO_DE_ESQUINA):
            salida.append(vertice)
            continue
        if giro > np.pi - 1e-9:  # media vuelta: no hay arco que valga
            salida.append(vertice)
            continue

        # Retranqueo del arco sobre cada segmento, y lo que de verdad cabe.
        retranqueo = r / np.tan((np.pi - giro) / 2.0)
        cabe = min(retranqueo, n_entra / 2.0, n_sale / 2.0)
        radio_real = cabe * np.tan((np.pi - giro) / 2.0)
        if radio_real <= 0.0:
            salida.append(vertice)
            continue

        p_entrada, p_salida = vertice - u * cabe, vertice + v * cabe
        centro_dir = v - u
        norma = float(np.linalg.norm(centro_dir))
        if norma <= 0.0:
            salida.append(vertice)
            continue
        # La distancia del vértice al centro es R/cos(giro/2), no R/sin: el
        # centro está sobre la bisectriz interior. Las dos coinciden a 90°,
        # que es justo el caso con el que se probó primero.
        centro = vertice + (centro_dir / norma) * (radio_real / np.cos(giro / 2.0))

        a0 = np.arctan2(*(p_entrada - centro)[::-1])
        a1 = np.arctan2(*(p_salida - centro)[::-1])
        barrido = (a1 - a0 + np.pi) % (2.0 * np.pi) - np.pi
        angulos = a0 + barrido * np.linspace(0.0, 1.0, PUNTOS_POR_ARCO)
        salida.extend(centro + radio_real * np.column_stack([np.cos(angulos), np.sin(angulos)]))

    salida.append(puntos[-1])
    limpio = [salida[0]]
    for p in salida[1:]:
        if float(np.linalg.norm(p - limpio[-1])) > 1e-12:
            limpio.append(p)
    return Trazo(puntos=[(Metros(float(x)), Metros(float(y))) for x, y in limpio])


def suavizar(escritura: Escritura, radio: Longitud) -> Escritura:
    """Redondea las esquinas de todos los trazos al radio que el rodillo
    puede seguir. Es la etapa que convierte cualquier fuente de entrada
    —lienzo, foto vectorizada, fuente de línea única— en algo fabricable."""
    return Escritura(
        nombre=escritura.nombre,
        trazos=[redondear_esquinas(t, radio) for t in escritura.trazos],
    )


PASO_DE_TANGENTE = 1e-4
"""Fracción del trazo con la que se mide su pendiente en un extremo."""


def _tangente(trazo: Trazo, *, al_final: bool) -> Arreglo:
    """Hacia dónde va el lápiz al acabar un trazo, o de dónde viene al
    empezarlo. Unitaria; cero si el trazo degenera, y entonces el vuelo sale
    recto, que es lo que hacía siempre.

    **Se mide sobre `interpolar`, no sobre la polilínea.** Es la misma curva
    que va a recorrer la máquina, y tienen que coincidir: cuando esto leía la
    última cuerda de la polilínea y la interpolación pasó a ser una cúbica,
    el vuelo salía con una pendiente distinta de la que traía el trazo y la
    esquina que se acababa de quitar volvía por la puerta de atrás.
    """
    h = PASO_DE_TANGENTE
    fracciones = np.array([1.0 - h, 1.0]) if al_final else np.array([0.0, h])
    extremos = interpolar(trazo, fracciones)
    borde = extremos[1] - extremos[0]
    norma = float(np.linalg.norm(borde))
    return borde / norma if norma > 0.0 else np.zeros(2)


def vuelo(
    desde: Trazo,
    hasta: Trazo,
    fracciones: Arreglo,
    velocidades: tuple[float, float] | None = None,
) -> Arreglo:
    """Por dónde pasa la punta entre dos trazos, con el lápiz levantado.

    **Era una recta**, y ahí estaba el fallo más escondido del proyecto: una
    recta del final de un trazo al principio del siguiente mete una esquina
    en cada despegue y en cada aterrizaje. Una esquina es curvatura infinita,
    la leva la hereda, y el offset por el radio del rodillo se autointerseca:
    socavado. No se veía porque el muestreo la redondeaba, y el veredicto
    salía limpio o no según `Capacidad.muestras`, que no tiene nada que ver
    con la física.

    Ahora es una **Hermite cúbica tangente a los dos trazos**, y no cuesta
    nada: el lápiz va levantado durante todo el vuelo, así que su forma es la
    única parte de la trayectoria que se puede cambiar sin tocar lo que el
    cliente escribió.

    **Tangente no basta: hay que igualar también la velocidad.** Si el vuelo
    sale en la buena dirección pero al doble de prisa, la trayectoria en θ
    tiene un codo igual. `velocidades` son las derivadas dP/dθ de los dos
    trazos en sus extremos, y con ellas las tangentes de la Hermite se
    escalan para que el empalme sea C1 **en θ**, que es la variable en la que
    trabaja la leva. Sin ellas se cae al tercio del salto, que es el valor
    corriente de una Hermite y deja la esquina a medio quitar.
    """
    p0, p1 = desde.fin, hasta.inicio
    salto = float(np.linalg.norm(p1 - p0))
    if salto <= 0.0:
        return np.repeat(p0[None, :], len(fracciones), axis=0)

    if velocidades is None:
        escala = (salto * FRACCION_TANGENTE_DEL_VUELO,) * 2
    else:
        # Acotadas. Una Hermite con tangentes mucho más largas que la cuerda
        # se abomba hasta formar un lazo, y un lazo es una cúspide: la misma
        # esquina que se quería quitar, en otro sitio. Pasa cuando el trazo
        # va rápido y el salto al siguiente es corto.
        tope = salto * TANGENTE_MAXIMA_DEL_VUELO
        escala = (min(velocidades[0], tope), min(velocidades[1], tope))
    m0 = _tangente(desde, al_final=True) * escala[0]
    m1 = _tangente(hasta, al_final=False) * escala[1]

    s = np.asarray(fracciones, dtype=np.float64)[:, None]
    s2, s3 = s * s, s * s * s
    return (
        (2.0 * s3 - 3.0 * s2 + 1.0) * p0
        + (s3 - 2.0 * s2 + s) * m0
        + (-2.0 * s3 + 3.0 * s2) * p1
        + (s3 - s2) * m1
    )


def _altura_del_vuelo(fracciones: Arreglo, arco: float, capacidad: Capacidad) -> Arreglo:
    """Sube, se mantiene arriba y baja, con ley cicloidal en las rampas.

    Una rampa lineal tendría aceleración infinita al arrancar, y en la leva
    del lápiz eso es un golpe en cada trazo.
    """
    rampa = min(float(capacidad.arco_levantamiento) / arco, 0.5)
    altura = float(capacidad.altura_levantamiento)
    subida = altura * cicloidal(np.clip(fracciones / rampa, 0.0, 1.0))
    bajada = altura * cicloidal(np.clip((1.0 - fracciones) / rampa, 0.0, 1.0))
    return np.minimum(subida, bajada)


def programa(escritura: Escritura, capacidad: Capacidad) -> tuple[Programa, Veredicto]:
    """De la escritura a las tres pistas, con su veredicto.

    Las tres comparten rejilla porque las tres levas van caladas en el mismo
    eje: se leen todas en el mismo ángulo.
    """
    tramos, veredicto = repartir(escritura, capacidad)
    thetas = rejilla(capacidad.muestras)

    inicios = np.array([float(t.inicio) for t in tramos])
    cual = np.clip(np.searchsorted(inicios, thetas, side="right") - 1, 0, len(tramos) - 1)

    x = np.zeros_like(thetas)
    y = np.zeros_like(thetas)
    z = np.zeros_like(thetas)

    # Cuánto θ recibió cada trazo, para poder medir su velocidad de empalme.
    arcos = {t.indice: float(t.arco) for t in tramos if t.clase == "trazo"}

    for i, tramo in enumerate(tramos):
        aqui = cual == i
        if not np.any(aqui):
            continue
        fracciones = (thetas[aqui] - float(tramo.inicio)) / float(tramo.arco)
        if tramo.clase == "trazo":
            puntos = interpolar(escritura.trazos[tramo.indice], fracciones)
        else:
            desde = escritura.trazos[tramo.indice]
            hasta = escritura.trazos[(tramo.indice + 1) % len(escritura.trazos)]
            # Velocidad del vuelo en sus extremos, medida en la misma unidad
            # que la del trazo con el que empalma: metros por unidad de la
            # fracción del vuelo. Con esto el empalme es C1 en θ, no solo
            # tangente, y deja de haber codo al despegar y al aterrizar.
            salida = float(desde.longitud) * float(tramo.arco) / arcos[tramo.indice]
            entrada = (
                float(hasta.longitud)
                * float(tramo.arco)
                / arcos[(tramo.indice + 1) % len(escritura.trazos)]
            )
            puntos = vuelo(desde, hasta, fracciones, (salida, entrada))
            z[aqui] = _altura_del_vuelo(fracciones, float(tramo.arco), capacidad)
        x[aqui] = puntos[:, 0]
        y[aqui] = puntos[:, 1]

    lista = thetas.tolist()
    return (
        Programa(
            nombre=escritura.nombre,
            pistas=[
                PistaContinua(canal=CANAL_X, unidad="m", thetas=lista, valores=x.tolist()),
                PistaContinua(canal=CANAL_Y, unidad="m", thetas=lista, valores=y.tolist()),
                PistaContinua(canal=CANAL_Z, unidad="m", thetas=lista, valores=z.tolist()),
            ],
        ),
        veredicto,
    )


__all__ = [
    "CANAL_X",
    "CANAL_Y",
    "CANAL_Z",
    "MUESTRAS_MINIMAS_POR_TRAMO",
    "Capacidad",
    "Escritura",
    "Tramo",
    "Trazo",
    "encajar",
    "interpolar",
    "programa",
    "redondear_esquinas",
    "remuestrear",
    "repartir",
    "suavizar",
    "vuelo",
]
