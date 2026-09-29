"""Regenera los archivos de referencia de `tests/golden/`.

Solo se ejecuta cuando un cambio en la geometría es **intencionado**. Si el
test de referencia falla y no se sabe por qué, la respuesta no es regenerar:
es averiguar qué ha cambiado.

    uv run python scripts/regenerar_golden.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from emit.layout import Formato, maquetar
from emit.template import escribir_pdf
from tests.emit.piezas_de_prueba import leva

GOLDEN = Path(__file__).resolve().parent.parent / "tests" / "golden"


def main() -> int:
    GOLDEN.mkdir(parents=True, exist_ok=True)
    ruta = escribir_pdf(maquetar(leva(), Formato.A4), GOLDEN / "plantilla_leva_a4.pdf")
    print(f"regenerado {ruta.relative_to(GOLDEN.parent.parent)} ({ruta.stat().st_size} bytes)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
