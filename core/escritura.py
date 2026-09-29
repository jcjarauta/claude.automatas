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

from core.cam.curves import cicloidal, rejilla
from core.program import PistaContinua, Programa
from core.units import TAU, AnguloCiclo, Arco, Longitud, Metros, grados, mm
from core.verdict import Incidencia, Veredicto

Arreglo = npt.NDArray[np.float64]
Punto = tuple[Metros, Metros]

CANAL_X = "punta.x"
CANAL_Y = "punta.y"
CANAL_Z = "levantamiento"

MUESTRAS_MINIMAS_POR_TRAMO = 8
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


def interpolar(trazo: Trazo, fracciones: Arreglo) -> Arreglo:
    """Puntos del trazo a las fracciones dadas de su longitud de arco.

    `fracciones` va de 0 a 1. Devuelve un array (n, 2) en metros.
    """
    coordenadas = trazo.coordenadas
    acumulada = _acumulada(coordenadas)
    objetivo = np.asarray(fracciones, dtype=np.float64) * acumulada[-1]
    return np.column_stack(
        [
            np.interp(objetivo, acumulada, coordenadas[:, 0]),
            np.interp(objetivo, acumulada, coordenadas[:, 1]),
        ]
    )


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

    for i, tramo in enumerate(tramos):
        aqui = cual == i
        if not np.any(aqui):
            continue
        fracciones = (thetas[aqui] - float(tramo.inicio)) / float(tramo.arco)
        if tramo.clase == "trazo":
            puntos = interpolar(escritura.trazos[tramo.indice], fracciones)
        else:
            desde = escritura.trazos[tramo.indice].fin
            hasta = escritura.trazos[(tramo.indice + 1) % len(escritura.trazos)].inicio
            puntos = desde + np.outer(fracciones, hasta - desde)
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
    "remuestrear",
    "repartir",
]
