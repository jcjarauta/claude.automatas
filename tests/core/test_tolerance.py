"""C4 · Cadena de tolerancias."""

from __future__ import annotations

import math

import numpy as np
import pytest

from core.actors import BrazoCincoBarras
from core.tolerance import (
    CadenaTolerancias,
    Contribucion,
    amplificacion_perfil_a_seguidor,
    amplificacion_seguidor_a_punta,
    cadena,
)
from core.units import grados, mm

pytestmark = pytest.mark.core


def brazo() -> BrazoCincoBarras:
    return BrazoCincoBarras(separacion=mm(60.0), proximal=mm(55.0), distal=mm(70.0))


def psi_en_reposo() -> np.ndarray:
    return brazo().inversa(np.array([[0.0, 0.070]]))


# -- amplificación del perfil al seguidor -----------------------------------


def test_sin_angulo_de_presion_la_amplificacion_es_la_inversa_del_brazo():
    assert amplificacion_perfil_a_seguidor(mm(60.0), 0.0) == pytest.approx(1 / 0.060)


def test_el_angulo_de_presion_amplifica_el_error():
    """A 60° el error se duplica. Es la segunda razón para vigilarlo."""
    recto = amplificacion_perfil_a_seguidor(mm(60.0), 0.0)
    inclinado = amplificacion_perfil_a_seguidor(mm(60.0), grados(60.0))
    assert inclinado == pytest.approx(2.0 * recto, rel=1e-9)


def test_a_noventa_grados_la_amplificacion_es_infinita():
    """Es lo que significa la singularidad: el contacto ya no mueve nada."""
    assert math.isinf(amplificacion_perfil_a_seguidor(mm(60.0), grados(90.0)))


def test_un_brazo_mas_largo_amplifica_menos():
    corto = amplificacion_perfil_a_seguidor(mm(30.0), grados(20.0))
    largo = amplificacion_perfil_a_seguidor(mm(90.0), grados(20.0))
    assert largo < corto


# -- amplificación del seguidor a la punta ----------------------------------


def test_el_jacobiano_sale_positivo_y_del_orden_del_brazo():
    a = amplificacion_seguidor_a_punta(brazo(), psi_en_reposo(), 0)
    assert 0.01 < a < 0.30


def test_las_diferencias_finitas_coinciden_con_el_desplazamiento_real():
    """Contraste contra un giro finito del seguidor."""
    actuador = brazo()
    psi = psi_en_reposo()
    jacobiano = amplificacion_seguidor_a_punta(actuador, psi, 0)
    delta = 1e-5
    movido = psi.copy()
    movido[0, 0] += delta
    real = float(np.linalg.norm(actuador.directa(movido) - actuador.directa(psi)) / delta)
    assert jacobiano == pytest.approx(real, rel=1e-4)


# -- la cadena --------------------------------------------------------------


def test_el_peor_caso_suma_y_el_cuadratico_compone():
    c = CadenaTolerancias(
        contribuciones=(
            Contribucion(nombre="a", magnitud=3e-4, amplificacion=1.0),
            Contribucion(nombre="b", magnitud=4e-4, amplificacion=1.0),
        )
    )
    assert c.peor_caso == pytest.approx(7e-4)
    assert c.cuadratica == pytest.approx(5e-4)


def test_la_cadena_senala_la_holgura_dominante():
    c = CadenaTolerancias(
        contribuciones=(
            Contribucion(nombre="pequeña", magnitud=1e-5, amplificacion=1.0),
            Contribucion(nombre="gorda", magnitud=1e-3, amplificacion=1.0),
        )
    )
    dominante = c.dominante
    assert dominante is not None
    assert dominante.nombre == "gorda"


def test_una_cadena_vacia_no_tiene_dominante():
    assert CadenaTolerancias(contribuciones=()).dominante is None


def test_la_reduccion_del_pantografo_divide_todo_el_error():
    """El principio del proyecto: memoria grande, resultado pequeño."""
    comun = {
        "brazos_seguidor": (mm(60.0), mm(60.0)),
        "angulos_presion": (grados(20.0), grados(20.0)),
        "error_perfil": mm(0.15),
        "holgura_pivote": grados(0.2),
    }
    directo = cadena(brazo(), psi_en_reposo(), reduccion=1.0, **comun)  # type: ignore[arg-type]
    reducido = cadena(brazo(), psi_en_reposo(), reduccion=4.0, **comun)  # type: ignore[arg-type]
    assert reducido.peor_caso == pytest.approx(directo.peor_caso / 4.0, rel=1e-9)


def test_el_juego_de_la_transmision_no_lo_divide_la_reduccion():
    """**El error de un factor `reduccion` que es fácil de cometer.**

    El error de perfil nace en el canto de la leva, antes de la transmisión,
    así que la transmisión lo divide —o lo amplifica, si `reduccion` < 1—.
    El juego de flanco nace **dentro** de la transmisión y se mide en su
    salida, que es el eje del actuador: no lo divide nadie. Meterlo por el
    mismo sitio que el error de perfil lo equivocaría por el factor entero,
    que en el escribiente son seis veces.
    """
    comun = {
        "brazos_seguidor": (mm(60.0), mm(60.0)),
        "angulos_presion": (grados(20.0), grados(20.0)),
        "error_perfil": 0.0,
        "holgura_pivote": 0.0,
        "juego_de_la_transmision": grados(0.1),
    }
    uno = cadena(brazo(), psi_en_reposo(), reduccion=1.0, **comun)  # type: ignore[arg-type]
    seis = cadena(brazo(), psi_en_reposo(), reduccion=1.0 / 6.0, **comun)  # type: ignore[arg-type]
    assert seis.peor_caso == pytest.approx(uno.peor_caso, rel=1e-9)


def test_sin_juego_de_transmision_la_cadena_es_la_de_antes():
    """El parámetro es opcional y su ausencia no cambia ningún número: una
    máquina sin transmisión no gana contribuciones de cero que ensucien el
    recuento de `dominante`."""
    comun = {
        "brazos_seguidor": (mm(60.0), mm(60.0)),
        "angulos_presion": (grados(20.0), grados(20.0)),
        "error_perfil": mm(0.15),
        "holgura_pivote": grados(0.2),
    }
    sin = cadena(brazo(), psi_en_reposo(), **comun)  # type: ignore[arg-type]
    cero = cadena(brazo(), psi_en_reposo(), juego_de_la_transmision=0.0, **comun)  # type: ignore[arg-type]
    assert len(sin.contribuciones) == len(cero.contribuciones)
    assert sin.peor_caso == pytest.approx(cero.peor_caso)


def test_el_juego_de_la_transmision_entra_una_vez_por_seguidor():
    """Cada canal tiene su propio par de engranajes, con su propio juego."""
    c = cadena(
        brazo(),
        psi_en_reposo(),
        brazos_seguidor=(mm(60.0), mm(60.0)),
        angulos_presion=(grados(20.0), grados(20.0)),
        error_perfil=0.0,
        holgura_pivote=0.0,
        juego_de_la_transmision=grados(0.1),
    )
    cuantos = [c_.nombre for c_ in c.contribuciones if "transmisión" in c_.nombre]
    assert len(cuantos) == 2


def test_la_cadena_del_escribiente_da_un_orden_de_magnitud_razonable():
    """Con kerf de 0,15 mm y holguras de 0,2°, el error en la punta debe
    quedar por debajo del milímetro. Si no, la escritura no se reconoce."""
    c = cadena(
        brazo(),
        psi_en_reposo(),
        brazos_seguidor=(mm(60.0), mm(60.0)),
        angulos_presion=(grados(20.0), grados(20.0)),
        error_perfil=mm(0.15),
        holgura_pivote=grados(0.2),
        reduccion=1.0,
    )
    assert 0.0 < c.cuadratica < 1e-3
    assert c.peor_caso >= c.cuadratica


def test_una_magnitud_negativa_es_un_error_de_programa():
    with pytest.raises(ValueError, match="negativa"):
        Contribucion(nombre="mal", magnitud=-1e-4, amplificacion=1.0)


def test_hace_falta_un_angulo_de_presion_por_seguidor():
    with pytest.raises(ValueError, match="por seguidor"):
        cadena(
            brazo(),
            psi_en_reposo(),
            brazos_seguidor=(mm(60.0), mm(60.0)),
            angulos_presion=(grados(20.0),),
            error_perfil=mm(0.15),
            holgura_pivote=grados(0.2),
        )
