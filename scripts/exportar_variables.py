"""Convierte un fichero de contratos en la tabla de variables de Onshape.

    uv run python scripts/exportar_variables.py                    # escribiente, a la pantalla
    uv run python scripts/exportar_variables.py --out build/
    uv run python scripts/exportar_variables.py --csv \
        --contratos docs/reloj/contratos.json --out build/

**Una tabla por maquina, y por tanto un documento de Onshape por maquina.**
El Variable Studio tiene un solo espacio de nombres, asi que mezclar las cotas
del escribiente con las del reloj es pedir que alguien dibuje una platina con
el radio base de una leva. Cada maquina tiene su fichero de contratos, su
tabla y su documento.

Lo que las dos comparten -el contrato de eje- esta escrito en los dos ficheros
a proposito, y hay un test que comprueba que dicen lo mismo. Es la unica forma
de que el arbol del reloj entre en el agujero del escribiente el dia que se
acoplen.

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
import csv as modulo_csv
import io
import math
import sys
from pathlib import Path

from compile.contratos import RUTA, Contratos, Estado, Valor, cargar

CABECERA = """// Variables de {maquina}, generadas desde {fuente}
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


def featurescript(
    contratos: Contratos,
    maquina: str = "el escribiente",
    fuente: str = "docs/contratos.json",
) -> str:
    """El bloque para pegar en una Feature Studio de Onshape."""
    lineas = [
        CABECERA.format(
            maquina=maquina, fuente=fuente, version=contratos.version, fecha=contratos.fecha
        )
    ]
    for contrato in contratos.contratos:
        estado = contrato.estado.value.upper()
        lineas.append(f"// ---- {contrato.nombre.upper()} · {estado} ----")
        lineas.append(f"// {contrato.porque}")
        if contrato.estado is Estado.PENDIENTE:
            lineas.append("// OJO: pendiente de medir. Se puede dibujar, no se puede prometer.")
        for valor in contrato.valores:
            expresion, comentario = _valor_para_onshape(valor)
            tolerancia = f"  [{valor.tolerancia}]" if valor.tolerancia else ""
            lineas.append(
                f"export const {valor.nombre} = {expresion};  // {comentario}{tolerancia}"
            )
        lineas.append("")
    return "\n".join(lineas)


def csv(contratos: Contratos) -> str:
    """La tabla, por si se importa en vez de pegarse.

    Se escribe con el modulo `csv` y no a mano porque una tolerancia o una
    descripcion pueden llevar coma -`m6 en el plato metalico, deslizante en
    el POM` la lleva- y a mano eso parte la fila en dos columnas de mas sin
    que nada avise.
    """
    buffer = io.StringIO()
    escritor = modulo_csv.writer(buffer, lineterminator="\n")
    escritor.writerow(
        ["nombre", "valor", "unidad", "contrato", "estado", "tolerancia", "descripcion"]
    )
    for contrato in contratos.contratos:
        for valor in contrato.valores:
            if valor.unidad == "m":
                cifra, unidad = f"{valor.en_mm:.4f}", "mm"
            elif valor.unidad == "rad":
                cifra, unidad = f"{math.degrees(valor.valor):.4f}", "deg"
            else:
                cifra, unidad = f"{valor.valor:.6g}", valor.unidad.replace("adimensional", "")
            escritor.writerow(
                [
                    valor.nombre,
                    cifra,
                    unidad,
                    contrato.nombre,
                    contrato.estado.value,
                    valor.tolerancia,
                    valor.descripcion,
                ]
            )
    return buffer.getvalue()


def _maquina_de(fuente: Path) -> str:
    """El rotulo sale de la carpeta: `docs/reloj/contratos.json` -> reloj.

    El del escribiente vive en `docs/` a secas por razones historicas, asi
    que esa es la excepcion y no hay forma de deducirlo del nombre.
    """
    carpeta = fuente.parent.name
    return "escribiente" if carpeta in ("docs", "") else carpeta


def main(argv: list[str] | None = None) -> int:
    partes = argparse.ArgumentParser(prog="exportar_variables", description=__doc__)
    partes.add_argument("--out", type=Path, default=None, help="carpeta donde escribir")
    partes.add_argument("--csv", action="store_true", help="CSV en vez de FeatureScript")
    partes.add_argument(
        "--contratos",
        type=Path,
        default=None,
        help="fichero de contratos; por defecto el del escribiente",
    )
    partes.add_argument(
        "--maquina",
        default=None,
        help="rotulo de la maquina; por defecto sale de la carpeta del fichero",
    )
    opciones = partes.parse_args(argv)

    fuente = opciones.contratos if opciones.contratos is not None else RUTA
    maquina = opciones.maquina or _maquina_de(fuente)
    contratos = cargar(fuente)
    texto = (
        csv(contratos)
        if opciones.csv
        else featurescript(contratos, maquina=f"el {maquina}", fuente=str(fuente))
    )

    if opciones.out is None:
        print(texto)
        return 0

    opciones.out.mkdir(parents=True, exist_ok=True)
    nombre = f"variables-{maquina}.{'csv' if opciones.csv else 'fs'}"
    ruta = opciones.out / nombre
    ruta.write_text(texto, encoding="utf-8")
    print(f"escrito {ruta}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
