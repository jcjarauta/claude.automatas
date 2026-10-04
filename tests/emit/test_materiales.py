"""El material en bruto: cada pieza remite a uno, y la lista de compra cuadra."""

from __future__ import annotations

import pytest

from emit.materiales import STOCK, compra
from emit.plataforma import LISTADO

pytestmark = pytest.mark.core


def test_toda_pieza_sale_de_un_material_del_stock():
    """El mismo material con dos nombres salía en la lista como dos compras:
    pasó con la barra W10. Ahora un nombre que no está en STOCK salta aquí."""
    fuera = {n: f.material for n, f in LISTADO.items() if f.material not in STOCK}
    assert not fuera, fuera


def test_no_hay_material_que_no_se_use():
    usados = {f.material for f in LISTADO.values()}
    assert set(STOCK) == usados, set(STOCK) - usados


def test_la_lista_lleva_cada_pieza_una_vez_y_con_su_cantidad():
    vistas: dict[str, int] = {}
    for linea in compra():
        assert linea.cantidad > 0.0, linea.material
        for nombre, cantidad in linea.piezas:
            assert nombre not in vistas, nombre
            vistas[nombre] = cantidad
    assert vistas == {n: f.cantidad for n, f in LISTADO.items()}


def test_la_barra_w10_es_una_sola_compra_con_sus_cinco_ejes():
    w10 = next(x for x in compra() if x.material == "barra W10 h6 rectificada")
    assert {n for n, _ in w10.piezas} == {
        "eje_pivote",
        "eje_manivela",
        "eje_cartucho",
        "munon",
        "eje_motriz",
    }


def test_el_documento_esta_al_dia():
    from scripts.lista_materiales import DOCUMENTO, documento

    assert DOCUMENTO.read_text(encoding="utf-8") == documento(), (
        "docs/materiales.md no está al día: uv run python scripts/lista_materiales.py --escribir"
    )
