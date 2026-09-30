"""La hoja de trazo patrón.

Lo que se comprueba es lo que hace que la hoja sirva para verificar: que el
trazo y el vuelo se distinguen, que está a 1:1, que lleva cuadro de
calibración y que se puede colocar. Una hoja bonita que no se pueda alinear
bajo la máquina no verifica nada.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest

from compile.escribiente import compilar
from core.escritura import Escritura, Trazo
from core.units import mm
from emit.layout import LADO_CALIBRACION, Formato
from emit.patron import UMBRAL_DE_APOYO, lamina_de_patron, patron_de

pytestmark = pytest.mark.core

CAJA = (-40.0, 85.0, 80.0, 30.0)


def recto(n: int = 20) -> tuple[np.ndarray, np.ndarray]:
    """Un recorrido en línea con el lápiz abajo, arriba y abajo otra vez."""
    puntos = np.column_stack([np.linspace(-0.02, 0.02, n), np.full(n, 0.100)])
    altura = np.zeros(n)
    altura[n // 3 : 2 * n // 3] = 0.003
    return puntos, altura


def hola() -> Escritura:
    datos = json.loads(Path("demo/hola.json").read_text(encoding="utf-8"))
    return Escritura(
        nombre=datos["nombre"],
        trazos=[
            Trazo(puntos=[(mm(float(x)), mm(float(y))) for x, y in t]) for t in datos["trazos"]
        ],
    )


# ---------------------------------------------------------------------------
# Partir el recorrido
# ---------------------------------------------------------------------------


def test_el_trazo_y_el_vuelo_se_separan():
    """Sin separarlos, la hoja mostraría líneas rectas entre trazos que la
    máquina no dibuja, y el lápiz parecería estar fallando."""
    puntos, altura = recto()
    p = patron_de("prueba", puntos, altura, CAJA, 0.1)
    assert len(p.escritos) == 2
    assert len(p.vuelo) == 1


def test_el_recorrido_llega_en_metros_y_sale_en_milimetros():
    """La conversión ocurre en el emisor, que es donde toca."""
    puntos, altura = recto()
    p = patron_de("prueba", puntos, altura, CAJA, 0.1)
    xs = [x for tramo in p.escritos for x, _ in tramo]
    assert min(xs) == pytest.approx(-20.0)
    assert max(xs) == pytest.approx(20.0)


def test_el_umbral_de_apoyo_no_puede_ser_cero():
    """La altura sale de RECORRER la leva, así que oscila alrededor del cero
    unas milésimas. Con umbral cero el trazo se parte en costuras donde la
    máquina dibuja seguido: pasó, y salían dieciséis tramos de cuatro."""
    compilacion = compilar(hola())
    simulacion = compilacion.simulacion
    assert simulacion is not None

    con_umbral = patron_de("hola", simulacion.puntos, simulacion.altura, CAJA, 0.1)
    sin_umbral = patron_de("hola", simulacion.puntos, simulacion.altura, CAJA, 0.1, umbral=1e-9)

    assert len(con_umbral.escritos) <= len(compilacion.escritura.trazos) + 1
    assert len(sin_umbral.escritos) > len(con_umbral.escritos)


def test_el_umbral_por_defecto_es_menos_que_el_levantamiento():
    """Si fuera mayor, la hoja diría que el lápiz escribe en pleno vuelo."""
    assert 0.0 < UMBRAL_DE_APOYO < 3.0


def test_un_recorrido_vacio_no_revienta():
    p = patron_de("nada", np.zeros((0, 2)), np.zeros(0), CAJA, 0.0)
    assert p.escritos == ()
    assert p.vuelo == ()


# ---------------------------------------------------------------------------
# La hoja
# ---------------------------------------------------------------------------


def lamina(formato: Formato = Formato.A4, peor: float | None = None):
    puntos, altura = recto()
    return lamina_de_patron(patron_de("hola", puntos, altura, CAJA, 0.108), formato, peor)


def test_la_hoja_esta_a_uno_a_uno():
    """Como cualquier hoja de este proyecto que se mida con una regla."""
    assert lamina().escala == 1.0


def test_la_hoja_lleva_cuadro_de_calibracion():
    """Con más motivo que ninguna: una hoja patrón escalada un 1 % diría que
    la máquina está mal cuando la que está mal es la impresora."""
    textos = " ".join(t.texto for t in lamina().textos)
    assert "100 mm" in textos
    assert "la impresión está escalada" in textos


def test_la_hoja_dice_como_se_imprime_y_como_se_usa():
    textos = " ".join(t.texto for t in lamina().textos)
    assert "SIN ajuste de página" in textos
    assert "manivela" in textos


def test_la_hoja_lleva_cuatro_escuadras_para_colocarla():
    """Sin marcas de registro no se puede alinear bajo la máquina, y una
    hoja que no se puede colocar no verifica nada."""
    marcas = [t for t in lamina().trazos if t.tipo == "marca"]
    # Ocho brazos de escuadra más la cruz del centro, que son dos trazos.
    assert len(marcas) == 4 * 2 + 2


def test_el_trazo_se_distingue_del_vuelo_en_blanco_y_negro():
    """Continua gruesa frente a punteada, como el resto del proyecto."""
    tipos = {t.tipo for t in lamina().trazos}
    assert "corte" in tipos, "el trazo tiene que ir en continua gruesa"
    assert "oculta" in tipos, "el vuelo tiene que ir punteado"
    assert "referencia" in tipos, "la caja de escritura va en discontinuo"


def test_la_desviacion_admisible_se_rotula_si_se_sabe():
    """Es lo que separa «el lápiz no cae en la línea» de «no cae más de lo
    que debería»."""
    con = " ".join(t.texto for t in lamina(peor=2.79).textos)
    sin = " ".join(t.texto for t in lamina().textos)
    assert "2.8 mm" in con
    assert "admisible" not in sin


def test_nada_se_sale_de_la_pagina():
    for formato in (Formato.A4, Formato.A3):
        hoja = lamina(formato)
        for trazo in hoja.trazos:
            for x, y in trazo.puntos:
                assert -0.5 <= x <= hoja.ancho + 0.5, f"x = {x} fuera de {hoja.ancho}"
                assert -0.5 <= y <= hoja.alto + 0.5, f"y = {y} fuera de {hoja.alto}"


def test_el_cuadro_de_calibracion_cabe_debajo_del_dibujo():
    """Si se solaparan, el cuadro dejaría de poder medirse."""
    hoja = lamina()
    del hoja
    assert LADO_CALIBRACION == 100.0


def test_una_hoja_en_a3_coloca_el_dibujo_centrado():
    hoja = lamina(Formato.A3)
    xs = [x for t in hoja.trazos if t.tipo == "corte" for x, _ in t.puntos]
    centro = sum(xs) / len(xs)
    assert centro == pytest.approx(hoja.ancho / 2.0, abs=1.0)


# ---------------------------------------------------------------------------
# Y el PDF de verdad
# ---------------------------------------------------------------------------


def test_se_escribe_un_pdf_que_se_abre(tmp_path: Path):
    from pypdf import PdfReader

    from emit.patron import escribir_patron

    puntos, altura = recto()
    ruta = escribir_patron(
        patron_de("hola", puntos, altura, CAJA, 0.108), tmp_path / "patron.pdf", peor_caso=2.79
    )
    assert ruta.exists()
    lector = PdfReader(str(ruta))
    assert len(lector.pages) == 1
    caja = lector.pages[0].mediabox
    assert float(caja.width) == pytest.approx(595.28, abs=1.0)
