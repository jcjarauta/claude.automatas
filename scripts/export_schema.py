"""Exporta el esquema JSON de los modelos del contrato a `docs/schema/`.

El esquema versionado es la forma de ver en un diff que un cambio en el modelo
rompe el contrato. `tests/core/test_schema.py` comprueba que lo guardado
coincide con lo que generan los modelos, así que no puede quedarse atrás sin
que falle la suite.

    uv run python scripts/export_schema.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from core.comercial import PiezaComercial
from core.module import FichaModulo, Maquina
from core.program import Programa
from core.verdict import Veredicto

DESTINO = Path(__file__).resolve().parent.parent / "docs" / "schema"

MODELOS = {
    "programa": Programa,
    "ficha_modulo": FichaModulo,
    "maquina": Maquina,
    "veredicto": Veredicto,
    "pieza_comercial": PiezaComercial,
}


def esquemas() -> dict[str, str]:
    """Nombre de fichero -> contenido, para escribir o para comparar."""
    return {
        f"{nombre}.schema.json": json.dumps(
            modelo.model_json_schema(), indent=2, ensure_ascii=False, sort_keys=True
        )
        + "\n"
        for nombre, modelo in MODELOS.items()
    }


def main() -> int:
    DESTINO.mkdir(parents=True, exist_ok=True)
    for fichero, contenido in esquemas().items():
        (DESTINO / fichero).write_text(contenido, encoding="utf-8")
        print(f"escrito docs/schema/{fichero}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
