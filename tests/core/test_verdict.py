"""El veredicto: un fallo de envolvente es un resultado, no una excepción."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from core.units import grados
from core.verdict import Incidencia, Veredicto

pytestmark = pytest.mark.core


def error() -> Incidencia:
    return Incidencia(
        gravedad="error",
        codigo="angulo_presion_excedido",
        mensaje="El ángulo de presión llega a 38°, por encima del límite de 30°.",
        theta=grados(212.0),
        sugerencia="Agranda el círculo base o reparte más grados en ese trazo.",
    )


def aviso() -> Incidencia:
    return Incidencia(
        gravedad="aviso",
        codigo="curvatura_justa",
        mensaje="El radio de curvatura mínimo es 2,1 veces el del rodillo.",
        theta=grados(95.0),
    )


def test_un_veredicto_vacio_es_apto():
    assert Veredicto().apto is True


def test_un_aviso_no_impide_fabricar():
    assert Veredicto(incidencias=(aviso(),)).apto is True


def test_un_error_lo_impide():
    assert Veredicto(incidencias=(aviso(), error())).apto is False


def test_apto_se_calcula_y_no_se_puede_contradecir():
    """Un apto entrante se descarta: la única verdad son las incidencias."""
    v = Veredicto.model_validate({"incidencias": [error().model_dump()], "apto": True})
    assert v.apto is False


def test_un_campo_mal_escrito_sigue_fallando():
    """Descartar `apto` no debe abrir la puerta a que pasen erratas."""
    with pytest.raises(ValidationError):
        Veredicto.model_validate({"incidencias": [], "metrikas": {}})


def test_apto_viaja_en_el_json():
    crudo = Veredicto(incidencias=(error(),)).model_dump_json()
    assert '"apto":false' in crudo.replace(" ", "")


def test_el_veredicto_sobrevive_a_json_identico():
    original = Veredicto(
        incidencias=(aviso(), error()),
        metricas={"angulo_presion_max": 38.0, "curvatura_min_ratio": 2.1},
    )
    assert Veredicto.model_validate_json(original.model_dump_json()) == original


def test_separa_errores_de_avisos():
    v = Veredicto(incidencias=(aviso(), error()))
    assert len(v.errores) == 1
    assert len(v.avisos) == 1


def test_anadir_incidencias_devuelve_otro_veredicto_y_no_muta():
    original = Veredicto()
    nuevo = original.con(error())
    assert original.apto is True
    assert nuevo.apto is False
    assert len(original.incidencias) == 0


def test_cada_incidencia_puede_decir_donde_ocurre():
    assert error().theta is not None
    assert Incidencia(gravedad="aviso", codigo="c", mensaje="m").theta is None
