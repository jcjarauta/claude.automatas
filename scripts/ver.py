"""Mira una pieza o la máquina entera en el visor de VS Code.

    uv run --group cad python scripts/ver.py seguidor
    uv run --group cad python scripts/ver.py --conjunto --theta 90
    uv run --group cad python scripts/ver.py --conjunto --step build/montaje.step

Hace falta la extensión **OCP CAD Viewer** de VS Code, con el visor
abierto (paleta de comandos → *OCP CAD Viewer: Open viewer*). Sin visor,
`--step` escribe el sólido y se abre con cualquier cosa.

**Por qué existe.** Las catorce envolventes del catálogo estuvieron mil
veces pequeñas durante días con tres tests encima, y lo que faltaba no era
otro test: era que alguien hubiera **abierto** uno de esos archivos
alguna vez. Se generaban, se guardaban y se arrastraban al CAD. Esto pone
el ojo en el bucle sin salir del editor.
"""

from __future__ import annotations

import argparse
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from emit.plataforma import LISTADO

RAIZ = Path(__file__).resolve().parent.parent


def _conjunto(theta_grados: float):
    from compile.conjunto import piezas_en
    from compile.escribiente import Escribiente, compilar
    from scripts.exportar_para_cad import leer

    compilacion = compilar(leer(RAIZ / "demo" / "hola.json"))
    piezas = piezas_en(compilacion, Escribiente(), math.radians(theta_grados))
    return [p.nombre for p in piezas], [p.solido for p in piezas]


def main(argv: list[str] | None = None) -> int:
    partes = argparse.ArgumentParser(prog="ver", description=__doc__)
    partes.add_argument("pieza", nargs="?", choices=sorted(LISTADO), help="una pieza suelta")
    partes.add_argument("--conjunto", action="store_true", help="la máquina montada")
    partes.add_argument("--theta", type=float, default=0.0, help="ángulo del árbol, en grados")
    partes.add_argument("--step", type=Path, help="escribe un STEP en vez de mostrarlo")
    op = partes.parse_args(argv)

    if not op.conjunto and op.pieza is None:
        partes.error("di qué pieza, o --conjunto")

    if op.conjunto:
        nombres, solidos = _conjunto(op.theta)
    else:
        from emit.montaje import solido_de

        nombres, solidos = [op.pieza], [solido_de(op.pieza)]

    if op.step is not None:
        from build123d import Compound, export_step

        op.step.parent.mkdir(parents=True, exist_ok=True)
        export_step(Compound(children=solidos), str(op.step))
        print(f"{len(solidos)} sólidos en {op.step}")
        return 0

    try:
        from ocp_vscode import show
    except ImportError:
        print(
            "falta el visor: uv sync --group cad, y la extensión «OCP CAD Viewer» en VS Code.\n"
            "Mientras tanto, --step escribe el sólido en un archivo.",
            file=sys.stderr,
        )
        return 1

    try:
        show(*solidos, names=nombres)
    except Exception as fallo:
        print(
            f"el visor no respondió ({fallo}).\nAbre «OCP CAD Viewer: Open viewer» en la "
            "paleta de comandos de VS Code, o usa --step.",
            file=sys.stderr,
        )
        return 1
    print(f"{len(solidos)} sólidos en el visor")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
