"""El regulador del reloj en 3D: péndulo, áncora y rueda de escape montados.

Las piezas del escape **no se vuelven a dibujar**: se extruyen los polígonos
de `core/reloj/graham.py`, los mismos que juzga la envolvente y que salen en
las plantillas, a 4 mm. El péndulo sale de las cotas de los contratos
(`pendulo`, `lenteja`, `suspension`). Aquí, y solo aquí, se pasa a mm
(regla 3): build123d trabaja en milímetros.

Es un ensamblaje con nombres jerárquicos para animar cada parte por su ruta,
con cada nodo puesto en su eje de giro y sus piezas en el marco del nodo: el
visor gira cada nodo alrededor de su origen.

    /regulador/banco      tablero, platina, puente, ejes y soporte (quietos)
    /regulador/rueda      la rueda de escape, en su eje
    /regulador/ancora     yugo, paletas y horquilla, en el eje del áncora
    /regulador/pendulo    fleje, varilla, vástago y lenteja, en la flexión
    /regulador/testigos   marcas de contacto y caída, que el visor esconde

Planos, de delante (+z, la esfera) a atrás:

    puente delantero         z  10 … 14
    rueda y paletas          z   0 …  4
    yugo                     z -4,5 … -0,5
    platina trasera          z -14 … -8
    horquilla                z -18 … -16
    péndulo (varilla)        z -28 … -20
    tablero del banco        z -70 … -52

**El eje de la rueda no llega al péndulo.** Con el áncora coaxial a la
suspensión, la varilla baja justo por detrás del centro de la rueda: el eje
de la rueda gira entre el puente y la platina trasera y acaba en ella, y la
horquilla y el péndulo van detrás. Solo el eje del áncora atraviesa la
platina, hasta la horquilla. Platina y puente son los **provisionales** del
banco R2 (ROADMAP: «una platina provisional»); el bastidor de verdad es el
paso 6. **Supuesto, no decisión**: el eje del áncora y la flexión del
péndulo son coaxiales (`bench/reloj/escape_dinamica.json`).
"""

from __future__ import annotations

from typing import Any, Final

from shapely.geometry import Polygon

from compile.regulador import HORQUILLA, Regulador, contratos_reloj, horquilla
from core.reloj.graham import contorno_rueda, nariz, paleta, yugo

MM: Final[float] = 1000.0

ESPESOR_ESCAPE: Final[float] = 4.0
"""mm: rueda, yugo y paletas, del contrato `ancora_espesor`."""

# Profundidad (z, mm) de cada plano: la cara de detrás y la de delante.
PLANO_PUENTE: Final[tuple[float, float]] = (10.0, 14.0)
PLANO_RUEDA: Final[tuple[float, float]] = (0.0, 4.0)
PLANO_YUGO: Final[tuple[float, float]] = (-4.5, -0.5)
PLANO_PLATINA: Final[tuple[float, float]] = (-14.0, -8.0)
PLANO_HORQUILLA: Final[tuple[float, float]] = (-18.0, -16.0)
PLANO_PENDULO: Final[float] = -28.0
"""El fleje; la varilla de 8 va delante de él, de -28 a -20."""
PLANO_TABLERO: Final[tuple[float, float]] = (-70.0, -52.0)

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
    z_atras = PLANO_PENDULO - 1.0
    for lado in (-1.0, 1.0):
        x0 = lado * (ancho_v / 2 + 0.5)
        x1 = x0 + lado * 2.0
        pletina += _caja((min(x0, x1), max(x0, x1)), (-largo, -largo + 10.0), (z_atras, zh[1]))
    piezas.append(_con(pletina, "horquilla", "laton"))
    # El eje del áncora, de la horquilla al puente: atraviesa la platina.
    piezas.append(
        _con(_cilindro_z((0.0, 0.0), float(a.eje) * MM, (zh[0], PLANO_PUENTE[1])), "eje", "acero")
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
    eje_d = float(reg.ancora.eje) * MM
    # La platina trasera PROVISIONAL, con el paso del eje del áncora y el
    # asiento del de la rueda, y cuatro columnas al tablero.
    abajo, arriba = -75.0, ey + 45.0
    platina = _caja((-75.0, 75.0), (abajo, arriba), PLANO_PLATINA)
    platina -= _cilindro_z((ex, ey), eje_d + 0.4, (PLANO_PLATINA[0] - 1, PLANO_PLATINA[1] + 1))
    platina -= _cilindro_z((0.0, 0.0), eje_d, (PLANO_PLATINA[0] - 1, PLANO_PLATINA[1] + 1))
    columnas = None
    for x, y in (
        (-65.0, abajo + 10),
        (65.0, abajo + 10),
        (-65.0, arriba - 10),
        (65.0, arriba - 10),
    ):
        col = _cilindro_z((x, y), 10.0, (PLANO_TABLERO[1], PLANO_PLATINA[0]))
        columnas = col if columnas is None else columnas + col
    # El puente delantero PROVISIONAL: una barra por delante de la rueda y del
    # áncora, sobre dos pilares fuera del alcance de dientes y yugo.
    puente = _caja((-8.0, 8.0), (abajo + 15, arriba - 15), PLANO_PUENTE)
    puente -= _cilindro_z((ex, ey), eje_d + 0.4, (PLANO_PUENTE[0] - 1, PLANO_PUENTE[1] + 1))
    pilares = _cilindro_z((0.0, abajo + 25), 8.0, (PLANO_PLATINA[1], PLANO_PUENTE[0]))
    pilares += _cilindro_z((0.0, arriba - 25), 8.0, (PLANO_PLATINA[1], PLANO_PUENTE[0]))
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
    # El eje de la rueda gira entre la platina y el puente: no pasa de la cara
    # de detrás de la platina, así que nunca llega a la horquilla ni al péndulo.
    eje_rueda = _cilindro_z((0.0, 0.0), eje_d, (PLANO_PLATINA[0], PLANO_PUENTE[1]))
    banco = Compound(
        children=[
            _con(tablero, "tablero", "tablero", 0.35),
            _con(soporte, "soporte_suspension", "madera"),
            _con(eje_rueda, "eje_rueda", "acero"),
            _con(platina, "platina", "madera", 0.55),
            _con(columnas, "columnas", "acero"),
            _con(puente, "puente", "madera", 0.55),
            _con(pilares, "pilares", "acero"),
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


def piezas_en_mundo(conjunto: Any, theta_grados: float = 0.0) -> dict[str, Any]:
    """Cada pieza del ensamblaje en el marco del mundo, con el péndulo y el
    áncora girados `theta_grados`: para comprobar holguras sin el visor."""
    from build123d import Rot

    salida: dict[str, Any] = {}
    for nodo in conjunto.children:
        giro = Rot(Z=theta_grados) if nodo.label in ("pendulo", "ancora") else Rot(Z=0)
        for pieza in nodo.children:
            salida[f"{nodo.label}/{pieza.label}"] = nodo.location * giro * pieza
    return salida


__all__ = [
    "COLORES",
    "ensamblaje",
    "piezas_del_ancora",
    "piezas_del_pendulo",
    "piezas_en_mundo",
    "testigos",
]
