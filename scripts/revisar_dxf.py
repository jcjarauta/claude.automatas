"""Compara un DXF dibujado en el CAD contra el contrato.

    uv run python scripts/revisar_dxf.py --pieza varilla boceto.dxf

**Para que sirve.** El flujo es de un solo sentido: se toca el JSON, se
regenera la tabla, se dibuja. Nada impide que alguien acote a mano dentro de
Onshape, y si lo hace, el dibujo y el compilador dejan de decir lo mismo sin
que nadie se entere hasta que la pieza esta cortada. Esto lo caza en un
segundo.

Es la verificacion automatica de la metodologia aplicada al lado del CAD:
mide la geometria que salio del dibujo y la cruza con la cota del contrato.
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from pathlib import Path

import ezdxf

from compile.contratos import Contratos, cargar

RELOJ = Path("docs/reloj/contratos.json")
HOLGURA = 0.01
"""Milimetros. Un DXF trae los numeros en doble precision, asi que lo que se
busca es coincidencia exacta; esta holgura es para el redondeo, no para la
fabricacion."""


@dataclass(frozen=True)
class Medida:
    """Una cota medida en el dibujo frente a la que dice el contrato."""

    que: str
    contrato: float
    dibujo: float | None

    @property
    def pasa(self) -> bool:
        return self.dibujo is not None and abs(self.dibujo - self.contrato) <= HOLGURA


def _medidas_varilla(c: Contratos, ruta: Path) -> list[Medida]:
    doc = ezdxf.readfile(ruta)
    espacio = doc.modelspace()
    lineas = [e for e in espacio if e.dxftype() == "LINE"]
    circulos = [e for e in espacio if e.dxftype() == "CIRCLE"]

    xs = [v for e in lineas for v in (e.dxf.start.x, e.dxf.end.x)]
    ys = [v for e in lineas for v in (e.dxf.start.y, e.dxf.end.y)]
    largo = max(xs) - min(xs) if xs else None
    ancho = max(ys) - min(ys) if ys else None

    v = c.contrato("pendulo")
    medidas = [
        Medida("largo del contorno", v.valor("varilla_largo").en_mm, largo),
        Medida("ancho del contorno", v.valor("varilla_ancho").en_mm, ancho),
    ]

    # Los taladros, ordenados por su distancia al extremo de referencia.
    taladros = sorted(circulos, key=lambda e: e.dxf.center.x)
    esperados = (
        ("taladro cerca", "varilla_taladro_cerca"),
        ("taladro lejos", "varilla_taladro_lejos"),
    )
    for i, (titulo, clave) in enumerate(esperados):
        centro = taladros[i].dxf.center.x - min(xs) if i < len(taladros) else None
        medidas.append(Medida(f"{titulo}, al extremo", v.valor(clave).en_mm, centro))
    diametro = v.valor("varilla_taladro_diametro").en_mm
    for i, titulo in enumerate(("diametro del taladro cerca", "diametro del taladro lejos")):
        d = 2.0 * taladros[i].dxf.radius if i < len(taladros) else None
        medidas.append(Medida(titulo, diametro, d))

    # Centrados en el ancho: lo que deja pared igual a los dos lados.
    if ancho is not None:
        for i, titulo in enumerate(("taladro cerca, al eje", "taladro lejos, al eje")):
            y = taladros[i].dxf.center.y - min(ys) if i < len(taladros) else None
            medidas.append(Medida(titulo, ancho / 2.0, y))
    return medidas


REVISORES = {"varilla": _medidas_varilla}


def informe(medidas: list[Medida]) -> tuple[str, bool]:
    lineas = [f"{'que':34s} {'contrato':>10s} {'dibujo':>10s}   "]
    lineas.append("-" * 64)
    todo = True
    for m in medidas:
        dibujo = "AUSENTE" if m.dibujo is None else f"{m.dibujo:10.3f}"
        marca = "ok" if m.pasa else "NO COINCIDE"
        todo = todo and m.pasa
        lineas.append(f"{m.que:34s} {m.contrato:10.3f} {dibujo:>10s}   {marca}")
    lineas.append("")
    lineas.append(
        "El dibujo dice lo mismo que el contrato."
        if todo
        else "HAY COTAS QUE NO COINCIDEN. O el dibujo se acoto a mano, o el "
        "contrato cambio y falta regenerar."
    )
    return "\n".join(lineas), todo


def main(argv: list[str] | None = None) -> int:
    partes = argparse.ArgumentParser(prog="revisar_dxf", description=__doc__)
    partes.add_argument("dxf", type=Path)
    partes.add_argument("--pieza", default="varilla", choices=sorted(REVISORES))
    partes.add_argument("--contratos", type=Path, default=RELOJ)
    opciones = partes.parse_args(argv)

    medidas = REVISORES[opciones.pieza](cargar(opciones.contratos), opciones.dxf)
    texto, todo = informe(medidas)
    print(texto)
    return 0 if todo else 1


if __name__ == "__main__":
    sys.exit(main())
