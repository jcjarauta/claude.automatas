"""El regulador del reloj en 3D: péndulo, áncora y rueda de escape montados.

Las piezas del escape **no se vuelven a dibujar**: se extruyen los polígonos
de `core/reloj/graham.py`, los mismos que juzga la envolvente y que salen en
las plantillas, a 4 mm. El péndulo sale de las cotas de los contratos
(`pendulo`, `lenteja`, `suspension`). Aquí, y solo aquí, se pasa a mm
(regla 3): build123d trabaja en milímetros.

Es un ensamblaje con nombres jerárquicos para animar cada parte por su ruta,
con cada nodo puesto en su eje de giro y sus piezas en el marco del nodo: el
visor gira cada nodo alrededor de su origen.

    /regulador/banco      tablero, ejes y soporte de la suspensión (quietos)
    /regulador/rueda      la rueda de escape, en su eje
    /regulador/ancora     yugo, paletas y horquilla, en el eje del áncora
    /regulador/pendulo    fleje, varilla, vástago y lenteja, en la flexión
    /regulador/testigos   marcas de contacto y caída, que el visor esconde

Planos, de delante (+z, la esfera) a atrás: rueda y paletas; yugo; horquilla;
péndulo; tablero. **Supuesto, no decisión**: el eje del áncora y la flexión
del péndulo son coaxiales (`bench/reloj/escape_dinamica.json`); por eso el
eje del áncora acaba en la horquilla y no llega al plano del fleje.
"""

from __future__ import annotations

from typing import Any, Final

from shapely.geometry import Polygon

from compile.regulador import HORQUILLA, Regulador, contratos_reloj, horquilla
from core.reloj.graham import contorno_rueda, nariz, paleta, yugo

MM: Final[float] = 1000.0

ESPESOR_ESCAPE: Final[float] = 4.0
"""mm: rueda, yugo y paletas, del contrato `ancora_espesor`."""

# Profundidad (z, mm) de cada plano: la cara de delante y la de atrás.
PLANO_RUEDA: Final[tuple[float, float]] = (0.0, 4.0)
PLANO_YUGO: Final[tuple[float, float]] = (-4.5, -0.5)
PLANO_HORQUILLA: Final[tuple[float, float]] = (-9.0, -7.0)
PLANO_PENDULO: Final[float] = -16.0
"""Centro del plano del péndulo: la varilla de 8 va de -20 a -12."""
PLANO_TABLERO: Final[tuple[float, float]] = (-58.0, -40.0)

COLORES: Final[dict[str, str]] = {
    "madera": "#c8a165",
    "laton": "#d4af37",
    "acero": "#9aa0a6",
    "lenteja": "#5b4636",
    "tablero": "#e8dcc4",
    "testigo": "#d00000",
}


def _prisma(figura: Polygon, z: tuple[float, float], origen: tuple[float, float]) -> Any:
    """La planta (en m) extruida de z[0] a z[1] (en mm), en el marco de un
    nodo con el origen en `origen` (m)."""
    from build123d import Plane, Polyline, extrude, make_face

    def anillo(coords: Any) -> list[tuple[float, float]]:
        return [((x - origen[0]) * MM, (y - origen[1]) * MM) for x, y in list(coords)[:-1]]

    exterior = make_face(
        Plane.XY.offset(z[0]) * Polyline(*anillo(figura.exterior.coords), close=True)
    )
    for hueco in figura.interiors:
        exterior -= make_face(Plane.XY.offset(z[0]) * Polyline(*anillo(hueco.coords), close=True))
    return extrude(exterior, amount=z[1] - z[0])


def _caja(x: tuple[float, float], y: tuple[float, float], z: tuple[float, float]) -> Any:
    from build123d import Align, Box, Pos

    return Pos(x[0], y[0], z[0]) * Box(
        x[1] - x[0], y[1] - y[0], z[1] - z[0], align=(Align.MIN, Align.MIN, Align.MIN)
    )


def _cilindro_z(centro: tuple[float, float], diametro: float, z: tuple[float, float]) -> Any:
    from build123d import Align, Cylinder, Pos

    return Pos(centro[0], centro[1], z[0]) * Cylinder(
        diametro / 2, z[1] - z[0], align=(Align.CENTER, Align.CENTER, Align.MIN)
    )


def _cilindro_y(centro_xz: tuple[float, float], diametro: float, y: tuple[float, float]) -> Any:
    from build123d import Align, Cylinder, Pos, Rot

    return Pos(centro_xz[0], y[0], centro_xz[1]) * (
        Rot(X=-90)
        * Cylinder(diametro / 2, y[1] - y[0], align=(Align.CENTER, Align.CENTER, Align.MIN))
    )


def _con(solido: Any, nombre: str, color: str, alfa: float = 1.0) -> Any:
    from build123d import Color

    solido.label = nombre
    solido.color = Color(COLORES[color], alfa)
    return solido


def piezas_del_pendulo(c: dict[str, float]) -> list[Any]:
    """En el marco de la flexión, con la varilla colgando hacia -y."""
    z0 = PLANO_PENDULO
    flexion = c["muelle_flexion_a_varilla"] * MM
    libre = c["muelle_largo_libre"] * MM
    ancho_fleje = c["muelle_ancho"] * MM
    fleje_arriba = libre / 2 + c["muelle_empotrado"] * MM
    fleje_abajo = -(libre / 2 + c["muelle_solape"] * MM)
    e_fleje = c["muelle_espesor"] * MM
    fleje = _caja(
        (-ancho_fleje / 2, ancho_fleje / 2),
        (fleje_abajo, fleje_arriba),
        (z0 - e_fleje / 2, z0 + e_fleje / 2),
    )
    ancho_v, espesor_v = c["varilla_ancho"] * MM, c["varilla_espesor"] * MM
    largo_v = c["varilla_largo"] * MM
    varilla = _caja(
        (-ancho_v / 2, ancho_v / 2),
        (-flexion - largo_v, -flexion),
        (z0 + e_fleje / 2, z0 + e_fleje / 2 + espesor_v),
    )
    zc = z0 + e_fleje / 2 + espesor_v / 2
    abajo_v = -flexion - largo_v
    vastago = _cilindro_y(
        (0.0, zc),
        c["vastago_diametro"] * MM,
        (abajo_v - c["vastago_saliente"] * MM, abajo_v + c["varilla_vastago_profundidad"] * MM),
    )
    centro_lenteja = -c["lenteja_centro_a_flexion"] * MM
    e_lenteja = c["lenteja_espesor"] * MM
    from build123d import Align, Cylinder, Pos

    lenteja = Pos(0.0, centro_lenteja, zc) * Cylinder(
        c["lenteja_diametro"] * MM / 2, e_lenteja, align=(Align.CENTER, Align.CENTER, Align.CENTER)
    )
    lenteja -= Pos(0.0, centro_lenteja, zc) * Cylinder(
        c["lenteja_taladro_diametro"] * MM / 2, e_lenteja + 2, align=(Align.CENTER,) * 3
    )
    return [
        _con(fleje, "fleje", "acero"),
        _con(varilla, "varilla", "madera"),
        _con(vastago, "vastago", "acero"),
        _con(lenteja, "lenteja", "lenteja"),
    ]


def piezas_del_ancora(reg: Regulador) -> list[Any]:
    """Yugo, paletas y horquilla, en el marco del eje del áncora."""
    a = reg.ancora
    o = a.eje_ancora
    h = horquilla(a)
    zh = PLANO_HORQUILLA
    piezas = [
        _con(_prisma(yugo(a), PLANO_YUGO, o), "yugo", "madera"),
        _con(_prisma(paleta(a, "entrada"), PLANO_RUEDA, o), "paleta_entrada", "laton"),
        _con(_prisma(paleta(a, "salida"), PLANO_RUEDA, o), "paleta_salida", "laton"),
    ]
    # La horquilla PROVISIONAL: la pletina y dos dedos que abrazan la varilla.
    c = contratos_reloj()
    pletina = _prisma(h, zh, o)
    ancho_v = c["varilla_ancho"] * MM
    largo = HORQUILLA["largo"] * MM
    z_atras = PLANO_PENDULO - c["varilla_espesor"] * MM - 1.0
    for lado in (-1.0, 1.0):
        x0 = lado * (ancho_v / 2 + 0.5)
        x1 = x0 + lado * 2.0
        pletina += _caja((min(x0, x1), max(x0, x1)), (-largo, -largo + 10.0), (z_atras, zh[1]))
    piezas.append(_con(pletina, "horquilla", "laton"))
    # El eje del áncora, de la horquilla a delante de la paleta.
    piezas.append(
        _con(
            _cilindro_z((0.0, 0.0), float(a.eje) * MM, (zh[0], PLANO_RUEDA[1] + 4)), "eje", "acero"
        )
    )
    return piezas


def testigos(reg: Regulador) -> list[Any]:
    """Una bolita roja en la nariz de cada paleta y otra entre las dos, para la
    caída. El visor no cambia colores en una animación; sí mueve piezas: el
    testigo se esconde detrás del tablero cuando no toca."""
    from build123d import Pos, Sphere

    salida = []
    for lado in ("entrada", "salida"):
        n = nariz(reg.ancora, lado)
        x, y = n.reposo[0] * MM, n.reposo[1] * MM
        salida.append(
            _con(Pos(x, y, PLANO_RUEDA[1] + 3) * Sphere(2.2), f"contacto_{lado}", "testigo")
        )
    r = float(reg.rueda.radio_punta) * MM
    salida.append(_con(Pos(0.0, r + 6, PLANO_RUEDA[1] + 3) * Sphere(3.0), "caida", "testigo"))
    return salida


def ensamblaje(reg: Regulador) -> Any:
    """El regulador montado, con el péndulo vertical y la rueda en φ = 0."""
    from build123d import Compound, Location, Pos

    c = contratos_reloj()
    eje = reg.ancora.eje_ancora
    ex, ey = eje[0] * MM, eje[1] * MM
    largo_total = (c["lenteja_centro_a_flexion"] + c["lenteja_diametro"]) * MM

    # El color, después de taladrar: la resta crea un sólido nuevo sin él.
    rueda = _prisma(contorno_rueda(reg.rueda), PLANO_RUEDA, (0.0, 0.0))
    rueda = _con(
        rueda - _cilindro_z((0.0, 0.0), float(reg.ancora.eje) * MM, (-1.0, 10.0)), "rueda", "madera"
    )

    tablero = _caja((-160.0, 160.0), (ey - largo_total - 60, ey + 120), PLANO_TABLERO)
    soporte = _caja(
        (ex - c["soporte_ancho"] * MM / 2, ex + c["soporte_ancho"] * MM / 2),
        (
            ey + c["muelle_largo_libre"] * MM / 2,
            ey + c["muelle_largo_libre"] * MM / 2 + c["soporte_alto"] * MM,
        ),
        (
            PLANO_PENDULO - c["soporte_espesor"] * MM / 2,
            PLANO_PENDULO + c["soporte_espesor"] * MM / 2,
        ),
    )
    soporte += _caja(
        (ex - 8.0, ex + 8.0),
        (ey + 20.0, ey + 60.0),
        (PLANO_TABLERO[1], PLANO_PENDULO - c["soporte_espesor"] * MM / 2),
    )
    eje_rueda = _cilindro_z(
        (0.0, 0.0), float(reg.ancora.eje) * MM, (PLANO_TABLERO[1], PLANO_RUEDA[1] + 6)
    )
    banco = Compound(
        children=[
            _con(tablero, "tablero", "tablero", 0.35),
            _con(soporte, "soporte_suspension", "madera"),
            _con(eje_rueda, "eje_rueda", "acero"),
        ],
        label="banco",
    )
    nodo_rueda = Compound(children=[rueda], label="rueda").locate(Location((0, 0, 0)))
    nodo_ancora = Compound(children=piezas_del_ancora(reg), label="ancora").locate(Pos(ex, ey, 0))
    nodo_pendulo = Compound(children=piezas_del_pendulo(c), label="pendulo").locate(Pos(ex, ey, 0))
    marcas = Compound(children=testigos(reg), label="testigos")
    return Compound(
        children=[banco, nodo_rueda, nodo_ancora, nodo_pendulo, marcas], label="regulador"
    )


__all__ = ["COLORES", "ensamblaje", "piezas_del_ancora", "piezas_del_pendulo", "testigos"]
