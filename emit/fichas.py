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

**Cada cota dice de qué variable sale.** Debajo del número va `#cota.nombre`
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
CAJETIN = (187.0, MARGEN, ANCHO - MARGEN - 187.0, 34.0)
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

TINTA = "#1b1b1b"
COTA = "#b03030"
GRIS = "#8a8f96"

Polilinea = list[tuple[float, float]]


# ---------------------------------------------------------------------------
# Texto
# ---------------------------------------------------------------------------


def _texto(t: str) -> str:
    """Lo que Helvetica sabe escribir: las fuentes estándar del PDF van en
    Windows-1252, y lo que no está ahí sale como un cuadrado."""
    sustituir = {chr(0x2212): "-", chr(0x2192): "->", chr(0x2248): "~", chr(0x03B8): "theta"}
    t = "".join(sustituir.get(ch, ch) for ch in t)
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
    largo, ancho = 2.2 * MM, 0.7 * MM
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
    variable: str,
) -> None:
    """Cota lineal entre dos puntos de la hoja (en puntos), desplazada
    `separacion` (en puntos) con sus líneas auxiliares."""
    from reportlab.lib.colors import HexColor

    sx, sy = separacion
    a2, b2 = (a[0] + sx, a[1] + sy), (b[0] + sx, b[1] + sy)
    cv.setStrokeColor(HexColor(COTA))
    cv.setFillColor(HexColor(COTA))
    cv.setLineWidth(0.18 * MM)
    n = math.hypot(sx, sy) or 1.0
    ext = 1.2 * MM
    cv.line(a[0], a[1], a2[0] + sx / n * ext, a2[1] + sy / n * ext)
    cv.line(b[0], b[1], b2[0] + sx / n * ext, b2[1] + sy / n * ext)
    cv.line(a2[0], a2[1], b2[0], b2[1])
    _flecha(cv, a2[0], a2[1], a2[0] - b2[0], a2[1] - b2[1])
    _flecha(cv, b2[0], b2[1], b2[0] - a2[0], b2[1] - a2[1])
    mx, my = (a2[0] + b2[0]) / 2, (a2[1] + b2[1]) / 2
    angulo = math.degrees(math.atan2(b2[1] - a2[1], b2[0] - a2[0]))
    if angulo > 90 or angulo <= -90:
        angulo -= 180
    cv.saveState()
    cv.translate(mx, my)
    cv.rotate(angulo)
    cv.setFont("Helvetica", 7)
    cv.drawCentredString(0, 0.8 * MM, _texto(texto))
    if variable:
        cv.setFont("Helvetica", 4.6)
        cv.setFillColor(HexColor(GRIS))
        cv.drawCentredString(0, -2.2 * MM, _texto(f"#cota.{variable}"))
    cv.restoreState()


def _rotulo_circulo(
    lienzo: _Lienzo, cx: float, cy: float, r: float, texto: str, variable: str, angulo: float
) -> None:
    """Línea de referencia desde el canto de un círculo hacia fuera, con su
    texto en el extremo."""
    from reportlab.lib.colors import HexColor

    cv = lienzo.cv
    ux, uy = math.cos(math.radians(angulo)), math.sin(math.radians(angulo))
    x0, y0 = lienzo.p(cx + r * ux, cy + r * uy)
    x1, y1 = x0 + ux * 7 * MM, y0 + uy * 7 * MM
    lado = 1 if ux >= 0 else -1
    x2 = x1 + lado * 3 * MM
    cv.setStrokeColor(HexColor(COTA))
    cv.setFillColor(HexColor(COTA))
    cv.setLineWidth(0.18 * MM)
    cv.line(x0, y0, x1, y1)
    cv.line(x1, y1, x2, y1)
    _flecha(cv, x0, y0, -ux, -uy)
    cv.setFont("Helvetica", 7)
    dibujar = cv.drawString if lado > 0 else cv.drawRightString
    dibujar(x2 + lado * 0.6 * MM, y1 - 0.8 * MM, _texto(texto))
    if variable:
        cv.setFont("Helvetica", 4.6)
        cv.setFillColor(HexColor(GRIS))
        dibujar(x2 + lado * 0.6 * MM, y1 - 3.2 * MM, _texto(f"#cota.{variable}"))


def _marco(cv: Any) -> None:
    from reportlab.lib.colors import HexColor

    cv.setStrokeColor(HexColor(TINTA))
    cv.setLineWidth(0.5 * MM)
    cv.rect(MARGEN * MM, MARGEN * MM, (ANCHO - 2 * MARGEN) * MM, (ALTO - 2 * MARGEN) * MM)


def _cajetin(cv: Any, titulo: str, plano: str, hoja: str, escala: str, grupo: Grupo) -> None:
    """El cajetín, abajo a la derecha: qué es, de qué máquina y a qué escala."""
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
    cv.setFont("Helvetica", 7)
    cv.drawString((x + 3) * MM, (y + 17) * MM, _texto("Escribiente · claude.automatas"))
    cv.drawString((x + 3) * MM, (y + 13.5) * MM, _texto(f"Grupo: {grupo.nombre}"))
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


def variable_de(medida: float, ficha: Ficha, c: dict[str, float], diametro: bool = False) -> str:
    """El nombre de la variable de la ficha que vale `medida`, si hay una.
    Un diámetro también casa con un radio del contrato, al doble."""
    for v, x in _variables(ficha, c):
        if v.mapa != "cota":
            continue
        if abs(x - medida) < 0.011:
            return v.nombre
        if diametro and "radio" in v.nombre and abs(2 * x - medida) < 0.011:
            return v.nombre
    return ""


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


def _ficha_de_pieza(cv: Any, pieza: Pieza, grupo: Grupo, c: dict[str, float], hoja: str) -> None:
    from reportlab.lib.colors import HexColor

    ficha = LISTADO[pieza.nombre]
    vistas = {n: vista_de_pieza(pieza.solido, n) for n in VISTAS_PIEZA}
    escala = escala_comun(vistas)
    # Otra vez, con los arcos partidos para la escala a la que se dibujan.
    vistas = {n: vista_de_pieza(pieza.solido, n, escala * 2.5) for n in VISTAS_PIEZA}
    pieza.vistas = vistas
    _marco(cv)

    taladros: list[tuple[str, float, float, float]] = []
    for nombre, (x, y, w, h) in CELDAS.items():
        v = vistas[nombre]
        x0, y0, x1, y1 = v.caja()
        e = min((w - 10) / (x1 - x0), (h - 14) / (y1 - y0)) if nombre == "isométrica" else escala
        ox = x + w / 2 - (x0 + x1) / 2 * e
        oy = y + h / 2 - (y0 + y1) / 2 * e
        lienzo = _Lienzo(cv, e, ox, oy)
        for p in v.ocultas:
            lienzo.polilinea(p, 0.13, GRIS, True)
        for p in v.visibles:
            lienzo.polilinea(p, 0.35, TINTA, False)
        cv.setFillColor(HexColor("#41464d"))
        cv.setFont("Helvetica-Bold", 7)
        rotulo = nombre if nombre != "isométrica" else "isométrica (sin escala)"
        cv.drawString((x + 2) * MM, (y + h - 4) * MM, _texto(rotulo.upper()))
        if nombre == "isométrica":
            continue

        # Cotas de conjunto: ancho debajo y alto a la izquierda.
        ancho, alto = x1 - x0, y1 - y0
        var = variable_de(ancho, ficha, c, diametro=True)
        _cota(
            cv,
            lienzo.p(x0, y0),
            lienzo.p(x1, y0),
            (0, -7 * MM),
            con_sufijo(_numero(ancho), var, ficha),
            var,
        )
        if alto > 0.05:
            var = variable_de(alto, ficha, c, diametro=True)
            _cota(
                cv,
                lienzo.p(x0, y0),
                lienzo.p(x0, y1),
                (-7 * MM, 0),
                con_sufijo(_numero(alto), var, ficha),
                var,
            )

        if nombre != "planta":
            continue
        # El datum: el origen de la pieza, donde la ficha empieza a medir.
        dx, dy = lienzo.p(0.0, 0.0)
        cv.setStrokeColor(HexColor(COTA))
        cv.setLineWidth(0.2 * MM)
        cv.line(dx - 3 * MM, dy, dx + 3 * MM, dy)
        cv.line(dx, dy - 3 * MM, dx, dy + 3 * MM)
        # Los círculos: el mayor centrado es el contorno; el resto, taladros.
        circulos = v.circulos
        exterior = max((ci for ci in circulos if ci[3]), key=lambda ci: ci[2], default=None)
        vistos_r: set[float] = set()
        angulos = iter((35.0, 145.0, 215.0, 325.0, 60.0, 120.0, 240.0, 300.0) * 4)
        for cx, cy, r, entero in circulos:
            if (cx, cy, r, entero) == exterior and abs(r - max(ancho, alto) / 2) < 0.6:
                var = variable_de(2 * r, ficha, c, True)
                _rotulo_circulo(
                    lienzo,
                    cx,
                    cy,
                    r,
                    con_sufijo(f"Ø{_numero(2 * r)}", var, ficha),
                    var,
                    next(angulos),
                )
                continue
            if entero:
                letra = chr(ord("A") + len(taladros))
                taladros.append((letra, cx, cy, 2 * r))
                px, py = lienzo.p(cx, cy)
                cv.setFillColor(HexColor(COTA))
                cv.setFont("Helvetica-Bold", 6)
                cv.drawCentredString(px + r * escala * MM * 0.0, py - 1.0 * MM, letra)
            elif round(r, 2) not in vistos_r:
                vistos_r.add(round(r, 2))
                _rotulo_circulo(
                    lienzo,
                    cx,
                    cy,
                    r,
                    f"R{_numero(r)}",
                    variable_de(r, ficha, c) or variable_de(2 * r, ficha, c, True),
                    next(angulos),
                )

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

    filas = [("Variable (#mapa.nombre)", "Qué es", "Valor", "")]
    for v, x_v in _variables(ficha, c):
        unidad = "°" if v.mapa == "angulo" else ""
        filas.append(
            (
                f"#{v.mapa}.{v.nombre}",
                v.etiqueta + ("" if v.en_el_perfil else " (se teclea)"),
                _numero(x_v) + unidad,
                v.sufijo,
            )
        )
    y = _tabla(cv, x, y, (50, 30, 12, 10), filas, cuerpo=5.4)

    if taladros:
        filas = [("Taladro", "X", "Y", "Ø", "Ø de", "Al datum", "Posición de")]
        for letra, tx, ty, d in taladros:
            distancia = math.hypot(tx, ty)
            filas.append(
                (
                    letra,
                    _numero(tx),
                    _numero(ty),
                    _numero(d),
                    variable_de(d, ficha, c, True),
                    _numero(distancia),
                    variable_de(distancia, ficha, c) if distancia > 0.01 else "datum",
                )
            )
        y = _tabla(cv, x, y, (9, 9, 9, 7, 30, 9, 29), filas, cuerpo=5.0)

    cv.setFont("Helvetica-Bold", 6.5)
    cv.setFillColor(HexColor(TINTA))
    if ficha.porque and y > CAJETIN[1] + CAJETIN[3] + 14:
        cv.drawString(x * MM, y * MM, "Por qué es así")
        y = _parrafo(cv, ficha.porque, x, y - 3, 100, 5.6) - 1
    if ficha.montaje and y > CAJETIN[1] + CAJETIN[3] + 14:
        cv.setFont("Helvetica-Bold", 6.5)
        cv.drawString(x * MM, y * MM, "Montaje")
        _parrafo(cv, ficha.montaje, x, y - 3, 100, 5.6)

    _cajetin(
        cv, f"Pieza {pieza.marca}: {pieza.nombre}", pieza.plano, hoja, _rotulo_escala(escala), grupo
    )


# ---------------------------------------------------------------------------
# La ficha de grupo
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Comercial:
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


def _ficha_de_grupo(cv: Any, g: FichasDeGrupo, hoja: str) -> None:
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

    # El despiece: un canal del grupo, explosionado, con un globo por marca.
    cv.setFont("Helvetica-Bold", 7)
    cv.setFillColor(HexColor("#41464d"))
    cv.drawString((MARGEN + 94) * MM, 182 * MM, "DESPIECE (un canal, explosionado)")
    from emit.dossier import Vista

    lineas = []
    anclas: list[tuple[int, Any]] = []
    origen, arriba = (600.0, -800.0, 600.0), (0.0, 0.0, 1.0)
    for marca, _nombre, solido in g.despiece:
        visibles, _ = solido.project_to_viewport(origen, arriba, (0, 0, 60))
        polis = [_polilinea(a) for a in visibles]
        lineas += [(g.grupo.color, 0.45, p) for p in polis]
        xs = [x for p in polis for x, _ in p]
        ys = [y for p in polis for _, y in p]
        anclas.append((marca, ((min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2)))
    izquierda, derecha = MARGEN + 96.0, MARGEN + 176.0
    e, ox, oy = _vista_en(
        cv, Vista(tuple(lineas)), izquierda + 10, 100, derecha - izquierda - 20, 78
    )
    # Los globos, en dos columnas a los lados del despiece y sin pisarse:
    # cada uno a la altura de su pieza, empujado hacia abajo si no cabe.
    primeras: dict[int, tuple[float, float]] = {}
    for marca, (ax, ay) in anclas:
        primeras.setdefault(marca, ((ox + ax * e), (oy + ay * e)))
    columnas: dict[bool, list[float]] = {True: [], False: []}
    cv.setLineWidth(0.2 * MM)
    for marca, (px, py) in sorted(primeras.items(), key=lambda m: -m[1][1]):
        a_la_izquierda = px < (izquierda + derecha) / 2
        ocupadas = columnas[a_la_izquierda]
        by = py
        while any(abs(by - o) < 8.0 for o in ocupadas):
            by -= 2.0
        ocupadas.append(by)
        bx = izquierda + 3 if a_la_izquierda else derecha - 3
        cv.setStrokeColor(HexColor(TINTA))
        cv.line(px * MM, py * MM, (bx + (3 if a_la_izquierda else -3)) * MM, by * MM)
        cv.setFillColor(HexColor("#41464d"))
        cv.circle(px * MM, py * MM, 0.6 * MM, stroke=0, fill=1)
        cv.setFillColor(HexColor("#ffffff"))
        cv.circle(bx * MM, by * MM, 3 * MM, stroke=1, fill=1)
        cv.setFillColor(HexColor(TINTA))
        cv.setFont("Helvetica-Bold", 7)
        cv.drawCentredString(bx * MM, (by - 1.0) * MM, str(marca))

    # La lista de piezas.
    filas = [("Marca", "Pieza", "Cant.", "Material", "Proceso", "Plano")]
    for p in g.piezas:
        f = LISTADO[p.nombre]
        filas.append(
            (str(p.marca), p.nombre, str(p.cantidad_en_el_grupo), f.material, f.proceso, p.plano)
        )
    y = _tabla(cv, MARGEN + 4, 95, (11, 26, 10, 46, 60, 22), filas, cuerpo=6.4)
    filas = [("Comercial", "Cant.", "Para")]
    filas += [(k.designacion, str(k.cantidad), k.para) for k in g.comerciales]
    y = _tabla(cv, MARGEN + 4, y - 1, (52, 10, 113), filas, cuerpo=6.4)
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

    _cajetin(cv, f"Grupo: {g.grupo.nombre}", f"G-{g.grupo.nombre[:3].upper()}", hoja, "-", g.grupo)


def escribir_fichas(g: FichasDeGrupo, destino: Path | str) -> Path:
    """El PDF con la ficha de grupo y una ficha por pieza fabricada."""
    from reportlab import rl_config

    rl_config.invariant = 1
    from reportlab.pdfgen import canvas

    destino = Path(destino)
    destino.parent.mkdir(parents=True, exist_ok=True)
    cv = canvas.Canvas(str(destino), pagesize=(ANCHO * MM, ALTO * MM), pageCompression=1)
    cv.setTitle(_texto(f"Fichas del grupo {g.grupo.nombre}"))
    cv.setAuthor("claude.automatas")
    total = 1 + len(g.piezas)
    _ficha_de_grupo(cv, g, f"1/{total}")
    cv.showPage()
    for i, p in enumerate(g.piezas, start=2):
        _ficha_de_pieza(cv, p, g.grupo, g.contrato, f"{i}/{total}")
        cv.showPage()
    cv.save()
    return destino


def grupo(nombre: str) -> Grupo:
    return next(g for g in GRUPOS if g.nombre == nombre)


def base_de(colocada: str) -> str:
    """La clave del `LISTADO` de una pieza colocada: `sector_1` es `sector`."""
    for clave in sorted(LISTADO, key=len, reverse=True):
        if colocada == clave or colocada.startswith(clave + "_"):
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
    "variable_de",
    "vista_de_pieza",
]
