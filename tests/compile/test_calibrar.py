"""El cartucho de calibrar pone cada seguidor en su punto de diseño."""

from __future__ import annotations

import numpy as np
import pytest

from compile.calibrar import cartucho_de_calibrar
from compile.escribiente import SEGUIDORES, Escribiente, holguras_de_los_ejes
from core.cam.curves import desde_muestras, rejilla
from core.cam.synth import sintetizar

pytestmark = pytest.mark.core


def _radios(pieza) -> np.ndarray:
    return np.hypot(*np.array([[float(x), float(y)] for x, y in pieza.contorno]).T)


def test_cada_disco_es_redondo_al_radio_de_diseño_de_su_canal():
    m = Escribiente()
    for i, pieza in enumerate(cartucho_de_calibrar(m)):
        r = _radios(pieza)
        assert r.max() - r.min() < 1e-9, pieza.numero
        assert r.mean() == pytest.approx(m.radio_base_de(i) - float(m.radio_rodillo), abs=1e-9)


def test_lleva_el_pasador_de_fase_como_las_levas():
    """Es un cartucho: entra en la misma garra y en la misma U, y solo en
    fase cero."""
    from compile.escribiente import compilar
    from tests.casos import hola

    de_verdad = compilar(hola()).piezas[0].taladros
    for pieza in cartucho_de_calibrar():
        assert pieza.taladros == de_verdad


def test_los_ejes_de_los_rodillos_libran_los_discos_de_encima():
    m = Escribiente()
    thetas = rejilla(48)
    quieto = desde_muestras(thetas, np.zeros_like(thetas), n=720)
    perfiles = {n: sintetizar(quieto, m.seguidor(i)) for i, n in enumerate(SEGUIDORES)}
    holguras = holguras_de_los_ejes(perfiles, m)
    assert min(holguras.values()) >= float(m.holgura_eje_rodillo)
