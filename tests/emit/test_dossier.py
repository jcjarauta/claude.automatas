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


def test_las_tres_tablas_del_despiece_llevan_marca_en_cada_fila():
    """B1: la marca y el plano salen del registro único (`docs/numeracion.json`)
    y no queda ninguna fila sin ellos: son piezas que alguien tiene que
    encontrar encima de la mesa."""
    pytest.importorskip("build123d", reason="hace falta el kernel: uv sync --group cad")
    from scripts.dossier import datos

    d = datos("commit prueba")
    sin_marca = [n for n, *_ in d.fabricadas if ("piezas", n) not in d.marcas]
    sin_marca += [n for n, *_ in d.comerciales if ("comerciales", n) not in d.marcas]
    sin_marca += [
        f"{dz} · {p}"
        for dz, _, p in d.tornilleria
        if ("tornilleria", f"{dz} · {p}") not in d.marcas
    ]
    assert not sin_marca, sin_marca
    assert d.marcas[("piezas", "tambor")] == ("P-AMP-03", "P-AMP-03")
    assert d.marcas[("comerciales", "cinta_amplificador")][1] == "G-AMP"


def test_cada_pagina_dice_que_no_se_mide_sobre_ella(tmp_path, monkeypatch):
    """B4: el dossier va a escala libre; la frontera con las plantillas 1:1
    se dice en el pie de cada página."""
    pytest.importorskip("build123d", reason="hace falta el kernel: uv sync --group cad")
    from reportlab import rl_config

    from emit.dossier import escribir_dossier
    from emit.estilo import NO_MEDIR
    from scripts.dossier import datos

    monkeypatch.setattr(rl_config, "pageCompression", 0)
    pdf = escribir_dossier(datos("commit prueba"), tmp_path / "d.pdf").read_bytes()
    paginas = pdf.count(b"/Type /Page") - pdf.count(b"/Type /Pages")
    assert pdf.count(f"({NO_MEDIR}) Tj".encode("latin-1")) == paginas


def _celdas(tabla) -> list[list[str]]:
    return [
        [c.getPlainText() if hasattr(c, "getPlainText") else str(c) for c in fila]
        for fila in tabla._cellvalues
    ]


def test_el_indice_lleva_toda_marca_con_su_documento_y_hoja():
    """Fase 5: cada cosa marcada, en el orden de montaje, con dónde está
    dibujada; y por orden alfabético, remitiendo a la marca."""
    pytest.importorskip("build123d", reason="hace falta el kernel: uv sync --group cad")
    from reportlab.lib.styles import getSampleStyleSheet

    from emit.dossier import _indice
    from scripts.dossier import datos

    d = datos("commit prueba")
    estilo = getSampleStyleSheet()["BodyText"]
    por_marca, _, alfabetico = _indice(d, 500.0, estilo, estilo)
    filas = _celdas(por_marca)[1:]
    assert {f[0] for f in filas} == {codigo for codigo, _ in d.marcas.values()}
    tambor = next(f for f in filas if f[1] == "tambor")
    assert tambor[0] == "P-AMP-03"
    assert tambor[5:] == ["fichas_amplificador.pdf", "4"]
    # En el orden de montaje: el bastidor, lo primero; las levas, lo último.
    assert filas[0][4].endswith("bastidor")
    assert filas[-1][4].endswith("levas")
    nombres = [f[0] for f in _celdas(alfabetico)[1:]]
    assert nombres == sorted(nombres)
    assert "tambor" in nombres
