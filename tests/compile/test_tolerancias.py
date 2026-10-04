"""El presupuesto de error del escribiente.

Lo que se comprueba aquí no son valores absolutos —dos de las cuatro
contribuciones no están medidas— sino **relaciones que tienen que cumplirse
sea cual sea la geometría**: que el varillaje amplifique, que amplifique más
cuanto mayor es la relación, y que el error del modelo no se amplifique
porque ya está medido en la punta.

Un test que clavara «2,79 mm» solo diría que nadie ha tocado los valores por
defecto. Estos dicen que la física está bien montada.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest

from compile.escribiente import Escribiente, compilar
from compile.tolerancias import (
    Holguras,
    amplificacion_del_canto,
    presupuesto_de_error,
)
from core.escritura import Escritura, Trazo
from core.units import Radianes, mm

pytestmark = pytest.mark.core


def hola() -> Escritura:
    datos = json.loads(Path("demo/hola.json").read_text(encoding="utf-8"))
    return Escritura(
        nombre=datos["nombre"],
        trazos=[
            Trazo(puntos=[(mm(float(x)), mm(float(y))) for x, y in trazo])
            for trazo in datos["trazos"]
        ],
    )


def presupuesto(maquina: Escribiente | None = None, holguras: Holguras | None = None):
    maquina = maquina or Escribiente()
    return presupuesto_de_error(compilar(hola(), maquina), maquina, holguras)


# ---------------------------------------------------------------------------
# El varillaje amplifica, y esa es toda la cuestión
# ---------------------------------------------------------------------------


def test_un_error_en_el_canto_llega_a_la_punta_muy_amplificado():
    """Es el número que cambia con quién corta la leva, y el que decide la
    precisión real de la máquina."""
    p = presupuesto()
    del_perfil = [c for c in p.cadena.contribuciones if "perfil" in c.nombre]
    assert del_perfil
    for contribucion in del_perfil:
        assert contribucion.amplificacion > 10.0


def test_la_cuenta_de_cabeza_se_queda_corta_frente_al_jacobiano():
    """`relacion × proximal / brazo_seguidor` da 10,4 con el brazo de 52 del
    derecho, y sirve para hablar con
    el taller. Pero el cinco barras mueve la punta con una palanca efectiva
    mayor que el brazo proximal, así que la amplificación real es casi el
    doble. La cuenta corta es optimista y conviene no confundirlas."""
    maquina = Escribiente()
    de_cabeza = amplificacion_del_canto(maquina)
    assert de_cabeza == pytest.approx(6.0 * 90.0 / 52.0)
    real = max(c.amplificacion for c in presupuesto().cadena.contribuciones if "perfil" in c.nombre)
    assert real > de_cabeza


def test_subir_la_relacion_del_varillaje_empeora_el_error():
    """La contrapartida que `Escribiente.relacion` promete en su docstring:
    la leva se hace pequeña y el error se hace grande, por el mismo factor.
    Es lo que C4 existe para poner encima de la mesa."""
    tres = presupuesto(Escribiente(relacion=3.0)).peor_caso
    seis = presupuesto(Escribiente(relacion=6.0)).peor_caso
    ocho = presupuesto(Escribiente(relacion=8.0)).peor_caso
    assert tres < seis < ocho


def test_el_error_del_modelo_no_se_amplifica():
    """Ya está medido en la punta: es lo que el simulador ve en el papel.
    Amplificarlo sería contarlo dos veces."""
    p = presupuesto()
    modelo = next(c for c in p.cadena.contribuciones if "modelo" in c.nombre)
    assert modelo.amplificacion == pytest.approx(1.0)


def test_el_hardware_domina_sobre_el_modelo():
    """La conclusión que reordena dónde mirar: la precisión de este producto
    no la decide el compilador.

    Decía «la decide quien corta la leva», y era verdad hasta que el
    amplificador 6:1 pasó de ser un escalar a ser un par de engranajes. Lo
    que no cambia es que **el término del compilador es el pequeño**: el
    muestreo de la leva aporta menos de la quinta parte que el dominante,
    sea cual sea. Ajustar el muestreo no arregla esta máquina.

    Con el perfil a ±0,05 era cinco veces más que el muestreo. **Al pedir
    ±0,02 deja de serlo**: el corte sigue mandando, pero el muestreo pasa a
    ser un tercio del dominante, y subir las muestras empieza a valer la pena.
    Las dos cosas quedan dichas aquí.
    """
    flojo = presupuesto(holguras=Holguras(error_de_perfil=mm(0.05)))
    modelo = next(c for c in flojo.cadena.contribuciones if "modelo" in c.nombre)
    assert flojo.dominante is not None
    assert "modelo" not in flojo.dominante.nombre
    assert flojo.dominante.en_punta > 5.0 * modelo.en_punta

    p = presupuesto()
    modelo = next(c for c in p.cadena.contribuciones if "modelo" in c.nombre)
    assert p.dominante is not None
    assert "modelo" not in p.dominante.nombre
    assert 2.0 * modelo.en_punta < p.dominante.en_punta < 5.0 * modelo.en_punta


def test_la_cinta_no_le_quita_el_primer_puesto_al_corte():
    """**El motivo por el que el amplificador es una cinta y no engranajes.**

    Aquí vivía el test contrario, que pinchaba que el juego de flanco de un
    par de calidad 8d —1,98 mm en la punta— desbancaba al corte y llevaba el
    peor caso de 2,8 a 6,7 mm. Decía que había que borrarlo si se cambiaba
    de mecanismo, y eso es lo que ha pasado.

    Una cinta anclada por los dos extremos no tiene juego, solo elasticidad:
    0,092 mm en la punta con el fleje de 0,05 x 5, veinte veces menos. El
    corte vuelve a ser el término dominante y el presupuesto queda en 3,02.

    El margen del test es un quinto del dominante y no un milímetro: si
    alguien adelgaza la cinta o alarga el vano hasta que la elasticidad pese
    como el corte, la decisión habrá dejado de estar justificada y esto
    tiene que decirlo.

    Con el perfil a ±0,02 la cinta sigue sin mandar, pero ya pesa casi la
    mitad que el corte: es la siguiente palanca, después del corte.
    """
    flojo = Holguras(error_de_perfil=mm(0.05))
    con = presupuesto(holguras=flojo)
    sin = presupuesto(holguras=flojo.model_copy(update={"juego_del_amplificador": Radianes(0.0)}))
    assert con.dominante is not None
    assert "perfil" in con.dominante.nombre
    transmision = sum(c.en_punta for c in con.cadena.contribuciones if "transmisión" in c.nombre)
    assert transmision < 0.20 * con.dominante.en_punta
    assert con.peor_caso == pytest.approx(sin.peor_caso, abs=4e-4)

    fino = presupuesto()
    assert fino.dominante is not None
    assert "perfil" in fino.dominante.nombre
    cinta = sum(c.en_punta for c in fino.cadena.contribuciones if "transmisión" in c.nombre)
    assert 0.3 * fino.dominante.en_punta < cinta < fino.dominante.en_punta


def test_el_juego_de_flanco_no_lo_divide_la_relacion():
    """Lo mismo que vigila `core`, visto desde el escribiente: subir la
    relación del varillaje amplifica el error del canto y **no** el juego de
    los engranajes, porque este ya está en el lado del brazo."""
    seis = presupuesto(maquina=Escribiente(relacion=6.0))
    tres = presupuesto(maquina=Escribiente(relacion=3.0))
    juego = lambda p: sum(  # noqa: E731
        c.en_punta for c in p.cadena.contribuciones if "transmisión" in c.nombre
    )
    assert juego(seis) == pytest.approx(juego(tres), rel=1e-9)


# ---------------------------------------------------------------------------
# Las holguras son datos declarados, y se nota cuando cambian
# ---------------------------------------------------------------------------


def test_apretar_la_tolerancia_del_taller_baja_el_error_proporcionalmente():
    flojo = presupuesto(holguras=Holguras(error_de_perfil=mm(0.10)))
    apretado = presupuesto(holguras=Holguras(error_de_perfil=mm(0.05)))
    del_perfil = lambda p: sum(  # noqa: E731
        c.en_punta for c in p.cadena.contribuciones if "perfil" in c.nombre
    )
    assert del_perfil(flojo) == pytest.approx(2.0 * del_perfil(apretado), rel=1e-6)


def test_el_desgaste_se_suma_al_error_de_corte():
    """Una leva gastada es una leva mal cortada: entran por el mismo sitio."""
    nueva = presupuesto(holguras=Holguras(desgaste=mm(0.0)))
    usada = presupuesto(holguras=Holguras(desgaste=mm(0.05)))
    assert usada.peor_caso > nueva.peor_caso


def test_el_juego_de_los_pivotes_cuenta_y_no_esta_medido():
    """Es la contribución con más incertidumbre y la que mide E4."""
    sin = presupuesto(holguras=Holguras(holgura_de_pivote=Radianes(0.0)))
    con = presupuesto(holguras=Holguras(holgura_de_pivote=Radianes(4.0e-4)))
    assert con.peor_caso > sin.peor_caso


# ---------------------------------------------------------------------------
# Los dos totales
# ---------------------------------------------------------------------------


def test_el_peor_caso_es_mayor_que_el_cuadratico():
    """Todo conspirando frente a holguras independientes. La diferencia es
    grande, y decir cuál se usa no es una formalidad."""
    p = presupuesto()
    assert p.peor_caso > p.cuadratica
    assert p.cuadratica > 0.0


def test_la_cadena_se_evalua_en_el_peor_punto_del_ciclo():
    """La amplificación cambia con la postura del varillaje. Evaluar en una
    posición cualquiera daría un número que no se puede prometer."""
    p = presupuesto()
    assert 0.0 <= p.theta_peor < 2.0 * np.pi


def test_una_compilacion_que_no_llego_a_simular_no_se_presupuesta():
    maquina = Escribiente(caja_ancho=mm(600.0), caja_alto=mm(200.0))
    compilacion = compilar(hola(), maquina)
    with pytest.raises(ValueError, match="no llegó a simular"):
        presupuesto_de_error(compilacion, maquina)
