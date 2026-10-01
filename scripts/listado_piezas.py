"""Escribe en `docs/metodologia.md` el listado de piezas y variables.

    uv run python scripts/listado_piezas.py --escribir

La tabla se **genera**. Escrita a mano envejecería en silencio, y lo que la
lee es alguien tecleando cotas en un CAD: una fila que dice 40 donde el
contrato dice 80 no se nota hasta que la pieza está cortada.

Es el mismo patrón que el resto de cruces del repo —la hoja de bocetos
contra el CSV, el catálogo contra la ficha— aplicado al documento: hay un
test que falla si el markdown y `emit/plataforma.LISTADO` se separan.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from emit.plataforma import tabla_markdown

RAIZ = Path(__file__).resolve().parent.parent
METODOLOGIA = RAIZ / "docs" / "metodologia.md"
INICIO = "<!-- listado:inicio · generado por scripts/listado_piezas.py, no editar a mano -->"
FIN = "<!-- listado:fin -->"


def con_listado(documento: str, tabla: str | None = None) -> str:
    """El documento con la tabla puesta entre las marcas."""
    tabla = tabla_markdown() if tabla is None else tabla
    if INICIO not in documento or FIN not in documento:
        raise ValueError(f"faltan las marcas {INICIO} / {FIN} en el documento")
    antes = documento[: documento.index(INICIO) + len(INICIO)]
    despues = documento[documento.index(FIN) :]
    return f"{antes}\n\n{tabla}\n{despues}"


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--escribir", action="store_true", help="si no, solo imprime la tabla")
    op = p.parse_args(argv)
    if not op.escribir:
        print(tabla_markdown(), end="")
        return 0
    viejo = METODOLOGIA.read_text(encoding="utf-8")
    nuevo = con_listado(viejo)
    METODOLOGIA.write_text(nuevo, encoding="utf-8")
    print("sin cambios" if nuevo == viejo else f"listado actualizado en {METODOLOGIA}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
