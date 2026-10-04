"""La cadena del levantamiento contra el contrato.

Las cotas que se derivan de la geometría —la bieleta, la x del eje del
balancín— se recalculan aquí y se cruzan con lo que dice el contrato. Si
alguien mueve el seguidor, el poste o el tirante, esto avisa de que la
bieleta ya no es la que está en el contrato.
"""

from __future__ import annotations

import math

import pytest

from compile.contratos import cargar
from compile.escribiente import Escribiente
from compile.levantamiento import bieleta_isogona, calaje_elevador, eje_balancin_x


@pytest.fixture(scope="module")
def contratos():
    return cargar()


@pytest.fixture(scope="module")
def bieleta(contratos):
    return bieleta_isogona(contratos, Escribiente())


def _valor(contratos, nombre):
    return float(contratos.variables()[nombre].valor)


def test_el_pasador_del_seguidor_3_no_esta_en_el_eje_de_simetria(bieleta):
    """Es el error que tumbó la bieleta de 25: se dio por hecho que el
    pasador caía en x = 0 del cinco barras, y el seguidor apunta a 9,3° en el
    marco de la leva, no a -90° en el del cinco barras."""
    assert bieleta.pasador[0] == pytest.approx(-0.02941, abs=1e-5)
    assert bieleta.pasador[1] == pytest.approx(0.014549, abs=1e-5)


def test_la_bieleta_es_isogona(bieleta):
    assert bieleta.factor == pytest.approx(1.0, abs=1e-12)


def test_el_contrato_lleva_la_bieleta_que_sale_de_la_geometria(contratos, bieleta):
    assert _valor(contratos, "bieleta_entre_centros") == pytest.approx(bieleta.largo, abs=1e-5)


def test_el_eje_del_balancin_pone_el_tirante_en_su_sitio(contratos):
    x = eje_balancin_x(contratos)
    assert _valor(contratos, "balancin_eje_x") == pytest.approx(x, abs=1e-6)
    palanca = _valor(contratos, "brazo_palanca")
    assert x + palanca * math.cos(calaje_elevador(contratos)) == pytest.approx(
        _valor(contratos, "tirante_x")
    )


def test_el_calaje_del_contrato_es_el_de_media_altura(contratos):
    """El de la cadena es el mismo número que el congelado del compilador."""
    assert calaje_elevador(contratos) == pytest.approx(
        _valor(contratos, "calaje_elevador"), abs=1e-9
    )


def test_la_mesa_baja_lo_que_la_leva_manda(contratos, bieleta):
    """Cinemática exacta, no lineal: el seguidor recorre los 0,475 mm de su
    pasador y la palanca tiene que bajar el tirante los 3 mm de
    altura_levantamiento, no los 2,45 que daba la bieleta de 25."""
    r = _valor(contratos, "levantamiento_pasador_al_pivote")
    e = _valor(contratos, "balancin_entrada")
    palanca = _valor(contratos, "brazo_palanca")
    relacion = Escribiente().relacion
    calaje = calaje_elevador(contratos)
    medio_giro = calaje / relacion  # lo que se desvía el seguidor a cada lado
    psi0 = math.atan2(
        bieleta.pasador[1] - bieleta.pivote[1], bieleta.pasador[0] - bieleta.pivote[0]
    )

    def giro_del_eje(dpsi):
        sx = bieleta.pivote[0] + r * math.cos(psi0 + dpsi)
        sy = bieleta.pivote[1] + r * math.sin(psi0 + dpsi)

        def resto(g):
            ox = bieleta.ojo[0] + e * math.sin(g)
            return math.hypot(ox - sx, bieleta.ojo[1] - sy) - bieleta.largo

        a, b = -0.5, 0.5
        for _ in range(100):
            g = (a + b) / 2
            a, b = (g, b) if (resto(g) > 0) == (resto(a) > 0) else (a, g)
        return (a + b) / 2

    baja = palanca * (math.sin(giro_del_eje(medio_giro)) - math.sin(giro_del_eje(-medio_giro)))
    assert baja == pytest.approx(0.003, abs=2e-6)
