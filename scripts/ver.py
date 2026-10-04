"""Mira una pieza o la máquina entera en el visor de VS Code.

    uv run --group cad python scripts/ver.py seguidor
    uv run --group cad python scripts/ver.py --conjunto --theta 90
    uv run --group cad python scripts/ver.py --conjunto --step build/montaje.step
    uv run --group cad python scripts/ver.py --conjunto --grupos cartucho,entre_puntos
    uv run --group cad python scripts/ver.py --conjunto --sacado 80 --vista planta

En `--conjunto` las piezas van **agrupadas por subsistema** (`emit.montaje.GRUPOS`),
cada grupo de un color y el bastidor translúcido, y se imprime la tabla de
auditoría: qué hay en cada grupo, cuánto se mueve y dónde está.

Hace falta la extensión **OCP CAD Viewer** de VS Code, con el visor
abierto (paleta de comandos → *OCP CAD Viewer: Open viewer*). Sin visor,
`--step` escribe el sólido y se abre con cualquier cosa.

**Por qué existe.** Las catorce envolventes del catálogo estuvieron mil
veces pequeñas durante días con tres tests encima, y lo que faltaba no era
otro test: era que alguien hubiera **abierto** uno de esos archivos
alguna vez. Se generaban, se guardaban y se arrastraban al CAD. Esto pone
el ojo en el bucle sin salir del editor.
"""

from __future__ import annotations

import argparse
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from emit.plataforma import LISTADO

RAIZ = Path(__file__).resolve().parent.parent


def _piezas(theta_grados: float, sacado: float = 0.0):
    """La máquina en un ángulo, con el cartucho sacado `sacado` mm por su
    pasillo si se pide: es la vista del cambio de cartucho."""
    from build123d import Pos, Rot

    from compile.conjunto import piezas_en
    from compile.escribiente import Escribiente, compilar
    from emit.montaje import grupo_de
    from emit.plataforma import contrato_mm
    from scripts.exportar_para_cad import leer

    compilacion = compilar(leer(RAIZ / "demo" / "hola.json"))
    piezas = piezas_en(compilacion, Escribiente(), math.radians(theta_grados))
    a = contrato_mm()["cartucho_salida_angulo"]
    fuera = Pos(sacado * math.cos(a), sacado * math.sin(a), 0.0)
    # El montaje vive en el marco de la leva, que mira de lado respecto de la
    # base. Para mirarlo se gira entero sobre el árbol hasta que la salida del
    # cartucho apunte a +Y: la base queda a escuadra, la mesa delante (-Y) y
    # el cambio de cartucho detrás.
    a_escuadra = Rot(Z=90.0 - math.degrees(a))
    return [
        (
            p,
            a_escuadra
            * (
                fuera * p.solido
                if sacado and grupo_de(p.nombre).nombre in ("levas", "cartucho")
                else p.solido
            ),
        )
        for p in piezas
    ]


def _conjunto(theta_grados: float):
    piezas = _piezas(theta_grados)
    return [p.nombre for p, _ in piezas], [s for _, s in piezas]


def auditoria(piezas) -> str:
    """Una línea por grupo: cuántas piezas, cuántas se mueven y la caja que
    ocupa, en mm. Es el punto de partida de la auditoría de conjunto."""
    from emit.montaje import GRUPOS, grupo_de

    filas = [
        f"{'grupo':14s} {'piezas':>6s} {'móviles':>7s}   "
        f"{'x':>15s} {'y':>15s} {'z':>15s}   objetivo"
    ]
    for g in GRUPOS:
        suyas = [(p, s) for p, s in piezas if grupo_de(p.nombre) is g]
        if not suyas:
            continue
        cajas = [s.bounding_box() for _, s in suyas]

        def tramo(eje: str, cajas=cajas) -> str:
            lo = min(getattr(c.min, eje) for c in cajas)
            hi = max(getattr(c.max, eje) for c in cajas)
            return f"{lo:7.1f}..{hi:6.1f}"

        moviles = sum(p.movil for p, _ in suyas)
        filas.append(
            f"{g.nombre:14s} {len(suyas):6d} {moviles:7d}   "
            f"{tramo('X')} {tramo('Y')} {tramo('Z')}   {g.objetivo}"
        )
    filas.append(f"{'total':14s} {len(piezas):6d} {sum(p.movil for p, _ in piezas):7d}")
    return chr(10).join(filas)


VISTAS = {"iso": "ISO", "planta": "TOP", "frente": "FRONT", "perfil": "RIGHT", "atras": "BACK"}
"""Con la máquina a escuadra (ver `_piezas`): «frente» es el lado de la mesa
y «atras» el del cambio de cartucho."""


def main(argv: list[str] | None = None) -> int:
    partes = argparse.ArgumentParser(prog="ver", description=__doc__)
    partes.add_argument("pieza", nargs="?", choices=sorted(LISTADO), help="una pieza suelta")
    partes.add_argument("--conjunto", action="store_true", help="la máquina montada")
    partes.add_argument("--theta", type=float, default=0.0, help="ángulo del árbol, en grados")
    partes.add_argument("--step", type=Path, help="escribe un STEP en vez de mostrarlo")
    partes.add_argument("--grupos", help="solo estos grupos, separados por comas")
    partes.add_argument(
        "--nivel",
        choices=("levas", "cartucho", "maquina"),
        help="solo un nivel: las levas, el cartucho entero o la máquina",
    )
    partes.add_argument("--sacado", type=float, default=0.0, help="saca el cartucho, en mm")
    partes.add_argument("--vista", choices=sorted(VISTAS), default="iso")
    op = partes.parse_args(argv)

    if not op.conjunto and op.pieza is None:
        partes.error("di qué pieza, o --conjunto")

    if op.conjunto and op.step is None:
        return _mostrar_por_grupos(op)
    if op.conjunto:
        nombres, solidos = _conjunto(op.theta)
    else:
        from emit.montaje import solido_de

        nombres, solidos = [op.pieza], [solido_de(op.pieza)]

    if op.step is not None:
        from build123d import Compound, export_step

        op.step.parent.mkdir(parents=True, exist_ok=True)
        export_step(Compound(children=solidos), str(op.step))
        print(f"{len(solidos)} sólidos en {op.step}")
        return 0

    try:
        from ocp_vscode import show
    except ImportError:
        print(
            "falta el visor: uv sync --group cad, y la extensión «OCP CAD Viewer» en VS Code.\n"
            "Mientras tanto, --step escribe el sólido en un archivo.",
            file=sys.stderr,
        )
        return 1

    try:
        show(*solidos, names=nombres)
    except Exception as fallo:
        print(
            f"el visor no respondió ({fallo}).\nAbre «OCP CAD Viewer: Open viewer» en la "
            "paleta de comandos de VS Code, o usa --step.",
            file=sys.stderr,
        )
        return 1
    print(f"{len(solidos)} sólidos en el visor")
    return 0


def _mostrar_por_grupos(op) -> int:
    """El conjunto en el visor, un nodo por grupo y su color."""
    from build123d import Compound

    from emit.montaje import GRUPOS, grupo_de

    piezas = _piezas(op.theta, op.sacado)
    print(auditoria(piezas))
    if op.nivel:
        from emit.montaje import NIVELES

        op.grupos = ",".join(NIVELES[op.nivel])
    pedidos = set(op.grupos.split(",")) if op.grupos else {g.nombre for g in GRUPOS}
    desconocidos = pedidos - {g.nombre for g in GRUPOS}
    if desconocidos:
        print(f"no hay grupos {sorted(desconocidos)}", file=sys.stderr)
        return 1
    nodos, nombres, colores, opacidades = [], [], [], []
    for g in GRUPOS:
        if g.nombre not in pedidos:
            continue
        hijos = []
        for p, solido in piezas:
            if grupo_de(p.nombre) is g:
                solido.label = p.nombre
                hijos.append(solido)
        if hijos:
            nodos.append(Compound(children=hijos, label=g.nombre))
            nombres.append(g.nombre)
            colores.append(g.color)
            opacidades.append(g.opacidad if len(pedidos) > 1 else 1.0)
    try:
        from ocp_vscode import Camera, Collapse, show

        show(
            *nodos,
            names=nombres,
            colors=colores,
            alphas=opacidades,
            reset_camera=getattr(Camera, VISTAS[op.vista]),
            collapse=Collapse.LEAVES,
            grid=(False, False, False),
            axes=False,
        )
    except Exception as fallo:
        print(f"el visor no respondió ({fallo})", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
