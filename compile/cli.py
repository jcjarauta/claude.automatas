"""Un pedido, un comando.

    uv run python -m compile.cli demo/hola.json --out build/

Entrada: un JSON con la escritura ya capturada, en milímetros. Salida, en la
carpeta que se diga: el informe, las plantillas 1:1 para copistería y un DXF
por leva para quien tenga corte digital.

El código de salida es 1 si el veredicto es negativo. Así un script sabe que
ese pedido no se fabrica, sin leer el informe. Los archivos se escriben
igualmente: un pedido que no cabe también hay que poder mirarlo.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from compile.conjunto import montar
from compile.coste import PrecioCerrado, cargar_precios, valorar
from compile.energia import Accionamiento, analizar
from compile.escribiente import Escribiente, compilar
from compile.informe import escribir_informe, resumen
from core.energy.humano import Transmision
from core.escritura import Capacidad, Escritura, Trazo
from core.units import mm
from emit.dxf import Kerf, escribir_dxfs
from emit.paquete import escribir_paquete
from emit.step import disponible as hay_kernel
from emit.step import escribir_step

KERF = Path("bench/kerf.json")
PRECIOS = Path("bench/precios.json")


def leer_escritura(ruta: Path | str) -> Escritura:
    """Lee el JSON de captura. Coordenadas en **milímetros**, como las manda
    el cliente; a metros se pasa aquí, en la frontera."""
    datos = json.loads(Path(ruta).read_text(encoding="utf-8"))
    return Escritura(
        nombre=datos["nombre"],
        trazos=[
            Trazo(puntos=[(mm(float(x)), mm(float(y))) for x, y in trazo])
            for trazo in datos["trazos"]
        ],
    )


def escribir_programa(escritura_json: dict[str, object], destino: Path) -> Path:
    ruta = destino / "programa.json"
    ruta.write_text(
        json.dumps(escritura_json, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    return ruta


def main(argv: list[str] | None = None) -> int:
    partes = argparse.ArgumentParser(prog="compile.cli", description=__doc__)
    partes.add_argument("entrada", type=Path, help="JSON con la escritura, en mm")
    partes.add_argument("--out", type=Path, default=Path("build"), help="carpeta de salida")
    partes.add_argument("--muestras", type=int, default=720, help="muestras por vuelta")
    partes.add_argument("--rpm", type=float, default=30.0, help="a cuánto se piensa girar")
    partes.add_argument(
        "--relacion-manivela",
        type=float,
        default=1.0,
        help="vueltas de manivela por vuelta del árbol",
    )
    partes.add_argument("--sin-dxf", action="store_true", help="solo papel")
    partes.add_argument(
        "--corte",
        type=float,
        default=None,
        help="lo que cobra el taller por el bloque de tres levas, si no es el de bench/",
    )
    partes.add_argument(
        "--step",
        action="store_true",
        help="además, el cartucho en 3-D para arrastrar a un CAD (necesita --group cad)",
    )
    partes.add_argument(
        "--dxf-para-cad",
        action="store_true",
        help="DXF sin el rótulo de texto, para importar a un CAD sin avisos",
    )
    opciones = partes.parse_args(argv)

    escritura = leer_escritura(opciones.entrada)
    maquina = Escribiente()
    compilacion = compilar(escritura, maquina, Capacidad(muestras=opciones.muestras))

    accionamiento = Accionamiento(
        transmision=Transmision(relacion=opciones.relacion_manivela),
        vueltas_por_minuto=opciones.rpm,
    )
    montaje = None
    veredicto_montaje = None
    energia = None
    veredicto_energia = None
    valoracion = None
    if compilacion.perfiles:
        montaje, veredicto_montaje = montar(compilacion, maquina)
        energia, veredicto_energia = analizar(compilacion, montaje.inercia, accionamiento)
        if PRECIOS.exists():
            corte = (
                PrecioCerrado(euros_por_bloque=opciones.corte, cerrado=True)
                if opciones.corte is not None
                else None
            )
            valoracion = valorar(compilacion, maquina, cargar_precios(PRECIOS), corte=corte)

    destino: Path = opciones.out
    destino.mkdir(parents=True, exist_ok=True)
    escribir_informe(
        compilacion,
        maquina,
        destino / "informe.md",
        montaje,
        veredicto_montaje,
        energia,
        veredicto_energia,
        accionamiento,
        valoracion,
    )
    escribir_programa(
        json.loads(compilacion.programa.model_dump_json()),
        destino,
    )

    if compilacion.piezas:
        escribir_paquete(compilacion.piezas, destino)
        if not opciones.sin_dxf:
            kerf = Kerf.desde(KERF) if KERF.exists() else Kerf()
            escribir_dxfs(compilacion.piezas, destino, kerf, rotulo=not opciones.dxf_para_cad)
        if opciones.step:
            if hay_kernel():
                escribir_step(compilacion.piezas, destino / "cartucho.step")
            else:
                print("sin STEP: falta el kernel. Instálalo con  uv sync --group cad")

    print(resumen(compilacion))
    if valoracion is not None:
        aviso = "" if valoracion.precio_cerrado else " (previsión)"
        print(
            f"cartucho {valoracion.cartucho:.2f} €{aviso} "
            f"+ plataforma {valoracion.plataforma:.2f} € "
            f"= {valoracion.total:.2f} €"
        )
    if veredicto_montaje is not None and not veredicto_montaje.apto:
        for incidencia in veredicto_montaje.errores:
            print(f"  [conjunto] {incidencia.mensaje}")
    print(f"escrito en {destino}/")
    apto = (
        compilacion.veredicto.apto
        and (veredicto_montaje is None or veredicto_montaje.apto)
        and (veredicto_energia is None or veredicto_energia.apto)
    )
    return 0 if apto else 1


if __name__ == "__main__":
    sys.exit(main())
