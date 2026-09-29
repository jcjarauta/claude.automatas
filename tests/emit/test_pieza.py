"""La pieza y sus siete metadatos obligatorios."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from core.units import Metros, a_mm, mm
from emit.pieza import Pieza, Taladro, Veta
from tests.emit.piezas_de_prueba import leva

pytestmark = pytest.mark.core

SIETE_METADATOS = (
    "nombre",
    "numero",
    "conjunto",
    "material",
    "espesor",
    "cantidad",
    "veta",
)


@pytest.mark.parametrize("campo", SIETE_METADATOS)
def test_falta_un_metadato_y_la_pieza_no_se_construye(campo: str):
    """Ninguno tiene valor por defecto. Una plantilla impresa sin material ni
    espesor obliga a preguntar, y quien la recibe está en otro taller."""
    base = leva().model_dump()
    del base[campo]
    with pytest.raises(ValidationError):
        Pieza(**base)


def test_son_exactamente_siete():
    """Si alguien añade o quita un obligatorio, este test lo dice."""
    obligatorios = {
        nombre
        for nombre, campo in Pieza.model_fields.items()
        if campo.is_required() and nombre != "contorno"
    }
    assert obligatorios == set(SIETE_METADATOS)


def test_los_metadatos_no_admiten_cadenas_vacias():
    with pytest.raises(ValidationError):
        leva(material="")


def test_la_cantidad_no_puede_ser_cero():
    with pytest.raises(ValidationError):
        leva(cantidad=0)


def test_el_espesor_va_en_metros_y_rechaza_milimetros_sueltos():
    """Pasar 5 pensando en milímetros son 5 metros de tablero."""
    with pytest.raises(ValidationError):
        leva(espesor=Metros(5.0))


# ---------------------------------------------------------------------------
# Geometría
# ---------------------------------------------------------------------------


def test_el_contorno_no_repite_el_punto_de_cierre():
    """Mismo criterio que las pistas del programa: el cierre es implícito."""
    with pytest.raises(ValidationError, match="repite el punto de cierre"):
        leva(
            contorno=[
                (Metros(0.0), Metros(0.0)),
                (Metros(0.1), Metros(0.0)),
                (Metros(0.1), Metros(0.1)),
                (Metros(0.0), Metros(0.0)),
            ]
        )


def test_un_contorno_de_menos_de_tres_puntos_no_es_una_pieza():
    with pytest.raises(ValidationError):
        leva(contorno=[(Metros(0.0), Metros(0.0)), (Metros(0.1), Metros(0.0))])


def test_la_caja_envolvente_incluye_los_taladros():
    """Un taladro que asome fuera del contorno sigue habiendo que dibujarlo."""
    pieza = leva(
        contorno=[
            (Metros(0.0), Metros(0.0)),
            (Metros(0.1), Metros(0.0)),
            (Metros(0.1), Metros(0.1)),
            (Metros(0.0), Metros(0.1)),
        ],
        taladros=[Taladro(centro=(Metros(0.12), Metros(0.05)), diametro=mm(10.0))],
        referencias=[],
        marca_fase=None,
    )
    assert a_mm(pieza.ancho) == pytest.approx(125.0)


def test_la_leva_de_referencia_mide_lo_que_se_espera():
    pieza = leva()
    assert 60.0 < a_mm(pieza.ancho) < 110.0
    assert 60.0 < a_mm(pieza.alto) < 110.0


def test_la_pieza_es_inmutable():
    with pytest.raises(ValidationError):
        leva().nombre = "otra"  # type: ignore[misc]


def test_la_veta_solo_admite_los_valores_del_enum():
    with pytest.raises(ValidationError):
        leva(veta="diagonal")
    assert leva(veta=Veta.LARGO).veta is Veta.LARGO
