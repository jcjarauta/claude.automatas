"""El dibujo conceptual de la máquina.

No se comprueba que sea bonito: se comprueba que **salga del modelo**. Un
dibujo de arquitectura que se mantiene a mano deja de coincidir con el código
a la primera semana, y entonces es peor que no tenerlo porque nadie sabe cuál
de los dos miente.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from compile.escribiente import SEGUIDORES, Escribiente
from scripts.dibujar_maquina import main


@pytest.fixture
def dibujo(tmp_path: Path) -> str:
    destino = tmp_path / "maquina.svg"
    assert main(["--out", str(destino)]) == 0
    return destino.read_text(encoding="utf-8")


def test_las_cotas_del_dibujo_son_las_del_modelo(dibujo: str):
    """Si alguien cambia la separación del cinco barras, el dibujo cambia
    solo. Es la única forma de que un dibujo así siga siendo cierto."""
    m = Escribiente()
    assert f"separación {float(m.separacion) * 1000:.0f}" in dibujo
    assert f"radio base {float(m.radio_base) * 1000:.0f}" in dibujo
    assert f"proximal {float(m.proximal) * 1000:.0f}" in dibujo


def test_estan_los_tres_canales(dibujo: str):
    for nombre in SEGUIDORES:
        assert nombre in dibujo


def test_el_dibujo_dice_lo_que_falta(dibujo: str):
    """**Lo que más importa del dibujo.** Entre la planta de las levas y el
    alzado del varillaje no hay mecanismo: la relación 6:1 es un número en el
    código. Un dibujo que rellenara ese hueco con algo verosímil haría creer
    que el diseño está cerrado."""
    assert "SIN DEFINIR" in dibujo
    assert "123,1" in dibujo
    assert "120,0" in dibujo


def test_las_levas_van_a_escala_real(dibujo: str):
    """Exagerar el lóbulo daría una idea equivocada de la pieza: la de
    escritura varía 3,7 mm sobre 52 de radio y la del elevador 0,56. La
    forma se enseña aparte, amplificada y rotulada como tal."""
    assert "desviación ×8" in dibujo
