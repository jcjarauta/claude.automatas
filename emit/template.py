"""Escribe una lámina maquetada como PDF a escala 1:1.

Esta capa es fina a propósito: recibe coordenadas en milímetros ya resueltas y
solo las traduce a la unidad interna del PDF, que es el punto de 1/72 de
pulgada. Toda la geometría se decide en `emit/layout.py`, que se puede
comprobar sin abrir un PDF.

Sobre la exactitud: 1 mm son 72/25,4 = 2,834645... puntos, un número que el
PDF guarda con decimales de sobra. El error que queda es de nanómetros. El
riesgo real no está aquí sino en la impresora, y por eso cada hoja lleva su
cuadro de calibración.

El lienzo se abre en modo invariante para que el mismo contenido produzca
siempre los mismos bytes: sin eso el PDF lleva fecha de creación y un
identificador aleatorio, y no habría forma de compararlo contra una
referencia guardada.
"""

from __future__ import annotations

from pathlib import Path
from typing import Final

from reportlab.lib.colors import Color
from reportlab.pdfgen.canvas import Canvas

from emit.layout import Circulo, Lamina, Texto, TipoTrazo, Trazo

PUNTOS_POR_MM: Final[float] = 72.0 / 25.4

NEGRO = Color(0, 0, 0)
GRIS = Color(0.45, 0.45, 0.45)

ESTILOS: Final[dict[TipoTrazo, tuple[float, tuple[float, ...] | None, Color]]] = {
    # tipo: (grosor en mm, patrón de guiones en mm, color)
    "corte": (0.6, None, NEGRO),
    "taladro": (0.25, None, NEGRO),
    "referencia": (0.25, (3.0, 2.0), GRIS),
    "oculta": (0.25, (0.8, 1.2), GRIS),
    "marca": (0.3, None, NEGRO),
    "cajetin": (0.3, None, GRIS),
}
"""Semántica de línea, pensada para distinguirse impresa en blanco y negro.
El corte es el trazo grueso continuo; todo lo demás es más fino o discontinuo,
para que nadie corte por donde no debe."""


def _pt(mm_valor: float) -> float:
    return mm_valor * PUNTOS_POR_MM


def _dibujar_trazo(lienzo: Canvas, trazo: Trazo) -> None:
    grosor, guiones, color = ESTILOS[trazo.tipo]
    lienzo.setLineWidth(_pt(grosor))
    lienzo.setStrokeColor(color)
    lienzo.setDash([_pt(g) for g in guiones] if guiones else [], 0)
    camino = lienzo.beginPath()
    primero, *resto = trazo.puntos
    camino.moveTo(_pt(primero[0]), _pt(primero[1]))
    for punto in resto:
        camino.lineTo(_pt(punto[0]), _pt(punto[1]))
    if trazo.cerrado:
        camino.close()
    lienzo.drawPath(camino, stroke=1, fill=0)


def _dibujar_circulo(lienzo: Canvas, circulo: Circulo) -> None:
    grosor, guiones, color = ESTILOS[circulo.tipo]
    lienzo.setLineWidth(_pt(grosor))
    lienzo.setStrokeColor(color)
    lienzo.setDash([_pt(g) for g in guiones] if guiones else [], 0)
    lienzo.circle(
        _pt(circulo.centro[0]), _pt(circulo.centro[1]), _pt(circulo.radio), stroke=1, fill=0
    )


def _dibujar_texto(lienzo: Canvas, texto: Texto) -> None:
    lienzo.setFillColor(NEGRO)
    lienzo.setFont("Helvetica-Bold" if texto.negrita else "Helvetica", _pt(texto.tamano))
    if texto.anclaje == "centro":
        lienzo.drawCentredString(_pt(texto.x), _pt(texto.y), texto.texto)
    else:
        lienzo.drawString(_pt(texto.x), _pt(texto.y), texto.texto)


def escribir_pdf(laminas: list[Lamina], destino: Path | str, version: str | None = None) -> Path:
    """Vuelca las láminas a un PDF, una página por lámina.

    Con `version`, cada lámina la lleva al pie: se imprimen sueltas y se
    pegan sobre el tablero, y sin versión no hay forma de saber de qué
    diseño salió la que tiene uno delante."""
    if version:
        from dataclasses import replace

        from emit.layout import Texto as _Rotulo

        laminas = [
            replace(
                lamina,
                textos=(*lamina.textos, _Rotulo(lamina.ancho - 10.0, 4.0, version, 2.5)),
            )
            for lamina in laminas
        ]
    if not laminas:
        raise ValueError("no hay nada que escribir: la lista de láminas está vacía")
    escalas = {lamina.escala for lamina in laminas}
    if len(escalas) > 1:
        # Un papel con dos escalas es la forma más rápida de que alguien
        # corte por la vista en vez de por la plantilla.
        raise ValueError(
            f"un documento no mezcla escalas: llegan {sorted(escalas)}. Las plantillas "
            "de corte van a 1:1 en su archivo y la documentación en el suyo."
        )
    ruta = Path(destino)
    ruta.parent.mkdir(parents=True, exist_ok=True)

    escala = laminas[0].escala
    lienzo = Canvas(str(ruta), invariant=1, pageCompression=0)
    if escala == 1.0:
        lienzo.setTitle(f"Plantilla 1:1 · {len(laminas)} hoja(s)")
        lienzo.setSubject("Imprimir al 100 %, sin ajustar a la página")
    else:
        lienzo.setTitle(f"Documentación 1:{1 / escala:.0f} · {len(laminas)} hoja(s)")
        lienzo.setSubject("Documentación: no es una plantilla, no se corta por aquí")

    for lamina in laminas:
        lienzo.setPageSize((_pt(lamina.ancho), _pt(lamina.alto)))
        for trazo in lamina.trazos:
            _dibujar_trazo(lienzo, trazo)
        for circulo in lamina.circulos:
            _dibujar_circulo(lienzo, circulo)
        for texto in lamina.textos:
            _dibujar_texto(lienzo, texto)
        lienzo.showPage()

    lienzo.save()
    return ruta


__all__ = ["ESTILOS", "PUNTOS_POR_MM", "escribir_pdf"]
