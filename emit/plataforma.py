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

from emit.dxf import guardar

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
    """Las longitudes del contrato en mm y los ángulos en radianes.

    Con el **gemelo en positivo de cada ángulo negativo**: la herramienta de
    ángulo del CAD mide una magnitud y no acepta un signo, así que teclear
    -58,407 en ese campo no da el ángulo de enfrente, da un campo en rojo.
    Lo que se teclea es 58,407 y el lado lo decide dónde cae el rasgo, igual
    que la cara plana de la chaveta: el número no lo dice, lo dice el sitio.

    Es el patrón del gemelo de diámetro con otra cara, y por el mismo
    motivo: no hacer el error improbable, hacerlo imposible.
    """
    datos = json.loads(CONTRATOS.read_text(encoding="utf-8"))
    salida: dict[str, float] = {}
    for g in datos["contratos"]:
        for v in g["valores"]:
            nombre = v["nombre"]
            valor = float(v["valor"]) * (MM if v["unidad"] == "m" else 1.0)
            salida[nombre] = valor
            if v["unidad"] == "rad" and -math.pi < valor < 0.0:
                salida[f"{nombre}_positivo"] = -valor
    return salida


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


def agujero_en_d(centro: Punto, radio: float, chaveta: float, angulo: float = 0.0) -> Perfil:
    """El agujero que cala: un arco y la cuerda de la cara plana.

    `angulo` (radianes) es hacia dónde mira la normal de la cara. En los
    brazos es 0 —mira al otro cubo, `brazo_chaveta_angulo`— y no es una
    elección: a cualquier otro ángulo el brazo deja de ser simétrico respecto
    de su propio eje, y entonces el proximal volteado no sirve para el otro
    lado. En el balancín es 90°, `balancin_chaveta_angulo`: va en el mismo
    eje de una cara plana que la palanca y tiene que quedar a un cuarto de
    vuelta de ella.
    """
    if not 0.0 < chaveta < radio:
        raise ValueError("la cara plana se come el agujero o no lo toca")
    t = math.acos(chaveta / radio)
    cx, cy = centro
    co, si = math.cos(angulo), math.sin(angulo)

    def girar(x: float, y: float) -> Punto:
        return (cx + x * co - y * si, cy + x * si + y * co)

    h = radio * math.sin(t)
    return [
        Arco(centro, radio, angulo + t, angulo + 2 * math.pi - t),
        Segmento(girar(chaveta, -h), girar(chaveta, h)),
    ]


def circulo(centro: Punto, radio: float) -> Perfil:
    return [Arco(centro, radio, 0.0, 2 * math.pi)]


def seguidor(c: dict[str, float] | None = None) -> Perfil:
    """La barra del seguidor: pivote, rodillo, muelle y los dos al sector.

    Es una barra de dos cubos como los brazos, y lleva **cuatro** agujeros en
    línea porque todo lo que cuelga del seguidor tira sobre el mismo eje: el
    muelle cerca, para que su par apenas varíe; los dos tornillos del sector
    repartidos, porque el agujero del sector es de paso y hacen falta dos
    puntos para quitarle el giro; y el rodillo al final, a 45.

    En línea y no en una brida alrededor del cubo: una brida con los
    tornillos a 11 obligaría a un cubo de Ø28 en una pieza de 45 de largo.
    """
    c = contrato_mm() if c is None else c
    largo = c["brazo_seguidor"]
    perfil = barra(largo, c["seguidor_cubo_diametro"] / 2, c["seguidor_extremo_diametro"] / 2)
    perfil += circulo((0.0, 0.0), c["seguidor_pivote_diametro"] / 2)
    perfil += circulo((c["seguidor_muelle_radio"], 0.0), c["seguidor_muelle_diametro"] / 2)
    for cota in ("union_sector_seguidor_cerca", "union_sector_seguidor_lejos"):
        perfil += circulo((c[cota], 0.0), c["union_sector_seguidor_diametro"] / 2)
    perfil += circulo((largo, 0.0), c["seguidor_rodillo_diametro"] / 2)
    return perfil


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
    """El disco del cabestrante, con los dos agujeros que lo calan al seguidor.

    **Dos círculos no eran la pieza entera.** Se dio por buena cuando sector y
    seguidor eran lo único dibujado de su lado, y su agujero central es de
    PASO —libra la valona de Ø15— así que no sujeta ni orienta nada: sin estos
    dos tornillos el sector gira suelto sobre el casquillo y la relación 6:1
    no llega al brazo.

    Y al ponerlos, el disco **gana una orientación** que antes no tenía. Eso
    cambia su datum: ya hay un «centro siguiente» sobre +X, así que se ancla
    como las demás y no por el caso de los rasgos concéntricos.
    """
    c = contrato_mm() if c is None else c
    perfil = disco(
        c["amplificador_sector_radio_mecanizado"], c["amplificador_sector_agujero_diametro"]
    )
    for cota in ("union_sector_seguidor_cerca", "union_sector_seguidor_lejos"):
        perfil += circulo((c[cota], 0.0), c["union_sector_seguidor_diametro"] / 2)
    return perfil


def tambor(c: dict[str, float] | None = None) -> Perfil:
    """El tambor, con el agujero en D del eje de pivote.

    Era redondo, y así no cala: el par que la cinta le da no llegaba al eje
    ni, por tanto, al brazo. El cabestrante 6:1 entero colgaba de esa cara
    plana que faltaba.
    """
    c = contrato_mm() if c is None else c
    return circulo((0.0, 0.0), c["amplificador_tambor_radio_mecanizado"]) + agujero_en_d(
        (0.0, 0.0), c["brazo_eje_diametro"] / 2, c["brazo_chaveta"]
    )


def casquillo_rueda(c: dict[str, float] | None = None) -> Perfil:
    """El casquillo que pone la rueda Z60, de agujero 15, en el árbol de 10."""
    c = contrato_mm() if c is None else c
    return disco(c["casquillo_rueda_diametro"] / 2, c["eje_diametro"])


def platina_levas(c: dict[str, float] | None = None) -> Perfil:
    """La platina de levas: un disco con los seis agujeros del mecanismo.

    **Es un disco y no un rectángulo** porque los seis caben dentro de 71,063
    —los tres postes son los de más afuera— así que el contorno se dice con
    una sola cota, y es la forma que el reparto a 120° ya pedía.

    Los dos pivotes del cinco barras caen a la **misma distancia**, 68,213, y a
    ángulos simétricos respecto de la bisectriz de 60° entre el poste 1 y el
    2. No es casualidad: salen de la misma transformación que deja cada
    pivote a 68,000 de su poste, que es lo que el cabestrante necesita.
    """
    c = contrato_mm() if c is None else c
    perfil = circulo((0.0, 0.0), c["platina_diametro"] / 2)
    perfil += circulo((0.0, 0.0), c["rodamiento_arbol_alojamiento_diametro"] / 2)
    # `contrato_mm` pasa a milímetros las LONGITUDES y deja los ángulos en
    # radianes, así que aquí no se divide por nada. Dividir por MM «por
    # simetría» ponía los tres postes a dos milésimas de grado uno de otro.
    for i in range(3):
        t = c["poste_reparto"] * i
        centro = (
            c["poste_radio_al_arbol"] * math.cos(t),
            c["poste_radio_al_arbol"] * math.sin(t),
        )
        perfil += circulo(centro, c["poste_eje_diametro"] / 2)
    for cota in ("platina_pivote_angulo_izquierdo", "platina_pivote_angulo_derecho"):
        t = c[cota]
        centro = (
            c["platina_pivote_al_arbol"] * math.cos(t),
            c["platina_pivote_al_arbol"] * math.sin(t),
        )
        perfil += circulo(centro, c["brazo_eje_diametro"] / 2)
    # El séptimo: el rodamiento del eje de la manivela, a 28 del árbol. En el
    # plato de abajo no sujeta nada —es una ventana más al mecanismo— y a
    # cambio los TRES platos son la misma pieza.
    t = c["platina_manivela_angulo"]
    centro = (c["reductor_entre_ejes"] * math.cos(t), c["reductor_entre_ejes"] * math.sin(t))
    perfil += circulo(centro, c["rodamiento_arbol_alojamiento_diametro"] / 2)
    return perfil


def volante(c: dict[str, float] | None = None) -> Perfil:
    """El volante del eje de la manivela: un disco aligerado con seis
    agujeros y el mismo agujero en D que cala los brazos.

    **La única pieza cuya cota no es un encaje, es un requisito.** Su
    diámetro no lo decide nada que toque: lo decide la inercia que hace
    falta para que la manivela no vaya a tirones, y por eso lo vigila un
    test contra C7 y no contra un ajuste.

    Va aligerado porque la inercia vive en el borde: seis agujeros de Ø24
    quitan 100 g de latón y solo un 9 % de inercia.

    Cala igual que un brazo, con la cara plana de la barra Ø10 h6. No lleva
    prisionero: un taladro radial no sale de una plancha cortada, y la cara
    plana ya existe en los otros tres sitios de la máquina.
    """
    c = contrato_mm() if c is None else c
    perfil = circulo((0.0, 0.0), c["volante_diametro"] / 2)
    perfil += agujero_en_d((0.0, 0.0), c["brazo_eje_diametro"] / 2, c["brazo_chaveta"])
    # `contrato_mm` deja los ángulos en radianes: aquí no se divide por nada.
    for i in range(6):
        t = c["volante_aligeramiento_reparto"] * i
        r = c["volante_aligeramiento_al_centro"]
        centro = (r * math.cos(t), r * math.sin(t))
        perfil += circulo(centro, c["volante_aligeramiento_diametro"] / 2)
    return perfil


def balancin(c: dict[str, float] | None = None) -> Perfil:
    """El brazo de entrada del balancín: la pieza que da el cuarto de vuelta.

    Es una barra de dos cubos como los brazos, pero diminuta: 6,333 entre
    centros, que es `levantamiento_pasador_al_pivote` partido por la
    relación. No es una elección de tamaño, es lo que la relación 6 obliga a
    medir, y es lo que decide que el eje sea de 4 y no de 10 como los demás:
    con 10 el pasador se metería dentro del agujero del eje.

    Cala por la cara plana, igual que los brazos, y en el mismo eje va la
    palanca del lápiz 90,75 mm más adelante. El eje corre de proa a popa, y
    esa orientación es toda la invención: convierte el movimiento del
    seguidor, que va de lado, en el vertical que necesita la mesa. Su cara
    plana va girada 90°: con el eje de una sola cara, eso deja la palanca
    horizontal y el balancín apuntando hacia arriba.
    """
    c = contrato_mm() if c is None else c
    largo = c["balancin_entrada"]
    cubo, extremo = c["balancin_cubo_diametro"] / 2, c["balancin_extremo_diametro"] / 2
    return (
        barra(largo, cubo, extremo)
        + agujero_en_d(
            (0.0, 0.0),
            c["balancin_eje_diametro"] / 2,
            c["balancin_chaveta"],
            c["balancin_chaveta_angulo"],
        )
        + circulo((largo, 0.0), c["balancin_perno_diametro"] / 2)
    )


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


def base(c: dict[str, float] | None = None) -> Perfil:
    """La tabla de nogal: un rectángulo y los tres agujeros de los postes.

    **El datum es el poste 1 y el siguiente va sobre +X.** Los tres postes
    forman un triángulo equilátero —están a 120° del árbol— así que la pieza
    se acota con un lado y un ángulo de 60 en vez de con tres polares, y el
    agujero del árbol, que es el datum de los platos, aquí no existe: en la
    base no hay nada en el centro.

    La planta sale de dos cosas que ya estaban: el plato por detrás y la
    tarjeta por delante, con 10 mm de nogal a cada punta. La altura no sale
    de aquí, y por eso `base_al_plato` está pendiente.

    **Los postes bajan hasta la base y hacen de pata.** No hay pilar: es el
    mismo argumento que hizo del tercer plato la misma pieza. A cambio el
    poste pasa de 105 a 195 y la base lleva su patrón de agujeros, que es
    el de los platos visto desde otro datum.
    """
    c = contrato_mm() if c is None else c
    lado, radio = c["base_entre_postes"], c["poste_eje_diametro"] / 2
    izquierdo, trasero = c["base_poste_al_borde_izquierdo"], c["base_poste_al_borde_trasero"]
    centro = (-izquierdo + c["base_ancho"] / 2, -trasero + c["base_fondo"] / 2)
    perfil = rectangulo(centro, c["base_ancho"], c["base_fondo"])
    perfil += circulo((0.0, 0.0), radio)
    perfil += circulo((lado, 0.0), radio)
    t = c["base_postes_angulo"]
    perfil += circulo((lado * math.cos(t), lado * math.sin(t)), radio)
    return perfil


PERFILES = {
    "mordaza": lambda c: mordaza(c),
    "eje_pivote": lambda c: eje_pivote(c),
    "sector": lambda c: sector(c),
    "tambor": lambda c: tambor(c),
    "seguidor": lambda c: seguidor(c),
    "platina_levas": lambda c: platina_levas(c),
    "volante": lambda c: volante(c),
    "base": lambda c: base(c),
    "balancin": lambda c: balancin(c),
    "eje_manivela": lambda c: eje_pivote(c),
    "casquillo_rueda": lambda c: casquillo_rueda(c),
}
"""Las piezas prismáticas que no son barras. El resto sale de `BRAZOS`.

El sector y el tambor estaban fuera «porque son discos y su hoja lleva
secciones». Fuera del bucle salieron **las dos a la mitad**, y por la misma
causa: la hoja del cabestrante rotulaba el canto como radio y el campo del
CAD pide diámetro. Un disco con un agujero es una forma como otra."""

BRAZOS = {
    "brazo_proximal": ("brazo_proximal", True, "brazo"),
    "brazo_distal": ("brazo_distal", False, "brazo"),
    # **La palanca ya no va en un eje de 10.** Cuelga del eje del balancín,
    # que es de 4 porque el brazo de entrada mide 6,33 y con 10 el pasador
    # se metía DENTRO del agujero del eje. El cubo y la cara plana la siguen
    # a ese eje: lo que comparten es el encaje, no la familia de piezas.
    "palanca_lapiz": ("brazo_palanca", True, "balancin"),
    # La manivela es un brazo más: la misma pletina con otro largo, el
    # mismo agujero en D y el mismo perno de Ø6 en el extremo, que aquí
    # lleva el pomo en vez de una biela. Lo único suyo es cuánto mide.
    "manivela": ("manivela_entre_centros", True, "brazo"),
}


def brazo(cual: str, c: dict[str, float] | None = None) -> Perfil:
    """Una de las tres barras del cinco barras, en su marco y en el datum."""
    if cual not in BRAZOS:
        raise KeyError(f"no sé dibujar «{cual}». Hay: {', '.join(BRAZOS)}")
    c = contrato_mm() if c is None else c
    entre_centros, calado, eje = BRAZOS[cual]
    largo = c[entre_centros]
    extremo, perno = c["brazo_extremo_diametro"] / 2, c["brazo_perno_diametro"] / 2
    if not calado:
        # Biela: no cala nada. El extremo del codo lleva su perno de 6; el de
        # la punta, el tubo hueco por el que pasa el lápiz, y por eso es más
        # grande. Los dos distales comparten ese tubo.
        punta = c["distal_punta_diametro"] / 2
        return (
            barra(largo, extremo, punta)
            + circulo((0.0, 0.0), perno)
            + circulo((largo, 0.0), c["punta_tubo_diametro"] / 2)
        )
    cubo, radio = c[f"{eje}_cubo_diametro"] / 2, c[f"{eje}_eje_diametro"] / 2
    return (
        barra(largo, cubo, extremo)
        + agujero_en_d((0.0, 0.0), radio, c[f"{eje}_chaveta"])
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
    montaje: str = ""
    """Con qué se junta la pieza, cara por cara, y a qué altura queda.

    El contorno y las cotas bastan para CORTARLA; para ENSAMBLARLA no. Un
    disco de POM de 5 con cuatro agujeros no dice por sí mismo cuál de sus
    dos caras mira al plato, qué lleva encima ni contra qué apoya, y eso es
    justo lo que hay que saber con la pieza en la mano.

    Se escribe mirando la sección: primero la cara de abajo, luego la de
    arriba, y después lo que atraviesa.
    """
    material: str = ""
    """De qué es y en qué formato se compra.

    No es para dibujarla: es para el despiece del dossier y para la lista de
    la compra. La `forma` ya lo menciona de pasada, en prosa, y una lista de
    materiales sacada de una prosa es una lista escrita a mano con pasos de
    por medio.
    """
    proceso: str = ""
    """Cómo se saca la pieza del material. Decide quién la hace y dónde."""


def _barra_calada(
    entre_centros: str,
    etiqueta: str,
    calaje: str,
    porque: str,
    montaje: str = "",
    eje: str = "brazo",
    material: str = "",
    proceso: str = "",
) -> Ficha:
    """El proximal y la palanca son la misma pieza con otra longitud, así que
    su lista de variables se escribe una vez. Repetirla era la forma segura
    de que una de las dos se quedara atrás."""
    return Ficha(
        "barra de dos cubos **desiguales** en pletina de latón",
        2 if calaje == "calaje_izquierdo" else 1,
        (
            Variable("cota", entre_centros, etiqueta),
            Variable("cota", "brazo_espesor", "espesor", en_el_perfil=False),
            Variable("cota", f"{eje}_eje_diametro", "Ø eje", "H7"),
            Variable("cota", "brazo_perno_diametro", "Ø perno", "H7"),
            Variable("cota", f"{eje}_cubo_diametro_radio", "R del cubo del eje"),
            Variable("cota", "brazo_extremo_diametro_radio", "R del extremo"),
            Variable("cota", f"{eje}_chaveta", "cara plana a"),
            Variable("cota", f"{eje}_chaveta_cuerda", "cuerda"),
            Variable("angulo", "brazo_chaveta_angulo", "girada"),
            Variable("angulo", calaje, "calaje del EJE", en_el_perfil=False),
        ),
        ("plancha", "brazo_espesor"),
        porque,
        montaje,
        material,
        proceso,
    )


LISTADO: dict[str, Ficha] = {
    "brazo_proximal": _barra_calada(
        "brazo_proximal",
        "entre centros",
        "calaje_izquierdo",
        "Se corta UNA y valen las dos: los calajes suman -180 grados, así que el brazo "
        "derecho es este volteado. La cara plana del agujero es lo único que lo cala, y "
        "va a cero grados del eje de la pieza justo para que el volteo siga valiendo.",
        montaje=(
            "Cara de abajo contra la cabeza del perno del codo; cara de arriba contra el plato "
            "1, con 1 mm de holgura. El cubo de Ø18 se cala en el eje de pivote por la cara "
            "plana y se aprieta con un collar por debajo. El derecho es este mismo volteado, "
            "así que queda un milímetro más abajo: los dos proximales se cruzan."
        ),
        material="latón, pletina de 3",
        proceso="corte + taladro",
    ),
    "brazo_distal": Ficha(
        "barra de dos cubos desiguales en pletina de latón: codo y punta",
        2,
        (
            Variable("cota", "brazo_distal", "entre centros"),
            Variable("cota", "brazo_espesor", "espesor", en_el_perfil=False),
            Variable("cota", "brazo_perno_diametro", "Ø perno del codo", "H7"),
            Variable("cota", "brazo_extremo_diametro_radio", "R del codo"),
            Variable("cota", "punta_tubo_diametro", "Ø tubo de la punta", "H7"),
            Variable("cota", "distal_punta_diametro_radio", "R de la punta"),
        ),
        ("plancha", "brazo_espesor"),
        "Es una biela: gira libre y no cala nada. La punta es hueca —un tubo de 13 por el "
        "que pasa el lápiz— y por eso ese extremo es más grande que el del codo: con el "
        "lápiz en el eje de la punta, nada de lo que gire sobre ella mueve la mina.",
        montaje=(
            "Por debajo de los dos proximales, cada distal en su plano: 3 de pletina y 0,5 de "
            "arandela entre brazo y brazo. El codo gira en su perno de Ø6; la punta, en el tubo "
            "común de Ø13. El cubo grande va siempre a la punta."
        ),
        material="latón, pletina de 3",
        proceso="corte + taladro",
    ),
    "palanca_lapiz": _barra_calada(
        "brazo_palanca",
        "entre centros",
        "calaje_elevador",
        "Como el proximal pero más corta. Su error no desplaza el trazo, lo levanta "
        "antes o después; aun así va calada, porque con la palanca girada el lápiz no "
        "apoya donde debe.",
        montaje=(
            "Calada al eje del balancín por la cara plana, en el extremo de x = 65, por encima "
            "del plato 1. En el extremo libre cuelga el tirante por su perno de Ø6. Horizontal "
            "a media altura de levantamiento: ese es el calaje."
        ),
        eje="balancin",
        material="latón, pletina de 3",
        proceso="corte + taladro",
    ),
    "mordaza": Ficha(
        "bloque con un tornillo que aprieta y una ranura que cala",
        4,
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
        montaje=(
            "Se atornilla sobre la cara libre del sector, con el M4 pasando por su ranura. La "
            "cinta entra entre el bloque y el sector, y el M3 la aprieta contra el canto. Dos "
            "por cinta, una en cada anclaje, justo por fuera de los puntos de tangencia."
        ),
        material="latón, pletina de 6",
        proceso="fresado",
    ),
    "eje_pivote": Ficha(
        "barra Ø10 h6 con una cara plana, cortada a medida",
        2,
        (
            Variable("cota", "brazo_eje_diametro", "Ø", "h6"),
            Variable("cota", "eje_pivote_largo", "largo", en_el_perfil=False),
            Variable("cota", "brazo_chaveta", "cara plana a"),
            Variable("cota", "brazo_chaveta_cuerda", "cuerda"),
        ),
        ("barra", "eje_pivote_largo"),
        "Una barra de stock con un fresado, igual en los tres sitios. NO lleva ningún "
        "ángulo: mientras el calaje se mecanizaba aquí, esta pieza traía cuatro "
        "decimales y había una por lado. La cara plana es la misma que la del agujero "
        "del brazo, para que encajen.",
        montaje=(
            "Atraviesa el plato 1. Por debajo cala el brazo proximal; por encima, el tambor del "
            "cabestrante, cuya cara alta queda a 33,5 del plato. Un collar bajo el proximal y "
            "un circlip sobre el tambor: 55 en los dos lados. La cara plana mira al otro cubo "
            "del brazo y es lo único que fija el calaje."
        ),
        material="acero W10 h6 rectificado",
        proceso="corte a medida + fresado de la cara plana",
    ),
    "sector": Ficha(
        "disco de POM sin muesca, con los dos tornillos que lo calan al seguidor",
        2,
        (
            Variable("cota", "amplificador_sector_radio_mecanizado_diametro", "Ø del canto"),
            Variable("cota", "amplificador_sector_espesor", "espesor", en_el_perfil=False),
            Variable("cota", "amplificador_sector_agujero_diametro", "Ø de paso"),
            Variable("angulo", "amplificador_tangencia", "la cinta entra a", en_el_perfil=False),
            Variable("cota", "union_sector_seguidor_cerca", "centro al tornillo cercano"),
            Variable("cota", "union_sector_seguidor_lejos", "centro al tornillo lejano"),
            Variable("cota", "union_sector_seguidor_diametro", "Ø paso de los dos al seguidor"),
        ),
        ("plancha", "amplificador_sector_espesor"),
        "Disco entero, sin muesca: la cinta abraza el lado OPUESTO al tambor, así que en "
        "el lado libre no hay nada que librar. Lo que sí le pone orientación son los DOS "
        "tornillos que lo calan al seguidor, y hacen falta: su agujero central es de paso "
        "—libra la valona de Ø15— y no sujeta ni orienta nada, así que sin ellos el disco "
        "gira suelto sobre el casquillo y la relación 6:1 no llega al brazo.",
        montaje=(
            "Se atornilla a la cara de ARRIBA del seguidor con los dos M3, así que gira con él "
            "sobre el poste. Su agujero de Ø16 libra la valona del casquillo. El canto tiene "
            "que quedar coplanario con el del tambor dentro de 0,2 mm: eso es lo que sustituye "
            "a las pestañas."
        ),
        material="POM-C negro, plancha de 5",
        proceso="fresado CNC",
    ),
    "tambor": Ficha(
        "cilindro liso con agujero, sin pestañas",
        2,
        (
            Variable("cota", "amplificador_tambor_radio_mecanizado_diametro", "Ø del canto"),
            Variable("cota", "amplificador_tambor_ancho", "ancho", en_el_perfil=False),
            Variable("cota", "brazo_eje_diametro", "Ø agujero", "H7"),
            Variable("cota", "brazo_chaveta", "cara plana a"),
            Variable("cota", "brazo_chaveta_cuerda", "cuerda"),
            Variable("angulo", "brazo_chaveta_angulo", "girada"),
            Variable("angulo", "amplificador_tambor_abrazado", "abrazado", en_el_perfil=False),
        ),
        ("barra", "amplificador_tambor_ancho"),
        "Cilindro liso, sin pestañas. Lo que mantiene la cinta en su sitio no son las "
        "pestañas sino que los dos asientos sean coplanarios, y eso es una tolerancia y "
        "no un resalte. R8 son 160 espesores de cinta: pasa de sobra el radio mínimo.",
        montaje=(
            "Cala en el eje de pivote por la cara plana, por encima del plato 1, enfrentado al "
            "sector de su canal: de 111,5 a 117,5, coplanario con él. La cinta lo abraza 185 "
            "grados y se ancla en el sector, no aquí."
        ),
        material="latón, barra de Ø16",
        proceso="torneado",
    ),
    "manivela": Ficha(
        "barra de dos cubos en pletina de latón, como los brazos",
        1,
        (
            Variable("cota", "manivela_entre_centros", "entre centros"),
            Variable("cota", "brazo_espesor", "espesor", en_el_perfil=False),
            Variable("cota", "brazo_eje_diametro", "Ø eje", "H7"),
            Variable("cota", "brazo_perno_diametro", "Ø del pomo", "H7"),
            Variable("cota", "brazo_cubo_diametro_radio", "R del cubo del eje"),
            Variable("cota", "brazo_extremo_diametro_radio", "R del extremo"),
            Variable("cota", "brazo_chaveta", "cara plana a"),
            Variable("cota", "brazo_chaveta_cuerda", "cuerda"),
            Variable("angulo", "brazo_chaveta_angulo", "girada"),
        ),
        ("plancha", "brazo_espesor"),
        "UN BRAZO MÁS: misma pletina, mismo cubo, mismo agujero en D y mismo perno de "
        "Ø6 en el extremo —que aquí lleva el pomo en vez de una biela—: lo único suyo es "
        "cuánto mide. Y eso tampoco es una elección de dibujo: 100 mm es lo que hace que "
        "los 4 N·m de C9 signifiquen 40 N en la mano, que es lo que empuja un adulto sin "
        "esforzarse. NO lleva calaje: la manivela se cala donde se quiera, que para eso se "
        "gira. Va en el eje rápido, con el piñón Z20 y el volante.",
        montaje=(
            "Fuera de la pila, encima del plato 3: cala en el eje de la manivela por la cara "
            "plana y lleva el pomo en el perno del extremo. Es lo único que sobresale por "
            "arriba."
        ),
        material="latón, pletina de 3 + pomo de madera",
        proceso="corte + taladro",
    ),
    "volante": Ficha(
        "disco de latón aligerado, en el eje de la manivela",
        1,
        (
            Variable("cota", "volante_diametro", "Ø del disco"),
            Variable("cota", "volante_espesor", "espesor", en_el_perfil=False),
            Variable("cota", "brazo_eje_diametro", "Ø del eje", "H7"),
            Variable("cota", "brazo_chaveta", "cara plana a"),
            Variable("cota", "brazo_chaveta_cuerda", "cuerda"),
            Variable("cota", "volante_aligeramiento_diametro", "Ø de cada aligeramiento"),
            Variable("cota", "volante_aligeramiento_al_centro", "del eje a cada aligeramiento"),
            Variable("angulo", "volante_aligeramiento_reparto", "entre aligeramientos"),
            Variable(
                "num",
                "manivela_vueltas_por_minuto",
                "a cuánto se gira (no se dibuja)",
                en_el_perfil=False,
            ),
        ),
        ("plancha", "volante_espesor"),
        "La única pieza cuyo diámetro no lo decide un encaje sino un REQUISITO: la inercia "
        "que hace falta para que la manivela no vaya a tirones. Dimensionado contra el peor "
        "caso de referencia —«firma», que pide un 59 % más que «hola»— y no contra el demo. "
        "Aligerado porque la inercia vive en el borde: seis agujeros de Ø24 quitan 100 g de "
        "latón y solo un 9 % de inercia. Cala con la misma cara plana que los brazos, sin "
        "prisionero: un taladro radial no sale de una plancha cortada.",
        montaje=(
            "Encima del plato 3, 1 mm por encima, en el eje de la manivela y bajo ella. Cala por "
            "la cara plana y no lleva prisionero. NO va en la bahía del reductor: centrado a 28 "
            "del árbol con R52, el árbol y la rueda Z60 lo atravesarían."
        ),
        material="latón, plancha de 6",
        proceso="corte + taladro",
    ),
    "base": Ficha(
        "tabla de nogal con los tres agujeros de los postes",
        1,
        (
            Variable("cota", "base_ancho", "ancho"),
            Variable("cota", "base_fondo", "fondo"),
            Variable("cota", "base_espesor", "espesor", en_el_perfil=False),
            Variable("cota", "poste_eje_diametro", "Ø de cada poste", "H7"),
            Variable("cota", "base_entre_postes", "entre postes"),
            Variable("angulo", "base_postes_angulo", "el tercero a"),
            Variable("cota", "base_poste_al_borde_izquierdo", "datum al borde izquierdo"),
            Variable("cota", "base_poste_al_borde_trasero", "datum al borde de atrás"),
            Variable("cota", "base_poste_empotrado", "fondo del agujero ciego", en_el_perfil=False),
        ),
        ("plancha", "base_espesor"),
        "La planta la cierran dos cosas que ya existían: el plato Ø170 por detrás y la "
        "tarjeta A7 por delante, con 10 mm de nogal a cada punta. Por eso mide 275 de "
        "fondo y no los 160 de la ficha de producto, que se escribió antes de saber "
        "dónde cae el papel. "
        "Los tres agujeros son el patrón de los platos visto desde otro datum: aquí no "
        "hay árbol que poner en el origen, así que el datum es un poste y el siguiente "
        "va sobre +X. Como los tres están a 120 grados del árbol, el triángulo es "
        "equilátero y se acota con un lado y 60 grados. "
        "Los agujeros son CIEGOS, 15 de los 25: la base no se taladra de parte a parte "
        "para que no asome el acero por debajo. "
        "Lo que esta tabla todavía no sabe es a qué altura queda el plato 1: "
        "base_al_plato son 75 provisionales y de ahí cuelga el largo del poste.",
        montaje=(
            "Es la pieza de abajo y no se monta sobre nada. Recibe los tres postes en sus "
            "agujeros ciegos de 15, y sobre ella apoyan los soportes de la mesa del papel. La "
            "tarjeta va suelta encima de la mesa."
        ),
        material="nogal americano macizo de 25",
        proceso="corte + taladro ciego",
    ),
    "balancin": Ficha(
        "barra de dos cubos diminuta, en la misma pletina de latón de 3",
        1,
        (
            Variable("cota", "balancin_entrada", "entre centros"),
            Variable("cota", "balancin_espesor", "espesor", en_el_perfil=False),
            Variable("cota", "balancin_eje_diametro", "Ø eje", "H7"),
            Variable("cota", "balancin_perno_diametro", "Ø pasador", "H7"),
            Variable("cota", "balancin_cubo_diametro_radio", "R del cubo del eje"),
            Variable("cota", "balancin_extremo_diametro_radio", "R del extremo"),
            Variable("cota", "balancin_chaveta", "cara plana a"),
            Variable("cota", "balancin_chaveta_cuerda", "cuerda"),
            Variable("angulo", "balancin_chaveta_angulo", "girada"),
        ),
        ("plancha", "balancin_espesor"),
        "Mide 6,333 entre centros porque es lo que la relación 6 obliga: el pasador del "
        "seguidor va a 38 del pivote y 38 partido por 6 es esto. De ahí sale todo lo "
        "demás de la pieza, incluido que su eje sea de 4 y no de 10 como los otros tres: "
        "con 10 el pasador se metería DENTRO del agujero del eje, pared -0,17, y con 4 "
        "quedan 3,33. Esa pared es la cota que manda aquí.",
        montaje=(
            "Calado por la cara plana en el extremo de popa del eje del balancín, apuntando "
            "HACIA ARRIBA y con el cubo por encima del plano de seguidores. El pasador de Ø2 "
            "recibe la bieleta isógona, que viene horizontal desde el agujero del seguidor 3. "
            "En el mismo eje, 90,75 mm a proa, va la palanca del lápiz."
        ),
        material="latón, pletina de 3",
        proceso="corte + taladro",
    ),
    "platina_levas": Ficha(
        "disco de contrachapado con los siete agujeros del mecanismo",
        3,
        (
            Variable("cota", "platina_diametro", "Ø del disco"),
            Variable("cota", "platina_espesor", "espesor", en_el_perfil=False),
            Variable("cota", "rodamiento_arbol_alojamiento_diametro", "Ø del árbol", "H7"),
            Variable("cota", "poste_eje_diametro", "Ø de cada poste", "h6"),
            Variable("cota", "poste_radio_al_arbol", "del árbol a los postes"),
            Variable("angulo", "poste_reparto", "entre postes"),
            Variable("cota", "brazo_eje_diametro", "Ø de cada pivote"),
            Variable("cota", "platina_pivote_al_arbol", "del árbol a los pivotes"),
            Variable(
                "angulo",
                "platina_pivote_angulo_izquierdo_positivo",
                "pivote izquierdo a, bajo +X",
            ),
            Variable("angulo", "platina_pivote_angulo_derecho", "pivote derecho a"),
            Variable("cota", "reductor_entre_ejes", "del árbol a la manivela"),
            Variable(
                "angulo",
                "platina_manivela_angulo_positivo",
                "eje de la manivela a, bajo +X",
            ),
        ),
        ("plancha", "platina_espesor"),
        "Un disco y no un rectángulo: los agujeros caben dentro de 71,063 —los postes "
        "son los de más afuera— así que el contorno se dice con una sola cota. Van "
        "TRES, en los mismos postes de Ø8, que por eso pasan de 70 a 105. El tercero "
        "cierra la bahía del reductor y da el SEGUNDO apoyo del eje de la manivela: "
        "con un solo rodamiento el eje queda en voladizo cargando 294 g de volante y "
        "los 40 N de la mano. El séptimo agujero no sujeta nada en el plato de abajo, "
        "y a cambio los tres platos son LA MISMA PIEZA. Que haya más de un plato no es "
        "por rigidez —un poste en voladizo flecta 0,0135 mm con 5 N, contra un "
        "presupuesto de error de 2,79— sino porque deja el mecanismo a la vista, que "
        "es el argumento del producto.",
        montaje=(
            "Los tres son la misma pieza y van a tres alturas: el 1 sobre los separadores de la "
            "base, el 2 a 58 por encima y el 3 a 20 más. Los tres postes los atraviesan y son "
            "lo que los separa y los alinea. El Ø19 del centro y el de 28 llevan los "
            "rodamientos del árbol y del eje de la manivela."
        ),
        material="contrachapado de abedul de 9",
        proceso="corte láser o CNC",
    ),
    "seguidor": Ficha(
        "barra de dos cubos con cuatro agujeros en línea, en POM-C de 5",
        3,
        (
            Variable("cota", "brazo_seguidor", "entre centros"),
            Variable("cota", "seguidor_espesor", "espesor", en_el_perfil=False),
            Variable("cota", "seguidor_pivote_diametro", "Ø alojamiento del casquillo", "H7"),
            Variable("cota", "seguidor_cubo_diametro", "Ø del cubo"),
            Variable("cota", "seguidor_extremo_diametro", "Ø del extremo"),
            Variable("cota", "seguidor_rodillo_diametro", "Ø paso del eje del rodillo"),
            Variable("cota", "seguidor_muelle_radio", "pivote al muelle"),
            Variable("cota", "seguidor_muelle_diametro", "Ø anclaje del muelle"),
            Variable("cota", "union_sector_seguidor_cerca", "pivote al tornillo cercano"),
            Variable("cota", "union_sector_seguidor_lejos", "pivote al tornillo lejano"),
            Variable("cota", "union_sector_seguidor_diametro", "Ø paso de los dos al sector"),
            Variable(
                "cota", "rodillo_descuelgue_1", "baja el rodillo, canal 1", en_el_perfil=False
            ),
            Variable("cota", "rodillo_descuelgue_2", "canal 2", en_el_perfil=False),
            Variable("cota", "rodillo_descuelgue_3", "canal 3", en_el_perfil=False),
        ),
        ("plancha", "seguidor_espesor"),
        "La misma plancha de POM-C 5 que las levas y el sector, y justo el largo útil "
        "del casquillo GFM-0810-06, que mide 6 con 1 de valona. El muelle va cerca del "
        "pivote a propósito: su fuerza va con 1/r y su recorrido con r, así que la "
        "variación del par va con r². A 12 varía un 9,6 % en todo el barrido; a 30, un 60 %. "
        "Y el sector se cala con DOS tornillos en línea con el brazo: su agujero es de "
        "paso y no sitúa nada, y una brida con ellos a 11 pediría un cubo de Ø28.",
        montaje=(
            "Pivota sobre su poste a través del casquillo igus, en el plano único de "
            "seguidores, a 21 de la cara baja de la primera leva. Por encima lleva el sector "
            "atornillado; por debajo, el eje del rodillo descolgado hasta su leva: 21, 14 o 7 "
            "según el canal, que es lo único que distingue un montaje de otro."
        ),
        material="POM-C negro, plancha de 5",
        proceso="fresado CNC",
    ),
    "eje_manivela": Ficha(
        "barra Ø10 h6 con una cara plana, como los de pivote",
        1,
        (
            Variable("cota", "brazo_eje_diametro", "Ø", "h6"),
            Variable("cota", "eje_manivela_largo", "largo", en_el_perfil=False),
            Variable("cota", "brazo_chaveta", "cara plana a"),
            Variable("cota", "brazo_chaveta_cuerda", "cuerda"),
            Variable("angulo", "brazo_chaveta_angulo", "girada"),
        ),
        ("barra", "eje_manivela_largo"),
        "La misma barra que los ejes de pivote, con otro largo: lleva el piñón, el volante "
        "y la manivela, y las tres calan por la misma cara plana. No estaba en el listado: "
        "el volante y la manivela hablaban de él y nadie lo había declarado.",
        montaje=(
            "Gira en dos rodamientos 6800, en el plato 2 y en el plato 3, a 28 del árbol. En "
            "la bahía lleva el piñón; encima del plato 3, el volante y luego la manivela. "
            "Empieza 1 por debajo del plato 2 y acaba 1 por encima de la manivela: 51."
        ),
        material="acero W10 h6 rectificado",
        proceso="corte a medida + fresado de la cara plana",
    ),
    "casquillo_rueda": Ficha(
        "casquillo de latón: la rueda Z60 en el árbol",
        1,
        (
            Variable("cota", "casquillo_rueda_diametro", "Ø exterior", "p6"),
            Variable("cota", "eje_diametro", "Ø interior", "H7"),
            Variable("cota", "casquillo_rueda_largo", "largo", en_el_perfil=False),
        ),
        ("barra", "casquillo_rueda_largo"),
        "La rueda Z60 viene de fábrica con agujero de 15 H7 y el árbol es de 10: sin él no "
        "hay encaje. Va entre una pieza de catálogo y un contrato congelado, y por eso se "
        "hace a medida y no se cambia ninguno de los dos.",
        montaje=(
            "A presión en la rueda, en la bahía del reductor, a la altura del piñón. Al árbol, "
            "con un prisionero M3: es lo que pasa el par de la manivela a las levas."
        ),
        material="latón, barra de Ø16",
        proceso="torneado + taladro roscado M3",
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
    guardar(doc, destino)
    return destino
