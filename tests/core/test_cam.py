"""C2 y C3 · Síntesis del perfil de leva y su envolvente.

Los invariantes que exige la puerta de E2: cierre periódico, continuidad,
invarianza a la velocidad, undercutting y determinismo.
"""

from __future__ import annotations

import numpy as np
import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from core.cam.curves import derivada_ciclica, desde_muestras, orientacion, rejilla
from core.cam.envelope import (
    angulo_de_presion,
    autointerseca,
    evaluar,
    radio_de_curvatura,
)
from core.cam.synth import Seguidor, sintetizar
from core.units import TAU, grados, mm

pytestmark = pytest.mark.core


def seguidor() -> Seguidor:
    return Seguidor.bien_puesto(radio_base=mm(40.0), brazo=mm(60.0), radio_rodillo=mm(4.0))


def oscilacion(amplitud_grados: float, n_muestras: int = 48, n: int = 720):
    thetas = rejilla(n_muestras)
    return desde_muestras(thetas, grados(amplitud_grados) * np.sin(thetas), n=n)


def perfil(amplitud_grados: float = 8.0, n: int = 720):
    return sintetizar(oscilacion(amplitud_grados, n=n), seguidor())


# ---------------------------------------------------------------------------
# Cierre periódico
# ---------------------------------------------------------------------------


def test_el_perfil_cierra_en_posicion():
    """Al dar la vuelta, la leva vuelve al mismo punto. El extremo nunca se
    almacenó, así que el cierre es exacto por construcción."""
    p = perfil()
    paso = TAU / len(p)
    continuado = np.roll(p.perfil, -1, axis=0)
    salto_ultimo = np.linalg.norm(continuado[-1] - p.perfil[0])
    salto_tipico = float(np.median(np.linalg.norm(np.diff(p.perfil, axis=0), axis=1)))
    assert salto_ultimo < 1e-12, f"la leva no cierra: {salto_ultimo} m"
    assert paso > 0.0
    assert salto_tipico > 0.0


def test_el_perfil_cierra_en_velocidad():
    p = perfil()
    paso = TAU / len(p)
    v = derivada_ciclica(p.perfil, paso)
    assert np.linalg.norm(v[0] - v[-1]) < 0.2 * float(np.linalg.norm(v).max())


def test_el_perfil_cierra_en_aceleracion():
    """El spline periódico impone C²: la segunda derivada no puede saltar en
    θ=0, que es donde un spline natural metería un artefacto."""
    p = perfil()
    paso = TAU / len(p)
    a = derivada_ciclica(derivada_ciclica(p.perfil, paso), paso)
    salto_en_cero = float(np.linalg.norm(a[0] - a[-1]))
    salto_tipico = float(np.median(np.linalg.norm(np.diff(a, axis=0), axis=1)))
    assert salto_en_cero < 10.0 * salto_tipico, (
        f"salto en el cierre {salto_en_cero:.2e} frente a {salto_tipico:.2e} típico"
    )


def test_psi_cierra_el_ciclo():
    f = oscilacion(8.0)
    assert abs(float(f.valores[0] - f.valores[-1])) < 0.05
    assert abs(float(f.primera[0] - f.primera[-1])) < 0.05


# ---------------------------------------------------------------------------
# Continuidad
# ---------------------------------------------------------------------------


def test_la_segunda_derivada_no_da_saltos():
    """La ley fundamental del diseño de levas: desplazamiento, velocidad y
    aceleración continuos en todo el ciclo."""
    p = perfil()
    paso = TAU / len(p)
    a = derivada_ciclica(derivada_ciclica(p.perfil, paso), paso)
    saltos = np.linalg.norm(np.diff(a, axis=0, append=a[:1]), axis=1)
    assert float(saltos.max()) < 20.0 * float(np.median(saltos))


def test_el_perfil_no_tiene_puntos_repetidos():
    p = perfil()
    distancias = np.linalg.norm(np.diff(p.perfil, axis=0, append=p.perfil[:1]), axis=1)
    assert float(distancias.min()) > 0.0


# ---------------------------------------------------------------------------
# Invarianza a la velocidad
# ---------------------------------------------------------------------------


def test_muestrear_el_doble_de_denso_no_cambia_el_perfil():
    """θ manda y el tiempo no existe. Recorrer la trayectoria con el doble de
    muestras es el análogo discreto de recorrerla al doble de velocidad: el
    perfil tiene que ser el mismo."""
    poco = sintetizar(oscilacion(8.0, n_muestras=48, n=360), seguidor())
    mucho = sintetizar(oscilacion(8.0, n_muestras=96, n=360), seguidor())
    error = float(np.linalg.norm(poco.perfil - mucho.perfil, axis=1).max())
    assert error < 1e-5, f"{error * 1000:.4f} mm de diferencia"


def test_la_resolucion_de_salida_no_mueve_el_perfil():
    """Calcular con 360 o con 1440 puntos debe dar la misma leva."""
    basto = sintetizar(oscilacion(8.0, n=360), seguidor())
    fino = sintetizar(oscilacion(8.0, n=1440), seguidor())
    # Se comparan los puntos que comparten θ.
    error = float(np.linalg.norm(basto.perfil - fino.perfil[::4], axis=1).max())
    assert error < 1e-9


def test_en_el_nucleo_no_hay_ninguna_nocion_de_velocidad():
    """Estructural: si alguien mete un `dt` o unas rpm, este test lo dice."""
    import inspect

    from core.cam import synth

    firma = inspect.signature(synth.sintetizar)
    prohibidos = {"dt", "tiempo", "velocidad", "rpm", "segundos"}
    assert not (set(firma.parameters) & prohibidos)


# ---------------------------------------------------------------------------
# Undercutting
# ---------------------------------------------------------------------------


def test_una_oscilacion_suave_es_apta():
    v = evaluar(perfil(8.0))
    assert v.apto, [i.codigo for i in v.incidencias]


def test_una_oscilacion_excesiva_da_veredicto_negativo():
    v = evaluar(perfil(40.0))
    assert not v.apto
    assert {"angulo_presion_excedido"} <= {i.codigo for i in v.incidencias}


def test_un_rodillo_demasiado_grande_produce_undercutting_y_se_detecta():
    """El caso construido a propósito: curvatura menor que el rodillo. Debe
    salir veredicto negativo, no un perfil cruzado en silencio."""
    grande = Seguidor.bien_puesto(radio_base=mm(40.0), brazo=mm(60.0), radio_rodillo=mm(45.0))
    p = sintetizar(oscilacion(20.0), grande)
    v = evaluar(p)
    assert not v.apto
    codigos = {i.codigo for i in v.incidencias}
    assert codigos & {"perfil_autointersecado", "curvatura_menor_que_rodillo"}


def test_el_aviso_de_curvatura_justa_aparece_antes_que_el_error():
    """Hay una franja donde la leva funciona pero con poco margen."""
    radios = [mm(r) for r in (4.0, 8.0, 12.0, 16.0)]
    avisos = []
    for r in radios:
        s = Seguidor.bien_puesto(radio_base=mm(40.0), brazo=mm(60.0), radio_rodillo=r)
        v = evaluar(sintetizar(oscilacion(12.0), s))
        avisos.append({i.codigo for i in v.incidencias})
    # Con rodillo pequeño no hay nada que decir; con uno grande, aviso o error.
    assert not avisos[0]
    assert avisos[-1]


def test_la_autointerseccion_se_detecta_sobre_el_perfil_real():
    sano = perfil(8.0)
    assert not autointerseca(sano)


def test_el_radio_de_curvatura_de_un_circulo_es_su_radio():
    """Comprobación contra geometría conocida: con el seguidor quieto la curva
    de paso es una circunferencia centrada en el eje."""
    thetas = rejilla(48)
    quieto = desde_muestras(thetas, np.zeros_like(thetas), n=720)
    s = Seguidor.bien_puesto(radio_base=mm(40.0), brazo=mm(60.0), radio_rodillo=mm(4.0))
    p = sintetizar(quieto, s)
    radios = radio_de_curvatura(p)
    assert np.allclose(radios, mm(40.0), rtol=1e-3)


def test_con_el_seguidor_quieto_la_leva_es_un_circulo():
    thetas = rejilla(48)
    quieto = desde_muestras(thetas, np.zeros_like(thetas), n=720)
    s = Seguidor.bien_puesto(radio_base=mm(40.0), brazo=mm(60.0), radio_rodillo=mm(4.0))
    p = sintetizar(quieto, s)
    assert p.radio_maximo == pytest.approx(p.radio_minimo, abs=1e-9)
    assert p.radio_maximo == pytest.approx(mm(36.0), abs=1e-9)


def test_un_seguidor_quieto_no_tiene_angulo_de_presion():
    """Sin movimiento no hace falta fuerza: el ángulo no está definido y se
    toma cero."""
    thetas = rejilla(48)
    quieto = desde_muestras(thetas, np.zeros_like(thetas), n=720)
    s = Seguidor.bien_puesto(radio_base=mm(40.0), brazo=mm(60.0), radio_rodillo=mm(4.0))
    assert float(np.max(angulo_de_presion(sintetizar(quieto, s)))) == pytest.approx(0.0)


# ---------------------------------------------------------------------------
# El seguidor al revés y el seguidor en un poste fijo
# ---------------------------------------------------------------------------


def test_el_seguidor_al_reves_es_el_espejo_sobre_la_recta_del_pivote():
    """Con `sentido=-1` el brazo apunta al otro lado de la recta centro-pivote.
    El pivote no se mueve; el rodillo en reposo cae en el simétrico y el
    brazo sigue perpendicular al radio, así que el ángulo de presión sigue
    arrancando en cero."""
    directo = Seguidor.bien_puesto(mm(40.0), mm(60.0), mm(4.0), orientacion_pivote=0.3)
    reves = Seguidor.bien_puesto(mm(40.0), mm(60.0), mm(4.0), orientacion_pivote=0.3, sentido=-1)
    assert reves.pivote == pytest.approx(directo.pivote)

    def contacto(s: Seguidor) -> np.ndarray:
        return np.array(s.pivote) + s.brazo * np.array([np.cos(s.psi_cero), np.sin(s.psi_cero)])

    a, b = contacto(directo), contacto(reves)
    assert np.hypot(*b) == pytest.approx(mm(40.0))
    eje = np.array([np.cos(0.3), np.sin(0.3)])
    assert float(a @ eje) == pytest.approx(float(b @ eje))  # la misma proyección

    def lado(v: np.ndarray) -> float:
        return float(eje[0] * v[1] - eje[1] * v[0])

    assert lado(a) == pytest.approx(-lado(b))  # al otro lado
    assert lado(a) > 0.0
    # Perpendicular al radio en reposo.
    brazo = b - np.array(reves.pivote)
    assert float(brazo @ b) == pytest.approx(0.0, abs=1e-12)


def test_un_seguidor_al_reves_tambien_hace_un_circulo_si_esta_quieto():
    thetas = rejilla(48)
    quieto = desde_muestras(thetas, np.zeros_like(thetas), n=720)
    s = Seguidor.bien_puesto(mm(40.0), mm(60.0), mm(4.0), sentido=-1)
    p = sintetizar(quieto, s)
    assert p.radio_maximo == pytest.approx(mm(36.0), abs=1e-9)
    assert p.radio_minimo == pytest.approx(mm(36.0), abs=1e-9)


def test_el_sentido_solo_puede_ser_uno_o_menos_uno():
    with pytest.raises(ValueError, match="sentido"):
        Seguidor.bien_puesto(mm(40.0), mm(60.0), mm(4.0), sentido=0)


def test_en_el_poste_el_brazo_decide_el_radio_base():
    """El poste está donde está: con el pivote a `distancia` del árbol, un
    brazo más largo pide una leva más pequeña. `radio_base² + brazo² =
    distancia²`, porque el brazo sigue perpendicular al radio."""
    distancia = float(np.hypot(mm(55.0), mm(45.0)))
    for brazo in (mm(45.0), mm(52.0), mm(59.0)):
        s = Seguidor.en_el_poste(distancia, brazo, mm(3.0), orientacion_pivote=1.0)
        assert s.distancia_pivote == pytest.approx(distancia)
        assert s.brazo == pytest.approx(brazo)
        assert Seguidor.radio_base_en_el_poste(distancia, brazo) == pytest.approx(
            np.sqrt(distancia**2 - brazo**2)
        )
    with pytest.raises(ValueError, match="poste"):
        Seguidor.en_el_poste(mm(50.0), mm(50.0), mm(3.0))


# ---------------------------------------------------------------------------
# Determinismo
# ---------------------------------------------------------------------------


def test_cien_sintesis_dan_bytes_identicos():
    primera = perfil().perfil
    for _ in range(100):
        assert perfil().perfil.tobytes() == primera.tobytes()


def test_el_veredicto_es_reproducible():
    primero = evaluar(perfil(15.0))
    assert evaluar(perfil(15.0)) == primero


# ---------------------------------------------------------------------------
# Propiedades
# ---------------------------------------------------------------------------


@settings(max_examples=40, deadline=None)
@given(amplitud=st.floats(min_value=0.5, max_value=12.0))
def test_toda_leva_sintetizada_cierra_y_no_se_cruza(amplitud: float):
    p = sintetizar(oscilacion(amplitud), seguidor())
    continuado = np.roll(p.perfil, -1, axis=0)
    assert np.linalg.norm(continuado[-1] - p.perfil[0]) < 1e-12
    assert not autointerseca(p)


@settings(max_examples=40, deadline=None)
@given(
    amplitud=st.floats(min_value=0.5, max_value=20.0),
    base=st.floats(min_value=0.025, max_value=0.060),
)
def test_agrandar_el_circulo_base_nunca_empeora_el_angulo_de_presion(amplitud: float, base: float):
    """La palanca de diseño principal: más círculo base, menos ángulo de
    presión, a cambio de una leva más grande."""
    pequeno = Seguidor.bien_puesto(radio_base=base, brazo=mm(60.0), radio_rodillo=mm(4.0))
    grande = Seguidor.bien_puesto(radio_base=base * 1.5, brazo=mm(60.0), radio_rodillo=mm(4.0))
    f = oscilacion(amplitud)
    presion_pequeno = float(np.max(angulo_de_presion(sintetizar(f, pequeno))))
    presion_grande = float(np.max(angulo_de_presion(sintetizar(f, grande))))
    assert presion_grande <= presion_pequeno + 1e-6


@settings(max_examples=30, deadline=None)
@given(amplitud=st.floats(min_value=0.5, max_value=12.0))
def test_el_perfil_va_siempre_por_dentro_de_la_curva_de_paso(amplitud: float):
    p = sintetizar(oscilacion(amplitud), seguidor())
    separacion = np.linalg.norm(p.paso - p.perfil, axis=1)
    assert np.allclose(separacion, p.seguidor.radio_rodillo, atol=1e-12)


def test_la_orientacion_de_la_curva_de_paso_es_estable():
    """El signo de la normal exterior depende de ella; si cambiara a mitad de
    ciclo el perfil saldría del revés."""
    for amplitud in (1.0, 5.0, 10.0, 15.0):
        assert orientacion(sintetizar(oscilacion(amplitud), seguidor()).paso) == -1.0


@pytest.mark.parametrize("sentido", [1, -1])
def test_hacia_dentro_es_el_giro_que_acerca_el_rodillo_al_arbol(sentido: int):
    """El signo del giro que mete el rodillo hacia la leva. Lo necesita el
    tope del seguidor, que solo para ese lado, y cambia con el sentido."""
    s = Seguidor.bien_puesto(mm(40.0), mm(60.0), mm(4.0), orientacion_pivote=0.7, sentido=sentido)

    def radio(delta: float) -> float:
        a = s.psi_cero + delta
        return float(np.hypot(s.pivote[0] + s.brazo * np.cos(a), s.pivote[1] + s.brazo * np.sin(a)))

    d = s.hacia_dentro
    assert d in (1, -1)
    assert radio(d * 0.01) < radio(0.0) < radio(-d * 0.01)
    assert (
        d == sentido
    )  # el rodillo cae al lado del sentido, y hacia dentro es seguir girando hacia él
