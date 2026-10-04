"""El cartucho montado: interferencias, pila, masa e inercia.

Lo que estos tests defienden es que hay un límite de conjunto que no se ve
mirando una leva: los postes de los otros dos seguidores están a una
distancia fija, y la leva crece con la frase.
"""

from __future__ import annotations

import numpy as np
import pytest

from compile.conjunto import Cartucho, montar
from compile.escribiente import Escribiente, compilar
from core.escritura import Escritura, Trazo
from core.solido import densidad_de
from core.units import a_mm, mm

pytestmark = pytest.mark.core


def trazo(*puntos: tuple[float, float]) -> Trazo:
    return Trazo(puntos=[(mm(x), mm(y)) for x, y in puntos])


def hola() -> Escritura:
    return Escritura(
        nombre="hola",
        trazos=[
            trazo((0.0, 0.0), (0.0, 20.0)),
            trazo((0.0, 10.0), (8.0, 10.0), (8.0, 0.0)),
            trazo((14.0, 0.0), (14.0, 12.0), (20.0, 12.0), (20.0, 0.0), (14.0, 0.0)),
            trazo((26.0, 0.0), (26.0, 20.0)),
        ],
    )


# ---------------------------------------------------------------------------
# El cartucho por defecto monta
# ---------------------------------------------------------------------------


def test_el_cartucho_por_defecto_monta_sin_tocarse():
    _, veredicto = montar(compilar(hola()), Escribiente())
    assert veredicto.apto
    assert not veredicto.errores


def test_los_numeros_del_conjunto_son_plausibles():
    """Un cartucho que pesara dos kilos o midiera medio metro sería otra cosa."""
    montaje, _ = montar(compilar(hola()), Escribiente())
    assert 10.0 < a_mm(montaje.altura_pila) < 40.0
    assert 0.05 < float(montaje.masa) < 0.5
    assert float(montaje.inercia) > 0.0
    assert 40.0 < a_mm(montaje.radio_maximo) < 80.0


def test_la_pila_son_tres_levas_y_dos_separadores():
    maquina = Escribiente()
    cartucho = Cartucho()
    montaje, _ = montar(compilar(hola()), maquina, cartucho)
    esperado = 3 * float(maquina.espesor_leva) + 2 * float(cartucho.separador)
    assert float(montaje.altura_pila) == pytest.approx(esperado)


def test_la_masa_descuenta_el_taladro_del_eje():
    maquina = Escribiente()
    montaje, _ = montar(compilar(hola()), maquina)
    densidad = densidad_de(maquina.material_leva)
    agujero = np.pi * (float(maquina.taladro_eje) / 2.0) ** 2
    hueco = 3 * agujero * float(maquina.espesor_leva) * densidad
    assert hueco > 0.0
    assert float(montaje.masa) < 0.5
    # La masa con taladro tiene que ser menor que la del disco macizo.
    macizo = sum(
        np.pi * p.radio_maximo**2 * float(maquina.espesor_leva) * densidad
        for p in compilar(hola()).perfiles.values()
    )
    assert float(montaje.masa) < macizo


# ---------------------------------------------------------------------------
# El límite que decide qué frases caben
# ---------------------------------------------------------------------------


def test_una_frase_mayor_deja_menos_hueco_al_poste():
    """Es el límite de conjunto: la leva crece con el barrido del seguidor, y
    los postes están donde están."""

    def hueco(ancho_mm: float) -> float:
        maquina = Escribiente(caja_ancho=mm(ancho_mm), caja_alto=mm(ancho_mm * 0.375))
        montaje, _ = montar(compilar(hola(), maquina), maquina)
        return float(montaje.holgura_al_poste)

    assert hueco(120.0) < hueco(40.0)


def test_si_la_leva_llega_al_poste_se_rechaza():
    """Con poco radio base y sin relación, el barrido del seguidor es enorme y
    la leva se come el hueco."""
    maquina = Escribiente(caja_ancho=mm(140.0), caja_alto=mm(50.0), relacion=1.0)
    compilacion = compilar(hola(), maquina)
    if not compilacion.perfiles:
        pytest.skip("esa caja ni siquiera es alcanzable por el brazo")
    _, veredicto = montar(compilacion, maquina)
    assert not veredicto.apto
    assert "leva_contra_poste" in [i.codigo for i in veredicto.errores]


def test_un_poste_mas_gordo_deja_menos_hueco():
    compilacion = compilar(hola())
    maquina = Escribiente()
    fino, _ = montar(compilacion, maquina, Cartucho(radio_poste=mm(5.0)))
    gordo, _ = montar(compilacion, maquina, Cartucho(radio_poste=mm(12.0)))
    assert float(gordo.holgura_al_poste) < float(fino.holgura_al_poste)


def test_poco_hueco_avisa_antes_de_rechazar():
    compilacion = compilar(hola())
    _, veredicto = montar(compilacion, Escribiente(), Cartucho(holgura_minima=mm(20.0)))
    assert veredicto.apto
    assert "poco_hueco_al_poste" in [i.codigo for i in veredicto.avisos]


def test_una_pila_demasiado_alta_avisa():
    maquina = Escribiente(espesor_leva=mm(30.0))
    _, veredicto = montar(compilar(hola(), maquina), maquina, Cartucho(altura_maxima=mm(50.0)))
    assert "pila_alta" in [i.codigo for i in veredicto.avisos]


def test_una_leva_que_se_come_el_eje_se_rechaza():
    compilacion = compilar(hola())
    _, veredicto = montar(compilacion, Escribiente(), Cartucho(radio_eje=mm(60.0)))
    assert not veredicto.apto
    assert "leva_come_el_eje" in [i.codigo for i in veredicto.errores]


# ---------------------------------------------------------------------------
# Bordes
# ---------------------------------------------------------------------------


def test_sin_levas_no_hay_conjunto_que_montar():
    maquina = Escribiente(caja_ancho=mm(600.0), caja_alto=mm(200.0))
    with pytest.raises(ValueError, match="no hay levas"):
        montar(compilar(hola(), maquina), maquina)


def test_montar_dos_veces_da_lo_mismo():
    compilacion = compilar(hola())
    uno, _ = montar(compilacion, Escribiente())
    otro, _ = montar(compilacion, Escribiente())
    assert uno == otro


def test_el_veredicto_del_conjunto_lleva_sus_numeros():
    _, veredicto = montar(compilar(hola()), Escribiente())
    for clave in ("altura_pila", "masa_cartucho", "inercia_cartucho", "holgura_al_poste"):
        assert clave in veredicto.metricas


def test_el_obstaculo_es_la_valona_del_casquillo_y_no_el_poste():
    """Un poste necesita casquillo, y la valona del casquillo es bastante
    mayor que el eje. Contarlo mal fue lo que casi deja el conjunto sin
    hueco: con la valona de bronce de Ø28 el aviso salta, y con la del igus
    GFM-0810 sobre poste de Ø8 —Ø15, que es la de catálogo— sobra sitio."""
    compilacion = compilar(hola())
    maquina = Escribiente()

    def hueco(radio_mm: float) -> float:
        montaje, _ = montar(compilacion, maquina, Cartucho(radio_poste=mm(radio_mm)))
        return float(montaje.holgura_al_poste)

    # Una valona mayor come hueco milímetro a milímetro.
    assert hueco(16.0) < hueco(14.0) < hueco(7.5) < hueco(4.0)

    # Con el casquillo del contrato el conjunto sale limpio.
    _, con_igus = montar(compilacion, maquina, Cartucho(radio_poste=mm(7.5)))
    assert con_igus.apto
    assert not con_igus.incidencias

    # Y con una valona bastante mayor, salta el aviso.
    _, con_valona_grande = montar(compilacion, maquina, Cartucho(radio_poste=mm(16.0)))
    assert "poco_hueco_al_poste" in [i.codigo for i in con_valona_grande.avisos]

    # El caso que destapó todo esto —poste Ø16 con casquillo de bronce de
    # valona Ø28— quedó al filo: 3,3 mm sobre un mínimo de 3,0. Con la pila
    # escalonada la leva mayor es la del elevador, unos 2 mm más pequeña que
    # la que había, y el mismo caso sube a 4,8.
    assert 0.0045 < hueco(14.0) < 0.005


def test_el_hueco_al_poste_es_el_que_dice_el_contrato_de_bastidor():
    """11,3 mm con «hola», la valona real del GFM-0810 (Ø15) y el calaje fijo.
    Ha cambiado tres veces y por eso está clavado en un test: primero por leer
    Ø12 donde el fabricante dice Ø15, luego al fijar el calaje (9,7) y luego
    al escalonar la pila, que deja como leva mayor la del elevador."""
    montaje, _ = montar(compilar(hola()), Escribiente())
    assert float(montaje.holgura_al_poste) == pytest.approx(0.0113, abs=1e-4)


def test_los_estados_por_el_perfil_cortado_son_los_de_la_curva_de_paso():
    """La animación sale del perfil cortado; el barrido, de la curva de paso.
    Leen la misma leva, así que dan la misma máquina a micro-radianes: si un
    día discrepan, la pieza cortada no es el diseño."""
    import numpy as np

    from compile.conjunto import estados

    compilacion = compilar(hola())
    m = Escribiente()
    thetas = np.linspace(0.0, 2.0 * np.pi, 24, endpoint=False)
    paso = estados(compilacion, m, thetas)
    contacto = estados(compilacion, m, thetas, camino="contacto")
    for a, b in zip(paso, contacto, strict=True):
        assert abs(a.psi_izquierdo - b.psi_izquierdo) < 1e-5
        assert abs(a.psi_derecho - b.psi_derecho) < 1e-5
        assert abs(a.giro_balancin - b.giro_balancin) < 1e-4
    with pytest.raises(ValueError, match="camino"):
        estados(compilacion, m, thetas, camino="programa")
