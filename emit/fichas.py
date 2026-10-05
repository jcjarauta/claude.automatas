"""Fichas de grupo y de pieza: el dossier de fabricación, pieza a pieza.

Dos hojas, las dos en A4 apaisado y con el mismo cajetín:

- **Ficha de grupo.** Para qué está el grupo, dónde va en la máquina (la
  isométrica de todo, con el grupo resaltado), su **despiece** —explosionado,
  con un globo por marca— y la lista de piezas: marca, pieza, cantidad,
  material, proceso y la ficha que la dibuja. Detrás, la secuencia de montaje
  del grupo, su tornillería y lo que le falta.
- **Ficha de pieza.** Cuatro vistas en **sistema europeo** —alzado arriba a la
  izquierda, perfil izquierdo a su derecha, planta debajo del alzado— y una
  isométrica; las tres primeras a una escala normalizada común. Cotas de
  conjunto, los diámetros y radios, el datum y una tabla de taladros; y la
  tabla de **variables**: cada una con su nombre de contrato, que es lo que se
  teclea en el CAD, y su valor.

**Cada cota dice de qué variable sale.** Junto al número va, en un círculo, la
fila de la tabla de variables donde está su `#cota.nombre`
cuando el valor es el de una variable de la ficha. Una cota sin variable es
una cota que nadie va a poder cambiar desde el contrato, y la hoja lo enseña.

**Es un emisor y solo traduce.** Las formas salen del taller
(`emit.montaje.taller`), las colocaciones de `colocar`, los datos de cada pieza
de su `Ficha` y los números del contrato. **Determinista**: el mismo contrato da
el mismo PDF byte a byte.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from emit.dossier import _polilinea, proyectar
from emit.montaje import GRUPOS, Grupo, grupo_de
from emit.plataforma import LISTADO, Ficha, valor

MM = 72.0 / 25.4
"""Puntos por milímetro: reportlab trabaja en puntos."""

ANCHO, ALTO = 297.0, 210.0
MARGEN = 8.0
CAJETIN = (187.0, MARGEN, ANCHO - MARGEN - 187.0, 40.0)
"""x, y, ancho, alto del cajetín, en mm de la hoja."""

ESCALAS = (10.0, 5.0, 2.0, 1.0, 0.5, 0.2, 0.1)
"""Las escalas normalizadas (UNE-EN ISO 5455), de mayor a menor."""

VISTAS_PIEZA: dict[str, tuple[tuple[float, float, float], tuple[float, float, float]]] = {
    "alzado": ((0.0, -1.0, 0.0), (0.0, 0.0, 1.0)),
    "perfil izquierdo": ((-1.0, 0.0, 0.0), (0.0, 0.0, 1.0)),
    "planta": ((0.0, 0.0, 1.0), (0.0, 1.0, 0.0)),
    "isométrica": ((1.0, -1.0, 1.0), (0.0, 0.0, 1.0)),
}
"""Desde dónde se mira cada pieza (dirección hacia el observador) y qué es
arriba. La pieza está en su marco de taller: el perfil en XY, extruida en Z,
con el datum en el origen."""

CELDAS = {
    "alzado": (MARGEN, 106.0, 89.0, 96.0),
    "perfil izquierdo": (MARGEN + 89.0, 106.0, 89.0, 96.0),
    "planta": (MARGEN, MARGEN, 89.0, 96.0),
    "isométrica": (MARGEN + 89.0, MARGEN, 89.0, 96.0),
}
"""x, y, ancho, alto de cada vista en la hoja. Sistema europeo: el perfil
izquierdo a la derecha del alzado y la planta debajo."""

HUECO_COTAS = 13.0
"""mm de cada celda que se reservan alrededor de la vista para las cotas."""

from emit import acotado, estilo  # noqa: E402
from emit.estilo import COTA, GRIS, TINTA  # noqa: E402

Polilinea = list[tuple[float, float]]


# ---------------------------------------------------------------------------
# Texto
# ---------------------------------------------------------------------------


def _texto(t: str) -> str:
    """Lo que Helvetica sabe escribir: las fuentes estándar del PDF van en
    Windows-1252, y lo que no está ahí sale como un cuadrado."""
    sustituir = {chr(0x2212): "-", chr(0x2192): "->", chr(0x2248): "~", chr(0x03B8): "theta"}
    t = "".join(sustituir.get(ch, ch) for ch in t).replace("**", "")
    return t.encode("cp1252", "replace").decode("cp1252")


def _numero(x: float) -> str:
    return f"{round(x, 2):g}".replace(".", ",")


def _parrafo(cv: Any, texto: str, x: float, y: float, ancho: float, cuerpo: float) -> float:
    """Escribe un párrafo con saltos de línea a mano y devuelve la y de debajo."""
    from reportlab.pdfbase.pdfmetrics import stringWidth

    palabras = _texto(texto).split()
    linea = ""
    cv.setFont("Helvetica", cuerpo)
    for palabra in palabras:
        prueba = f"{linea} {palabra}".strip()
        if stringWidth(prueba, "Helvetica", cuerpo) / MM > ancho and linea:
            cv.drawString(x * MM, y * MM, linea)
            y -= cuerpo * 0.42
            linea = palabra
        else:
            linea = prueba
    if linea:
        cv.drawString(x * MM, y * MM, linea)
        y -= cuerpo * 0.42
    return y


# ---------------------------------------------------------------------------
# Las vistas de una pieza
# ---------------------------------------------------------------------------


@dataclass
class VistaPieza:
    """Una vista proyectada de una pieza, en mm del modelo."""

    visibles: list[Polilinea]
    ocultas: list[Polilinea]
    circulos: list[tuple[float, float, float, bool]]
    """(cx, cy, r, entero) de las aristas circulares visibles."""
    medidas: tuple[float, float, float, float] | None = None
    """La caja **exacta** de la pieza en los ejes de la vista: de ella salen
    las cotas. La de las polilíneas no vale: un círculo dibujado es un
    polígono, y el tambor de Ø13,95 se acotaba 13,91."""

    def caja(self) -> tuple[float, float, float, float]:
        if self.medidas is not None:
            return self.medidas
        xs = [x for p in self.visibles + self.ocultas for x, _ in p]
        ys = [y for p in self.visibles + self.ocultas for _, y in p]
        return min(xs), min(ys), max(xs), max(ys)


EJES_DE_VISTA = {
    "alzado": ((0, 1.0), (2, 1.0)),
    "perfil izquierdo": ((1, -1.0), (2, 1.0)),
    "planta": ((0, 1.0), (1, 1.0)),
}
"""Qué eje del modelo es la horizontal y cuál la vertical de cada vista, con
su signo: medido con un sólido asimétrico, el perfil izquierdo lleva -Y."""


def _polilinea_fina(arista: Any, escala: float) -> Polilinea:
    """Como la del dossier, pero con los arcos partidos según lo que miden
    en el papel: un M3 a 2:1 no puede salir hexagonal."""
    from build123d import GeomType

    if arista.geom_type == GeomType.LINE:
        return _polilinea(arista)
    pasos = max(12, min(400, int(arista.length * escala / 0.35)))
    puntos = [arista.position_at(i / pasos) for i in range(pasos + 1)]
    return [(round(q.X, 4), round(q.Y, 4)) for q in puntos]


def vista_de_pieza(solido: Any, vista: str, escala: float = 1.0) -> VistaPieza:
    from build123d import GeomType

    hacia, arriba = VISTAS_PIEZA[vista]
    origen = tuple(1000.0 * v for v in hacia)
    visibles, ocultas = solido.project_to_viewport(origen, arriba, (0.0, 0.0, 0.0))
    circulos = []
    for arista in visibles:
        if arista.geom_type == GeomType.CIRCLE:
            a, b = arista.position_at(0.0), arista.position_at(1.0)
            # «Entero» para acotar: un círculo cerrado, o un arco de más de
            # media vuelta —un eje con cara plana se acota por su diámetro.
            entero = (a - b).length < 1e-6 or arista.length > math.pi * arista.radius * 1.02
            centro = arista.arc_center
            circulos.append(
                (round(centro.X, 3), round(centro.Y, 3), round(arista.radius, 3), entero)
            )
    medidas = None
    if vista in EJES_DE_VISTA:
        b = solido.bounding_box(optimal=True)
        bajo, alto = (b.min.X, b.min.Y, b.min.Z), (b.max.X, b.max.Y, b.max.Z)
        (ih, sh), (iv, sv) = EJES_DE_VISTA[vista]
        h = sorted((bajo[ih] * sh, alto[ih] * sh))
        v = sorted((bajo[iv] * sv, alto[iv] * sv))
        medidas = (round(h[0], 4), round(v[0], 4), round(h[1], 4), round(v[1], 4))
    return VistaPieza(
        visibles=[_polilinea_fina(a, escala) for a in visibles],
        ocultas=[_polilinea_fina(a, escala) for a in ocultas],
        circulos=sorted(set(circulos)),
        medidas=medidas,
    )


def escala_comun(vistas: dict[str, VistaPieza]) -> float:
    """La mayor escala normalizada a la que caben las tres vistas
    ortográficas, cada una en su celda con el hueco de las cotas."""
    for escala in ESCALAS:
        cabe = True
        for nombre, v in vistas.items():
            if nombre == "isométrica":
                continue
            x0, y0, x1, y1 = v.caja()
            _, _, w, h = CELDAS[nombre]
            if (x1 - x0) * escala > w - 2 * HUECO_COTAS or (y1 - y0) * escala > h - 2 * HUECO_COTAS:
                cabe = False
        if cabe:
            return escala
    return ESCALAS[-1]


def _rotulo_escala(escala: float) -> str:
    return f"{escala:g}:1" if escala >= 1 else f"1:{1 / escala:g}"


# ---------------------------------------------------------------------------
# Dibujo
# ---------------------------------------------------------------------------


@dataclass
class _Lienzo:
    """Una vista puesta en la hoja: de mm del modelo a mm de la hoja."""

    cv: Any
    escala: float
    ox: float
    oy: float

    def p(self, x: float, y: float) -> tuple[float, float]:
        return (self.ox + x * self.escala) * MM, (self.oy + y * self.escala) * MM

    def polilinea(self, puntos: Polilinea, grosor: float, color: str, discontinua: bool) -> None:
        from reportlab.lib.colors import HexColor

        cv = self.cv
        cv.setStrokeColor(HexColor(color))
        cv.setLineWidth(grosor * MM)
        cv.setDash([1.2 * MM, 0.8 * MM] if discontinua else [])
        camino = cv.beginPath()
        camino.moveTo(*self.p(*puntos[0]))
        for x, y in puntos[1:]:
            camino.lineTo(*self.p(x, y))
        cv.drawPath(camino, stroke=1, fill=0)
        cv.setDash([])


def _flecha(cv: Any, x: float, y: float, dx: float, dy: float) -> None:
    """Punta de flecha rellena en (x, y), en puntos, apuntando a (dx, dy)."""
    n = math.hypot(dx, dy) or 1.0
    ux, uy = dx / n, dy / n
    largo, ancho = estilo.FLECHA_LARGO * MM, estilo.FLECHA_ANCHO * MM
    camino = cv.beginPath()
    camino.moveTo(x, y)
    camino.lineTo(x - ux * largo - uy * ancho, y - uy * largo + ux * ancho)
    camino.lineTo(x - ux * largo + uy * ancho, y - uy * largo - ux * ancho)
    camino.close()
    cv.drawPath(camino, stroke=0, fill=1)


def _cota(
    cv: Any,
    a: tuple[float, float],
    b: tuple[float, float],
    separacion: tuple[float, float],
    texto: str,
    ref: str,
) -> None:
    """Cota lineal entre dos puntos de la hoja, desplazada `separacion`, con
    sus extensiones; todo en puntos. `ref` es la fila de su variable."""
    acotado.a_pdf(
        cv,
        acotado.lineal(
            (a[0] / MM, a[1] / MM),
            (b[0] / MM, b[1] / MM),
            (separacion[0] / MM, separacion[1] / MM),
            _texto(texto),
            ref,
        ),
    )


def _rotulo_circulo(
    lienzo: _Lienzo, cx: float, cy: float, r: float, texto: str, ref: str, angulo: float
) -> None:
    """Línea de referencia desde el canto de un círculo hacia fuera, con su
    texto en el extremo."""
    x, y = lienzo.p(cx, cy)
    acotado.a_pdf(
        lienzo.cv,
        acotado.radial((x / MM, y / MM), r * lienzo.escala, angulo, _texto(texto), ref),
    )


def _marco(cv: Any) -> None:
    from reportlab.lib.colors import HexColor

    cv.setStrokeColor(HexColor(TINTA))
    cv.setLineWidth(0.5 * MM)
    cv.rect(MARGEN * MM, MARGEN * MM, (ANCHO - 2 * MARGEN) * MM, (ALTO - 2 * MARGEN) * MM)


def _cajetin(
    cv: Any, titulo: str, plano: str, hoja: str, escala: str, grupo: Grupo, version: str
) -> None:
    """El cajetín, abajo a la derecha: qué es, de qué máquina, a qué escala
    y **de qué versión**. Una hoja que circula suelta y fotocopiada por el
    taller sin versión sobrevive al diseño que la generó, y no hay forma de
    saber si es más vieja que la de al lado."""
    from reportlab.lib.colors import HexColor

    x, y, w, h = CAJETIN
    cv.setStrokeColor(HexColor(TINTA))
    cv.setLineWidth(0.35 * MM)
    cv.rect(x * MM, y * MM, w * MM, h * MM)
    for fy in (y + h - 12, y + 12):
        cv.line(x * MM, fy * MM, (x + w) * MM, fy * MM)
    cv.line((x + w * 0.62) * MM, y * MM, (x + w * 0.62) * MM, (y + 12) * MM)
    cv.setFillColor(HexColor(grupo.color))
    cv.rect((x + 2) * MM, (y + h - 10) * MM, 4 * MM, 8 * MM, stroke=0, fill=1)
    cv.setFillColor(HexColor(TINTA))
    cv.setFont("Helvetica-Bold", 11)
    cv.drawString((x + 8) * MM, (y + h - 7.5) * MM, _texto(titulo))
    cv.setFont(estilo.FUENTE_NEGRITA, 7)
    cv.setFillColor(HexColor(COTA))
    cv.drawString((x + 3) * MM, (y + 22.5) * MM, _texto(estilo.NO_MEDIR))
    cv.setFillColor(HexColor(TINTA))
    cv.setFont(estilo.FUENTE, 7)
    cv.drawString((x + 3) * MM, (y + 17) * MM, _texto("Escribiente · claude.automatas"))
    cv.drawString((x + 3) * MM, (y + 13.5) * MM, _texto(f"Grupo: {grupo.nombre} · {version}"))
    cv.drawString((x + 3) * MM, (y + 7) * MM, _texto(f"Plano {plano}"))
    cv.drawString((x + 3) * MM, (y + 3) * MM, _texto("Cotas en mm · sistema europeo"))
    cv.drawString((x + w * 0.62 + 3) * MM, (y + 7) * MM, _texto(f"Escala {escala}"))
    cv.drawString((x + w * 0.62 + 3) * MM, (y + 3) * MM, _texto(f"Hoja {hoja}"))


def _tabla(
    cv: Any,
    x: float,
    y: float,
    anchos: Sequence[float],
    filas: Sequence[Sequence[str]],
    cuerpo: float = 6.0,
) -> float:
    """Una tabla sencilla con cabecera; devuelve la y de debajo."""
    from reportlab.lib.colors import HexColor
    from reportlab.pdfbase.pdfmetrics import stringWidth

    alto = cuerpo * 0.5
    cv.setLineWidth(0.15 * MM)
    cv.setStrokeColor(HexColor("#c4c7cc"))
    for i, fila in enumerate(filas):
        cv.setFont("Helvetica-Bold" if i == 0 else "Helvetica", cuerpo)
        cv.setFillColor(HexColor(TINTA if i else "#41464d"))
        cx = x
        for celda, ancho in zip(fila, anchos, strict=True):
            t = _texto(celda)
            while stringWidth(t, "Helvetica", cuerpo) / MM > ancho - 1.2 and len(t) > 2:
                t = t[:-2] + "…"
            cv.drawString((cx + 0.6) * MM, (y - alto + 0.9) * MM, t)
            cx += ancho
        cv.line(x * MM, (y - alto) * MM, (x + sum(anchos)) * MM, (y - alto) * MM)
        y -= alto
    return y - 2.0


# ---------------------------------------------------------------------------
# Variables: qué cota sale de qué número del contrato
# ---------------------------------------------------------------------------


def _variables(ficha: Ficha, c: dict[str, float]) -> list[tuple[Any, float]]:
    salida = []
    for v in ficha.variables:
        try:
            salida.append((v, valor(c, v)))
        except KeyError:
            continue
    return salida


def con_sufijo(texto: str, variable: str, ficha: Ficha) -> str:
    """El texto de una cota con la tolerancia o la rosca de su variable:
    «Ø10 h6», «Ø3 M3»."""
    sufijo = next((v.sufijo for v in ficha.variables if v.nombre == variable), "")
    return f"{texto} {sufijo}".strip()


def es_diametro(v: Any) -> bool:
    """Si una variable es un diámetro: lo dice su rótulo («Ø de paso») o su
    nombre (`…_diametro`). Es la clase de la cota, no su valor."""
    return str(v.etiqueta).lstrip().startswith("Ø") or v.nombre.endswith("_diametro")


def es_radio(v: Any) -> bool:
    """Si una variable es un radio: «R del cubo», `…_radio`. Para un arco de
    contorno el CAD pide radio, y es el gemelo `_radio` lo que se teclea."""
    return str(v.etiqueta).lstrip().startswith("R") or v.nombre.endswith("_radio")


CLASES = ("diametro", "radio", "distancia")


def variable_de(
    medida: float, ficha: Ficha, c: dict[str, float], clase: str, preferir: str = ""
) -> str:
    """La variable de la ficha que da esta cota, mirando **su clase** además
    de su valor.

    Casar solo por valor es la trampa que ya se pagó en `comparar_dxf.py`:
    con unas cuantas cotas, cualquier número redondo encuentra una que lo
    explique. El calzo tiene un cubo de Ø22 y un tornillo a 22 del centro, y
    el diámetro salía con el nombre de la distancia. Un diámetro casa con
    diámetros, un radio con la mitad de un diámetro, una distancia con lo que
    no es diámetro. Si aun así casan dos, se dice: «ambigua: a | b».
    """
    if clase not in CLASES:
        raise ValueError(f"clase de cota «{clase}»: {CLASES}")
    candidatas: list[str] = []
    for v, x in _variables(ficha, c):
        if v.mapa != "cota":
            continue
        radio = es_radio(v)
        diametro = es_diametro(v) and not radio
        if clase == "diametro":
            casa = (diametro and abs(x - medida) < 0.011) or (radio and abs(2 * x - medida) < 0.011)
        elif clase == "radio":
            casa = (diametro and abs(x / 2 - medida) < 0.011) or (radio and abs(x - medida) < 0.011)
        else:
            casa = not diametro and not radio and abs(x - medida) < 0.011
        if casa and v.nombre not in candidatas:
            candidatas.append(v.nombre)
    if len(candidatas) > 1 and preferir:
        # Un rasgo con nombre propio desempata sin adivinar: la cuerda de una
        # cara plana es la variable de la cuerda aunque el ancho valga igual.
        con_nombre = [n for n in candidatas if preferir in n]
        if len(con_nombre) == 1:
            return con_nombre[0]
    if len(candidatas) > 1:
        return "ambigua: " + " | ".join(candidatas)
    return candidatas[0] if candidatas else ""


# ---------------------------------------------------------------------------
# Lo que se lee en la planta: contorno y taladros, de la geometría
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Arco:
    """Un arco del contorno exterior: se acota en la vista, no en la tabla."""

    cx: float
    cy: float
    r: float
    entero: bool
    """Un círculo cerrado o más de media vuelta: se acota por su diámetro."""


@dataclass(frozen=True)
class Taladro:
    """Un hueco que atraviesa la pieza: un contorno interior de su cara de
    arriba. Lo de fuera —un cubo, un extremo redondeado— no es un taladro
    aunque sea un círculo, y en la tabla de taladros haría un agujero donde
    va material."""

    letra: str
    tipo: str
    """«taladro», «en D», «ranura» o «contorno»."""
    cx: float
    cy: float
    diametro: float
    recorrido: float = 0.0
    """En una ranura, la distancia entre los centros de sus dos arcos."""


@dataclass(frozen=True)
class Rasgos:
    contorno: tuple[Arco, ...]
    taladros: tuple[Taladro, ...]


def rasgos(solido: Any) -> Rasgos:
    """El contorno y los taladros de la cara de arriba de la pieza, leídos de
    la geometría y no de su dibujo."""
    from build123d import GeomType

    zmax = solido.bounding_box(optimal=True).max.Z
    caras = [
        f
        for f in solido.faces()
        if f.geom_type == GeomType.PLANE and abs(f.center().Z - zmax) < 1e-6
    ]
    if not caras:
        return Rasgos((), ())
    cara = max(caras, key=lambda f: f.area)

    def arcos(alambre: Any) -> list[Any]:
        return [e for e in alambre.edges() if e.geom_type == GeomType.CIRCLE]

    contorno = []
    for e in arcos(cara.outer_wire()):
        entero = (
            e.position_at(0) - e.position_at(1)
        ).length < 1e-6 or e.length > math.pi * e.radius
        contorno.append(
            Arco(round(e.arc_center.X, 3), round(e.arc_center.Y, 3), round(e.radius, 3), entero)
        )

    huecos = []
    for alambre in cara.inner_wires():
        circulos = arcos(alambre)
        lineas = len(alambre.edges()) - len(circulos)
        if len(circulos) == 1 and lineas == 0:
            e = circulos[0]
            huecos.append(("taladro", e.arc_center.X, e.arc_center.Y, 2 * e.radius, 0.0))
        elif len(circulos) == 1:
            e = circulos[0]
            huecos.append(("en D", e.arc_center.X, e.arc_center.Y, 2 * e.radius, 0.0))
        elif len(circulos) == 2 and abs(circulos[0].radius - circulos[1].radius) < 1e-6:
            a, b = circulos[0].arc_center, circulos[1].arc_center
            huecos.append(
                ("ranura", (a.X + b.X) / 2, (a.Y + b.Y) / 2, 2 * circulos[0].radius, (a - b).length)
            )
        else:
            centro = alambre.center()
            huecos.append(("contorno", centro.X, centro.Y, 0.0, 0.0))
    huecos.sort(key=lambda h: (round(h[1], 3), round(h[2], 3), h[0]))
    taladros = tuple(
        Taladro(chr(ord("A") + i), t, round(x, 3), round(y, 3), round(d, 3), round(r, 3))
        for i, (t, x, y, d, r) in enumerate(huecos)
    )
    return Rasgos(tuple(sorted(set(contorno), key=lambda a: (a.r, a.cx, a.cy))), taladros)


# ---------------------------------------------------------------------------
# La sección
# ---------------------------------------------------------------------------


def cortar(solido: Any) -> Any:
    """La pieza cortada por el plano XZ que pasa por el datum, quedándose con
    la mitad de atrás: vista desde delante, es la sección A-A."""
    from build123d import Box, Pos

    b = solido.bounding_box(optimal=True)
    lado = 4.0 * max(b.size.X, b.size.Y, b.size.Z) + 10.0
    detras = Pos(b.center().X, lado / 2.0, b.center().Z) * Box(lado, lado, lado)
    return solido & detras


def caras_cortadas(cortado: Any) -> list[Any]:
    """Las caras del corte —planas, en y = 0, mirando hacia delante— como
    polígonos de shapely en (X, Z): lo que se raya."""
    from build123d import GeomType
    from shapely.geometry import Polygon

    def puntos(alambre: Any) -> list[tuple[float, float]]:
        salida = []
        for e in alambre.edges():
            pasos = 1 if e.geom_type == GeomType.LINE else max(8, int(e.length / 0.2))
            for i in range(pasos):
                p = e.position_at(i / pasos)
                salida.append((p.X, p.Z))
        return salida

    poligonos = []
    for f in cortado.faces():
        if f.geom_type != GeomType.PLANE or abs(f.center().Y) > 1e-6:
            continue
        if abs(abs(f.normal_at().Y) - 1.0) > 1e-6:
            continue
        exterior = puntos(f.outer_wire())
        if len(exterior) >= 3:
            poligonos.append(Polygon(exterior, [puntos(w) for w in f.inner_wires()]).buffer(0))
    return poligonos


def _rayado(lienzo: Any, poligono: Any, paso_papel: float = 1.3) -> None:
    """Rayado a 45° de una cara cortada, recortado a la cara."""
    from shapely.geometry import LineString

    paso = paso_papel / lienzo.escala
    x0, y0, x1, y1 = poligono.bounds
    k = x0 - (y1 - y0)
    while k < x1:
        raya = LineString([(k, y0), (k + (y1 - y0), y1)]).intersection(poligono)
        partes = getattr(raya, "geoms", [raya])
        for parte in partes:
            if parte.geom_type == "LineString" and not parte.is_empty:
                lienzo.polilinea(list(parte.coords), 0.12, TINTA, False)
        k += paso * math.sqrt(2.0)


# ---------------------------------------------------------------------------
# La ficha de pieza
# ---------------------------------------------------------------------------


@dataclass
class Pieza:
    """Lo que hace falta para la ficha de una pieza."""

    nombre: str
    """La clave del `LISTADO`."""
    marca: int
    plano: str
    solido: Any
    cantidad_en_el_grupo: int
    vistas: dict[str, VistaPieza] = field(default_factory=dict)
    acotacion: Any = None
    """Lo que su ficha rotula (`emit.dibujable.Acotacion`): el test lo cruza
    con el perfil y lo busca en el PDF."""


def _clase_de_extension(medida: float, contorno: Sequence[Arco]) -> str:
    """Una cota de conjunto es un diámetro si la da un arco entero del
    contorno —el calzo mide 22 de alto porque su cubo es de Ø22—; si no, una
    distancia."""
    if any(a.entero and abs(2 * a.r - medida) < 0.011 for a in contorno):
        return "diametro"
    return "distancia"


def _globo(cv: Any, x: float, y: float, letra: str) -> None:
    """La letra de un taladro, en su globo, en puntos de la hoja."""
    from reportlab.lib.colors import HexColor

    cv.setStrokeColor(HexColor(COTA))
    cv.setFillColor(HexColor("#ffffff"))
    cv.setLineWidth(0.18 * MM)
    cv.circle(x, y, 1.9 * MM, stroke=1, fill=1)
    cv.setFillColor(HexColor(COTA))
    cv.setFont("Helvetica-Bold", 6)
    cv.drawCentredString(x, y - 0.75 * MM, letra)


TEXTO_TANGENTE = "Los tramos rectos del contorno son tangentes a los dos arcos que unen."


def _texto_extrusion(ficha: Ficha) -> str:
    """Lo que dice en qué tramo corre cada rasgo: todos, en toda la pieza.
    El eje de pivote no decía que su cara plana va en los 66 enteros, y
    deducir se olvida."""
    clase, cota = ficha.solido
    a_lo_largo = "su espesor" if clase == "plancha" else "su largo"
    return (
        f"Perfil extruido: cada rasgo de la planta —taladros, caras planas, ranuras— "
        f"atraviesa la pieza en todo {a_lo_largo}, #cota.{cota}."
    )


def _rotulo(texto: str, variable: str, ficha: Ficha) -> str:
    """El número de una cota: con su tolerancia si tiene variable, y entre
    paréntesis si no la tiene, que en dibujo técnico es una cota de
    referencia: derivada, no se fabrica a ella y no hay nada que teclear."""
    return con_sufijo(texto, variable, ficha) if variable else f"({texto})"


def _longitudes(
    perfil: Any, rectos: Sequence[int], medida: float, eje: int, texto: str, var: str
) -> list[Any]:
    """Los tramos rectos que ya mide una cota de conjunto: los alineados con
    ella y de su largo."""
    from emit.dibujable import Cota

    salida = []
    for i in rectos:
        a, b = perfil[i].a, perfil[i].b
        alineado = abs(a[1 - eje] - b[1 - eje]) < 1e-6
        if alineado and abs(abs(a[eje] - b[eje]) - medida) < 0.02:
            salida.append(Cota("longitud", texto, var, not var, medida, segmento=i))
    return salida


def _centros_del_taladro(perfil: Any, t: Taladro) -> list[tuple[float, float]]:
    """Los centros de arco que la fila de un taladro sitúa: el suyo, o los
    dos de una ranura, a medio recorrido a cada lado."""
    from emit.plataforma import Arco as ArcoPerfil

    if t.tipo != "ranura":
        return [(t.cx, t.cy)]
    centros = [
        e.centro
        for e in perfil
        if isinstance(e, ArcoPerfil)
        and abs(e.radio - t.diametro / 2) < 0.011
        and abs(math.dist(e.centro, (t.cx, t.cy)) - t.recorrido / 2) < 0.02
    ]
    return centros or [(t.cx, t.cy)]


def _centros_de_arcos(
    cv: Any,
    lienzo: Any,
    perfil: Any,
    rasgo: Rasgos,
    ficha: Ficha,
    c: dict[str, float],
    ref: Any,
    encima: float,
    derecha: float,
) -> list[Any]:
    """Cotas desde el datum a cada centro de arco del contorno que no está en
    el datum ni es el de un taladro de su mismo radio."""
    from emit.dibujable import Cota
    from emit.plataforma import Arco as ArcoPerfil

    situados = [(t.cx, t.cy, t.diametro / 2) for t in rasgo.taladros if t.tipo != "ranura"]
    vistos: list[tuple[float, float]] = []
    salida = []
    renglon = 0
    for e in perfil:
        if not isinstance(e, ArcoPerfil):
            continue
        cx, cy = e.centro
        if math.hypot(cx, cy) < 0.02 or any(math.dist((cx, cy), v) < 0.02 for v in vistos):
            continue
        if any(
            math.dist((cx, cy), (tx, ty)) < 0.02 and abs(tr - e.radio) < 0.011
            for tx, ty, tr in situados
        ):
            continue
        if any(t.tipo == "ranura" for t in rasgo.taladros) and any(
            (cx, cy) in _centros_del_taladro(perfil, t) for t in rasgo.taladros
        ):
            continue
        vistos.append((cx, cy))
        distancia = math.hypot(cx, cy)
        var = variable_de(distancia, ficha, c, "distancia")
        texto = _rotulo(_numero(distancia), var, ficha)
        if abs(cy) < 0.02:
            _cota(
                cv,
                lienzo.p(0.0, 0.0),
                lienzo.p(cx, 0.0),
                (0, (encima + 6.0 * renglon) * MM),
                texto,
                ref(var),
            )
        else:
            _cota(
                cv,
                lienzo.p(0.0, 0.0),
                lienzo.p(cx, cy),
                (0, (encima + 6.0 * renglon) * MM),
                texto,
                ref(var),
            )
        renglon += 1
        salida.append(Cota("centro", texto, var, not var, distancia, en=(cx, cy)))
    return salida


def _cara_plana(
    cv: Any,
    lienzo: Any,
    perfil: Any,
    cara: Any,
    ficha: Ficha,
    c: dict[str, float],
    ref: Any,
    x1: float,
    y1: float,
) -> list[Any]:
    """Los tres datos de una cara plana: distancia al eje, cuerda y lado. Una
    cuerda sola no la sitúa: a 4 del centro cae a +4 o a -4, y con la cara al
    otro lado el brazo se monta media vuelta girado."""
    from reportlab.lib.colors import HexColor

    from emit.dibujable import Cota

    salida = []
    ox, oy = cara.centro
    ux, uy = math.cos(cara.angulo), math.sin(cara.angulo)
    pie = (ox + cara.distancia * ux, oy + cara.distancia * uy)
    var = variable_de(cara.distancia, ficha, c, "distancia", preferir="chaveta")
    texto = _rotulo(_numero(cara.distancia), var, ficha)
    # La distancia, por encima de la vista: del centro a la cara.
    alto = (y1 - oy) * lienzo.escala + 4.0
    _cota(cv, lienzo.p(ox, oy), lienzo.p(*pie), (-uy * alto * MM, ux * alto * MM), texto, ref(var))
    salida.append(
        Cota("cara_distancia", texto, var, not var, cara.distancia, segmento=cara.segmento)
    )
    # La cuerda, por fuera de la cara.
    seg = perfil[cara.segmento]
    var = variable_de(cara.cuerda, ficha, c, "distancia", preferir="cuerda")
    texto = _rotulo(_numero(cara.cuerda), var, ficha)
    fuera = (x1 - pie[0]) * lienzo.escala + 6.0
    _cota(
        cv, lienzo.p(*seg.a), lienzo.p(*seg.b), (ux * fuera * MM, uy * fuera * MM), texto, ref(var)
    )
    salida.append(Cota("cara_cuerda", texto, var, not var, cara.cuerda, segmento=cara.segmento))
    # El lado: sobre +X se dice; girada, con su cota angular.
    if abs(cara.angulo) < 1e-6:
        texto = "cara plana: normal sobre +X"
        px, py = lienzo.p(ox, oy)
        cv.setFillColor(HexColor(COTA))
        cv.setFont(estilo.FUENTE, estilo.CUERPO_TABLA)
        cv.drawString(px, py + (alto + 4.0) * MM, texto)
        salida.append(Cota("cara_lado", texto, segmento=cara.segmento))
    else:
        texto = acotado.grados(cara.angulo)
        var = ""
        for v, x in _variables(ficha, c):
            if v.mapa == "angulo" and abs(abs(x) - abs(math.degrees(cara.angulo))) < 0.011:
                var = v.nombre
        cx_, cy_ = lienzo.p(ox, oy)
        acotado.a_pdf(
            cv,
            acotado.angular(
                (cx_ / MM, cy_ / MM),
                0.0,
                cara.angulo,
                cara.radio * lienzo.escala + 5.0,
                texto,
                ref(var),
            ),
        )
        salida.append(Cota("cara_lado", texto, var, not var, segmento=cara.segmento))
    return salida


def _longitud_de_tramo(
    cv: Any, lienzo: Any, perfil: Any, i: int, ficha: Ficha, c: dict[str, float], ref: Any
) -> Any:
    """La longitud de un tramo libre, junto a él, por el lado de fuera."""
    from emit.dibujable import Cota

    a, b = perfil[i].a, perfil[i].b
    largo = math.dist(a, b)
    var = variable_de(largo, ficha, c, "distancia")
    texto = _rotulo(_numero(largo), var, ficha)
    dx, dy = b[0] - a[0], b[1] - a[1]
    n = math.hypot(dx, dy) or 1.0
    normal = (dy / n, -dx / n)
    medio = ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2)
    if normal[0] * medio[0] + normal[1] * medio[1] < 0:
        normal = (-normal[0], -normal[1])
    _cota(cv, lienzo.p(*a), lienzo.p(*b), (normal[0] * 5 * MM, normal[1] * 5 * MM), texto, ref(var))
    return Cota("longitud", texto, var, not var, largo, segmento=i)


def _ficha_de_pieza(
    cv: Any, pieza: Pieza, grupo: Grupo, c: dict[str, float], hoja: str, version: str
) -> None:
    from reportlab.lib.colors import HexColor

    from emit.dibujable import Acotacion, Cota, construccion, perfil_de

    ficha = LISTADO[pieza.nombre]
    rasgo = rasgos(pieza.solido)
    perfil = perfil_de(pieza.nombre, c)
    obra = construccion(perfil)
    acot = Acotacion(pieza.nombre)
    pieza.acotacion = acot
    cortado = cortar(pieza.solido)
    hay_seccion = cortado.volume > 1e-6

    def proyectar_todo(escala: float) -> dict[str, VistaPieza]:
        vistas = {n: vista_de_pieza(pieza.solido, n, escala) for n in VISTAS_PIEZA}
        if hay_seccion:
            # La sección se mira como el alzado, pero de la pieza cortada.
            seccion = vista_de_pieza(cortado, "alzado", escala)
            vistas["perfil izquierdo"] = seccion
        return vistas

    vistas = proyectar_todo(1.0)
    escala = escala_comun(vistas)
    # Otra vez, con los arcos partidos para la escala a la que se dibujan.
    vistas = proyectar_todo(escala * 2.5)
    pieza.vistas = vistas
    _marco(cv)

    # La referencia de cada cota: la fila de su variable en la tabla. El
    # nombre largo a 4,6 pt no se leía impreso y cruzaba las líneas de cota.
    filas_de = {v.nombre: str(i) for i, (v, _) in enumerate(_variables(ficha, c), start=1)}

    def ref(variable: str) -> str:
        if variable.startswith("ambigua"):
            return "?"
        return filas_de.get(variable, "")

    rotulos = {
        "alzado": "alzado",
        "perfil izquierdo": (
            (
                "sección A-A, por el eje"
                if ficha.solido[0] == "barra"
                else "sección A-A, por el datum"
            )
            if hay_seccion
            else "perfil izquierdo"
        ),
        "planta": "planta",
        "isométrica": "isométrica (sin escala)",
    }
    for nombre, (x, y, w, h) in CELDAS.items():
        v = vistas[nombre]
        x0, y0, x1, y1 = v.caja()
        e = min((w - 10) / (x1 - x0), (h - 14) / (y1 - y0)) if nombre == "isométrica" else escala
        ox = x + w / 2 - (x0 + x1) / 2 * e
        oy = y + h / 2 - (y0 + y1) / 2 * e
        if nombre == "planta":
            # Sitio debajo y a la izquierda para las cotas por coordenadas.
            ox += 3.0
            oy += 3.0
        lienzo = _Lienzo(cv, e, ox, oy)
        if nombre == "perfil izquierdo" and hay_seccion:
            for poligono in caras_cortadas(cortado):
                _rayado(lienzo, poligono)
        for p in v.ocultas:
            lienzo.polilinea(p, estilo.OCULTA, GRIS, True)
        for p in v.visibles:
            lienzo.polilinea(p, estilo.VISIBLE, TINTA, False)
        cv.setFillColor(HexColor("#41464d"))
        cv.setFont("Helvetica-Bold", 7)
        cv.drawString((x + 2) * MM, (y + h - 4) * MM, _texto(rotulos[nombre].upper()))
        if nombre in ("isométrica", "perfil izquierdo") and (nombre == "isométrica" or hay_seccion):
            continue

        # Cotas de conjunto: ancho debajo y alto a la izquierda.
        ancho, alto = x1 - x0, y1 - y0
        clase_ancho = _clase_de_extension(ancho, rasgo.contorno)
        clase_alto = (
            _clase_de_extension(alto, rasgo.contorno) if nombre == "planta" else "distancia"
        )
        var = variable_de(ancho, ficha, c, clase_ancho)
        texto = _rotulo(_numero(ancho), var, ficha)
        _cota(cv, lienzo.p(x0, y0), lienzo.p(x1, y0), (0, -6 * MM), texto, ref(var))
        acot.cotas.append(Cota("conjunto", texto, var, not var, ancho))
        if nombre == "planta":
            acot.cotas += _longitudes(perfil, obra.rectos, ancho, 0, texto, var)
        if alto > 0.05:
            var = variable_de(alto, ficha, c, clase_alto)
            # En alzado, la vertical es la dirección de extrusión, y su
            # variable la dice la ficha sin adivinar: el tambor mide 6 de
            # ancho y 6 de cuerda de chaveta, y por valor sería ambigua.
            extrusion = ficha.solido[1]
            if nombre == "alzado" and extrusion in c and abs(c[extrusion] - alto) < 0.011:
                var = extrusion
            texto = _rotulo(_numero(alto), var, ficha)
            _cota(cv, lienzo.p(x0, y0), lienzo.p(x0, y1), (-6 * MM, 0), texto, ref(var))
            acot.cotas.append(Cota("conjunto", texto, var, not var, alto))
            if nombre == "planta":
                acot.cotas += _longitudes(perfil, obra.rectos, alto, 1, texto, var)

        if nombre != "planta":
            continue
        # El datum: el origen de la pieza, donde la ficha empieza a medir.
        dx, dy = lienzo.p(0.0, 0.0)
        cv.setStrokeColor(HexColor(COTA))
        cv.setLineWidth(0.2 * MM)
        cv.line(dx - 3 * MM, dy, dx + 3 * MM, dy)
        cv.line(dx, dy - 3 * MM, dx, dy + 3 * MM)

        # El plano de corte de la sección A-A, por el datum.
        if hay_seccion:
            ax0, ay = lienzo.p(x0 - 3.0 / e, 0.0)
            ax1, _ = lienzo.p(x1 + 3.0 / e, 0.0)
            cv.setStrokeColor(HexColor(TINTA))
            cv.setLineWidth(0.18 * MM)
            cv.setDash([3 * MM, 0.8 * MM, 0.5 * MM, 0.8 * MM])
            cv.line(ax0, ay, ax1, ay)
            cv.setDash([])
            cv.setFillColor(HexColor(TINTA))
            for ax in (ax0, ax1):
                cv.setLineWidth(0.5 * MM)
                cv.line(ax, ay, ax, ay + 2.5 * MM)
                _flecha(cv, ax, ay + 4.5 * MM, 0, 1)
                cv.setFont("Helvetica-Bold", 7)
                cv.drawCentredString(ax + 2.2 * MM, ay + 3.0 * MM, "A")

        # El contorno: Ø o R en la vista, una vez por radio.
        angulos = iter((35.0, 145.0, 215.0, 325.0, 60.0, 120.0, 240.0, 300.0) * 4)
        vistos: set[float] = set()
        for arco in sorted(rasgo.contorno, key=lambda a: -a.r):
            if round(arco.r, 2) in vistos:
                continue
            vistos.add(round(arco.r, 2))
            iguales = sum(1 for a in rasgo.contorno if abs(a.r - arco.r) < 0.011)
            veces = f"{iguales}× " if iguales > 1 else ""
            como_radio = variable_de(arco.r, ficha, c, "radio")
            radio_declarado = any(v.nombre == como_radio and es_radio(v) for v in ficha.variables)
            if arco.entero and not radio_declarado:
                var = variable_de(2 * arco.r, ficha, c, "diametro")
                rotulo = veces + _rotulo(f"Ø{_numero(2 * arco.r)}", var, ficha)
                acot.cotas.append(Cota("diametro", rotulo, var, not var, 2 * arco.r))
            else:
                var = variable_de(arco.r, ficha, c, "radio")
                rotulo = veces + _rotulo(f"R{_numero(arco.r)}", var, ficha)
                acot.cotas.append(Cota("radio", rotulo, var, not var, arco.r))
            _rotulo_circulo(lienzo, arco.cx, arco.cy, arco.r, rotulo, ref(var), next(angulos))

        # Los radios del perfil que no están en la cara de arriba —la valona
        # del eje del cartucho está más abajo—, rotulados igual.
        from emit.plataforma import Arco as ArcoPerfil

        hechos = [k.valor for k in acot.cotas if k.clase == "radio"]
        hechos += [k.valor / 2 for k in acot.cotas if k.clase == "diametro"]
        hechos += [t.diametro / 2 for t in rasgo.taladros]
        for arco_p in perfil:
            if not isinstance(arco_p, ArcoPerfil):
                continue
            if any(abs(arco_p.radio - r) < 0.011 for r in hechos):
                continue
            hechos.append(arco_p.radio)
            entero = abs(arco_p.hasta - arco_p.desde) > math.pi
            if entero:
                var = variable_de(2 * arco_p.radio, ficha, c, "diametro")
                rotulo = _rotulo(f"Ø{_numero(2 * arco_p.radio)}", var, ficha)
                acot.cotas.append(Cota("diametro", rotulo, var, not var, 2 * arco_p.radio))
            else:
                var = variable_de(arco_p.radio, ficha, c, "radio")
                rotulo = _rotulo(f"R{_numero(arco_p.radio)}", var, ficha)
                acot.cotas.append(Cota("radio", rotulo, var, not var, arco_p.radio))
            _rotulo_circulo(lienzo, *arco_p.centro, arco_p.radio, rotulo, ref(var), next(angulos))

        # Cada centro de arco que no es el datum ni el de un taladro, con su
        # propia cota desde el datum —aunque coincida en número con otra cosa:
        # el centro del R4,5 del calzo cae a 38, como su tornillo, y se situaba
        # solo por coincidencia—. Encima de la vista, una por renglón.
        # Un renglón más arriba si hay cara plana: su cota y su lado van debajo.
        encima = (y1 - 0.0) * e + 6.0 + (6.0 if obra.caras_planas else 0.0)
        acot.cotas += _centros_de_arcos(
            cv, lienzo, perfil, rasgo, ficha, c, ref, encima, x1 * e + 8.0
        )

        # Las caras planas: distancia al eje, cuerda y lado.
        for cara in obra.caras_planas:
            acot.cotas += _cara_plana(cv, lienzo, perfil, cara, ficha, c, ref, x1, y1)

        # Los tramos libres: su longitud, junto a cada uno.
        cubiertos = {k.segmento for k in acot.cotas if k.clase == "longitud"}
        for i in obra.rectos:
            if i in cubiertos:
                continue
            acot.cotas.append(_longitud_de_tramo(cv, lienzo, perfil, i, ficha, c, ref))
        for i in obra.tangentes:
            acot.cotas.append(Cota("tangente", TEXTO_TANGENTE, segmento=i))

        # Los taladros: cada uno con su letra en la vista —si está en la
        # tabla, está en el dibujo—, fuera de su centro para no pisar el datum.
        for t in rasgo.taladros:
            r = max(t.diametro / 2, 0.5)
            angulo = math.radians(135.0 if abs(t.cx) < 1e-6 and abs(t.cy) < 1e-6 else 45.0)
            bx, by = lienzo.p(t.cx + r * math.cos(angulo), t.cy + r * math.sin(angulo))
            gx, gy = bx + 4.2 * MM * math.cos(angulo), by + 4.2 * MM * math.sin(angulo)
            cv.setStrokeColor(HexColor(COTA))
            cv.setLineWidth(0.15 * MM)
            cv.line(bx, by, gx - 1.9 * MM * math.cos(angulo), gy - 1.9 * MM * math.sin(angulo))
            _globo(cv, gx, gy, t.letra)

        # Y sus posiciones, acotadas por coordenadas desde el datum.
        abajo = lienzo.p(0.0, y0)[1] - 13 * MM
        izquierda = lienzo.p(x0, 0.0)[0] - 13 * MM
        cv.setFont("Helvetica", 5.6)
        xs = sorted({round(t.cx, 2) for t in rasgo.taladros} | {0.0})
        ys = sorted({round(t.cy, 2) for t in rasgo.taladros} | {0.0})
        for xv in xs:
            px, _ = lienzo.p(xv, 0.0)
            cv.setStrokeColor(HexColor(GRIS))
            cv.setLineWidth(0.1 * MM)
            cv.line(px, abajo + 1.0 * MM, px, lienzo.p(0.0, y0)[1] - 1.0 * MM)
            cv.saveState()
            cv.translate(px + 0.7 * MM, abajo - 0.6 * MM)
            cv.rotate(90)
            cv.setFillColor(HexColor(COTA))
            cv.drawRightString(0, 0, _numero(xv))
            cv.restoreState()
        for yv in ys:
            _, py = lienzo.p(0.0, yv)
            cv.setStrokeColor(HexColor(GRIS))
            cv.setLineWidth(0.1 * MM)
            cv.line(izquierda + 1.0 * MM, py, lienzo.p(x0, 0.0)[0] - 1.0 * MM, py)
            cv.setFillColor(HexColor(COTA))
            cv.drawRightString(izquierda + 0.4 * MM, py - 0.7 * MM, _numero(yv))

    # --- la columna de la derecha -------------------------------------------
    x, y = 187.0, ALTO - MARGEN - 6
    cv.setFillColor(HexColor(grupo.color))
    cv.rect(x * MM, (y - 1) * MM, 3 * MM, 6 * MM, stroke=0, fill=1)
    cv.setFillColor(HexColor(TINTA))
    cv.setFont("Helvetica-Bold", 12)
    cv.drawString((x + 5) * MM, y * MM, _texto(f"{pieza.marca} · {pieza.nombre}"))
    y -= 5
    y = _parrafo(cv, ficha.forma, x, y, 100, 7)
    y -= 1
    datos = [
        ("Cantidad", f"{ficha.cantidad} en la máquina, {pieza.cantidad_en_el_grupo} en el grupo"),
        ("Material", ficha.material or "—"),
        ("Proceso", ficha.proceso or "—"),
        ("Se extruye", f"{ficha.solido[0]}, a lo largo de #cota.{ficha.solido[1]}"),
    ]
    y = _tabla(cv, x, y, (18, 84), [("Dato", ""), *datos])

    filas = [("Ref.", "Variable (#mapa.nombre)", "Qué es", "Valor", "")]
    for fila, (v, x_v) in enumerate(_variables(ficha, c), start=1):
        unidad = "°" if v.mapa == "angulo" else ""
        filas.append(
            (
                str(fila),
                f"#{v.mapa}.{v.nombre}",
                v.etiqueta + ("" if v.en_el_perfil else " (se teclea)"),
                _numero(x_v) + unidad,
                v.sufijo,
            )
        )
    y = _tabla(cv, x, y, (6, 47, 29, 11, 9), filas, cuerpo=estilo.CUERPO_TABLA)

    if rasgo.taladros:
        filas = [("Taladro", "Tipo", "X", "Y", "Ø", "Ø de", "Al datum", "Posición de")]
        for t in rasgo.taladros:
            distancia = math.hypot(t.cx, t.cy)
            var_d = variable_de(t.diametro, ficha, c, "diametro")
            var_p = variable_de(distancia, ficha, c, "distancia") if distancia > 0.01 else ""
            acot.cotas.append(Cota("diametro", _numero(t.diametro), var_d, not var_d, t.diametro))
            for cx_, cy_ in _centros_del_taladro(perfil, t):
                acot.cotas.append(Cota("centro", _numero(t.cx), var_p, not var_p, en=(cx_, cy_)))
            filas.append(
                (
                    t.letra,
                    t.tipo,
                    _numero(t.cx),
                    _numero(t.cy),
                    _numero(t.diametro),
                    variable_de(t.diametro, ficha, c, "diametro"),
                    _numero(distancia),
                    variable_de(distancia, ficha, c, "distancia") if distancia > 0.01 else "datum",
                )
            )
        y = _tabla(cv, x, y, (9, 10, 8, 8, 6, 26, 9, 26), filas, cuerpo=5.0)

    cv.setFont("Helvetica-Bold", 6.5)
    cv.setFillColor(HexColor(TINTA))
    cv.drawString(x * MM, y * MM, "Construcción")
    if obra.tangentes:
        y = _parrafo(cv, TEXTO_TANGENTE, x, y - 3, 100, 5.6)
    else:
        y -= 3
    y = _parrafo(cv, _texto_extrusion(ficha), x, y, 100, 5.6) - 1
    cv.setFont("Helvetica-Bold", 6.5)
    if ficha.porque and y > CAJETIN[1] + CAJETIN[3] + 14:
        cv.drawString(x * MM, y * MM, "Por qué es así")
        y = _parrafo(cv, ficha.porque, x, y - 3, 100, 5.6) - 1
    if ficha.montaje and y > CAJETIN[1] + CAJETIN[3] + 14:
        cv.setFont("Helvetica-Bold", 6.5)
        cv.drawString(x * MM, y * MM, "Montaje")
        _parrafo(cv, ficha.montaje, x, y - 3, 100, 5.6)

    _cajetin(
        cv,
        f"Pieza {pieza.marca}: {pieza.nombre}",
        pieza.plano,
        hoja,
        _rotulo_escala(escala),
        grupo,
        version,
    )


# ---------------------------------------------------------------------------
# La ficha de grupo
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Comercial:
    codigo: str
    """C-AMP-01 o T-AMP-03: su marca del registro."""
    designacion: str
    cantidad: int
    para: str


@dataclass(frozen=True)
class FichasDeGrupo:
    """Todo lo que hace falta para las fichas de un grupo."""

    grupo: Grupo
    piezas: tuple[Pieza, ...]
    comerciales: tuple[Comercial, ...]
    sin_ficha: tuple[str, ...]
    """Lo que el grupo lleva colocado en el 3D y no tiene ficha: una laguna."""
    contexto: tuple[tuple[str, Any], ...]
    """Toda la máquina colocada, para la isométrica de situación."""
    despiece: tuple[tuple[int, str, Any], ...]
    """(marca, nombre, sólido ya explosionado) de un canal del grupo."""
    contrato: dict[str, float]
    """El contrato en mm con que se dibujan las fichas."""


def _vista_en(
    cv: Any, vista: Any, x: float, y: float, w: float, h: float
) -> tuple[float, float, float]:
    """Dibuja una vista del dossier encajada en un rectángulo; devuelve la
    transformación (escala, ox, oy) para poner encima globos o rótulos."""
    from reportlab.lib.colors import HexColor

    x0, y0, x1, y1 = vista.caja()
    e = min(w / (x1 - x0), h / (y1 - y0))
    ox = x + w / 2 - (x0 + x1) / 2 * e
    oy = y + h / 2 - (y0 + y1) / 2 * e
    for color, grosor, puntos in vista.lineas:
        cv.setStrokeColor(HexColor(color))
        cv.setLineWidth(grosor * 0.6 * MM)
        camino = cv.beginPath()
        camino.moveTo((ox + puntos[0][0] * e) * MM, (oy + puntos[0][1] * e) * MM)
        for px, py in puntos[1:]:
            camino.lineTo((ox + px * e) * MM, (oy + py * e) * MM)
        cv.drawPath(camino, stroke=1, fill=0)
    return e, ox, oy


DESPIECE = (MARGEN + 96.0, 100.0, 80.0, 78.0)
"""x, y, ancho, alto en mm de la hoja: dónde va el despiece, globos incluidos."""

RADIO_GLOBO = 3.0


def despiece_en_hoja(g: FichasDeGrupo) -> Any:
    """El despiece de la hoja de grupo, ya en mm de la hoja: lo que se dibuja,
    la caja de cada pieza y los globos (`emit.explosion.Esquema`). Lo dibuja
    `_ficha_de_grupo` y lo mide el test: los globos ni se pisan ni tapan
    ninguna pieza."""
    from emit.explosion import VISTA_ISOMETRICA, Esquema, ancla_de, caja_de, colocar_globos

    origen, arriba, mira = VISTA_ISOMETRICA
    propias = []
    for marca, nombre, solido in g.despiece:
        visibles, _ = solido.project_to_viewport(origen, arriba, mira)
        propias.append((marca, nombre, [_polilinea(a) for a in visibles]))
    x0, y0, x1, y1 = caja_de([q for _, _, polis in propias for q in polis])
    # Sitio para una columna de globos a cada lado.
    x, y, w, h = DESPIECE
    hueco = 3.4 * RADIO_GLOBO
    e = min((w - 2 * hueco) / (x1 - x0), h / (y1 - y0))
    ox = x + w / 2 - (x0 + x1) / 2 * e
    oy = y + h / 2 - (y0 + y1) / 2 * e

    esquema = Esquema()
    anclas: dict[str, tuple[float, float]] = {}
    for marca, nombre, polis in propias:
        en_hoja = [[(ox + px * e, oy + py * e) for px, py in q] for q in polis]
        esquema.lineas += [(g.grupo.color, 0.45, q) for q in en_hoja]
        esquema.cajas[nombre] = caja_de(en_hoja)
        anclas.setdefault(str(marca), ancla_de(en_hoja))
    todo = caja_de([q for _, _, q in esquema.lineas])
    esquema.globos = colocar_globos(list(anclas.items()), todo[0], todo[2], RADIO_GLOBO)
    return esquema


def _ficha_de_grupo(cv: Any, g: FichasDeGrupo, hoja: str, version: str) -> None:
    from reportlab.lib.colors import HexColor

    _marco(cv)
    cv.setFillColor(HexColor(g.grupo.color))
    cv.rect((MARGEN + 4) * MM, (ALTO - MARGEN - 13) * MM, 4 * MM, 9 * MM, stroke=0, fill=1)
    cv.setFillColor(HexColor(TINTA))
    cv.setFont("Helvetica-Bold", 15)
    cv.drawString((MARGEN + 11) * MM, (ALTO - MARGEN - 9) * MM, _texto(f"Grupo · {g.grupo.nombre}"))
    cv.setFont("Helvetica", 8)
    cv.drawString((MARGEN + 11) * MM, (ALTO - MARGEN - 13) * MM, _texto(g.grupo.objetivo))

    # Dónde va: la máquina entera, con el grupo resaltado.
    situacion = proyectar(list(g.contexto), "isométrica", resaltar=g.grupo.nombre)
    cv.setFont("Helvetica-Bold", 7)
    cv.setFillColor(HexColor("#41464d"))
    cv.drawString((MARGEN + 4) * MM, 182 * MM, "SITUACIÓN EN LA MÁQUINA")
    _vista_en(cv, situacion, MARGEN + 4, 100, 84, 80)

    # El despiece: el grupo entero, explosionado, con un globo por marca.
    cv.setFont("Helvetica-Bold", 7)
    cv.setFillColor(HexColor("#41464d"))
    cv.drawString((MARGEN + 94) * MM, 182 * MM, "DESPIECE (el grupo entero, explosionado)")
    esquema = despiece_en_hoja(g)
    cv.setStrokeColor(HexColor(g.grupo.color))
    for _color, grosor, puntos in esquema.lineas:
        cv.setLineWidth(grosor * 0.6 * MM)
        camino = cv.beginPath()
        camino.moveTo(puntos[0][0] * MM, puntos[0][1] * MM)
        for px, py in puntos[1:]:
            camino.lineTo(px * MM, py * MM)
        cv.drawPath(camino, stroke=1, fill=0)
    cv.setLineWidth(0.2 * MM)
    for globo in esquema.globos:
        (px, py), (bx, by) = globo.ancla, globo.centro
        lado = 1 if px > bx else -1
        cv.setStrokeColor(HexColor(TINTA))
        cv.line(px * MM, py * MM, (bx + lado * globo.radio) * MM, by * MM)
        cv.setFillColor(HexColor("#41464d"))
        cv.circle(px * MM, py * MM, 0.6 * MM, stroke=0, fill=1)
        cv.setFillColor(HexColor("#ffffff"))
        cv.circle(bx * MM, by * MM, globo.radio * MM, stroke=1, fill=1)
        cv.setFillColor(HexColor(TINTA))
        cv.setFont("Helvetica-Bold", 7)
        cv.drawCentredString(bx * MM, (by - 1.0) * MM, globo.clave)

    # La lista de piezas.
    filas = [("Marca", "Pieza", "Cant.", "Material", "Proceso", "Plano")]
    for p in g.piezas:
        f = LISTADO[p.nombre]
        filas.append(
            (str(p.marca), p.nombre, str(p.cantidad_en_el_grupo), f.material, f.proceso, p.plano)
        )
    y = _tabla(cv, MARGEN + 4, 95, (11, 26, 10, 46, 60, 22), filas, cuerpo=6.4)
    filas = [("Marca", "Comercial y tornillería", "Cant.", "Para")]
    filas += [(k.codigo, k.designacion, str(k.cantidad), k.para) for k in g.comerciales]
    y = _tabla(cv, MARGEN + 4, y - 1, (16, 52, 10, 97), filas, cuerpo=6.4)
    if g.sin_ficha:
        cv.setFillColor(HexColor(COTA))
        cv.setFont("Helvetica-Bold", 6.6)
        cv.drawString(
            (MARGEN + 4) * MM,
            (y - 1) * MM,
            _texto("Sin ficha (laguna del modelo): " + ", ".join(g.sin_ficha)),
        )

    # La secuencia de montaje del grupo, en la columna de la derecha.
    x, y = 187.0, ALTO - MARGEN - 22
    cv.setFillColor(HexColor(TINTA))
    cv.setFont("Helvetica-Bold", 8)
    cv.drawString(x * MM, y * MM, "SECUENCIA DE MONTAJE")
    y -= 4.5
    for paso, p in enumerate(g.piezas, start=1):
        f = LISTADO[p.nombre]
        if not f.montaje or y < CAJETIN[1] + CAJETIN[3] + 8:
            continue
        cv.setFont("Helvetica-Bold", 6.4)
        cv.drawString(x * MM, y * MM, _texto(f"{paso}. {p.nombre} (marca {p.marca})"))
        y = _parrafo(cv, f.montaje, x + 3, y - 3, 97, 5.5) - 1.2

    _cajetin(
        cv,
        f"Grupo: {g.grupo.nombre}",
        f"G-{g.grupo.sigla}",
        hoja,
        estilo.ESCALA_VARIAS,
        g.grupo,
        version,
    )


def hojas_de(g: FichasDeGrupo) -> dict[str, int]:
    """Pieza → hoja en que `escribir_fichas` pone su ficha. La hoja 1 es la
    del grupo. El índice del dossier lo saca del registro
    (`emit.numeracion.paginas`) y un test lo cruza con esto."""
    return {p.nombre: i for i, p in enumerate(g.piezas, start=2)}


def escribir_fichas(
    g: FichasDeGrupo, destino: Path | str, version: str, comprimir: bool = True
) -> Path:
    """El PDF con la ficha de grupo y una ficha por pieza fabricada.

    `version` va al cajetín de cada hoja (el commit). `comprimir=False` deja
    el texto legible en el PDF, que es como los tests leen lo que de verdad
    se ha dibujado."""
    from reportlab import rl_config

    rl_config.invariant = 1
    from reportlab.pdfgen import canvas

    destino = Path(destino)
    destino.parent.mkdir(parents=True, exist_ok=True)
    cv = canvas.Canvas(
        str(destino), pagesize=(ANCHO * MM, ALTO * MM), pageCompression=int(comprimir)
    )
    cv.setTitle(_texto(f"Fichas del grupo {g.grupo.nombre}"))
    cv.setAuthor("claude.automatas")
    total = 1 + len(g.piezas)
    _ficha_de_grupo(cv, g, f"1/{total}", version)
    cv.showPage()
    hojas = hojas_de(g)
    for p in g.piezas:
        _ficha_de_pieza(cv, p, g.grupo, g.contrato, f"{hojas[p.nombre]}/{total}", version)
        cv.showPage()
    cv.save()
    return destino


def grupo(nombre: str) -> Grupo:
    return next(g for g in GRUPOS if g.nombre == nombre)


def base_de(colocada: str) -> str:
    """La clave del `LISTADO` de una pieza colocada: `sector_1` es `sector`, y
    los brazos del cinco barras se colocan sin su «brazo_»: `proximal_1` es
    `brazo_proximal`."""
    for clave in sorted(LISTADO, key=len, reverse=True):
        for nombre in (clave, clave.removeprefix("brazo_")):
            if colocada == nombre or colocada.startswith(nombre + "_"):
                return clave
    return ""


__all__ = [
    "Comercial",
    "FichasDeGrupo",
    "Pieza",
    "VistaPieza",
    "base_de",
    "escala_comun",
    "escribir_fichas",
    "grupo",
    "grupo_de",
    "hojas_de",
    "variable_de",
    "vista_de_pieza",
]
