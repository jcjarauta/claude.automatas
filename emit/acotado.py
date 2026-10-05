"""Las cotas como dato: un solo acotado para las hojas SVG y las PDF.

Una cota es una lista de primitivas —líneas, arcos, puntas de flecha,
círculos y rótulos— en mm de la hoja, y dos traducciones: `a_svg` y `a_pdf`.
Así una cota lineal, radial o **angular** es la misma en una hoja de bocetos
y en una ficha de pieza, con el mismo estilo (`emit.estilo`).

**La cota angular no existía**, y por eso nada que tuviera un ángulo se
acotaba: ni la posición de una cara plana, ni la de los taladros de la
mordaza en el sector. No era que se olvidaran: no se podía.

**El marco es el de quien llama.** Las primitivas no saben si la hoja tiene la
y hacia arriba (PDF) o hacia abajo (SVG): los ángulos se miden en el sentido
de los ejes que se den. Una hoja SVG que quiera ángulos antihorarios en
pantalla los pasa cambiados de signo.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

from emit import estilo

Punto = tuple[float, float]


@dataclass(frozen=True)
class Linea:
    a: Punto
    b: Punto
    grosor: float = estilo.LINEA_DE_COTA
    color: str = estilo.COTA


@dataclass(frozen=True)
class Arco:
    centro: Punto
    radio: float
    desde: float
    """Radianes, sentido positivo de los ejes de la hoja."""
    hasta: float
    grosor: float = estilo.LINEA_DE_COTA
    color: str = estilo.COTA


@dataclass(frozen=True)
class Punta:
    """Una punta de flecha rellena, con el vértice en `en`."""

    en: Punto
    hacia: Punto
    """Dirección a la que apunta, sin normalizar."""
    color: str = estilo.COTA


@dataclass(frozen=True)
class Circulo:
    centro: Punto
    radio: float
    color: str = estilo.REFERENCIA
    relleno: str = "#ffffff"


@dataclass(frozen=True)
class Rotulo:
    en: Punto
    texto: str
    cuerpo: float = estilo.CUERPO_COTA
    color: str = estilo.COTA
    angulo: float = 0.0
    """Grados, sentido positivo de los ejes de la hoja."""
    anclaje: str = "centro"
    """«centro», «izquierda» o «derecha»."""


Primitiva = Linea | Arco | Punta | Circulo | Rotulo

SEPARACION_DEL_TEXTO = 0.9
"""mm entre la línea de cota y la base de su número."""


def _unitario(dx: float, dy: float) -> Punto:
    n = math.hypot(dx, dy) or 1.0
    return dx / n, dy / n


def referencia(en: Punto, numero: str) -> list[Primitiva]:
    """La referencia a la fila de la tabla de variables: un número en un
    círculo, que se lee impreso y no cruza las líneas como un nombre largo."""
    return [
        Circulo(en, 1.55),
        Rotulo((en[0], en[1] - 0.6), numero, estilo.CUERPO_REFERENCIA, estilo.REFERENCIA),
    ]


def lineal(a: Punto, b: Punto, desplazamiento: Punto, texto: str, ref: str = "") -> list[Primitiva]:
    """Cota lineal entre dos puntos, desplazada con sus extensiones."""
    sx, sy = desplazamiento
    a2, b2 = (a[0] + sx, a[1] + sy), (b[0] + sx, b[1] + sy)
    ux, uy = _unitario(sx, sy)
    extra = 1.2
    salida: list[Primitiva] = [
        Linea(a, (a2[0] + ux * extra, a2[1] + uy * extra), estilo.EXTENSION),
        Linea(b, (b2[0] + ux * extra, b2[1] + uy * extra), estilo.EXTENSION),
        Linea(a2, b2),
        Punta(a2, (a2[0] - b2[0], a2[1] - b2[1])),
        Punta(b2, (b2[0] - a2[0], b2[1] - a2[1])),
    ]
    angulo = math.degrees(math.atan2(b2[1] - a2[1], b2[0] - a2[0]))
    if angulo > 90 or angulo <= -90:
        angulo -= 180
    medio = ((a2[0] + b2[0]) / 2, (a2[1] + b2[1]) / 2)
    nx, ny = -math.sin(math.radians(angulo)), math.cos(math.radians(angulo))
    texto_en = (medio[0] + nx * SEPARACION_DEL_TEXTO, medio[1] + ny * SEPARACION_DEL_TEXTO)
    salida.append(Rotulo(texto_en, texto, angulo=angulo))
    if ref:
        largo_texto = 0.18 * estilo.CUERPO_COTA * max(len(texto), 1) / 2 + 2.6
        tx, ty = math.cos(math.radians(angulo)), math.sin(math.radians(angulo))
        salida += referencia(
            (texto_en[0] + tx * largo_texto, texto_en[1] + ty * largo_texto + 1.0), ref
        )
    return salida


def radial(
    centro: Punto, radio: float, angulo: float, texto: str, ref: str = "", largo: float = 7.0
) -> list[Primitiva]:
    """Línea de referencia desde el canto de un arco hacia fuera, con la
    flecha en el canto y el texto en el extremo. `angulo` en grados."""
    ux, uy = math.cos(math.radians(angulo)), math.sin(math.radians(angulo))
    p0 = (centro[0] + radio * ux, centro[1] + radio * uy)
    p1 = (p0[0] + ux * largo, p0[1] + uy * largo)
    lado = 1.0 if ux >= 0 else -1.0
    p2 = (p1[0] + lado * 3.0, p1[1])
    salida: list[Primitiva] = [
        Linea(p0, p1),
        Linea(p1, p2),
        Punta(p0, (-ux, -uy)),
        Rotulo(
            (p2[0] + lado * 0.6, p2[1] - 0.8),
            texto,
            anclaje="izquierda" if lado > 0 else "derecha",
        ),
    ]
    if ref:
        ancho = 0.18 * estilo.CUERPO_COTA * max(len(texto), 1) + 2.4
        salida += referencia((p2[0] + lado * (0.6 + ancho), p2[1] + 0.4), ref)
    return salida


def angular(
    vertice: Punto,
    desde: float,
    hasta: float,
    radio: float,
    texto: str,
    ref: str = "",
    rayos: tuple[float, float] = (0.0, 0.0),
) -> list[Primitiva]:
    """Cota angular: dos líneas de referencia desde el vértice, el arco de
    cota entre ellas con una flecha en cada extremo y el número en grados.

    `desde` y `hasta` en radianes, en el sentido positivo de la hoja; el arco
    va de uno a otro por el camino corto. `rayos` es dónde empiezan las dos
    líneas de referencia, medido desde el vértice: cero si salen de él, más
    si arrancan en el canto de la pieza.
    """
    barrido = (hasta - desde + math.pi) % (2 * math.pi) - math.pi
    if barrido < 0:
        desde, hasta, barrido = hasta, desde, -barrido
    salida: list[Primitiva] = []
    for a, r0 in ((desde, rayos[0]), (desde + barrido, rayos[1])):
        ux, uy = math.cos(a), math.sin(a)
        salida.append(
            Linea(
                (vertice[0] + r0 * ux, vertice[1] + r0 * uy),
                (vertice[0] + (radio + 1.5) * ux, vertice[1] + (radio + 1.5) * uy),
                estilo.EXTENSION,
            )
        )
    salida.append(Arco(vertice, radio, desde, desde + barrido))
    for a, sentido in ((desde, -1.0), (desde + barrido, 1.0)):
        en = (vertice[0] + radio * math.cos(a), vertice[1] + radio * math.sin(a))
        tangente = (-math.sin(a) * sentido, math.cos(a) * sentido)
        salida.append(Punta(en, tangente))
    medio = desde + barrido / 2
    giro = math.degrees(medio) - 90.0
    while giro > 90:
        giro -= 180
    while giro <= -90:
        giro += 180
    texto_en = (
        vertice[0] + (radio + 1.4) * math.cos(medio),
        vertice[1] + (radio + 1.4) * math.sin(medio),
    )
    salida.append(Rotulo(texto_en, texto, angulo=giro))
    if ref:
        fuera = radio + 5.2
        salida += referencia(
            (vertice[0] + fuera * math.cos(medio), vertice[1] + fuera * math.sin(medio)), ref
        )
    return salida


def grados(angulo: float) -> str:
    """El rótulo de un ángulo: **sin signo**, porque el campo de ángulo del
    CAD mide una magnitud y no acepta un signo. El lado lo dice dónde cae el
    rasgo, y la variable que se teclea es el gemelo `_positivo` del contrato."""
    return f"{round(abs(math.degrees(angulo)), 2):g}".replace(".", ",") + "°"


# ---------------------------------------------------------------------------
# Las dos traducciones
# ---------------------------------------------------------------------------


def _flecha(en: Punto, hacia: Punto) -> list[Punto]:
    ux, uy = _unitario(*hacia)
    largo, ancho = estilo.FLECHA_LARGO, estilo.FLECHA_ANCHO
    return [
        en,
        (en[0] - ux * largo - uy * ancho, en[1] - uy * largo + ux * ancho),
        (en[0] - ux * largo + uy * ancho, en[1] - uy * largo - ux * ancho),
    ]


def a_pdf(cv: Any, primitivas: list[Primitiva]) -> None:
    """Dibuja en un lienzo de reportlab; coordenadas en mm, la y hacia arriba."""
    from reportlab.lib.colors import HexColor

    mm = 72.0 / 25.4
    for p in primitivas:
        if isinstance(p, Linea):
            cv.setStrokeColor(HexColor(p.color))
            cv.setLineWidth(p.grosor * mm)
            cv.line(p.a[0] * mm, p.a[1] * mm, p.b[0] * mm, p.b[1] * mm)
        elif isinstance(p, Arco):
            cv.setStrokeColor(HexColor(p.color))
            cv.setLineWidth(p.grosor * mm)
            pasos = max(8, int(abs(p.hasta - p.desde) * p.radio / 0.4))
            camino = cv.beginPath()
            for i in range(pasos + 1):
                a = p.desde + (p.hasta - p.desde) * i / pasos
                x = (p.centro[0] + p.radio * math.cos(a)) * mm
                y = (p.centro[1] + p.radio * math.sin(a)) * mm
                if i == 0:
                    camino.moveTo(x, y)
                else:
                    camino.lineTo(x, y)
            cv.drawPath(camino, stroke=1, fill=0)
        elif isinstance(p, Punta):
            cv.setFillColor(HexColor(p.color))
            v = _flecha(p.en, p.hacia)
            camino = cv.beginPath()
            camino.moveTo(v[0][0] * mm, v[0][1] * mm)
            for x, y in v[1:]:
                camino.lineTo(x * mm, y * mm)
            camino.close()
            cv.drawPath(camino, stroke=0, fill=1)
        elif isinstance(p, Circulo):
            cv.setStrokeColor(HexColor(p.color))
            cv.setFillColor(HexColor(p.relleno))
            cv.setLineWidth(estilo.EXTENSION * mm)
            cv.circle(p.centro[0] * mm, p.centro[1] * mm, p.radio * mm, stroke=1, fill=1)
        elif isinstance(p, Rotulo):
            cv.saveState()
            cv.setFillColor(HexColor(p.color))
            cv.setFont(estilo.FUENTE, p.cuerpo)
            cv.translate(p.en[0] * mm, p.en[1] * mm)
            cv.rotate(p.angulo)
            texto = p.texto.encode("cp1252", "replace").decode("cp1252")
            if p.anclaje == "izquierda":
                cv.drawString(0, 0, texto)
            elif p.anclaje == "derecha":
                cv.drawRightString(0, 0, texto)
            else:
                cv.drawCentredString(0, 0, texto)
            cv.restoreState()


def a_svg(primitivas: list[Primitiva]) -> list[str]:
    """Elementos SVG en el marco de quien llama. Con la y hacia abajo, un
    rótulo girado se gira al revés: SVG rota en sentido horario."""
    salida: list[str] = []
    for p in primitivas:
        if isinstance(p, Linea):
            salida.append(
                f'<line x1="{p.a[0]:.2f}" y1="{p.a[1]:.2f}" x2="{p.b[0]:.2f}" y2="{p.b[1]:.2f}" '
                f'stroke="{p.color}" stroke-width="{p.grosor:.2f}"/>'
            )
        elif isinstance(p, Arco):
            x0 = p.centro[0] + p.radio * math.cos(p.desde)
            y0 = p.centro[1] + p.radio * math.sin(p.desde)
            x1 = p.centro[0] + p.radio * math.cos(p.hasta)
            y1 = p.centro[1] + p.radio * math.sin(p.hasta)
            grande = 1 if abs(p.hasta - p.desde) > math.pi else 0
            barrido = 1 if p.hasta > p.desde else 0
            salida.append(
                f'<path d="M {x0:.2f},{y0:.2f} A {p.radio:.2f},{p.radio:.2f} 0 {grande} '
                f'{barrido} {x1:.2f},{y1:.2f}" fill="none" stroke="{p.color}" '
                f'stroke-width="{p.grosor:.2f}"/>'
            )
        elif isinstance(p, Punta):
            v = _flecha(p.en, p.hacia)
            puntos = " ".join(f"{x:.2f},{y:.2f}" for x, y in v)
            salida.append(f'<polygon points="{puntos}" fill="{p.color}"/>')
        elif isinstance(p, Circulo):
            salida.append(
                f'<circle cx="{p.centro[0]:.2f}" cy="{p.centro[1]:.2f}" r="{p.radio:.2f}" '
                f'fill="{p.relleno}" stroke="{p.color}" stroke-width="{estilo.EXTENSION:.2f}"/>'
            )
        elif isinstance(p, Rotulo):
            ancla = {"izquierda": "start", "derecha": "end"}.get(p.anclaje, "middle")
            tamano = p.cuerpo * 25.4 / 72.0
            salida.append(
                f'<text x="{p.en[0]:.2f}" y="{p.en[1]:.2f}" fill="{p.color}" '
                f'font-family="{estilo.FUENTE},Arial,sans-serif" font-size="{tamano:.2f}" '
                f'text-anchor="{ancla}" transform="rotate({-p.angulo:.2f} {p.en[0]:.2f} '
                f'{p.en[1]:.2f})">{p.texto}</text>'
            )
    return salida


__all__ = [
    "Arco",
    "Circulo",
    "Linea",
    "Primitiva",
    "Punta",
    "Rotulo",
    "a_pdf",
    "a_svg",
    "angular",
    "grados",
    "lineal",
    "radial",
    "referencia",
]
