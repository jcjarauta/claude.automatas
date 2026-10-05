"""Cada ficha de pieza sirve para dibujar la pieza desde cero.

El perfil de la pieza —la lista de `Arco` y `Segmento` que va al DXF— y lo
que su ficha rotula son dos listas que describen lo mismo desde lados
distintos: lo que aparece en una y falta en la otra es siempre algo. Se
cruzan en los diez grupos, y cada cota que la ficha dice rotular se busca en
el PDF: si no está escrita, no cuenta.
"""

from __future__ import annotations

import math
import re

import pytest

from emit.dibujable import Acotacion, construccion, faltas, perfil_de
from emit.plataforma import Arco, Segmento, contrato_mm

GRUPOS_CON_PIEZAS = (
    "bastidor",
    "cartucho",
    "entre_puntos",
    "accionamiento",
    "seguidores",
    "amplificador",
    "cinco_barras",
    "levantamiento",
    "portalapiz",
)


def _textos(pdf: bytes) -> list[str]:
    """El texto de cada hoja de un PDF sin comprimir, como se escribió."""

    def literal(m: re.Match[bytes]) -> str:
        crudo = m.group(1)
        crudo = re.sub(rb"\\([0-7]{3})", lambda o: bytes([int(o.group(1), 8)]), crudo)
        crudo = crudo.replace(rb"\(", b"(").replace(rb"\)", b")").replace(rb"\\", b"\\")
        return crudo.decode("cp1252", "replace")

    hojas = []
    for flujo in re.findall(rb"stream\r?\n(.*?)endstream", pdf, re.S):
        if b" Tj" not in flujo:
            continue
        hojas.append(" ".join(literal(m) for m in re.finditer(rb"\((.*?)\) Tj", flujo, re.S)))
    return hojas


@pytest.fixture(scope="module", params=GRUPOS_CON_PIEZAS)
def grupo(request, tmp_path_factory):
    pytest.importorskip("build123d", reason="hace falta el kernel: uv sync --group cad")
    from emit.fichas import escribir_fichas
    from scripts.fichas import preparar

    fichas = preparar(request.param)
    ruta = tmp_path_factory.mktemp(request.param) / "f.pdf"
    pdf = escribir_fichas(fichas, ruta, "commit prueba", comprimir=False).read_bytes()
    return fichas, _textos(pdf)


@pytest.mark.slow
def test_toda_pieza_se_puede_dibujar_con_su_ficha(grupo):
    fichas, _ = grupo
    pendientes = []
    for p in fichas.piezas:
        pendientes += faltas(perfil_de(p.nombre, fichas.contrato), p.acotacion)
    assert not pendientes, "\n".join(pendientes)


@pytest.mark.slow
def test_lo_que_la_ficha_dice_acotar_esta_escrito_en_la_hoja(grupo):
    """No las variables que la generan: lo que se ha dibujado."""
    fichas, hojas = grupo
    assert len(hojas) == 1 + len(fichas.piezas)
    for p, hoja in zip(fichas.piezas, hojas[1:], strict=True):
        texto = " ".join(hoja.split())
        for cota in p.acotacion.cotas:
            buscado = " ".join(cota.texto.split())
            if cota.clase == "tangente":
                # Va en un párrafo, que se parte en renglones.
                assert all(palabra in texto for palabra in buscado.split()), p.nombre
            else:
                assert buscado in texto, f"{p.nombre}: «{cota.texto}» no está en la hoja"


# ---------------------------------------------------------------------------
# Cómo se lee la construcción del perfil
# ---------------------------------------------------------------------------


def test_una_barra_de_dos_cubos_son_dos_circulos_y_sus_tangentes():
    """«Barra de dos cubos» dibujada como un trapecio es otra pieza, y se ve
    bien: los dos tramos rectos son tangentes y la hoja tiene que decirlo."""
    c = construccion(perfil_de("calzo_sector", contrato_mm()))
    assert len(c.tangentes) == 2
    assert not c.rectos
    assert not c.caras_planas


def test_una_cara_plana_se_situa_con_distancia_cuerda_y_lado():
    c = construccion(perfil_de("tambor", contrato_mm()))
    (cara,) = c.caras_planas
    assert cara.distancia == pytest.approx(4.0)
    assert cara.cuerda == pytest.approx(6.0)
    # Una cuerda sola no la sitúa: el lado sale de hacia dónde mira la normal.
    assert cara.angulo == pytest.approx(0.0)


def test_el_cruce_dice_lo_que_falta_con_el_nombre_de_la_pieza():
    perfil = [
        Arco((0.0, 0.0), 5.0, 0.0, math.pi),
        Arco((20.0, 0.0), 3.0, math.pi, 2 * math.pi),
        Segmento((0.0, 5.0), (20.0, 3.0)),
    ]
    pendientes = faltas(perfil, Acotacion("prueba"))
    assert pendientes
    assert all(f.startswith("prueba:") for f in pendientes)
    assert any("R3 en (20, 0) con el centro sin situar" in f for f in pendientes)
    assert any("tramo de" in f for f in pendientes)
