"""Genera plantillas de muestra para la verificación humana de E3.

    uv run python scripts/plantillas_demo.py [carpeta]

Produce dos archivos:

- `plantilla_leva_A4.pdf` — una leva real en una hoja. Es la que hay que
  imprimir y medir con una regla metálica.
- `plantilla_bastidor_troceado_A4.pdf` — una pieza que no cabe en A4, para
  comprobar el solape y las marcas de registro al pegar las hojas.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.units import a_mm
from emit.layout import Formato, formato_minimo, maquetar
from emit.template import escribir_pdf
from tests.emit.piezas_de_prueba import bastidor_grande, leva


def main() -> int:
    destino = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("out")
    destino.mkdir(parents=True, exist_ok=True)

    for pieza, formato, nombre in (
        (leva(), Formato.A4, "plantilla_leva_A4.pdf"),
        (bastidor_grande(), Formato.A4, "plantilla_bastidor_troceado_A4.pdf"),
    ):
        laminas = maquetar(pieza, formato)
        ruta = escribir_pdf(laminas, destino / nombre)
        print(
            f"{ruta.name:<40} {a_mm(pieza.ancho):6.1f} × {a_mm(pieza.alto):6.1f} mm  "
            f"→ {len(laminas)} hoja(s) {formato.value}  "
            f"(cabría entera en {formato_minimo(pieza)})"
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
