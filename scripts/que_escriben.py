"""Qué escriben las levas de hoy, leídas por el perfil que se va a cortar.

    uv run python scripts/que_escriben.py [--muestras 720]

Para el pedido de ejemplo (demo/hola.json) y los cuatro casos de
tests/casos.py dice, recorriendo las levas por su **perfil cortado**
(`compile.recorrido`): el error máximo y medio del trazo contra lo que pidió
el cliente, cuántos trazos y vuelos hay, qué fracción de la vuelta escribe y
cuánto tarda la frase. Al lado va lo mismo leído por la **curva de paso**
(`compile.escribiente.simular`), que es lo que decide hoy si un pedido sale:
si los dos caminos discrepan, uno de los dos miente.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

RAIZ = Path(__file__).resolve().parent.parent


def casos() -> dict[str, object]:
    from scripts.exportar_para_cad import leer
    from tests.casos import CASOS

    return {"demo/hola.json": leer(RAIZ / "demo" / "hola.json")} | {
        f"casos.{n}": f() for n, f in CASOS.items()
    }


def informe(muestras: int = 720) -> list[dict[str, object]]:
    from compile.energia import relacion_del_contrato, rpm_del_arbol
    from compile.escribiente import Escribiente, compilar
    from compile.recorrido import recorrer

    maquina = Escribiente()
    filas: list[dict[str, object]] = []
    for nombre, escritura in casos().items():
        compilacion = compilar(escritura, maquina)  # type: ignore[arg-type]
        fila: dict[str, object] = {
            "caso": nombre,
            "apto": compilacion.veredicto.apto,
            "errores": [i.codigo for i in compilacion.veredicto.errores],
            "trazos_pedidos": len(compilacion.escritura.trazos),
        }
        if not compilacion.perfiles or compilacion.simulacion is None:
            fila["recorrido"] = None
            filas.append(fila)
            continue
        r = recorrer(compilacion, maquina, muestras)
        trazos, vuelos = r.tramos()
        fila |= {
            "recorrido": r,
            "contacto_max_mm": r.error_maximo * 1000.0,
            "contacto_medio_mm": r.error_medio * 1000.0,
            "paso_max_mm": compilacion.simulacion.error_maximo * 1000.0,
            "paso_medio_mm": compilacion.simulacion.error_medio * 1000.0,
            "trazos": trazos,
            "vuelos": vuelos,
            "escribe": r.fraccion_escribiendo,
            "segundos": 60.0 / rpm_del_arbol(),
            "rpm_manivela": rpm_del_arbol() * relacion_del_contrato(),
        }
        filas.append(fila)
    return filas


def main(argv: list[str] | None = None) -> int:
    sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[union-attr]
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--muestras", type=int, default=720, help="ángulos por vuelta")
    op = p.parse_args(argv)
    for f in informe(op.muestras):
        print(
            f"\n== {f['caso']}  ({'apto' if f['apto'] else 'NO apto: ' + ', '.join(f['errores'])})"
        )  # type: ignore[arg-type]
        if f["recorrido"] is None:
            print("   sin levas que recorrer: el compilador no llegó a sintetizarlas")
            continue
        print(
            f"   error del trazo, perfil cortado: máx {1000 * f['contacto_max_mm']:.1f} µm, "  # type: ignore[operator]
            f"medio {1000 * f['contacto_medio_mm']:.1f} µm"  # type: ignore[operator]
        )
        print(
            f"   error del trazo, curva de paso:  máx {1000 * f['paso_max_mm']:.1f} µm, "  # type: ignore[operator]
            f"medio {1000 * f['paso_medio_mm']:.1f} µm   (contra los puntos: mide su separación)"  # type: ignore[operator]
        )
        print(
            f"   {f['trazos']} trazos y {f['vuelos']} vuelos (el pedido tiene "
            f"{f['trazos_pedidos']} trazos); escribe el {100 * f['escribe']:.1f} % de la vuelta"  # type: ignore[operator]
        )
        print(
            f"   la frase entera: {f['segundos']:.2f} s, una vuelta del árbol a "
            f"{f['rpm_manivela']:.0f} rpm de manivela con la reducción 3:1"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
