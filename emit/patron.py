"""La hoja de trazo patrón: lo que la máquina debería escribir, a tamaño real.

Es el método de verificación más barato que tiene el proyecto y sale gratis,
porque el compilador ya simula el trazo para comprobarse a sí mismo. Lo único
que faltaba era sacarlo por la impresora.

**Cómo se usa.** Se imprime a 1:1, se pone bajo la máquina alineando las
cuatro marcas de registro, se gira la manivela y se mira si el lápiz cae
sobre la línea. Sin instrumentos, sin medir y sin saber leer un plano:
cualifica cualquiera. En un taller ocupacional eso no es una comodidad, es la
diferencia entre una verificación que se hace y una que no.

**Qué caza y qué no.** Caza lo que se nota a simple vista y es casi todo lo
que puede ir mal en el montaje: un cartucho calado donde no toca, un brazo
con el calaje equivocado, una leva cambiada de sitio, el lápiz que no
levanta. No caza décimas: para eso está el presupuesto de error, y la
diferencia entre lo que promete el modelo y lo que llega a la punta es de un
orden de magnitud.

**Se imprime el vuelo, no solo el trazo.** La línea de puntos es por dónde
pasa la punta con el lápiz levantado. No queda en el papel del cliente, pero
en la hoja patrón dice si el levantamiento ocurre donde debe, que es la mitad
de los fallos de programa.

**Lleva cuadro de calibración** como cualquier hoja 1:1 del proyecto. Con más
motivo que ninguna: una hoja patrón escalada un 1 % diría que la máquina está
mal cuando la que está mal es la impresora.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from pathlib import Path

import numpy as np

from emit.layout import (
    LADO_CALIBRACION,
    MARGEN,
    Formato,
    Lamina,
    Texto,
    Trazo,
    cuadro_de_calibracion,
)

LADO_REGISTRO = 12.0
"""Largo del brazo de cada marca de registro, en milímetros."""

MARGEN_AL_TRAZO = 12.0
"""Lo que se deja alrededor de la caja de escritura, para que las marcas de
registro no caigan encima del dibujo."""

ALTO_TITULO = 34.0

UMBRAL_DE_APOYO = 0.1
"""Por debajo de cuántos milímetros se considera que el lápiz escribe.

No puede ser cero. La altura de la hoja patrón no sale del programa sino de
**recorrer la leva**, así que oscila alrededor del cero unas milésimas. Con
un umbral de 1e-9 mm el trazo se partía en dieciséis tramos donde hay
cuatro, y la hoja salía con costuras donde la máquina dibuja seguido.

0,1 mm es menos de lo que se mueve un lápiz sobre su muelle y más que el
ruido del muestreo.
"""

Tramo = tuple[tuple[float, float], ...]
"""Un trozo de recorrido continuo, en milímetros de página."""


@dataclass(frozen=True)
class Patron:
    """Lo que hace falta para dibujar la hoja, ya en milímetros.

    Como `Pieza`, es la frontera entre el compilador y el emisor: el
    compilador la rellena y el emisor solo la traduce a papel. Por eso este
    módulo no sabe que existe una `Compilacion`.
    """

    nombre: str
    escritos: tuple[Tramo, ...]
    """Tramos por donde pasa la punta con el lápiz apoyado."""
    vuelo: tuple[Tramo, ...]
    """Y con el lápiz levantado."""
    caja: tuple[float, float, float, float]
    """x0, y0, ancho, alto de la caja de escritura."""
    error_del_modelo: float
    """Lo que el simulador dice que se desvía, en milímetros. **No es la
    precisión de la máquina**: eso lo dice el presupuesto de error."""


def patron_de(
    nombre: str,
    puntos: np.ndarray,
    altura: np.ndarray,
    caja: tuple[float, float, float, float],
    error_del_modelo: float,
    umbral: float = UMBRAL_DE_APOYO,
) -> Patron:
    """Parte el recorrido en tramos según el lápiz esté apoyado o en vuelo.

    `puntos` y `altura` llegan **en metros**, como salen del núcleo, y aquí
    se pasan a milímetros: es un emisor, que es donde toca convertir.

    Sin partirlo, el trazo saldría unido por los vuelos y la hoja mostraría
    líneas que la máquina no dibuja.
    """
    xy = np.asarray(puntos, dtype=np.float64) * 1000.0
    apoyado = np.asarray(altura, dtype=np.float64) * 1000.0 <= umbral
    if len(xy) == 0:
        return Patron(nombre, (), (), caja, error_del_modelo)

    cortes = np.flatnonzero(np.diff(apoyado.astype(np.int8))) + 1
    escritos: list[Tramo] = []
    vuelos: list[Tramo] = []
    inicio = 0
    for tramo in np.split(xy, cortes):
        if len(tramo) >= 2:
            destino = escritos if bool(apoyado[inicio]) else vuelos
            destino.append(tuple((float(x), float(y)) for x, y in tramo))
        inicio += len(tramo)

    return Patron(
        nombre=nombre,
        escritos=tuple(escritos),
        vuelo=tuple(vuelos),
        caja=caja,
        error_del_modelo=error_del_modelo,
    )


def _marca_de_registro(x: float, y: float, hacia_x: float, hacia_y: float) -> list[Trazo]:
    """Una escuadra en una esquina, para alinear la hoja bajo la máquina."""
    brazo = LADO_REGISTRO
    return [
        Trazo("marca", ((x, y), (x + brazo * hacia_x, y))),
        Trazo("marca", ((x, y), (x, y + brazo * hacia_y))),
    ]


def lamina_de_patron(
    patron: Patron,
    formato: Formato = Formato.A4,
    peor_caso: float | None = None,
) -> Lamina:
    """Monta la hoja entera, a 1:1.

    `peor_caso` es el error esperado en la punta según C4, en milímetros. Si
    se pasa, se rotula: es lo que separa «el lápiz no cae en la línea» de
    «el lápiz no cae en la línea **más de lo que debería**».
    """
    ancho_pagina, alto_pagina = formato.medidas
    x0, y0, ancho_caja, alto_caja = patron.caja

    # La caja se centra en la página, con sitio arriba para el título y abajo
    # para el cuadro de calibración.
    alto_del_dibujo = alto_caja + 2.0 * (MARGEN_AL_TRAZO + LADO_REGISTRO)
    hueco = alto_pagina - ALTO_TITULO - LADO_CALIBRACION - 3.0 * MARGEN - alto_del_dibujo
    dx = ancho_pagina / 2.0 - (x0 + ancho_caja / 2.0)
    dy = (
        MARGEN
        + LADO_CALIBRACION
        + MARGEN
        + max(hueco, 0.0) / 2.0
        + MARGEN_AL_TRAZO
        + LADO_REGISTRO
        - y0
    )

    trazos: list[Trazo] = []
    textos: list[Texto] = []

    # La caja de escritura, en discontinuo: es referencia, no se dibuja.
    trazos.append(
        Trazo(
            "referencia",
            (
                (x0 + dx, y0 + dy),
                (x0 + ancho_caja + dx, y0 + dy),
                (x0 + ancho_caja + dx, y0 + alto_caja + dy),
                (x0 + dx, y0 + alto_caja + dy),
            ),
            cerrado=True,
        )
    )

    # El trazo y el vuelo.
    for tramo in patron.escritos:
        trazos.append(Trazo("corte", tuple((x + dx, y + dy) for x, y in tramo)))
    for tramo in patron.vuelo:
        trazos.append(Trazo("oculta", tuple((x + dx, y + dy) for x, y in tramo)))

    # Marcas de registro en las cuatro esquinas de la caja, separadas.
    m = MARGEN_AL_TRAZO
    esquinas = (
        (x0 - m, y0 - m, 1.0, 1.0),
        (x0 + ancho_caja + m, y0 - m, -1.0, 1.0),
        (x0 + ancho_caja + m, y0 + alto_caja + m, -1.0, -1.0),
        (x0 - m, y0 + alto_caja + m, 1.0, -1.0),
    )
    for ex, ey, hx, hy in esquinas:
        trazos += _marca_de_registro(ex + dx, ey + dy, hx, hy)

    # La cruz del centro de la caja, que es el punto de calaje de los brazos.
    cx, cy = x0 + ancho_caja / 2.0 + dx, y0 + alto_caja / 2.0 + dy
    trazos.append(Trazo("marca", ((cx - 4.0, cy), (cx + 4.0, cy))))
    trazos.append(Trazo("marca", ((cx, cy - 4.0), (cx, cy + 4.0))))

    # El cuadro de calibración, abajo a la izquierda.
    cuadro = cuadro_de_calibracion(MARGEN, MARGEN)
    trazos += cuadro.trazos
    textos += cuadro.textos

    # El título.
    arriba = alto_pagina - MARGEN
    textos.append(Texto(MARGEN, arriba - 5.0, "HOJA DE TRAZO PATRÓN", 6.0, True))
    textos.append(
        Texto(MARGEN, arriba - 12.0, f"«{patron.nombre}» · {date.today().isoformat()}", 4.0)
    )
    textos.append(
        Texto(
            MARGEN,
            arriba - 19.0,
            "Imprimir a 1:1, SIN ajuste de página. Poner bajo la máquina alineando las "
            "cuatro escuadras.",
            3.2,
        )
    )
    textos.append(
        Texto(
            MARGEN,
            arriba - 24.5,
            "Girar la manivela despacio y comprobar que la punta cae sobre la línea continua.",
            3.2,
        )
    )
    linea = "Línea continua: trazo. Punteada: vuelo, con el lápiz levantado."
    if peor_caso is not None:
        linea += f" Desviación admisible: {peor_caso:.1f} mm."
    textos.append(Texto(MARGEN, arriba - 30.0, linea, 3.2))

    # Junto al cuadro de calibración, lo que no es obvio.
    x_nota = MARGEN + LADO_CALIBRACION + 8.0
    textos.append(Texto(x_nota, MARGEN + LADO_CALIBRACION - 6.0, "Qué dice esta hoja", 4.0, True))
    for i, nota in enumerate(
        (
            "La cruz del centro es el punto de calaje de los brazos.",
            "Si el trazo sale desplazado en bloque, revisa el calaje.",
            "Si sale girado o espejado, el cartucho está mal calado.",
            "Si el lápiz raya donde hay puntos, revisa la leva del elevador.",
            f"Error del modelo: {patron.error_del_modelo:.3f} mm. No es el de la máquina.",
        )
    ):
        textos.append(Texto(x_nota, MARGEN + LADO_CALIBRACION - 14.0 - i * 5.5, nota, 3.2))

    return Lamina(
        ancho=ancho_pagina,
        alto=alto_pagina,
        trazos=tuple(trazos),
        circulos=tuple(cuadro.circulos),
        textos=tuple(textos),
        escala=1.0,
    )


def escribir_patron(
    patron: Patron,
    destino: Path | str,
    formato: Formato = Formato.A4,
    peor_caso: float | None = None,
    version: str | None = None,
) -> Path:
    """Escribe `patron.pdf` en la carpeta del pedido."""
    from emit.template import escribir_pdf

    return escribir_pdf([lamina_de_patron(patron, formato, peor_caso)], destino, version)


__all__ = [
    "ALTO_TITULO",
    "LADO_REGISTRO",
    "MARGEN_AL_TRAZO",
    "Patron",
    "escribir_patron",
    "lamina_de_patron",
    "patron_de",
]
