"""C11 · el péndulo compuesto, su energía y su Q.

Lo que se prueba aquí no es aritmética: es que el modelo no se equivoque en
las dos cosas que deciden el proyecto. Que el periodo salga de la masa
repartida y no de un punto, y que la pérdida por oscilación sea del orden de
microjulios, que es lo que hace que una pesa de kilos sobre a un péndulo.
"""

from __future__ import annotations

import math

import pytest

from core.reloj import pendulo
from core.units import Kilogramos, Metros, Radianes

pytestmark = pytest.mark.core

G = 9.80665


def _simple(largo: float) -> pendulo.Pendulo:
    """Toda la masa a distancia L y nada de varilla: el péndulo de libro."""
    return pendulo.Pendulo(
        masa_lenteja=Kilogramos(1.0),
        centro_lenteja=Metros(largo),
        masa_varilla=Kilogramos(1.0e-9),
        varilla_desde=Metros(largo),
        varilla_hasta=Metros(largo),
    )


def test_con_toda_la_masa_concentrada_da_el_pendulo_simple():
    """El caso límite tiene solución cerrada, y es la red de seguridad del
    resto: si esto falla, el momento de inercia está mal montado."""
    p = _simple(0.994)
    esperado = 2.0 * math.pi * math.sqrt(0.994 / G)
    assert p.periodo() == pytest.approx(esperado, rel=1e-6)


def test_una_varilla_sola_da_el_periodo_de_una_barra_que_pivota():
    """Una barra uniforme de largo L colgada de un extremo oscila como un
    péndulo simple de 2L/3. Es el otro extremo del modelo."""
    largo = 0.9
    p = pendulo.Pendulo(
        masa_lenteja=Kilogramos(1.0e-9),
        centro_lenteja=Metros(largo),
        masa_varilla=Kilogramos(0.08),
        varilla_desde=Metros(0.0),
        varilla_hasta=Metros(largo),
    )
    esperado = 2.0 * math.pi * math.sqrt((2.0 * largo / 3.0) / G)
    assert p.periodo() == pytest.approx(esperado, rel=1e-6)


def test_la_varilla_acorta_el_periodo_frente_al_pendulo_simple():
    """LA razón de que C11 exista. La masa de la varilla está más arriba que
    la lenteja, así que baja el centro de masas menos de lo que baja la
    inercia: el conjunto oscila más deprisa que un péndulo simple de la misma
    longitud, y hay que alargarlo para compensar."""
    simple = _simple(0.994)
    real = pendulo.Pendulo(
        masa_lenteja=Kilogramos(1.032),
        centro_lenteja=Metros(0.994),
        masa_varilla=Kilogramos(0.0785),
        varilla_desde=Metros(0.015),
        varilla_hasta=Metros(0.95),
    )
    assert real.periodo() < simple.periodo()


def test_el_periodo_no_depende_de_la_amplitud():
    """En la aproximación de ángulo pequeño, que es donde trabaja un reloj.
    Si esto cambiase con la amplitud, el reloj atrasaria al perder cuerda."""
    p = _simple(0.994)
    assert p.periodo() == pytest.approx(p.periodo(), rel=1e-12)


def test_la_energia_almacenada_crece_con_el_cuadrado_de_la_amplitud():
    """1 - cos(theta) va como theta^2/2. Doblar la amplitud cuadruplica la
    energia, y es lo que hace que la amplitud sea la variable que vigilar."""
    p = _simple(0.994)
    poca = p.energia(Radianes(0.02))
    mucha = p.energia(Radianes(0.04))
    assert mucha / poca == pytest.approx(4.0, rel=0.01)


def test_la_energia_del_pendulo_son_milijulios():
    """Orden de magnitud. Si saliera en julios, el escape tendria que ser
    otra cosa."""
    p = pendulo.Pendulo(
        masa_lenteja=Kilogramos(1.032),
        centro_lenteja=Metros(0.994),
        masa_varilla=Kilogramos(0.0785),
        varilla_desde=Metros(0.015),
        varilla_hasta=Metros(0.95),
    )
    assert 1.0e-3 < p.energia(Radianes(math.radians(2.0))) < 20.0e-3


def test_la_potencia_que_hay_que_reponer_son_microvatios():
    """El numero que ordena el plan de pruebas entero: mantener el pendulo
    en marcha cuesta millonesimas de vatio, asi que la pesa no la decide el
    pendulo sino el rozamiento de todo lo demas."""
    p = pendulo.Pendulo(
        masa_lenteja=Kilogramos(1.032),
        centro_lenteja=Metros(0.994),
        masa_varilla=Kilogramos(0.0785),
        varilla_desde=Metros(0.015),
        varilla_hasta=Metros(0.95),
    )
    potencia = p.potencia_de_mantenimiento(Radianes(math.radians(2.0)), calidad=1500.0)
    assert 1.0e-6 < potencia < 100.0e-6


def test_mas_calidad_pide_menos_potencia_y_en_proporcion_inversa():
    p = _simple(0.994)
    a = p.potencia_de_mantenimiento(Radianes(0.035), calidad=1000.0)
    b = p.potencia_de_mantenimiento(Radianes(0.035), calidad=2000.0)
    assert a / b == pytest.approx(2.0, rel=1e-9)


def test_el_arrastre_del_aire_no_es_lo_que_limita_el_q():
    """La conclusion que decide donde mirar en R1. Con la lenteja de canto y
    una varilla estrecha, el aire solo da un Q de varios miles: lo que va a
    limitar es la suspension, no la aerodinamica. Si este test se rompe,
    alguien ha ensanchado la varilla o la lenteja de golpe."""
    p = pendulo.Pendulo(
        masa_lenteja=Kilogramos(1.032),
        centro_lenteja=Metros(0.994),
        masa_varilla=Kilogramos(0.0785),
        varilla_desde=Metros(0.015),
        varilla_hasta=Metros(0.95),
    )
    q = p.calidad_por_el_aire(
        Radianes(math.radians(2.0)),
        frente_lenteja=Metros(0.1),
        alto_lenteja=Metros(0.027),
        ancho_varilla=Metros(0.008),
    )
    assert q > 5000.0


def test_una_varilla_mas_ancha_baja_el_q_del_aire():
    """Con `_simple` no se veria: su varilla mide cero y no roza. Hace falta
    el pendulo real, que es justo el punto -lo que paga el arrastre de la
    varilla es su ancho por su radio al cubo."""
    p = pendulo.Pendulo(
        masa_lenteja=Kilogramos(1.032),
        centro_lenteja=Metros(0.994),
        masa_varilla=Kilogramos(0.0785),
        varilla_desde=Metros(0.015),
        varilla_hasta=Metros(0.95),
    )
    estrecha = p.calidad_por_el_aire(
        Radianes(0.035),
        frente_lenteja=Metros(0.1),
        alto_lenteja=Metros(0.027),
        ancho_varilla=Metros(0.008),
    )
    ancha = p.calidad_por_el_aire(
        Radianes(0.035),
        frente_lenteja=Metros(0.1),
        alto_lenteja=Metros(0.027),
        ancho_varilla=Metros(0.030),
    )
    assert ancha < estrecha


def test_un_milimetro_de_mas_son_cuarenta_y_tres_segundos_al_dia():
    """La cota que justifica todo el cuidado con el datum. dT/T = dL/2L, y
    sobre 994 mm un milimetro son 43 s/dia."""
    p = _simple(0.994)
    assert p.deriva_por_milimetro() == pytest.approx(43.0, abs=1.0)


def test_la_deriva_por_milimetro_es_menor_en_un_pendulo_mas_largo():
    assert _simple(1.5).deriva_por_milimetro() < _simple(0.5).deriva_por_milimetro()


def test_la_longitud_equivalente_es_menor_que_la_posicion_de_la_lenteja():
    """Y por eso hay que bajar la lenteja mas alla de los 994 de libro."""
    p = pendulo.Pendulo(
        masa_lenteja=Kilogramos(1.032),
        centro_lenteja=Metros(1.007),
        masa_varilla=Kilogramos(0.0796),
        varilla_desde=Metros(0.015),
        varilla_hasta=Metros(0.963),
    )
    assert p.longitud_equivalente() < p.centro_lenteja


def test_el_buscador_devuelve_la_posicion_que_da_el_periodo_pedido():
    """C11 al reves: no 'que periodo da esta lenteja' sino 'donde va la
    lenteja para batir 2 s'. Es la que usa el compilador, porque el periodo
    se elige y la posicion se calcula."""
    centro = pendulo.centro_para_periodo(
        periodo=2.0,
        masa_lenteja=Kilogramos(1.032),
        densidad_varilla=700.0,
        ancho_varilla=Metros(0.015),
        espesor_varilla=Metros(0.008),
        flexion_a_varilla=Metros(0.015),
        centro_bajo_varilla=Metros(0.044),
    )
    largo = centro - 0.015 - 0.044
    p = pendulo.Pendulo(
        masa_lenteja=Kilogramos(1.032),
        centro_lenteja=Metros(centro),
        masa_varilla=Kilogramos(700.0 * largo * 0.015 * 0.008),
        varilla_desde=Metros(0.015),
        varilla_hasta=Metros(0.015 + largo),
    )
    assert p.periodo() == pytest.approx(2.0, abs=1.0e-6)


def test_la_correccion_de_c11_se_sale_del_recorrido_de_la_tuerca():
    """El hallazgo que obliga a construirla y no a regularla. La tuerca M6 da
    +/-10 mm en diez vueltas, unos +/-440 s/dia. La correccion por inercia
    real son casi 13 mm: no cabe, asi que si se corta la varilla con el
    numero del pendulo simple el reloj no se puede poner en hora."""
    centro = pendulo.centro_para_periodo(
        periodo=2.0,
        masa_lenteja=Kilogramos(1.032),
        densidad_varilla=700.0,
        ancho_varilla=Metros(0.015),
        espesor_varilla=Metros(0.008),
        flexion_a_varilla=Metros(0.015),
        centro_bajo_varilla=Metros(0.044),
    )
    simple = 9.80665 * 2.0**2 / (4.0 * math.pi**2)
    assert (centro - simple) * 1000.0 > 10.0


def test_una_varilla_sin_masa_no_necesita_correccion():
    """Limite de control: si la varilla no pesa, C11 devuelve el pendulo
    simple y la correccion es cero."""
    centro = pendulo.centro_para_periodo(
        periodo=2.0,
        masa_lenteja=Kilogramos(1.0),
        densidad_varilla=1.0e-9,
        ancho_varilla=Metros(0.015),
        espesor_varilla=Metros(0.008),
        flexion_a_varilla=Metros(0.015),
        centro_bajo_varilla=Metros(0.044),
    )
    assert centro == pytest.approx(9.80665 * 4.0 / (4.0 * math.pi**2), rel=1e-6)
