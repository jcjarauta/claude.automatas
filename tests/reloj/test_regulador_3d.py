"""El regulador en 3D: lo que gira no atraviesa nada.

Con el áncora coaxial a la suspensión, la varilla del péndulo baja justo
por detrás del centro de la rueda. El eje de la rueda no puede llegar al
péndulo: gira entre el puente y la platina trasera y acaba en ella. Se
comprueba en todo el recorrido del áncora que permite la geometría.
"""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.slow

PERMITIDOS = {frozenset({"pendulo/fleje", "banco/soporte_suspension"})}
"""El fleje va apretado en su soporte: es su empotramiento."""


@pytest.fixture(scope="module")
def conjunto():
    pytest.importorskip("build123d", reason="hace falta el kernel: uv sync --group cad")
    from compile.regulador import regulador
    from emit.regulador_3d import ensamblaje

    return ensamblaje(regulador(1.0))


def _comun(a, b) -> float:
    ca, cb = a.bounding_box(), b.bounding_box()
    if (
        ca.max.X < cb.min.X
        or cb.max.X < ca.min.X
        or ca.max.Y < cb.min.Y
        or cb.max.Y < ca.min.Y
        or ca.max.Z < cb.min.Z
        or cb.max.Z < ca.min.Z
    ):
        return 0.0
    return float((a & b).volume)


@pytest.mark.parametrize("theta", [-8.8, -3.0, 0.0, 3.0, 8.8])
def test_el_eje_de_la_rueda_no_toca_el_pendulo_ni_la_horquilla(conjunto, theta):
    from emit.regulador_3d import piezas_en_mundo

    p = piezas_en_mundo(conjunto, theta)
    giran = [k for k in p if k.startswith("pendulo/")] + ["ancora/horquilla"]
    choques = [
        (fijo, g, round(_comun(p[fijo], p[g]), 3))
        for fijo in ("banco/eje_rueda", "rueda/rueda")
        for g in giran
        if _comun(p[fijo], p[g]) > 1e-3
    ]
    assert not choques, choques


@pytest.mark.parametrize("theta", [-8.8, 0.0, 8.8])
def test_lo_que_oscila_no_atraviesa_el_banco(conjunto, theta):
    from emit.regulador_3d import piezas_en_mundo

    p = piezas_en_mundo(conjunto, theta)
    oscilan = [k for k in p if k.startswith(("pendulo/", "ancora/"))]
    fijos = [k for k in p if k.startswith("banco/")]
    choques = [
        (o, f, round(_comun(p[o], p[f]), 3))
        for o in oscilan
        for f in fijos
        if frozenset({o, f}) not in PERMITIDOS and _comun(p[o], p[f]) > 1e-3
    ]
    assert not choques, choques
