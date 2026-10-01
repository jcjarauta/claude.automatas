"""Perfiles de las piezas prismáticas de la plataforma, y su DXF.

El reparto con Onshape decía que la plataforma se dibuja a mano. Sigue
siendo verdad en lo que importa —el vínculo con el contrato lo pone quien
acota, y por eso la pieza sigue siendo paramétrica— pero la **forma** la
entrega este módulo. Construir una tangente exterior entre dos círculos
desiguales o un agujero en D a mano es donde están los errores, y es trabajo
que no hace falta repetir por pieza.

El bucle entero está en `docs/metodologia.md` §2d: generar, dibujar, que el
CAD diga «totalmente definida», comparar.

**El sitio es la mitad del valor.** Un croquis importado llega exacto y
suelto, y las cotas de la pieza no quitan los tres grados de libertad del
plano. Aquí cada pieza se emite con su rasgo datum en el ORIGEN y el centro
siguiente sobre +X, que deja el anclaje en dos coincidentes enganchados a
geometría que ya está dibujada.

**En su propio marco, no en el de la máquina.** El contrato tiene la
transformada (`brazo_origen_*`, `brazo_orientacion`), pero emitir el brazo
donde de verdad va lo deja girado -3,749°, miserable de acotar, y además el
mismo brazo ocupa DOS posiciones. No hay una posición.

Regla 3: el contrato entra en SI y aquí se cruza a milímetros, como en
`emit/dxf.py` y `emit/layout.py`. Nada de medias tintas aguas abajo.
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass
from pathlib import Path

from ezdxf.filemanagement import new as nuevo_dxf

RAIZ = Path(__file__).resolve().parent.parent
CONTRATOS = RAIZ / "docs" / "contratos.json"
MM = 1000.0

Punto = tuple[float, float]


@dataclass(frozen=True)
class Arco:
    centro: Punto
    radio: float
    desde: float
    hasta: float
    """En radianes, sentido antihorario de `desde` a `hasta`."""


@dataclass(frozen=True)
class Segmento:
    a: Punto
    b: Punto


Perfil = list[Arco | Segmento]


def contrato_mm() -> dict[str, float]:
    """Las longitudes del contrato en mm y los ángulos en radianes."""
    datos = json.loads(CONTRATOS.read_text(encoding="utf-8"))
    return {
        v["nombre"]: float(v["valor"]) * (MM if v["unidad"] == "m" else 1.0)
        for g in datos["contratos"]
        for v in g["valores"]
    }


def barra(largo: float, r0: float, r1: float) -> Perfil:
    """Contorno de una barra de dos cubos: dos arcos y sus tangentes.

    El datum —el cubo de r0— va en el origen y el otro en (largo, 0). Los
    radios pueden ser distintos, así que las tangentes no son paralelas: el
    punto de contacto sale de imponer la perpendicularidad al radio, que da
    `cos t = (r0 - r1) / largo`. Es la misma condición que coloca la cinta en
    el cabestrante, y es la que se escribió mal dos veces por razonar sobre
    el dibujo en vez de resolverla.
    """
    if largo <= abs(r0 - r1):
        raise ValueError("un cubo se come al otro: no hay tangente exterior")
    t = math.acos((r0 - r1) / largo)
    arriba = ((r0 * math.cos(t), r0 * math.sin(t)), (largo + r1 * math.cos(t), r1 * math.sin(t)))
    abajo = ((largo + r1 * math.cos(-t), r1 * math.sin(-t)), (r0 * math.cos(-t), r0 * math.sin(-t)))
    return [
        Arco((0.0, 0.0), r0, t, 2 * math.pi - t),
        Segmento(abajo[1], abajo[0]),
        Arco((largo, 0.0), r1, -t, t),
        Segmento(arriba[1], arriba[0]),
    ]


def agujero_en_d(centro: Punto, radio: float, chaveta: float) -> Perfil:
    """El agujero que cala: un arco y la cuerda de la cara plana.

    La cara mira al otro cubo —normal en +X, `brazo_chaveta_angulo` = 0— y no
    es una elección: a cualquier otro ángulo el brazo deja de ser simétrico
    respecto de su propio eje, y entonces el proximal volteado no sirve para
    el otro lado.
    """
    if not 0.0 < chaveta < radio:
        raise ValueError("la cara plana se come el agujero o no lo toca")
    t = math.acos(chaveta / radio)
    x = centro[0] + chaveta
    return [
        Arco(centro, radio, t, 2 * math.pi - t),
        Segmento((x, centro[1] - radio * math.sin(t)), (x, centro[1] + radio * math.sin(t))),
    ]


def circulo(centro: Punto, radio: float) -> Perfil:
    return [Arco(centro, radio, 0.0, 2 * math.pi)]


def disco(radio: float, agujero: float) -> Perfil:
    """Un disco con un agujero concéntrico: el sector y el tambor.

    Los dos rasgos son **círculos enteros**, y eso decide cómo se teclean:
    Onshape acota el diámetro de un círculo, así que la cota que va en el
    campo es la forma `_diametro`. El contrato guarda los dos cantos como
    radio —47,975 y 7,975— y meterlos tal cual deja la pieza a la mitad, que
    es lo que pasó con las dos.
    """
    return circulo((0.0, 0.0), radio) + circulo((0.0, 0.0), agujero / 2)


def sector(c: dict[str, float] | None = None) -> Perfil:
    c = contrato_mm() if c is None else c
    return disco(
        c["amplificador_sector_radio_mecanizado"], c["amplificador_sector_agujero_diametro"]
    )


def tambor(c: dict[str, float] | None = None) -> Perfil:
    c = contrato_mm() if c is None else c
    return disco(c["amplificador_tambor_radio_mecanizado"], c["brazo_eje_diametro"])


def ranura(centro: Punto, largo: float, radio: float) -> Perfil:
    """Una ranura recta: dos semicírculos y sus dos tangentes, horizontal.

    `largo` es el recorrido entre los dos centros, no el largo total. Es lo
    que desliza el tornillo dentro, que es lo que hay que acotar.
    """
    x0, x1 = centro[0] - largo / 2, centro[0] + largo / 2
    y = centro[1]
    return [
        Arco((x0, y), radio, math.pi / 2, 3 * math.pi / 2),
        Segmento((x0, y - radio), (x1, y - radio)),
        Arco((x1, y), radio, -math.pi / 2, math.pi / 2),
        Segmento((x1, y + radio), (x0, y + radio)),
    ]


def rectangulo(centro: Punto, largo: float, ancho: float) -> Perfil:
    x0, x1 = centro[0] - largo / 2, centro[0] + largo / 2
    y0, y1 = centro[1] - ancho / 2, centro[1] + ancho / 2
    esquinas = [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]
    return [Segmento(a, b) for a, b in zip(esquinas, esquinas[1:] + esquinas[:1], strict=True)]


def mordaza(c: dict[str, float] | None = None) -> Perfil:
    """El anclaje de la cinta: un bloque, un tornillo que aprieta y una ranura.

    **Agarra por rozamiento y no por arrastre**, y eso no es una simplificación:
    la cinta no se puede arrollar a menos de `cinta_radio_minimo` —cien veces
    su espesor, o sea 5 mm de radio— así que un pasador de arrastre tendría que
    ser de Ø10 y no cabe en una mordaza. Con un M3 a 0,3 N·m el rozamiento da
    188 N contra una carga de trabajo de unos pocos newton.

    La **ranura** es la que cala la máquina. Se desliza con el cartucho en fase
    cero y el brazo en su calaje, se aprieta, y se comprueba con la hoja de
    trazo patrón. Por eso ni el eje ni el tambor llevan ya ningún ángulo
    mecanizado: el calaje vive aquí, donde se puede corregir.

    Datum: el tornillo de apriete en el origen, la ranura sobre +X.
    """
    c = contrato_mm() if c is None else c
    largo, ancho = c["mordaza_largo"], c["mordaza_ancho"]
    apriete = c["mordaza_tornillo_diametro"] / 2
    fijacion = c["mordaza_fijacion_diametro"] / 2
    entre, voladizo = c["mordaza_entre_tornillos"], c["mordaza_voladizo"]
    # El bloque NO se centra entre los dos agujeros: la ranura llega más lejos
    # que el segundo centro, y centrándolo se salía por el extremo. Lo sitúa
    # `mordaza_voladizo` desde el tornillo de apriete, que es el datum.
    return (
        rectangulo((largo / 2 - voladizo, 0.0), largo, ancho)
        + circulo((0.0, 0.0), apriete)
        + ranura((entre, 0.0), c["mordaza_recorrido"], fijacion)
    )


def eje_pivote(c: dict[str, float] | None = None) -> Perfil:
    """La sección del eje: un Ø10 con una cara plana, y nada más.

    **Aquí es donde se nota la decisión de la mordaza.** Mientras el calaje se
    mecanizaba en el eje, esta pieza llevaba un ángulo de cuatro decimales y
    había que hacer una por lado. Con el calaje en la mordaza es una barra de
    stock con un fresado, igual en los tres sitios.

    La cara plana es la misma que la del agujero del brazo, al mismo
    desplazamiento, para que encajen.
    """
    c = contrato_mm() if c is None else c
    radio = c["brazo_eje_diametro"] / 2
    t = math.acos(c["brazo_chaveta"] / radio)
    x = c["brazo_chaveta"]
    return [
        Arco((0.0, 0.0), radio, t, 2 * math.pi - t),
        Segmento((x, -radio * math.sin(t)), (x, radio * math.sin(t))),
    ]


PERFILES = {
    "mordaza": lambda c: mordaza(c),
    "eje_pivote": lambda c: eje_pivote(c),
    "sector": lambda c: sector(c),
    "tambor": lambda c: tambor(c),
}
"""Las piezas prismáticas que no son barras. El resto sale de `BRAZOS`.

El sector y el tambor estaban fuera «porque son discos y su hoja lleva
secciones». Fuera del bucle salieron **las dos a la mitad**, y por la misma
causa: la hoja del cabestrante rotulaba el canto como radio y el campo del
CAD pide diámetro. Un disco con un agujero es una forma como otra."""

BRAZOS = {
    "brazo_proximal": ("brazo_proximal", True),
    "brazo_distal": ("brazo_distal", False),
    "palanca_lapiz": ("brazo_palanca", True),
}


def brazo(cual: str, c: dict[str, float] | None = None) -> Perfil:
    """Una de las tres barras del cinco barras, en su marco y en el datum."""
    if cual not in BRAZOS:
        raise KeyError(f"no sé dibujar «{cual}». Hay: {', '.join(BRAZOS)}")
    c = contrato_mm() if c is None else c
    entre_centros, calado = BRAZOS[cual]
    largo = c[entre_centros]
    extremo, perno = c["brazo_extremo_diametro"] / 2, c["brazo_perno_diametro"] / 2
    if not calado:
        # Biela: los dos extremos iguales porque no cala nada.
        return (
            barra(largo, extremo, extremo)
            + circulo((0.0, 0.0), perno)
            + circulo((largo, 0.0), perno)
        )
    cubo, eje = c["brazo_cubo_diametro"] / 2, c["brazo_eje_diametro"] / 2
    return (
        barra(largo, cubo, extremo)
        + agujero_en_d((0.0, 0.0), eje, c["brazo_chaveta"])
        + circulo((largo, 0.0), perno)
    )


@dataclass(frozen=True)
class Variable:
    """Una cota que hay que teclear, con cómo se lee en la hoja."""

    mapa: str
    nombre: str
    etiqueta: str
    sufijo: str = ""
    en_el_perfil: bool = True
    """Si el DXF ya la trae resuelta. Las que no —el espesor, el calaje— no
    son geometría del perfil y hay que teclearlas igual: el archivo no
    sustituye a la tabla de variables, la adelgaza."""


@dataclass(frozen=True)
class Ficha:
    forma: str
    cantidad: int
    variables: tuple[Variable, ...]
    solido: tuple[str, str] = ("plancha", "")
    """(clase, cota de la tercera dimensión).

    Un perfil 2D no es una pieza: le falta por dónde se extruye. `plancha` se
    extruye en espesor y su segunda vista es una **sección**; `barra` se
    extruye a lo largo y la suya es un **alzado**. Sin esto la hoja enseña un
    contorno y el espesor se queda solo en la tabla, que es donde menos se
    mira.
    """
    porque: str = ""
    """Por qué la pieza es así, en dos frases, para la hoja.

    No es decoración: quien dibuja sin saber por qué una cota es la que es
    la «mejora» al primer apuro. El porqué largo vive en `docs/contratos.md`;
    aquí va lo que hay que tener delante mientras se dibuja.
    """


def _barra_calada(entre_centros: str, etiqueta: str, calaje: str, porque: str) -> Ficha:
    """El proximal y la palanca son la misma pieza con otra longitud, así que
    su lista de variables se escribe una vez. Repetirla era la forma segura
    de que una de las dos se quedara atrás."""
    return Ficha(
        "barra de dos cubos **desiguales** en pletina de latón",
        2 if calaje == "calaje_izquierdo" else 1,
        (
            Variable("cota", entre_centros, etiqueta),
            Variable("cota", "brazo_espesor", "espesor", en_el_perfil=False),
            Variable("cota", "brazo_eje_diametro", "Ø eje", "H7"),
            Variable("cota", "brazo_perno_diametro", "Ø perno", "H7"),
            Variable("cota", "brazo_cubo_diametro_radio", "R del cubo del eje"),
            Variable("cota", "brazo_extremo_diametro_radio", "R del extremo"),
            Variable("cota", "brazo_chaveta", "cara plana a"),
            Variable("cota", "brazo_chaveta_cuerda", "cuerda"),
            Variable("angulo", "brazo_chaveta_angulo", "girada"),
            Variable("angulo", calaje, "calaje del EJE", en_el_perfil=False),
        ),
        ("plancha", "brazo_espesor"),
        porque,
    )


LISTADO: dict[str, Ficha] = {
    "brazo_proximal": _barra_calada(
        "brazo_proximal",
        "entre centros",
        "calaje_izquierdo",
        "Se corta UNA y valen las dos: los calajes suman -180 grados, así que el brazo "
        "derecho es este volteado. La cara plana del agujero es lo único que lo cala, y "
        "va a cero grados del eje de la pieza justo para que el volteo siga valiendo.",
    ),
    "brazo_distal": Ficha(
        "barra de dos cubos **iguales** en pletina de latón",
        2,
        (
            Variable("cota", "brazo_distal", "entre centros"),
            Variable("cota", "brazo_espesor", "espesor", en_el_perfil=False),
            Variable("cota", "brazo_perno_diametro", "Ø los dos", "H7"),
            Variable("cota", "brazo_extremo_diametro_radio", "R los dos"),
        ),
        ("plancha", "brazo_espesor"),
        "Es una biela: gira libre en los dos pernos y no cala nada. Que los dos extremos "
        "salgan iguales es la consecuencia, no una elección; si dejaran de serlo sería "
        "que alguien le ha puesto un calaje que no necesita.",
    ),
    "palanca_lapiz": _barra_calada(
        "brazo_palanca",
        "entre centros",
        "calaje_elevador",
        "Como el proximal pero más corta. Su error no desplaza el trazo, lo levanta "
        "antes o después; aun así va calada, porque con la palanca girada el lápiz no "
        "apoya donde debe.",
    ),
    "mordaza": Ficha(
        "bloque con un tornillo que aprieta y una ranura que cala",
        6,
        (
            Variable("cota", "mordaza_largo", "largo"),
            Variable("cota", "mordaza_voladizo", "del tornillo al borde"),
            Variable("cota", "mordaza_ancho", "ancho"),
            Variable("cota", "mordaza_espesor", "espesor", en_el_perfil=False),
            Variable("cota", "mordaza_tornillo_diametro", "Ø aprieta la cinta", "M3"),
            Variable("cota", "mordaza_fijacion_diametro", "Ø fija al sector", "M4"),
            Variable("cota", "mordaza_entre_tornillos", "entre los dos"),
            Variable("cota", "mordaza_recorrido", "recorrido de la ranura"),
            Variable("cota", "mordaza_ranura_cerca", "datum al centro cercano"),
            Variable("cota", "mordaza_ranura_lejos", "datum al centro lejano"),
            Variable("cota", "cinta_radio_minimo", "radio mínimo de la cinta", en_el_perfil=False),
        ),
        ("plancha", "mordaza_espesor"),
        "Aquí vive el calaje de la máquina. La ranura desliza con el cartucho en fase "
        "cero y el brazo en su ángulo, se aprieta, y se comprueba con la hoja de trazo "
        "patrón. Agarra por ROZAMIENTO y no por arrastre: la cinta no se arrolla a menos "
        "de 5 mm de radio, así que un pasador tendría que ser de Ø10 y no cabe. Los dos "
        "tornillos son M3 y M4 a propósito, para que no se puedan cambiar de agujero.",
    ),
    "eje_pivote": Ficha(
        "barra Ø10 h6 con una cara plana, cortada a medida",
        3,
        (
            Variable("cota", "brazo_eje_diametro", "Ø", "h6"),
            Variable("cota", "eje_pivote_largo", "largo", "PENDIENTE", en_el_perfil=False),
            Variable("cota", "brazo_chaveta", "cara plana a"),
            Variable("cota", "brazo_chaveta_cuerda", "cuerda"),
        ),
        ("barra", "eje_pivote_largo"),
        "Una barra de stock con un fresado, igual en los tres sitios. NO lleva ningún "
        "ángulo: mientras el calaje se mecanizaba aquí, esta pieza traía cuatro "
        "decimales y había una por lado. La cara plana es la misma que la del agujero "
        "del brazo, para que encajen.",
    ),
    "sector": Ficha(
        "disco entero de POM, sin muesca",
        3,
        (
            Variable("cota", "amplificador_sector_radio_mecanizado_diametro", "Ø del canto"),
            Variable("cota", "amplificador_sector_espesor", "espesor", en_el_perfil=False),
            Variable("cota", "amplificador_sector_agujero_diametro", "Ø de paso"),
            Variable("angulo", "amplificador_tangencia", "la cinta entra a", en_el_perfil=False),
        ),
        ("plancha", "amplificador_sector_espesor"),
        "Disco entero, sin muesca: la cinta abraza el lado OPUESTO al tambor, así que "
        "en el lado libre no hay nada que librar, y una muesca le pondría orientación a "
        "una pieza que siendo un disco con un agujero no la tiene.",
    ),
    "tambor": Ficha(
        "cilindro liso con agujero, sin pestañas",
        3,
        (
            Variable("cota", "amplificador_tambor_radio_mecanizado_diametro", "Ø del canto"),
            Variable("cota", "amplificador_tambor_ancho", "ancho", en_el_perfil=False),
            Variable("cota", "brazo_eje_diametro", "Ø agujero", "H7"),
            Variable("angulo", "amplificador_tambor_abrazado", "abrazado", en_el_perfil=False),
        ),
        ("barra", "amplificador_tambor_ancho"),
        "Cilindro liso, sin pestañas. Lo que mantiene la cinta en su sitio no son las "
        "pestañas sino que los dos asientos sean coplanarios, y eso es una tolerancia y "
        "no un resalte. R8 son 160 espesores de cinta: pasa de sobra el radio mínimo.",
    ),
}
"""Qué se teclea en cada pieza de la plataforma, y nada más.

**Está aquí y no en la hoja ni en el documento** porque los tres lo
imprimen: el plano, `docs/metodologia.md` y el que lo copia. Tres listas de
variables es la forma garantizada de que una se quede atrás, que es la
trampa de «rotular una variable que no existe» con otro disfraz.
"""


def _numero(x: float) -> str:
    """Tres decimales como mucho, sin ceros de relleno, y coma.

    La coma no es coquetería: la hoja, el plano y el informe se leen en el
    mismo taller, y un separador que cambia de sitio invita a leer 47.975
    como cuarenta y siete mil."""
    return f"{round(x, 3):g}".replace(".", ",")


def _valor(c: dict[str, float], v: Variable) -> str:
    if v.mapa == "angulo":
        return _numero(math.degrees(c[v.nombre]))
    if v.nombre in c:
        return _numero(c[v.nombre])
    # Los gemelos los fabrica el exportador, no el contrato.
    for sufijo, factor in (("_radio", 0.5), ("_diametro", 2.0)):
        if v.nombre.endswith(sufijo) and v.nombre.removesuffix(sufijo) in c:
            return _numero(c[v.nombre.removesuffix(sufijo)] * factor)
    raise KeyError(v.nombre)


def tabla_markdown(c: dict[str, float] | None = None) -> str:
    """El listado de piezas y variables, en markdown.

    Se genera y no se escribe a mano: una tabla de variables copiada envejece
    en silencio, y lo que la lee es alguien tecleando en un CAD.
    """
    c = contrato_mm() if c is None else c
    filas = ["| Pieza | Forma | Cotas |", "| --- | --- | --- |"]
    for pieza, ficha in LISTADO.items():
        cotas = " · ".join(
            f"{v.etiqueta} `#{v.mapa}.{v.nombre}` {_valor(c, v)}"
            + (f" {v.sufijo}" if v.sufijo else "")
            for v in ficha.variables
        )
        filas.append(f"| `{pieza}` ×{ficha.cantidad} | {ficha.forma} | {cotas} |")
    return "\n".join(filas) + "\n"


def escribir_dxf(perfil: Perfil, destino: Path, capa: str = "VISIBLE") -> Path:
    """El perfil a DXF, **sin rótulos**.

    Un `TEXT` de DXF no es una entidad de boceto y Onshape suelta un «no se ha
    podido importar la entidad desconocida» al verlo. Estos archivos se
    importan a un croquis, así que no llevan ninguno: lo que hay que leer va
    en la hoja, no en el archivo.
    """
    doc = nuevo_dxf("R2010", setup=False)
    doc.header["$INSUNITS"] = 4  # milímetros, para que el CAD no pregunte
    doc.layers.add(capa)
    msp = doc.modelspace()
    for e in perfil:
        if isinstance(e, Segmento):
            msp.add_line(e.a, e.b, dxfattribs={"layer": capa})
        elif abs(e.hasta - e.desde - 2 * math.pi) < 1e-12:
            msp.add_circle(e.centro, e.radio, dxfattribs={"layer": capa})
        else:
            msp.add_arc(
                e.centro,
                e.radio,
                math.degrees(e.desde),
                math.degrees(e.hasta),
                dxfattribs={"layer": capa},
            )
    destino.parent.mkdir(parents=True, exist_ok=True)
    doc.saveas(destino)
    return destino
