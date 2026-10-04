"""Maquetación de la plantilla a escala 1:1, en milímetros.

Aquí se cruza la frontera de unidades del proyecto: entra geometría en metros
y sale una lámina en milímetros. Es el único sitio donde ocurre.

La maquetación está separada del PDF a propósito. Una `Lamina` es una lista de
primitivas con coordenadas exactas, así que los invariantes que importan —que
el cuadro mida 100 mm, que las teselas solapen lo declarado, que cada pieza
lleve sus siete metadatos— se comprueban sobre datos, sin abrir un PDF ni
depender de cómo lo escriba la biblioteca de turno. Y la misma lámina podrá
salir a SVG el día que haga falta.

El recorrido es: se maqueta todo sobre **una hoja virtual** del tamaño que
pida el contenido, y después esa hoja se sirve entera —para plóter A0 o A1— o
se trocea en páginas del formato elegido.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Literal

from core.units import Longitud, Metros, a_mm
from emit.pieza import Pieza

LADO_CALIBRACION = 100.0
"""Milímetros. El cuadro que delata una impresión escalada."""

ALTO_CABECERA = 118.0
"""Milímetros reservados arriba de cada página: cuadro de calibración,
advertencia de impresión y metadatos. Cuesta espacio y no es negociable: una
plantilla 1:1 sin forma de comprobar la escala es peligrosa."""

MARGEN = 10.0
SOLAPE = 12.0
"""Milímetros que comparten dos teselas contiguas, para poder pegarlas."""

SEPARACION = 8.0
"""Milímetros entre dos piezas agrupadas en la misma hoja. No es estético:
una sierra de cinta necesita entrada y salida, y dos contornos pegados
obligan a cortar dos veces por el mismo sitio."""

ALTO_ROTULO = 9.0
"""Milímetros reservados bajo cada pieza agrupada para su rótulo de dos
líneas. En una hoja con cinco piezas, la cabecera ya no dice de cuál habla.
Si el rótulo se parte en más líneas, cada una añade `ALTO_LINEA_ROTULO`."""

ANCHO_MEDIO_CARACTER = 0.55
"""Ancho de un carácter como fracción de su altura, por lo alto. Sirve para
reservar sitio sin que esta capa tenga que saber de fuentes ni de PDF:
pasarse es inofensivo, quedarse corto saca el rótulo de la hoja."""

TipoTrazo = Literal["corte", "taladro", "referencia", "oculta", "marca", "cajetin"]


class Formato(StrEnum):
    """Formatos de papel, en milímetros. A0 y A1 son para plóter."""

    A4 = "A4"
    A3 = "A3"
    A2 = "A2"
    A1 = "A1"
    A0 = "A0"

    @property
    def medidas(self) -> tuple[float, float]:
        """Ancho y alto en milímetros, en vertical."""
        return {
            Formato.A4: (210.0, 297.0),
            Formato.A3: (297.0, 420.0),
            Formato.A2: (420.0, 594.0),
            Formato.A1: (594.0, 841.0),
            Formato.A0: (841.0, 1189.0),
        }[self]


@dataclass(frozen=True)
class Trazo:
    """Una polilínea en coordenadas de página, en milímetros."""

    tipo: TipoTrazo
    puntos: tuple[tuple[float, float], ...]
    cerrado: bool = False


@dataclass(frozen=True)
class Circulo:
    tipo: TipoTrazo
    centro: tuple[float, float]
    radio: float


@dataclass(frozen=True)
class Texto:
    x: float
    y: float
    texto: str
    tamano: float = 3.0
    """Altura en milímetros. Por debajo de 2,5 no se lee impreso."""
    negrita: bool = False
    anclaje: Literal["izquierda", "centro"] = "izquierda"


@dataclass(frozen=True)
class Lamina:
    """Una página lista para imprimir, en milímetros."""

    ancho: float
    alto: float
    trazos: tuple[Trazo, ...] = ()
    circulos: tuple[Circulo, ...] = ()
    textos: tuple[Texto, ...] = ()
    indice: tuple[int, int] = (1, 1)
    """Número de tesela y total, para que se puedan ordenar al pegarlas."""
    escala: float = 1.0
    """1.0 es tamaño real. Una plantilla de corte **siempre** vale 1: se pega
    sobre el tablero y se corta por encima. Las vistas del dossier van a otra
    escala y por eso no pueden compartir documento con estas: quien tenga
    delante un papel con dos escalas acabará cortando por la equivocada."""


@dataclass
class _Acumulador:
    trazos: list[Trazo] = field(default_factory=list)
    circulos: list[Circulo] = field(default_factory=list)
    textos: list[Texto] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Bloques
# ---------------------------------------------------------------------------


def cuadro_de_calibracion(x: float, y: float) -> _Acumulador:
    """El cuadro de 100 × 100 mm con su leyenda.

    Es un cuadro y no una regla porque una regla solo delata el escalado en un
    eje. Algunas impresoras escalan distinto en x y en y, y eso deforma la
    pieza sin que se note en una sola dirección.
    """
    a = _Acumulador()
    lado = LADO_CALIBRACION
    a.trazos.append(
        Trazo(
            tipo="cajetin",
            puntos=((x, y), (x + lado, y), (x + lado, y + lado), (x, y + lado)),
            cerrado=True,
        )
    )
    # Marcas de 10 en 10 mm en los dos lados, para medir con una regla
    # cualquiera sin tener que apuntar al vértice exacto.
    for i in range(1, 10):
        d = i * 10.0
        largo = 4.0 if i % 5 else 7.0
        a.trazos.append(Trazo("cajetin", ((x + d, y), (x + d, y + largo))))
        a.trazos.append(Trazo("cajetin", ((x, y + d), (x + largo, y + d))))
    a.textos.append(Texto(x + lado / 2, y + lado / 2 + 2, "100 mm", 5.0, True, "centro"))
    a.textos.append(
        Texto(
            x + lado / 2,
            y + lado / 2 - 6,
            "si este cuadrado no mide 100 mm,",
            3.2,
            anclaje="centro",
        )
    )
    a.textos.append(
        Texto(x + lado / 2, y + lado / 2 - 11, "la impresión está escalada", 3.2, anclaje="centro")
    )
    return a


def cabecera(
    pieza: Pieza,
    ancho_pagina: float,
    alto_pagina: float,
    indice: tuple[int, int],
) -> _Acumulador:
    """Cuadro de calibración, advertencia de impresión y los siete metadatos."""
    a = _Acumulador()
    y0 = alto_pagina - ALTO_CABECERA
    a.trazos.append(Trazo("cajetin", ((MARGEN, y0), (ancho_pagina - MARGEN, y0))))

    calibracion = cuadro_de_calibracion(MARGEN, y0 + 8.0)
    a.trazos += calibracion.trazos
    a.textos += calibracion.textos

    x = MARGEN + LADO_CALIBRACION + 10.0
    y = alto_pagina - MARGEN - 6.0
    a.textos.append(Texto(x, y, f"{pieza.conjunto} · {pieza.nombre}", 5.0, True))
    # La advertencia va en dos líneas: en A4 esta columna tiene 90 mm y en una
    # sola línea se salía de la hoja. Un aviso cortado no avisa de nada.
    y -= 7.5
    a.textos.append(Texto(x, y, "IMPRIMIR AL 100 %,", 4.0, True))
    y -= 5.5
    a.textos.append(Texto(x, y, "SIN AJUSTAR A LA PÁGINA", 4.0, True))
    y -= 8.0
    for etiqueta, valor in (
        ("pieza", pieza.numero),
        ("conjunto", pieza.conjunto),
        ("material", pieza.material),
        ("espesor", f"{a_mm(pieza.espesor):.1f} mm"),
        ("cantidad", f"{pieza.cantidad}"),
        ("veta", pieza.veta.value),
        ("tamaño", f"{a_mm(pieza.ancho):.1f} × {a_mm(pieza.alto):.1f} mm"),
    ):
        a.textos.append(Texto(x, y, f"{etiqueta}:", 3.2))
        a.textos.append(Texto(x + 22.0, y, valor, 3.2, True))
        y -= 4.9
    if indice[1] > 1:
        y -= 2.5
        a.textos.append(Texto(x, y, f"hoja {indice[0]} de {indice[1]}", 4.0, True))
    return a


def _recortar(acumulado: _Acumulador, ancho: float, alto: float) -> _Acumulador:
    """Deja fuera lo que no toca la página.

    Al trocear, la pieza entera se dibuja en cada tesela con un
    desplazamiento distinto, así que casi todo cae fuera. Las líneas las
    recorta el propio PDF sin hacer daño, pero un rótulo a medio cortar es
    peor que ninguno: se lee mal y no dice a qué pieza pertenece. Los que
    quedan fuera aparecen enteros en la tesela vecina, que para eso solapan.
    """
    margen = 1.0

    def dentro(x: float, y: float) -> bool:
        return -margen <= x <= ancho + margen and -margen <= y <= alto + margen

    def toca(trazo: Trazo) -> bool:
        xs = [p[0] for p in trazo.puntos]
        ys = [p[1] for p in trazo.puntos]
        return (
            max(xs) >= -margen
            and min(xs) <= ancho + margen
            and (max(ys) >= -margen and min(ys) <= alto + margen)
        )

    return _Acumulador(
        trazos=[t for t in acumulado.trazos if toca(t)],
        circulos=[
            c
            for c in acumulado.circulos
            if dentro(c.centro[0] + c.radio, c.centro[1])
            or dentro(c.centro[0] - c.radio, c.centro[1])
        ],
        textos=[t for t in acumulado.textos if dentro(t.x, t.y)],
    )


def _marca_de_registro(x: float, y: float) -> list[Trazo]:
    """Cruz de alineación. Dos teselas contiguas la comparten."""
    brazo = 5.0
    return [
        Trazo("marca", ((x - brazo, y), (x + brazo, y))),
        Trazo("marca", ((x, y - brazo), (x, y + brazo))),
    ]


# ---------------------------------------------------------------------------
# Maquetación
# ---------------------------------------------------------------------------


def _primitivas_de_la_pieza(pieza: Pieza, dx: float, dy: float) -> _Acumulador:
    """Pasa la pieza a milímetros y la sitúa. Aquí y solo aquí se convierte."""
    a = _Acumulador()

    def mmp(p: tuple[Metros, Metros]) -> tuple[float, float]:
        return (a_mm(p[0]) + dx, a_mm(p[1]) + dy)

    a.trazos.append(Trazo("corte", tuple(mmp(p) for p in pieza.contorno), cerrado=True))

    for referencia in pieza.referencias:
        a.trazos.append(
            Trazo("referencia", tuple(mmp(p) for p in referencia.puntos), referencia.cerrada)
        )

    for taladro in pieza.taladros:
        centro = mmp(taladro.centro)
        radio = a_mm(taladro.diametro) / 2.0
        a.circulos.append(Circulo("taladro", centro, radio))
        brazo = radio + 3.0
        a.trazos.append(
            Trazo("taladro", ((centro[0] - brazo, centro[1]), (centro[0] + brazo, centro[1])))
        )
        a.trazos.append(
            Trazo("taladro", ((centro[0], centro[1] - brazo), (centro[0], centro[1] + brazo)))
        )
        a.textos.append(
            Texto(
                centro[0] + brazo + 1.5,
                centro[1] - 1.2,
                f"Ø{a_mm(taladro.diametro):.1f} {taladro.tolerancia}".rstrip(),
                2.8,
            )
        )

    if pieza.marca_fase is not None:
        centro = mmp(pieza.marca_fase)
        a.circulos.append(Circulo("marca", centro, 3.0))
        a.trazos += _marca_de_registro(*centro)
        a.textos.append(Texto(centro[0] + 5.0, centro[1] + 4.0, "FASE 0", 3.2, True))

    return a


def maquetar(
    pieza: Pieza,
    formato: Formato = Formato.A3,
    *,
    hoja_unica: bool = False,
) -> list[Lamina]:
    """De una pieza a las páginas que hay que imprimir.

    Con `hoja_unica` la página crece hasta caber entera, que es lo que quiere
    un plóter. Sin él, el contenido se trocea en páginas del formato pedido,
    con solape y marcas de registro para poder pegarlas.
    """
    ancho_pagina, alto_pagina = formato.medidas
    util_ancho = ancho_pagina - 2 * MARGEN
    util_alto = alto_pagina - ALTO_CABECERA - 2 * MARGEN

    ancho_pieza = a_mm(pieza.ancho)
    alto_pieza = a_mm(pieza.alto)

    if hoja_unica:
        ancho_pagina = max(ancho_pagina, ancho_pieza + 2 * MARGEN)
        alto_pagina = max(alto_pagina, alto_pieza + ALTO_CABECERA + 2 * MARGEN)
        util_ancho = ancho_pagina - 2 * MARGEN
        util_alto = alto_pagina - ALTO_CABECERA - 2 * MARGEN

    x0, _, _, y1 = pieza.limites
    columnas = max(1, _teselas(ancho_pieza, util_ancho))
    filas = max(1, _teselas(alto_pieza, util_alto))
    total = columnas * filas

    laminas: list[Lamina] = []
    for fila in range(filas):
        for columna in range(columnas):
            # Desplazamiento de la pieza para que a esta tesela le toque su
            # trozo. El solape se descuenta del avance, no del tamaño útil.
            # El origen es la esquina superior izquierda del área útil: la
            # fila 0 enseña la banda de arriba de la pieza y las siguientes
            # van bajando, que es como se leen y como se pegan.
            techo = alto_pagina - ALTO_CABECERA - MARGEN
            dx = MARGEN - a_mm(x0) - columna * (util_ancho - SOLAPE)
            dy = techo - a_mm(y1) + fila * (util_alto - SOLAPE)

            acumulado = _recortar(_primitivas_de_la_pieza(pieza, dx, dy), ancho_pagina, alto_pagina)
            indice = (fila * columnas + columna + 1, total)
            encabezado = cabecera(pieza, ancho_pagina, alto_pagina, indice)

            if total > 1:
                for marca_x in (MARGEN, ancho_pagina - MARGEN):
                    for marca_y in (MARGEN, MARGEN + util_alto):
                        acumulado.trazos += _marca_de_registro(marca_x, marca_y)

            laminas.append(
                Lamina(
                    ancho=ancho_pagina,
                    alto=alto_pagina,
                    trazos=tuple(acumulado.trazos + encabezado.trazos),
                    circulos=tuple(acumulado.circulos + encabezado.circulos),
                    textos=tuple(acumulado.textos + encabezado.textos),
                    indice=indice,
                )
            )
    return laminas


def _teselas(necesario: float, util: float) -> int:
    """Cuántas páginas hacen falta contando el solape entre contiguas."""
    if necesario <= util:
        return 1
    avance = util - SOLAPE
    if avance <= 0.0:
        raise ValueError(
            f"con un solape de {SOLAPE} mm no queda avance en una página útil de "
            f"{util:.1f} mm. Usa un formato mayor."
        )
    return int(-(-(necesario - util) // avance)) + 1


def cabe_en_una_hoja(pieza: Pieza, formato: Formato) -> bool:
    ancho_pagina, alto_pagina = formato.medidas
    return (
        a_mm(pieza.ancho) <= ancho_pagina - 2 * MARGEN
        and a_mm(pieza.alto) <= alto_pagina - ALTO_CABECERA - 2 * MARGEN
    )


def formato_minimo(pieza: Pieza) -> Formato | None:
    """El formato más pequeño donde la pieza cabe de una pieza, si hay alguno."""
    for formato in (Formato.A4, Formato.A3, Formato.A2, Formato.A1, Formato.A0):
        if cabe_en_una_hoja(pieza, formato):
            return formato
    return None


# ---------------------------------------------------------------------------
# Varias piezas en una hoja
# ---------------------------------------------------------------------------


def _ancho_estimado(texto: str, tamano: float) -> float:
    """Ancho aproximado de un rótulo, por lo alto.

    Deliberadamente generoso: esta capa no conoce la fuente —de eso sabe
    `emit/template.py`— y equivocarse por exceso solo deja hueco de más.
    """
    return len(texto) * ANCHO_MEDIO_CARACTER * tamano


def _recortar_texto(texto: str, ancho_max: float, tamano: float) -> str:
    """Corta una palabra que no cabe ni sola. Último recurso."""
    if _ancho_estimado(texto, tamano) <= ancho_max:
        return texto
    cabe = max(1, int(ancho_max / (ANCHO_MEDIO_CARACTER * tamano)) - 1)
    return texto[:cabe] + "…"


def _envolver(texto: str, ancho_max: float, tamano: float) -> list[str]:
    """Parte un rótulo en varias líneas para que quepa a lo ancho.

    Se envuelve en vez de recortar porque los metadatos de la pieza no son
    decorativos: quien recibe la hoja necesita el material y el espesor, y un
    rótulo cortado por el borde le obliga a preguntar a alguien que está en
    otro taller y en otro momento.
    """
    # Se parte por los separadores de campo cuando los hay: cortar
    # "POM 5 mm · 5.0 mm" entre "5" y "mm" deja una línea que no dice nada.
    separador = " · " if " · " in texto else " "
    lineas: list[str] = []
    actual = ""
    for palabra in texto.split(separador):
        tentativa = f"{actual}{separador}{palabra}" if actual else palabra
        if actual and _ancho_estimado(tentativa, tamano) > ancho_max:
            lineas.append(actual)
            actual = palabra
        else:
            actual = tentativa
    lineas.append(actual)
    return [_recortar_texto(linea, ancho_max, tamano) for linea in lineas]


ANCHO_ROTULO_MINIMO = 45.0
"""Milímetros que se reservan a lo ancho para el rótulo de una pieza chica.
Por debajo de esto el rótulo se parte en tantas líneas que ocupa más alto que
la propia pieza."""

ANCHO_ROTULO_MAXIMO = 80.0
"""Y por encima, una pieza estrecha acapararía media hoja."""

ALTO_LINEA_ROTULO = 4.2


def _lineas_de_rotulo(pieza: Pieza, ancho_max: float) -> list[tuple[str, float, bool]]:
    """Las líneas del rótulo: texto, cuerpo y negrita.

    El conjunto va arriba, en la cabecera, porque es el mismo para toda la
    hoja. Los otros seis viajan con su pieza: en una hoja con cinco contornos,
    saber que uno es de 5 mm y otro de 9 es lo que evita cortarlos del tablero
    equivocado.
    """
    titulo = f"{pieza.numero} · {pieza.nombre}"
    detalle = (
        f"{pieza.material} · {a_mm(pieza.espesor):.1f} mm · ×{pieza.cantidad} · "
        f"veta {pieza.veta.value}"
    )
    return [(linea, 3.2, True) for linea in _envolver(titulo, ancho_max, 3.2)] + [
        (linea, 2.8, False) for linea in _envolver(detalle, ancho_max, 2.8)
    ]


def _ancho_de_rotulo(pieza: Pieza) -> float:
    return min(max(a_mm(pieza.ancho), ANCHO_ROTULO_MINIMO), ANCHO_ROTULO_MAXIMO)


def _rotulo_de_pieza(pieza: Pieza, x: float, y: float) -> list[Texto]:
    ancho_max = _ancho_de_rotulo(pieza)
    return [
        Texto(x, y - i * ALTO_LINEA_ROTULO, linea, tamano, negrita)
        for i, (linea, tamano, negrita) in enumerate(_lineas_de_rotulo(pieza, ancho_max))
    ]


def _hueco(pieza: Pieza) -> tuple[float, float]:
    """Lo que ocupa una pieza agrupada: su caja, su rótulo y la separación."""
    ancho_rotulo = _ancho_de_rotulo(pieza)
    lineas = len(_lineas_de_rotulo(pieza, ancho_rotulo))
    alto_rotulo = ALTO_ROTULO + (lineas - 1) * ALTO_LINEA_ROTULO
    return max(a_mm(pieza.ancho), ancho_rotulo), a_mm(pieza.alto) + alto_rotulo


def cabecera_juego(
    conjunto: str,
    ancho_pagina: float,
    alto_pagina: float,
    indice: tuple[int, int],
    piezas: Sequence[Pieza],
) -> _Acumulador:
    """Cabecera de una hoja con varias piezas.

    Los metadatos de cada una van junto a ella, no aquí: una cabecera que
    hablara de cinco piezas a la vez no diría de cuál.
    """
    a = _Acumulador()
    y0 = alto_pagina - ALTO_CABECERA
    a.trazos.append(Trazo("cajetin", ((MARGEN, y0), (ancho_pagina - MARGEN, y0))))

    calibracion = cuadro_de_calibracion(MARGEN, y0 + 8.0)
    a.trazos += calibracion.trazos
    a.textos += calibracion.textos

    x = MARGEN + LADO_CALIBRACION + 10.0
    y = alto_pagina - MARGEN - 6.0
    a.textos.append(Texto(x, y, conjunto, 5.0, True))
    y -= 7.5
    a.textos.append(Texto(x, y, "IMPRIMIR AL 100 %,", 4.0, True))
    y -= 5.5
    a.textos.append(Texto(x, y, "SIN AJUSTAR A LA PÁGINA", 4.0, True))
    y -= 8.0
    a.textos.append(Texto(x, y, f"hoja {indice[0]} de {indice[1]}", 4.0, True))
    y -= 6.0
    a.textos.append(
        Texto(x, y, f"{len(piezas)} pieza{'s' if len(piezas) != 1 else ''} en esta hoja", 3.2)
    )
    # La lista de números es la hoja de recuento: al terminar de cortar se
    # comprueba contra ella que no falta ninguna sobre la mesa.
    ancho_columna = ancho_pagina - MARGEN - x
    for linea in _envolver(", ".join(p.numero for p in piezas), ancho_columna, 3.2)[:4]:
        y -= 4.6
        a.textos.append(Texto(x, y, linea, 3.2))
    return a


def _repartir(
    piezas: Sequence[Pieza], util_ancho: float, util_alto: float
) -> list[list[tuple[Pieza, float, float]]]:
    """Reparte las piezas en hojas, por estantes.

    Estante a estante, de más alta a más baja: es el reparto que usa
    cualquiera al colocar piezas sobre un tablero, y deja poco hueco cuando
    las alturas se parecen. **No resuelve el empaquetado óptimo**, que es un
    problema en sí y no toca todavía: aquí solo se trata de no gastar una hoja
    por cada arandela.

    Devuelve, por hoja, la lista de (pieza, x de la izquierda, y del techo).
    """
    ordenadas = sorted(piezas, key=lambda p: _hueco(p)[1], reverse=True)
    hojas: list[list[tuple[Pieza, float, float]]] = []
    actual: list[tuple[Pieza, float, float]] = []
    x = 0.0
    techo = util_alto
    alto_estante = 0.0

    for pieza in ordenadas:
        ancho, alto = _hueco(pieza)
        if x > 0.0 and x + SEPARACION + ancho > util_ancho:
            # No cabe en este estante: se abre el siguiente, más abajo.
            techo -= alto_estante + SEPARACION
            x, alto_estante = 0.0, 0.0
        if techo - alto < 0.0:
            # Tampoco cabe el estante en esta hoja.
            if actual:
                hojas.append(actual)
            actual, x, techo, alto_estante = [], 0.0, util_alto, 0.0
        avance = x if x == 0.0 else x + SEPARACION
        actual.append((pieza, avance, techo))
        x = avance + ancho
        alto_estante = max(alto_estante, alto)

    if actual:
        hojas.append(actual)
    return hojas


def maquetar_juego(
    piezas: Sequence[Pieza],
    formato: Formato = Formato.A3,
) -> list[Lamina]:
    """De un conjunto de piezas a las hojas que hay que imprimir.

    Las que caben comparten hoja; las que no, se trocean aparte con
    `maquetar()`, cada una con su cabecera completa. Una hoja por pieza
    desperdicia papel y obliga a barajar treinta folios en el taller.
    """
    if not piezas:
        raise ValueError("no hay piezas que maquetar")

    ancho_pagina, alto_pagina = formato.medidas
    util_ancho = ancho_pagina - 2 * MARGEN
    util_alto = alto_pagina - ALTO_CABECERA - 2 * MARGEN
    techo_pagina = alto_pagina - ALTO_CABECERA - MARGEN

    caben = [p for p in piezas if cabe_en_una_hoja(p, formato)]
    grandes = [p for p in piezas if not cabe_en_una_hoja(p, formato)]

    conjuntos = sorted({p.conjunto for p in piezas})
    nombre = conjuntos[0] if len(conjuntos) == 1 else f"{len(conjuntos)} conjuntos"

    repartidas = _repartir(caben, util_ancho, util_alto)
    total = len(repartidas)

    laminas: list[Lamina] = []
    for numero, hoja in enumerate(repartidas, start=1):
        acumulado = _Acumulador()
        for pieza, x, techo in hoja:
            x0, _, _, y1 = pieza.limites
            dx = MARGEN + x - a_mm(x0)
            dy = techo_pagina - (util_alto - techo) - a_mm(y1)
            colocada = _primitivas_de_la_pieza(pieza, dx, dy)
            acumulado.trazos += colocada.trazos
            acumulado.circulos += colocada.circulos
            acumulado.textos += colocada.textos
            acumulado.textos += _rotulo_de_pieza(
                pieza, MARGEN + x, dy + a_mm(pieza.limites[1]) - 4.5
            )

        indice = (numero, total)
        encabezado = cabecera_juego(
            nombre, ancho_pagina, alto_pagina, indice, [pieza for pieza, _, _ in hoja]
        )
        recortado = _recortar(acumulado, ancho_pagina, alto_pagina)
        laminas.append(
            Lamina(
                ancho=ancho_pagina,
                alto=alto_pagina,
                trazos=tuple(recortado.trazos + encabezado.trazos),
                circulos=tuple(recortado.circulos + encabezado.circulos),
                textos=tuple(recortado.textos + encabezado.textos),
                indice=indice,
            )
        )

    for pieza in grandes:
        laminas += maquetar(pieza, formato)
    return laminas


def formato_minimo_juego(piezas: Sequence[Pieza]) -> Formato | None:
    """El formato más pequeño donde **todas** las piezas caben sin trocear.

    No busca el que gasta menos hojas: busca el que evita pegar papeles, que
    es lo que de verdad estropea una plantilla.
    """
    for formato in (Formato.A4, Formato.A3, Formato.A2, Formato.A1, Formato.A0):
        if all(cabe_en_una_hoja(pieza, formato) for pieza in piezas):
            return formato
    return None


__all__ = [
    "ALTO_CABECERA",
    "ALTO_ROTULO",
    "LADO_CALIBRACION",
    "MARGEN",
    "SEPARACION",
    "SOLAPE",
    "Circulo",
    "Formato",
    "Lamina",
    "Longitud",
    "Texto",
    "Trazo",
    "cabe_en_una_hoja",
    "cuadro_de_calibracion",
    "formato_minimo",
    "formato_minimo_juego",
    "maquetar",
    "maquetar_juego",
]
