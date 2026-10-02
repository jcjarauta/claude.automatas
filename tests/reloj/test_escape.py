"""C12 · el escape: cuanto par pide para mantener el pendulo en marcha.

Es el calculo que decide el proyecto entero, y el que la metodologia dice que
hay que medir en R2. Lo que se hace aqui es acotarlo por arriba y por abajo
para saber que esperar del banco: si la medida sale fuera de este rango, el
que esta mal es el banco o el modelo, no el reloj.
"""

from __future__ import annotations

import math

import pytest

from core.reloj import escape
from core.units import Julios

pytestmark = pytest.mark.core


def test_un_diente_escapa_por_oscilacion_completa():
    """La relacion que hace que 30 dientes y 2 s den una vuelta por minuto, y
    que la aguja de segundos salga gratis."""
    assert escape.vuelta_de_la_rueda(dientes=30, periodo=2.0) == pytest.approx(60.0)


def test_el_impulso_reparte_el_diente_en_dos():
    """Hay dos impulsos por oscilacion, uno por paleta, y entre los dos la
    rueda avanza un diente. El angulo de cada impulso es medio paso."""
    assert escape.angulo_de_impulso(dientes=30) == pytest.approx(math.radians(6.0))


def test_el_par_teorico_son_decimas_de_milinewton_metro():
    """El orden de magnitud que ordena el plan: el par ideal es ridiculo
    comparado con lo que da la pesa, asi que lo que dimensiona el reloj no es
    el pendulo sino el rozamiento."""
    par = escape.par_minimo_teorico(perdida_por_ciclo=Julios(27.0e-6), dientes=30)
    assert 50.0e-6 < par < 500.0e-6


def test_el_par_teorico_crece_con_lo_que_pierde_el_pendulo():
    a = escape.par_minimo_teorico(perdida_por_ciclo=Julios(20.0e-6), dientes=30)
    b = escape.par_minimo_teorico(perdida_por_ciclo=Julios(40.0e-6), dientes=30)
    assert b / a == pytest.approx(2.0, rel=1e-9)


def test_mas_dientes_piden_mas_par_para_la_misma_energia():
    """Con mas dientes, cada impulso recorre menos angulo, asi que para
    entregar la misma energia hace falta mas par. Es la contrapartida de
    poner una aguja de segundos mas fina."""
    pocos = escape.par_minimo_teorico(perdida_por_ciclo=Julios(27.0e-6), dientes=30)
    muchos = escape.par_minimo_teorico(perdida_por_ciclo=Julios(27.0e-6), dientes=60)
    assert muchos > pocos


def test_el_rendimiento_real_multiplica_el_par_entre_ocho_y_cincuenta():
    """Ningun reloj de madera pasa del 12 % de rendimiento global y muchos no
    llegan al 2. Ese factor es lo que separa el calculo de la realidad, y por
    eso R2 mide en vez de calcular."""
    ideal = escape.par_minimo_teorico(perdida_por_ciclo=Julios(27.0e-6), dientes=30)
    optimista = escape.par_con_rendimiento(ideal, rendimiento=0.12)
    pesimista = escape.par_con_rendimiento(ideal, rendimiento=0.02)
    assert optimista / ideal == pytest.approx(1.0 / 0.12, rel=1e-9)
    assert pesimista / optimista == pytest.approx(6.0, rel=1e-9)


def test_un_rendimiento_imposible_no_se_acepta():
    """Un rendimiento mayor que uno daria un par menor que el ideal, que es
    energia de la nada. Mejor que reviente aqui que en una hoja de calculo."""
    with pytest.raises(ValueError, match="no es fisico"):
        escape.par_con_rendimiento(1.0e-4, rendimiento=1.5)
    with pytest.raises(ValueError, match="no es fisico"):
        escape.par_con_rendimiento(1.0e-4, rendimiento=0.0)


def test_el_abarque_del_ancora_es_un_impar_y_medio():
    """Si el abarque fuese entero, las dos paletas trabajarian en fase y el
    escape no alternaria. Tiene que ser el medio impar mas proximo a un
    cuarto de los dientes."""
    assert escape.abarque(dientes=30) == pytest.approx(7.5)
    assert escape.abarque(dientes=32) == pytest.approx(8.5)
    assert escape.abarque(dientes=36) == pytest.approx(8.5)


def test_el_ancora_abarca_un_cuarto_de_vuelta_largo():
    """Con 30 dientes y abarque 7,5 son 90 grados exactos, que es lo que hace
    que el ancora sea una pieza de proporciones manejables."""
    assert escape.angulo_abarcado(dientes=30) == pytest.approx(math.pi / 2.0)


def test_el_brazo_del_ancora_es_tangente_a_la_rueda():
    """La construccion clasica del ancora de retroceso: el eje se pone a la
    distancia que hace que cada brazo quede PERPENDICULAR al radio de la
    rueda en el punto de contacto. Asi la paleta empuja en la direccion del
    movimiento y no contra el eje."""
    radio = 45.0
    d = escape.distancia_entre_centros(radio, dientes=30)
    brazo = escape.brazo_paleta(radio, dientes=30)
    # El triangulo centro-contacto-eje tiene que ser rectangulo en el contacto
    assert brazo**2 + radio**2 == pytest.approx(d**2, rel=1e-9)


def test_con_abarque_de_noventa_grados_el_brazo_mide_el_radio():
    """Caso particular de 30 dientes y abarque 7,5: el cuarto de vuelta hace
    el triangulo isosceles y el ancora sale de proporciones manejables."""
    assert escape.brazo_paleta(45.0, dientes=30) == pytest.approx(45.0, rel=1e-9)
    assert escape.distancia_entre_centros(45.0, dientes=30) == pytest.approx(
        45.0 * math.sqrt(2.0), rel=1e-9
    )


def test_el_eje_del_ancora_queda_siempre_fuera_de_la_rueda():
    """Obvio y facil de romper con un signo: si la distancia saliera menor
    que el radio, el eje caeria dentro del dentado."""
    for dientes in (20, 30, 36, 48, 60):
        assert escape.distancia_entre_centros(45.0, dientes) > 45.0


def test_abarcar_mas_angulo_aleja_el_eje():
    """Y se dispara cerca de media vuelta, que es lo que impide abarcar mucho
    mas de un cuarto. Se compara por angulo y no por dientes: el abarque ronda
    siempre el cuarto, asi que mas dientes no significa mas angulo."""
    anchos = sorted(
        (escape.angulo_abarcado(d), escape.distancia_entre_centros(45.0, d))
        for d in (20, 30, 36, 48, 60)
    )
    distancias = [d for _, d in anchos]
    assert distancias == sorted(distancias)


def test_el_recorrido_del_ancora_es_el_del_pendulo():
    """La horquilla los ata, asi que el ancora barre exactamente lo que barre
    el pendulo. Ese es TODO el presupuesto angular que hay para repartir
    entre reposo, impulso y caida."""
    assert escape.recorrido_del_ancora(amplitud=0.0349) == pytest.approx(0.0698, rel=1e-9)
