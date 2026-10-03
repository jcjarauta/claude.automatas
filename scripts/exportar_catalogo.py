"""Escribe el catálogo de piezas comerciales en STEP, para importarlo al CAD.

    uv run --group cad python scripts/exportar_catalogo.py --out build/catalogo/

Un archivo por referencia, más un índice en markdown con las cotas de
interfaz y de dónde sale cada una. Todo se genera desde `docs/piezas/`, así
que **no puede discrepar de lo que calcula el compilador**.

Son envolventes, no modelos de fabricante: exactas en las cotas que la ficha
marca como críticas y toscas en el resto. Para montar, acotar y comprobar
interferencias es lo correcto; para el render de venta se importa encima el
STEP del fabricante, si lo hay.

Necesita el kernel: `uv sync --group cad`.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from core.comercial import PiezaComercial
from emit.catalogo import caja_envolvente, cargar, escribir_catalogo


def indice(piezas: list[PiezaComercial]) -> str:
    """La hoja que acompaña a los STEP: qué es cada uno y qué hay que pedir."""
    lineas = [
        "# Catálogo de piezas comerciales",
        "",
        "Generado desde `docs/piezas/` con `scripts/exportar_catalogo.py`.",
        "**No se edita a mano**: se toca la ficha y se regenera.",
        "",
        "Los sólidos son **envolventes**. Son exactos en las cotas marcadas como",
        "críticas —las que otra pieza toca— y toscos en el resto: un engranaje sale",
        "como un disco sin dientes, y un muelle como el cilindro que ocupa.",
        "",
        "| Pieza | Cant. | Referencia | Envolvente (mm) | Cotas críticas |",
        "| --- | --- | --- | --- | --- |",
    ]
    for p in piezas:
        x, y, z = caja_envolvente(p)
        criticas = ", ".join(f"{c.nombre} {float(c.valor) * 1000:g}" for c in p.criticas) or "—"
        lineas.append(
            f"| `{p.nombre}.step` | {p.cantidad} | {p.designacion} | "
            f"{x:.1f} × {y:.1f} × {z:.1f} | {criticas} |"
        )

    pendientes = [p for p in piezas if not p.fuente.verificado or p.pedir]
    if pendientes:
        lineas += ["", "## Lo que falta confirmar", ""]
        for p in pendientes:
            que = p.pedir or "el precio, que no se pudo leer en la página del proveedor"
            lineas.append(f"- **{p.nombre}** ({p.fuente.proveedor}): {que}")

    lineas += ["", "## De dónde sale cada cota", ""]
    for p in piezas:
        lineas.append(
            f"- **{p.nombre}** — [{p.fuente.referencia}]({p.fuente.url}), {p.fuente.fecha}"
        )
    return "\n".join(lineas) + "\n"


def main(argv: list[str] | None = None) -> int:
    partes = argparse.ArgumentParser(prog="exportar_catalogo", description=__doc__)
    partes.add_argument("--out", type=Path, default=Path("build/catalogo"))
    opciones = partes.parse_args(argv)

    piezas = cargar()
    if not piezas:
        print("no hay fichas en docs/piezas/", file=sys.stderr)
        return 1

    escritos = escribir_catalogo(piezas, opciones.out)
    (opciones.out / "README.md").write_text(indice(piezas), encoding="utf-8")

    print(f"{len(escritos)} piezas en {opciones.out}/")
    sin_verificar = [p.nombre for p in piezas if not p.fuente.verificado]
    if sin_verificar:
        print(f"sin verificar: {', '.join(sin_verificar)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
