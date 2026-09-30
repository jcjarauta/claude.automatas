"""Convierte `docs/contratos.json` en la tabla de variables de Onshape.

    uv run python scripts/exportar_variables.py            # a la pantalla
    uv run python scripts/exportar_variables.py --out build/

**Para qué.** La plataforma se dibuja a mano en Onshape y tiene que usar los
mismos números que el compilador. Copiarlos a ojo es cómo la valona del
casquillo acabó siendo Ø12 en tres sitios cuando el fabricante dice Ø15. Esto
los escribe una vez, en el formato que Onshape entiende, y se pegan en el
**Variable Studio** del documento. Todas las Part Studios de la plataforma
los referencian desde ahí con `#nombre`.

**El flujo es de un solo sentido.** Se toca el JSON, se regenera, se pega. No
se editan las variables dentro de Onshape: lo que se edite allí se pierde en
la siguiente regeneración y, peor, deja de coincidir con lo que calcula el
compilador sin que nadie se entere.

**Unidades.** El compilador trabaja en metros y radianes; Onshape en
milímetros y grados. La conversión ocurre aquí, que es la frontera, y no a
medias por el camino.

Dos formatos:

- **FeatureScript**, para pegar en una Feature Studio y llamarla desde el
  Variable Studio. Es el que conserva los comentarios.
- **CSV**, por si se prefiere la tabla de variables importada.
"""

from __future__ import annotations

import argparse
import math
import sys
from pathlib import Path

from compile.contratos import Contratos, Estado, Valor, cargar

CABECERA = """// Variables del escribiente, generadas desde docs/contratos.json
// NO EDITAR AQUI: se regenera con  uv run python scripts/exportar_variables.py
// Version del contrato: {version}   Fecha: {fecha}
"""


def _valor_para_onshape(valor: Valor) -> tuple[str, str]:
    """Devuelve (expresión, comentario) ya en unidades de Onshape."""
    if valor.unidad == "m":
        return f"{valor.en_mm:.4f} * millimeter", valor.descripcion
    if valor.unidad == "rad":
        return f"{math.degrees(valor.valor):.4f} * degree", valor.descripcion
    return f"{valor.valor:.6g}", valor.descripcion


def featurescript(contratos: Contratos) -> str:
    """El bloque para pegar en una Feature Studio de Onshape."""
    lineas = [CABECERA.format(version=contratos.version, fecha=contratos.fecha)]
    for contrato in contratos.contratos:
        estado = contrato.estado.value.upper()
        lineas.append(f"// ---- {contrato.nombre.upper()} · {estado} ----")
        lineas.append(f"// {contrato.porque}")
        if contrato.estado is Estado.PENDIENTE:
            lineas.append("// OJO: pendiente de E4. Se puede dibujar, no se puede prometer.")
        for valor in contrato.valores:
            expresion, comentario = _valor_para_onshape(valor)
            tolerancia = f"  [{valor.tolerancia}]" if valor.tolerancia else ""
            lineas.append(
                f"export const {valor.nombre} = {expresion};  // {comentario}{tolerancia}"
            )
        lineas.append("")
    return "\n".join(lineas)


def csv(contratos: Contratos) -> str:
    """La tabla, por si se importa en vez de pegarse."""
    filas = ["nombre,valor,unidad,contrato,estado,tolerancia,descripcion"]
    for contrato in contratos.contratos:
        for valor in contrato.valores:
            if valor.unidad == "m":
                cifra, unidad = f"{valor.en_mm:.4f}", "mm"
            elif valor.unidad == "rad":
                cifra, unidad = f"{math.degrees(valor.valor):.4f}", "deg"
            else:
                cifra, unidad = f"{valor.valor:.6g}", ""
            descripcion = valor.descripcion.replace('"', "'")
            filas.append(
                f"{valor.nombre},{cifra},{unidad},{contrato.nombre},"
                f'{contrato.estado.value},{valor.tolerancia},"{descripcion}"'
            )
    return "\n".join(filas) + "\n"


def main(argv: list[str] | None = None) -> int:
    partes = argparse.ArgumentParser(prog="exportar_variables", description=__doc__)
    partes.add_argument("--out", type=Path, default=None, help="carpeta donde escribir")
    partes.add_argument("--csv", action="store_true", help="CSV en vez de FeatureScript")
    opciones = partes.parse_args(argv)

    contratos = cargar()
    texto = csv(contratos) if opciones.csv else featurescript(contratos)

    if opciones.out is None:
        print(texto)
        return 0

    opciones.out.mkdir(parents=True, exist_ok=True)
    nombre = "variables.csv" if opciones.csv else "variables.fs"
    ruta = opciones.out / nombre
    ruta.write_text(texto, encoding="utf-8")
    print(f"escrito {ruta}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
