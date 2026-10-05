"""La numeración única: qué existe hoy, y su registro.

    uv run --group cad python scripts/numeracion.py            # qué falta o sobra
    uv run --group cad python scripts/numeracion.py --alta     # numera lo nuevo
    uv run --group cad python scripts/numeracion.py --iniciar  # solo la primera vez

El registro es `docs/numeracion.json` (`emit.numeracion`). Este script mira
qué existe —lo que se fabrica, lo que se compra y la tornillería— y en qué
grupo se monta, para que el registro no se quede atrás. `--alta` da a lo
nuevo la siguiente marca libre de su grupo y no toca nada de lo que ya tiene
número: después se revisa el diff como cualquier dato y se congela el golden
(`tests/golden/numeracion.json`) con `scripts/regenerar_golden.py`.

**El orden de la primera numeración** es el de montaje: dentro de cada grupo,
de abajo arriba en la máquina montada. Desde ahí, los números son un dato.
"""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

RAIZ = Path(__file__).resolve().parent.parent
GOLDEN = RAIZ / "tests" / "golden" / "numeracion.json"

COMERCIALES_COLOCADOS = {
    "poste_pivote": "poste",
    "rodamiento_arbol": "rodamiento_arbol",
    "rodillo_seguidor": "rodillo_",
    "rueda_reductor": "rueda",
    "pinon_reductor": "pinon",
    "portaminas": "portaminas",
    "pasador_indice": "pasador_indice",
    "muelle_garra": "muelle_garra",
    "muelle_seguidor": "muelle_seguidor_",
    "cinta_amplificador": "cinta_",
}
"""Cómo se llama en el montaje cada comercial que se dibuja: su grupo es el
de la pieza colocada."""

COMERCIALES_SIN_COLOCAR = {
    "casquillo_pivote": "seguidores",
    "anillo_lapiz": "portalapiz",
    "arbol_de_levas": "entre_puntos",
    "plancha_pom": "levas",
}
"""Los que no se dibujan en el montaje, con su grupo declarado: el casquillo
va dentro del seguidor, el anillo en el portaminas, la barra W10 de la que
salen los ejes y la plancha de la que salen las levas."""

SIN_MARCA = ("tornilleria",)
"""Entradas del catálogo que no son una pieza: la línea de compra de toda la
tornillería, que la serie T numera línea a línea."""


def inventario():
    """grupo → serie → lo que existe hoy, en orden de montaje."""
    from emit.catalogo import cargar
    from emit.materiales import tornilleria
    from emit.montaje import grupo_de
    from emit.plataforma import LISTADO
    from scripts.dossier import ALIAS, grupo_de_pieza
    from scripts.ver import _piezas

    colocadas = [(p.nombre, s) for p, s in _piezas(0.0)]
    nombres = [n for n, _ in colocadas]

    def altura(pieza: str) -> float:
        buscado = ALIAS.get(pieza, pieza)
        alturas = [
            s.bounding_box().min.Z
            for n, s in colocadas
            if n == buscado or n.startswith((buscado + "_", buscado.replace("brazo_", "") + "_"))
        ]
        return min(alturas, default=0.0)

    salida: dict[str, dict[str, list[str]]] = {}

    def poner(grupo: str, serie: str, nombre: str) -> None:
        salida.setdefault(grupo, {"piezas": [], "comerciales": [], "tornilleria": []})
        salida[grupo][serie].append(nombre)

    for pieza in sorted(LISTADO, key=lambda n: (altura(n), n)):
        poner(grupo_de_pieza(pieza, nombres), "piezas", pieza)
    for comercial in cargar():
        if comercial.nombre in SIN_MARCA:
            continue
        if comercial.nombre in COMERCIALES_SIN_COLOCAR:
            grupo = COMERCIALES_SIN_COLOCAR[comercial.nombre]
        else:
            prefijo = COMERCIALES_COLOCADOS[comercial.nombre]
            colocada = next(n for n in nombres if n.startswith(prefijo))
            grupo = grupo_de(colocada).nombre
        poner(grupo, "comerciales", comercial.nombre)
    for f in tornilleria():
        poner(f.grupo, "tornilleria", f.clave)
    return salida


def main(argv: list[str] | None = None) -> int:
    from emit.montaje import GRUPOS
    from emit.numeracion import REGISTRO, SERIES, cargar, dar_de_alta, diferencias, guardar

    sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[union-attr]
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--alta", action="store_true", help="numera lo que exista sin marca")
    p.add_argument("--iniciar", action="store_true", help="crea el registro y su golden")
    op = p.parse_args(argv)

    actual = inventario()
    if op.iniciar:
        if REGISTRO.exists():
            print(f"{REGISTRO} ya existe: los números son un dato, no se rehacen.")
            return 1
        vacio = {g.nombre: {"sigla": g.sigla, **{s: {} for s in SERIES}} for g in GRUPOS}
        registro, altas = dar_de_alta(vacio, actual)
        guardar(registro)
        shutil.copyfile(REGISTRO, GOLDEN)
        print(f"{REGISTRO}: {len(altas)} marcas; golden en {GOLDEN}")
        return 0

    registro = cargar()
    if op.alta:
        registro, altas = dar_de_alta(registro, actual)
        guardar(registro)
        print("\n".join(altas) or "nada nuevo")
        return 0
    faltas = diferencias(registro, actual)
    print("\n".join(faltas) or "el registro está al día")
    return 1 if faltas else 0


if __name__ == "__main__":
    raise SystemExit(main())
