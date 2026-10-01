"""Qué CSV hay que reimportar al Variable Studio, y qué ha cambiado en cada uno.

    uv run python scripts/csv_pendientes.py build/cad

`docs/importado.json` guarda el sha256 de lo que está **ahora mismo** en
Onshape. Esto compara el paquete recién generado contra eso y dice qué
archivos difieren y, fila a fila, qué entra, qué sale y qué cambia de valor.

**Hace falta porque reimportar de más también cuesta.** Un mapa del Variable
Studio no se actualiza: se borra y se vuelve a crear, y mientras tanto todo lo
que lo referencia se pone en rojo. Decir «reimporta los cinco» por si acaso es
pedir cinco veces ese susto cuando normalmente ha cambiado uno.

Y hace falta porque la alternativa es que alguien se acuerde. El bucle de
`docs/metodologia.md` §2d lo pide por pieza, y una lista que se escribe a mano
se queda atrás la segunda vez.

Después de importar se marca con `scripts/marcar_importado.py`.
"""

from __future__ import annotations

import argparse
import csv as _csv
import hashlib
import json
import sys
from dataclasses import dataclass, field
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

RAIZ = Path(__file__).resolve().parent.parent
IMPORTADO = RAIZ / "docs" / "importado.json"


@dataclass
class Cambio:
    archivo: str
    altas: list[str] = field(default_factory=list)
    bajas: list[str] = field(default_factory=list)
    distintas: list[tuple[str, str, str]] = field(default_factory=list)

    @property
    def hay(self) -> bool:
        return bool(self.altas or self.bajas or self.distintas)


def _filas(texto: str) -> dict[str, str]:
    """Nombre -> valor. Los CSV que se importan no llevan cabecera."""
    return {f[0]: f[1] for f in _csv.reader(texto.splitlines()) if len(f) >= 2}


def estado() -> dict[str, dict[str, object]]:
    return dict(json.loads(IMPORTADO.read_text(encoding="utf-8"))["archivos"])


def pendientes(paquete: Path) -> list[Cambio]:
    """Los archivos que difieren de lo que hay en Onshape, con el detalle."""
    dentro, salida = estado(), []
    for nombre, guardado in sorted(dentro.items()):
        ruta = paquete / f"{nombre}.csv"
        if not ruta.exists():
            continue
        crudo = ruta.read_bytes()
        if hashlib.sha256(crudo).hexdigest() == guardado["sha256"]:
            continue
        cambio = Cambio(nombre)
        ahora = _filas(crudo.decode("utf-8"))
        antes = _filas((guardado.get("contenido") or "") or "")
        if not antes:
            # Sin copia del contenido solo se puede decir que cambió. Es el
            # caso de la primera vez; a partir de ahí se guarda y hay detalle.
            cambio.altas = sorted(ahora)
        else:
            cambio.altas = sorted(ahora.keys() - antes.keys())
            cambio.bajas = sorted(antes.keys() - ahora.keys())
            cambio.distintas = [
                (n, antes[n], ahora[n])
                for n in sorted(ahora.keys() & antes.keys())
                if antes[n] != ahora[n]
            ]
        salida.append(cambio)
    return salida


def informe(cambios: list[Cambio], mapas: dict[str, tuple[str, str]]) -> str:
    if not cambios:
        return "# Reimportar\n\nNada. Lo que hay en Onshape coincide con el paquete.\n"
    lineas = [
        "# Reimportar",
        "",
        "Lo que ha cambiado desde la última importación. **Lo que no está aquí no",
        "se toca**: un mapa del Variable Studio no se actualiza, se borra y se",
        "vuelve a crear, y mientras tanto todo lo que lo referencia se pone en rojo.",
        "",
        "| Archivo | Variable | Factor |",
        "| --- | --- | --- |",
    ]
    for c in cambios:
        mapa, factor = mapas.get(c.archivo, ("?", "?"))
        lineas.append(f"| `{c.archivo}.csv` | `#{mapa}` | `{factor}` |")
    for c in cambios:
        lineas += ["", f"## `{c.archivo}.csv`", ""]
        for n in c.altas:
            lineas.append(f"- **nueva** `{n}`")
        for n in c.bajas:
            lineas.append(
                f"- **se va** `{n}` — la clave vieja se queda en el mapa si no borras la tabla"
            )
        for n, a, b in c.distintas:
            lineas.append(f"- **cambia** `{n}`: {a} → {b}")
    lineas += [
        "",
        "Al terminar: `uv run python scripts/marcar_importado.py`",
        "",
    ]
    return "\n".join(lineas)


def main(argv: list[str] | None = None) -> int:
    from scripts.exportar_para_cad import MAPAS

    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("paquete", type=Path, nargs="?", default=Path("build/cad"))
    op = p.parse_args(argv)
    cambios = pendientes(op.paquete)
    print(informe(cambios, MAPAS), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
