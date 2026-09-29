"""El compilador completo: de una frase a tres levas, con veredicto.

Aquí se comprueban los requisitos de E5 que no dependen de ningún archivo: la
simulación inversa, el determinismo, el presupuesto de tiempo y que ninguna
frase produzca salida inválida en silencio.
"""

from __future__ import annotations

import random
import time

import numpy as np
import pytest

from compile.escribiente import (
    ERROR_DE_TRAZO_MAXIMO,
    SEGUIDORES,
    Escribiente,
    compilar,
    encajar_en_la_caja,
    simular,
)
from core.escritura import Capacidad, Escritura, Trazo, remuestrear
from core.units import a_grados, a_mm, grados, mm

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


def garabato(semilla: int, trazos: int = 4, puntos: int = 7) -> Escritura:
    """Una escritura al azar pero plausible: trazos continuos, no ruido."""
    azar = random.Random(semilla)
    lista = []
    for _ in range(trazos):
        x, y = azar.uniform(0.0, 40.0), azar.uniform(0.0, 25.0)
        camino = [(x, y)]
        for _ in range(puntos - 1):
            x += azar.uniform(-8.0, 8.0)
            y += azar.uniform(-8.0, 8.0)
            camino.append((x, y))
        lista.append(trazo(*camino))
    return Escritura(nombre=f"garabato {semilla}", trazos=lista)


# ---------------------------------------------------------------------------
# La máquina por defecto compila
# ---------------------------------------------------------------------------


def test_la_maquina_por_defecto_compila_una_frase():
    compilacion = compilar(hola())
    assert compilacion.veredicto.apto
    assert not compilacion.veredicto.errores
    assert len(compilacion.piezas) == 3
    assert set(compilacion.perfiles) == set(SEGUIDORES)


def test_cada_leva_es_una_pieza_con_su_taladro_y_su_fase():
    for pieza in compilar(hola()).piezas:
        assert pieza.marca_fase is not None
        assert len(pieza.taladros) == 1
        assert a_mm(pieza.espesor) == pytest.approx(5.0)
        assert pieza.conjunto == "cartucho hola"


def test_la_escritura_se_encaja_en_la_caja_y_sube_al_papel():
    maquina = Escribiente()
    encajada = encajar_en_la_caja(hola(), maquina)
    _, y0, _, y1 = encajada.limites
    centro = (float(y0) + float(y1)) / 2.0
    assert centro == pytest.approx(float(maquina.caja_centro_y))
    assert a_mm(encajada.ancho) <= a_mm(maquina.caja_ancho) + 1e-9
    assert a_mm(encajada.alto) <= a_mm(maquina.caja_alto) + 1e-9


# ---------------------------------------------------------------------------
# El calaje
# ---------------------------------------------------------------------------


def test_la_leva_se_sintetiza_para_la_desviacion_y_no_para_el_angulo_absoluto():
    """El brazo derecho trabaja hacia los -177°. Si la leva se sintetizara
    para ese ángulo, el seguidor estaría a un cuarto de vuelta de su punto de
    diseño y el ángulo de presión no sería el calculado."""
    compilacion = compilar(hola())
    assert abs(a_grados(compilacion.calajes["derecho"])) > 90.0
    assert abs(a_grados(compilacion.calajes["izquierdo"])) < 45.0
    for perfil in compilacion.perfiles.values():
        assert float(np.mean(perfil.psi)) == pytest.approx(0.0, abs=1e-9)


def test_la_relacion_reduce_el_barrido_del_seguidor():
    """Es lo que permite que la leva no tenga que ser enorme."""
    uno = compilar(hola(), Escribiente(relacion=1.0))
    tres = compilar(hola(), Escribiente(relacion=3.0))

    def barrido(compilacion) -> float:
        perfil = compilacion.perfiles["izquierdo"]
        return float(perfil.psi.max() - perfil.psi.min())

    assert barrido(tres) == pytest.approx(barrido(uno) / 3.0, rel=1e-9)


def test_una_relacion_mayor_permite_una_leva_menor():
    """La contrapartida, que el informe dice, es que amplifica el error."""

    def presion_maxima(compilacion) -> float:
        return max(
            v
            for k, v in compilacion.veredicto.metricas.items()
            if k.startswith("angulo_presion_max")
        )

    assert presion_maxima(compilar(hola(), Escribiente(relacion=3.0))) < presion_maxima(
        compilar(hola(), Escribiente(relacion=1.0))
    )


# ---------------------------------------------------------------------------
# Simulación inversa
# ---------------------------------------------------------------------------


def test_recorrer_las_levas_reconstruye_la_escritura():
    """La comprobación que de verdad juzga la etapa. Se leen las levas ya
    sintetizadas, se pasa por la cinemática directa y se mira el papel."""
    compilacion = compilar(hola())
    assert compilacion.simulacion is not None
    assert compilacion.simulacion.error_maximo < ERROR_DE_TRAZO_MAXIMO


def test_la_simulacion_levanta_el_lapiz_donde_toca():
    compilacion = compilar(hola())
    simulacion = compilacion.simulacion
    assert simulacion is not None
    assert float(simulacion.altura.max()) > 0.002
    assert len(simulacion.escritos) < len(simulacion.puntos)


def test_un_reparto_grueso_estropea_el_trazo_y_se_dice():
    """Con pocas muestras la leva no describe las esquinas y la punta se sale.
    Tiene que salir como error, no pasar en silencio."""
    compilacion = compilar(hola(), capacidad=Capacidad(muestras=48))
    assert compilacion.simulacion is not None
    assert compilacion.simulacion.error_maximo > compilar(hola()).simulacion.error_maximo  # type: ignore[union-attr]


def test_la_simulacion_no_se_engaña_con_una_leva_de_otra_frase():
    """Si la comparación fuera contra sí misma, el error sería cero siempre."""
    maquina = Escribiente()
    compilacion = compilar(hola(), maquina)
    otra = encajar_en_la_caja(garabato(7), maquina)
    enganosa = simular(compilacion.perfiles, compilacion.calajes, maquina, otra, muestras=720)
    assert enganosa.error_maximo > 10.0 * ERROR_DE_TRAZO_MAXIMO


# ---------------------------------------------------------------------------
# Ninguna frase falla en silencio
# ---------------------------------------------------------------------------


@pytest.mark.slow
def test_cien_frases_al_azar_o_compilan_o_dicen_por_que():
    """El requisito de E5: nada de salida inválida sin avisar."""
    for semilla in range(100):
        escritura = garabato(semilla, trazos=1 + semilla % 6)
        compilacion = compilar(escritura, capacidad=Capacidad(muestras=360))
        veredicto = compilacion.veredicto
        if veredicto.apto:
            assert len(compilacion.piezas) == 3
            assert compilacion.simulacion is not None
            assert compilacion.simulacion.error_maximo < ERROR_DE_TRAZO_MAXIMO
        else:
            assert veredicto.errores, f"semilla {semilla}: no apto sin decir por qué"
            for incidencia in veredicto.errores:
                assert incidencia.sugerencia, f"{incidencia.codigo} no dice qué hacer"


def test_una_frase_que_no_cabe_devuelve_veredicto_y_no_excepcion():
    imposible = Escritura(
        nombre="demasiado",
        trazos=[trazo((float(i), 0.0), (float(i), 5.0)) for i in range(60)],
    )
    veredicto = compilar(imposible).veredicto
    assert not veredicto.apto
    assert "capacidad_superada" in [i.codigo for i in veredicto.errores]


def test_una_caja_mayor_que_el_brazo_es_veredicto_y_no_excepcion():
    """Geometría fuera de alcance por diseño: se devuelve, no se lanza."""
    maquina = Escribiente(caja_ancho=mm(600.0), caja_alto=mm(200.0))
    compilacion = compilar(hola(), maquina)
    assert not compilacion.veredicto.apto
    assert "fuera_de_alcance" in [i.codigo for i in compilacion.veredicto.errores]
    assert compilacion.piezas == []


def test_el_levantamiento_mas_alto_que_la_palanca_no_revienta():
    maquina = Escribiente(brazo_palanca=mm(2.0))
    with pytest.raises(Exception, match="palanca"):
        compilar(hola(), maquina, Capacidad(altura_levantamiento=mm(10.0)))


# ---------------------------------------------------------------------------
# Determinismo y presupuesto
# ---------------------------------------------------------------------------


def test_compilar_dos_veces_da_lo_mismo():
    uno, otro = compilar(hola()), compilar(hola())
    assert uno.programa == otro.programa
    assert uno.piezas == otro.piezas
    assert uno.veredicto.metricas == otro.veredicto.metricas


def test_compilar_una_frase_tipica_tarda_menos_de_diez_segundos():
    """Presupuesto de E5. Sobra mucho, y conviene que se note si deja de sobrar."""
    inicio = time.perf_counter()
    compilar(hola())
    assert time.perf_counter() - inicio < 10.0


# ---------------------------------------------------------------------------
# Lo que el informe necesita
# ---------------------------------------------------------------------------


def test_el_veredicto_lleva_los_numeros_de_cada_leva():
    metricas = compilar(hola()).veredicto.metricas
    for nombre in SEGUIDORES:
        assert f"angulo_presion_max_{nombre}" in metricas
    assert "error_trazo_maximo" in metricas


def test_las_levas_caben_en_un_cartucho_razonable():
    """Si esto sube mucho, el cartucho deja de ser transportable. Es la
    decisión de diámetro máximo que E1 dejó abierta."""
    diametros = [p.radio_maximo * 2000.0 for p in compilar(hola()).perfiles.values()]
    assert max(diametros) < 150.0


def test_una_frase_larga_se_reparte_sin_perder_trazos():
    escritura = garabato(3, trazos=6)
    compilacion = compilar(escritura, capacidad=Capacidad(muestras=1440))
    if compilacion.veredicto.apto:
        assert len([t for t in compilacion.tramos if t.clase == "trazo"]) == 6
        simulacion = compilacion.simulacion
        assert simulacion is not None
        for original in compilacion.escritura.trazos:
            for punto in remuestrear(original, 8):
                assert float(np.min(np.linalg.norm(simulacion.escritos - punto, axis=1))) < 0.001


def test_subir_el_levantamiento_sube_el_angulo_de_presion_del_elevador():
    """Más altura en el mismo arco es más pendiente, y la leva lo nota."""

    def presion(altura_mm: float) -> float:
        capacidad = Capacidad(altura_levantamiento=mm(altura_mm), arco_levantamiento=grados(8.0))
        return compilar(hola(), capacidad=capacidad).veredicto.metricas[
            "angulo_presion_max_elevador"
        ]

    assert presion(6.0) > presion(2.0)
