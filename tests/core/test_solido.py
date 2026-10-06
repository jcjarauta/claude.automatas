"""Masa e inercia de un prisma a partir de su polígono.

Las fórmulas de Green son exactas para un polígono, así que estos tests
comparan contra valores analíticos y no contra tolerancias de malla. Donde
hay tolerancia es al aproximar un círculo por un polígono, y entonces se dice
cuántos lados hacen falta.
"""

from __future__ import annotations

import numpy as np
import pytest

from core.solido import (
    DENSIDADES,
    area,
    centroide,
    densidad_de,
    descontar_taladro,
    inercia_de_prisma,
    masa_de_prisma,
    momento_polar,
)
from core.units import Metros, mm

pytestmark = pytest.mark.core


def cuadrado(lado: float, centro: tuple[float, float] = (0.0, 0.0)) -> np.ndarray:
    mitad = lado / 2.0
    return np.array(
        [
            (centro[0] - mitad, centro[1] - mitad),
            (centro[0] + mitad, centro[1] - mitad),
            (centro[0] + mitad, centro[1] + mitad),
            (centro[0] - mitad, centro[1] + mitad),
        ]
    )


def circulo(radio: float, lados: int = 2048) -> np.ndarray:
    angulos = np.linspace(0.0, 2.0 * np.pi, lados, endpoint=False)
    return np.column_stack([radio * np.cos(angulos), radio * np.sin(angulos)])


# ---------------------------------------------------------------------------
# Área y centroide
# ---------------------------------------------------------------------------


def test_el_area_de_un_cuadrado_es_su_lado_al_cuadrado():
    assert area(cuadrado(0.1)) == pytest.approx(0.01)


def test_el_area_no_depende_del_sentido_de_giro():
    """El perfil de una leva puede venir en cualquiera de los dos sentidos."""
    horario = cuadrado(0.1)[::-1]
    assert area(horario) == pytest.approx(area(cuadrado(0.1)))


def test_el_area_de_un_circulo_converge_a_pi_erre_cuadrado():
    assert area(circulo(0.05)) == pytest.approx(np.pi * 0.05**2, rel=1e-5)


def test_el_centroide_de_un_cuadrado_esta_en_su_centro():
    assert centroide(cuadrado(0.1, centro=(0.3, -0.2))) == pytest.approx((0.3, -0.2))


def test_un_poligono_degenerado_se_rechaza():
    with pytest.raises(ValueError, match="tres puntos"):
        area(np.array([[0.0, 0.0], [1.0, 1.0]]))


# ---------------------------------------------------------------------------
# Momento polar
# ---------------------------------------------------------------------------


def test_el_momento_polar_de_un_disco_es_el_de_libro():
    """J = π·r⁴/2 respecto de su centro."""
    assert momento_polar(circulo(0.05)) == pytest.approx(np.pi * 0.05**4 / 2.0, rel=1e-4)


def test_el_momento_polar_de_un_cuadrado_es_el_de_libro():
    """J = a⁴/6 respecto del centro, para un cuadrado de lado a."""
    assert momento_polar(cuadrado(0.1)) == pytest.approx(0.1**4 / 6.0)


def test_steiner_se_cumple():
    """Alejar la pieza del eje suma A·d². Si esto fallara, una leva excéntrica
    daría una inercia que no es la suya."""
    lado, distancia = 0.06, 0.2
    propio = momento_polar(cuadrado(lado))
    trasladado = momento_polar(cuadrado(lado, centro=(distancia, 0.0)))
    assert trasladado == pytest.approx(propio + lado**2 * distancia**2)


def test_el_eje_se_puede_mover_en_vez_de_mover_la_pieza():
    lado, distancia = 0.06, 0.2
    assert momento_polar(cuadrado(lado, centro=(distancia, 0.0)), eje=(distancia, 0.0)) == (
        pytest.approx(momento_polar(cuadrado(lado)))
    )


# ---------------------------------------------------------------------------
# Masa e inercia
# ---------------------------------------------------------------------------


def test_la_masa_es_area_por_espesor_por_densidad():
    masa = masa_de_prisma(cuadrado(0.1), mm(5.0), 1410.0)
    assert float(masa) == pytest.approx(0.01 * 0.005 * 1410.0)


def test_una_leva_de_pom_de_cinco_milimetros_pesa_lo_que_debe():
    """Una comprobación con los números reales: un disco de 114 mm en POM."""
    masa = masa_de_prisma(circulo(0.057), mm(5.0), densidad_de("POM 5 mm"))
    assert float(masa) == pytest.approx(0.0719, abs=0.001)


def test_la_inercia_es_el_momento_polar_por_espesor_por_densidad():
    inercia = inercia_de_prisma(circulo(0.057), mm(5.0), 1410.0)
    esperado = np.pi * 0.057**4 / 2.0 * 0.005 * 1410.0
    assert float(inercia) == pytest.approx(esperado, rel=1e-4)


def test_el_material_se_reconoce_por_su_principio():
    """El campo lleva el espesor pegado porque es lo que se pide en la tienda."""
    assert densidad_de("POM 5 mm") == DENSIDADES["POM"]
    assert densidad_de("contrachapado de abedul 9 mm") == DENSIDADES["contrachapado de abedul"]
    # Las paletas del escape del reloj son de latón.
    assert densidad_de("latón de 4") == pytest.approx(8500.0)


def test_un_material_desconocido_no_se_inventa():
    with pytest.raises(KeyError, match="no hay densidad"):
        densidad_de("titanio sinterizado")


# ---------------------------------------------------------------------------
# Taladros
# ---------------------------------------------------------------------------


def test_el_taladro_del_eje_quita_area_y_muy_poca_inercia():
    """Está en el eje de giro, así que su contribución a J es diminuta: es
    justo el material que menos trabaja."""
    superficie, polar = descontar_taladro(circulo(0.057), (Metros(0.0), Metros(0.0)), mm(10.0))
    assert superficie == pytest.approx(np.pi * 0.005**2)
    assert polar == pytest.approx(np.pi * 0.005**4 / 2.0)
    # Seis cienmilésimas del total: el material del eje no aporta inercia.
    assert polar / momento_polar(circulo(0.057)) < 1e-4


def test_un_taladro_lejos_del_eje_si_cuenta():
    _, cerca = descontar_taladro(circulo(0.057), (Metros(0.0), Metros(0.0)), mm(6.0))
    _, lejos = descontar_taladro(circulo(0.057), (Metros(0.04), Metros(0.0)), mm(6.0))
    assert lejos > 100.0 * cerca


def test_descontar_el_taladro_coincide_con_restarlo_del_poligono():
    """Contraste contra el camino largo: un anillo mallado como polígono."""
    externo, interno = 0.057, 0.005
    entero = momento_polar(circulo(externo))
    _, agujero = descontar_taladro(circulo(externo), (Metros(0.0), Metros(0.0)), Metros(0.01))
    anillo = np.pi * (externo**4 - interno**4) / 2.0
    assert entero - agujero == pytest.approx(anillo, rel=1e-4)


# ---------------------------------------------------------------------------
# Discos: el volante
# ---------------------------------------------------------------------------


def test_la_inercia_de_un_disco_es_media_eme_erre_cuadrado():
    radio, espesor, densidad = 0.025, 0.006, 8500.0
    masa = np.pi * radio**2 * espesor * densidad
    from core.solido import inercia_de_disco, masa_de_disco

    assert float(masa_de_disco(radio, espesor, densidad)) == pytest.approx(masa)
    assert float(inercia_de_disco(radio, espesor, densidad)) == pytest.approx(0.5 * masa * radio**2)


def test_el_disco_coincide_con_el_poligono_que_lo_aproxima():
    """Dos caminos otra vez: la fórmula cerrada y la integral del polígono."""
    from core.solido import inercia_de_disco

    radio, espesor, densidad = 0.03, 0.005, 1410.0
    assert float(inercia_de_disco(radio, espesor, densidad)) == pytest.approx(
        float(inercia_de_prisma(circulo(radio), mm(5.0), densidad)), rel=1e-4
    )


def test_el_radio_necesario_va_y_vuelve():
    from core.solido import inercia_de_disco, radio_de_disco_para
    from core.units import KgM2

    objetivo = KgM2(3.4e-5)
    radio = radio_de_disco_para(objetivo, 0.006, 8500.0)
    assert float(inercia_de_disco(radio, 0.006, 8500.0)) == pytest.approx(float(objetivo))


def test_doblar_el_radio_multiplica_la_inercia_por_dieciseis():
    """Va con la cuarta potencia: es la razón de que un volante pequeño en el
    eje rápido gane a uno grande en el lento."""
    from core.solido import inercia_de_disco

    uno = float(inercia_de_disco(0.02, 0.006, 8500.0))
    doble = float(inercia_de_disco(0.04, 0.006, 8500.0))
    assert doble == pytest.approx(16.0 * uno)
