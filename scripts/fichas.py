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


def preparar(nombre: str):
    import numpy as np

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

    # Las marcas salen del registro (`docs/numeracion.json`), no de aquí:
    # el mismo número en la ficha, en el dossier y en el índice.
    from emit.catalogo import cargar as catalogo
    from emit.numeracion import cargar as registro_de
    from emit.numeracion import marcas
    from scripts.numeracion import COMERCIALES_COLOCADOS

    todas = marcas(registro_de())
    del_registro = sorted(
        (m for m in todas.values() if m.grupo == g.nombre), key=lambda m: (m.serie, m.numero)
    )
    piezas = tuple(
        Pieza(
            nombre=m.nombre,
            marca=m.numero,
            plano=m.codigo,
            solido=hecho[m.nombre],
            cantidad_en_el_grupo=sum(1 for p in del_grupo if base_de(p.nombre) == m.nombre),
        )
        for m in del_registro
        if m.serie == "piezas" and m.nombre in hecho
    )
    marca_de = {p.nombre: p.marca for p in piezas}
    del_catalogo = {k.nombre: k for k in catalogo()}
    por_clave = {f.clave: f for f in tornilleria()}
    comerciales = tuple(
        Comercial(
            m.codigo,
            del_catalogo[m.nombre].designacion,
            del_catalogo[m.nombre].cantidad,
            m.nombre.replace("_", " "),
        )
        for m in del_registro
        if m.serie == "comerciales"
    ) + tuple(
        Comercial(
            m.codigo,
            por_clave[m.nombre].designacion,
            por_clave[m.nombre].cantidad,
            por_clave[m.nombre].para,
        )
        for m in del_registro
        if m.serie == "tornilleria"
    )

    # Lo que está en el 3D y no es pieza, comercial ni tornillería del
    # registro: una laguna del modelo.
    prefijos_comerciales = tuple(
        pre for nombre, pre in COMERCIALES_COLOCADOS.items() if ("comerciales", nombre) in todas
    )
    # Lo que está dibujado y no lleva ficha a propósito: la tornillería va en
    # su tabla (cada línea dice qué pieza la dibuja), y las levas son de cada
    # pedido (plantillas.pdf).
    dibujadas_sin_ficha = ("leva_", *{f.en_3d for f in tornilleria() if f.en_3d})
    sin_ficha = tuple(
        sorted(
            {
                p.nombre.rstrip("_0123456789")
                for p in del_grupo
                if not base_de(p.nombre)
                and not p.nombre.startswith(prefijos_comerciales)
                and not p.nombre.startswith(dibujadas_sin_ficha)
            }
        )
    )

    # El despiece: el grupo entero, explosionado como declara
    # `emit.explosion.EXPLOSIONES`, en el orden de las marcas.
    from emit.explosion import explosionar_grupo

    despiece = tuple(
        explosionar_grupo([(p.nombre, p.solido) for p in del_grupo], g.nombre, marca_de, base_de)
    )
    # El despiece explosionado pieza a pieza, la hoja 2.
    from emit.despiece import despiece as explosionado

    explosion = explosionado(
        tuple((p.nombre, p.solido) for p in colocadas), g.nombre, todas, COMERCIALES_COLOCADOS
    )
    return FichasDeGrupo(
        grupo=g,
        piezas=piezas,
        comerciales=comerciales,
        sin_ficha=sin_ficha,
        contexto=tuple((p.nombre, p.solido) for p in colocadas),
        despiece=despiece,
        contrato=c,
        explosion=explosion,
        leyenda=leyenda_de(explosion, todas),
    )


def leyenda_de(explosion, marcas) -> tuple[tuple[str, str, int], ...]:
    """(número, qué es, cuántas) de cada número del despiece explosionado:
    lo fabricado y lo comprado por su nombre; la tornillería, por su
    designación."""
    from collections import Counter

    from emit.despiece import marcas_de
    from scripts.numeracion import COMERCIALES_COLOCADOS

    cuantas = Counter(e.texto for e in explosion.etiquetas)
    que: dict[str, str] = {}
    for e in explosion.etiquetas:
        nombres = [
            m.nombre.split(" · ")[0] if m.serie == "tornilleria" else m.nombre
            for m in marcas_de(e.nombre, marcas, COMERCIALES_COLOCADOS)
        ]
        que.setdefault(e.texto, " + ".join(nombres))

    def orden(texto: str) -> tuple[int, int, str]:
        serie = {"C": 1, "T": 2}.get(texto[0], 0 if texto[0].isdigit() else 3)
        cifras = "".join(ch for ch in texto.split(",")[0] if ch.isdigit())
        return (serie, int(cifras or 0), texto)

    return tuple((t, que[t], cuantas[t]) for t in sorted(cuantas, key=orden))


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
