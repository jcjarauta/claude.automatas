"""C6, C7 y C9: par, volante y lo que da una mano.

Casi todo se comprueba contra cuentas cerradas: un par constante, un seno,
un caso donde el resultado se sabe de antemano. Es lo único que distingue
comprobar de volver a ejecutar el mismo código.
"""

from __future__ import annotations

import numpy as np
import pytest

from core.energy.budget import CargaSeguidor, par_de_un_canal, presupuesto
from core.energy.flywheel import (
    desde_vueltas_por_minuto,
    fluctuacion,
    fluctuacion_con,
    inercia_necesaria,
    vueltas_por_minuto,
)
from core.energy.humano import Manivela, Transmision, relacion_minima
from core.units import TAU, Julios, KgM2, NewtonMetro

pytestmark = pytest.mark.core


def rejilla(n: int = 720) -> np.ndarray:
    return np.linspace(0.0, TAU, n, endpoint=False)


def canal_sinusoidal(amplitud: float = 0.15, n: int = 720):
    """ψ = A·sen θ, con sus derivadas exactas. Sirve de patrón."""
    thetas = rejilla(n)
    return thetas, (
        amplitud * np.sin(thetas),
        amplitud * np.cos(thetas),
        -amplitud * np.sin(thetas),
    )


# ---------------------------------------------------------------------------
# C6 · Par
# ---------------------------------------------------------------------------


def test_un_seguidor_parado_no_pide_par():
    """Aunque su muelle apriete. Es lo que uno nota al girar una manivela por
    un tramo de reposo: no cuesta nada."""
    quieto = np.zeros(720)
    estatico, inercial = par_de_un_canal(quieto, quieto, quieto, CargaSeguidor())
    assert np.allclose(estatico, 0.0)
    assert np.allclose(inercial, 0.0)


def test_el_par_es_el_del_seguidor_por_la_derivada():
    """T_árbol = T_seguidor · ψ'. Es la relación que sostiene todo C6."""
    carga = CargaSeguidor(par_muelle=NewtonMetro(0.1), rigidez=0.0, rozamiento=NewtonMetro(0.0))
    _, (psi, psi_prima, psi_segunda) = canal_sinusoidal()
    estatico, _ = par_de_un_canal(psi, psi_prima, psi_segunda, carga)
    assert np.allclose(estatico, 0.1 * psi_prima)


def test_el_muelle_devuelve_lo_que_se_le_dio():
    """Sin rozamiento ni rigidez, el par medio de un muelle de precarga a lo
    largo de una vuelta cerrada es cero: lo que cuesta subir se recupera al
    bajar. Si esto no diera cero, el modelo estaría creando energía."""
    carga = CargaSeguidor(par_muelle=NewtonMetro(0.1), rigidez=0.0, rozamiento=NewtonMetro(0.0))
    _, (psi, psi_prima, psi_segunda) = canal_sinusoidal()
    estatico, _ = par_de_un_canal(psi, psi_prima, psi_segunda, carga)
    assert float(np.mean(estatico)) == pytest.approx(0.0, abs=1e-12)


def test_el_rozamiento_no_devuelve_nada():
    """Al revés que el muelle: siempre resta, suba o baje el seguidor."""
    carga = CargaSeguidor(par_muelle=NewtonMetro(0.0), rozamiento=NewtonMetro(0.02))
    _, (psi, psi_prima, psi_segunda) = canal_sinusoidal()
    estatico, _ = par_de_un_canal(psi, psi_prima, psi_segunda, carga)
    assert float(np.mean(estatico)) > 0.0


def test_la_inercia_solo_cuenta_a_velocidad():
    """Por eso se devuelve como coeficiente de ω² y no sumada: girar despacio
    no cuesta inercia, y el núcleo no tiene por qué saber a qué velocidad se
    va a girar."""
    thetas, (psi, psi_prima, psi_segunda) = canal_sinusoidal()
    presupuestado = presupuesto(thetas, {"uno": (psi, psi_prima, psi_segunda)}, {})
    assert np.allclose(presupuestado.total(0.0), presupuestado.estatico)

    def aportacion(omega: float) -> float:
        return float(np.max(np.abs(presupuestado.total(omega) - presupuestado.estatico)))

    # Va con el cuadrado: el doble de velocidad son cuatro veces más par.
    assert aportacion(10.0) == pytest.approx(4.0 * aportacion(5.0))
    assert aportacion(5.0) > 0.0


def test_tres_canales_suman():
    thetas, terna = canal_sinusoidal()
    uno = presupuesto(thetas, {"a": terna}, {}, rozamiento_arbol=NewtonMetro(0.0))
    tres = presupuesto(
        thetas, {"a": terna, "b": terna, "c": terna}, {}, rozamiento_arbol=NewtonMetro(0.0)
    )
    assert np.allclose(tres.estatico, 3.0 * uno.estatico)


def test_el_rozamiento_del_arbol_es_un_suelo():
    thetas, terna = canal_sinusoidal()
    presupuestado = presupuesto(
        thetas,
        {"a": terna},
        {"a": CargaSeguidor(par_muelle=NewtonMetro(0.0), rozamiento=NewtonMetro(0.0))},
        rozamiento_arbol=NewtonMetro(0.03),
    )
    assert np.allclose(presupuestado.estatico, 0.03)


def test_el_trabajo_por_vuelta_es_el_par_medio_por_dos_pi():
    thetas, terna = canal_sinusoidal()
    presupuestado = presupuesto(thetas, {"a": terna}, {})
    assert presupuestado.trabajo() == pytest.approx(presupuestado.medio() * TAU)


def test_sin_canales_no_hay_presupuesto():
    with pytest.raises(ValueError, match="no hay canales"):
        presupuesto(rejilla(), {}, {})


# ---------------------------------------------------------------------------
# C7 · Volante
# ---------------------------------------------------------------------------


def test_un_par_constante_no_fluctua():
    """Nada que guardar: el volante no hace falta."""
    thetas = rejilla()
    assert float(fluctuacion(thetas, np.full_like(thetas, 0.3)).energia) == pytest.approx(
        0.0, abs=1e-12
    )


def test_la_fluctuacion_de_un_seno_es_la_de_libro():
    """Con T = A·sen θ, el par medio es cero y la integral acumulada es
    A·(1 - cos θ): va de 0 a 2A, así que ΔE = 2A."""
    thetas = rejilla(3600)
    amplitud = 0.4
    assert float(fluctuacion(thetas, amplitud * np.sin(thetas)).energia) == pytest.approx(
        2.0 * amplitud, rel=1e-5
    )


def test_la_fluctuacion_no_depende_del_par_medio():
    """Sumar un par constante cambia el trabajo, no la irregularidad."""
    thetas = rejilla()
    seno = 0.4 * np.sin(thetas)
    assert float(fluctuacion(thetas, seno).energia) == pytest.approx(
        float(fluctuacion(thetas, seno + 5.0).energia)
    )


def test_donde_sube_y_donde_baja():
    """Con un seno, el árbol acelera hasta media vuelta y frena después."""
    thetas = rejilla(720)
    variacion = fluctuacion(thetas, 0.4 * np.sin(thetas))
    assert variacion.theta_maximo == pytest.approx(np.pi, abs=0.02)
    assert variacion.theta_minimo in (pytest.approx(0.0, abs=0.02), pytest.approx(TAU, abs=0.02))


def test_la_inercia_necesaria_es_la_formula_de_libro():
    assert float(inercia_necesaria(Julios(0.01), 3.0, 0.15)) == pytest.approx(0.01 / (0.15 * 9.0))


def test_girar_mas_deprisa_pide_mucho_menos_volante():
    """Va con el cuadrado de la velocidad: el doble de rpm es la cuarta parte
    de inercia. Es la palanca más barata que hay."""
    despacio = float(inercia_necesaria(Julios(0.01), 3.0))
    deprisa = float(inercia_necesaria(Julios(0.01), 6.0))
    assert deprisa == pytest.approx(despacio / 4.0)


def test_la_vuelta_atras_es_consistente():
    energia, omega, coeficiente = Julios(0.0065), 3.14, 0.15
    inercia = inercia_necesaria(energia, omega, coeficiente)
    assert fluctuacion_con(inercia, energia, omega) == pytest.approx(coeficiente)


def test_una_velocidad_negativa_no_tiene_sentido():
    with pytest.raises(ValueError, match="positiva"):
        inercia_necesaria(Julios(0.01), 0.0)


def test_un_coeficiente_imposible_se_rechaza():
    with pytest.raises(ValueError, match="entre 0 y 1"):
        inercia_necesaria(Julios(0.01), 3.0, 1.5)


def test_las_revoluciones_por_minuto_van_y_vuelven():
    assert vueltas_por_minuto(desde_vueltas_por_minuto(30.0)) == pytest.approx(30.0)


def test_el_cartucho_ya_hace_algo_de_volante():
    """No hay que añadir toda la inercia: la que ya gira cuenta."""
    assert fluctuacion_con(KgM2(2.6e-4), Julios(0.0065), 3.14) > 0.15


# ---------------------------------------------------------------------------
# C9 · La mano
# ---------------------------------------------------------------------------


def test_la_manivela_no_da_lo_mismo_en_todo_el_giro():
    """Si diera par constante sería un motor, no una persona."""
    par = Manivela().par(rejilla())
    assert float(np.min(par)) < float(np.max(par))


def test_el_suelo_es_el_minimo_de_la_curva():
    manivela = Manivela(par_maximo=NewtonMetro(4.0), suelo=0.45)
    par = manivela.par(rejilla())
    assert float(np.min(par)) == pytest.approx(4.0 * 0.45, rel=1e-3)
    assert float(np.max(par)) == pytest.approx(4.0, rel=1e-3)


def test_con_suelo_uno_la_manivela_es_un_motor():
    par = Manivela(suelo=1.0).par(rejilla())
    assert np.allclose(par, par[0])


def test_la_fase_mueve_el_punto_bueno():
    """Es un grado de libertad del montaje: girar la manivela sobre su eje
    puede sacar de apuros un pedido justo."""
    thetas = rejilla()
    sin_fase = Manivela().par(thetas)
    con_fase = Manivela(fase=np.pi / 2).par(thetas)
    assert not np.allclose(sin_fase, con_fase)
    assert float(np.mean(sin_fase)) == pytest.approx(float(np.mean(con_fase)), rel=1e-6)


def test_un_reductor_multiplica_el_par_disponible():
    thetas = rejilla()
    manivela = Manivela()
    directo = Transmision(relacion=1.0, rendimiento=1.0).disponible(manivela, thetas)
    reducido = Transmision(relacion=3.0, rendimiento=1.0).disponible(manivela, thetas)
    assert float(np.mean(reducido)) == pytest.approx(3.0 * float(np.mean(directo)), rel=1e-3)


def test_el_rendimiento_se_descuenta():
    thetas = rejilla()
    entero = Transmision(relacion=2.0, rendimiento=1.0).disponible(Manivela(), thetas)
    con_perdidas = Transmision(relacion=2.0, rendimiento=0.8).disponible(Manivela(), thetas)
    assert np.allclose(con_perdidas, 0.8 * entero)


def test_la_relacion_minima_cubre_el_pedido_con_margen():
    thetas = rejilla()
    pedido = np.full_like(thetas, 3.0)
    relacion = relacion_minima(Manivela(), pedido, thetas, margen=1.3)
    assert relacion is not None
    disponible = Transmision(relacion=relacion).disponible(Manivela(), thetas)
    assert float(np.min(disponible)) >= 1.3 * 3.0


def test_si_no_hace_falta_reductor_la_relacion_es_uno():
    thetas = rejilla()
    assert relacion_minima(Manivela(), np.full_like(thetas, 0.05), thetas) == 1.0


def test_si_ni_con_el_maximo_llega_se_dice():
    """Entonces el problema no es de transmisión: la máquina pide demasiado."""
    thetas = rejilla()
    assert relacion_minima(Manivela(), np.full_like(thetas, 500.0), thetas) is None


# ---------------------------------------------------------------------------
# Referir inercias entre ejes
# ---------------------------------------------------------------------------


def test_una_inercia_en_el_eje_rapido_cuenta_al_cuadrado():
    """La misma chapa rinde nueve veces más en una reducción de 3:1. Es la
    razón de poner el volante en la manivela y no en el árbol de levas."""
    from core.energy.flywheel import referir

    assert float(referir(KgM2(1.0e-4), 3.0)) == pytest.approx(9.0e-4)


def test_referir_con_relacion_uno_no_cambia_nada():
    from core.energy.flywheel import referir

    assert float(referir(KgM2(2.5e-4), 1.0)) == pytest.approx(2.5e-4)


def test_una_relacion_negativa_no_tiene_sentido():
    from core.energy.flywheel import referir

    with pytest.raises(ValueError, match="positiva"):
        referir(KgM2(1.0e-4), 0.0)
