"""Escribe en `docs/niveles.md` la tabla de los tres niveles del escribiente.

    uv run --group cad python scripts/niveles.py --escribir

Levas, cartucho y máquina se fabrican y se montan por separado, con otra
frecuencia y a menudo por otra persona. La tabla cuenta lo que tiene cada
uno —piezas, unidades, materiales, procesos, comerciales, fijaciones y
ajustes a mano— para que las mejoras se busquen donde pesan. Se genera
entre marcas; lo que hay fuera (el análisis) se escribe a mano, y un test
avisa si la tabla se queda vieja.
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

RAIZ = Path(__file__).resolve().parent.parent
DOCUMENTO = RAIZ / "docs" / "niveles.md"
INICIO = "<!-- niveles:inicio · generado por scripts/niveles.py, no editar a mano -->"
FIN = "<!-- niveles:fin -->"

COMERCIAL_DEL_CARTUCHO = ("pasador_indice",)
"""Lo comercial que viaja con el cartucho; el resto es de la máquina."""

AJUSTES: dict[str, tuple[str, ...]] = {
    "levas": (),
    "cartucho": (),
    "maquina": (
        "orientar 3 collares de seguidor con la galga de 1,20",
        "calar 2 brazos con la mordaza de la cinta",
        "apretar 6 collares de plato a su altura",
    ),
}
"""Lo que se ajusta a mano, no lo que se monta: cada uno es una ocasión de
error y un paso del dossier."""


@dataclass(frozen=True)
class Nivel:
    nombre: str
    quien: str
    piezas: tuple[tuple[str, int, str, str], ...]
    """(pieza, unidades, material, proceso)."""
    comerciales: tuple[tuple[str, int], ...]
    fijaciones: int
    ajustes: tuple[str, ...]


def niveles() -> list[Nivel]:
    from compile.escribiente import Escribiente, compilar
    from emit.catalogo import cargar
    from emit.materiales import tornilleria
    from emit.montaje import nivel_de
    from emit.plataforma import LISTADO
    from scripts.dossier import grupo_de_pieza
    from tests.casos import hola

    levas = compilar(hola(), Escribiente()).piezas
    material_leva = Escribiente().material_leva
    from scripts.ver import _piezas

    montadas = [p.nombre for p, _ in _piezas(0.0)]
    por_nivel: dict[str, list[tuple[str, int, str, str]]] = {"cartucho": [], "maquina": []}
    for nombre, ficha in LISTADO.items():
        nivel = nivel_de(grupo_de_pieza(nombre, montadas))
        por_nivel[nivel].append((nombre, ficha.cantidad, ficha.material, ficha.proceso))
    comerciales = [(p.nombre, p.cantidad) for p in cargar()]
    return [
        Nivel(
            "levas",
            "por pedido, fuera: fresado en un solo amarre",
            tuple((p.nombre, 1, material_leva, "fresado CNC") for p in levas),
            (),
            0,
            AJUSTES["levas"],
        ),
        Nivel(
            "cartucho",
            "metal a stock; se monta por pedido con las levas",
            tuple(por_nivel["cartucho"]),
            tuple(c for c in comerciales if c[0] in COMERCIAL_DEL_CARTUCHO),
            0,
            AJUSTES["cartucho"],
        ),
        Nivel(
            "maquina",
            "a stock, igual en todos los pedidos",
            tuple(por_nivel["maquina"]),
            tuple(c for c in comerciales if c[0] not in COMERCIAL_DEL_CARTUCHO),
            sum(f.cantidad for f in tornilleria()),
            AJUSTES["maquina"],
        ),
    ]


def tabla() -> str:
    filas = [
        "| Nivel | Quién y cuándo | Piezas fabricadas | Unidades | Materiales | Procesos "
        "| Comerciales (ud.) | Fijaciones | Ajustes a mano |",
        "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |",
    ]
    for n in niveles():
        ajustes = "; ".join(n.ajustes) if n.ajustes else "ninguno"
        filas.append(
            f"| **{n.nombre}** | {n.quien} | {len(n.piezas)} | {sum(u for _, u, _, _ in n.piezas)} "
            f"| {len({m for _, _, m, _ in n.piezas})} | {len({p for _, _, _, p in n.piezas})} "
            f"| {len(n.comerciales)} ({sum(u for _, u in n.comerciales)}) | {n.fijaciones} "
            f"| {ajustes} |"
        )
    return "\n".join(filas) + "\n"


def con_tabla(documento: str) -> str:
    if INICIO not in documento or FIN not in documento:
        raise ValueError(f"faltan las marcas {INICIO} / {FIN}")
    antes = documento[: documento.index(INICIO) + len(INICIO)]
    return f"{antes}\n\n{tabla()}\n{documento[documento.index(FIN) :]}"


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--escribir", action="store_true")
    op = p.parse_args(argv)
    if not op.escribir:
        print(tabla(), end="")
        return 0
    viejo = DOCUMENTO.read_text(encoding="utf-8")
    nuevo = con_tabla(viejo)
    DOCUMENTO.write_text(nuevo, encoding="utf-8", newline="\n")
    print("sin cambios" if nuevo == viejo else f"tabla actualizada en {DOCUMENTO}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
