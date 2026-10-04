"""Escribe el dossier de montaje en build/fab/dossier.pdf.

    uv run --group cad python scripts/dossier.py [--destino ruta.pdf]

Compila el pedido de ejemplo, monta la máquina a escuadra con la base y le
pasa a `emit.dossier` lo que imprime: las piezas colocadas, el despiece, la
tornillería y `docs/procedimientos.md`. El emisor no compila nada.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

RAIZ = Path(__file__).resolve().parent.parent

ALIAS = {"platina_levas": "plato1", "casquillo_rodillo": "eje_rodillo_1"}  # el resto, por prefijo
"""Piezas del listado que en el montaje se llaman de otra forma: la platina
es cada uno de los tres platos, y el casquillo va dentro del eje del rodillo."""


def _version() -> str:
    try:
        salida = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=RAIZ,
            capture_output=True,
            text=True,
            check=True,
        )
        return f"commit {salida.stdout.strip()}"
    except (OSError, subprocess.CalledProcessError):
        return "sin control de versiones"


def grupo_de_pieza(pieza: str, nombres: list[str] | None = None) -> str:
    """El subsistema de una pieza del listado, buscándola en el montaje: la
    pieza «brazo_proximal» se coloca como «proximal_1», la platina como cada
    plato. Sin `nombres`, monta la máquina para buscarlos."""
    from emit.montaje import grupo_de

    if nombres is None:
        from scripts.ver import _piezas

        nombres = [p.nombre for p, _ in _piezas(0.0)]
    buscado = ALIAS.get(pieza, pieza)
    for n in nombres:
        if n == buscado or n.startswith((buscado + "_", buscado.replace("brazo_", "") + "_")):
            return grupo_de(n).nombre
    raise ValueError(f"la pieza {pieza} no está en el montaje")


def datos(version: str | None = None):
    from emit.catalogo import cargar
    from emit.dossier import Datos
    from emit.materiales import tornilleria
    from emit.plataforma import LISTADO
    from scripts.ver import _piezas

    colocadas = [(p.nombre, s) for p, s in _piezas(0.0)]
    nombres = [n for n, _ in colocadas]

    fabricadas = tuple(
        (n, f.cantidad, f.material, f.proceso, grupo_de_pieza(n, nombres), f.montaje)
        for n, f in LISTADO.items()
    )
    comerciales = tuple((p.nombre, p.cantidad, p.designacion) for p in cargar())
    return Datos(
        titulo="Escribiente",
        piezas=tuple(colocadas),
        fabricadas=fabricadas,
        comerciales=comerciales,
        tornilleria=tuple((f.designacion, f.cantidad, f.para) for f in tornilleria()),
        procedimientos=(RAIZ / "docs" / "procedimientos.md").read_text(encoding="utf-8"),
        pie=version or _version(),
    )


def main(argv: list[str] | None = None) -> int:
    from emit.dossier import escribir_dossier

    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--destino", type=Path, default=RAIZ / "build" / "fab" / "dossier.pdf")
    op = p.parse_args(argv)
    ruta = escribir_dossier(datos(), op.destino)
    print(f"dossier en {ruta}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
