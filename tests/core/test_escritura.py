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
    CANAL_X,
    CANAL_Y,
    CANAL_Z,
    Capacidad,
    Escritura,
    Trazo,
    encajar,
    interpolar,
    programa,
    redondear_esquinas,
    remuestrear,
    repartir,
    suavizar,
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


# ---------------------------------------------------------------------------
# El vuelo: la parte invisible, que era la que rompía la leva
# ---------------------------------------------------------------------------


def test_el_vuelo_sale_y_entra_tangente_al_trazo():
    """**El arreglo del socavado.**

    El vuelo era una recta del final de un trazo al principio del siguiente,
    así que en cada despegue y en cada aterrizaje había una esquina: la
    trayectoria cambiaba de dirección de golpe. Una esquina es curvatura
    infinita, y la leva la hereda.

    Como el lápiz va levantado, la forma del vuelo es libre: hacerlo salir y
    entrar tangente no cuesta un micrómetro de fidelidad.
    """
    escritura = Escritura(
        nombre="dos trazos en ángulo",
        trazos=[
            Trazo(puntos=[(mm(0.0), mm(0.0)), (mm(10.0), mm(0.0))]),
            Trazo(puntos=[(mm(20.0), mm(10.0)), (mm(20.0), mm(20.0))]),
        ],
    )
    prog, _ = programa(escritura, Capacidad(muestras=2880))
    x = np.array(prog.pista(CANAL_X).valores)
    y = np.array(prog.pista(CANAL_Y).valores)
    z = np.array(prog.pista(CANAL_Z).valores)

    xy = np.column_stack([x, y])
    velocidad = np.diff(np.vstack([xy, xy[:1]]), axis=0)
    giro = np.abs(np.diff(np.arctan2(velocidad[:, 1], velocidad[:, 0])))
    giro = np.minimum(giro, 2.0 * np.pi - giro)

    # En las transiciones lápiz arriba/abajo no puede haber un quiebro.
    apoyado = z <= 1e-9
    transiciones = np.flatnonzero(np.diff(apoyado.astype(np.int8)))
    for i in transiciones:
        vecindad = giro[max(i - 2, 0) : min(i + 2, len(giro))]
        assert np.max(vecindad) < np.radians(20.0), (
            f"quiebro de {np.degrees(np.max(vecindad)):.0f}° al despegar o aterrizar"
        )


def test_el_vuelo_empieza_y_acaba_donde_debe():
    """Suavizarlo no puede moverlo: tiene que dejar el lápiz exactamente al
    principio del trazo siguiente."""
    escritura = Escritura(
        nombre="dos",
        trazos=[
            Trazo(puntos=[(mm(0.0), mm(0.0)), (mm(10.0), mm(5.0))]),
            Trazo(puntos=[(mm(30.0), mm(20.0)), (mm(40.0), mm(25.0))]),
        ],
    )
    prog, _ = programa(escritura, Capacidad(muestras=2880))
    xy = np.column_stack([prog.pista(CANAL_X).valores, prog.pista(CANAL_Y).valores])
    z = np.array(prog.pista(CANAL_Z).valores)
    apoyado = z <= 1e-9

    # El primer punto apoyado después de un vuelo es el inicio de un trazo.
    aterrizajes = np.flatnonzero(np.diff(apoyado.astype(np.int8)) > 0) + 1
    inicios = [t.inicio for t in escritura.trazos]
    for i in aterrizajes:
        distancias = [float(np.linalg.norm(xy[i] - p)) for p in inicios]
        assert min(distancias) < 1e-4, "el vuelo no aterriza donde empieza el trazo"


def test_el_vuelo_no_se_sale_de_la_caja_de_los_trazos():
    """Una curva se abomba. Si se abombara demasiado, el lápiz levantado se
    saldría del alcance del brazo y la compilación fallaría por sorpresa."""
    escritura = Escritura(
        nombre="ida y vuelta",
        trazos=[
            Trazo(puntos=[(mm(0.0), mm(0.0)), (mm(40.0), mm(0.0))]),
            Trazo(puntos=[(mm(40.0), mm(20.0)), (mm(0.0), mm(20.0))]),
        ],
    )
    prog, _ = programa(escritura, Capacidad(muestras=1440))
    xy = np.column_stack([prog.pista(CANAL_X).valores, prog.pista(CANAL_Y).valores])
    puntos = np.vstack([t.coordenadas for t in escritura.trazos])
    holgura = 0.25 * float(np.ptp(puntos, axis=0).max())
    assert xy.min(axis=0).min() > puntos.min() - holgura
    assert xy.max(axis=0).max() < puntos.max() + holgura


def test_lo_que_se_escribe_no_cambia_al_suavizar_el_vuelo():
    """El vuelo es invisible; el trazo es el producto. Tocar uno no puede
    mover el otro ni un micrómetro."""
    escritura = Escritura(
        nombre="uno",
        trazos=[
            Trazo(puntos=[(mm(0.0), mm(0.0)), (mm(10.0), mm(3.0)), (mm(20.0), mm(0.0))]),
            Trazo(puntos=[(mm(30.0), mm(10.0)), (mm(40.0), mm(12.0))]),
        ],
    )
    prog, _ = programa(escritura, Capacidad(muestras=2880))
    xy = np.column_stack([prog.pista(CANAL_X).valores, prog.pista(CANAL_Y).valores])
    z = np.array(prog.pista(CANAL_Z).valores)
    escritos = xy[z <= 1e-9]

    def a_la_polilinea(punto: np.ndarray, poli: np.ndarray) -> float:
        """Distancia al SEGMENTO más cercano, no al vértice más cercano."""
        a, b = poli[:-1], poli[1:]
        ab = b - a
        largo = np.einsum("ij,ij->i", ab, ab)
        s = np.clip(np.einsum("ij,ij->i", punto - a, ab) / np.where(largo > 0, largo, 1), 0.0, 1.0)
        return float(np.min(np.linalg.norm(punto - (a + s[:, None] * ab), axis=1)))

    # Cada punto escrito tiene que caer sobre alguno de los trazos.
    for punto in escritos[::7]:
        cerca = min(a_la_polilinea(punto, t.coordenadas) for t in escritura.trazos)
        # 10 µm de margen: la muestra del aterrizaje cae justo en la frontera
        # del vuelo. Es cuatro órdenes menos que el error de la máquina.
        assert cerca < 1e-5, f"un punto apoyado se ha ido a {cerca * 1000:.3f} mm del trazo"


# ---------------------------------------------------------------------------
# El redondeo de esquinas: lo que un rodillo puede seguir
# ---------------------------------------------------------------------------


def esquina(giro_grados: float, brazo_mm: float = 20.0) -> Trazo:
    """Un trazo en V que **gira** los grados que se pidan.

    El parámetro es el giro, no la dirección del segundo brazo: 0° es seguir
    recto y 180° es doblarse sobre sí mismo. Es la magnitud de la que depende
    todo lo demás.
    """
    a = np.radians(giro_grados)
    return Trazo(
        puntos=[
            (mm(-brazo_mm), mm(0.0)),
            (mm(0.0), mm(0.0)),
            (mm(brazo_mm * np.cos(a)), mm(brazo_mm * np.sin(a))),
        ]
    )


def radio_minimo(puntos: np.ndarray) -> float:
    """Radio de curvatura mínimo de una polilínea, medido **en sus propios
    vértices**, en metros.

    Medirlo remuestreando más fino que las cuerdas no mide la curva: mide
    las esquinas entre cuerdas, y da un número que se va a cero según lo
    fino que se remuestree. Es el mismo error que escondía el socavado.
    """
    a, b, c = puntos[:-2], puntos[1:-1], puntos[2:]
    ab, bc, ac = b - a, c - b, c - a
    area2 = np.abs(ab[:, 0] * bc[:, 1] - ab[:, 1] * bc[:, 0])
    lados = np.linalg.norm(ab, axis=1) * np.linalg.norm(bc, axis=1) * np.linalg.norm(ac, axis=1)
    with np.errstate(divide="ignore", invalid="ignore"):
        radios = np.where(area2 > 1e-18, lados / (2.0 * area2), np.inf)
    return float(np.min(radios))


def test_una_esquina_se_redondea_al_radio_que_se_pide():
    """Un rodillo de Ø6 no puede seguir un pico. Si la trayectoria lo tiene,
    la leva lo hereda y el offset se autointerseca: socavado."""
    redondeado = redondear_esquinas(esquina(90.0), mm(2.0))
    assert radio_minimo(redondeado.coordenadas) > 0.0018


def test_un_trazo_ya_suave_no_se_toca():
    """El redondeo cuesta fidelidad: sólo se paga donde hace falta."""
    suave = Trazo(
        puntos=[(mm(float(x)), mm(float(2.0 * np.sin(x / 10.0)))) for x in range(0, 60, 2)]
    )
    igual = redondear_esquinas(suave, mm(0.5))
    assert len(igual.puntos) == len(suave.puntos)
    assert np.allclose(igual.coordenadas, suave.coordenadas)


def test_el_redondeo_no_aleja_el_trazo_mas_de_lo_que_promete():
    """Lo que se le quita al cliente tiene que ser una cota declarada, no una
    sorpresa. Una esquina redondeada a R se separa del pico menos de R."""
    radio = mm(2.0)
    original = esquina(90.0)
    redondeado = redondear_esquinas(original, radio)
    pico = original.coordenadas[1]
    lejos = float(np.max(np.linalg.norm(redondeado.coordenadas - pico, axis=1)))
    cerca = float(np.min(np.linalg.norm(redondeado.coordenadas - pico, axis=1)))
    assert cerca < float(radio), "el redondeo se ha ido demasiado lejos del pico"
    assert lejos > 0.0


def test_una_esquina_mas_cerrada_se_redondea_mas():
    """Cuanto más cierra el trazo, más material se come el arco al mismo
    radio: el apex se separa del pico R/cos(giro/2) - R. Es física, no una
    opción, y es lo que hay que poder contarle al cliente."""

    def desvio(giro: float) -> float:
        t = esquina(giro)
        return float(
            np.min(
                np.linalg.norm(
                    redondear_esquinas(t, mm(2.0)).coordenadas - t.coordenadas[1], axis=1
                )
            )
        )

    assert desvio(150.0) > desvio(90.0) > desvio(30.0)


def test_un_radio_que_no_cabe_en_el_segmento_se_recorta():
    """Con segmentos cortos no hay sitio para el arco pedido. Antes que
    pasarse de largo y cruzar el trazo, se redondea menos."""
    corto = Trazo(puntos=[(mm(0.0), mm(0.0)), (mm(2.0), mm(0.0)), (mm(2.0), mm(2.0))])
    redondeado = redondear_esquinas(corto, mm(10.0))
    dentro = redondeado.coordenadas
    assert dentro[:, 0].min() >= -1e-9
    assert dentro[:, 1].min() >= -1e-9
    assert float(redondeado.longitud) < float(corto.longitud) * 1.5


def test_el_redondeo_conserva_los_extremos():
    """El trazo tiene que seguir empezando y acabando donde empezaba: si no,
    el vuelo que lo enlaza deja de cuadrar."""
    original = esquina(60.0)
    redondeado = redondear_esquinas(original, mm(3.0))
    assert np.allclose(redondeado.inicio, original.inicio)
    assert np.allclose(redondeado.fin, original.fin)


def test_un_trazo_de_dos_puntos_no_tiene_esquinas_que_redondear():
    recto = Trazo(puntos=[(mm(0.0), mm(0.0)), (mm(10.0), mm(0.0))])
    assert np.allclose(redondear_esquinas(recto, mm(2.0)).coordenadas, recto.coordenadas)


def test_redondear_una_escritura_entera_las_redondea_todas():
    escritura = Escritura(nombre="dos picos", trazos=[esquina(90.0), esquina(45.0)])
    suavizada = suavizar(escritura, mm(2.0))
    assert len(suavizada.trazos) == len(escritura.trazos)
    for t in suavizada.trazos:
        assert radio_minimo(t.coordenadas) > 0.0015
