"""Las fichas de fabricación de un grupo: ficha de grupo y una por pieza.

    uv run --group cad python scripts/fichas.py amplificador
    uv run --group cad python scripts/fichas.py amplificador --out build/fichas_amplificador.pdf

Es la **muestra** del dossier de fabricación (`emit.fichas`): un grupo entero,
para decidir el formato antes de sacar todos. La máquina se coloca en fase
cero con el pedido de referencia, «hola», porque la ficha de grupo enseña
dónde va el grupo y eso pide la máquina montada; las fichas de pieza no
dependen del pedido.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

RAIZ = Path(__file__).resolve().parent.parent

EXPLOSION = 14.0
"""mm que sube cada pieza sobre la anterior en el despiece."""


def preparar(nombre: str):
    import numpy as np
    from build123d import Pos

    from compile.conjunto import estados
    from compile.escribiente import SEGUIDORES, Escribiente, compilar
    from compile.renglones import leer_pedido
    from emit.fichas import Comercial, FichasDeGrupo, Pieza, base_de, grupo
    from emit.materiales import tornilleria
    from emit.montaje import colocar, grupo_de, taller
    from emit.plataforma import contrato_mm

    c = contrato_mm()
    maquina = Escribiente()
    compilacion = compilar(leer_pedido(RAIZ / "demo" / "hola.json").escritura, maquina)
    estado = estados(compilacion, maquina, np.array([0.0]), camino="contacto")[0]
    seguidores = [maquina.seguidor(i) for i in range(len(SEGUIDORES))]
    hecho = taller(c)
    colocadas = colocar(list(compilacion.piezas), seguidores, estado, c, hecho)
    g = grupo(nombre)
    del_grupo = [p for p in colocadas if grupo_de(p.nombre) is g]

    # Las piezas fabricadas, por orden de montaje: de abajo arriba.
    claves: list[str] = []
    for p in sorted(del_grupo, key=lambda p: (p.solido.bounding_box().min.Z, p.nombre)):
        clave = base_de(p.nombre)
        if clave and clave in hecho and clave not in claves:
            claves.append(clave)
    sigla = g.nombre[:3].upper()
    piezas = tuple(
        Pieza(
            nombre=clave,
            marca=marca,
            plano=f"P-{sigla}-{marca:02d}",
            solido=hecho[clave],
            cantidad_en_el_grupo=sum(1 for p in del_grupo if base_de(p.nombre) == clave),
        )
        for marca, clave in enumerate(claves, start=1)
    )
    marca_de = {p.nombre: p.marca for p in piezas}

    # Lo que está en el 3D y no es pieza fabricada: comercial o laguna.
    sueltas = sorted({p.nombre.rstrip("_0123456789") for p in del_grupo if not base_de(p.nombre)})
    sin_ficha = tuple(n for n in sueltas if not n.startswith("tornillo"))
    # La palabra que nombra cada pieza en la tornillería: la última de su
    # clave (`calzo_sector` es un «sector», `eje_pivote` un «pivote»).
    palabras = {k.rsplit("_", 1)[-1] for k in claves} | set(sin_ficha)
    comerciales = tuple(
        Comercial(f.designacion, f.cantidad, f.para)
        for f in tornilleria()
        if any(palabra in f.para for palabra in palabras)
    )

    # El despiece: el grupo entero, cada pieza fabricada subida sobre la
    # anterior.
    canal = [p for p in del_grupo if base_de(p.nombre) in marca_de]
    canal.sort(key=lambda p: (p.solido.bounding_box().min.Z, p.nombre))
    despiece = tuple(
        (marca_de[base_de(p.nombre)], p.nombre, Pos(0, 0, k * EXPLOSION) * p.solido)
        for k, p in enumerate(canal)
    )
    return FichasDeGrupo(
        grupo=g,
        piezas=piezas,
        comerciales=comerciales,
        sin_ficha=sin_ficha,
        contexto=tuple((p.nombre, p.solido) for p in colocadas),
        despiece=despiece,
        contrato=c,
    )


def main(argv: list[str] | None = None) -> int:
    from emit.fichas import escribir_fichas

    sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[union-attr]
    p = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    p.add_argument("grupo", help="nombre del grupo, como en emit.montaje.GRUPOS")
    p.add_argument("--out", type=Path, default=None)
    op = p.parse_args(argv)
    destino = op.out or RAIZ / "build" / f"fichas_{op.grupo}.pdf"
    fichas = preparar(op.grupo)
    from scripts.dossier import _version

    escribir_fichas(fichas, destino, _version())
    print(
        f"{destino}: ficha del grupo {op.grupo} y {len(fichas.piezas)} de pieza; "
        f"{len(fichas.comerciales)} comerciales; sin ficha: {', '.join(fichas.sin_ficha) or 'nada'}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
