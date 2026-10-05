"""La explosión, declarada: de cada grupo y de la máquina entera.

**Nada se ajusta mirando.** Cada grupo declara en `EXPLOSIONES`:

- `eje` y `separacion`: la dirección en que se monta el grupo y los mm entre
  una pieza y la siguiente. El orden es el de su **marca** en el registro
  (`docs/numeracion.json`), que es el orden de montaje: la pieza de marca n
  sube n-1 separaciones. Dos piezas con la misma marca —los dos sectores—
  suben lo mismo: están en sitios distintos.
- `eje_conjunto` y `separacion_conjunto`: hacia dónde sale el grupo entero,
  como un bloque, en la explosión de la máquina, en el marco de la base a
  escuadra (+Y hacia atrás, por donde sale el cartucho; -Y hacia la mesa;
  +Z hacia arriba).

Ajustado a ojo, a la tercera cota que se mueva deja de cuadrar y nadie se
entera. Declarado, lo comprueba un test que mide cajas: que los bloques no se
solapen y que los globos no se pisen ni tapen la pieza que describen.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class Explosion:
    eje: tuple[float, float, float]
    """Hacia dónde se monta el grupo: sus piezas se separan por aquí."""
    separacion: float
    """mm entre una pieza del grupo y la siguiente."""
    eje_conjunto: tuple[float, float, float]
    """Hacia dónde sale el grupo como bloque en la explosión de la máquina, en
    el marco de la base a escuadra. **Cuánto** sale no se declara: se deriva
    (`explosionar_conjunto`)."""


Caja = tuple[float, float, float, float]

ARRIBA = (0.0, 0.0, 1.0)
QUIETO = (0.0, 0.0, 0.0)
DELANTE = (0.0, -1.0, 0.0)

EXPLOSIONES: dict[str, Explosion] = {
    "bastidor": Explosion(ARRIBA, 30.0, QUIETO),
    "accionamiento": Explosion(ARRIBA, 12.0, ARRIBA),
    "entre_puntos": Explosion(ARRIBA, 12.0, ARRIBA),
    "cartucho": Explosion(ARRIBA, 10.0, ARRIBA),
    "levas": Explosion(ARRIBA, 8.0, ARRIBA),
    "seguidores": Explosion(ARRIBA, 10.0, (-1.0, 0.0, 0.0)),
    "amplificador": Explosion(ARRIBA, 14.0, (1.0, 0.0, 0.0)),
    "cinco_barras": Explosion(ARRIBA, 30.0, DELANTE),
    "levantamiento": Explosion(ARRIBA, 14.0, DELANTE),
    "portalapiz": Explosion(ARRIBA, 10.0, (0.0, -1.0, 1.0)),
}
"""Una por grupo de `emit.montaje.GRUPOS`, en el **orden en que se colocan**
los bloques de la explosión de conjunto: el bastidor queda quieto y cada uno
de los demás sale por su eje lo justo para no tocar a los anteriores."""

HUECO = 12.0
"""mm, en la isométrica, entre un bloque y los que ya están colocados."""

PASO = 2.0
"""mm con que se busca la distancia de cada bloque."""

VISTA_ISOMETRICA = ((600.0, -800.0, 600.0), (0.0, 0.0, 1.0), (0.0, 0.0, 60.0))
"""Desde dónde, qué es arriba y adónde se mira: la isométrica del dossier."""


def _proyector() -> Any:
    """La proyección de la isométrica, para cajas: (x, y, z) → (u, v)."""
    origen, arriba, mira = VISTA_ISOMETRICA
    f = [m - o for m, o in zip(mira, origen, strict=True)]
    n = math.sqrt(sum(x * x for x in f))
    f = [x / n for x in f]
    derecha = [
        f[1] * arriba[2] - f[2] * arriba[1],
        f[2] * arriba[0] - f[0] * arriba[2],
        f[0] * arriba[1] - f[1] * arriba[0],
    ]
    n = math.sqrt(sum(x * x for x in derecha))
    derecha = [x / n for x in derecha]
    alto = [
        derecha[1] * f[2] - derecha[2] * f[1],
        derecha[2] * f[0] - derecha[0] * f[2],
        derecha[0] * f[1] - derecha[1] * f[0],
    ]

    def proyectar(p: tuple[float, float, float]) -> tuple[float, float]:
        d = [p[i] - mira[i] for i in range(3)]
        return (sum(d[i] * derecha[i] for i in range(3)), sum(d[i] * alto[i] for i in range(3)))

    return proyectar


def _unitario(v: tuple[float, float, float]) -> tuple[float, float, float]:
    n = math.sqrt(sum(x * x for x in v))
    return (0.0, 0.0, 0.0) if n == 0 else (v[0] / n, v[1] / n, v[2] / n)


def explosionar_grupo(
    piezas: Sequence[tuple[str, Any]], grupo: str, marca_de: dict[str, int], base_de: Any
) -> list[tuple[int, str, Any]]:
    """(marca, nombre, sólido desplazado) de las piezas fabricadas del grupo.
    `base_de` da la clave del listado de un nombre colocado."""
    from build123d import Pos

    e = EXPLOSIONES[grupo]
    eje = _unitario(e.eje)
    presentes = sorted({marca_de[base_de(n)] for n, _ in piezas if base_de(n) in marca_de})
    rango = {m: i for i, m in enumerate(presentes)}
    salida = []
    for nombre, solido in piezas:
        clave = base_de(nombre)
        if clave not in marca_de:
            continue
        paso = rango[marca_de[clave]] * e.separacion
        salida.append(
            (marca_de[clave], nombre, Pos(eje[0] * paso, eje[1] * paso, eje[2] * paso) * solido)
        )
    return salida


def explosionar_conjunto(
    piezas: Sequence[tuple[str, Any]],
) -> tuple[list[tuple[str, Any]], dict[str, float]]:
    """Cada pieza desplazada con su grupo, como un bloque, y cuánto ha salido
    cada grupo.

    La distancia de cada bloque se **deriva**: la menor, en pasos de `PASO`,
    a la que su caja en la isométrica queda a `HUECO` de las de los bloques
    ya colocados, en el orden de `EXPLOSIONES`. Así no hay ningún número
    puesto mirando, y si el montaje cambia la explosión se rehace sola."""
    from build123d import Pos

    from emit.montaje import grupo_de

    proyectar = _proyector()
    por_grupo: dict[str, list[tuple[str, Any]]] = {}
    for nombre, solido in piezas:
        por_grupo.setdefault(grupo_de(nombre).nombre, []).append((nombre, solido))

    def caja_proyectada(solidos: list[Any], d: tuple[float, float, float]) -> Caja:
        us, vs = [], []
        for s in solidos:
            b = s.bounding_box()
            for x in (b.min.X, b.max.X):
                for y in (b.min.Y, b.max.Y):
                    for z in (b.min.Z, b.max.Z):
                        u, v = proyectar((x + d[0], y + d[1], z + d[2]))
                        us.append(u)
                        vs.append(v)
        return min(us), min(vs), max(us), max(vs)

    def con_hueco(c: Caja) -> Caja:
        return c[0] - HUECO, c[1] - HUECO, c[2] + HUECO, c[3] + HUECO

    colocadas: list[Caja] = []
    distancias: dict[str, float] = {}
    salida: list[tuple[str, Any]] = []
    for grupo, e in EXPLOSIONES.items():
        suyas = por_grupo.get(grupo, [])
        if not suyas:
            continue
        eje = _unitario(e.eje_conjunto)
        solidos = [s for _, s in suyas]
        distancia = 0.0
        if eje != (0.0, 0.0, 0.0):
            while any(
                solapan(con_hueco(caja_proyectada(solidos, tuple(distancia * x for x in eje))), o)
                for o in colocadas
            ):
                distancia += PASO
        d = (eje[0] * distancia, eje[1] * distancia, eje[2] * distancia)
        colocadas.append(caja_proyectada(solidos, d))
        distancias[grupo] = distancia
        salida += [(n, Pos(*d) * s) for n, s in suyas]
    return salida, distancias


# ---------------------------------------------------------------------------
# Globos y cajas
# ---------------------------------------------------------------------------


def caja_de(polilineas: Sequence[Sequence[tuple[float, float]]]) -> Caja:
    xs = [x for p in polilineas for x, _ in p]
    ys = [y for p in polilineas for _, y in p]
    return min(xs), min(ys), max(xs), max(ys)


def ancla_de(polilineas: Sequence[Sequence[tuple[float, float]]]) -> tuple[float, float]:
    """Dónde toca la línea de referencia: el punto dibujado de la pieza más
    cercano al centro de su caja. El centro a secas puede caer en hueco —el
    de una U, el de un aro— y la flecha no señalaría nada."""
    x0, y0, x1, y1 = caja_de(polilineas)
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    return min(
        (q for p in polilineas for q in p), key=lambda q: ((q[0] - cx) ** 2 + (q[1] - cy) ** 2, q)
    )


def solapan(a: Caja, b: Caja) -> bool:
    return a[0] < b[2] and b[0] < a[2] and a[1] < b[3] and b[1] < a[3]


@dataclass(frozen=True)
class Globo:
    clave: str
    ancla: tuple[float, float]
    """Dónde toca la línea de referencia: el centro de lo que describe."""
    centro: tuple[float, float]
    radio: float

    def caja(self) -> Caja:
        x, y = self.centro
        return x - self.radio, y - self.radio, x + self.radio, y + self.radio


def colocar_globos(
    anclas: Sequence[tuple[str, tuple[float, float]]],
    izquierda: float,
    derecha: float,
    radio: float,
) -> list[Globo]:
    """Dos columnas, una a cada lado de lo dibujado: cada globo a la altura
    de lo que describe y, si no cabe, desplazado hacia abajo lo justo para no
    pisar al de encima. Fuera del dibujo, así que no tapa ninguna pieza."""
    columnas: dict[bool, list[float]] = {True: [], False: []}
    salida = []
    medio = (izquierda + derecha) / 2
    for clave, (x, y) in sorted(anclas, key=lambda a: -a[1][1]):
        a_la_izquierda = x < medio
        ocupadas = columnas[a_la_izquierda]
        altura = y
        while any(abs(altura - o) < 2.2 * radio for o in ocupadas):
            altura -= 0.25 * radio
        ocupadas.append(altura)
        cx = izquierda - 1.6 * radio if a_la_izquierda else derecha + 1.6 * radio
        salida.append(Globo(clave, (x, y), (cx, altura), radio))
    return salida


@dataclass
class Esquema:
    """Lo que se dibuja de una explosión, en mm de la proyección."""

    lineas: list[tuple[str, float, list[tuple[float, float]]]] = field(default_factory=list)
    cajas: dict[str, Caja] = field(default_factory=dict)
    """La caja de cada bloque (de cada grupo, o de cada pieza)."""
    globos: list[Globo] = field(default_factory=list)
    distancias: dict[str, float] = field(default_factory=dict)
    """Cuánto ha salido cada grupo: derivado, se imprime con la explosión."""


def esquema_de_conjunto(piezas: Sequence[tuple[str, Any]]) -> Esquema:
    """La máquina explosionada en isométrica: un bloque por grupo, en su
    color, con un globo con su código de grupo."""
    from emit.dossier import proyectar
    from emit.montaje import GRUPOS, grupo_de

    explosionadas, distancias = explosionar_conjunto(piezas)
    esquema = Esquema(distancias=distancias)
    anclas: list[tuple[str, tuple[float, float]]] = []
    for g in GRUPOS:
        suyas = [(n, s) for n, s in explosionadas if grupo_de(n) is g]
        if not suyas:
            continue
        vista = proyectar(suyas, "isométrica", grupos=[g.nombre])
        if not vista.lineas:
            continue
        esquema.lineas += [(g.color, grosor, list(p)) for _, grosor, p in vista.lineas]
        esquema.cajas[g.nombre] = caja_de([p for _, _, p in vista.lineas])
        anclas.append((g.nombre, ancla_de([p for _, _, p in vista.lineas])))
    todo = caja_de([p for _, _, p in esquema.lineas])
    radio = 0.03 * (todo[2] - todo[0])
    esquema.globos = colocar_globos(anclas, todo[0], todo[2], radio)
    return esquema


__all__ = [
    "EXPLOSIONES",
    "Esquema",
    "Explosion",
    "Globo",
    "ancla_de",
    "caja_de",
    "colocar_globos",
    "esquema_de_conjunto",
    "explosionar_conjunto",
    "explosionar_grupo",
    "solapan",
]
