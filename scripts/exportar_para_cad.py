"""Arma el paquete que hace falta para montar el escribiente en un CAD.

    uv run --group cad python scripts/exportar_para_cad.py demo/hola.json --out build/cad/

Todo lo que hace falta existía ya, pero repartido en tres comandos que
escriben en tres sitios y sin decir en qué orden se usan. Esto los junta y
añade la hoja que dice qué hacer con cada cosa, que es lo que faltaba de
verdad: **un paquete de importación no es un montón de archivos, es un montón
de archivos con un orden.**

El reparto con el CAD es el de `CLAUDE.md`, y es lo que hace que la cuota
anual de Onshape deje de importar:

- **El cartucho** cambia en cada pedido y no se edita nunca a mano. Lo genera
  el compilador: DXF para bocetos y STEP para el sólido. Se arrastra.
- **La plataforma** no cambia entre pedidos y tiene que seguir siendo
  paramétrica. Se escribe una vez dentro del CAD, y lee sus cotas del
  Variable Studio.
- **Las piezas comerciales** se generan desde su ficha, no se bajan del
  fabricante: así por construcción dicen lo mismo que el compilador.

El camino por pedido —el que se repite cientos de veces— no toca la API
nunca.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from compile.contratos import cargar as cargar_contratos
from compile.escribiente import compilar
from core.escritura import Escritura, Trazo
from core.units import mm
from emit.dxf import escribir_dxf
from scripts.exportar_variables import csv, featurescript


def leer(entrada: Path) -> Escritura:
    datos = json.loads(entrada.read_text(encoding="utf-8"))
    return Escritura(
        nombre=datos.get("nombre", entrada.stem),
        trazos=[Trazo(puntos=[(mm(x), mm(y)) for x, y in t]) for t in datos["trazos"]],
    )


def hoja_de_ruta(nombre: str, catalogo: bool, solido: bool) -> str:
    """El orden. Sin esto el paquete es un montón de archivos."""
    paso_catalogo = (
        "2. **Importa el catálogo comercial**, `catalogo/*.step`. Son"
        " envolventes\n   generadas desde `docs/piezas/`: exactas en las cotas"
        " que otra pieza toca\n   y toscas en el resto. Un engranaje sale como"
        " un disco sin dientes, porque\n   para saber si cabe los dientes no"
        " aportan nada. Para el render de venta se\n   importa encima el STEP"
        " del fabricante, si lo hay.\n"
        if catalogo
        else "2. *(Sin catálogo: relanza con `--group cad` para generarlo.)*\n"
    )
    paso_solido = (
        "4. **Arrastra `cartucho/cartucho.step`** si quieres la pila montada de"
        " una pieza,\n   en vez de los tres bocetos.\n"
        if solido
        else "4. *(Sin STEP del cartucho: relanza con `--group cad`.)*\n"
    )
    return f"""# Paquete de CAD · cartucho «{nombre}»

Generado con `scripts/exportar_para_cad.py`. **No se edita a mano**: se toca
el contrato o la ficha y se regenera.

## El orden

1. **Pega `variables.fs` en el Variable Studio** del documento de la
   plataforma. Es la tabla de cotas congeladas —eje, bastidor, fase, calaje—
   que comparten el compilador y el CAD. De ahí las referencian todas las
   Part Studios.

   **El flujo es de un solo sentido.** Se toca `docs/contratos.json`, se
   regenera y se pega. Lo que se edite dentro del CAD se pierde en la
   siguiente regeneración y, peor, deja de coincidir con lo que calcula el
   compilador sin que nadie se entere.

{paso_catalogo}
3. **Importa los bocetos del cartucho**, `cartucho/*.dxf`. Van **sin el
   rótulo de texto**: el `TEXT` de DXF no es una entidad de boceto y el CAD
   suelta un «no se ha podido importar la entidad desconocida». La geometría
   entra bien; el aviso confunde. Los DXF con rótulo, para el taller, salen
   del comando normal del compilador.

{paso_solido}
5. **La plataforma se dibuja dentro del CAD**, a mano y una sola vez. No sale
   de aquí a propósito: no cambia entre pedidos y tiene que seguir siendo
   paramétrica.

## Qué es de quién

| | Quién lo hace | Cómo llega al CAD |
| --- | --- | --- |
| El cartucho | El compilador, en cada pedido | Se arrastra el DXF o el STEP |
| Las piezas comerciales | Se generan desde su ficha | Se arrastra el STEP |
| La plataforma | A mano, una vez | Se dibuja dentro |
| Las cotas que comparten | `docs/contratos.json` | Se pega en el Variable Studio |

## Antes de montar

El calaje de cada brazo va en `calajes.md`. **Montar un brazo al ángulo
equivocado escribe basura**, y es un error que no se ve hasta que la máquina
dibuja. Es una constante de la máquina, no del pedido.
"""


def main(argv: list[str] | None = None) -> int:
    partes = argparse.ArgumentParser(prog="exportar_para_cad", description=__doc__)
    partes.add_argument("entrada", type=Path, help="JSON con la escritura, en mm")
    partes.add_argument("--out", type=Path, default=Path("build/cad"))
    opciones = partes.parse_args(argv)

    destino = opciones.out
    destino.mkdir(parents=True, exist_ok=True)
    escritura = leer(opciones.entrada)
    compilacion = compilar(escritura)

    # 1 · las cotas compartidas
    contratos = cargar_contratos()
    (destino / "variables.fs").write_text(featurescript(contratos), encoding="utf-8")
    (destino / "variables.csv").write_text(csv(contratos), encoding="utf-8")

    # 2 · el catálogo comercial, si hay kernel
    catalogo = False
    try:
        from emit.catalogo import cargar, escribir_catalogo

        escribir_catalogo(cargar(), destino / "catalogo")
        catalogo = True
    except ImportError:
        pass

    # 3 · los bocetos del cartucho, sin rótulo
    carpeta = destino / "cartucho"
    carpeta.mkdir(exist_ok=True)
    for pieza in compilacion.piezas:
        escribir_dxf(pieza, carpeta / f"{pieza.numero}.dxf", rotulo=False)

    # 4 · el sólido, si hay kernel y si el perfil lo admite
    #
    # Un perfil autointersecado no levanta cara y el kernel lanza. Eso **no**
    # puede llevarse por delante el paquete entero: mismo criterio que el
    # CLI, un pedido que no cabe también hay que poder mirarlo, y los
    # bocetos y las cotas siguen sirviendo aunque el sólido no salga.
    solido = False
    fallo_del_solido = ""
    try:
        from emit.step import escribir_step

        escribir_step(compilacion.piezas, carpeta / "cartucho.step")
        solido = True
    except ImportError:
        fallo_del_solido = "falta el kernel: uv sync --group cad"
    except Exception as exc:  # el kernel de OCCT lanza de todo y no documenta qué
        fallo_del_solido = f"el kernel no pudo apilar el cartucho: {type(exc).__name__}"

    # 5 · el calaje, que es lo que se monta mal
    (destino / "calajes.md").write_text(
        "# Calaje de los brazos\n\n"
        "El ángulo al que va calado cada brazo sobre el eje de su seguidor.\n"
        "**Es una constante de la máquina, no del pedido**, y montarlo mal\n"
        "escribe basura.\n\n"
        "| Brazo | Calaje |\n| --- | --- |\n"
        + "".join(
            f"| {nombre} | {valor * 180.0 / 3.141592653589793:.3f}° |\n"
            for nombre, valor in compilacion.calajes.items()
        ),
        encoding="utf-8",
    )

    (destino / "README.md").write_text(
        hoja_de_ruta(escritura.nombre, catalogo, solido), encoding="utf-8"
    )

    print(f"paquete de CAD en {destino}/")
    if not catalogo:
        print("sin catálogo comercial: falta el kernel. uv sync --group cad")
    if fallo_del_solido:
        print(f"sin STEP del cartucho: {fallo_del_solido}")
    if not compilacion.veredicto.apto:
        print("OJO: este pedido no es apto. Los archivos están, pero no se fabrica.")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
