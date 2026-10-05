"""El conjunto en 3D: sólidos de la plataforma y dónde va cada uno.

**Qué problema resuelve.** `emit/plataforma.py` da el *perfil* de cada
pieza y `scripts/dibujar_conjunto.py` da el plano de conjunto en dos
vistas. Entre los dos falta lo único que puede contestar una pregunta que
hoy no contesta nadie: **qué se toca con qué mientras la máquina gira.**

`compile/conjunto.py` mira en el plano, y solo mira **las levas contra los
postes**. No mira el brazo contra el poste, ni el sector contra el plato,
ni el volante contra nada. Y Onshape tampoco: su detección de
interferencias es estática, hay que congelar θ y repetir a mano, y eso en
una rejilla de 24 posiciones ya es una tarde (ver `docs/ensamblaje.md`).

Aquí el barrido es un bucle, y por tanto puede ser un test.

**El compilador es el solucionador, y no por falta de otro.** build123d
tiene articulaciones —`RevoluteJoint` y compañía— pero `connect_to()`
construye un **árbol**: coloca el hijo respecto del padre y no reconcilia
dos caminos que llegan al mismo sitio. El cinco barras es un lazo cerrado,
el contacto leva-rodillo no es una articulación y el cabestrante es una
relación entre dos giros: ninguno de los tres cabe. Lo que sí cabe, y es
además lo que mandan las reglas 1 y 2, es que la cinemática la resuelva
`core/` —pura, en θ, con tests— y que aquí solo se **coloque**:

    θ → core/ → ψ de cada seguidor → este módulo → sólidos en su sitio

Un solucionador aquí sería cinemática fuera del núcleo.

**Unidades: milímetros**, como el resto de `emit/`. Los perfiles ya llegan
en mm desde `emit.plataforma.contrato_mm`.
"""

from __future__ import annotations

import math
from collections.abc import Callable
from dataclasses import dataclass
from functools import cache
from typing import Any

from emit.plataforma import (
    BRAZOS,
    LISTADO,
    PERFILES,
    Arco,
    Perfil,
    Punto,
    Segmento,
    brazo,
    contrato_mm,
    texto,
)

_FALTA = "hace falta el kernel OCCT: uv sync --group cad"

CIERRE = 1e-6
"""Cuándo dos extremos de un perfil se consideran el mismo punto, en mm.

Los perfiles salen de senos y cosenos del contrato, así que un extremo
compartido no coincide al bit. Un micrómetro es mil veces menor que
cualquier rasgo de estas piezas y mil veces mayor que el redondeo."""


# ---------------------------------------------------------------------------
# De un perfil plano a un sólido
# ---------------------------------------------------------------------------


def _extremos(elemento: Arco | Segmento) -> tuple[Punto, Punto]:
    """Por dónde empieza y acaba un elemento del perfil."""
    if isinstance(elemento, Segmento):
        return elemento.a, elemento.b
    cx, cy, r = elemento.centro[0], elemento.centro[1], elemento.radio
    return (
        (cx + r * math.cos(elemento.desde), cy + r * math.sin(elemento.desde)),
        (cx + r * math.cos(elemento.hasta), cy + r * math.sin(elemento.hasta)),
    )


def _mismo(a: Punto, b: Punto) -> bool:
    return math.hypot(a[0] - b[0], a[1] - b[1]) <= CIERRE


def bucles(perfil: Perfil) -> list[Perfil]:
    """Parte un perfil en los lazos cerrados que lo componen.

    Un `Perfil` es una lista plana donde el contorno viene primero y los
    agujeros detrás, encadenados: el final de un elemento es el principio
    del siguiente hasta que se vuelve al punto de partida. Un círculo
    entero es un lazo de un solo elemento, porque empieza y acaba igual.

    Se parte siguiendo la conectividad y no por orden de aparición: así un
    perfil nuevo no tiene que declarar dónde acaba su contorno.
    """
    salida: list[Perfil] = []
    actual: Perfil = []
    inicio: Punto | None = None
    for elemento in perfil:
        a, b = _extremos(elemento)
        if inicio is None:
            inicio = a
        actual.append(elemento)
        if _mismo(b, inicio):
            salida.append(actual)
            actual, inicio = [], None
    if actual:
        raise ValueError(f"el perfil deja {len(actual)} elementos sin cerrar un lazo")
    return salida


def _extension(bucle: Perfil) -> float:
    """Diagonal de la caja del lazo. Decide cuál es el contorno exterior."""
    xs: list[float] = []
    ys: list[float] = []
    for elemento in bucle:
        if isinstance(elemento, Arco):
            cx, cy, r = elemento.centro[0], elemento.centro[1], elemento.radio
            xs += [cx - r, cx + r]
            ys += [cy - r, cy + r]
        else:
            xs += [elemento.a[0], elemento.b[0]]
            ys += [elemento.a[1], elemento.b[1]]
    return math.hypot(max(xs) - min(xs), max(ys) - min(ys))


def _trazar(bucle: Perfil) -> None:
    """Dibuja un lazo dentro de un `BuildLine` ya abierto."""
    from build123d import CenterArc, Line

    for elemento in bucle:
        if isinstance(elemento, Segmento):
            Line(elemento.a, elemento.b)
        else:
            CenterArc(
                center=elemento.centro,
                radius=elemento.radio,
                start_angle=math.degrees(elemento.desde),
                arc_size=math.degrees(elemento.hasta - elemento.desde),
            )


def solido_de_perfil(perfil: Perfil, espesor: float) -> Any:
    """Extruye un perfil de la plataforma: contorno fuera, lazos dentro.

    **Los arcos entran como arcos**, no como polilínea densa. Por la vía de
    `emit/step.py` —que parte de un `Pieza`, cuyo contorno es una lista de
    puntos— un cubo de Ø18 llegaría facetado; aquí llega redondo, y el
    hueco que mide un barrido de interferencia depende de eso.
    """
    try:
        from build123d import BuildLine, BuildPart, BuildSketch, Mode, extrude, make_face
    except ImportError as exc:  # pragma: no cover - depende del entorno
        raise ImportError(_FALTA) from exc

    lazos = sorted(bucles(perfil), key=_extension, reverse=True)
    if not lazos:
        raise ValueError("el perfil no tiene ningún lazo cerrado")

    with BuildPart() as parte:
        with BuildSketch():
            with BuildLine():
                _trazar(lazos[0])
            make_face()
            for agujero in lazos[1:]:
                with BuildLine():
                    _trazar(agujero)
                make_face(mode=Mode.SUBTRACT)
        extrude(amount=espesor)

    if parte.part is None:  # pragma: no cover - solo si el contorno no cierra
        raise ValueError("el perfil no llegó a formar un sólido")
    return parte.part


def perfil_y_espesor(nombre: str, c: dict[str, float] | None = None) -> tuple[Perfil, float]:
    """El perfil de una pieza de la plataforma y por dónde se extruye.

    El espesor sale de `LISTADO[nombre].solido`, que es la misma pareja
    (clase, cota) que usa la hoja para decidir si la segunda vista es una
    sección o un alzado. Una sola declaración para las dos cosas.
    """
    c = contrato_mm() if c is None else c
    perfil = brazo(nombre, c) if nombre in BRAZOS else PERFILES[nombre](c)
    _, cota = LISTADO[nombre].solido
    return perfil, c[cota]


def solido_de(nombre: str, c: dict[str, float] | None = None) -> Any:
    """El sólido de una pieza de la plataforma, apoyado en Z = 0."""
    perfil, espesor = perfil_y_espesor(nombre, c)
    return solido_de_perfil(perfil, espesor)


# ---------------------------------------------------------------------------
# Dónde va cada pieza
# ---------------------------------------------------------------------------


def alturas(c: dict[str, float] | None = None) -> dict[str, tuple[float, float]]:
    """La pila vertical, de la cara alta de la base hacia arriba, en mm.

    Todo sale de la cadena declarada: `base_al_plato`, `platina_espesor`,
    `leva_sobre_plato`, `pila_altura`, `seguidor_plano_z`, `poste_vano`,
    `reductor_bahia`, `brazo_espesor` y `brazo_arandela`. No hay ni un número
    suelto, y por eso mover `base_al_plato` mueve la máquina entera.

    Vive aquí y no en el script del plano de conjunto porque la usan los
    dos: **el dibujo en dos vistas y el montaje en tres dimensiones tienen
    que colocar las piezas en el mismo sitio**, y dos copias de una pila de
    alturas se separan a la tercera cota que se mueva.
    """
    c = contrato_mm() if c is None else c
    bap, pl = c["base_al_plato"], c["platina_espesor"]
    p1 = (bap, bap + pl)
    leva0 = p1[1] + c["leva_sobre_plato"]
    seg = leva0 + c["seguidor_plano_z"]
    # El sector va sobre un calzo: la cinta, en su plano, tiene que pasar por
    # encima de los seguidores que cruza sin rozarlos.
    sobre = seg + c["seguidor_espesor"] + c["calzo_sector_espesor"]
    sector = (
        sobre,
        sobre + c["amplificador_sector_espesor"],
    )
    p2 = (p1[1] + c["poste_vano"], p1[1] + c["poste_vano"] + pl)
    p3 = (p2[1] + c["reductor_bahia"], p2[1] + c["reductor_bahia"] + pl)
    eje_balancin = (
        seg + c["seguidor_espesor"] + c["holgura_minima"] + c["balancin_cubo_diametro"] / 2
    )
    # El varillaje, de arriba abajo bajo el plato 1: cada brazo en su plano,
    # 3 de pletina y medio de arandela entre uno y otro. Con 1 de desnivel
    # los proximales se solapaban donde se cruzan. **Cada distal justo debajo
    # de su proximal**: así cada codo une dos planos contiguos y su perno no
    # atraviesa el plano de otro brazo. Con los dos proximales arriba, el
    # perno del codo 1 cruzaba el plano del proximal 2, que pasa por debajo
    # del codo 1 porque los proximales se cruzan (docs/propuesta_codo.md).
    paso = c["brazo_espesor"] + c["brazo_arandela"]
    tope = p1[0] - HOLGURA_AXIAL
    brazos = {
        nombre: (tope - (i + 1) * c["brazo_espesor"] - i * c["brazo_arandela"], tope - i * paso)
        for i, nombre in enumerate(ORDEN_DE_LOS_BRAZOS)
    }
    # El tambor, centrado en el sector: coplanarios, que es lo que sustituye
    # a las pestañas.
    medio_sector = sum(sector) / 2
    tambor = (
        medio_sector - c["amplificador_tambor_ancho"] / 2,
        medio_sector + c["amplificador_tambor_ancho"] / 2,
    )
    bahia = (p2[1], p3[0])
    medio_bahia = sum(bahia) / 2
    volante = (p3[1] + HOLGURA_AXIAL, p3[1] + HOLGURA_AXIAL + c["volante_espesor"])
    manivela = (volante[1] + HOLGURA_AXIAL, volante[1] + HOLGURA_AXIAL + c["brazo_espesor"])
    return {
        "base": (-c["base_espesor"], 0.0),
        "mesa": (c["mesa_altura"] - c["mesa_espesor"], c["mesa_altura"]),
        "plato1": p1,
        "levas": (leva0, leva0 + c["pila_altura"]),
        "seguidores": (seg, seg + c["seguidor_espesor"]),
        "sector": sector,
        "balancin": (eje_balancin, eje_balancin),
        "plato2": p2,
        "bahia": bahia,
        "engrane": (
            medio_bahia - c["casquillo_rueda_largo"] / 2,
            medio_bahia + c["casquillo_rueda_largo"] / 2,
        ),
        "plato3": p3,
        "volante": volante,
        "manivela": manivela,
        "tambor": tambor,
        "punta_tubo": (p1[0] - c["punta_tubo_largo"], p1[0]),
        "poste": (-c["base_poste_empotrado"], p3[1]),
        **brazos,
    }


ORDEN_DE_LOS_BRAZOS = ("proximal_1", "distal_1", "proximal_2", "distal_2")
"""De arriba abajo bajo el plato 1. Cada distal bajo su proximal."""

JUEGO_GIRATORIO = 0.02
"""Juego diametral de un pasador que gira en su agujero (H7/h8 en Ø2)."""

HOLGURA_AXIAL = 1.0
"""La holgura de 1 mm que ya pedía la ficha del proximal contra el plato 1,
y la que se deja entre el plato 3, el volante y la manivela."""


@dataclass(frozen=True)
class Grupo:
    """Un subsistema del conjunto: para qué está, cómo se pinta y qué piezas
    son suyas, por el principio de su nombre."""

    nombre: str
    objetivo: str
    color: str
    opacidad: float
    prefijos: tuple[str, ...]

    @property
    def sigla(self) -> str:
        """Tres letras para los códigos de plano: P-AMP-03, G-AMP."""
        return SIGLAS[self.nombre]


SIGLAS = {
    "bastidor": "BAS",
    "levas": "LEV",
    "cartucho": "CAR",
    "entre_puntos": "ENT",
    "accionamiento": "ACC",
    "seguidores": "SEG",
    "amplificador": "AMP",
    "cinco_barras": "CBR",
    "levantamiento": "ELV",
    "portalapiz": "POR",
}
"""La sigla de cada grupo, **declarada** y no sacada del nombre: las tres
primeras letras de «levas» y de «levantamiento» son las mismas."""


GRUPOS: tuple[Grupo, ...] = (
    Grupo(
        "bastidor",
        "Lo que no se mueve: base, postes, platos y rodamientos",
        "#9aa0a6",
        0.25,
        (
            "base",
            "poste1",
            "poste2",
            "poste3",
            "plato",
            "rodamiento_",
            "collar_plato_",
            "tubo_separador_",
        ),
    ),
    Grupo(
        "levas",
        "Lo único que se fabrica para cada pedido: la frase del cliente en tres levas",
        "#ff6a00",
        1.0,
        ("leva_",),
    ),
    Grupo(
        "cartucho",
        "El metal que enhebra las levas y viaja con ellas: igual en todos los pedidos",
        "#c9a227",
        1.0,
        ("eje_cartucho", "separador_", "pasador_indice"),
    ),
    Grupo(
        "entre_puntos",
        "Lo que sujeta, arrastra y pone en fase el cartucho",
        "#2f6fdb",
        1.0,
        ("munon", "eje_motriz", "garra", "pasador_garra", "muelle_garra", "circlip_garra_"),
    ),
    Grupo(
        "accionamiento",
        texto("La manivela, el volante y el reductor {reductor_relacion}:1"),
        "#8e44ad",
        1.0,
        ("rueda", "casquillo_rueda", "pinon", "eje_manivela", "volante", "manivela"),
    ),
    Grupo(
        "seguidores",
        "Lo que lee las levas: seguidores, rodillos, sus ejes, topes y muelles",
        "#27ae60",
        1.0,
        (
            "seguidor_",
            "rodillo_",
            "eje_rodillo_",
            "collar_seguidor_",
            "placa_tope_",
            "pasador_tope_",
            "muelle_seguidor_",
        ),
    ),
    Grupo(
        "amplificador",
        texto("El cabestrante {relacion_cabestrante}:1: sectores, tambores y ejes de pivote"),
        "#f1c40f",
        1.0,
        (
            "sector_",
            "tambor_",
            "eje_pivote_",
            "cinta_",
            "mordaza_",
            "tornillo_tambor_",
            "calzo_sector_",
            "tornillos_sector_",
            "tornillo_mordaza_",
        ),
    ),
    Grupo(
        "cinco_barras",
        "El brazo que lleva la punta por el papel",
        "#e74c3c",
        1.0,
        ("proximal_", "distal_", "perno_codo_", "arandela_codo_", "casquillo_punta"),
    ),
    Grupo(
        "levantamiento",
        "Del seguidor 3 a la mesa: balancín, bieleta, tirante y mesa",
        "#17a2b8",
        1.0,
        (
            "eje_balancin",
            "balancin",
            "palanca_lapiz",
            "apoyo_balancin",
            "bieleta",
            "casquillo_bieleta",
            "bulon_tirante",
            "tirante",
            "biela_mesa",
            "soporte_mesa",
            "eje_mesa",
            "orejeta_mesa",
            "mesa",
        ),
    ),
    Grupo(
        "portalapiz",
        "La punta: tubo, horquilla, pinza, láminas y portaminas",
        "#d63384",
        1.0,
        (
            "tubo_punta",
            "brazo_horquilla",
            "poste_horquilla",
            "pinza",
            "lamina_flexura_",
            "portaminas",
        ),
    ),
)
"""Los subsistemas del conjunto, en el orden en que se lee la máquina: de lo
fijo a la punta. Es lo que el visor pinta de un color por grupo y lo que la
auditoría de conjunto cuenta; un test exige que toda pieza colocada caiga en
exactamente uno."""


NIVELES: dict[str, tuple[str, ...]] = {
    "levas": ("levas",),
    "cartucho": ("levas", "cartucho"),
    "maquina": tuple(
        g
        for g in (
            "bastidor",
            "entre_puntos",
            "accionamiento",
            "seguidores",
            "amplificador",
            "cinco_barras",
            "levantamiento",
            "portalapiz",
        )
    ),
}
"""Los tres niveles en que se fabrica y se monta el escribiente: las levas,
por pedido; el cartucho, las levas con el metal que las enhebra, que se
monta por pedido con piezas de stock; y la máquina, la plataforma, igual en
todas. Es la división que importa para buscar mejoras de montaje y de
fabricación, porque cada nivel lo hace alguien distinto y con otra
frecuencia."""


def nivel_de(grupo: str) -> str:
    """El nivel más estrecho al que pertenece un grupo."""
    for nivel in ("levas", "cartucho", "maquina"):
        if grupo in NIVELES[nivel]:
            return nivel
    raise ValueError(f"el grupo «{grupo}» no está en ningún nivel")


@cache
def _prefijos_de_la_tornilleria() -> tuple[tuple[str, str], ...]:
    from emit.materiales import tornilleria

    return tuple(sorted({(f.en_3d, f.grupo) for f in tornilleria() if f.en_3d}))


def _grupo_de_la_tornilleria(nombre: str) -> set[str]:
    return {g for prefijo, g in _prefijos_de_la_tornilleria() if nombre.startswith(prefijo)}


def grupo_de(nombre: str) -> Grupo:
    """El grupo de una pieza colocada. Exactamente uno: dos sería ambiguo, y
    ninguno, una pieza que nadie audita."""
    suyos = [g for g in GRUPOS if nombre.startswith(g.prefijos)]
    # La tornillería cae en el grupo que declara su línea de compra
    # (`emit.materiales.Fijacion.grupo`), que es el que le da su marca.
    suyos += [g for g in GRUPOS if g.nombre in _grupo_de_la_tornilleria(nombre)]
    suyos = list(dict.fromkeys(suyos))
    if len(suyos) != 1:
        raise ValueError(f"«{nombre}» cae en {len(suyos)} grupos: {[g.nombre for g in suyos]}")
    return suyos[0]


@dataclass(frozen=True)
class Colocada:
    """Una pieza con su sólido ya puesto donde va."""

    nombre: str
    solido: Any
    movil: bool
    """Si se mueve al girar el árbol. Lo que decide qué pares hay que
    barrer: dos piezas quietas no pueden empezar a tocarse."""


def _poner(solido: Any, angulo: float = 0.0, centro: Punto = (0.0, 0.0), z: float = 0.0) -> Any:
    """Gira un sólido sobre su Z y lo lleva a su sitio. Ángulo en radianes.

    El giro va **antes** que la traslación: el perfil se dibuja con su
    datum en el origen, así que girar después lo mandaría de paseo.
    """
    from build123d import Pos, Rot

    return Pos(centro[0], centro[1], z) * Rot(Z=math.degrees(angulo)) * solido


@dataclass(frozen=True)
class Estado:
    """La máquina en un ángulo del árbol. Todo lo calcula `core/`.

    `desviaciones` es lo que se aparta cada seguidor de su punto de
    diseño, que es para lo que se sintetiza la leva. `psi` es el ángulo
    **absoluto** de cada brazo en el marco del cinco barras, que ya lleva
    dentro la relación y el calaje. Son dos cosas distintas y confundirlas
    es la trampa del calaje que `CLAUDE.md` documenta.
    """

    theta: float
    desviaciones: tuple[float, float, float]
    psi_izquierdo: float
    psi_derecho: float
    giro_balancin: float = 0.0
    """Radianes que gira el eje del balancín: positivo baja la mesa. Lo
    calcula `compile.levantamiento.giro_del_eje` desde la desviación del
    seguidor 3, cerrando el lazo de la bieleta."""
    caida_mesa: float = 0.0
    """Metros que baja la mesa desde la posición de escritura."""


def _del_cinco_barras(c: dict[str, float]) -> Callable[[Punto], Punto]:
    """Lleva un punto del marco del cinco barras al de la leva.

    Los dos marcos existen y el contrato ata el uno al otro con
    `brazo_origen_x/y` y `brazo_orientacion`. Aquí se monta en el de la
    **leva**, porque es donde viven los pivotes de los seguidores y los
    perfiles de leva, y porque una interferencia no depende del marco.
    """
    g = c["brazo_origen_giro"]
    ox, oy = c["brazo_origen_x"], c["brazo_origen_y"]

    def llevar(p: Punto) -> Punto:
        return (
            p[0] * math.cos(g) - p[1] * math.sin(g) + ox,
            p[0] * math.sin(g) + p[1] * math.cos(g) + oy,
        )

    return llevar


def taller(c: dict[str, float] | None = None) -> dict[str, Any]:
    """Los sólidos de la máquina sin colocar, uno por pieza distinta.

    Extruir un perfil cuesta, y en un barrido se repite en cada ángulo la
    misma plancha. Construirlos una vez y recolocarlos deja el barrido en
    segundos en vez de en minutos; es la diferencia entre un test que se
    ejecuta y uno que se desactiva.
    """
    from emit.catalogo import cargar
    from emit.catalogo import solido_de as solido_comercial

    c = contrato_mm() if c is None else c
    from build123d import Plane, mirror

    piezas = {n: solido_de(n, c) for n in LISTADO}
    # El distal es curvo y los dos son la misma pieza: el izquierdo, volteado.
    piezas["brazo_distal_volteado"] = mirror(piezas["brazo_distal"], about=Plane.XZ)
    comerciales = {p.nombre: p for p in cargar()}
    piezas["poste"] = solido_comercial(comerciales["poste_pivote"])
    for nombre in (
        "rodamiento_arbol",
        "rodillo_seguidor",
        "rueda_reductor",
        "pinon_reductor",
        "portaminas",
    ):
        piezas[nombre] = solido_comercial(comerciales[nombre])
    piezas.update(_detalles_del_cartucho(c, piezas))
    return piezas


def _direccion_de_salida(c: dict[str, float]) -> tuple[Punto, Punto]:
    """La dirección por la que sale el cartucho y la que queda a su derecha,
    en el marco de la leva y en fase cero. La ranura de la garra y la U del
    muñón van a lo largo de la primera: así el cartucho entra deslizando."""
    a = c["cartucho_salida_angulo"]
    return (math.cos(a), math.sin(a)), (math.sin(a), -math.cos(a))


def _caja(
    c: dict[str, float], centro: tuple[float, float, float], largo: float, ancho: float, alto: float
) -> Any:
    """Una caja con el largo a lo largo de la salida, centrada en `centro`."""
    from build123d import Box, Pos, Rot

    return Pos(*centro) * Rot(Z=math.degrees(c["cartucho_salida_angulo"])) * Box(largo, ancho, alto)


def _detalles_del_cartucho(c: dict[str, float], piezas: dict[str, Any]) -> dict[str, Any]:
    """Lo que el perfil extruido no lleva: el tetón y la ranura del eje del
    cartucho, la U del muñón, la lengüeta y las ranuras de la garra, y el
    pasador de la garra. Cada uno en el marco de su pieza: el eje en el
    origen, z = 0 en su cara de abajo y +X en fase cero."""
    from build123d import Align, Cylinder, Pos

    u, n = _direccion_de_salida(c)
    abajo = (Align.CENTER, Align.CENTER, Align.MIN)
    r_eje = c["eje_diametro"] / 2.0
    fuera = c["garra_ranura_desplazamiento"]

    # El eje del cartucho, con su valona en una pieza: la valona con el
    # taladro del pasador abajo, el eje encima, el tetón debajo y la ranura
    # descentrada arriba, pasante a lo largo de la salida. El perfil del
    # listado es su planta; el sólido se hace aquí.
    largo = c["cartucho_eje_largo"]
    valona = Cylinder(c["cubo_diametro"] / 2.0, c["cubo_espesor"], align=abajo) - Pos(
        c["pasador_radio"], 0, 0
    ) * Cylinder(c["pasador_diametro"] / 2.0, c["cubo_espesor"], align=abajo)
    cuerpo = valona + Cylinder(r_eje, largo, align=abajo)
    teton = Pos(0, 0, -c["cartucho_teton_largo"]) * Cylinder(
        c["cartucho_teton_diametro"] / 2.0, c["cartucho_teton_largo"], align=abajo
    )
    fondo = c["garra_ranura_profundidad"]
    ranura = _caja(
        c,
        (n[0] * fuera, n[1] * fuera, largo - fondo / 2.0),
        4 * r_eje,
        c["garra_ranura_ancho"],
        fondo,
    )
    eje_cartucho = cuerpo + teton - ranura

    # El muñón: la U, de boca `munon_horquilla_ancho`, desde el eje hacia la
    # salida, en lo alto.
    alto_u = c["munon_horquilla_alto"]
    boca = c["munon_horquilla_ancho"]
    tope = c["munon_largo"]
    u_recta = _caja(
        c, (u[0] * 2 * r_eje / 2, u[1] * 2 * r_eje / 2, tope - alto_u / 2), 2 * r_eje, boca, alto_u
    )
    u_fondo = Pos(0, 0, tope - alto_u) * Cylinder(boca / 2.0, alto_u, align=abajo)
    munon = piezas["munon"] - u_recta - u_fondo

    # La garra: lengüeta 0,1 más estrecha que la ranura y 0,1 más corta que
    # su fondo, para que el manguito apoye con su cara y no con la lengüeta;
    # y las dos ranuras verticales del pasador, a lo largo de la salida.
    lengueta = _caja(
        c,
        (n[0] * fuera, n[1] * fuera, -(fondo - 0.1) / 2.0),
        2 * r_eje - 0.2,
        c["garra_ranura_ancho"] - 0.1,
        fondo - 0.1,
    )
    alto = c["garra_alto"]
    paso = c["garra_pasador_diametro"] + 0.1
    ranuras = _caja(
        c,
        (0.0, 0.0, alto / 2.0),
        c["garra_diametro"] + 2.0,
        paso,
        alto - 0.8,
    ) - Cylinder(r_eje, alto, align=abajo)
    garra = piezas["garra"] + lengueta - ranuras

    # El pasador de la garra, transversal al eje motriz, a lo largo de la salida.
    from build123d import Location, Plane, Vector

    r_pasador = c["garra_pasador_diametro"] / 2.0 - JUEGO_GIRATORIO / 2.0
    medio = c["garra_diametro"] / 2.0 + 0.5
    pasador_garra = Location(
        Plane(origin=Vector(-u[0] * medio, -u[1] * medio, 0.0), z_dir=Vector(u[0], u[1], 0.0))
    ) * Cylinder(r_pasador, 2 * medio, align=abajo)
    # El taladro del pasador en el eje motriz, cuyo pie queda 1 sobre la
    # cabeza del cartucho: el pasador está a `garra_pasador_alto` de ella.
    z_taladro = c["garra_pasador_alto"] - 1.0
    taladro = Location(
        Plane(origin=Vector(-u[0] * 6, -u[1] * 6, z_taladro), z_dir=Vector(u[0], u[1], 0.0))
    ) * Cylinder(c["garra_pasador_diametro"] / 2.0, 12.0, align=abajo)
    eje_motriz = piezas["eje_motriz"] - taladro
    return {
        "eje_cartucho": eje_cartucho,
        "munon": munon,
        "garra": garra,
        "pasador_garra": pasador_garra,
        "eje_motriz": eje_motriz,
    }


def _cilindro(
    radio: float, desde: tuple[float, float, float], hasta: tuple[float, float, float]
) -> Any:
    """Un cilindro entre dos puntos: varillas, patas y taladros."""
    from build123d import Align, Cylinder, Location, Plane, Vector

    a, b = Vector(*desde), Vector(*hasta)
    return Location(Plane(origin=a, z_dir=b - a)) * Cylinder(
        radio, (b - a).length, align=(Align.CENTER, Align.CENTER, Align.MIN)
    )


def _en_plano(
    solido: Any,
    origen: tuple[float, float, float],
    x: tuple[float, float, float],
    z: tuple[float, float, float],
) -> Any:
    """Lleva un sólido de su marco al plano dado: su X a `x`, su Z a `z`."""
    from build123d import Location, Plane

    return Location(Plane(origin=origen, x_dir=x, z_dir=z)) * solido


def colocar(
    levas: list[Any],
    seguidores: list[Any],
    estado: Estado,
    c: dict[str, float] | None = None,
    piezas_base: dict[str, Any] | None = None,
) -> list[Colocada]:
    """La máquina entera en 3D, en el marco de la leva, en el estado dado.

    `levas` son las `Pieza` que salen de compilar el pedido y `seguidores`
    los `core.cam.synth.Seguidor` de la máquina: este módulo **no importa
    el compilador**, porque los emisores están debajo de él. Quien llame
    calcula el estado —el giro de cada brazo, el del eje del balancín y lo
    que baja la mesa—; aquí solo se coloca.

    Lo que no entra: la cinta del cabestrante y sus cuatro mordazas, cuya
    posición sobre el sector dice su ficha, y la tornillería.
    """
    from build123d import Pos

    from emit import fijaciones as fj
    from emit.step import solido_de_pieza

    c = contrato_mm() if c is None else c
    hecho = taller(c) if piezas_base is None else piezas_base
    z, piezas = alturas(c), []
    cortes: list[tuple[str, Any]] = []
    """(pieza, sólido que se le resta): el agujero de cada tornillo en la pieza
    que lo recibe. Se aplica al final, cuando ya está todo colocado."""
    al_marco = _del_cinco_barras(c)
    mm = 1000.0

    pivotes = [(s.pivote[0] * mm, s.pivote[1] * mm) for s in seguidores]

    # --- lo que no se mueve -------------------------------------------------
    platina = hecho["platina_levas"]
    for plato in ("plato1", "plato2", "plato3"):
        piezas.append(Colocada(plato, _poner(platina, z=z[plato][0]), movil=False))

    # La base se sitúa por sus agujeros, como en la realidad: el datum sobre
    # el poste 1 y su +X apuntando al poste 2.
    hacia = math.atan2(pivotes[1][1] - pivotes[0][1], pivotes[1][0] - pivotes[0][0])
    piezas.append(Colocada("base", _poner(hecho["base"], hacia, pivotes[0], z["base"][0]), False))

    poste = hecho["poste"]
    for i, pivote in enumerate(pivotes):
        piezas.append(Colocada(f"poste{i + 1}", _poner(poste, 0.0, pivote, z["poste"][0]), False))
        # El M3 avellanado, enrasado en la punta del poste sobre el plato 3.
        punta_poste = Pos(*pivote, z["poste"][1])
        piezas.append(
            Colocada(f"tornillo_poste_{i + 1}", punta_poste * fj.avellanado(3.0, 10.0), False)
        )
        cortes.append((f"poste{i + 1}", punta_poste * fj.taladro_avellanado(3.0, 10.0)))
        # La altura de los platos la dan dos tubos donde no gira nada —de la
        # base al plato 1 y del 2 al 3— y dos collares donde sí: sobre el 1 y
        # bajo el 2, que es el vano de los seguidores. El M3 avellanado de la
        # punta del poste aprieta plato 3, tubo y plato 2 contra su collar.
        for k, (pie, techo) in enumerate(
            ((0.0, z["plato1"][0]), (z["plato2"][1], z["plato3"][0])), 1
        ):
            piezas.append(
                Colocada(
                    f"tubo_separador_{k}_{i + 1}",
                    _cilindro(c["tubo_separador_diametro"] / 2.0, (*pivote, pie), (*pivote, techo))
                    - _cilindro(
                        c["tubo_separador_interior_diametro"] / 2.0,
                        (*pivote, pie - 1.0),
                        (*pivote, techo + 1.0),
                    ),
                    False,
                )
            )
        for plato, lado, pie in (
            ("plato1", "sobre", z["plato1"][1]),
            ("plato2", "bajo", z["plato2"][0] - c["collar_seguidor_largo"]),
        ):
            nombre = f"collar_plato_{plato[-1]}{lado}_{i + 1}"
            piezas.append(Colocada(nombre, _poner(hecho["collar"], 0.0, pivote, pie), False))
            piezas.append(
                _prisionero_del_collar(
                    c, nombre, pivote, pie + c["collar_seguidor_largo"] / 2, cortes, False
                )
            )

    # --- lo que gira con el árbol -------------------------------------------
    # Cada leva a la altura de su rodillo: el contrato dice cuánto baja cada
    # uno desde el plano de los seguidores, y eso ordena la pila sin que este
    # módulo tenga que importar el compilador.
    seg_medio = z["seguidores"][0] + c["seguidor_espesor"] / 2.0
    for i, pieza in enumerate(levas):
        altura = seg_medio - c[f"rodillo_descuelgue_{i + 1}"] - ESPESOR_DE_LEVA / 2.0
        if not z["levas"][0] - 1e-6 <= altura <= z["levas"][1] - ESPESOR_DE_LEVA + 1e-6:
            raise ValueError(f"la leva {i + 1} cae fuera de la pila: revisa rodillo_descuelgue")
        piezas.append(
            Colocada(f"leva_{i + 1}", _poner(solido_de_pieza(pieza), estado.theta, z=altura), True)
        )

    # --- lo que mueve cada leva ---------------------------------------------
    seguidor_solido, sector_solido = hecho["seguidor"], hecho["sector"]
    for i, (pivote, seg) in enumerate(zip(pivotes, seguidores, strict=True)):
        angulo = seg.psi_cero + estado.desviaciones[i]
        piezas.append(
            Colocada(
                f"seguidor_{i + 1}",
                _poner(seguidor_solido, angulo, pivote, z["seguidores"][0]),
                True,
            )
        )
        # El rodillo, en el agujero de su canal y a la altura de su leva.
        brazo = seg.brazo * mm
        rodillo_en = (pivote[0] + brazo * math.cos(angulo), pivote[1] + brazo * math.sin(angulo))
        centro_z = seg_medio - c[f"rodillo_descuelgue_{i + 1}"]
        ancho = hecho["rodillo_seguidor"].bounding_box().size.Z
        piezas.append(
            Colocada(
                f"rodillo_{i + 1}",
                _poner(hecho["rodillo_seguidor"], 0.0, rodillo_en, centro_z - ancho / 2.0),
                True,
            )
        )
        piezas.append(
            Colocada(
                f"eje_rodillo_{i + 1}", _eje_del_rodillo(c, z, rodillo_en, centro_z, ancho), True
            )
        )
        piezas += _tope_y_muelle(c, z, hecho, i + 1, pivote, seg.psi_cero, seg.hacia_dentro, angulo)
        pie_collar = z["seguidores"][0] - 1.0 - c["tope_placa_espesor"] - c["collar_seguidor_largo"]
        piezas.append(
            _prisionero_del_collar(
                c, f"collar_seguidor_{i + 1}", pivote, pie_collar + 1.5, cortes, False
            )
        )
        if i < 2:  # el canal del elevador no lleva cabestrante
            piezas += _union_del_sector(c, z, hecho, i + 1, pivote, angulo)
            piezas.append(
                Colocada(
                    f"sector_{i + 1}", _poner(sector_solido, angulo, pivote, z["sector"][0]), True
                )
            )

    # --- el varillaje, cada brazo en su plano --------------------------------
    proximal, distal = hecho["brazo_proximal"], hecho["brazo_distal"]
    sep = c["brazo_separacion"] / 2.0
    lados = ((-sep, estado.psi_izquierdo), (sep, estado.psi_derecho))
    codos = [
        (x + c["brazo_proximal"] * math.cos(psi), c["brazo_proximal"] * math.sin(psi))
        for x, psi in lados
    ]
    punta = _punta(codos[0], codos[1], c["brazo_distal"])
    for lado, (x, psi) in enumerate(lados):
        n = lado + 1
        pivote = al_marco((x, 0.0))
        giro = psi + c["brazo_origen_giro"]
        piezas.append(
            Colocada(f"proximal_{n}", _poner(proximal, giro, pivote, z[f"proximal_{n}"][0]), True)
        )
        codo_plano = codos[lado]
        # Curvado hacia la caja: el izquierdo cruza de derecha a izquierda y
        # lleva la pieza volteada para que la curva quede del mismo lado.
        cuerpo = hecho["brazo_distal_volteado"] if lado == 0 else distal
        piezas.append(
            Colocada(
                f"distal_{n}",
                _poner(
                    cuerpo,
                    math.atan2(punta[1] - codo_plano[1], punta[0] - codo_plano[0])
                    + c["brazo_origen_giro"],
                    al_marco(codo_plano),
                    z[f"distal_{n}"][0],
                ),
                True,
            )
        )
        # El anillo de ajuste bajo el proximal: lo que no deja bajar al eje.
        bajo = z[f"proximal_{n}"][0]
        piezas.append(
            Colocada(
                f"anillo_proximal_{n}",
                Pos(*pivote, bajo - ANILLO_DE_AJUSTE[1] - 0.05)
                * fj.arandela(c["brazo_eje_diametro"], *ANILLO_DE_AJUSTE),
                True,
            )
        )
        # Y el circlip sobre el tambor: lo que no lo deja subir.
        piezas.append(
            Colocada(
                f"circlip_tambor_{n}",
                Pos(*pivote, z["tambor"][1] + 0.05) * fj.circlip(c["brazo_eje_diametro"]),
                True,
            )
        )
        # El codo: un pasador enrasado calado en el distal, que gira en el
        # proximal, con una arandela de 0,5 entre los dos cubos.
        cx, cy = al_marco(codo_plano)
        piezas.append(
            Colocada(
                f"perno_codo_{n}",
                Pos(cx, cy, z[f"distal_{n}"][0]) * hecho["perno_codo"],
                True,
            )
        )
        piezas.append(
            Colocada(
                f"arandela_codo_{n}",
                _cilindro(
                    c["brazo_extremo_diametro"] / 2.0,
                    (cx, cy, z[f"distal_{n}"][1]),
                    (cx, cy, z[f"proximal_{n}"][0]),
                )
                - _cilindro(
                    c["brazo_perno_diametro"] / 2.0 + 0.1,
                    (cx, cy, z[f"distal_{n}"][1] - 1.0),
                    (cx, cy, z[f"proximal_{n}"][0] + 1.0),
                ),
                True,
            )
        )
        # El eje de pivote cala el proximal por debajo y el tambor por encima:
        # los dos giran con el brazo, con la cara plana mirando a su otro cubo.
        tope_eje = z["tambor"][1] + 1.5
        piezas.append(
            Colocada(
                f"eje_pivote_{n}",
                _poner(hecho["eje_pivote"], giro, pivote, tope_eje - c["eje_pivote_largo"]),
                True,
            )
        )
        piezas.append(
            Colocada(f"tambor_{n}", _poner(hecho["tambor"], giro, pivote, z["tambor"][0]), True)
        )
        piezas += _cinta(
            c,
            hecho,
            z,
            n,
            sector_en=pivotes[lado],
            giro_sector=estado.desviaciones[lado],
            tambor_en=pivote,
            giro_tambor=giro
            - (c[("calaje_izquierdo", "calaje_derecho")[lado]] + c["brazo_origen_giro"]),
        )

    piezas += _transmision(c, hecho, estado, z, cortes)
    piezas += _levantamiento(c, hecho, estado, seguidores, z, cortes)
    piezas += _portalapiz(c, hecho, z, al_marco(punta), cortes)
    return _cortar(piezas, cortes)


def _cortar(piezas: list[Colocada], cortes: list[tuple[str, Any]]) -> list[Colocada]:
    """Resta a cada pieza los agujeros de la tornillería que recibe."""
    por_pieza: dict[str, list[Any]] = {}
    for nombre, corte in cortes:
        por_pieza.setdefault(nombre, []).append(corte)
    sin_dueno = set(por_pieza) - {p.nombre for p in piezas}
    if sin_dueno:
        raise ValueError(f"cortes para piezas que no están: {sorted(sin_dueno)}")
    salida = []
    for p in piezas:
        solido = p.solido
        for corte in por_pieza.get(p.nombre, []):
            solido = solido - corte
        salida.append(Colocada(p.nombre, solido, p.movil))
    return salida


ANILLO_DE_AJUSTE = (20.0, 2.95)
"""Ø exterior y ancho del anillo bajo cada proximal: el hueco que deja el eje
de pivote es de 3 (`test_el_eje_de_pivote_llega_del_collar_al_circlip`)."""

LARGO_SOPORTE = 25.0
"""El M2 de cada soporte de la mesa, desde bajo la base con la cabeza
embutida: 25 de base y 2 en el soporte. Con 30 llegaba al eje fijo, que
está a 6 de la base."""

LARGO_LAMINA = 4.0
"""El M2 de cada pestaña de lámina: en la pinza, con 5 llegaba al
portaminas; 4 deja 0,1 de pared hasta su agujero."""

PRISIONERO = (3.0, 4.0)
"""Métrica y largo de los prisioneros DIN 913 de collares, casquillo y pinza."""


def _prisionero_radial(
    nombre: str,
    centro: tuple[float, float, float],
    direccion: tuple[float, float, float],
    desde: float,
    pared: float,
    anfitriones: tuple[str, ...],
    cortes: list[tuple[str, Any]],
    movil: bool,
) -> Colocada:
    """Un prisionero que entra radial: la punta a `desde` del eje, contra lo
    que aprieta, y su agujero roscado en cada anfitrión hasta `pared`."""
    d, largo = PRISIONERO
    ux, uy, uz = direccion

    def a(r: float) -> tuple[float, float, float]:
        return (centro[0] + r * ux, centro[1] + r * uy, centro[2] + r * uz)

    tornillo = _cilindro((d - JUEGO_GIRATORIO) / 2, a(desde + 0.01), a(desde + 0.01 + largo))
    agujero = _cilindro(d / 2, a(desde - 0.5), a(max(pared, desde + largo) + 0.5))
    for anfitrion in anfitriones:
        cortes.append((anfitrion, agujero))
    return Colocada(nombre, tornillo, movil)


def _prisionero_del_collar(
    c: dict[str, float],
    collar: str,
    pivote: Punto,
    altura: float,
    cortes: list[tuple[str, Any]],
    movil: bool,
) -> Colocada:
    """El M3 radial de un collar, hacia fuera del árbol: es por donde se le
    llega con la llave."""
    n = math.hypot(*pivote)
    fuera = (pivote[0] / n, pivote[1] / n, 0.0)
    return _prisionero_radial(
        "prisionero_" + collar,
        (*pivote, altura),
        fuera,
        c["poste_eje_diametro"] / 2,
        c["collar_seguidor_diametro"] / 2,
        (collar,),
        cortes,
        movil,
    )


ESPESOR_DE_LEVA = 5.0
"""POM-C de 5, `Escribiente.espesor_leva`."""

CABEZA_DEL_EJE = (6.0, 1.7)
"""Ø y alto de la cabeza del M3 DIN 7984 (cabeza baja) que hace de eje del
rodillo. Va por DEBAJO del rodillo: por arriba está el sector."""

TUERCA_DEL_EJE = (6.0, 1.8)
"""Entre aristas y alto de la tuerca fina M3 DIN 439, sobre el seguidor."""


def _union_del_sector(
    c: dict[str, float],
    z: dict[str, tuple[float, float]],
    hecho: dict[str, Any],
    n: int,
    pivote: Punto,
    angulo: float,
) -> list[Colocada]:
    """El calzo entre seguidor y sector, y los dos M3 DIN 912 que atraviesan
    sector, calzo y seguidor, con su tuerca fina debajo del seguidor."""
    x, y = pivote
    piezas = [
        Colocada(
            f"calzo_sector_{n}",
            _poner(
                hecho["calzo_sector"], angulo, pivote, z["sector"][0] - c["calzo_sector_espesor"]
            ),
            True,
        )
    ]
    tornillos = None
    for cota in ("union_sector_seguidor_cerca", "union_sector_seguidor_lejos"):
        px, py = x + c[cota] * math.cos(angulo), y + c[cota] * math.sin(angulo)
        bajo = z["seguidores"][0] - TUERCA_DEL_EJE[1]
        uno = _cilindro(1.5 - JUEGO_GIRATORIO / 2.0, (px, py, bajo), (px, py, z["sector"][1]))
        uno += _cilindro(
            CABEZA_DIN_912_M3[0] / 2.0,
            (px, py, z["sector"][1]),
            (px, py, z["sector"][1] + CABEZA_DIN_912_M3[1]),
        )
        uno += _cilindro(TUERCA_DEL_EJE[0] / 2.0, (px, py, bajo), (px, py, z["seguidores"][0]))
        tornillos = uno if tornillos is None else tornillos + uno
    piezas.append(Colocada(f"tornillos_sector_{n}", tornillos, True))
    return piezas


CABEZA_DIN_912_M3 = (5.5, 3.0)
"""Ø y alto de la cabeza de un M3 Allen DIN 912."""


def _arco(
    centro: Punto, radio: float, desde: float, hasta: float, z: tuple[float, float], grueso: float
) -> Any:
    """Un trozo de anillo de `grueso` por fuera de `radio`, de `desde` a
    `hasta` en sentido antihorario: la cinta abrazada a una polea."""
    from build123d import Polyline, Pos, extrude, make_face

    n = max(8, int(abs(hasta - desde) / math.radians(3)))
    # Las cuerdas de un polígono caen dentro de su círculo; se agranda el
    # radio interior hasta que caigan fuera, para no meter la cinta en la polea.
    radio = radio / math.cos((hasta - desde) / n / 2.0)
    fuera = [
        (
            centro[0] + (radio + grueso) * math.cos(desde + (hasta - desde) * k / n),
            centro[1] + (radio + grueso) * math.sin(desde + (hasta - desde) * k / n),
        )
        for k in range(n + 1)
    ]
    dentro = [
        (
            centro[0] + radio * math.cos(desde + (hasta - desde) * k / n),
            centro[1] + radio * math.sin(desde + (hasta - desde) * k / n),
        )
        for k in range(n, -1, -1)
    ]
    cara = make_face(Polyline(*(fuera + dentro), close=True))
    return Pos(0.0, 0.0, z[0]) * extrude(cara, z[1] - z[0])


def _tramo(a: Punto, b: Punto, normal: Punto, z: tuple[float, float], grueso: float) -> Any:
    """Un tramo recto de cinta de `a` a `b`, con su grueso hacia `normal`."""
    from build123d import Polyline, Pos, extrude, make_face

    na = (a[0] + normal[0] * grueso, a[1] + normal[1] * grueso)
    nb = (b[0] + normal[0] * grueso, b[1] + normal[1] * grueso)
    cara = make_face(Polyline(a, b, nb, na, close=True))
    return Pos(0.0, 0.0, z[0]) * extrude(cara, z[1] - z[0])


def _cinta(
    c: dict[str, float],
    hecho: dict[str, Any],
    z: dict[str, tuple[float, float]],
    n: int,
    sector_en: Punto,
    giro_sector: float,
    tambor_en: Punto,
    giro_tambor: float,
) -> list[Colocada]:
    """La cinta del cabestrante de un canal, su mordaza y el tornillo del
    tambor.

    Correa abierta: deja el sector y el tambor por las dos tangentes
    exteriores, a ±`amplificador_tangencia` de la línea de centros. Abraza
    el sector por detrás, los 272°, y allí la sujeta la **mordaza**, cuya
    ranura da el calaje. En el tambor abraza el lado lejano, y sus **dos
    extremos se solapan** bajo un M2 radial que pasa por un agujero del
    fleje: el fleje no se dobla para anclarse, queda plano sobre el
    cilindro. Los dos centros no se mueven; lo que gira con el seguidor y
    con el brazo son la mordaza y el tornillo.
    """
    from build123d import Pos, Rot

    rs, rt = c["amplificador_sector_radio_mecanizado"], c["amplificador_tambor_radio_mecanizado"]
    t = c["cinta_espesor"]
    sx, sy = sector_en
    tx, ty = tambor_en
    hacia = math.atan2(ty - sy, tx - sx)
    fi = c["amplificador_tangencia"]
    plano = z["sector"]
    cinta = _arco(sector_en, rs, hacia + fi, hacia + 2 * math.pi - fi, plano, t)
    cinta += _arco(tambor_en, rt, hacia - fi, hacia + fi, plano, t)
    for signo in (1.0, -1.0):
        a = hacia + signo * fi
        normal = (math.cos(a), math.sin(a))
        de_sector = (sx + rs * normal[0], sy + rs * normal[1])
        de_tambor = (tx + rt * normal[0], ty + rt * normal[1])
        cinta += _tramo(de_sector, de_tambor, normal, plano, t)
    piezas = [Colocada(f"cinta_{n}", cinta, True)]

    # La mordaza, sobre la cara libre del sector, detrás, a lo largo de la
    # cinta y con su canto exterior en el canto del sector.
    atras = hacia + math.pi + giro_sector
    radial = rs - c["mordaza_ancho"] / 2.0
    mordaza = (
        Pos(sx + radial * math.cos(atras), sy + radial * math.sin(atras), plano[1])
        * Rot(Z=math.degrees(atras) + 90.0)
        * Pos(c["mordaza_voladizo"] - c["mordaza_largo"] / 2.0, 0.0, 0.0)
        * hecho["mordaza"]
    )
    piezas.append(Colocada(f"mordaza_{n}", mordaza, True))
    # El prisionero que aprieta la cinta, en el agujero de M3 de la mordaza:
    # la cabeza enrasada arriba y la punta sobre la cinta.
    from emit import fijaciones as fj

    ((ax, ay, _), _, _, _), *otros = fj.agujeros(mordaza, c["mordaza_tornillo_diametro"])
    if otros:
        raise ValueError("la mordaza tiene más de un agujero de M3")
    techo = plano[1] + c["mordaza_espesor"]
    piezas.append(
        Colocada(
            f"prisionero_mordaza_{n}", Pos(ax, ay, techo + 0.05) * fj.prisionero(3.0, 6.0), True
        )
    )
    # El centro de la ranura, con la mordaza a media carrera.
    hueco = c["mordaza_entre_tornillos"] + c["mordaza_voladizo"] - c["mordaza_largo"] / 2.0
    mx = sx + radial * math.cos(atras) + hueco * math.cos(atras + math.pi / 2.0)
    my = sy + radial * math.sin(atras) + hueco * math.sin(atras + math.pi / 2.0)
    arriba = plano[1] + c["mordaza_espesor"]
    m4 = _cilindro(2.0 - JUEGO_GIRATORIO / 2.0, (mx, my, plano[0] - 2.2), (mx, my, arriba))
    m4 += _cilindro(3.5, (mx, my, arriba), (mx, my, arriba + 4.0))
    m4 += _cilindro(3.6, (mx, my, plano[0] - 2.2), (mx, my, plano[0]))
    piezas.append(Colocada(f"tornillo_mordaza_{n}", m4, True))

    # El M2 del tambor, radial, en el lado lejano: cabeza de Ø3,8 × 1,3
    # sobre los dos extremos solapados de la cinta.
    lejos = hacia + giro_tambor
    medio = (plano[0] + plano[1]) / 2.0
    pie = rt + 2 * t
    tornillo = _cilindro(
        1.9,
        (tx + pie * math.cos(lejos), ty + pie * math.sin(lejos), medio),
        (tx + (pie + 1.3) * math.cos(lejos), ty + (pie + 1.3) * math.sin(lejos), medio),
    )
    piezas.append(Colocada(f"tornillo_tambor_{n}", tornillo, True))
    return piezas


def _tope_y_muelle(
    c: dict[str, float],
    z: dict[str, tuple[float, float]],
    hecho: dict[str, Any],
    n: int,
    pivote: Punto,
    reposo: float,
    hacia_dentro: int,
    angulo: float,
) -> list[Colocada]:
    """Lo que sostiene y empuja un seguidor, en su poste: el collar, la placa
    de tope soldada encima, el pasador de tope y el muelle de torsión con sus
    dos patas. La placa va girada `tope_angulo` desde el brazo del seguidor
    en reposo, hacia el lado en que el rodillo se mete."""
    x, y = pivote
    techo = z["seguidores"][0] - 1.0  # la valona del casquillo igus
    pie_placa = techo - c["tope_placa_espesor"]
    pie_collar = pie_placa - c["collar_seguidor_largo"]
    a = reposo + hacia_dentro * c["tope_angulo"]
    piezas = [
        Colocada(f"collar_seguidor_{n}", _poner(hecho["collar"], a, pivote, pie_collar), False),
        Colocada(f"placa_tope_{n}", _poner(hecho["placa_tope"], a, pivote, pie_placa), False),
    ]
    px, py = x + c["tope_brazo"] * math.cos(a), y + c["tope_brazo"] * math.sin(a)
    piezas.append(
        Colocada(
            f"pasador_tope_{n}",
            _cilindro(
                c["tope_pasador_diametro"] / 2.0,
                (px, py, techo),
                (px, py, z["seguidores"][1] - 0.5),
            ),
            False,
        )
    )
    # El muelle: cuatro espiras de 0,8 sobre el collar, y sus dos patas. La
    # fija sube a la placa; la móvil, a su agujero del seguidor, y se mueve
    # con él.
    hilo = MUELLE_DE_TORSION[0]
    exterior = c["collar_seguidor_diametro"] / 2.0 + 0.35 + 2 * hilo
    alto = MUELLE_DE_TORSION[1] * hilo * 1.4
    pie = pie_placa - 0.5 - alto
    espiras = _cilindro(exterior, (x, y, pie), (x, y, pie + alto)) - _cilindro(
        exterior - 2 * hilo, (x, y, pie - 1), (x, y, pie + alto + 1)
    )
    medio = exterior - hilo
    r = hilo / 2.0
    fija = (x + c["muelle_pata_radio"] * math.cos(a), y + c["muelle_pata_radio"] * math.sin(a))
    movil = (
        x + c["seguidor_muelle_radio"] * math.cos(angulo),
        y + c["seguidor_muelle_radio"] * math.sin(angulo),
    )
    patas = []
    for punta, altura in ((fija, techo - 0.2), (movil, z["seguidores"][0] + 3.0)):
        d = math.hypot(punta[0] - x, punta[1] - y)
        arranque = (x + (punta[0] - x) * medio / d, y + (punta[1] - y) * medio / d, pie + alto - r)
        patas.append(_cilindro(r, arranque, (punta[0], punta[1], pie + alto - r)))
        patas.append(
            _cilindro(r, (punta[0], punta[1], pie + alto - r), (punta[0], punta[1], altura))
        )
    muelle = espiras
    for pata in patas:
        muelle += pata
    piezas.append(Colocada(f"muelle_seguidor_{n}", muelle, True))
    return piezas


MUELLE_DE_TORSION = (0.8, 4)
"""Hilo y espiras del muelle de torsión del seguidor: 0,8 de cuerda de piano,
Ø medio 13, cuatro espiras. 0,44 N·mm por grado: los 50 mN·m de precarga son
113° de torsión, y en los ±2,6° del seguidor el par varía un 4 %."""


def _eje_del_rodillo(
    c: dict[str, float],
    z: dict[str, tuple[float, float]],
    centro: Punto,
    centro_z: float,
    ancho: float,
) -> Any:
    """El eje del rodillo descolgado: un M3 avellanado (DIN 7991) que entra
    por arriba con la cabeza enrasada en el seguidor, baja por el casquillo,
    atraviesa el rodillo y se cierra debajo con una tuerca fina.

    **Por arriba no asoma nada**: la cinta del cabestrante pasa por encima
    del seguidor izquierdo y del elevador, y una tuerca encima del seguidor
    la cortaba (auditoría A6). Por debajo la tuerca de 1,8 ocupa menos que
    la cabeza de 2 que había. El mismo tornillo en los tres canales, cortado
    a su largo."""
    x, y = centro
    pie = centro_z - ancho / 2.0
    techo = z["seguidores"][1]
    radio = 1.5 - JUEGO_GIRATORIO / 2.0
    eje = _cilindro(radio, (x, y, pie - TUERCA_DEL_EJE[1]), (x, y, techo))
    eje += _cilindro(TUERCA_DEL_EJE[0] / 2.0, (x, y, pie - TUERCA_DEL_EJE[1]), (x, y, pie))
    eje += _cilindro(
        c["casquillo_rodillo_diametro"] / 2.0,
        (x, y, centro_z + ancho / 2.0),
        (x, y, z["seguidores"][0]),
    )
    return eje


def _entre_puntos(
    c: dict[str, float], hecho: dict[str, Any], estado: Estado, z: dict[str, tuple[float, float]]
) -> list[Colocada]:
    """El cartucho entre puntos y lo que lo sujeta: el muñón abajo, el eje del
    cartucho con su cubo, sus separadores y su pasador, y arriba la garra en
    el eje motriz con su pasador, su muelle y el anillo. Todo gira con θ.

    Lo que antes era un árbol de 92 de una pieza, que no dejaba sacar las
    levas sin desmontar media torre.
    """
    t = estado.theta
    piezas: list[Colocada] = []
    pie_cartucho = z["plato1"][1] + c["munon_holgura"] + c["munon_horquilla_alto"]
    if abs(pie_cartucho + c["cubo_espesor"] - z["levas"][0]) > 1e-6:
        raise ValueError("el cubo no llega a la primera leva: revisa leva_sobre_plato")
    piezas.append(
        Colocada("munon", _poner(hecho["munon"], t, z=pie_cartucho - c["munon_largo"]), True)
    )
    piezas.append(Colocada("eje_cartucho", _poner(hecho["eje_cartucho"], t, z=pie_cartucho), True))
    # Los separadores, encima de las dos levas de abajo.
    seg_medio = z["seguidores"][0] + c["seguidor_espesor"] / 2.0
    pies = sorted(
        seg_medio - c[f"rodillo_descuelgue_{i}"] - ESPESOR_DE_LEVA / 2.0 for i in (1, 2, 3)
    )
    for k, pie in enumerate(pies[:2], start=1):
        piezas.append(
            Colocada(f"separador_{k}", _poner(hecho["separador"], t, z=pie + ESPESOR_DE_LEVA), True)
        )
    rp = c["pasador_diametro"] / 2.0 - JUEGO_GIRATORIO / 2.0
    pasador = _cilindro(
        rp, (c["pasador_radio"], 0.0, 0.0), (c["pasador_radio"], 0.0, c["pasador_longitud"])
    )
    piezas.append(Colocada("pasador_indice", _poner(pasador, t, z=pie_cartucho), True))

    cabeza = pie_cartucho + c["cartucho_eje_largo"]
    pie_motriz = cabeza + 1.0
    if abs(pie_motriz + c["eje_motriz_largo"] - (z["plato3"][0] + 2.0 + 5.0)) > 1e-6:
        raise ValueError("el eje motriz no acaba en el rodamiento del plato 3: eje_motriz_largo")
    piezas.append(Colocada("eje_motriz", _poner(hecho["eje_motriz"], t, z=pie_motriz), True))
    piezas.append(Colocada("garra", _poner(hecho["garra"], t, z=cabeza), True))
    piezas.append(
        Colocada(
            "pasador_garra",
            _poner(hecho["pasador_garra"], t, z=cabeza + c["garra_pasador_alto"]),
            True,
        )
    )
    techo_garra = cabeza + c["garra_alto"]
    muelle = _cilindro(6.8, (0, 0, techo_garra), (0, 0, techo_garra + c["garra_muelle_largo"]))
    muelle -= _cilindro(
        5.6, (0, 0, techo_garra - 1), (0, 0, techo_garra + c["garra_muelle_largo"] + 1)
    )
    piezas.append(Colocada("muelle_garra", muelle, True))
    from build123d import Pos

    from emit import fijaciones as fj

    # Los dos circlips del eje de Ø10: sobre el muelle de la garra, y bajo el
    # muñón, contra la cara baja del plato 1.
    anillo_z = techo_garra + c["garra_muelle_largo"]
    circlip = fj.circlip(c["eje_diametro"])
    piezas.append(Colocada("circlip_garra_1", Pos(0, 0, anillo_z) * circlip, True))
    _, espesor = fj.DIN_6799[c["eje_diametro"]]
    bajo_plato = z["plato1"][0] - 0.05 - espesor
    piezas.append(Colocada("circlip_garra_2", Pos(0, 0, bajo_plato) * circlip, True))
    return piezas


def _punta(codo_1: Punto, codo_2: Punto, distal: float) -> Punto:
    """Donde se cortan los dos distales: la punta del cinco barras, la que
    escribe. Es la solución hacia la caja —la de más Y—, la misma rama que
    usa el núcleo. Apuntar los distales a un punto fijo los dejaba bien solo
    en el centro de la caja; el lápiz va aquí y se mueve con la frase."""
    dx, dy = codo_2[0] - codo_1[0], codo_2[1] - codo_1[1]
    d = math.hypot(dx, dy)
    if d > 2 * distal:
        raise ValueError("los dos codos están más lejos que dos distales: no hay punta")
    medio = (codo_1[0] + dx / 2, codo_1[1] + dy / 2)
    h = math.sqrt(distal**2 - (d / 2) ** 2)
    candidatas = [(medio[0] - s * h * dy / d, medio[1] + s * h * dx / d) for s in (1, -1)]
    return max(candidatas, key=lambda p: p[1])


def _transmision(
    c: dict[str, float],
    hecho: dict[str, Any],
    estado: Estado,
    z: dict[str, tuple[float, float]],
    cortes: list[tuple[str, Any]] | None = None,
) -> list[Colocada]:
    """El árbol, el reductor, el volante y la manivela.

    El árbol va de 2 por debajo del plato 1 a 2 por encima de la rueda: con
    120 asomaba por encima del plato 3, donde va el volante. El volante va
    encima del plato 3 y no en la bahía: centrado a 28 del árbol y con R52,
    lo atravesaban el árbol y la rueda.
    """
    # Quien solo quiere dónde van las piezas no necesita sus agujeros.
    cortes = [] if cortes is None else cortes
    from build123d import Align, Cylinder

    piezas = _entre_puntos(c, hecho, estado, z)
    rodamiento = hecho["rodamiento_arbol"]
    t = c["platina_manivela_angulo"]
    manivela_en = (c["reductor_entre_ejes"] * math.cos(t), c["reductor_entre_ejes"] * math.sin(t))
    for plato, n in (("plato1", 1), ("plato2", 2), ("plato3", 3)):
        piezas.append(
            Colocada(f"rodamiento_arbol_{n}", _poner(rodamiento, z=z[plato][0] + 2.0), False)
        )
    for plato, n in (("plato2", 1), ("plato3", 2)):
        piezas.append(
            Colocada(
                f"rodamiento_manivela_{n}",
                _poner(rodamiento, 0.0, manivela_en, z[plato][0] + 2.0),
                False,
            )
        )
    # La rueda Z60 viene a 15 y el árbol es de 10: el casquillo los une.
    agujero_rueda = Cylinder(
        c["casquillo_rueda_diametro"] / 2, 20.0, align=(Align.CENTER, Align.CENTER, Align.CENTER)
    )
    rueda = hecho["rueda_reductor"] - agujero_rueda
    piezas.append(Colocada("rueda", _poner(rueda, estado.theta, z=z["engrane"][0]), True))
    piezas.append(
        Colocada(
            "casquillo_rueda",
            _poner(hecho["casquillo_rueda"], estado.theta, z=z["engrane"][0]),
            True,
        )
    )
    # Su prisionero, radial a media altura: atraviesa la rueda y el casquillo
    # y aprieta en el árbol.
    piezas.append(
        _prisionero_radial(
            "prisionero_rueda",
            (0.0, 0.0, z["engrane"][0] + c["casquillo_rueda_largo"] / 2),
            (math.cos(estado.theta), math.sin(estado.theta), 0.0),
            c["eje_diametro"] / 2,
            c["casquillo_rueda_diametro"] / 2,
            ("casquillo_rueda", "rueda"),
            cortes,
            True,
        )
    )
    # La manivela da 3 vueltas por cada una del árbol, y al revés: es un
    # engrane exterior. Lo que gira con ella va en su eje, con la misma cara.
    giro_m = t - c["reductor_relacion"] * estado.theta
    agujero_pinon = Cylinder(
        c["brazo_eje_diametro"] / 2, 20.0, align=(Align.CENTER, Align.CENTER, Align.CENTER)
    )
    pinon = hecho["pinon_reductor"] - agujero_pinon
    piezas.append(Colocada("pinon", _poner(pinon, giro_m, manivela_en, z["engrane"][0]), True))
    piezas.append(
        Colocada(
            "eje_manivela",
            _poner(hecho["eje_manivela"], giro_m, manivela_en, z["plato2"][0] - HOLGURA_AXIAL),
            True,
        )
    )
    piezas.append(
        Colocada("volante", _poner(hecho["volante"], giro_m, manivela_en, z["volante"][0]), True)
    )
    piezas.append(
        Colocada("manivela", _poner(hecho["manivela"], giro_m, manivela_en, z["manivela"][0]), True)
    )
    return piezas


def _levantamiento(
    c: dict[str, float],
    hecho: dict[str, Any],
    estado: Estado,
    seguidores: list[Any],
    z: dict[str, tuple[float, float]],
    cortes: list[tuple[str, Any]] | None = None,
) -> list[Colocada]:
    """La cadena del levantamiento, en el marco del cinco barras y llevada al
    de la leva: el seguidor 3 empuja la bieleta, la bieleta gira el eje del
    balancín, la palanca baja el tirante y el tirante baja la mesa.

    El giro del eje y lo que baja la mesa vienen en el `Estado`: los calcula
    `compile.levantamiento`, que cierra el lazo de la bieleta.
    """
    # Quien solo quiere dónde van las piezas no necesita sus agujeros.
    cortes = [] if cortes is None else cortes
    from build123d import Pos, Rot

    g = c["brazo_origen_giro"]
    a_leva = Pos(c["brazo_origen_x"], c["brazo_origen_y"], 0.0) * Rot(Z=math.degrees(g))
    piezas: list[Colocada] = []

    def poner(nombre: str, solido: Any, movil: bool) -> None:
        piezas.append(Colocada(nombre, a_leva * solido, movil))

    # --- el eje del balancín, de proa a popa, y lo que lleva calado --------
    x_eje, z_eje = c["balancin_eje_x"], z["balancin"][0]
    # El balancín va por DETRÁS del codo de la bieleta: la varilla llega del
    # seguidor 3, que está a proa, y por delante cruzaría su extremo.
    y_balancin = c["balancin_ojo_y"] - c["bieleta_holgura_balancin"] - c["balancin_espesor"]
    y_palanca = c["tirante_y"] - c["bulon_tirante_taladro"]
    y_proa = y_palanca + c["brazo_espesor"] + 2.0
    y_popa = y_proa - c["balancin_eje_largo"]
    giro = math.degrees(estado.giro_balancin)
    # Marco del eje: su Z local corre a +Y, y gira `giro` en sus apoyos.
    eje = Pos(x_eje, y_popa, z_eje) * Rot(Y=giro) * Rot(X=-90)
    poner("eje_balancin", eje * hecho["eje_balancin"], True)
    # El balancín lleva su cara plana a +90°: calado en la misma cara que la
    # palanca, apunta hacia arriba.
    alfa = math.degrees(c["balancin_chaveta_angulo"])
    poner("balancin", eje * Pos(0, 0, y_balancin - y_popa) * Rot(Z=-alfa) * hecho["balancin"], True)
    poner("palanca_lapiz", eje * Pos(0, 0, y_palanca - y_popa) * hecho["palanca_lapiz"], True)

    # Los dos apoyos, colgados del plato 2, con el agujero del eje.
    for cual in ("trasero", "delantero"):
        y = c[f"apoyo_balancin_{cual}_y"]
        poner(
            f"apoyo_balancin_{cual}",
            _en_plano(
                hecho["apoyo_balancin"],
                (x_eje, y - c["apoyo_balancin_fondo"] / 2, z_eje),
                (0, 0, 1),
                (0, 1, 0),
            ),
            False,
        )

    # --- la bieleta: el seguidor donde lo deja la leva, el ojo donde lo deja el eje
    seg3 = seguidores[2]
    psi = seg3.psi_cero + estado.desviaciones[2]
    r = c["levantamiento_pasador_al_pivote"]
    px, py = (
        seg3.pivote[0] * 1000.0 + r * math.cos(psi),
        seg3.pivote[1] * 1000.0 + r * math.sin(psi),
    )
    # Del marco de la leva al del cinco barras: la inversa de `a_leva`.
    lx, ly = px - c["brazo_origen_x"], py - c["brazo_origen_y"]
    sx, sy = lx * math.cos(g) + ly * math.sin(g), -lx * math.sin(g) + ly * math.cos(g)
    e = c["balancin_entrada"]
    ojo = (
        x_eje + e * math.sin(estado.giro_balancin),
        c["balancin_ojo_y"],
        z_eje + e * math.cos(estado.giro_balancin),
    )
    # La pata gira en su agujero: se modela con el juego de un H7/h8 de 2,
    # 0,02 en diámetro. Línea con línea, el kernel no sabe si dos cilindros
    # iguales se tocan o se atraviesan.
    rb = c["bieleta_diametro"] / 2 - JUEGO_GIRATORIO / 2
    bieleta = (
        _cilindro(rb, (sx, sy, z["seguidores"][0]), (sx, sy, ojo[2]))
        + _cilindro(rb, (sx, sy, ojo[2]), ojo)
        + _cilindro(rb, ojo, (ojo[0], ojo[1] - c["bieleta_pata_balancin"], ojo[2]))
    )
    poner("bieleta", bieleta, True)
    poner("casquillo_bieleta", Pos(sx, sy, z["seguidores"][0]) * hecho["casquillo_bieleta"], True)

    # --- el tirante, a plomo desde el perno de la palanca -------------------
    perno = (
        x_eje + c["brazo_palanca"] * math.cos(estado.giro_balancin),
        z_eje - c["brazo_palanca"] * math.sin(estado.giro_balancin),
    )
    bulon = _en_plano(hecho["bulon_tirante"], (perno[0], y_palanca, perno[1]), (1, 0, 0), (0, 1, 0))
    taladro_bulon = _cilindro(
        c["tirante_diametro"] / 2,
        (perno[0], c["tirante_y"], perno[1] - 10.0),
        (perno[0], c["tirante_y"], perno[1] + 10.0),
    )
    poner("bulon_tirante", bulon - taladro_bulon, True)
    arriba = perno[1] + c["brazo_perno_diametro"] / 2
    tirante = Pos(perno[0], c["tirante_y"], arriba - c["tirante_largo"]) * hecho["tirante"]
    ojo_tirante = _cilindro(
        c["tirante_ojo_diametro"] / 2,
        (perno[0] - 5.0, c["tirante_y"], arriba - c["tirante_largo"] + 2.0),
        (perno[0] + 5.0, c["tirante_y"], arriba - c["tirante_largo"] + 2.0),
    )
    poner("tirante", tirante - ojo_tirante, True)

    # --- la mesa y sus bielas laterales --------------------------------------
    biela = c["mesa_biela"]
    caida = estado.caida_mesa * 1000.0
    a = -math.asin(max(-1.0, min(1.0, caida / biela)))
    zb = c["mesa_bisagra_z"]
    dentro, ancho = c["mesa_biela_x_dentro"], c["mesa_biela_espesor"]
    fuera = dentro + ancho
    for lado, y_fijo in (
        ("trasera", c["mesa_bisagra_cerca"]),
        ("delantera", c["mesa_bisagra_lejos"]),
    ):
        y_movil, z_movil = y_fijo + biela * math.cos(a), zb + biela * math.sin(a)
        for signo, x0 in (("d", dentro), ("i", -fuera)):
            poner(
                f"biela_mesa_{lado}_{signo}",
                _en_plano(
                    hecho["biela_mesa"], (x0, y_fijo, zb), (0, math.cos(a), math.sin(a)), (1, 0, 0)
                ),
                True,
            )
            x_sop = x0 + ancho if signo == "d" else x0 - c["soporte_mesa_ancho"]
            poner(
                f"soporte_mesa_{lado}_{signo}",
                _en_plano(hecho["soporte_mesa"], (x_sop, y_fijo, zb), (0, 0, 1), (1, 0, 0)),
                False,
            )
            x_eje_fijo = dentro if signo == "d" else -dentro - c["mesa_eje_fijo_largo"]
            poner(
                f"eje_mesa_fijo_{lado}_{signo}",
                _en_plano(hecho["eje_mesa_fijo"], (x_eje_fijo, y_fijo, zb), (0, 1, 0), (1, 0, 0)),
                False,
            )
        poner(
            f"eje_mesa_movil_{lado}",
            _en_plano(hecho["eje_mesa_movil"], (-fuera, y_movil, z_movil), (0, 1, 0), (1, 0, 0)),
            True,
        )
        poner(
            f"orejeta_mesa_{lado}",
            _en_plano(
                hecho["orejeta_mesa"],
                (-c["orejeta_mesa_ancho"] / 2, y_movil, z_movil),
                (0, 0, 1),
                (1, 0, 0),
            ),
            True,
        )
    corrimiento = biela - biela * math.cos(a)
    mesa = (
        Pos(0.0, c["mesa_bisagra_cerca"] + biela - corrimiento, z["mesa"][0] - caida)
        * Rot(Z=90)
        * hecho["mesa"]
    )
    poner("mesa", mesa, True)

    # --- la tornillería y la retención ---------------------------------------
    from emit import fijaciones as fj

    def cortar(nombre: str, solido: Any) -> None:
        cortes.append((nombre, a_leva * solido))

    def a_lo_largo(solido: Any, punto: tuple[float, float, float], eje: str) -> Any:
        """El sólido de su marco (eje en +Z) con su eje a lo largo de X o Y."""
        x, z_ = {"+X": ((0, 1, 0), (1, 0, 0)), "-X": ((0, 1, 0), (-1, 0, 0))}.get(
            eje, ((1, 0, 0), (0, 1, 0) if eje == "+Y" else (0, -1, 0))
        )
        return _en_plano(solido, punto, x, z_)

    # El circlip del bulón, por fuera del ojo del tirante.
    fuera_tirante = c["tirante_y"] + c["tirante_diametro"] / 2 + 0.05
    poner(
        "circlip_bulon",
        a_lo_largo(fj.circlip(6.0), (perno[0], fuera_tirante, perno[1]), "+Y"),
        True,
    )
    # Los dos circlips del eje del balancín, por fuera de sus apoyos.
    _, s4 = fj.DIN_6799[c["balancin_eje_diametro"]]
    for k, (cual, signo) in enumerate((("trasero", -1), ("delantero", 1)), start=1):
        cara = c[f"apoyo_balancin_{cual}_y"] + signo * (c["apoyo_balancin_fondo"] / 2 + 0.05)
        y = cara if signo > 0 else cara - s4
        poner(
            f"circlip_balancin_{k}",
            a_lo_largo(fj.circlip(c["balancin_eje_diametro"]), (x_eje, y, z_eje), "+Y"),
            True,
        )
    # Los apoyos, al plato 2: un M3 que baja por el plato y rosca en el apoyo.
    techo_plato = z["plato2"][1]
    for cual in ("trasero", "delantero"):
        en = (x_eje, c[f"apoyo_balancin_{cual}_y"], techo_plato)
        poner(f"tornillo_apoyo_{cual}", Pos(*en) * fj.allen(3.0, 16.0), False)
        cortar("plato2", Pos(*en) * fj.taladro(3.0, 16.0))
        cortar(f"apoyo_balancin_{cual}", Pos(*en) * fj.taladro(3.0, 16.0))
    # Los soportes de la mesa, desde bajo la base: la cabeza embutida.
    pie_base = z["base"][0]
    cabeza = fj.CABEZA_DIN_912[2.0]
    for lado, y_fijo in (
        ("trasera", c["mesa_bisagra_cerca"]),
        ("delantera", c["mesa_bisagra_lejos"]),
    ):
        for signo in ("d", "i"):
            x0 = dentro if signo == "d" else -fuera
            x_sop = x0 + ancho if signo == "d" else x0 - c["soporte_mesa_ancho"]
            en = Pos(x_sop + c["soporte_mesa_ancho"] / 2, y_fijo, pie_base + cabeza[1]) * Rot(X=180)
            poner(f"tornillo_soporte_{lado}_{signo}", en * fj.allen(2.0, LARGO_SOPORTE), False)
            cortar("base", en * fj.taladro(2.0, LARGO_SOPORTE, cabeza))
            cortar(f"soporte_mesa_{lado}_{signo}", en * fj.taladro(2.0, LARGO_SOPORTE))
    # Los circlips de los ejes de la mesa: uno por fuera de cada soporte en
    # los fijos, y uno en cada punta del móvil.
    _, s15 = fj.DIN_6799[c["mesa_eje_diametro"]]
    k = 0
    for _lado, y_fijo in (
        ("trasera", c["mesa_bisagra_cerca"]),
        ("delantera", c["mesa_bisagra_lejos"]),
    ):
        y_movil, z_movil = y_fijo + biela * math.cos(a), zb + biela * math.sin(a)
        fuera_soporte = fuera + c["soporte_mesa_ancho"] + 0.05
        for x, y_, z_, movil in (
            (fuera_soporte, y_fijo, zb, False),
            (-fuera_soporte - s15, y_fijo, zb, False),
            (fuera + 0.05, y_movil, z_movil, True),
            (-fuera - 0.05 - s15, y_movil, z_movil, True),
        ):
            k += 1
            poner(
                f"circlip_mesa_{k}",
                a_lo_largo(fj.circlip(c["mesa_eje_diametro"]), (x, y_, z_), "+X"),
                movil,
            )
    # La mesa a sus orejetas: un M2 por cada una, en el agujero de la mesa
    # que cae sobre ella.
    for lado in ("trasera", "delantera"):
        orejeta = next(p for p in piezas if p.nombre == f"orejeta_mesa_{lado}")
        caja = (a_leva.inverse() * orejeta.solido).bounding_box()
        sobre = [
            (punto, direccion)
            for punto, direccion, _, _ in fj.agujeros(mesa, c["mesa_tornillo_diametro"])
            if caja.min.X <= punto[0] <= caja.max.X and caja.min.Y <= punto[1] <= caja.max.Y
        ]
        if len(sobre) != 1:
            raise ValueError(f"la orejeta {lado} tiene {len(sobre)} agujeros de la mesa encima")
        (px, py, _), _ = sobre[0]
        en = Pos(px, py, mesa.bounding_box().max.Z)
        poner(f"tornillo_orejeta_{lado}", en * fj.allen(2.0, 8.0), True)
        cortar(f"orejeta_mesa_{lado}", en * fj.taladro(2.0, 8.0))
    # La arandela de presión que retiene la pata de la bieleta en el balancín.
    poner(
        "arandela_bieleta",
        a_lo_largo(
            fj.arandela(c["bieleta_diametro"], 4.4, 0.5),
            (ojo[0], y_balancin - 0.05, ojo[2]),
            "-Y",
        ),
        True,
    )
    return piezas


def _portalapiz(
    c: dict[str, float],
    hecho: dict[str, Any],
    z: dict[str, tuple[float, float]],
    punta: Punto,
    cortes: list[tuple[str, Any]] | None = None,
) -> list[Colocada]:
    """El lápiz y lo que lo sujeta, en la punta del cinco barras.

    La punta es un tubo hueco y el portaminas pasa por dentro: así lo que gira
    sobre la punta no mueve la mina. El portaminas va rígido sobre las dos
    láminas, y es la mesa la que baja para levantar.
    """
    # Quien solo quiere dónde van las piezas no necesita sus agujeros.
    cortes = [] if cortes is None else cortes
    from build123d import Align, Box, Pos, Rot

    piezas: list[Colocada] = []
    g = math.degrees(c["brazo_origen_giro"])
    hacia = Pos(punta[0], punta[1], 0.0) * Rot(Z=g)

    def poner(nombre: str, solido: Any) -> None:
        piezas.append(Colocada(nombre, hacia * solido, True))

    tubo = z["punta_tubo"]
    poner("tubo_punta", Pos(0, 0, tubo[0]) * hecho["tubo_punta"])
    # Entre los dos distales queda el plano del proximal 2, vacío en la punta:
    # lo llena un casquillo en el tubo.
    poner("casquillo_punta", Pos(0, 0, z["distal_2"][1]) * hecho["casquillo_punta"])
    # Marco del cinco barras con el origen en la punta: el brazo va a +Y.
    poner("brazo_horquilla", Pos(0, 0, tubo[1]) * Rot(Z=90) * hecho["brazo_horquilla"])
    pie = tubo[1] + c["horquilla_espesor"]
    cara_poste = c["horquilla_largo"] - c["poste_horquilla_fondo"] / 2
    poner(
        "poste_horquilla",
        _en_plano(
            hecho["poste_horquilla"],
            (0.0, cara_poste, pie + c["poste_horquilla_tornillo_al_pie"]),
            (0, 0, 1),
            (0, 1, 0),
        ),
    )
    tope = pie + c["poste_horquilla_alto"]
    poner("pinza", Pos(0, 0, tope - c["pinza_largo"]) * hecho["pinza"])
    # Las láminas: el largo libre, horizontal, y cada pestaña doblada hacia
    # abajo contra su cara.
    cara_pinza = c["pinza_al_borde"]
    libre = cara_poste - cara_pinza
    for n, zl in enumerate((tope - 22.0, tope - 2.0), start=1):
        lamina = Pos(0, cara_pinza, zl) * Box(
            c["flexura_ancho"],
            libre,
            c["flexura_espesor"],
            align=(Align.CENTER, Align.MIN, Align.CENTER),
        )
        for y_pestana in (cara_pinza, cara_poste - c["flexura_espesor"]):
            lamina += Pos(0, y_pestana, zl) * Box(
                c["flexura_ancho"],
                c["flexura_espesor"],
                c["flexura_empotramiento"],
                align=(Align.CENTER, Align.MIN, Align.MAX),
            )
        poner(f"lamina_flexura_{n}", lamina)
    poner("portaminas", Pos(0, 0, c["mesa_altura"]) * hecho["portaminas"])

    # --- la tornillería -----------------------------------------------------
    from emit import fijaciones as fj

    def cortar(nombre: str, solido: Any) -> None:
        cortes.append((nombre, hacia * solido))

    # El prisionero de la pinza, por su cara -X: la de proa lleva las láminas.
    medio = tope - c["pinza_largo"] / 2
    r_agujero = c["pinza_agujero_diametro"] / 2
    d, largo = PRISIONERO
    tornillo = _cilindro(
        (d - JUEGO_GIRATORIO) / 2,
        (-(r_agujero + 0.01 + largo), 0.0, medio),
        (-(r_agujero + 0.01), 0.0, medio),
    )
    poner("prisionero_pinza", tornillo)
    cortar(
        "pinza", _cilindro(d / 2, (-cara_pinza - 0.5, 0.0, medio), (-r_agujero + 0.5, 0.0, medio))
    )
    # Un M2 por pestaña: dos en el poste y dos en la pinza, con la cabeza en
    # el lado libre de la lámina.
    e = c["flexura_espesor"]
    k = 0
    for n, zl in enumerate((tope - 22.0, tope - 2.0), start=1):
        zt = zl - c["flexura_empotramiento"] / 2
        for cara, hacia_pieza, anfitrion in (
            (cara_pinza + e, (0.0, -1.0, 0.0), "pinza"),
            (cara_poste - e, (0.0, 1.0, 0.0), "poste_horquilla"),
        ):
            k += 1
            en = _en_plano(
                fj.allen(2.0, LARGO_LAMINA),
                (0.0, cara, zt),
                (1.0, 0.0, 0.0),
                (0.0, -hacia_pieza[1], 0.0),
            )
            poner(f"tornillo_lamina_{k}", en)
            agujero = _en_plano(
                fj.taladro(2.0, LARGO_LAMINA + e),
                (0.0, cara, zt),
                (1.0, 0.0, 0.0),
                (0.0, -hacia_pieza[1], 0.0),
            )
            cortar(anfitrion, agujero)
            cortar(f"lamina_flexura_{n}", agujero)
    return piezas
