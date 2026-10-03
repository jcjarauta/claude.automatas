"""Deja constancia de lo que se acaba de importar al Variable Studio.

    uv run python scripts/marcar_importado.py              # todos
    uv run python scripts/marcar_importado.py variables_cota

Guarda el sha256 y el contenido de cada CSV en `docs/importado.json`, que es
contra lo que `scripts/csv_pendientes.py` compara la próxima vez.

**Se guarda el contenido y no solo el hash** porque un hash dice que algo
cambió y no qué: reconstruir eso a mano es justo el trabajo que este par de
scripts existe para quitar.
"""

from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.csv_pendientes import IMPORTADO


def marcar(paquete: Path, cuales: list[str] | None = None, hoy: str | None = None) -> list[str]:
    datos = json.loads(IMPORTADO.read_text(encoding="utf-8"))
    hoy = hoy or datetime.date.today().isoformat()
    tocados = []
    for nombre in cuales or sorted(datos["archivos"]):
        ruta = paquete / f"{nombre}.csv"
        if not ruta.exists():
            continue
        crudo = ruta.read_bytes()
        texto = crudo.decode("utf-8")
        datos["archivos"][nombre] = {
            "sha256": hashlib.sha256(crudo).hexdigest(),
            "fecha": hoy,
            "filas": len([x for x in texto.splitlines() if x]),
            "contenido": texto,
        }
        tocados.append(nombre)
    IMPORTADO.write_text(
        json.dumps(datos, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n"
    )
    return tocados


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("archivos", nargs="*")
    p.add_argument("--paquete", type=Path, default=Path("build/cad"))
    op = p.parse_args(argv)
    tocados = marcar(op.paquete, op.archivos or None)
    print("marcado como importado: " + (", ".join(tocados) or "nada"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
