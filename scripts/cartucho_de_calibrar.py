"""Escribe los DXF del cartucho de calibrar en build/fab/calibrar/.

    uv run python scripts/cartucho_de_calibrar.py

Tres discos de POM de 5 redondos, al radio de diseño de cada canal, con el
taladro del eje, el pasador de índice y la marca de fase. Se montan con el
mismo eje, cubo y separadores que un cartucho de verdad. Para qué sirven:
`compile/calibrar.py` y `docs/procedimientos.md`.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from compile.calibrar import cartucho_de_calibrar
from emit.dxf import escribir_dxf

RAIZ = Path(__file__).resolve().parent.parent


def main() -> int:
    destino = RAIZ / "build" / "fab" / "calibrar"
    destino.mkdir(parents=True, exist_ok=True)
    for pieza in cartucho_de_calibrar():
        ruta = escribir_dxf(pieza, destino / f"{pieza.numero}.dxf")
        print(f"{pieza.numero}  {pieza.nombre}  ->  {ruta}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
