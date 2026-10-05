"""Diagnóstico: ¿se puede dibujar cada pieza desde cero con su ficha?

    uv run --group cad python scripts/dibujable.py          # recuento por grupo
    uv run --group cad python scripts/dibujable.py --todo   # cada falta

Genera las fichas de cada grupo y cruza el perfil de cada pieza —la lista de
Arco y Segmento que va al DXF— con lo que su ficha rotula
(`emit.dibujable.faltas`). Es el mismo cruce que el test
(`tests/emit/test_dibujable.py`): aquí se lee entero, con el nombre de cada
pieza.
"""

from __future__ import annotations

import argparse
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


def main(argv: list[str] | None = None) -> int:
    from emit.dibujable import faltas, perfil_de
    from emit.fichas import escribir_fichas
    from emit.montaje import GRUPOS
    from scripts.fichas import preparar

    sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[union-attr]
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--todo", action="store_true", help="cada falta, no solo el recuento")
    op = p.parse_args(argv)

    total = 0
    with tempfile.TemporaryDirectory() as carpeta:
        for g in GRUPOS:
            fichas = preparar(g.nombre)
            if not fichas.piezas:
                continue
            escribir_fichas(fichas, Path(carpeta) / f"{g.nombre}.pdf", "diagnóstico")
            pendientes = [
                f
                for pieza in fichas.piezas
                for f in faltas(perfil_de(pieza.nombre, fichas.contrato), pieza.acotacion)
            ]
            total += len(pendientes)
            print(f"== {g.nombre}: {len(pendientes)} faltas en {len(fichas.piezas)} piezas")
            if op.todo:
                for f in pendientes:
                    print(f"   {f}")
    print(f"TOTAL {total}")
    return 1 if total else 0


if __name__ == "__main__":
    raise SystemExit(main())
