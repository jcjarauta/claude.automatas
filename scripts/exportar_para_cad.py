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
import csv as _csv
import io
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from compile.contratos import cargar as cargar_contratos
from compile.escribiente import compilar
from core.escritura import Escritura, Trazo
from core.solido import DENSIDADES
from core.units import mm
from emit.catalogo import cargar as cargar_piezas
from emit.dxf import escribir_dxf
from scripts.exportar_variables import csv, featurescript


def leer(entrada: Path) -> Escritura:
    datos = json.loads(entrada.read_text(encoding="utf-8"))
    return Escritura(
        nombre=datos.get("nombre", entrada.stem),
        trazos=[Trazo(puntos=[(mm(x), mm(y)) for x, y in t]) for t in datos["trazos"]],
    )


CABECERA_PIEZAS = ("nombre", "valor", "unidad", "pieza", "critica", "tolerancia", "designacion")

UNIDAD_A_SUFIJO = {"mm": "cota", "deg": "angulo", "": "num"}
"""Qué archivo se lleva cada unidad. Los nombres son los de la variable que
se crea en el CAD: `#cota.radio_base`, `#angulo.calaje_izquierdo`."""


def por_unidad(tabla: str) -> dict[str, str]:
    """Parte la tabla de variables en un archivo por unidad.

    **El CAD aplica un único factor de conversión a todo el archivo que
    importa**, y estas 29 cotas mezclan 20 longitudes en mm, 5 ángulos en
    grados y 3 números sin unidad —la relación del varillaje, la del
    reductor y el sentido de giro—. Con un solo archivo, o los ángulos
    entran como milímetros o las longitudes como grados.

    Partirlo aquí y no allí no es comodidad: es que **el que sabe de qué
    unidad es cada cota es el contrato**, y dejar que alguien lo decida
    marcando casillas en una interfaz es pedir un error silencioso. Un
    calaje interpretado como milímetros no da un aviso, da una máquina que
    escribe torcido.
    """
    filas = list(_csv.reader(io.StringIO(tabla)))[1:]
    salida: dict[str, list[list[str]]] = {s: [] for s in UNIDAD_A_SUFIJO.values()}
    for fila in filas:
        if not fila:
            continue
        sufijo = UNIDAD_A_SUFIJO.get(fila[2])
        if sufijo is None:
            raise ValueError(
                f"la cota '{fila[0]}' usa la unidad '{fila[2]}', que no sabe a qué "
                f"archivo va. Añádela a UNIDAD_A_SUFIJO."
            )
        salida[sufijo].append(fila)
    return {s: _volcar(con_gemelos(v)) for s, v in salida.items() if v}


def con_gemelos(filas: list[list[str]]) -> list[list[str]]:
    """Añade la otra mitad de cada cota circular: el diámetro de un radio y
    el radio de un diámetro.

    **Onshape acota el diámetro por defecto**, y de las siete cotas
    circulares del contrato cuatro son radio y tres diámetro. Meter
    `#cota.radio_base` en una cota de diámetro da una leva de 27,5 mm en vez
    de 55: la mitad, y sin un solo aviso. Pasó en la primera prueba.

    Se podría resolver cambiando cada cota a radio con el botón derecho, o
    escribiendo `* 2` donde toque. Las dos cosas son disciplina, y la
    disciplina falla una vez de cada veinte. **Teniendo las dos formas no hay
    nada que recordar**: se escribe la que pida el campo y el nombre dice
    cuál es. Son siete filas de más.

    Es el mismo patrón que el pasador de índice del cartucho: no hacer el
    error improbable, hacerlo imposible.
    """
    salida: list[list[str]] = []
    for fila in filas:
        salida.append(fila)
        nombre, valor = fila[0], fila[1]
        if "radio" in nombre:
            gemelo, factor = f"{nombre}_diametro", 2.0
        elif "diametro" in nombre:
            gemelo, factor = f"{nombre}_radio", 0.5
        else:
            continue
        derivada = list(fila)
        derivada[0] = gemelo
        derivada[1] = f"{float(valor) * factor:.4f}"
        derivada[-1] = f"derivada de {nombre} — {fila[-1]}"
        salida.append(derivada)
    return salida


def _volcar(filas: list[list[str]]) -> str:
    """Filas a CSV, **sin cabecera**.

    El Variable Studio lee «todos los valores» sin saber que la primera fila
    es un rótulo, así que la cabecera entraría en el mapa como una clave
    `nombre` cuyo valor es el texto `valor`. Con un factor de conversión
    puesto, multiplicar ese texto por 1 mm no da una clave rara: **hace
    fallar la regeneración de toda la variable**, y el error que sale no
    menciona la cabecera por ningún lado.
    """
    salida = io.StringIO()
    escritor = _csv.writer(salida, lineterminator="\n", quoting=_csv.QUOTE_MINIMAL)
    escritor.writerows(filas)
    return salida.getvalue()


def materiales() -> str:
    """La tabla de densidades, para montar la biblioteca de materiales del CAD.

    **Va aquí y no en el CAD porque es la misma tabla con la que el
    compilador calcula la masa.** Si las dos no coinciden, la masa que dé el
    CAD y la que dé `core/solido.py` discreparán sin que nadie sepa cuál
    miente, y se pierde la comprobación por dos caminos, que es justo lo que
    hace valiosa la biblioteca.

    No es el formato de Onshape: su biblioteca lleva además módulo de Young,
    Poisson y límites elásticos. Se exporta la suya, se pegan estas filas y
    se reimporta.
    """
    # Sin línea de comentario: un CSV que se importa en el CAD no tiene
    # dónde poner un comentario, y un «#» al principio entra como una fila
    # más y ensucia el mapa. El aviso vive en el README.
    # Las tres columnas que pide Onshape, con ese rótulo exacto: es el
    # formato de su «Descargar ejemplo» y la importación no perdona otro.
    salida = io.StringIO()
    escritor = _csv.writer(salida, lineterminator="\n", quoting=_csv.QUOTE_MINIMAL)
    escritor.writerow(("Category", "Name", "Density [kg/m^3]"))
    categoria = {
        "POM": "Plástico",
        "PMMA": "Plástico",
        "iglidur": "Plástico",
        "contrachapado de abedul": "Madera",
        "nogal": "Madera",
        "DM": "Madera",
        "aluminio": "Metal",
        "latón": "Metal",
        "acero": "Metal",
        "acero inoxidable": "Metal",
    }
    for nombre, densidad in sorted(DENSIDADES.items()):
        escritor.writerow((categoria.get(nombre, "Otro"), nombre, f"{densidad:.0f}"))
    return salida.getvalue()


def cotas_comerciales() -> str:
    """Las cotas de interfaz de las piezas que se compran, como variables.

    Con esto una pieza comercial se puede dibujar **paramétrica** en el CAD
    en vez de importarse como un sólido mudo, y sigue mandando la ficha: si
    cambia el casquillo, cambia el JSON, se regenera y el modelo se mueve
    solo. Un STEP importado no hace eso.

    Lleva las críticas primero porque son las que otra pieza toca, y son las
    únicas que hay que acotar con cuidado.

    Además de las cotas de la ficha salen las **derivadas que el CAD pide y
    la ficha no guarda**: hoy solo el número de dientes de los engranajes.
    La ficha guarda el diámetro exterior, que es lo que se mide con el pie
    de rey sobre la pieza que llega; el FeatureScript pide Z. Si la cuenta
    hay que hacerla de cabeza rellenando un formulario, se hace mal: ya
    salió un piñón de 25 dientes en vez de 20.
    """
    salida = io.StringIO()
    escritor = _csv.writer(salida, lineterminator="\n", quoting=_csv.QUOTE_MINIMAL)
    escritor.writerow(CABECERA_PIEZAS)
    for pieza in cargar_piezas():
        for cota in sorted(pieza.cotas, key=lambda c: (not c.critica, c.nombre)):
            escritor.writerow(
                (
                    f"{pieza.nombre}_{cota.nombre}",
                    f"{float(cota.valor) * 1000:.4f}",
                    "mm",
                    pieza.nombre,
                    "si" if cota.critica else "no",
                    cota.tolerancia,
                    pieza.designacion,
                )
            )
        # Sin unidad a propósito: es un recuento y va a `piezas_num.csv`.
        # Con el factor en milímetros saldrían veinte milímetros de dientes.
        dientes = pieza.dientes
        if dientes is not None:
            escritor.writerow(
                (
                    f"{pieza.nombre}_dientes",
                    str(dientes),
                    "",
                    pieza.nombre,
                    "si",
                    "",
                    f"derivada de exterior/modulo - 2 — {pieza.designacion}",
                )
            )
    return salida.getvalue()


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
        else "4. *(Sin catálogo: relanza con `--group cad` para generarlo.)*\n"
    )
    paso_solido = (
        "6. **Arrastra `cartucho/cartucho.step`** si quieres la pila montada de"
        " una pieza,\n   en vez de los tres bocetos.\n"
        if solido
        else "6. *(Sin STEP del cartucho: relanza con `--group cad`.)*\n"
    )
    return f"""# Paquete de CAD · cartucho «{nombre}»

Generado con `scripts/exportar_para_cad.py`. **No se edita a mano**: se toca
el contrato o la ficha y se regenera.

## El orden

1. **Monta la biblioteca de materiales** con `materiales.csv`. Es la misma
   tabla de densidades con la que el compilador calcula la masa, así que si
   las dos coinciden se puede contrastar lo que pesa el modelo contra lo que
   dice `core/solido.py` —por dos caminos que no comparten una línea de
   código— y si no coinciden, la comprobación se pierde en silencio.

2. **Importa `variables.csv` en un Variable Studio.** Son las cotas
   congeladas —eje, bastidor, fase, calaje— que comparten el compilador y el
   CAD. De ahí las referencian todas las Part Studios.

   **El flujo es de un solo sentido.** Se toca `docs/contratos.json`, se
   regenera y se vuelve a importar. Lo que se edite dentro del CAD se pierde
   en la siguiente regeneración y, peor, deja de coincidir con lo que calcula
   el compilador sin que nadie se entere.

3. **Importa `piezas.csv`** si vas a dibujar las piezas comerciales
   paramétricas en vez de importar sus STEP. Son las cotas de interfaz de
   `docs/piezas/`, y con ellas un cambio de referencia mueve el modelo solo.
   Un STEP importado no hace eso.

   **El flujo es de un solo sentido.** Se toca `docs/contratos.json`, se
   regenera y se pega. Lo que se edite dentro del CAD se pierde en la
   siguiente regeneración y, peor, deja de coincidir con lo que calcula el
   compilador sin que nadie se entere.

{paso_catalogo}
5. **Importa los bocetos del cartucho**, `cartucho/*.dxf`. Van **sin el
   rótulo de texto**: el `TEXT` de DXF no es una entidad de boceto y el CAD
   suelta un «no se ha podido importar la entidad desconocida». La geometría
   entra bien; el aviso confunde. Los DXF con rótulo, para el taller, salen
   del comando normal del compilador.

{paso_solido}
7. **La plataforma se dibuja dentro del CAD**, a mano y una sola vez. No sale
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
    entero = csv(contratos)
    (destino / "variables.csv").write_text(entero, encoding="utf-8")
    for sufijo, contenido in por_unidad(entero).items():
        (destino / f"variables_{sufijo}.csv").write_text(contenido, encoding="utf-8")

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

    # 5 · la tabla de materiales, para la biblioteca del CAD
    (destino / "materiales.csv").write_text(materiales(), encoding="utf-8")

    # 6 · las cotas de las piezas comerciales, para poder dibujarlas
    #     paramétricas en vez de importarlas como sólidos mudos
    comerciales = cotas_comerciales()
    (destino / "piezas.csv").write_text(comerciales, encoding="utf-8")
    for sufijo, contenido in por_unidad(comerciales).items():
        (destino / f"piezas_{sufijo}.csv").write_text(contenido, encoding="utf-8")

    # 7 · el calaje, que es lo que se monta mal
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
