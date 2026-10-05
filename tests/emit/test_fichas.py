"""Las fichas de fabricación: la de grupo y una por pieza, deterministas y
con cada cota enlazada a su variable cuando la tiene."""

from __future__ import annotations

import pytest

pytest.importorskip("build123d", reason="hace falta el kernel: uv sync --group cad")


@pytest.fixture(scope="module")
def amplificador():
    from scripts.fichas import preparar

    return preparar("amplificador")


def test_el_grupo_lleva_sus_piezas_su_tornilleria_y_sus_lagunas(amplificador):
    nombres = [p.nombre for p in amplificador.piezas]
    assert nombres == ["eje_pivote", "calzo_sector", "tambor", "sector", "mordaza"]
    assert [p.marca for p in amplificador.piezas] == [1, 2, 3, 4, 5]
    assert all(p.cantidad_en_el_grupo == 2 for p in amplificador.piezas)
    designaciones = {k.designacion for k in amplificador.comerciales}
    assert "DIN 912 M4 × 16" in designaciones
    assert not any("ejes de la mesa" in k.para for k in amplificador.comerciales)
    # La cinta está en el 3D y no tiene ficha: la hoja lo dice.
    assert amplificador.sin_ficha == ("cinta",)


def test_las_cotas_salen_de_la_geometria_exacta_y_casan_con_su_variable(amplificador):
    """El tambor se acotaba 13,91 con la caja de las polilíneas."""
    from emit.fichas import variable_de, vista_de_pieza
    from emit.plataforma import LISTADO

    tambor = next(p for p in amplificador.piezas if p.nombre == "tambor")
    x0, _, x1, _ = vista_de_pieza(tambor.solido, "planta").caja()
    assert x1 - x0 == pytest.approx(13.95, abs=1e-3)
    nombre = variable_de(x1 - x0, LISTADO["tambor"], amplificador.contrato, diametro=True)
    assert nombre == "amplificador_tambor_radio_mecanizado_diametro"


def test_el_pdf_es_determinista_y_lleva_una_hoja_por_pieza(amplificador, tmp_path):
    from emit.fichas import escribir_fichas

    a = escribir_fichas(amplificador, tmp_path / "a.pdf").read_bytes()
    b = escribir_fichas(amplificador, tmp_path / "b.pdf").read_bytes()
    assert a == b
    hojas = a.count(b"/Type /Page") - a.count(b"/Type /Pages")
    assert hojas == 1 + len(amplificador.piezas)
