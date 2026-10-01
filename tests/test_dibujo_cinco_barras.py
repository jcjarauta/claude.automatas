"""La hoja del cinco barras y la palanca.

Igual que la de las piezas comerciales, esta hoja se tiene al lado mientras se
dibuja en el CAD, así que lo que hay que atar es lo mismo: que la postura que
enseña sea la que calcula el compilador, y que cada variable que rotula exista
de verdad en el CSV que se importa.
"""

from __future__ import annotations

import math
from pathlib import Path

import numpy as np
import pytest

from compile.escribiente import Escribiente
from scripts.dibujar_cinco_barras import contrato, filas, hoja, main, postura

pytestmark = pytest.mark.core


def test_la_postura_dibujada_es_un_varillaje_que_cierra():
    """**No se dibuja a mano una postura, se pregunta por ella.**

    Los cinco puntos salen de la cinemática inversa del propio compilador, así
    que las cuatro barras miden exactamente lo que dice el contrato. Si alguien
    tocara una longitud y no la otra, el varillaje dejaría de cerrar y esto lo
    diría antes de que nadie dibujara nada.
    """
    maquina = Escribiente()
    p = postura(maquina)
    largo = lambda a, b: float(np.linalg.norm(p[a] - p[b]))  # noqa: E731
    assert largo("pivote_izq", "codo_izq") == pytest.approx(float(maquina.proximal))
    assert largo("pivote_der", "codo_der") == pytest.approx(float(maquina.proximal))
    assert largo("codo_izq", "punta") == pytest.approx(float(maquina.distal))
    assert largo("codo_der", "punta") == pytest.approx(float(maquina.distal))
    assert largo("pivote_izq", "pivote_der") == pytest.approx(float(maquina.separacion))


def test_la_punta_dibujada_esta_en_el_centro_de_la_caja():
    """Que es la referencia del calaje, y por eso se dibuja esta postura y no
    otra: con el brazo montado a otro ángulo la máquina escribe basura."""
    maquina = Escribiente()
    punta = postura(maquina)["punta"]
    assert punta[0] == pytest.approx(0.0)
    assert punta[1] == pytest.approx(float(maquina.caja_centro_y))


def test_los_codos_van_hacia_fuera_y_los_proximales_se_cruzan():
    """La rama elegida, hecha test. Un varillaje tiene dos soluciones por
    punto; con la otra el dibujo sería distinto y la leva también. Y la
    consecuencia visible —que los dos proximales se crucen— es la razón por la
    que el rótulo del proximal no puede ir sobre la barra."""
    p = postura(Escribiente())
    assert p["codo_izq"][0] > 0.0 > p["codo_der"][0]


def test_cada_variable_que_rotula_existe_en_el_contrato():
    """Misma regla que en la hoja de piezas: lo que se imprime se teclea, así
    que tiene que existir. Aquí se cruza contra el contrato, que es de donde
    salen los CSV."""
    c = contrato()
    for cual in ("proximal", "distal", "palanca"):
        for etiqueta, _ in filas(c, cual):
            nombre = etiqueta[1:].partition(".")[2]
            assert nombre in c, f"{etiqueta} no está en docs/contratos.json"


def test_el_calaje_se_rotula_en_grados_y_no_en_radianes():
    """El contrato lo guarda en radianes, como manda la regla 3, y el CAD lo
    pide en grados. Un calaje de -0,065 tecleado como grados monta el brazo a
    un sitio que no es, y el error no da ningún aviso."""
    c = contrato()
    valores = dict(filas(c, "proximal"))
    rotulado = float(valores["#angulo.calaje_izquierdo"])
    assert rotulado == pytest.approx(math.degrees(c["calaje_izquierdo"]), abs=1e-3)
    assert abs(rotulado) > abs(c["calaje_izquierdo"])


def test_la_hoja_avisa_de_lo_que_no_esta_decidido():
    """El contorno de las barras no está en ningún contrato. Una hoja que no
    lo dijera invita a tomarse por cota lo que es un dibujo."""
    texto = hoja()
    assert "SIN DEFINIR" in texto
    assert "#cota.brazo_proximal" in texto
    assert "#angulo.calaje_elevador" in texto


def test_se_escribe_donde_se_le_pide(tmp_path: Path):
    destino = tmp_path / "barras.svg"
    assert main(["--out", str(destino)]) == 0
    assert destino.read_text(encoding="utf-8").startswith("<?xml")
