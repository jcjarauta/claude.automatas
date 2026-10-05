"""Qué hace falta acotar para que una pieza se pueda dibujar desde cero.

La ficha de una pieza tiene que servir para dibujarla en cualquier CAD a
alguien que no la ha visto nunca y solo tiene la hoja. «¿Puede alguien
dibujarla con esto?» no se automatiza, pero su condición necesaria sí, y los
dos lados ya son dato:

- el **perfil** de la pieza, la lista de `Arco` y `Segmento` que va al DXF;
- las **cotas** que la ficha rotula (`Cota`), cada una con lo que cubre.

`faltas` los cruza: cada arco tiene que tener una cota que dé su radio y otra
que sitúe su centro; cada tramo recto, una longitud o la declaración de
tangencia; cada cara plana, su distancia, su cuerda y de qué lado está. Lo
que no queda cubierto sale con el nombre de la pieza.

`construccion` lee del perfil **cómo se construye**: qué tramo es tangente a
qué arcos —«barra de dos cubos» son dos círculos y sus tangentes, y nada en
la hoja lo decía: quien lo dibujara como un trapecio obtenía otra pieza, y se
veía bien—, qué tramo es la cuerda de una cara plana y cuál es un tramo
libre que necesita su longitud.

**Una cuerda no sitúa una cara plana.** A 4 del centro puede caer a +4 o a
-4, y con la cara al otro lado el brazo se monta media vuelta girado. Por eso
una cara plana se acota con tres datos: distancia al eje, cuerda y lado.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

from emit.plataforma import BRAZOS, PERFILES, Arco, Perfil, Segmento, brazo

TOL = 0.02
"""mm: dos puntos son el mismo, o un tramo es tangente, por debajo de esto."""


def perfil_de(nombre: str, c: dict[str, float]) -> Perfil:
    """El perfil de una pieza, el mismo que va al DXF."""
    return brazo(nombre, c) if nombre in BRAZOS else PERFILES[nombre](c)


def _cerca(a: tuple[float, float], b: tuple[float, float], tol: float = TOL) -> bool:
    return math.dist(a, b) < tol


def _en_arco(p: tuple[float, float], a: Arco) -> bool:
    return abs(math.dist(p, a.centro) - a.radio) < TOL


def _tangente_en(p: tuple[float, float], direccion: tuple[float, float], a: Arco) -> bool:
    """Si un tramo que pasa por `p` con esa dirección es tangente al arco
    allí: perpendicular al radio."""
    rx, ry = p[0] - a.centro[0], p[1] - a.centro[1]
    n = math.hypot(rx, ry) or 1.0
    dx, dy = direccion
    m = math.hypot(dx, dy) or 1.0
    return abs((rx * dx + ry * dy) / (n * m)) < 1e-3


@dataclass(frozen=True)
class CaraPlana:
    """La cuerda de un círculo: un agujero en D o un eje con cara plana."""

    segmento: int
    centro: tuple[float, float]
    radio: float
    distancia: float
    """Del centro del círculo a la cara."""
    cuerda: float
    angulo: float
    """Radianes: hacia dónde mira la normal de la cara, desde el centro."""


@dataclass(frozen=True)
class Construccion:
    arcos: tuple[int, ...]
    tangentes: tuple[int, ...]
    """Tramos tangentes a los dos arcos que unen: no llevan longitud."""
    caras_planas: tuple[CaraPlana, ...]
    rectos: tuple[int, ...]
    """Tramos libres: necesitan su longitud."""


def construccion(perfil: Perfil) -> Construccion:
    arcos = [i for i, e in enumerate(perfil) if isinstance(e, Arco)]
    tangentes, caras, rectos = [], [], []
    for i, e in enumerate(perfil):
        if not isinstance(e, Segmento):
            continue
        direccion = (e.b[0] - e.a[0], e.b[1] - e.a[1])
        largo = math.hypot(*direccion)
        cuerda_de = [
            perfil[j]
            for j in arcos
            if _en_arco(e.a, perfil[j]) and _en_arco(e.b, perfil[j])  # type: ignore[arg-type]
        ]
        if cuerda_de:
            a: Arco = cuerda_de[0]  # type: ignore[assignment]
            mx, my = (e.a[0] + e.b[0]) / 2, (e.a[1] + e.b[1]) / 2
            distancia = math.dist((mx, my), a.centro)
            angulo = math.atan2(my - a.centro[1], mx - a.centro[0])
            caras.append(CaraPlana(i, a.centro, a.radio, distancia, largo, angulo))
            continue
        en_a = [
            j for j in arcos if _en_arco(e.a, perfil[j]) and _tangente_en(e.a, direccion, perfil[j])
        ]  # type: ignore[arg-type]
        en_b = [
            j for j in arcos if _en_arco(e.b, perfil[j]) and _tangente_en(e.b, direccion, perfil[j])
        ]  # type: ignore[arg-type]
        if en_a and en_b:
            tangentes.append(i)
        else:
            rectos.append(i)
    return Construccion(tuple(arcos), tuple(tangentes), tuple(caras), tuple(rectos))


# ---------------------------------------------------------------------------
# Lo que la ficha rotula, y el cruce
# ---------------------------------------------------------------------------

CLASES = (
    "diametro",
    "radio",
    "centro",
    "longitud",
    "tangente",
    "cara_distancia",
    "cara_cuerda",
    "cara_lado",
    "conjunto",
)


@dataclass(frozen=True)
class Cota:
    """Una cota que la ficha rotula, con lo que cubre."""

    clase: str
    texto: str
    """Lo que se lee en la hoja; el test lo busca en el PDF."""
    variable: str = ""
    referencia: bool = False
    """Una cota de referencia, entre paréntesis: derivada, no se fabrica a
    ella y no tiene variable que teclear."""
    valor: float = 0.0
    """mm de una longitud o un radio, o la posición de un centro."""
    en: tuple[float, float] = (0.0, 0.0)
    """El centro que sitúa, o el punto de referencia de la cota."""
    segmento: int = -1
    """El tramo del perfil que cubre, si cubre uno."""


@dataclass
class Acotacion:
    """Todo lo que la ficha de una pieza rotula."""

    pieza: str
    cotas: list[Cota] = field(default_factory=list)


def faltas(perfil: Perfil, acotacion: Acotacion) -> list[str]:
    """Lo que el perfil necesita y la ficha no da. Vacía: dibujable."""
    salida = []
    c = construccion(perfil)
    radios = [k.valor for k in acotacion.cotas if k.clase == "radio"]
    radios += [k.valor / 2 for k in acotacion.cotas if k.clase == "diametro"]
    centros = [(0.0, 0.0)] + [k.en for k in acotacion.cotas if k.clase == "centro"]
    for i in c.arcos:
        a: Arco = perfil[i]  # type: ignore[assignment]
        donde = f"R{a.radio:.3g} en ({a.centro[0]:.3g}, {a.centro[1]:.3g})"
        if not any(abs(a.radio - r) < 0.011 for r in radios):
            salida.append(f"{acotacion.pieza}: arco {donde} sin cota de radio")
        if not any(_cerca(a.centro, p) for p in centros):
            salida.append(f"{acotacion.pieza}: arco {donde} con el centro sin situar")
    cubiertos = {k.segmento for k in acotacion.cotas if k.clase in ("tangente", "longitud")}
    for i in c.tangentes + c.rectos:
        if i not in cubiertos:
            e: Segmento = perfil[i]  # type: ignore[assignment]
            salida.append(
                f"{acotacion.pieza}: tramo de {math.dist(e.a, e.b):.3g} sin longitud ni tangencia"
            )
    for cara in c.caras_planas:
        tiene = {k.clase for k in acotacion.cotas if k.segmento == cara.segmento}
        for clase in ("cara_distancia", "cara_cuerda", "cara_lado"):
            if clase not in tiene:
                salida.append(f"{acotacion.pieza}: cara plana sin {clase.removeprefix('cara_')}")
    for k in acotacion.cotas:
        if k.clase in ("tangente", "cara_lado"):
            continue
        if not k.variable and not k.referencia:
            salida.append(
                f"{acotacion.pieza}: cota {k.texto} sin variable y sin marcar de referencia"
            )
    return salida


__all__ = [
    "Acotacion",
    "CaraPlana",
    "Construccion",
    "Cota",
    "construccion",
    "faltas",
    "perfil_de",
]
