"""El escape Graham montado: la envolvente de conjunto que faltaba.

Ninguna comprobacion de pieza suelta ve si la paleta cabe entre dos dientes,
si el diente apoya en la punta o en la cara, o si la rueda retrocede durante
el reposo. Eso solo sale de **montar las piezas y moverlas**: se gira el
ancora en pasos pequenos y se deja avanzar la rueda hasta que toca.

La geometria de la propuesta del banco R2 vive en `docs/reloj/escape-r2.json`
y la carga `compile.escape_r2`. Cuando pase al contrato, estos tests se quedan
y cambia de donde leen.
"""

from __future__ import annotations

import dataclasses
import math

import numpy as np
import pytest

from compile.escape_r2 import geometria
from core.reloj.graham import (
    AncoraGraham,
    RuedaGraham,
    contacto_en_reposo,
    juzgar,
    marcha,
    nariz,
)
from core.units import grados, mm

AMPLITUD = grados(3.0)


def _codigos(veredicto: object) -> set[str]:
    return {i.codigo for i in veredicto.incidencias}  # type: ignore[attr-defined]


@pytest.fixture(scope="module")
def propuesta() -> tuple[RuedaGraham, AncoraGraham]:
    return geometria()


# ---------------------------------------------------------------------------
# Lo que tiene que hacer un Graham, en una oscilacion
# ---------------------------------------------------------------------------


def test_la_rueda_avanza_medio_diente_por_golpe(propuesta):
    rueda, ancora = propuesta
    m = marcha(rueda, ancora, AMPLITUD, oscilaciones=2)
    assert m.atasco is None
    # dos oscilaciones = cuatro golpes = dos dientes
    assert m.phi[-1] - m.phi[0] == pytest.approx(2 * rueda.paso, abs=grados(0.05))


def test_en_reposo_la_rueda_no_se_mueve(propuesta):
    """Lo que define al Graham: mientras el diente apoya en el arco, el ancora
    gira y la rueda no. Mas alla del impulso, nada de la rueda se mueve."""
    rueda, ancora = propuesta
    m = marcha(rueda, ancora, AMPLITUD, oscilaciones=2)
    lejos = np.abs(m.theta) > ancora.impulso + grados(0.3)
    saltos = np.abs(np.diff(m.phi))[lejos[1:]]
    assert saltos.max() < grados(0.01)


def test_solo_toca_la_punta(propuesta):
    rueda, ancora = propuesta
    radio = contacto_en_reposo(rueda, ancora, AMPLITUD)
    assert radio == pytest.approx(rueda.radio_punta, abs=mm(0.02))


def test_la_entrada_bloquea_por_fuera_y_la_salida_por_dentro(propuesta):
    """El diente de entrada viaja hacia el eje del ancora y el de salida se
    aleja de el: la cara de caida de una queda mas cerca del eje y la de la
    otra mas lejos que el arco de reposo."""
    _, ancora = propuesta
    entrada, salida = nariz(ancora, "entrada"), nariz(ancora, "salida")
    assert entrada.radio_reposo == pytest.approx(salida.radio_reposo)
    assert entrada.radio_caida < entrada.radio_reposo < salida.radio_caida


def test_la_esquina_de_caida_entra_mas_que_la_de_reposo(propuesta):
    """Es la que empuja el diente al salir. Al reves no hay impulso: el diente
    pasa por debajo del plano sin tocarlo y la rueda se desboca."""
    _, ancora = propuesta
    for lado in ("entrada", "salida"):
        n = nariz(ancora, lado)
        assert math.hypot(*n.caida) < math.hypot(*n.reposo)


# ---------------------------------------------------------------------------
# Lo que la envolvente tiene que cazar
# ---------------------------------------------------------------------------


def test_un_diente_en_cuna_retrocede(propuesta):
    """La cara de ataque con el pie por delante de la punta: la paleta apoya en
    la cara, no en la punta, y al profundizar empuja la rueda hacia atras."""
    rueda, ancora = propuesta
    cuna = dataclasses.replace(rueda, socavado=-rueda.socavado)
    veredicto = juzgar(cuna, ancora, AMPLITUD, oscilaciones=3)
    assert "retroceso_en_reposo" in _codigos(veredicto)


def test_una_paleta_que_no_cabe_entre_dientes_se_atasca(propuesta):
    rueda, ancora = propuesta
    ancha = dataclasses.replace(ancora, ancho_trabajo=mm(9.0))
    veredicto = juzgar(rueda, ancha, AMPLITUD, oscilaciones=2)
    assert "escape_atascado" in _codigos(veredicto)
    assert not veredicto.apto


def test_sin_reposo_el_escape_se_desboca(propuesta):
    """Si la paleta no llega a entrar en la rueda, nada la para."""
    rueda, ancora = propuesta
    corta = dataclasses.replace(ancora, reposo=grados(-12.0))
    veredicto = juzgar(rueda, corta, AMPLITUD, oscilaciones=1)
    assert "escape_desbocado" in _codigos(veredicto)


def test_escalar_todo_no_cambia_los_angulos(propuesta):
    """Hacer el escape el doble de grande no cambia caida ni impulso en grados.
    Lo que cambia es cuanto pesa el error de sierra, que es en milimetros."""
    rueda, ancora = propuesta
    r2, a2 = geometria(escala=2.0)
    v1 = juzgar(rueda, ancora, AMPLITUD, oscilaciones=2)
    v2 = juzgar(r2, a2, AMPLITUD, oscilaciones=2)
    for clave in ("caida_min", "impulso_rueda", "avance_por_golpe"):
        assert v2.metricas[clave] == pytest.approx(v1.metricas[clave], abs=grados(0.02))


# ---------------------------------------------------------------------------
# La vuelta entera, que es la prueba de verdad
# ---------------------------------------------------------------------------


@pytest.mark.slow
def test_la_propuesta_da_la_vuelta_entera(propuesta):
    """Cada diente pasa por las dos paletas. Ni atasco, ni desboque, ni
    retroceso, y la rueda avanza exactamente una vuelta."""
    rueda, ancora = propuesta
    veredicto = juzgar(rueda, ancora, AMPLITUD)
    assert veredicto.apto, [i.mensaje for i in veredicto.incidencias]
    assert veredicto.metricas["vuelta"] == pytest.approx(
        (rueda.dientes + 1) * rueda.paso, abs=grados(0.1)
    )


@pytest.mark.slow
@pytest.mark.parametrize("semilla", [1, 2, 3])
def test_aguanta_el_error_de_sierra(propuesta, semilla):
    """Rueda cortada a mano: cada diente desplazado y con el radio cambiado al
    azar hasta 0,3 mm, que es lo que se le pide al corte con segueta."""
    rueda, ancora = propuesta
    serrada = rueda.con_error_de_sierra(mm(0.3), semilla)
    veredicto = juzgar(serrada, ancora, AMPLITUD)
    assert veredicto.apto, [i.mensaje for i in veredicto.incidencias]


@pytest.mark.slow
def test_una_paleta_demasiado_ancha_no_aguanta_la_sierra(propuesta):
    """La razon de que la paleta mida 2,2 y no 2,75: con 2,75 el diente que
    acaba de pasar no deja sitio a la paleta de salida cuando la rueda tiene
    error de sierra."""
    rueda, ancora = propuesta
    ancha = dataclasses.replace(ancora, ancho_trabajo=mm(2.75))
    fallos = sum(
        not juzgar(rueda.con_error_de_sierra(mm(0.3), s), ancha, AMPLITUD).apto for s in (1, 2, 3)
    )
    assert fallos >= 2


@pytest.mark.slow
def test_a_doble_escala_la_paleta_ancha_aguanta_la_sierra():
    """Por que el banco R2 se imprime al doble en A3: el error de sierra es en
    milimetros y los angulos no cambian al escalar. Al doble, la paleta de
    2,75 equivalentes -que a escala 1 se atasca- aguanta el mismo 0,3 mm."""
    rueda, ancora = geometria(escala=2.0)
    ancha = dataclasses.replace(ancora, ancho_trabajo=mm(5.5))
    for s in (1, 2, 3):
        veredicto = juzgar(rueda.con_error_de_sierra(mm(0.3), s), ancha, AMPLITUD)
        assert veredicto.apto, [i.mensaje for i in veredicto.incidencias]
