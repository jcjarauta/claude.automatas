"""«Feliz cumpleaños» en letra inglesa con su swash: el primer pedido de dos
renglones, un cartucho por renglón (docs/propuesta_dimensionado.md, fase 4).

En una vuelta no cabe con calidad: la leva que se puede cortar redondearía la
letra más de medio milímetro. En dos, cada renglón escribe con menos de una
décima de error y los dos cartuchos se montan sobre los mismos brazos.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from compile.escribiente import SOCAVADO_TOLERABLE, compilar
from compile.renglones import compilar_por_renglones, leer_pedido

pytestmark = pytest.mark.core

PEDIDO = Path(__file__).resolve().parents[2] / "demo" / "feliz_cumpleanos.json"


def test_el_pedido_esta_al_dia_con_su_generador():
    from scripts.escritura_feliz_cumpleanos import pedido

    assert json.loads(PEDIDO.read_text(encoding="utf-8")) == json.loads(json.dumps(pedido()))


def test_en_una_vuelta_no_cabe_con_calidad():
    v = compilar(leer_pedido(PEDIDO).escritura).veredicto
    assert not v.apto
    assert v.metricas["error_trazo_maximo"] > SOCAVADO_TOLERABLE


def test_en_dos_renglones_cada_cartucho_escribe_bien():
    pedido = leer_pedido(PEDIDO)
    assert pedido.renglones is not None
    cartuchos = compilar_por_renglones(pedido.escritura, pedido.renglones)
    assert len(cartuchos) == 2
    for c in cartuchos:
        assert c.veredicto.apto, [i.codigo for i in c.veredicto.errores]
        assert c.veredicto.metricas["error_trazo_maximo"] < 0.0001
        assert c.calajes == cartuchos[0].calajes
