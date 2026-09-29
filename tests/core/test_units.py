"""Unidades: conversión y rechazo de magnitudes implausibles."""

from __future__ import annotations

import math

import pytest
from pydantic import BaseModel, ValidationError

from core.units import (
    TAU,
    AnguloCiclo,
    Longitud,
    Metros,
    Radianes,
    a_grados,
    a_mm,
    a_vueltas,
    grados,
    mm,
    vueltas,
)

pytestmark = pytest.mark.core


class _Pieza(BaseModel):
    radio: Longitud
    theta: AnguloCiclo


# ---------------------------------------------------------------------------
# Conversión
# ---------------------------------------------------------------------------


def test_milimetros_a_metros():
    assert mm(80.0) == pytest.approx(0.08)
    assert mm(0.1) == pytest.approx(0.0001)


def test_grados_a_radianes():
    assert grados(180.0) == pytest.approx(math.pi)
    assert grados(30.0) == pytest.approx(0.5235987755982988)


def test_vueltas_a_radianes():
    assert vueltas(0.25) == pytest.approx(TAU / 4)
    assert vueltas(1.0) == pytest.approx(TAU)


@pytest.mark.parametrize("valor", [0.1, 1.0, 80.0, 1234.5])
def test_la_conversion_va_y_vuelve(valor: float):
    assert a_mm(mm(valor)) == pytest.approx(valor)
    assert a_grados(grados(valor)) == pytest.approx(valor)
    assert a_vueltas(vueltas(valor)) == pytest.approx(valor)


# ---------------------------------------------------------------------------
# Rechazo de magnitudes implausibles
#
# El error real no es pasar un tipo equivocado — eso lo caza mypy — sino
# escribir el número en la unidad equivocada. Estos tests comprueban que los
# rangos de plausibilidad lo detectan.
# ---------------------------------------------------------------------------


def test_un_radio_en_milimetros_sin_convertir_es_rechazado():
    """80 son 80 mm en la cabeza de quien escribe, y 80 metros para el campo."""
    with pytest.raises(ValidationError, match="less than or equal to 10"):
        _Pieza(radio=Metros(80.0), theta=AnguloCiclo(0.0))


def test_un_angulo_en_grados_sin_convertir_es_rechazado():
    """90 grados son 1,57 rad. Pasar 90 donde se esperan radianes es 14 vueltas."""
    with pytest.raises(ValidationError, match=r"less than 6\.28"):
        _Pieza(radio=mm(80.0), theta=Radianes(90.0))


def test_un_radio_negativo_o_nulo_es_rechazado():
    with pytest.raises(ValidationError):
        _Pieza(radio=Metros(0.0), theta=AnguloCiclo(0.0))
    with pytest.raises(ValidationError):
        _Pieza(radio=Metros(-0.05), theta=AnguloCiclo(0.0))


def test_el_angulo_de_ciclo_excluye_la_vuelta_entera():
    """θ vive en [0, 2π). El punto final no se almacena: sería el inicial."""
    _Pieza(radio=mm(80.0), theta=AnguloCiclo(TAU - 1e-9))
    with pytest.raises(ValidationError):
        _Pieza(radio=mm(80.0), theta=Radianes(TAU))


def test_los_valores_bien_convertidos_pasan():
    pieza = _Pieza(radio=mm(80.0), theta=grados(90.0))
    assert a_mm(pieza.radio) == pytest.approx(80.0)
    assert a_grados(pieza.theta) == pytest.approx(90.0)
