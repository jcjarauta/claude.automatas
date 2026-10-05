"""Diagnóstico: ¿se puede dibujar cada pieza desde cero con lo que acota su ficha?

    uv run --group cad python scripts/dibujable.py          # recuento por grupo
    uv run --group cad python scripts/dibujable.py --todo   # cada falta

Cruza el perfil de cada pieza —la lista de Arco y Segmento que va al DXF—
con lo que su ficha acota hoy (`emit.fichas`): cada arco necesita su radio
y su centro situado; cada tramo recto, su longitud o la declaración de
tangencia; cada cara plana, distancia, cuerda y ángulo con signo; y cada
cota del dibujo, su variable. Lo que falta sale con el nombre de la pieza.

Es un diagnóstico y no un test: el test llega cuando las fichas lo cubran
(docs/propuesta_dossier.md).
"""

from __future__ import annotations

import argparse
import math
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

TOLERANCIA = 0.011
"""mm: dos medidas son la misma si no difieren más que esto."""


def _cerca(a: tuple[float, float], b: tuple[float, float]) -> bool:
    return math.dist(a, b) < 0.02


def faltas_de(nombre: str, c: dict[str, float], hecho: dict[str, Any]) -> list[str]:
    """Lo que la ficha de una pieza no da para dibujarla."""
    from emit.fichas import _clase_de_extension, rasgos, variable_de, vista_de_pieza
    from emit.plataforma import LISTADO, Arco
    from scripts.dibujar_pieza import PERFIL_DE

    ficha = LISTADO[nombre]
    if nombre not in PERFIL_DE:
        return ["sin perfil en dibujar_pieza.PERFIL_DE"]
    solido = hecho.get(nombre)
    if solido is None:
        return ["sin sólido en el taller: la ficha no se puede generar"]
    perfil = PERFIL_DE[nombre](c)
    r = rasgos(solido)
    radios = [a.r for a in r.contorno] + [t.diametro / 2 for t in r.taladros]
    centros = [(0.0, 0.0)] + [(t.cx, t.cy) for t in r.taladros]
    x0, y0, x1, y1 = vista_de_pieza(solido, "planta").caja()
    ancho, alto = x1 - x0, y1 - y0
    arcos = [e for e in perfil if isinstance(e, Arco)]

    faltas = []
    for e in perfil:
        if isinstance(e, Arco):
            donde = f"R{e.radio:.3g} en ({e.centro[0]:.3g}, {e.centro[1]:.3g})"
            if not any(abs(e.radio - x) < TOLERANCIA for x in radios):
                faltas.append(f"arco {donde}: sin cota de radio")
            if not any(_cerca(e.centro, ce) for ce in centros):
                faltas.append(f"arco {donde}: centro sin situar")
            elif not _cerca(e.centro, (0.0, 0.0)) and not any(
                _cerca(e.centro, (t.cx, t.cy)) and abs(t.diametro / 2 - e.radio) < 0.02
                for t in r.taladros
            ):
                faltas.append(f"arco {donde}: centro situado solo por coincidir con un taladro")
            continue
        largo = math.dist(e.a, e.b)
        es_cuerda = any(
            abs(math.dist(e.a, a.centro) - a.radio) < 0.02
            and abs(math.dist(e.b, a.centro) - a.radio) < 0.02
            for a in arcos
        )
        if es_cuerda:
            faltas.append(f"cara plana (cuerda {largo:.3g}): sin distancia, cuerda ni ángulo")
            continue
        horizontal = abs(e.a[1] - e.b[1]) < 1e-6
        vertical = abs(e.a[0] - e.b[0]) < 1e-6
        if (horizontal and abs(largo - ancho) < 0.02) or (vertical and abs(largo - alto) < 0.02):
            continue
        faltas.append(f"tramo recto de {largo:.3g}: sin longitud ni tangencia declarada")
    for medida, cual in ((ancho, "ancho"), (alto, "alto")):
        clase = _clase_de_extension(medida, r.contorno)
        if medida > 0.05 and not variable_de(medida, ficha, c, clase):
            faltas.append(f"cota {cual} de la planta, {medida:.3g}: en el dibujo y sin variable")
    return faltas


def main(argv: list[str] | None = None) -> int:
    from emit.montaje import taller
    from emit.plataforma import LISTADO, contrato_mm
    from scripts.dossier import grupo_de_pieza
    from scripts.ver import _piezas

    sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[union-attr]
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--todo", action="store_true", help="cada falta, no solo el recuento")
    op = p.parse_args(argv)

    c = contrato_mm()
    hecho = taller(c)
    nombres = [pieza.nombre for pieza, _ in _piezas(0.0)]
    por_grupo: dict[str, list[tuple[str, list[str]]]] = defaultdict(list)
    for nombre in LISTADO:
        try:
            g = grupo_de_pieza(nombre, nombres)
        except ValueError:
            g = "(sin montar)"
        por_grupo[g].append((nombre, faltas_de(nombre, c, hecho)))

    total = 0
    for g in sorted(por_grupo):
        n = sum(len(f) for _, f in por_grupo[g])
        total += n
        print(f"== {g}: {n} faltas en {len(por_grupo[g])} piezas")
        for nombre, faltas in por_grupo[g]:
            if op.todo:
                for falta in faltas:
                    print(f"   {nombre}: {falta}")
            elif faltas:
                print(f"   {nombre}: {len(faltas)}")
    print(f"TOTAL {total}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
