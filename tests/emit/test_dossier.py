"""El dossier de montaje: que lea todo lo que tiene que leer y salga igual."""

from __future__ import annotations

from pathlib import Path

import pytest

from emit.dossier import COMPROBACIONES, ORDEN_DE_MONTAJE, _limpio, bloques_de_markdown
from emit.montaje import GRUPOS

RAIZ = Path(__file__).resolve().parents[2]
PROCEDIMIENTOS = (RAIZ / "docs" / "procedimientos.md").read_text(encoding="utf-8")


def test_el_orden_de_montaje_pasa_por_todos_los_grupos_una_vez():
    assert sorted(ORDEN_DE_MONTAJE) == sorted(g.nombre for g in GRUPOS)
    assert ORDEN_DE_MONTAJE[-2:] == ("cartucho", "levas"), "se meten en una máquina montada"


def test_los_procedimientos_se_leen_enteros():
    """Cada título, cada paso numerado y cada tabla del markdown llega al
    dossier: lo que el intérprete no entienda no se puede perder."""
    bloques = bloques_de_markdown(PROCEDIMIENTOS)
    titulos = [c for t, c in bloques if t in ("h1", "h2")]
    renglones = [r.strip() for r in PROCEDIMIENTOS.splitlines()]
    assert titulos == [r.lstrip("#").strip() for r in renglones if r.startswith("#")]
    pasos = sum(len(c) for t, c in bloques if t == "lista")
    esperados = sum(
        1 for r in renglones if (r[:1].isdigit() and ". " in r[:4]) or r.startswith("- ")
    )
    assert pasos == esperados
    assert any(t == "tabla" for t, _ in bloques)


def test_todo_el_texto_cabe_en_la_fuente_del_pdf():
    """La Helvetica del PDF va en Windows-1252. Lo que no tiene sale como
    «?»: así salían las rayas y las viñetas. Ningún texto del dossier puede
    ganar un «?» al limpiarlo."""
    for texto in (PROCEDIMIENTOS, *COMPROBACIONES, *(g.objetivo for g in GRUPOS)):
        assert _limpio(texto).count("?") == texto.count("?")
    raros = "".join(chr(c) for c in (0x2212, 0x2014, 0x2192, 0x2022, 0x2026))
    assert "?" not in _limpio(raros)


cad = pytest.importorskip("build123d", reason="hace falta el kernel: uv sync --group cad")


def test_toda_pieza_fabricada_cae_en_un_paso_de_montaje():
    from scripts.dossier import datos

    d = datos(version="prueba")
    from emit.plataforma import LISTADO

    assert {f[0] for f in d.fabricadas} == set(LISTADO)
    assert {f[4] for f in d.fabricadas} <= set(ORDEN_DE_MONTAJE)


@pytest.mark.slow
def test_el_dossier_sale_igual_byte_a_byte(tmp_path):
    """Mismo montaje, mismo PDF: sin fecha de creación ni identificadores
    al azar. Es la regla de todos los emisores."""
    from emit.dossier import escribir_dossier
    from scripts.dossier import datos

    d = datos(version="prueba")
    uno = escribir_dossier(d, tmp_path / "uno.pdf").read_bytes()
    dos = escribir_dossier(d, tmp_path / "dos.pdf").read_bytes()
    assert uno[:5] == b"%PDF-"
    assert uno == dos
