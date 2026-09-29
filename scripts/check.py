"""Ejecuta las tres comprobaciones de la puerta E0 y devuelve 0 solo si todo pasa.

Funciona igual en Windows, macOS y Linux:

    uv run python scripts/check.py
"""

from __future__ import annotations

import subprocess
import sys

COMPROBACIONES = [
    ("formato y lint", ["ruff", "check", "."]),
    ("tipos", ["mypy", "core", "compile"]),
    ("tests", ["pytest"]),
]


def main() -> int:
    fallos = []
    for nombre, comando in COMPROBACIONES:
        print(f"\n=== {nombre}: {' '.join(comando)}")
        resultado = subprocess.run(comando, check=False)
        if resultado.returncode != 0:
            fallos.append(nombre)

    print()
    if fallos:
        print(f"ROJO — falla: {', '.join(fallos)}")
        return 1
    print("VERDE — lint, tipos y tests en orden")
    return 0


if __name__ == "__main__":
    sys.exit(main())
