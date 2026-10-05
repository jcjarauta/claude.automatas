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
from compile.energia import Accionamiento, analizar, relacion_del_contrato, rpm_del_arbol
from compile.escribiente import Compilacion, Escribiente, compilar
from compile.informe import escribir_informe, resumen
from compile.renglones import compilar_por_renglones, leer_pedido
from compile.tarjetas import cargar_tarjeta, maquina_para
from compile.tolerancias import presupuesto_de_error
from compile.version import version_del_repositorio
from core.energy.humano import Transmision
from core.escritura import Capacidad, Escritura, Trazo
from core.tarjeta import Tarjeta
from core.units import mm
from emit.dxf import Kerf, escribir_dxfs
from emit.paquete import escribir_paquete
from emit.patron import escribir_patron, patron_de
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
    partes.add_argument(
        "--muestras",
        type=int,
        default=None,
        help="muestras por vuelta; por defecto las elige la frase (720, 1440 o 2880)",
    )
    # Los dos por defecto salen del CONTRATO y no de un literal: la máquina
    # lleva reductor 3:1 y se gira a 90 rpm en la manivela, y con 1:1 y 30
    # el informe de cada pedido pedía un volante que ya está decidido.
    partes.add_argument(
        "--rpm",
        type=float,
        default=rpm_del_arbol(),
        help="a cuánto gira el ÁRBOL; por defecto lo que dice el contrato",
    )
    partes.add_argument(
        "--relacion-manivela",
        type=float,
        default=relacion_del_contrato(),
        help="vueltas de manivela por vuelta del árbol; por defecto, el contrato",
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

    pedido = leer_pedido(opciones.entrada)
    # La tarjeta la trae el pedido, no la línea de órdenes: es parte de lo
    # que se encarga. Y tiene que entrar AQUÍ, porque esta máquina es la que
    # usan la hoja patrón y el presupuesto además del compilador.
    tarjeta = None if pedido.tarjeta is None else cargar_tarjeta(pedido.tarjeta)
    maquina = Escribiente() if tarjeta is None else maquina_para(tarjeta)
    capacidad = None if opciones.muestras is None else Capacidad(muestras=opciones.muestras)
    if pedido.renglones is None:
        trabajos = [(compilar(pedido.escritura, maquina, capacidad), opciones.out)]
    else:
        # Un cartucho por renglón, cada uno en su carpeta, todos a la misma
        # escala y con los mismos calajes (compile.renglones).
        compilaciones = compilar_por_renglones(
            pedido.escritura, pedido.renglones, maquina, capacidad
        )
        trabajos = [
            (c, opciones.out / f"renglon_{numero}")
            for numero, c in enumerate(compilaciones, start=1)
        ]
    aptos = [_cartucho(c, maquina, destino, opciones, tarjeta) for c, destino in trabajos]
    return 0 if all(aptos) else 1


def _cartucho(
    compilacion: Compilacion,
    maquina: Escribiente,
    destino: Path,
    opciones: argparse.Namespace,
    tarjeta: Tarjeta | None = None,
) -> bool:
    """Informe, programa, patrón y piezas de un cartucho. Devuelve si es apto."""
    accionamiento = Accionamiento(
        transmision=Transmision(relacion=opciones.relacion_manivela),
        vueltas_por_minuto=opciones.rpm,
    )
    montaje = None
    veredicto_montaje = None
    energia = None
    veredicto_energia = None
    valoracion = None
    presupuesto = None
    if compilacion.perfiles:
        montaje, veredicto_montaje = montar(compilacion, maquina)
        presupuesto = presupuesto_de_error(compilacion, maquina)
        energia, veredicto_energia = analizar(compilacion, montaje.inercia, accionamiento)
        if PRECIOS.exists():
            corte = (
                PrecioCerrado(euros_por_bloque=opciones.corte, cerrado=True)
                if opciones.corte is not None
                else None
            )
            valoracion = valorar(compilacion, maquina, cargar_precios(PRECIOS), corte=corte)

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
        presupuesto,
        tarjeta,
    )
    escribir_programa(
        json.loads(compilacion.programa.model_dump_json()),
        destino,
    )

    if compilacion.simulacion is not None:
        ancho = float(maquina.caja_ancho) * 1000.0
        alto = float(maquina.caja_alto) * 1000.0
        centro_y = float(maquina.caja_centro_y) * 1000.0
        escribir_patron(
            patron_de(
                nombre=compilacion.escritura.nombre,
                puntos=compilacion.simulacion.puntos,
                altura=compilacion.simulacion.altura,
                caja=(-ancho / 2.0, centro_y - alto / 2.0, ancho, alto),
                error_del_modelo=compilacion.simulacion.error_maximo * 1000.0,
            ),
            destino / "patron.pdf",
            peor_caso=None if presupuesto is None else presupuesto.peor_caso * 1000.0,
            version=version_del_repositorio(),
        )

    if compilacion.piezas:
        escribir_paquete(compilacion.piezas, destino, version=version_del_repositorio())
        if not opciones.sin_dxf:
            kerf = Kerf.desde(KERF) if KERF.exists() else Kerf()
            escribir_dxfs(compilacion.piezas, destino, kerf, rotulo=not opciones.dxf_para_cad)
        if opciones.step:
            if hay_kernel():
                escribir_step(compilacion.piezas, destino / "cartucho.step")
            else:
                print("sin STEP: falta el kernel. Instálalo con  uv sync --group cad")

    print(resumen(compilacion))
    if presupuesto is not None:
        print(
            f"error esperado en la punta: {presupuesto.peor_caso * 1000:.2f} mm en el peor "
            f"caso, {presupuesto.cuadratica * 1000:.2f} mm cuadrático"
        )
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
    return (
        compilacion.veredicto.apto
        and (veredicto_montaje is None or veredicto_montaje.apto)
        and (veredicto_energia is None or veredicto_energia.apto)
    )


if __name__ == "__main__":
    sys.exit(main())
