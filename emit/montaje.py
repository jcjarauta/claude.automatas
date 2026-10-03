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
    `pila_altura`, `seguidor_plano_z`, `poste_vano` y `reductor_bahia`. No
    hay ni un número suelto, y por eso mover `base_al_plato` mueve la
    máquina entera.

    Vive aquí y no en el script del plano de conjunto porque la usan los
    dos: **el dibujo en dos vistas y el montaje en tres dimensiones tienen
    que colocar las piezas en el mismo sitio**, y dos copias de una pila de
    alturas se separan a la tercera cota que se mueva.
    """
    c = contrato_mm() if c is None else c
    bap, pl = c["base_al_plato"], c["platina_espesor"]
    p1 = (bap, bap + pl)
    leva0 = p1[1] + 2.0
    seg = leva0 + c["seguidor_plano_z"]
    p2 = (p1[1] + c["poste_vano"], p1[1] + c["poste_vano"] + pl)
    p3 = (p2[1] + c["reductor_bahia"], p2[1] + c["reductor_bahia"] + pl)
    return {
        "base": (-c["base_espesor"], 0.0),
        "mesa": (c["mesa_altura"] - c["mesa_espesor"], c["mesa_altura"]),
        "plato1": p1,
        "levas": (leva0, leva0 + c["pila_altura"]),
        "seguidores": (seg, seg + c["seguidor_espesor"]),
        "sector": (seg + c["seguidor_espesor"], seg + c["seguidor_espesor"] + 5.0),
        "balancin": (seg + c["balancin_entrada"], seg + c["balancin_entrada"]),
        "plato2": p2,
        "bahia": (p2[1], p3[0]),
        "plato3": p3,
        "poste": (-c["base_poste_empotrado"], p3[1]),
    }


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
    """Los sólidos de la plataforma sin colocar, uno por pieza distinta.

    Extruir un perfil cuesta, y en un barrido se repite en cada ángulo la
    misma plancha. Construirlos una vez y recolocarlos deja el barrido en
    segundos en vez de en minutos; es la diferencia entre un test que se
    ejecuta y uno que se desactiva.
    """
    from emit.catalogo import cargar
    from emit.catalogo import solido_de as solido_comercial

    c = contrato_mm() if c is None else c
    piezas = {n: solido_de(n, c) for n in ("platina_levas", "base", "seguidor", "sector")}
    piezas["brazo_proximal"] = solido_de("brazo_proximal", c)
    piezas["brazo_distal"] = solido_de("brazo_distal", c)
    piezas["poste"] = solido_comercial(next(p for p in cargar() if p.nombre == "poste_pivote"))
    return piezas


def colocar(
    levas: list[Any],
    seguidores: list[Any],
    estado: Estado,
    c: dict[str, float] | None = None,
    piezas_base: dict[str, Any] | None = None,
) -> list[Colocada]:
    """Las piezas de la máquina colocadas en 3D, en el marco de la leva.

    `levas` son las `Pieza` que salen de compilar el pedido y `seguidores`
    los `core.cam.synth.Seguidor` de la máquina: este módulo **no importa
    el compilador**, porque los emisores están debajo de él. Quien llame
    calcula el estado; aquí solo se coloca.

    **Lo que todavía no entra**: la cadena del levantamiento —bieleta,
    tirante, mesa y sus bielas— porque esas piezas aún no están dibujadas,
    y con ellas el balancín y la palanca, que existen pero no tienen a qué
    agarrarse. Está en `docs/ensamblaje.md` §8.
    """
    from emit.step import solido_de_pieza

    c = contrato_mm() if c is None else c
    hecho = taller(c) if piezas_base is None else piezas_base
    z, piezas = alturas(c), []
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

    # --- lo que gira con el árbol -------------------------------------------
    for i, pieza in enumerate(levas):
        altura = z["levas"][0] + i * (c["pila_altura"] - 3.0 * 5.0) / 2.0 + i * 5.0
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
        if i < 2:  # el canal del elevador no lleva cabestrante
            piezas.append(
                Colocada(
                    f"sector_{i + 1}", _poner(sector_solido, angulo, pivote, z["sector"][0]), True
                )
            )

    # --- el varillaje --------------------------------------------------------
    proximal, distal = hecho["brazo_proximal"], hecho["brazo_distal"]
    sep = c["brazo_separacion"] / 2.0
    for lado, (x, psi) in enumerate(
        ((-sep, estado.psi_izquierdo), (sep, estado.psi_derecho)),
    ):
        pivote = al_marco((x, 0.0))
        giro = psi + c["brazo_origen_giro"]
        piezas.append(
            Colocada(
                f"proximal_{lado + 1}",
                _poner(proximal, giro, pivote, z["plato1"][0] - 4.0 - lado),
                True,
            )
        )
        codo_plano = (x + c["brazo_proximal"] * math.cos(psi), c["brazo_proximal"] * math.sin(psi))
        punta = (0.0, c["caja_centro_y"])
        piezas.append(
            Colocada(
                f"distal_{lado + 1}",
                _poner(
                    distal,
                    math.atan2(punta[1] - codo_plano[1], punta[0] - codo_plano[0])
                    + c["brazo_origen_giro"],
                    al_marco(codo_plano),
                    z["plato1"][0] - 8.0 - lado,
                ),
                True,
            )
        )

    return piezas
