"""Qué escriben las levas, recorridas por el perfil que se va a cortar."""

from __future__ import annotations

import numpy as np
import pytest

from compile.escribiente import SEGUIDORES, _psi_desde_la_leva, compilar
from compile.recorrido import UMBRAL_DE_APOYO, recorrer, segundos_por_vuelta
from core.cam.contacto import psi_por_contacto
from tests.casos import CASOS

pytestmark = pytest.mark.core


@pytest.fixture(scope="module")
def hola():
    return compilar(CASOS["hola"]())


def test_los_dos_caminos_leen_la_misma_leva(hola):
    """El perfil cortado y la curva de paso dan el mismo seguidor, a micro-
    radianes: si un día discrepan, el desplazamiento por el rodillo está mal
    o la pieza está socavada, y lo dice esto antes que el papel."""
    thetas = np.linspace(0.0, 2.0 * np.pi, 90, endpoint=False)
    for nombre in SEGUIDORES:
        perfil = hola.perfiles[nombre]
        contacto = psi_por_contacto(perfil.perfil, perfil.seguidor, thetas)
        paso = _psi_desde_la_leva(perfil, thetas)
        assert np.max(np.abs(contacto - paso)) < 2e-5, nombre


def test_el_error_contra_la_linea_no_depende_del_muestreo(hola):
    """Contra los puntos escritos, el error se dividía por dos al doblar las
    muestras: medía la separación entre ellas. Contra la línea converge."""
    medio = recorrer(hola, muestras=720).error_maximo
    fino = recorrer(hola, muestras=1440).error_maximo
    assert fino < 0.05e-3
    assert medio < 2.0 * fino + 0.01e-3


@pytest.mark.parametrize("caso", ["hola", "firma", "puntos"])
def test_escribe_tantos_trazos_como_pide_el_cliente(caso):
    compilacion = compilar(CASOS[caso]())
    r = recorrer(compilacion)
    trazos, vuelos = r.tramos()
    assert trazos == len(compilacion.escritura.trazos)
    assert vuelos == trazos
    assert 0.0 < r.fraccion_escribiendo < 1.0
    assert r.error_maximo < 0.05e-3


def test_la_frase_que_no_cabe_tambien_se_recorre():
    """«apretada» no cabe y el veredicto lo dice; sus levas se sintetizan
    igual, y recorrerlas tiene que dar un número, no un fallo. Que escriba
    peor que las que caben es lo esperable."""
    compilacion = compilar(CASOS["apretada"]())
    assert not compilacion.veredicto.apto
    r = recorrer(compilacion)
    assert np.isfinite(r.error_maximo)
    assert r.error_maximo > recorrer(compilar(CASOS["hola"]())).error_maximo


def test_el_umbral_de_apoyo_es_mucho_menor_que_el_levantamiento():
    """0,05 mm frente a la altura de levantamiento: un vuelo nunca pasa por
    trazo, y el ruido del contacto nunca pasa por vuelo."""
    from core.escritura import Capacidad

    assert float(Capacidad().altura_levantamiento) / 20.0 > UMBRAL_DE_APOYO


def test_la_frase_tarda_una_vuelta_del_arbol():
    """90 rpm de manivela con la reducción 3:1: dos segundos."""
    assert segundos_por_vuelta(90.0, 3.0) == pytest.approx(2.0)
