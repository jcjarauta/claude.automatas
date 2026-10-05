"""Los textos de las fichas y de los grupos no pueden llevar números a mano
ni contradecir el material de la pieza."""

from __future__ import annotations

import re

import pytest

from emit.montaje import GRUPOS
from emit.plataforma import LISTADO, contrato_mm, texto

pytestmark = pytest.mark.core

DESIGNACIONES = re.compile(
    r"\{[a-z0-9_]+\}(?::1\b)?"  # lo que sale del contrato, y el «:1» de una relación
    r"|\bM\d+\b|\bZ\d+\b|\b[hHpPfF]\d+\b"  # rosca, dientes, ajuste ISO
    r"|\b(?:seguidor|plato|poste|canal) \d\b"  # nombres con ordinal
)
"""Lo único que puede llevar cifras en una descripción: un `{nombre}` del
contrato, una designación normalizada o el ordinal de una pieza."""

MATERIALES = re.compile(r"latón|laton|acero|aluminio|\bPOM|nogal|abedul|contrachapado|fleje|inox")


def _plantilla(t: str) -> str:
    return getattr(t, "plantilla", t)


def test_ninguna_descripcion_lleva_numeros_escritos_a_mano():
    """A3: «el cabestrante 6:1» siguió impreso cuando el contrato ya decía
    8:1. Un número en la prosa envejece en silencio; sale del contrato."""
    sueltos = []
    for g in GRUPOS:
        resto = DESIGNACIONES.sub("", _plantilla(g.objetivo))
        if re.search(r"\d", resto):
            sueltos.append(f"grupo {g.nombre}: {g.objetivo}")
    for nombre, f in LISTADO.items():
        resto = DESIGNACIONES.sub("", _plantilla(f.forma))
        if re.search(r"\d", resto):
            sueltos.append(f"{nombre}: {f.forma}")
    assert not sueltos, sueltos


def test_la_forma_no_nombra_el_material():
    """A5: «barra de latón» en el subtítulo y «chapa de latón de 3» en el
    material. La forma dice la geometría; el material lo dice su campo, y
    así no se pueden contradecir."""
    con_material = [n for n, f in LISTADO.items() if MATERIALES.search(f.forma)]
    assert not con_material, con_material


def test_la_relacion_del_cabestrante_sale_del_contrato():
    amplificador = next(g for g in GRUPOS if g.nombre == "amplificador")
    c = contrato_mm()
    relacion = c["amplificador_sector_radio"] / c["amplificador_tambor_radio"]
    assert f"{relacion:g}:1" in amplificador.objetivo
    otro = dict(c, amplificador_sector_radio=70.0, amplificador_tambor_radio=7.0)
    assert texto("el cabestrante {relacion_cabestrante}:1", otro) == "el cabestrante 10:1"
