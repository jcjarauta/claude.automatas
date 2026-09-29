"""El esquema versionado no puede quedarse atrás respecto a los modelos."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RAIZ / "scripts"))

from export_schema import DESTINO, esquemas  # noqa: E402

pytestmark = pytest.mark.core


@pytest.mark.parametrize("fichero", sorted(esquemas()))
def test_el_esquema_guardado_coincide_con_los_modelos(fichero: str):
    ruta = DESTINO / fichero
    assert ruta.exists(), (
        f"falta {ruta.relative_to(RAIZ)}. Ejecuta: uv run python scripts/export_schema.py"
    )
    assert ruta.read_text(encoding="utf-8") == esquemas()[fichero], (
        f"{fichero} está desfasado respecto a los modelos. "
        "Ejecuta: uv run python scripts/export_schema.py"
    )
