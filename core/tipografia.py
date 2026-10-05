"""Escribir un texto con una fuente monotrazo. C0 · la puerta de entrada.

**Qué problema resuelve.** El compilador quiere una `Escritura`: trazos
en orden, con el lápiz apoyado. Eso es justo lo que da un canvas y lo que
NO da una imagen ni una fuente normal —el contorno de una «o» son dos
círculos cerrados, y el trazo de la pluma es el anillo que hay entre
ellos—. Una fuente **monotrazo** es la excepción: sus glifos ya son
líneas centrales, dibujadas para recorrerlas con una pluma, que es
exactamente lo que hace esta máquina.

Así que escribir un texto no necesita visión por computador: necesita la
fuente correcta.

**Puro, como todo `core/`.** La fuente entra como dato ya cargado; de
leerla del disco se encarga quien llame. Y nada de modelos de lenguaje:
la regla 4 pide mismo input, misma geometría, byte a byte.

**Unidades.** La fuente viene en sus propias unidades enteras y con la y
hacia abajo, que es como se distribuye desde 1967. Aquí se convierte una
vez a metros con la y hacia arriba, y no se vuelve a tocar: SI dentro.
"""

from __future__ import annotations

import itertools
import math
import unicodedata
from dataclasses import dataclass

from pydantic import BaseModel, ConfigDict, Field

from core.errors import LetraDesconocida
from core.escritura import Escritura, Trazo
from core.units import Longitud, Metros

PuntoDeFuente = tuple[float, float]
"""La fuente de 1967 es entera —venía en tarjetas perforadas—, pero un
acento compuesto se escala y no lo es. Redondear a entero movería la marca
un noveno de altura de x, que se ve."""

ENLACE = 0.5
"""Hasta dónde se enlazan dos trazos seguidos, en alturas de x.

**Medido sobre la fuente, no elegido.** En la Hershey cursiva los huecos
entre trazos consecutivos de una palabra caen en dos grupos separados:
los de 0 a 0,46 alturas de x —que son los enlaces que la letra inglesa
ya trae dibujados— y los de 0,8 en adelante, que son levantadas de
verdad: el punto de una i, el salto a otra palabra. Medio es el valle
entre los dos.

Importa más de lo que parece: **cada vuelo del lápiz se come grados de
la vuelta del árbol**, así que enlazar o no decide si una frase cabe.
"""


HUECO_ENTRE_RENGLONES = 0.3
"""Aire entre lo más bajo de un renglón y lo más alto del siguiente, en
alturas de x.

**El interlineado no se elige, se mide.** Lo que no puede pasar es que una
mayúscula del renglón de abajo se meta en la «g» del de arriba, así que la
distancia entre líneas base sale de lo que de verdad miden las letras que
hay en el texto —ascendente más descendente— y esto es solo el hueco que
queda en medio. En la Hershey cursiva el ascendente llega a 2,78 alturas de
x y el descendente a 1,33, así que con mayúsculas y jotas el salto ronda las
4,4.

Tres décimas porque tiene que verse en el papel: con dos renglones en una
caja de 30 mm la altura de x acaba rondando los 5 mm, y 0,3 de eso son
milímetro y medio de blanco. Es un mínimo para que se lea, no un gusto
tipográfico.
"""


@dataclass(frozen=True)
class Composicion:
    """Un texto compuesto, y qué trazos son de cada renglón.

    Van juntos porque se calculan juntos y por separado se desincronizan: la
    agrupación se hace **después** de tirar los trazos que no valen, así que
    unos índices calculados aparte apuntarían a otra cosa.
    """

    escritura: Escritura
    renglones: tuple[tuple[int, ...], ...]
    """Los índices de los trazos de cada renglón, de arriba abajo. Es lo que
    `compile.renglones` necesita para hacer un cartucho por renglón."""
    interlineado: Longitud
    """Lo que hay entre dos líneas base. Cero con un solo renglón."""


class Glifo(BaseModel):
    """Una letra en unidades de la fuente, con la y hacia abajo."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    lado_izquierdo: int
    """Dónde empieza el dibujo respecto del punto de inserción."""
    avance: int
    """Cuánto corre el cursor hasta la letra siguiente."""
    trazos: list[list[PuntoDeFuente]]
    """Vacío en el espacio, que avanza y no dibuja."""


class Fuente(BaseModel):
    """Una fuente monotrazo entera. Es dato: un JSON en `docs/fuentes/`."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    nombre: str = Field(min_length=1)
    procedencia: str = Field(min_length=1)
    """De dónde sale y con qué licencia. Va en la ficha del pedido."""
    linea_base: float
    """La y de la línea base en unidades de fuente. Hacia abajo, así que
    es positiva y las mayúsculas quedan por encima, en negativo."""
    altura_mayuscula: float
    altura_de_x: float
    glifos: dict[str, Glifo]

    def faltan(self, texto: str) -> list[str]:
        """Los caracteres distintos que esta fuente no sabe dibujar.

        Normaliza antes de mirar: «á» se teclea de dos maneras y un
        portapapeles de macOS manda la que no es un solo carácter.
        """
        return sorted({c for c in unicodedata.normalize("NFC", texto) if c not in self.glifos})


_LETRAS: dict[str, tuple[str, str]] = {
    # Marca: las letras sin acento y las mismas con él, emparejadas
    # posición a posición. Dos cadenas en vez de un diccionario para que un
    # hueco se vea de un vistazo, y `strict=True` al emparejarlas para que
    # añadir una sola de las dos no cuele.
    "agudo": ("aeiouyAEIOUY", "áéíóúýÁÉÍÓÚÝ"),
    "grave": ("aeiouAEIOU", "àèìòùÀÈÌÒÙ"),
    "circunflejo": ("aeiouAEIOU", "âêîôûÂÊÎÔÛ"),
    "dieresis": ("aeiouyAEIOU", "äëïöüÿÄËÏÖÜ"),
    "tilde": ("anoANO", "ãñõÃÑÕ"),
    "cedilla": ("cC", "çÇ"),
}

ACENTOS: dict[str, tuple[str, str]] = {
    acentuada: (base, marca)
    for marca, (bases, acentuadas) in _LETRAS.items()
    for base, acentuada in zip(bases, acentuadas, strict=True)
}
"""Letra acentuada -> de qué letra y qué marca se compone.

**Por qué hay que componerlas.** La Hershey se distribuye con los 96
caracteres del ASCII y ninguna de sus 32 variantes trae una sola letra
acentuada. Sin esto la máquina no escribe «Begoña», ni «Sebastià», ni
«Anaïs» —medio listín de nombres de aquí— y la fuente se queja de una
letra que el cliente ha escrito bien.

**Y por qué se componen y no se dibujan.** Regla 4: la geometría de
producción no sale de un modelo de lenguaje. Cada marca es un trazo que
la fuente **ya tiene** y cada cota de colocación está medida sobre la
propia fuente; aquí solo se dice qué lleva cada letra encima, que es
ortografía y no geometría.

No hay circunflejo en castellano ni en catalán; va porque la marca sale
de la misma fuente que el agudo y el grave y porque un «Benoît» no tiene
por qué romper un pedido.
"""

MARCAS_DE_LA_FUENTE = "'^\"~,i"
"""Los glifos de los que sale toda la tinta de los acentos.

El `'` da el **largo** de una marca; el `^`, la **inclinación** del agudo y
del grave —son sus dos ramas, que la fuente dibuja simétricas—; las
comillas, la **separación** de la diéresis; el `~`, la onda; la `,`, la
cedilla; y la `i`, el **punto**, que es la única marca que una fuente
monotrazo dibuja ya sobre una minúscula y de la que salen por eso las dos
cotas de colocación.
"""

DECIMALES = 3
"""A cuántos decimales de unidad de fuente se redondea un acento compuesto.

La fuente de 1967 es entera porque venía en tarjetas perforadas; una marca
escalada no lo es. Se redondea para que el archivo se pueda leer y para que
el glifo que compone el núcleo y el que hay en el disco sean **el mismo**,
comparables con un igual y no con una tolerancia. A tamaño de tarjeta una
milésima de unidad es media micra.
"""


def _caja(trazos: list[list[PuntoDeFuente]]) -> tuple[float, float, float, float]:
    """x mínima, x máxima, y mínima, y máxima de la tinta."""
    xs = [x for t in trazos for x, _ in t]
    ys = [y for t in trazos for _, y in t]
    return min(xs), max(xs), min(ys), max(ys)


def _largo(trazo: list[PuntoDeFuente]) -> float:
    return sum(math.dist(a, b) for a, b in itertools.pairwise(trazo))


def _mover(trazos: list[list[PuntoDeFuente]], dx: float, dy: float) -> list[list[PuntoDeFuente]]:
    return [[(x + dx, y + dy) for x, y in t] for t in trazos]


def _pendiente(trazo: list[PuntoDeFuente]) -> float:
    """Cuánto sube el trazo por cada unidad que avanza, con la y hacia
    arriba. Positiva en un acento agudo y negativa en uno grave."""
    return -(trazo[-1][1] - trazo[0][1]) / (trazo[-1][0] - trazo[0][0])


def _escalar(trazo: list[PuntoDeFuente], factor: float) -> list[PuntoDeFuente]:
    """Encoge el trazo hacia su primer punto, que en el `^` es el vértice."""
    x0, y0 = trazo[0]
    return [(x0 + (x - x0) * factor, y0 + (y - y0) * factor) for x, y in trazo]


def _sobre_el_alto_de_x(glifo: Glifo, fuente: Fuente) -> list[list[PuntoDeFuente]]:
    """Los trazos del glifo que quedan **enteros** por encima del alto de la x.

    Es el punto de la i y el de la j, y nada más: el resto de lo que sube
    —la barra de la t, el asta de la b— cruza la línea. Se busca así y no
    por el número de trazo porque un índice es justo lo que se equivoca en
    silencio al cambiar de fuente.
    """
    tope = fuente.linea_base - fuente.altura_de_x
    return [list(t) for t in glifo.trazos if all(y < tope for _, y in t)]


def _marcas(fuente: Fuente) -> dict[str, list[list[PuntoDeFuente]]]:
    """Las cinco marcas, en tinta de la propia fuente y sin colocar."""
    if faltan := sorted({c for c in MARCAS_DE_LA_FUENTE if c not in fuente.glifos}):
        raise LetraDesconocida(
            f"la fuente «{fuente.nombre}» no puede dar acentos: le faltan "
            + ", ".join(f"«{c}»" for c in faltan)
            + ". De esos glifos sale toda la tinta de las marcas."
        )

    puntos = _sobre_el_alto_de_x(fuente.glifos["i"], fuente)
    if len(puntos) != 1:
        raise LetraDesconocida(
            f"en la fuente «{fuente.nombre}» la «i» tiene {len(puntos)} trazos "
            "sobre el alto de la x y hace falta exactamente uno: el punto."
        )
    punto = puntos[0]

    ramas = [list(t) for t in fuente.glifos["^"].trazos]
    if len(ramas) != 2 or ramas[0][0] != ramas[1][0]:
        raise LetraDesconocida(
            f"en la fuente «{fuente.nombre}» el «^» no son dos ramas que salgan "
            "del mismo vértice, que es de donde se sacan el agudo y el grave."
        )
    # El agudo sube hacia la derecha y el grave baja. Se eligen por la
    # inclinación y no por el orden en que la fuente las guarda, que es lo
    # que convertiría un acento en el otro sin que nada protestara. La y de
    # la fuente va hacia abajo, de ahí el signo.
    largo_de_marca = sum(_largo(list(t)) for t in fuente.glifos["'"].trazos)
    ramas = [_escalar(r, largo_de_marca / _largo(r)) for r in ramas]
    agudo, grave = sorted(ramas, key=_pendiente, reverse=True)

    comillas = [_caja([list(t)]) for t in fuente.glifos['"'].trazos]
    separacion = abs(comillas[1][0] - comillas[0][0])

    return {
        "agudo": [agudo],
        "grave": [grave],
        # Las dos ramas salen del vértice, así que son un solo recorrido de
        # pluma: subir por una y bajar por la otra. Dejarlas sueltas haría
        # levantar el lápiz en lo alto del acento para nada.
        "circunflejo": [list(reversed(agudo)) + grave[1:]],
        # Dos puntos de la i, no las comillas: en esta fuente miden siete
        # unidades de alto y sobre una «u» se leerían como un doble prima.
        # De las comillas se toma solo la separación.
        "dieresis": _mover([punto], -separacion / 2, 0.0) + _mover([punto], separacion / 2, 0.0),
        # El `~` son dos pasadas de la misma onda —mismo largo, mismo
        # centro—, que es como se engorda un trazo con pluma. La segunda
        # dibujaría lo mismo otra vez y costaría una levantada.
        "tilde": [list(fuente.glifos["~"].trazos[0])],
        "cedilla": [list(t) for t in fuente.glifos[","].trazos],
    }


def acentuar(fuente: Fuente) -> dict[str, Glifo]:
    """Los glifos acentuados que esta fuente puede componer, por su cuenta.

    Se compone **una vez**, al extraer la fuente, y el resultado se congela
    en `docs/fuentes/`: la fuente sigue siendo dato y un pedido de dentro de
    cinco años sale igual aunque esta función cambie. Un test cruza las dos
    cosas.

    La regla entera son dos cotas, y las dos están **medidas sobre el punto
    de la i**, que es la única marca que la fuente dibuja ya sobre una
    minúscula: va centrada sobre la tinta de la letra, y su parte de abajo
    queda tan por encima de la letra como el punto lo está del alto de la x.
    La cedilla es la excepción y cuelga de la línea base, sin hueco: separada
    se lee como una coma suelta detrás.
    """
    marcas = _marcas(fuente)
    tope = fuente.linea_base - fuente.altura_de_x
    hueco = tope - _caja(marcas["dieresis"])[3]

    compuestos: dict[str, Glifo] = {}
    for acentuada, (letra, marca) in ACENTOS.items():
        if (base := fuente.glifos.get(letra)) is None:
            continue
        # El punto de la i se va: lo sustituye el acento, y por eso «í»
        # cuesta exactamente lo mismo que «i».
        sobran = _sobre_el_alto_de_x(base, fuente)
        trazos = [list(t) for t in base.trazos if list(t) not in sobran]
        bx0, bx1, by0, _ = _caja(trazos)
        mx0, mx1, my0, my1 = _caja(marcas[marca])
        dx = (bx0 + bx1) / 2 - (mx0 + mx1) / 2
        dy = (fuente.linea_base - my0) if marca == "cedilla" else (by0 - hueco) - my1
        puestos = _mover(marcas[marca], dx, dy)
        compuestos[acentuada] = Glifo(
            lado_izquierdo=base.lado_izquierdo,
            avance=base.avance,
            # La marca va **delante**, que es donde la fuente pone el punto
            # de la i. Así «í» es la «i» con el punto cambiado por el acento
            # en el mismo sitio del recorrido, y cuesta exactamente igual.
            trazos=[
                [(round(x, DECIMALES), round(y, DECIMALES)) for x, y in t] for t in puestos + trazos
            ],
        )
    return compuestos


def _trazos_colocados(texto: str, fuente: Fuente, escala: float) -> list[list[tuple[float, float]]]:
    """Los glifos puestos en fila, ya en metros y con la y hacia arriba."""
    cursor, salida = 0.0, []
    for letra in texto:
        glifo = fuente.glifos[letra]
        for trazo in glifo.trazos:
            salida.append(
                [
                    ((x - glifo.lado_izquierdo + cursor) * escala, (fuente.linea_base - y) * escala)
                    for x, y in trazo
                ]
            )
        cursor += glifo.avance
    return salida


def _enlazar(
    trazos: list[list[tuple[float, float]]], hasta: float
) -> list[list[tuple[float, float]]]:
    """Une los trazos seguidos cuyo hueco no llega a `hasta`, en metros.

    Con `hasta` a cero se ve la fuente sin sus enlaces, pero **un hueco de
    longitud cero se une igual**: no es un enlace que la letra inglesa
    traiga dibujado, es el mismo recorrido de pluma guardado en dos trazos,
    que es como la fuente almacena una «n». Dejarlos sueltos hace levantar
    el lápiz y bajarlo en el mismo punto: 16° de la vuelta —el doble del
    arco de levantamiento— para dibujar exactamente lo mismo.
    """
    if not trazos:
        return trazos
    salida = [list(trazos[0])]
    for trazo in trazos[1:]:
        if math.dist(salida[-1][-1], trazo[0]) <= hasta:
            # El punto repetido no aporta nada y deja una cuerda de
            # longitud cero, que es lo que `redondear_esquinas` no sabe
            # mirar.
            salida[-1].extend(trazo[1:] if math.dist(salida[-1][-1], trazo[0]) == 0.0 else trazo)
        else:
            salida.append(list(trazo))
    return salida


def _vale(trazo: list[tuple[float, float]]) -> bool:
    """Un trazo de un punto o de longitud cero no se puede reparametrizar."""
    if len(trazo) < 2:
        return False
    return any(a != b for a, b in itertools.pairwise(trazo))


def _comprobar(texto: str, fuente: Fuente) -> None:
    """Que haya algo que escribir y que la fuente sepa escribirlo."""
    if not texto.strip():
        raise ValueError("el texto está vacío: no hay nada que escribir")
    # El salto de línea no es un carácter de la fuente: es maquetación.
    if faltan := fuente.faltan(texto.replace("\n", "")):
        raise LetraDesconocida(
            f"la fuente «{fuente.nombre}» no tiene "
            + ", ".join(f"«{c}»" for c in faltan)
            + ". Escríbelo con los caracteres que sí tiene, o añádelos a la fuente."
        )


def componer(
    texto: str,
    fuente: Fuente,
    altura_de_x: Longitud,
    enlace: float = ENLACE,
    nombre: str = "",
    hueco: float = HUECO_ENTRE_RENGLONES,
) -> Composicion:
    """El texto en trazos, repartido en renglones por sus saltos de línea.

    `altura_de_x` es lo que medirá una «o», y es la única escala que se
    da: el resto lo recoloca `encajar` cuando la frase entra en la caja de
    escritura. `enlace` va en alturas de x, no en metros, para que una
    frase grande y una pequeña se enlacen igual.

    **Un renglón es un cartucho, no una línea de texto.** Una vuelta del
    árbol escribe un renglón y hay que cambiar el cartucho para el
    siguiente, así que partir una frase cuesta tres levas más. Aquí solo se
    compone; quién parte y dónde es decisión de quien hace el pedido.

    **Se compone entero y a una sola escala.** Si cada renglón se escalara
    por su cuenta, las letras de «Feliz» no medirían lo que las de
    «cumpleaños». Por eso la agrupación sale de aquí y no de compilar tres
    veces por separado.
    """
    texto = unicodedata.normalize("NFC", texto)
    _comprobar(texto, fuente)

    escala = float(altura_de_x) / fuente.altura_de_x
    # Enlazar **por renglón**: en la lista plana, el último trazo de uno y
    # el primero del siguiente son consecutivos, y con un enlace holgado se
    # unirían en una raya en diagonal que además dejaría un trazo en dos
    # renglones a la vez.
    lineas = [
        [
            t
            for t in _enlazar(_trazos_colocados(linea, fuente, escala), enlace * float(altura_de_x))
            if _vale(t)
        ]
        for linea in texto.split("\n")
    ]
    # Una línea en blanco no es un renglón: sería un cartucho con tres levas
    # lisas, que se cobra y no escribe nada.
    lineas = [linea for linea in lineas if linea]
    if not lineas:
        raise ValueError(f"«{texto}» no deja ni un trazo que dibujar")

    salto = _interlineado(lineas, hueco * float(altura_de_x))
    trazos: list[Trazo] = []
    renglones: list[tuple[int, ...]] = []
    for numero, linea in enumerate(lineas):
        primero = len(trazos)
        trazos += [
            Trazo(puntos=[(Metros(x), Metros(y - numero * salto)) for x, y in t]) for t in linea
        ]
        renglones.append(tuple(range(primero, len(trazos))))
    return Composicion(
        escritura=Escritura(nombre=nombre or texto.replace("\n", " "), trazos=trazos),
        renglones=tuple(renglones),
        interlineado=Metros(salto if len(lineas) > 1 else 0.0),
    )


def huecos(
    texto: str,
    fuente: Fuente,
    altura_de_x: Longitud,
) -> tuple[tuple[float, ...], ...]:
    """Qué separa cada trazo del siguiente, en alturas de x, por renglón.

    Es lo que el enlace decide: un hueco por debajo se une y uno por
    encima se queda como levantada. Sirve para **enseñar la decisión** en
    vez de pedir que se adivine arrastrando un deslizante.

    **No dependen del enlace**, y eso no es casualidad: `_enlazar` mide
    siempre contra el final del trazo crudo anterior —unir dos trazos deja
    como final el del segundo—, así que unir uno no mueve el hueco
    siguiente. Por eso las marcas del deslizante se quedan quietas
    mientras se arrastra.

    En alturas de x, como el propio enlace, para que una frase grande y
    una pequeña se midan igual. Y por renglón: entre dos renglones no hay
    nada que enlazar, son cartuchos distintos.
    """
    texto = unicodedata.normalize("NFC", texto)
    escala = float(altura_de_x) / fuente.altura_de_x
    _comprobar(texto, fuente)
    salida: list[tuple[float, ...]] = []
    for linea in texto.split("\n"):
        trazos = [t for t in _trazos_colocados(linea, fuente, escala) if _vale(t)]
        salida.append(
            tuple(
                math.dist(a[-1], b[0]) / float(altura_de_x) for a, b in itertools.pairwise(trazos)
            )
        )
    return tuple(salida)


def _interlineado(lineas: list[list[list[tuple[float, float]]]], hueco: float) -> float:
    """Lo que hay que bajar de una línea base a la siguiente, en metros.

    Sale de lo que **miden las letras que hay**, no de un número elegido:
    el descendente más largo de todo el texto más el ascendente más alto,
    más el hueco. Se usa el mismo salto en todos los pares para que las
    líneas base queden en rejilla; calcularlo par a par daría un renglón
    pegado y el siguiente suelto según lleven o no una jota.
    """
    ys = [y for linea in lineas for trazo in linea for _, y in trazo]
    if not ys:
        return 0.0
    return (max(ys) - min(ys)) + hueco


def escribir(
    texto: str,
    fuente: Fuente,
    altura_de_x: Longitud,
    enlace: float = ENLACE,
    nombre: str = "",
) -> Escritura:
    """El texto de una tirada, sin partir en renglones.

    Es `componer` visto por un lado. No tiene implementación propia a
    propósito: dos caminos que componen lo mismo se separan.
    """
    return componer(texto, fuente, altura_de_x, enlace, nombre).escritura


__all__ = [
    "ACENTOS",
    "DECIMALES",
    "ENLACE",
    "HUECO_ENTRE_RENGLONES",
    "MARCAS_DE_LA_FUENTE",
    "Composicion",
    "Fuente",
    "Glifo",
    "acentuar",
    "componer",
    "escribir",
    "huecos",
]
