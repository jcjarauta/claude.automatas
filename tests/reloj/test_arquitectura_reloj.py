"""La regla del tiempo, comprobada (ver `docs/reloj/expediente.md`).

La regla 1 dice que todo programa es función de θ y que un `dt` en `core/`
está mal planteado. El reloj necesita el tiempo de verdad, y la excepción
está declarada y acotada en dos fronteras:

- en el núcleo, el tiempo entra **solo por el oscilador**:
  `core/reloj/pendulo.py` es el único módulo de `core/reloj/` donde un
  segundo es una magnitud;
- fuera del núcleo, el tiempo se **integra** en un solo sitio:
  `compile/regulador.py`, que simula el regulador.

Este test hace que las dos fronteras no se muevan sin que nadie se entere.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

pytestmark = pytest.mark.core

RAIZ = Path(__file__).resolve().parents[2]

DONDE_HAY_SEGUNDOS = {"pendulo.py"}
"""En `core/reloj/`, el único módulo que mide en segundos."""

FRONTERA_DE_LA_VUELTA = {"escape.py"}
"""`vuelta_de_la_rueda` traduce el periodo del oscilador a la vuelta de la
rueda: recibe un periodo y no hace nada más con él. Es la frontera que ya
declaraba su docstring."""

TIEMPO = re.compile(
    r"\bdt\b|solve_ivp|odeint|\bsegundos?\b|\btiempo\b|time\.",
    re.IGNORECASE,
)


def _codigo(ruta: Path) -> str:
    """El fuente sin docstrings ni comentarios: hablar del tiempo para decir
    que no se usa no es usarlo."""
    texto = ruta.read_text(encoding="utf-8")
    texto = re.sub(r'"""[\s\S]*?"""', "", texto)
    return "\n".join(linea.split("#", 1)[0] for linea in texto.splitlines())


def test_en_core_reloj_solo_el_pendulo_mide_en_segundos():
    culpables = []
    for ruta in sorted((RAIZ / "core" / "reloj").glob("*.py")):
        if ruta.name in DONDE_HAY_SEGUNDOS | FRONTERA_DE_LA_VUELTA | {"__init__.py"}:
            continue
        if TIEMPO.search(_codigo(ruta)):
            culpables.append(ruta.name)
    assert not culpables, f"tiempo en core/reloj fuera del oscilador: {culpables}"


def test_en_core_no_se_integra_en_el_tiempo():
    """Ni un integrador de ecuaciones en todo `core/`."""
    culpables = [
        str(r.relative_to(RAIZ))
        for r in sorted((RAIZ / "core").rglob("*.py"))
        if re.search(r"solve_ivp|odeint|\bdt\b", _codigo(r))
    ]
    assert not culpables, culpables


def test_solo_el_regulador_integra_en_el_tiempo():
    integran = [
        str(r.relative_to(RAIZ)).replace("\\", "/")
        for carpeta in ("core", "compile", "emit")
        for r in sorted((RAIZ / carpeta).rglob("*.py"))
        if "solve_ivp" in _codigo(r)
    ]
    assert integran == ["compile/regulador.py"], integran


def test_la_excepcion_esta_declarada_donde_dice_claude_md():
    claude = (RAIZ / "CLAUDE.md").read_text(encoding="utf-8")
    expediente = (RAIZ / "docs" / "reloj" / "expediente.md").read_text(encoding="utf-8")
    assert "docs/reloj/expediente.md" in claude
    assert "compile/regulador.py" in expediente
    assert "test_arquitectura_reloj.py" in expediente
