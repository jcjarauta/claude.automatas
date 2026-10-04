"""Escribe `docs/materiales.md`: qué material se pide y qué sale de cada uno.

    uv run python scripts/lista_materiales.py --escribir

Se genera desde `emit.materiales.STOCK` y `emit.plataforma.LISTADO`, y un
test falla si el documento y el código se separan.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from emit.materiales import CORTE, MARGEN_DE_CHAPA, STOCK, tabla_markdown, tabla_tornilleria

RAIZ = Path(__file__).resolve().parent.parent
DOCUMENTO = RAIZ / "docs" / "materiales.md"


def documento() -> str:
    return (
        "# Materiales de la plataforma\n\n"
        "<!-- generado por scripts/lista_materiales.py, no editar a mano -->\n\n"
        f"**{len(STOCK)} materiales** para una plataforma. Cada pieza fabricada remite a uno "
        "(`emit/materiales.py`), y un test lo exige: el mismo material con dos nombres sale "
        "en la lista como dos compras.\n\n"
        f"Barra, tubo y alambre se piden por largo: el de cada pieza más {CORTE:g} mm de corte. "
        f"La chapa, por superficie: la caja de cada perfil más {MARGEN_DE_CHAPA:g} mm alrededor, "
        "sin anidar. Las levas del cartucho salen de la misma plancha de POM y no cuentan aquí: "
        "son del pedido.\n\n" + tabla_markdown() + "\n## Tornillería y retención\n\n"
        "Las cantidades salen de las piezas del listado: si cambia cuántos sectores o "
        "collares hay, cambia aquí. Todo inox A2.\n\n" + tabla_tornilleria()
    )


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--escribir", action="store_true", help="si no, solo imprime")
    op = p.parse_args(argv)
    texto = documento()
    if not op.escribir:
        print(texto, end="")
        return 0
    viejo = DOCUMENTO.read_text(encoding="utf-8") if DOCUMENTO.exists() else ""
    DOCUMENTO.write_text(texto, encoding="utf-8", newline="\n")
    print("sin cambios" if texto == viejo else f"escrito {DOCUMENTO}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
