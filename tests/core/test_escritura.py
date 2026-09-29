"""Front-end de escritura: de una frase a las tres pistas indexadas por θ.

Estos tests se escribieron antes que el módulo, como manda la regla 8. Lo que
comprueban no es que el código haga lo que hace, sino que la vuelta completa
tenga sentido físico: que los arcos sumen exactamente una vuelta, que ningún
trazo se quede sin ángulo, que el lápiz esté abajo mientras escribe y arriba
mientras vuela, y que recorrer el programa reconstruya la frase.
"""

from __future__ import annotations

from itertools import pairwise

import numpy as np
import pytest

from core.escritura import (
    Capacidad,
    Escritura,
    Trazo,
    encajar,
    interpolar,
    programa,
    remuestrear,
    repartir,
)
from core.units import TAU, Metros, a_mm, grados, mm

pytestmark = pytest.mark.core

CANALES = ("punta.x", "punta.y", "levantamiento")


def trazo(*puntos: tuple[float, float]) -> Trazo:
    """Un trazo a partir de coordenadas en milímetros."""
    return Trazo(puntos=[(mm(x), mm(y)) for x, y in puntos])


def hola() -> Escritura:
    """Cuatro trazos separados, como una palabra corta escrita a mano."""
    return Escritura(
        nombre="hola",
        trazos=[
            trazo((0.0, 0.0), (0.0, 20.0)),
            trazo((0.0, 10.0), (8.0, 10.0), (8.0, 0.0)),
            trazo((14.0, 0.0), (14.0, 12.0), (20.0, 12.0), (20.0, 0.0), (14.0, 0.0)),
            trazo((26.0, 0.0), (26.0, 20.0)),
        ],
    )


def una_raya() -> Escritura:
    return Escritura(nombre="raya", trazos=[trazo((0.0, 0.0), (30.0, 0.0))])


# ---------------------------------------------------------------------------
# Geometría del trazo
# ---------------------------------------------------------------------------


def test_la_longitud_de_un_trazo_es_la_de_sus_cuerdas():
    assert a_mm(trazo((0.0, 0.0), (3.0, 4.0)).longitud) == pytest.approx(5.0)
    assert a_mm(trazo((0.0, 0.0), (3.0, 4.0), (3.0, 14.0)).longitud) == pytest.approx(15.0)


def test_un_trazo_necesita_al_menos_dos_puntos():
    with pytest.raises(ValueError, match="at least 2 items"):
        Trazo(puntos=[(Metros(0.0), Metros(0.0))])


def test_remuestrear_reparte_por_igual_en_longitud_de_arco():
    """Reparametrizar por arco es lo que hace que la punta avance a velocidad
    constante en θ: sin esto, un tramo con puntos juntos se dibujaría
    despacio y uno con puntos separados a saltos."""
    muestras = remuestrear(trazo((0.0, 0.0), (1.0, 0.0), (31.0, 0.0)), 16)
    pasos = np.linalg.norm(np.diff(muestras, axis=0), axis=1)
    assert pasos == pytest.approx(pasos[0], rel=1e-9)


def test_remuestrear_conserva_los_extremos():
    original = trazo((2.0, 3.0), (10.0, 3.0), (10.0, 9.0))
    muestras = remuestrear(original, 32)
    assert muestras[0] == pytest.approx([0.002, 0.003])
    assert muestras[-1] == pytest.approx([0.010, 0.009])


def test_remuestrear_se_queda_sobre_el_trazo():
    """Una L: todo punto remuestreado cae en uno de los dos segmentos."""
    muestras = remuestrear(trazo((0.0, 0.0), (10.0, 0.0), (10.0, 10.0)), 64)
    en_el_primero = (muestras[:, 1] < 1e-12) & (muestras[:, 0] <= 0.01 + 1e-12)
    en_el_segundo = np.abs(muestras[:, 0] - 0.01) < 1e-12
    assert np.all(en_el_primero | en_el_segundo)


def test_interpolar_en_la_mitad_del_arco_cae_en_la_mitad():
    punto = interpolar(trazo((0.0, 0.0), (20.0, 0.0)), np.array([0.5]))
    assert punto[0] == pytest.approx([0.010, 0.0])


# ---------------------------------------------------------------------------
# Normalizar
# ---------------------------------------------------------------------------


def test_encajar_mete_la_escritura_en_la_caja():
    encajada = encajar(hola(), ancho=mm(80.0), alto=mm(40.0))
    x0, y0, x1, y1 = encajada.limites
    assert a_mm(Metros(x1 - x0)) <= 80.0 + 1e-9
    assert a_mm(Metros(y1 - y0)) <= 40.0 + 1e-9


def test_encajar_conserva_la_proporcion():
    """Una letra estirada en un eje deja de parecerse a la del cliente."""
    original = hola()
    encajada = encajar(original, ancho=mm(80.0), alto=mm(40.0))
    proporcion = lambda e: a_mm(e.ancho) / a_mm(e.alto)  # noqa: E731
    assert proporcion(encajada) == pytest.approx(proporcion(original))


def test_encajar_toca_uno_de_los_dos_lados():
    """Normalizar es llenar la caja, no solo caber en ella."""
    encajada = encajar(hola(), ancho=mm(80.0), alto=mm(40.0))
    assert a_mm(encajada.ancho) == pytest.approx(80.0) or a_mm(encajada.alto) == pytest.approx(40.0)


def test_encajar_centra():
    encajada = encajar(hola(), ancho=mm(80.0), alto=mm(40.0))
    x0, y0, x1, y1 = encajada.limites
    assert a_mm(Metros(x0 + x1)) == pytest.approx(80.0)
    assert a_mm(Metros(y0 + y1)) == pytest.approx(40.0)


def test_encajar_tambien_agranda():
    diminuta = Escritura(nombre="chica", trazos=[trazo((0.0, 0.0), (1.0, 1.0))])
    assert a_mm(encajar(diminuta, ancho=mm(50.0), alto=mm(50.0)).ancho) == pytest.approx(50.0)


# ---------------------------------------------------------------------------
# Reparto de grados
# ---------------------------------------------------------------------------


def test_los_arcos_suman_una_vuelta_exacta():
    """Si no suman 2π, el programa no cierra y la leva sale con un escalón."""
    tramos, veredicto = repartir(hola(), Capacidad())
    assert veredicto.apto
    assert sum(float(t.arco) for t in tramos) == pytest.approx(TAU, abs=1e-12)


def test_los_tramos_van_seguidos_y_empiezan_en_cero():
    tramos, _ = repartir(hola(), Capacidad())
    assert float(tramos[0].inicio) == 0.0
    for anterior, siguiente in pairwise(tramos):
        assert float(siguiente.inicio) == pytest.approx(
            float(anterior.inicio) + float(anterior.arco)
        )


def test_se_alterna_trazo_y_vuelo_y_se_vuelve_al_principio():
    """El último tramo es el vuelo de regreso: el ciclo se cierra solo."""
    tramos, _ = repartir(hola(), Capacidad())
    assert [t.clase for t in tramos] == ["trazo", "vuelo"] * 4


def test_un_trazo_largo_recibe_mas_angulo_que_uno_corto():
    escritura = Escritura(
        nombre="dos",
        trazos=[trazo((0.0, 0.0), (40.0, 0.0)), trazo((0.0, 20.0), (10.0, 20.0))],
    )
    tramos, _ = repartir(escritura, Capacidad())
    largo, corto = (t for t in tramos if t.clase == "trazo")
    assert float(largo.arco) > float(corto.arco)


def test_ningun_trazo_baja_del_minimo():
    """Un punto sobre una i no puede quedarse sin ángulo: la leva tendría un
    escalón vertical en ese grado."""
    capacidad = Capacidad()
    escritura = Escritura(
        nombre="i",
        trazos=[trazo((0.0, 0.0), (0.0, 20.0)), trazo((0.0, 24.0), (0.01, 24.0))],
    )
    tramos, _ = repartir(escritura, capacidad)
    for tramo in tramos:
        if tramo.clase == "trazo":
            assert float(tramo.arco) >= float(capacidad.arco_minimo_trazo) - 1e-12


def test_todo_vuelo_deja_sitio_para_subir_y_bajar():
    capacidad = Capacidad()
    tramos, _ = repartir(hola(), capacidad)
    for tramo in tramos:
        if tramo.clase == "vuelo":
            assert float(tramo.arco) >= 2.0 * float(capacidad.arco_levantamiento) - 1e-12


def test_demasiados_trazos_no_caben_en_una_vuelta():
    """Es un veredicto, no una excepción: la frase no cabe y hay que decir
    qué cambiar."""
    muchos = Escritura(
        nombre="demasiado",
        trazos=[trazo((float(i), 0.0), (float(i), 5.0)) for i in range(60)],
    )
    _, veredicto = repartir(muchos, Capacidad())
    assert not veredicto.apto
    assert [i.codigo for i in veredicto.errores] == ["capacidad_superada"]
    assert veredicto.errores[0].sugerencia is not None


def test_el_veredicto_dice_cuanto_se_pasa():
    muchos = Escritura(
        nombre="demasiado",
        trazos=[trazo((float(i), 0.0), (float(i), 5.0)) for i in range(60)],
    )
    _, veredicto = repartir(muchos, Capacidad())
    assert veredicto.metricas["arco_minimo_necesario"] > TAU


# ---------------------------------------------------------------------------
# El programa
# ---------------------------------------------------------------------------


def test_el_programa_tiene_los_tres_canales():
    prog, _ = programa(hola(), Capacidad())
    assert prog.canales == frozenset(CANALES)


def test_las_pistas_viven_en_el_ciclo_sin_repetir_el_extremo():
    prog, _ = programa(hola(), Capacidad())
    for canal in CANALES:
        thetas = prog.pista(canal).thetas  # type: ignore[union-attr]
        assert thetas[0] == 0.0
        assert thetas[-1] < TAU
        assert all(b > a for a, b in pairwise(thetas))


def test_las_tres_pistas_comparten_rejilla():
    """Tres levas caladas en el mismo eje se leen en el mismo ángulo."""
    prog, _ = programa(hola(), Capacidad())
    rejillas = {tuple(prog.pista(c).thetas) for c in CANALES}  # type: ignore[union-attr]
    assert len(rejillas) == 1


def test_el_lapiz_esta_abajo_mientras_escribe():
    prog, _ = programa(hola(), Capacidad())
    tramos, _ = repartir(hola(), Capacidad())
    z = np.array(prog.pista("levantamiento").valores)  # type: ignore[union-attr]
    thetas = np.array(prog.pista("levantamiento").thetas)  # type: ignore[union-attr]
    for tramo in tramos:
        if tramo.clase == "trazo":
            dentro = (thetas >= float(tramo.inicio)) & (
                thetas < float(tramo.inicio) + float(tramo.arco)
            )
            assert np.all(z[dentro] == 0.0)


def test_el_lapiz_sube_en_los_vuelos():
    capacidad = Capacidad()
    prog, _ = programa(hola(), capacidad)
    tramos, _ = repartir(hola(), capacidad)
    z = np.array(prog.pista("levantamiento").valores)  # type: ignore[union-attr]
    thetas = np.array(prog.pista("levantamiento").thetas)  # type: ignore[union-attr]
    for tramo in tramos:
        if tramo.clase == "vuelo":
            centro = float(tramo.inicio) + float(tramo.arco) / 2.0
            i = int(np.argmin(np.abs(thetas - centro)))
            assert z[i] == pytest.approx(float(capacidad.altura_levantamiento), rel=1e-6)


def test_el_levantamiento_no_da_saltos():
    """Un escalón en la leva del lápiz es un golpe. La subida es cicloidal."""
    capacidad = Capacidad(muestras=1440)
    prog, _ = programa(hola(), capacidad)
    z = np.array(prog.pista("levantamiento").valores)  # type: ignore[union-attr]
    salto = float(np.max(np.abs(np.diff(np.append(z, z[0])))))
    assert salto < float(capacidad.altura_levantamiento) / 10.0


def test_el_recorrido_reconstruye_la_escritura():
    """La prueba de verdad: recorrer el programa y comprobar que la punta pasa
    por donde pasaba la mano. El error se mide contra el tamaño de la frase."""
    escritura = encajar(hola(), ancho=mm(80.0), alto=mm(60.0))
    prog, veredicto = programa(escritura, Capacidad(muestras=2880))
    assert veredicto.apto
    x = np.array(prog.pista("punta.x").valores)  # type: ignore[union-attr]
    y = np.array(prog.pista("punta.y").valores)  # type: ignore[union-attr]
    z = np.array(prog.pista("levantamiento").valores)  # type: ignore[union-attr]
    escritos = np.column_stack([x, y])[z == 0.0]

    for original in escritura.trazos:
        for punto in remuestrear(original, 24):
            distancia = np.min(np.linalg.norm(escritos - punto, axis=1))
            assert distancia < 0.001, f"la punta no pasa por {punto * 1000} mm"


def test_mas_muestras_reconstruyen_mejor():
    escritura = encajar(hola(), ancho=mm(80.0), alto=mm(60.0))

    def error(muestras: int) -> float:
        prog, _ = programa(escritura, Capacidad(muestras=muestras))
        x = np.array(prog.pista("punta.x").valores)  # type: ignore[union-attr]
        y = np.array(prog.pista("punta.y").valores)  # type: ignore[union-attr]
        z = np.array(prog.pista("levantamiento").valores)  # type: ignore[union-attr]
        escritos = np.column_stack([x, y])[z == 0.0]
        peor = 0.0
        for original in escritura.trazos:
            for punto in remuestrear(original, 24):
                peor = max(peor, float(np.min(np.linalg.norm(escritos - punto, axis=1))))
        return peor

    assert error(2880) < error(360)


def test_compilar_dos_veces_da_lo_mismo():
    """Idempotencia: es lo que permite comparar contra un golden."""
    uno, _ = programa(hola(), Capacidad())
    otro, _ = programa(hola(), Capacidad())
    assert uno == otro


def test_escalar_la_escritura_escala_las_pistas():
    """El reparto de θ depende de la forma, no del tamaño: una frase al doble
    de tamaño se escribe con las mismas levas, más grandes."""
    pequeña, _ = programa(encajar(hola(), ancho=mm(40.0), alto=mm(30.0)), Capacidad())
    grande, _ = programa(encajar(hola(), ancho=mm(80.0), alto=mm(60.0)), Capacidad())
    px = np.array(pequeña.pista("punta.x").valores)  # type: ignore[union-attr]
    gx = np.array(grande.pista("punta.x").valores)  # type: ignore[union-attr]
    assert np.allclose(gx - np.mean(gx), 2.0 * (px - np.mean(px)))


def test_una_sola_raya_tambien_compila():
    prog, veredicto = programa(una_raya(), Capacidad())
    assert veredicto.apto
    assert prog.canales == frozenset(CANALES)


def test_el_programa_se_llama_como_la_escritura():
    prog, _ = programa(hola(), Capacidad())
    assert prog.nombre == "hola"


def test_pocas_muestras_para_el_trazo_mas_corto_avisan():
    _, veredicto = programa(hola(), Capacidad(muestras=64))
    assert veredicto.apto
    assert "resolucion_justa" in [i.codigo for i in veredicto.avisos]


def test_un_peso_de_vuelo_menor_deja_mas_angulo_a_los_trazos():
    """Un vuelo no necesita precisión: puede ir más deprisa y devolver
    ángulo a lo que sí se ve en el papel."""

    def angulo_escrito(peso: float) -> float:
        tramos, _ = repartir(hola(), Capacidad(peso_vuelo=peso))
        return sum(float(t.arco) for t in tramos if t.clase == "trazo")

    assert angulo_escrito(0.25) > angulo_escrito(1.0)


def test_el_peso_de_vuelo_esta_acotado():
    with pytest.raises(ValueError, match="greater than 0"):
        Capacidad(peso_vuelo=0.0)
    with pytest.raises(ValueError, match="less than or equal to 1"):
        Capacidad(peso_vuelo=1.5)


def test_los_angulos_minimos_son_angulos():
    """Rangos, no floats desnudos: un arco de 400° no existe."""
    with pytest.raises(ValueError, match="less than or equal"):
        Capacidad(arco_minimo_trazo=grados(400.0))
