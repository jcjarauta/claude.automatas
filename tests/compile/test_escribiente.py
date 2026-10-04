"""El compilador completo: de una frase a tres levas, con veredicto.

Aquí se comprueban los requisitos de E5 que no dependen de ningún archivo: la
simulación inversa, el determinismo, el presupuesto de tiempo y que ninguna
frase produzca salida inválida en silencio.
"""

from __future__ import annotations

import random
import time
from dataclasses import replace

import numpy as np
import pytest

from compile.escribiente import (
    ERROR_DE_TRAZO_MAXIMO,
    ORDEN_EN_LA_PILA,
    SEGUIDORES,
    Escribiente,
    compilar,
    encajar_en_la_caja,
    simular,
)
from core.cam.envelope import radio_de_curvatura
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


# ---------------------------------------------------------------------------
# La pila escalonada
# ---------------------------------------------------------------------------


def test_con_las_tres_levas_iguales_el_eje_del_rodillo_atraviesa_las_de_encima():
    """El fallo que tenía la máquina y que no veía nadie: con el mismo radio
    base en los tres canales, el eje del rodillo de abajo pasa por dentro de
    las levas de arriba. Ahora es un veredicto, no una sorpresa al montar."""
    iguales = Escribiente(brazos_de_canal=(mm(45.0), mm(45.0), mm(45.0)), sentidos=(1, 1, 1))
    v = compilar(hola(), iguales).veredicto
    assert not v.apto
    assert "eje_de_rodillo_contra_leva" in {i.codigo for i in v.incidencias}


def test_la_pila_escalonada_deja_libres_los_ejes_de_los_rodillos():
    compilacion = compilar(hola())
    holgura = compilacion.veredicto.metricas["holgura_eje_rodillo_min"]
    assert holgura >= float(Escribiente().holgura_eje_rodillo)
    # Y cada leva cabe dentro de la de debajo, que es lo que la hace sacable.
    radios = {n: float(p.radio_maximo) for n, p in compilacion.perfiles.items()}
    abajo_arriba = [radios[n] for n in ORDEN_EN_LA_PILA]
    assert abajo_arriba == sorted(abajo_arriba, reverse=True)


def test_los_tres_seguidores_comparten_postes():
    """Escalonar la pila no mueve el bastidor: los tres pivotes siguen a la
    misma distancia del árbol, la del contrato."""
    m = Escribiente()
    distancias = [float(np.hypot(*m.seguidor(i).pivote)) for i in range(3)]
    assert distancias == pytest.approx([m.distancia_al_poste] * 3)


def test_cada_leva_es_una_pieza_con_su_taladro_y_su_fase():
    for pieza in compilar(hola()).piezas:
        assert pieza.marca_fase is not None
        # Dos: el del eje, que centra, y el del pasador, que orienta.
        assert len(pieza.taladros) == 2
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
    # El seguidor oscila alrededor de cero: el calaje se lo ha llevado casi
    # todo. Casi, y no del todo, porque la referencia es el centro de la caja
    # y no la media de esta frase — ver el test siguiente.
    for perfil in compilacion.perfiles.values():
        assert abs(float(np.mean(perfil.psi))) < grados(1.0)


def test_el_calaje_es_una_constante_de_la_maquina_y_no_del_pedido():
    """**El test que devuelve el brazo al stock.**

    Si el calaje dependiera de la frase, el brazo habría que calarlo en cada
    pedido y no se podría premontar la plataforma. Cuando se calculaba como
    la media de los ángulos del ciclo, se movía 3,3° entre frases: sobre 90
    mm de brazo proximal, 5 mm de trazo desplazado.
    """
    maquina = Escribiente()
    frases = [
        hola(),
        Escritura(nombre="i", trazos=[trazo((10.0, 5.0), (10.0, 20.0))]),
        Escritura(nombre="barrido", trazos=[trazo((2.0, 2.0), (78.0, 28.0))]),
        Escritura(nombre="alta", trazos=[trazo((35.0, 1.0), (45.0, 29.0))]),
    ]
    calajes = [compilar(f, maquina).calajes for f in frases]
    for nombre in SEGUIDORES:
        valores = [c[nombre] for c in calajes]
        assert max(valores) == pytest.approx(min(valores), abs=1e-12), (
            f"el calaje de {nombre} se mueve con la frase"
        )


def test_el_calaje_es_el_angulo_del_brazo_en_el_centro_de_la_caja():
    """La referencia no es arbitraria: es el punto medio del papel, que es
    donde el brazo pasa más tiempo y donde el barrido queda repartido."""
    maquina = Escribiente()
    centro = np.array([[0.0, float(maquina.caja_centro_y)]])
    psi = maquina.brazo.inversa(centro)
    calajes = maquina.calajes(Capacidad().altura_levantamiento)
    assert calajes["izquierdo"] == pytest.approx(float(psi[0, 0]))
    assert calajes["derecho"] == pytest.approx(float(psi[0, 1]))


def test_fijar_el_calaje_apenas_cuesta_radio_de_leva():
    """El precio de que el brazo sea pieza de stock. Con la media de la frase
    la leva era mínima; con una referencia fija crece, pero poco: es lo que
    hay que comprobar que sigue siendo verdad si cambia la geometría."""
    compilacion = compilar(hola())
    radio = max(p.radio_maximo for p in compilacion.perfiles.values())
    assert radio < 0.0555, f"la leva se ha ido a {radio * 1000:.1f} mm de radio"


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


# ---------------------------------------------------------------------------
# Segunda opinión: contacto contra el perfil cortado
# ---------------------------------------------------------------------------


def test_el_compilador_apoya_el_rodillo_y_lo_anota():
    metricas = compilar(hola()).veredicto.metricas
    assert metricas["error_contacto_rad"] > 0.0
    assert metricas["error_contacto_en_la_punta"] > 0.0


def test_el_error_de_contacto_de_la_maquina_por_defecto_es_de_muestreo():
    """Viene de que la pieza que se corta es un polígono, no la curva. Si
    subiera de aquí, sería otra cosa."""
    from compile.escribiente import ERROR_DE_CONTACTO_AVISO

    assert compilar(hola()).veredicto.metricas["error_contacto_rad"] < ERROR_DE_CONTACTO_AVISO


def test_mas_muestras_por_vuelta_bajan_el_error_de_contacto():
    def contacto(muestras: int) -> float:
        return compilar(hola(), capacidad=Capacidad(muestras=muestras)).veredicto.metricas[
            "error_contacto_rad"
        ]

    assert contacto(1440) < contacto(360)


def test_del_socavado_se_ocupa_la_envolvente_y_el_contacto_solo_lo_nota():
    """Reparto de papeles, y conviene tenerlo escrito. El socavado es local:
    pasa en unos pocos grados, y cazarlo por contacto exigiría muestrear todo
    el ciclo. La envolvente lo calcula exacto y gratis, así que es ella quien
    rechaza. El contacto solo enseña que el número sube."""
    # Relación 3 y rodillo de Ø16. Hacía falta subirlo: con Ø12 el caso
    # **dejó de socavar** al empezar a redondear las esquinas del trazo, que
    # es justo la medida de lo que valía el redondeo. Ahora el socavado que
    # se prueba es el de verdad —un rodillo que no cabe en el valle— y no el
    # que fabricaba una esquina de la polilínea.
    sana = compilar(hola())
    socavada = compilar(hola(), Escribiente(relacion=3.0, radio_rodillo=mm(8.0)))

    assert "perfil_autointersecado" in [i.codigo for i in socavada.veredicto.errores]
    assert not socavada.veredicto.apto
    assert (
        socavada.veredicto.metricas["error_contacto_rad"]
        > 2.0 * sana.veredicto.metricas["error_contacto_rad"]
    )


def test_un_desplazamiento_del_reves_si_lo_caza_el_contacto():
    """Esto es para lo que sirve: un error sistemático, el mismo en todo el
    ciclo. La simulación del trazo no lo vería, porque usa las mismas
    fórmulas que lo cometieron."""
    from compile.escribiente import verificar_por_contacto

    compilacion = compilar(hola())
    maquina = Escribiente()
    al_reves = {}
    for nombre, perfil in compilacion.perfiles.items():
        al_reves[nombre] = replace(
            perfil, perfil=perfil.paso + perfil.seguidor.radio_rodillo * perfil.normales
        )
    _, _, incidencias = verificar_por_contacto(al_reves, maquina)
    assert "contacto_discrepante" in [i.codigo for i in incidencias]


def test_la_simulacion_del_trazo_no_ve_el_socavado():
    """Por eso hacía falta el contacto. Documenta el hueco con un número."""
    socavada = compilar(hola(), Escribiente(radio_rodillo=mm(6.0)))
    assert socavada.simulacion is not None
    assert socavada.simulacion.error_maximo < ERROR_DE_TRAZO_MAXIMO


# ---------------------------------------------------------------------------
# Contrato de fase: el cartucho solo se puede montar de una manera
# ---------------------------------------------------------------------------


def test_las_tres_levas_llevan_el_pasador_en_el_mismo_sitio():
    """Es lo que las cala entre sí. Si cada una lo tuviera en su ángulo, no
    podrían compartir pasador y habría que alinearlas a ojo."""
    piezas = compilar(hola()).piezas
    pasadores = {
        (round(a_mm(p.taladros[1].centro[0]), 9), round(a_mm(p.taladros[1].centro[1]), 9))
        for p in piezas
    }
    assert len(pasadores) == 1
    (x, y) = next(iter(pasadores))
    assert (x, y) == pytest.approx((a_mm(Escribiente().radio_del_pasador), 0.0), abs=1e-9)


def test_el_pasador_cae_en_material_y_no_en_el_taladro_del_eje():
    maquina = Escribiente()
    pieza = compilar(hola(), maquina).piezas[0]
    radio = a_mm(maquina.radio_del_pasador)
    assert radio - a_mm(maquina.pasador_indice) / 2 > a_mm(maquina.taladro_eje) / 2
    minimo = min((a_mm(x) ** 2 + a_mm(y) ** 2) ** 0.5 for x, y in pieza.contorno)
    assert radio + a_mm(maquina.pasador_indice) / 2 < minimo


def test_la_marca_grabada_apunta_al_pasador_y_no_a_otro_sitio():
    """Dos referencias de fase que puedan discrepar son peores que ninguna."""
    pieza = compilar(hola()).piezas[0]
    assert pieza.marca_fase is not None
    assert a_mm(pieza.marca_fase[1]) == pytest.approx(0.0, abs=0.5)
    assert a_mm(pieza.marca_fase[0]) > 0.0


def test_dos_frases_distintas_comparten_el_mismo_pasador():
    """El cartucho es intercambiable: la plataforma no cambia entre pedidos."""
    otra = Escritura(nombre="ana", trazos=[trazo((0.0, 0.0), (10.0, 14.0), (20.0, 0.0))])
    uno = compilar(hola()).piezas[0].taladros[1]
    otro = compilar(otra).piezas[0].taladros[1]
    assert uno == otro


# ---------------------------------------------------------------------------
# El veredicto de curvatura no puede depender del muestreo
# ---------------------------------------------------------------------------


def peor_radio(compilacion) -> float:
    """El radio de curvatura mínimo de la peor de las tres levas."""
    return min(
        float(r[np.isfinite(r) & (r > 0.0)].min())
        for r in (radio_de_curvatura(p) for p in compilacion.perfiles.values())
    )


def test_el_radio_de_curvatura_no_se_divide_por_dos_al_doblar_el_muestreo():
    """**El test que faltaba, y el que habría cazado el agujero.**

    Un mínimo de verdad converge al refinar; una esquina no. Sin redondear,
    el radio mínimo del perfil de «hola» iba 13,5 → 7,5 → 4,4 → 1,9 mm al
    doblar las muestras de 720 a 5.760: se dividía por dos cada vez, que es
    la firma de una curvatura infinita que el muestreo estaba redondeando por
    accidente. Un veredicto de fabricabilidad que depende de un parámetro de
    cálculo no es un veredicto.
    """
    grueso = peor_radio(compilar(hola(), capacidad=Capacidad(muestras=720)))
    fino = peor_radio(compilar(hola(), capacidad=Capacidad(muestras=5760)))
    # Una esquina divide por dos en cada doblado: por ocho al refinar ocho
    # veces. Un mínimo de verdad se acerca despacio: las levas del brazo
    # pierden un 4-7 % por doblado (19,3 → 16,5 en el izquierdo con la pila
    # sin escalonar, 9,1 → 7,6 con la escalonada) y el elevador casi nada.
    # El umbral está entre las dos firmas, lejos de las dos.
    assert grueso / fino < 1.3, (
        f"el radio mínimo pasa de {grueso * 1000:.2f} a {fino * 1000:.2f} mm al "
        "refinar ocho veces: eso no es un mínimo, es una esquina"
    )
    # Y converge: el último doblado mueve mucho menos que el primero.
    muy_fino = peor_radio(compilar(hola(), capacidad=Capacidad(muestras=11520)))
    assert fino / muy_fino < 1.08


def test_sin_redondear_la_esquina_el_radio_si_se_desploma():
    """La contraprueba: que el test de arriba mide lo que dice medir y no
    pasa por casualidad. Con radio cero vuelve el desplome."""

    def crudo(muestras: int) -> Capacidad:
        return Capacidad(muestras=muestras, radio_de_esquina=mm(0.0))

    grueso = peor_radio(compilar(hola(), capacidad=crudo(720)))
    fino = peor_radio(compilar(hola(), capacidad=crudo(5760)))
    assert grueso / fino > 4.0


def test_el_pedido_se_compila_con_las_esquinas_ya_redondeadas():
    """`Compilacion.escritura` es lo que se fabrica, así que tiene que ser la
    redondeada y no la que entró: si no, el informe describiría una cosa y la
    leva sería otra."""
    entrada = hola()
    salida = compilar(entrada).escritura
    assert len(salida.trazos[2].coordenadas) > len(entrada.trazos[2].coordenadas)


def test_un_radio_de_cero_deja_pasar_la_escritura_tal_cual():
    entrada = hola()
    salida = compilar(entrada, capacidad=Capacidad(radio_de_esquina=mm(0.0))).escritura
    assert len(salida.trazos[2].coordenadas) == len(entrada.trazos[2].coordenadas)


def test_el_pedido_dice_cuanto_se_aparta_de_lo_que_escribio_el_cliente():
    """El número de fidelidad, que es el que contesta la pregunta del
    cliente. Los otros dos no la contestan: el error de trazo compara el
    recorrido con el programa —la misma interpolación consigo misma— y C4
    cuenta holguras de piezas."""
    v = compilar(hola()).veredicto
    assert 0.0 < v.metricas["desviacion_de_lo_capturado"] < float(mm(0.5))
    assert v.metricas["radio_de_esquina"] == pytest.approx(float(mm(1.0)))


def test_sin_redondear_la_curva_se_aparta_mucho_mas_de_lo_capturado():
    """La contraprueba, y el número que estuvo escondido todo este tiempo:
    `interpolar` es una cúbica por los puntos del cliente y con una polilínea
    escasa se pasa de largo. Redondear densifica donde gira y lo quita."""
    crudo = compilar(hola(), capacidad=Capacidad(radio_de_esquina=mm(0.0)))
    suave = compilar(hola())
    assert (
        crudo.veredicto.metricas["desviacion_de_lo_capturado"]
        > 5.0 * (suave.veredicto.metricas["desviacion_de_lo_capturado"])
    )


def test_una_frase_que_empieza_arriba_a_la_izquierda_no_salta_una_vuelta():
    """El brazo derecho apunta hacia la izquierda —los proximales se cruzan—
    y su ángulo vive junto a ±180°. Una frase que empieza arriba a la
    izquierda de la caja lo hacía saltar de +180° a -180°, y ese salto de
    una vuelta llegaba a la leva derecha como 360°/8 = 45° de desviación: el
    seguidor contra el tope y 90° de presión, en una diagonal de nada. Lo
    destapó «Feliz cumpleaños», cuya F empieza ahí."""
    diagonal = Escritura(
        nombre="diagonal",
        trazos=[trazo((0.0, 30.0), (10.0, 30.0), (20.0, 20.0), (40.0, 0.0), (80.0, 10.0))],
    )
    compilacion = compilar(diagonal)
    assert compilacion.veredicto.apto, [i.codigo for i in compilacion.veredicto.errores]
    for nombre, perfil in compilacion.perfiles.items():
        assert float(np.max(np.abs(perfil.psi))) < float(grados(5.0)), nombre
