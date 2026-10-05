"""La numeración es un dato: el registro contra su copia congelada y contra
lo que existe. Meter una pieza sale como ALTA; que un número cambie de dueño
falla diciendo cuál."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from emit.numeracion import REGISTRO, cargar, comparar, dar_de_alta, marcas

GOLDEN = Path(__file__).resolve().parent / "numeracion.json"


def test_el_registro_no_ha_cambiado_respecto_del_golden():
    """Si es un alta querida: `scripts/regenerar_golden.py` congela el nuevo."""
    golden = json.loads(GOLDEN.read_text(encoding="utf-8"))["grupos"]
    cambios = comparar(cargar(REGISTRO), golden)
    assert not cambios, "\n".join(cambios)


def test_todo_lo_que_existe_tiene_marca_y_en_su_grupo():
    pytest.importorskip("build123d", reason="hace falta el kernel: uv sync --group cad")
    from emit.numeracion import diferencias
    from scripts.numeracion import inventario

    faltas = diferencias(cargar(), inventario())
    assert not faltas, (
        "\n".join(faltas) + "\n→ uv run --group cad python scripts/numeracion.py --alta"
    )


def test_las_siglas_son_las_de_los_grupos_y_no_se_repiten():
    from emit.montaje import GRUPOS

    registro = cargar()
    assert {g: registro[g]["sigla"] for g in registro} == {g.nombre: g.sigla for g in GRUPOS}
    siglas = [g.sigla for g in GRUPOS]
    assert len(set(siglas)) == len(siglas)


def test_un_alta_es_alta_y_un_cambio_de_dueno_dice_cual():
    registro = {"amplificador": {"sigla": "AMP", "piezas": {"1": "eje", "2": None}}}
    nuevo, altas = dar_de_alta(registro, {"amplificador": {"piezas": ["eje", "tambor"]}})
    # El 2 está dado de baja: no se reutiliza.
    assert altas == ["ALTA: P-AMP-03 tambor"]
    assert comparar(nuevo, registro) == ["ALTA: P-AMP-03 es tambor"]
    cambiado = {"amplificador": {"sigla": "AMP", "piezas": {"1": "tambor", "2": None}}}
    assert comparar(cambiado, registro) == ["CAMBIA: P-AMP-01 era eje y es tambor"]
    borrado = {"amplificador": {"sigla": "AMP", "piezas": {"2": None}}}
    assert comparar(borrado, registro)[0].startswith("BORRADO: P-AMP-01")


def test_una_pieza_con_dos_marcas_no_se_admite():
    registro = {
        "amplificador": {"sigla": "AMP", "piezas": {"1": "eje"}},
        "bastidor": {"sigla": "BAS", "piezas": {"1": "eje"}},
    }
    with pytest.raises(ValueError, match="dos marcas"):
        marcas(registro)


def test_la_tornilleria_del_catalogo_es_la_de_la_lista():
    """Otro número escrito a mano: el catálogo seguía en 70 cuando la lista ya
    daba 72."""
    from emit.catalogo import cargar as catalogo
    from emit.materiales import tornilleria

    linea = next(p for p in catalogo() if p.nombre == "tornilleria")
    assert linea.cantidad == sum(f.cantidad for f in tornilleria())


# ---------------------------------------------------------------------------
# El índice: dónde está dibujada cada marca
# ---------------------------------------------------------------------------


def test_cada_marca_tiene_documento_y_hoja():
    from emit.numeracion import paginas

    registro = cargar()
    donde = paginas(registro)
    assert set(donde) == set(marcas(registro))
    assert donde[("piezas", "tambor")].documento == "fichas_amplificador.pdf"
    # Hoja 1, la de grupo; la 2, el despiece explosionado; después una por
    # pieza, en el orden de su marca.
    assert donde[("piezas", "eje_pivote")].hoja == 3
    assert donde[("piezas", "tambor")].hoja == 5
    assert donde[("comerciales", "cinta_amplificador")].hoja == 1


def test_un_numero_dado_de_baja_no_deja_hoja_vacia():
    from emit.numeracion import paginas

    registro = {
        "g": {
            "sigla": "GGG",
            "piezas": {"1": "a", "2": None, "3": "c"},
            "comerciales": {"1": "k"},
            "tornilleria": {},
        }
    }
    donde = paginas(registro)
    assert [donde[("piezas", n)].hoja for n in ("a", "c")] == [3, 4]
    assert donde[("comerciales", "k")].hoja == 1
    assert donde[("piezas", "a")].documento == "fichas_g.pdf"
