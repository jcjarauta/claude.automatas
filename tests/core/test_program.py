"""El programa indexado por ángulo: validación e ida y vuelta a JSON."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from core.program import Evento, PistaContinua, PistaEvento, Programa
from core.units import TAU, AnguloCiclo, Arco, Radianes, grados, vueltas

pytestmark = pytest.mark.core


def pista_x() -> PistaContinua:
    return PistaContinua(
        canal="x",
        unidad="m",
        thetas=[AnguloCiclo(0.0), grados(90.0), grados(180.0), grados(270.0)],
        valores=[0.0, 0.02, 0.0, -0.02],
    )


def pista_campana() -> PistaEvento:
    return PistaEvento(
        canal="campana",
        eventos=[
            Evento(theta=grados(45.0)),
            Evento(theta=grados(200.0), arco=Arco(grados(15.0))),
        ],
    )


# ---------------------------------------------------------------------------
# Ida y vuelta
# ---------------------------------------------------------------------------


def test_un_programa_sobrevive_a_json_identico():
    original = Programa(nombre="hola", pistas=[pista_x(), pista_campana()])
    vuelto = Programa.model_validate_json(original.model_dump_json())
    assert vuelto == original


def test_el_programa_admite_las_dos_clases_de_pista():
    programa = Programa(nombre="mixto", pistas=[pista_x(), pista_campana()])
    assert programa.canales == {"x", "campana"}
    assert programa.pista("x").tipo == "continua"
    assert programa.pista("campana").tipo == "evento"


def test_la_union_se_discrimina_al_deserializar():
    """Sin discriminador, pydantic podría elegir la clase equivocada en silencio."""
    crudo = Programa(nombre="mixto", pistas=[pista_x(), pista_campana()]).model_dump_json()
    vuelto = Programa.model_validate_json(crudo)
    assert isinstance(vuelto.pista("x"), PistaContinua)
    assert isinstance(vuelto.pista("campana"), PistaEvento)


# ---------------------------------------------------------------------------
# Invariantes de una pista continua
# ---------------------------------------------------------------------------


def test_los_angulos_deben_crecer():
    with pytest.raises(ValidationError, match="deben crecer"):
        PistaContinua(
            canal="x",
            unidad="m",
            thetas=[grados(90.0), grados(30.0)],
            valores=[0.0, 0.01],
        )


def test_no_se_admiten_angulos_repetidos():
    with pytest.raises(ValidationError, match="deben crecer"):
        PistaContinua(
            canal="x",
            unidad="m",
            thetas=[grados(30.0), grados(30.0)],
            valores=[0.0, 0.01],
        )


def test_debe_haber_tantos_angulos_como_valores():
    with pytest.raises(ValidationError, match="Deben ser tantos"):
        PistaContinua(
            canal="x",
            unidad="m",
            thetas=[AnguloCiclo(0.0), grados(90.0), grados(180.0)],
            valores=[0.0, 0.01],
        )


def test_no_se_almacena_la_muestra_de_una_vuelta_entera():
    """Sería la misma que la de cero y podría contradecirla."""
    with pytest.raises(ValidationError):
        PistaContinua(
            canal="x",
            unidad="m",
            thetas=[AnguloCiclo(0.0), Radianes(TAU)],
            valores=[0.0, 0.01],
        )


def test_una_pista_continua_no_puede_ser_binaria():
    with pytest.raises(ValidationError, match="no puede ser binaria"):
        PistaContinua(
            canal="x",
            unidad="binario",
            thetas=[AnguloCiclo(0.0), grados(90.0)],
            valores=[0.0, 1.0],
        )


def test_hacen_falta_al_menos_dos_muestras():
    with pytest.raises(ValidationError):
        PistaContinua(canal="x", unidad="m", thetas=[AnguloCiclo(0.0)], valores=[0.0])


# ---------------------------------------------------------------------------
# Invariantes de una pista de evento
# ---------------------------------------------------------------------------


def test_los_eventos_van_ordenados():
    with pytest.raises(ValidationError, match="ordenados"):
        PistaEvento(
            canal="campana",
            eventos=[Evento(theta=grados(200.0)), Evento(theta=grados(45.0))],
        )


def test_un_evento_instantaneo_no_tiene_arco():
    evento = Evento(theta=grados(45.0))
    assert evento.arco is None
    assert evento.fin == pytest.approx(float(grados(45.0)))


def test_el_fin_de_un_evento_puede_pasar_de_la_vuelta():
    """El ciclo da la vuelta: un evento que empieza en 350° y dura 20° es legal."""
    evento = Evento(theta=grados(350.0), arco=Arco(grados(20.0)))
    assert evento.fin > TAU


# ---------------------------------------------------------------------------
# Invariantes del programa
# ---------------------------------------------------------------------------


def test_un_canal_no_puede_tener_dos_pistas():
    with pytest.raises(ValidationError, match="dos veces el canal"):
        Programa(nombre="malo", pistas=[pista_x(), pista_x()])


def test_pedir_un_canal_que_no_existe_falla_claro():
    programa = Programa(nombre="hola", pistas=[pista_x()])
    with pytest.raises(KeyError, match="no tiene el canal"):
        programa.pista("z")


def test_el_programa_es_inmutable():
    programa = Programa(nombre="hola", pistas=[pista_x()])
    with pytest.raises(ValidationError):
        programa.nombre = "otro"  # type: ignore[misc]


def test_no_se_admiten_campos_de_mas():
    """Un campo mal escrito debe fallar, no ignorarse en silencio."""
    with pytest.raises(ValidationError):
        Programa(nombre="hola", pistas=[pista_x()], duracion=3.0)  # type: ignore[call-arg]


def test_una_vuelta_son_dos_pi():
    assert vueltas(1.0) == pytest.approx(TAU)
