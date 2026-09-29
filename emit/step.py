"""STEP: el sólido 3-D, para quien quiera el conjunto en un CAD.

Esto no calcula nada. La masa y la inercia salen exactas del polígono en
`core/solido.py`, y las interferencias que importan son planas: un kernel de
CAD no daría números mejores. Lo que sí da, y no se consigue de otra manera,
es un **STEP B-rep**: un sólido con caras, aristas y vértices de verdad, que
es lo que Onshape y cualquier otro CAD necesitan para poder acotar, medir y
emparejar piezas. Una malla —lo que exporta un OpenSCAD— entra como un
amasijo de triángulos con el que no se puede trabajar.

De ahí el reparto con Onshape, que es lo que hace que la cuota anual de su
API deje de importar:

- **El cartucho lo genera esto.** Cambia en cada pedido, no se edita nunca y
  entra arrastrando el archivo. Cero llamadas a la API.
- **La plataforma se escribe a mano en FeatureScript.** No cambia entre
  pedidos y tiene que seguir siendo paramétrica dentro de Onshape.

`build123d` es una dependencia **opcional**: son unos ochocientos megas de
kernel OCCT y ni el compilador ni la plantilla de papel los necesitan.

    uv sync --group cad

Sin ella, todo lo demás funciona y esto avisa de que falta.
"""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path
from typing import Any

from core.units import a_mm
from emit.pieza import Pieza

MARCA_DIAMETRO = 3.0
"""Milímetros del avellanado que señala la fase. Se rebaja en la cara de
arriba: un cartucho montado desfasado escribe basura, y la marca tiene que
verse con la pieza en la mano."""

MARCA_PROFUNDIDAD = 1.0

_FALTA = (
    "para exportar STEP hace falta build123d, que es una dependencia opcional "
    "por su tamaño. Instálala con:  uv sync --group cad"
)


def disponible() -> bool:
    """Si el kernel está instalado. Los tests que lo necesitan lo preguntan."""
    try:
        import build123d  # noqa: F401
    except ImportError:
        return False
    return True


def solido_de_pieza(pieza: Pieza, z: float = 0.0) -> Any:
    """Extruye el contorno, taladra los agujeros y rebaja la marca de fase.

    En milímetros: se cruza aquí la frontera de unidades, como en el resto de
    `emit/`. La marca no va sobre el contorno sino un poco hacia dentro, o se
    quedaría medio fuera de la pieza.
    """
    try:
        from build123d import (
            BuildLine,
            BuildPart,
            BuildSketch,
            Circle,
            Locations,
            Mode,
            Plane,
            Polyline,
            Pos,
            extrude,
            make_face,
        )
    except ImportError as exc:  # pragma: no cover - depende del entorno
        raise ImportError(_FALTA) from exc

    espesor = a_mm(pieza.espesor)
    contorno = [(a_mm(x), a_mm(y)) for x, y in pieza.contorno]

    with BuildPart() as parte:
        with BuildSketch():
            with BuildLine():
                Polyline(*contorno, close=True)
            make_face()
        extrude(amount=espesor)

        for taladro in pieza.taladros:
            with (
                BuildSketch(Plane.XY),
                Locations((a_mm(taladro.centro[0]), a_mm(taladro.centro[1]))),
            ):
                Circle(radius=a_mm(taladro.diametro) / 2.0)
            extrude(amount=espesor, mode=Mode.SUBTRACT)

        if pieza.marca_fase is not None:
            x, y = a_mm(pieza.marca_fase[0]), a_mm(pieza.marca_fase[1])
            radio = (x**2 + y**2) ** 0.5
            hacia_dentro = max(0.0, radio - MARCA_DIAMETRO) / radio if radio > 0.0 else 0.0
            with (
                BuildSketch(Plane.XY.offset(espesor - MARCA_PROFUNDIDAD)),
                Locations((x * hacia_dentro, y * hacia_dentro)),
            ):
                Circle(radius=MARCA_DIAMETRO / 2.0)
            extrude(amount=MARCA_PROFUNDIDAD, mode=Mode.SUBTRACT)

    solido = parte.part
    if solido is None:  # pragma: no cover - solo si el contorno no cierra
        raise ValueError(f"'{pieza.nombre}': el contorno no llegó a formar un sólido")
    return Pos(0.0, 0.0, z) * solido


def cartucho(piezas: Sequence[Pieza], separacion: float = 2.0) -> Any:
    """Las piezas apiladas en el árbol, en el orden en que se dan."""
    if not piezas:
        raise ValueError("no hay piezas que apilar")
    solidos = []
    altura = 0.0
    for pieza in piezas:
        solidos.append(solido_de_pieza(pieza, z=altura))
        altura += a_mm(pieza.espesor) + separacion
    conjunto = solidos[0]
    for solido in solidos[1:]:
        conjunto = conjunto + solido
    return conjunto


def escribir_step(
    piezas: Sequence[Pieza],
    destino: Path | str,
    separacion: float = 2.0,
) -> Path:
    """Vuelca el cartucho apilado a un STEP. Devuelve dónde quedó."""
    try:
        from build123d import export_step
    except ImportError as exc:  # pragma: no cover - depende del entorno
        raise ImportError(_FALTA) from exc

    ruta = Path(destino)
    ruta.parent.mkdir(parents=True, exist_ok=True)
    export_step(cartucho(piezas, separacion), str(ruta))
    return ruta


def masa_del_solido(solido: Any, densidad: float) -> float:
    """Kilogramos, a partir del volumen que mide el kernel.

    Existe para contrastar: `core/solido.py` calcula lo mismo integrando el
    polígono, y que dos caminos tan distintos coincidan es lo que permite
    fiarse del barato.
    """
    return float(solido.volume) * 1.0e-9 * densidad


__all__ = [
    "MARCA_DIAMETRO",
    "MARCA_PROFUNDIDAD",
    "cartucho",
    "disponible",
    "escribir_step",
    "masa_del_solido",
    "solido_de_pieza",
]
