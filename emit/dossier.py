"""El dossier de montaje: el PDF que acompaña a las piezas.

Lleva lo que pide `CLAUDE.md`: vistas ortográficas y una isométrica, la
lista de materiales, la de comerciales y tornillería, la secuencia de montaje
por subsistemas, la fase cero y cómo comprobarla, y la hoja de comprobación
final.

**Es un emisor y solo traduce.** Recibe las piezas ya colocadas —en 3D, a
escuadra con la base— y no sabe de dónde salen; el script que lo llama es
el que compila y monta (`scripts/dossier.py`). Los textos de taller no se
escriben aquí: se leen de `docs/procedimientos.md`, que es su única fuente, y
los de cada pieza de su ficha (`Ficha.montaje`).

**Las vistas son vectoriales**: aristas visibles de build123d
(`project_to_viewport`), un color por subsistema, dibujadas como líneas. Se
proyecta cada subsistema por separado, así que las aristas de un grupo no
ocultan las de otro: es un dibujo de líneas, no un render, y es lo que deja
leer el mecanismo a través del bastidor.

**Determinista**: mismo montaje, mismo PDF byte a byte (`rl_config.invariant`).
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from emit.montaje import GRUPOS, Grupo, grupo_de

VISTAS: dict[str, tuple[tuple[float, float, float], tuple[float, float, float]]] = {
    "isométrica": ((600.0, -800.0, 600.0), (0.0, 0.0, 1.0)),
    "planta": ((0.0, 0.0, 1000.0), (0.0, 1.0, 0.0)),
    "frente": ((0.0, -1000.0, 60.0), (0.0, 0.0, 1.0)),
    "perfil": ((1000.0, 0.0, 60.0), (0.0, 0.0, 1.0)),
}
"""Desde dónde se mira y hacia dónde es arriba, con la máquina a escuadra:
la mesa delante (-Y) y la salida del cartucho detrás (+Y)."""

ORDEN_DE_MONTAJE = (
    "bastidor",
    "cinco_barras",
    "entre_puntos",
    "seguidores",
    "amplificador",
    "accionamiento",
    "levantamiento",
    "portalapiz",
    "cartucho",
    "levas",
)
"""De abajo arriba y de dentro afuera. El cartucho y sus levas, los últimos:
es lo que se mete en una máquina ya montada, y lo que se cambia."""

COMPROBACIONES = (
    "Cada plato apretado entre sus collares; el 3, con su M3 avellanado en cada poste.",
    "Con el cartucho de calibrar puesto, la galga de 1,20 entra justa entre cada pasador "
    "de tope y su seguidor.",
    "Sin cartucho, cada seguidor descansa en su tope y ningún rodillo entra en el pasillo.",
    "El cartucho entra deslizando en fase cero y no entra girado media vuelta.",
    "El cubo apoya en el muñón y la garra está abajo, con el muelle extendido.",
    "Cada cinta, tensa y sin cruzar: la mordaza del sector apretada, el M2 del tambor apretado.",
    "Una vuelta lenta de manivela sin roces: ningún rodillo deja su leva, nada toca la cinta.",
    "La hoja de trazo patrón: el lápiz cae sobre la línea en toda la vuelta.",
)
"""La hoja de comprobación final. Cada línea es algo que en el banco de
pruebas del código ya se mira; aquí se mira con la máquina en la mano."""


# ---------------------------------------------------------------------------
# Vistas
# ---------------------------------------------------------------------------

Polilinea = list[tuple[float, float]]


@dataclass(frozen=True)
class Vista:
    """Una vista ya proyectada: polilíneas en mm del plano de la vista, con
    el color de su grupo y si va resaltada."""

    lineas: tuple[tuple[str, float, Polilinea], ...]
    """(color, grosor, polilínea)."""

    def caja(self) -> tuple[float, float, float, float]:
        xs = [x for _, _, p in self.lineas for x, _ in p]
        ys = [y for _, _, p in self.lineas for _, y in p]
        return min(xs), min(ys), max(xs), max(ys)


def _polilinea(arista: Any) -> Polilinea:
    from build123d import GeomType

    curva = arista.geom_type != GeomType.LINE
    pasos = max(4, min(48, int(arista.length / 1.5))) if curva else 1
    puntos = [arista.position_at(i / pasos) for i in range(pasos + 1)]
    return [(round(p.X, 3), round(p.Y, 3)) for p in puntos]


def proyectar(
    piezas: Sequence[tuple[str, Any]],
    vista: str,
    grupos: Sequence[str] | None = None,
    resaltar: str | None = None,
) -> Vista:
    """Proyecta las piezas de los grupos pedidos, un grupo cada vez.

    `resaltar` pinta ese grupo con su color y trazo grueso, y el resto en
    gris fino: es la vista de un paso de montaje.
    """
    from build123d import Compound

    origen, arriba = VISTAS[vista]
    lineas: list[tuple[str, float, Polilinea]] = []
    for g in GRUPOS:
        if grupos is not None and g.nombre not in grupos:
            continue
        solidos = [s for nombre, s in piezas if grupo_de(nombre) is g]
        if not solidos:
            continue
        visibles, _ = Compound(children=solidos).project_to_viewport(origen, arriba, (0, 0, 60))
        if resaltar is None:
            color = "#b8bcc2" if g.nombre == "bastidor" else g.color
            grosor = 0.25 if g.nombre == "bastidor" else 0.4
        elif g.nombre == resaltar:
            color, grosor = g.color, 0.6
        else:
            color, grosor = "#c8cbd0", 0.2
        lineas += [(color, grosor, _polilinea(a)) for a in visibles]
    return Vista(tuple(lineas))


# ---------------------------------------------------------------------------
# Texto: el markdown de los procedimientos, a párrafos de reportlab
# ---------------------------------------------------------------------------

_SUSTITUCIONES = {
    chr(0x2212): "-",  # signo menos
    chr(0x2265): ">=",
    chr(0x2264): "<=",
    chr(0x2192): "->",
    chr(0x2248): "~",
    chr(0x2011): "-",  # guion que no parte
}


def _limpio(texto: str) -> str:
    """Lo que la Helvetica del PDF no tiene se escribe con lo que sí."""
    for a, b in _SUSTITUCIONES.items():
        texto = texto.replace(a, b)
    # Las fuentes estándar del PDF van en Windows-1252: rayas, comillas,
    # viñetas y puntos suspensivos, sí; el signo menos y las flechas, no.
    return texto.encode("cp1252", "replace").decode("cp1252")


def _en_linea(texto: str) -> str:
    """Negritas y código del markdown, a las marcas de reportlab."""
    texto = _limpio(texto).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    texto = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", texto)
    texto = re.sub(r"`(.+?)`", r'<font name="Courier">\1</font>', texto)
    return texto


def bloques_de_markdown(md: str) -> list[tuple[str, Any]]:
    """El markdown de taller, en bloques: título, párrafo, lista, tabla.

    No es un intérprete de markdown: entiende lo que `docs/procedimientos.md`
    usa —títulos, párrafos, listas numeradas y con guion, una indentación y
    tablas— y nada más. Lo que no entienda sale como párrafo, no se pierde.
    """
    bloques: list[tuple[str, Any]] = []
    parrafo: list[str] = []
    tabla: list[list[str]] = []
    lista: list[tuple[int, str, str]] = []

    def cerrar() -> None:
        nonlocal parrafo, tabla, lista
        if parrafo:
            bloques.append(("parrafo", " ".join(parrafo)))
        if tabla:
            bloques.append(("tabla", [f for f in tabla if not set("".join(f)) <= set("-: ")]))
        if lista:
            bloques.append(("lista", lista))
        parrafo, tabla, lista = [], [], []

    for crudo in md.splitlines():
        linea = crudo.rstrip()
        sangria = len(linea) - len(linea.lstrip())
        texto = linea.strip()
        if not texto:
            cerrar()
            continue
        if texto.startswith("#"):
            cerrar()
            nivel = len(texto) - len(texto.lstrip("#"))
            bloques.append((f"h{nivel}", texto.lstrip("#").strip()))
        elif texto.startswith("|"):
            if parrafo or lista:
                cerrar()
            tabla.append([c.strip() for c in texto.strip("|").split("|")])
        elif m := re.match(r"(\d+)\.\s+(.*)", texto):
            if parrafo or tabla:
                cerrar()
            lista.append((sangria, m.group(1) + ".", m.group(2)))
        elif texto.startswith(("- ", "* ")):
            if parrafo or tabla:
                cerrar()
            lista.append((sangria, "•", texto[2:]))
        elif lista:
            nivel, marca, previo = lista[-1]
            lista[-1] = (nivel, marca, previo + " " + texto)
        else:
            parrafo.append(texto)
    cerrar()
    return bloques


# ---------------------------------------------------------------------------
# El PDF
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Datos:
    """Lo que el dossier imprime, ya calculado por quien lo llama."""

    titulo: str
    piezas: tuple[tuple[str, Any], ...]
    """(nombre, sólido) a escuadra con la base."""
    fabricadas: tuple[tuple[str, int, str, str, str, str], ...]
    """(pieza, cantidad, material, proceso, conjunto, montaje)."""
    comerciales: tuple[tuple[str, int, str], ...]
    """(pieza, cantidad, designación)."""
    tornilleria: tuple[tuple[str, int, str], ...]
    """(designación, cantidad, para)."""
    procedimientos: str
    """El markdown de `docs/procedimientos.md`."""
    pie: str
    """Lo que va al pie de cada página: de qué versión sale."""
    marcas: dict[tuple[str, str], tuple[str, str]] = field(default_factory=dict)
    """(serie, nombre) → (marca, plano), del registro `docs/numeracion.json`.
    Una pieza fabricada se busca por su nombre, una comercial por el suyo y
    una línea de tornillería por «designación · para»."""
    paginas: dict[tuple[str, str], tuple[str, int]] = field(default_factory=dict)
    """(serie, nombre) → (documento, hoja) donde está dibujado: el índice
    (`emit.numeracion.paginas`)."""


def _vista_flowable(vista: Vista, ancho: float, alto: float, titulo: str = "") -> Any:
    from reportlab.graphics.shapes import Drawing, PolyLine, String
    from reportlab.lib.colors import HexColor
    from reportlab.lib.units import mm

    x0, y0, x1, y1 = vista.caja()
    reserva = 5 * mm if titulo else 0.0
    escala = min(ancho / (x1 - x0), (alto - reserva) / (y1 - y0))
    dx = (ancho - (x1 - x0) * escala) / 2.0
    dibujo = Drawing(ancho, alto)
    for color, grosor, puntos in vista.lineas:
        plano = []
        for x, y in puntos:
            plano += [dx + (x - x0) * escala, (y - y0) * escala]
        dibujo.add(
            PolyLine(plano, strokeColor=HexColor(color), strokeWidth=grosor, strokeLineCap=1)
        )
    if titulo:
        dibujo.add(
            String(0, alto - 3.5 * mm, _limpio(titulo), fontName="Helvetica-Bold", fontSize=8)
        )
    return dibujo


def _esquema_flowable(esquema: Any, ancho: float, alto: float) -> Any:
    """La explosión de conjunto: los bloques en su color y un globo por grupo
    con su código, unido a su bloque. Todo lo que se dibuja sale del esquema
    (`emit.explosion.esquema_de_conjunto`), que es lo que mide el test."""
    from reportlab.graphics.shapes import Circle, Drawing, Line, PolyLine, String
    from reportlab.lib.colors import HexColor

    siglas = {g.nombre: g.sigla for g in GRUPOS}
    colores = {g.nombre: g.color for g in GRUPOS}
    cajas = [g.caja() for g in esquema.globos] + list(esquema.cajas.values())
    x0 = min(c[0] for c in cajas)
    y0 = min(c[1] for c in cajas)
    x1 = max(c[2] for c in cajas)
    y1 = max(c[3] for c in cajas)
    escala = min(ancho / (x1 - x0), alto / (y1 - y0))
    dx = (ancho - (x1 - x0) * escala) / 2.0

    def p(x: float, y: float) -> tuple[float, float]:
        return dx + (x - x0) * escala, (y - y0) * escala

    dibujo = Drawing(ancho, alto)
    for color, grosor, puntos in esquema.lineas:
        plano: list[float] = []
        for x, y in puntos:
            plano += list(p(x, y))
        dibujo.add(PolyLine(plano, strokeColor=HexColor(color), strokeWidth=grosor * 0.8))
    for globo in esquema.globos:
        ax, ay = p(*globo.ancla)
        cx, cy = p(*globo.centro)
        r = globo.radio * escala
        dibujo.add(Line(ax, ay, cx, cy, strokeColor=HexColor("#41464d"), strokeWidth=0.4))
        dibujo.add(
            Circle(
                cx,
                cy,
                r,
                strokeColor=HexColor(colores[globo.clave]),
                fillColor=HexColor("#ffffff"),
                strokeWidth=1.2,
            )
        )
        dibujo.add(
            String(
                cx,
                cy - 2.6,
                f"G-{siglas[globo.clave]}",
                fontName="Helvetica-Bold",
                fontSize=7,
                textAnchor="middle",
            )
        )
    return dibujo


def _indice(datos: Datos, ancho: float, celda: Any, h2: Any) -> list[Any]:
    """Las dos tablas del índice: por marca, en el orden de montaje, y por
    nombre, remitiendo a la marca."""
    from reportlab.platypus import Paragraph

    serie_de = {"piezas": 0, "comerciales": 1, "tornilleria": 2}
    paso_de = {g: i for i, g in enumerate(ORDEN_DE_MONTAJE, start=1)}
    grupo_de_sigla = {g.sigla: g.nombre for g in GRUPOS}
    que: dict[tuple[str, str], tuple[str, int, str]] = {}
    for n, k, material, *_ in datos.fabricadas:
        que[("piezas", n)] = (n, k, material)
    for n, k, d in datos.comerciales:
        que[("comerciales", n)] = (n, k, d)
    for d, k, para in datos.tornilleria:
        que[("tornilleria", f"{d} · {para}")] = (f"{d}, {para}", k, "")

    entradas = []
    for clave, (codigo, _) in datos.marcas.items():
        if clave not in que or clave not in datos.paginas:
            continue
        grupo = grupo_de_sigla[codigo.split("-")[1]]
        orden = (paso_de[grupo], serie_de[clave[0]], codigo)
        entradas.append((orden, clave, codigo, grupo))
    entradas.sort()

    filas = [["Marca", "Qué", "Ud.", "Material o designación", "Paso", "Documento", "Hoja"]]
    for (paso, _, _), clave, codigo, grupo in entradas:
        nombre, k, descripcion = que[clave]
        documento, hoja = datos.paginas[clave]
        filas.append(
            [codigo, nombre, str(k), descripcion, f"{paso}. {grupo}", documento, str(hoja)]
        )
    anchos = (0.1, 0.22, 0.05, 0.22, 0.13, 0.22, 0.06)
    salida = [_tabla(filas, [ancho * f for f in anchos], celda)]

    salida.append(Paragraph("Por orden alfabético", h2))
    filas = [["Pieza", "Marca", "Documento", "Hoja"]]
    filas += sorted(
        [que[clave][0], codigo, datos.paginas[clave][0], str(datos.paginas[clave][1])]
        for _, clave, codigo, _ in entradas
        if clave[0] != "tornilleria"
    )
    anchos = (0.4, 0.15, 0.3, 0.15)
    salida.append(_tabla(filas, [ancho * f for f in anchos], celda))
    return salida


def _tabla(filas: list[list[str]], anchos: list[float], estilo: Any, cabecera: bool = True) -> Any:
    from reportlab.lib import colors
    from reportlab.platypus import Paragraph, Table, TableStyle

    celdas = [[Paragraph(_en_linea(c), estilo) for c in fila] for fila in filas]
    tabla = Table(celdas, colWidths=anchos, repeatRows=1 if cabecera else 0)
    comandos = [
        ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#9aa0a6")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 1.5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 1.5),
    ]
    if cabecera:
        comandos.append(("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e8eaed")))
    tabla.setStyle(TableStyle(comandos))
    return tabla


def _leyenda(grupos: Sequence[Grupo], estilo: Any, ancho: float) -> Any:
    from reportlab.lib import colors
    from reportlab.platypus import Paragraph, Table, TableStyle

    filas = [
        [
            "",
            Paragraph(f"<b>{_limpio(g.nombre)}</b>", estilo),
            Paragraph(_en_linea(g.objetivo), estilo),
        ]
        for g in grupos
    ]
    tabla = Table(filas, colWidths=[6, ancho * 0.22, ancho - 6 - ancho * 0.22])
    comandos = [("VALIGN", (0, 0), (-1, -1), "MIDDLE")]
    for i, g in enumerate(grupos):
        comandos.append(("BACKGROUND", (0, i), (0, i), colors.HexColor(g.color)))
    tabla.setStyle(TableStyle(comandos))
    return tabla


def escribir_dossier(datos: Datos, destino: Path | str) -> Path:
    """Escribe el dossier en `destino` y lo devuelve."""
    from reportlab import rl_config
    from reportlab.lib.enums import TA_LEFT
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import mm
    from reportlab.platypus import (
        KeepTogether,
        PageBreak,
        Paragraph,
        SimpleDocTemplate,
        Spacer,
        Table,
    )

    rl_config.invariant = 1
    destino = Path(destino)
    destino.parent.mkdir(parents=True, exist_ok=True)
    hoja = getSampleStyleSheet()
    cuerpo = ParagraphStyle("cuerpo", parent=hoja["BodyText"], fontSize=8.5, leading=11)
    celda = ParagraphStyle("celda", parent=cuerpo, fontSize=7, leading=8.5, alignment=TA_LEFT)
    h1 = ParagraphStyle("h1", parent=hoja["Heading1"], fontSize=15, spaceAfter=4)
    h2 = ParagraphStyle("h2", parent=hoja["Heading2"], fontSize=11.5, spaceBefore=8, spaceAfter=3)
    ancho = A4[0] - 30 * mm

    def pie(lienzo: Any, doc: Any) -> None:
        lienzo.saveState()
        lienzo.setFont("Helvetica", 7)
        lienzo.drawString(15 * mm, 9 * mm, _limpio(f"{datos.titulo} · {datos.pie}"))
        lienzo.drawRightString(A4[0] - 15 * mm, 9 * mm, f"{doc.page}")
        # Las vistas del dossier van a escala libre: la frontera con las
        # plantillas 1:1, dicha en cada página (`emit.estilo.NO_MEDIR`).
        from reportlab.lib.colors import HexColor

        from emit.estilo import COTA, NO_MEDIR

        lienzo.setFillColor(HexColor(COTA))
        lienzo.drawCentredString(A4[0] / 2, 9 * mm, _limpio(NO_MEDIR))
        lienzo.restoreState()

    flujo: list[Any] = []

    # --- portada ------------------------------------------------------------------
    flujo.append(Paragraph(_limpio(datos.titulo), h1))
    flujo.append(
        Paragraph(
            "Dossier de montaje: qué es cada parte, en qué orden se monta, cómo se cala y cómo "
            "se comprueba. Las piezas y sus cotas están en sus hojas; aquí está cómo se juntan.",
            cuerpo,
        )
    )
    flujo.append(Spacer(1, 3 * mm))
    flujo.append(_vista_flowable(proyectar(datos.piezas, "isométrica"), ancho, 150 * mm))
    flujo.append(Spacer(1, 3 * mm))
    flujo.append(_leyenda(GRUPOS, celda, ancho))

    # --- índice -------------------------------------------------------------------
    if datos.paginas:
        flujo.append(PageBreak())
        flujo.append(Paragraph("Índice: dónde está cada cosa", h1))
        flujo.append(
            Paragraph(
                "Todo lo que hay encima de la mesa, por su marca: qué es, cuántas, en qué paso "
                "se monta y en qué documento y hoja está dibujado. Las piezas tienen ficha "
                "propia; los comerciales y la tornillería, la hoja de su grupo. Al final, por "
                "orden alfabético.",
                cuerpo,
            )
        )
        flujo.extend(_indice(datos, ancho, celda, h2))

    # --- vistas ortográficas ----------------------------------------------------
    flujo.append(PageBreak())
    flujo.append(Paragraph("Vistas", h1))
    flujo.append(_vista_flowable(proyectar(datos.piezas, "planta"), ancho, 140 * mm, "Planta"))
    flujo.append(Spacer(1, 6 * mm))
    medio = ancho / 2 - 3 * mm
    lado = [
        _vista_flowable(proyectar(datos.piezas, "frente"), medio, 90 * mm, "Frente"),
        _vista_flowable(proyectar(datos.piezas, "perfil"), medio, 90 * mm, "Perfil"),
    ]
    flujo.append(Table([lado], colWidths=[ancho / 2, ancho / 2]))

    # --- explosión de conjunto ----------------------------------------------------
    from emit.explosion import EXPLOSIONES, esquema_de_conjunto

    esquema = esquema_de_conjunto(datos.piezas)
    flujo.append(PageBreak())
    flujo.append(Paragraph("De qué está hecha: la explosión de conjunto", h1))
    flujo.append(
        Paragraph(
            "Cada grupo como un bloque, en su color y con su código de grupo, que es el de su "
            "hoja de fichas. La dirección de cada bloque está declarada; cuánto sale no: es lo "
            "justo para no tocar a los bloques anteriores.",
            cuerpo,
        )
    )
    flujo.append(_esquema_flowable(esquema, ancho, 165 * mm))
    filas = [["Grupo", "Código", "Sale hacia", "Cuánto (mm)"]]
    siglas = {g.nombre: g.sigla for g in GRUPOS}
    for nombre, distancia in esquema.distancias.items():
        eje = EXPLOSIONES[nombre].eje_conjunto
        hacia = (
            "queda quieto" if eje == (0.0, 0.0, 0.0) else f"({eje[0]:g}, {eje[1]:g}, {eje[2]:g})"
        )
        filas.append([nombre, f"G-{siglas[nombre]}", hacia, f"{distancia:.0f}"])
    flujo.append(_tabla(filas, [ancho * f for f in (0.3, 0.15, 0.35, 0.2)], celda))

    # --- despiece -----------------------------------------------------------------
    flujo.append(PageBreak())
    flujo.append(Paragraph("Despiece", h1))
    flujo.append(Paragraph("Piezas fabricadas", h2))

    def marca(serie: str, nombre: str) -> tuple[str, str]:
        return datos.marcas.get((serie, nombre), ("-", "-"))

    filas = [["Marca", "Pieza", "Ud.", "Material", "Proceso", "Plano"]]
    filas += sorted(
        [marca("piezas", n)[0], n, str(k), m, p, marca("piezas", n)[1]]
        for n, k, m, p, _, _ in datos.fabricadas
    )
    anchos = (0.11, 0.18, 0.05, 0.25, 0.3, 0.11)
    flujo.append(_tabla(filas, [ancho * f for f in anchos], celda))
    flujo.append(Paragraph("Comerciales", h2))
    filas = [["Marca", "Pieza", "Ud.", "Designación", "Hoja"]]
    filas += sorted(
        [marca("comerciales", n)[0], n, str(k), d, marca("comerciales", n)[1]]
        for n, k, d in datos.comerciales
    )
    anchos = (0.11, 0.2, 0.06, 0.52, 0.11)
    flujo.append(_tabla(filas, [ancho * f for f in anchos], celda))
    flujo.append(Paragraph("Tornillería y retención", h2))
    filas = [["Marca", "Designación", "Ud.", "Para", "Hoja"]]
    filas += sorted(
        [
            marca("tornilleria", f"{d} · {p}")[0],
            d,
            str(k),
            p,
            marca("tornilleria", f"{d} · {p}")[1],
        ]
        for d, k, p in datos.tornilleria
    )
    anchos = (0.11, 0.34, 0.06, 0.38, 0.11)
    flujo.append(_tabla(filas, [ancho * f for f in anchos], celda))

    # --- secuencia de montaje -----------------------------------------------------
    flujo.append(PageBreak())
    flujo.append(Paragraph("Secuencia de montaje", h1))
    flujo.append(
        Paragraph(
            "Por subsistemas, de abajo arriba y de dentro afuera. Cada paso dibuja la máquina "
            "hasta ahí, con lo nuevo en su color. El cartucho va el último: es lo que se mete en "
            "una máquina ya montada.",
            cuerpo,
        )
    )
    por_grupo = {g.nombre: g for g in GRUPOS}
    montadas: list[str] = []
    for paso, nombre in enumerate(ORDEN_DE_MONTAJE, start=1):
        g = por_grupo[nombre]
        montadas.append(nombre)
        texto = [
            Paragraph(f"{paso}. {_limpio(nombre)}", h2),
            Paragraph(_en_linea(g.objetivo + "."), cuerpo),
            _vista_flowable(
                proyectar(datos.piezas, "isométrica", grupos=montadas, resaltar=nombre),
                ancho,
                85 * mm,
            ),
        ]
        suyas = [f for f in datos.fabricadas if f[4] == nombre]
        if suyas:
            filas = [["Pieza", "Cómo se monta"]] + [[n, mt] for n, _, _, _, _, mt in suyas]
            texto.append(_tabla(filas, [ancho * 0.2, ancho * 0.8], celda))
        flujo.append(KeepTogether(texto[:3]))
        flujo.extend(texto[3:])

    # --- procedimientos ----------------------------------------------------------
    flujo.append(PageBreak())
    estilos = {"h1": h1, "h2": h2, "h3": h2}
    for tipo, contenido in bloques_de_markdown(datos.procedimientos):
        if tipo in estilos:
            flujo.append(Paragraph(_en_linea(contenido), estilos[tipo]))
        elif tipo == "parrafo":
            flujo.append(Paragraph(_en_linea(contenido), cuerpo))
        elif tipo == "tabla":
            columnas = max(len(f) for f in contenido)
            anchos = [ancho * 0.3] + [ancho * 0.7 / max(1, columnas - 1)] * (columnas - 1)
            flujo.append(_tabla(contenido, anchos, celda))
        elif tipo == "lista":
            for sangria, marca, item in contenido:
                estilo = ParagraphStyle(
                    "item", parent=cuerpo, leftIndent=8 + sangria * 3, bulletIndent=sangria * 3
                )
                flujo.append(Paragraph(_en_linea(item), estilo, bulletText=_limpio(marca)))
        flujo.append(Spacer(1, 1.5 * mm))

    # --- comprobación final -------------------------------------------------------
    flujo.append(PageBreak())
    flujo.append(Paragraph("Hoja de comprobación final", h1))
    flujo.append(
        Paragraph(
            "Una casilla por comprobación, con la máquina montada. Si una no se cumple, la "
            "máquina no sale: el apartado de procedimientos dice cómo corregirla.",
            cuerpo,
        )
    )
    filas = [["", "Comprobación", "Firma"]] + [["[  ]", c, ""] for c in COMPROBACIONES]
    flujo.append(_tabla(filas, [ancho * 0.07, ancho * 0.75, ancho * 0.18], cuerpo))

    doc = SimpleDocTemplate(
        str(destino),
        pagesize=A4,
        leftMargin=15 * mm,
        rightMargin=15 * mm,
        topMargin=14 * mm,
        bottomMargin=16 * mm,
        title=_limpio(datos.titulo),
        author="claude.automatas",
    )
    doc.build(flujo, onFirstPage=pie, onLaterPages=pie)
    return destino


__all__ = [
    "COMPROBACIONES",
    "ORDEN_DE_MONTAJE",
    "VISTAS",
    "Datos",
    "Vista",
    "bloques_de_markdown",
    "escribir_dossier",
    "proyectar",
]
