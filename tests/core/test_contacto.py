"""Recuperar ψ apoyando el rodillo en el perfil cortado.

Lo que se comprueba aquí es que **dos caminos distintos dan el mismo número**.
La síntesis va de ψ al perfil por la curva de paso y las normales; esto va del
polígono al ψ por contacto, sin mirar ni la curva de paso ni las normales. Si
coinciden, el desplazamiento por radio de rodillo está bien hecho. Si el
perfil está socavado, no coinciden, y ese es justo el hueco que la simulación
de E5 declara no cubrir.
"""

from __future__ import annotations

import numpy as np
import pytest

from core.cam.contacto import error_de_contacto, psi_por_contacto
from core.cam.curves import cicloidal, desde_muestras, rejilla
from core.cam.envelope import autointerseca
from core.cam.synth import PerfilLeva, Seguidor, sintetizar
from core.units import grados, mm

pytestmark = pytest.mark.core

TOLERANCIA = 1e-4
"""Radianes. El perfil se guarda como polígono, así que el rodillo apoya en
una cuerda y no en la curva. Con 360 muestras sobre una leva de 55 mm la
flecha de la cuerda son unas dos micras, que en el brazo del seguidor es un
orden de magnitud menos que esto."""


def seguidor(radio_rodillo_mm: float = 2.0) -> Seguidor:
    return Seguidor.bien_puesto(
        radio_base=mm(55.0), brazo=mm(45.0), radio_rodillo=mm(radio_rodillo_mm)
    )


def leva(amplitud_grados: float = 8.0, muestras: int = 360, rodillo_mm: float = 2.0) -> PerfilLeva:
    thetas = rejilla(48)
    psi = desde_muestras(thetas, grados(amplitud_grados) * np.sin(thetas), n=muestras)
    return sintetizar(psi, seguidor(rodillo_mm))


def leva_de_pico(rodillo_mm: float, arco_grados: float = 14.0, alto_grados: float = 8.0):
    """Una leva de levantamiento: sube y baja en pocos grados de θ.

    Es donde el radio de curvatura se hace pequeño, y por tanto donde un
    rodillo grande socava el perfil. La sinusoide no sirve para esto: su
    curvatura no baja de los 50 mm por mucha amplitud que se le dé.
    """
    thetas = rejilla(360)
    sube = np.clip(thetas / np.radians(arco_grados), 0.0, 1.0)
    baja = np.clip((np.radians(2.0 * arco_grados) - thetas) / np.radians(arco_grados), 0.0, 1.0)
    valores = np.radians(alto_grados) * np.minimum(cicloidal(sube), cicloidal(baja))
    return sintetizar(desde_muestras(thetas, valores, n=720), seguidor(rodillo_mm))


def unos_cuantos(perfil: PerfilLeva, cuantos: int = 24) -> np.ndarray:
    """Un submuestreo ordenado del ciclo: el contacto es caro y no hace falta
    recorrer las setecientas muestras para saber si coincide."""
    return perfil.thetas[:: max(1, len(perfil) // cuantos)]


# ---------------------------------------------------------------------------
# Coincide con la síntesis
# ---------------------------------------------------------------------------


def test_una_leva_circular_no_mueve_el_seguidor():
    """Con ψ constante el perfil es una circunferencia y el rodillo apoya
    siempre en el mismo sitio. Es el caso que tiene que salir exacto."""
    thetas = rejilla(48)
    psi = desde_muestras(thetas, np.zeros_like(thetas), n=360)
    perfil = sintetizar(psi, seguidor())
    recuperado = psi_por_contacto(perfil.perfil, perfil.seguidor, unos_cuantos(perfil))
    assert np.max(np.abs(recuperado)) < TOLERANCIA


@pytest.mark.parametrize("amplitud", [4.0, 8.0, 14.0])
def test_el_contacto_devuelve_el_psi_que_se_sintetizo(amplitud: float):
    """La comprobación independiente: del polígono al ángulo, sin pasar por
    la curva de paso."""
    perfil = leva(amplitud)
    thetas = unos_cuantos(perfil)
    esperado = np.interp(thetas, perfil.thetas, perfil.psi)
    assert np.max(np.abs(psi_por_contacto(perfil.perfil, perfil.seguidor, thetas) - esperado)) < (
        TOLERANCIA
    )


def test_error_de_contacto_resume_lo_mismo_en_un_numero():
    perfil = leva()
    thetas = unos_cuantos(perfil)
    esperado = np.interp(thetas, perfil.thetas, perfil.psi)
    assert error_de_contacto(perfil.perfil, esperado, perfil.seguidor, thetas) < TOLERANCIA


def test_entre_muestra_y_muestra_el_rodillo_apoya_en_la_cuerda():
    """En un ángulo que coincide con una muestra del perfil, el rodillo toca
    justo el vértice y el resultado es exacto. El error de verdad está **en
    medio**, donde apoya sobre la cuerda en vez de sobre la curva, y ahí más
    muestras es menos error.

    La referencia es la ψ analítica —una sinusoide— y no el propio perfil:
    comparar contra uno mismo no mide nada.
    """
    amplitud = float(grados(8.0))

    def error(muestras: int) -> float:
        perfil = leva(muestras=muestras)
        paso = 2.0 * np.pi / muestras
        medios = perfil.thetas[:: muestras // 12] + paso / 2.0
        recuperado = psi_por_contacto(perfil.perfil, perfil.seguidor, medios)
        return float(np.max(np.abs(recuperado - amplitud * np.sin(medios))))

    grueso, fino = error(120), error(720)
    assert fino < grueso / 5.0
    assert fino < 1e-4


# ---------------------------------------------------------------------------
# El hueco que cierra
# ---------------------------------------------------------------------------


def test_un_rodillo_demasiado_grande_socava_y_el_contacto_lo_delata():
    """Si el radio de curvatura baja del radio del rodillo, el perfil se cruza
    consigo mismo: la pieza que se corta no es la que se calculó. La
    simulación de E5 no lo ve, porque lee la curva de paso. Esto sí."""
    sano = leva_de_pico(rodillo_mm=3.0)
    socavado = leva_de_pico(rodillo_mm=6.0)
    assert not autointerseca(sano)
    assert autointerseca(socavado)

    def desviacion(perfil: PerfilLeva) -> float:
        thetas = unos_cuantos(perfil, 16)
        esperado = np.interp(thetas, perfil.thetas, perfil.psi)
        return error_de_contacto(perfil.perfil, esperado, perfil.seguidor, thetas)

    assert desviacion(sano) < TOLERANCIA
    assert desviacion(socavado) > 20.0 * TOLERANCIA


def test_un_perfil_desplazado_del_reves_se_nota():
    """Compensar el radio de rodillo hacia fuera en vez de hacia dentro es un
    error de un signo que no se ve en el dibujo: la leva parece una leva."""
    perfil = leva()
    al_reves = perfil.paso + perfil.seguidor.radio_rodillo * perfil.normales
    thetas = unos_cuantos(perfil, 16)
    esperado = np.interp(thetas, perfil.thetas, perfil.psi)
    assert error_de_contacto(al_reves, esperado, perfil.seguidor, thetas) > 20.0 * TOLERANCIA


# ---------------------------------------------------------------------------
# Propiedades
# ---------------------------------------------------------------------------


def test_el_rodillo_ni_flota_ni_penetra():
    """En la solución, la distancia del centro al perfil es el radio: ni más
    —flotaría— ni menos —se clavaría en la leva—."""
    from core.cam.contacto import _centros, _Leva

    perfil = leva()
    solido = _Leva(perfil.perfil)
    thetas = unos_cuantos(perfil, 12)
    psi = psi_por_contacto(perfil.perfil, perfil.seguidor, thetas)
    for theta, angulo in zip(thetas, psi, strict=True):
        centro = _centros(perfil.seguidor, np.array([angulo]), float(theta))
        holgura = solido.holgura(centro, perfil.seguidor.radio_rodillo)[0]
        assert abs(holgura) < 1e-7


def test_el_orden_de_los_puntos_del_poligono_no_cambia_el_resultado():
    """El perfil es un polígono cerrado: empezar a listarlo por otro vértice
    es el mismo sólido."""
    perfil = leva()
    thetas = unos_cuantos(perfil, 8)
    uno = psi_por_contacto(perfil.perfil, perfil.seguidor, thetas)
    rodado = psi_por_contacto(np.roll(perfil.perfil, 97, axis=0), perfil.seguidor, thetas)
    assert np.max(np.abs(uno - rodado)) < 1e-9


def test_dos_veces_da_lo_mismo():
    perfil = leva()
    thetas = unos_cuantos(perfil, 8)
    uno = psi_por_contacto(perfil.perfil, perfil.seguidor, thetas)
    otro = psi_por_contacto(perfil.perfil, perfil.seguidor, thetas)
    assert np.array_equal(uno, otro)


def test_un_poligono_que_no_es_poligono_se_rechaza():
    with pytest.raises(ValueError, match="polígono cerrado"):
        psi_por_contacto(np.array([[0.0, 0.0], [1.0, 1.0]]), seguidor(), np.array([0.0]))


def test_si_el_seguidor_no_llega_se_dice():
    """Un seguidor colocado lejos de la leva no apoya en ninguna parte, y eso
    tiene que salir como error con nombre y no como un número inventado."""
    perfil = leva()
    lejano = Seguidor(pivote=(1.0, 1.0), brazo=0.045, radio_rodillo=0.002)
    with pytest.raises(ValueError, match="no llega a tocar"):
        psi_por_contacto(perfil.perfil, lejano, np.array([0.0]))
