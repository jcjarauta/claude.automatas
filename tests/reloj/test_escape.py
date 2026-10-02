"""C12 · el escape: cuanto par pide para mantener el pendulo en marcha.

Es el calculo que decide el proyecto entero, y el que la metodologia dice que
hay que medir en R2. Lo que se hace aqui es acotarlo por arriba y por abajo
para saber que esperar del banco: si la medida sale fuera de este rango, el
que esta mal es el banco o el modelo, no el reloj.
"""

from __future__ import annotations

import math

import pytest

from core.reloj import escape
from core.units import Julios

pytestmark = pytest.mark.core


def test_un_diente_escapa_por_oscilacion_completa():
    """La relacion que hace que 30 dientes y 2 s den una vuelta por minuto, y
    que la aguja de segundos salga gratis."""
    assert escape.vuelta_de_la_rueda(dientes=30, periodo=2.0) == pytest.approx(60.0)


def test_el_impulso_reparte_el_diente_en_dos():
    """Hay dos impulsos por oscilacion, uno por paleta, y entre los dos la
    rueda avanza un diente. El angulo de cada impulso es medio paso."""
    assert escape.angulo_de_impulso(dientes=30) == pytest.approx(math.radians(6.0))


def test_el_par_teorico_son_decimas_de_milinewton_metro():
    """El orden de magnitud que ordena el plan: el par ideal es ridiculo
    comparado con lo que da la pesa, asi que lo que dimensiona el reloj no es
    el pendulo sino el rozamiento."""
    par = escape.par_minimo_teorico(perdida_por_ciclo=Julios(27.0e-6), dientes=30)
    assert 50.0e-6 < par < 500.0e-6


def test_el_par_teorico_crece_con_lo_que_pierde_el_pendulo():
    a = escape.par_minimo_teorico(perdida_por_ciclo=Julios(20.0e-6), dientes=30)
    b = escape.par_minimo_teorico(perdida_por_ciclo=Julios(40.0e-6), dientes=30)
    assert b / a == pytest.approx(2.0, rel=1e-9)


def test_mas_dientes_piden_mas_par_para_la_misma_energia():
    """Con mas dientes, cada impulso recorre menos angulo, asi que para
    entregar la misma energia hace falta mas par. Es la contrapartida de
    poner una aguja de segundos mas fina."""
    pocos = escape.par_minimo_teorico(perdida_por_ciclo=Julios(27.0e-6), dientes=30)
    muchos = escape.par_minimo_teorico(perdida_por_ciclo=Julios(27.0e-6), dientes=60)
    assert muchos > pocos


def test_el_rendimiento_real_multiplica_el_par_entre_ocho_y_cincuenta():
    """Ningun reloj de madera pasa del 12 % de rendimiento global y muchos no
    llegan al 2. Ese factor es lo que separa el calculo de la realidad, y por
    eso R2 mide en vez de calcular."""
    ideal = escape.par_minimo_teorico(perdida_por_ciclo=Julios(27.0e-6), dientes=30)
    optimista = escape.par_con_rendimiento(ideal, rendimiento=0.12)
    pesimista = escape.par_con_rendimiento(ideal, rendimiento=0.02)
    assert optimista / ideal == pytest.approx(1.0 / 0.12, rel=1e-9)
    assert pesimista / optimista == pytest.approx(6.0, rel=1e-9)


def test_un_rendimiento_imposible_no_se_acepta():
    """Un rendimiento mayor que uno daria un par menor que el ideal, que es
    energia de la nada. Mejor que reviente aqui que en una hoja de calculo."""
    with pytest.raises(ValueError, match="no es fisico"):
        escape.par_con_rendimiento(1.0e-4, rendimiento=1.5)
    with pytest.raises(ValueError, match="no es fisico"):
        escape.par_con_rendimiento(1.0e-4, rendimiento=0.0)


def test_el_abarque_del_ancora_es_un_impar_y_medio():
    """Si el abarque fuese entero, las dos paletas trabajarian en fase y el
    escape no alternaria. Tiene que ser el medio impar mas proximo a un
    cuarto de los dientes."""
    assert escape.abarque(dientes=30) == pytest.approx(7.5)
    assert escape.abarque(dientes=32) == pytest.approx(8.5)
    assert escape.abarque(dientes=36) == pytest.approx(8.5)


def test_el_ancora_abarca_un_cuarto_de_vuelta_largo():
    """Con 30 dientes y abarque 7,5 son 90 grados exactos, que es lo que hace
    que el ancora sea una pieza de proporciones manejables."""
    assert escape.angulo_abarcado(dientes=30) == pytest.approx(math.pi / 2.0)


def test_el_brazo_del_ancora_es_tangente_a_la_rueda():
    """La construccion clasica del ancora de retroceso: el eje se pone a la
    distancia que hace que cada brazo quede PERPENDICULAR al radio de la
    rueda en el punto de contacto. Asi la paleta empuja en la direccion del
    movimiento y no contra el eje."""
    radio = 45.0
    d = escape.distancia_entre_centros(radio, dientes=30)
    brazo = escape.brazo_paleta(radio, dientes=30)
    # El triangulo centro-contacto-eje tiene que ser rectangulo en el contacto
    assert brazo**2 + radio**2 == pytest.approx(d**2, rel=1e-9)


def test_con_abarque_de_noventa_grados_el_brazo_mide_el_radio():
    """Caso particular de 30 dientes y abarque 7,5: el cuarto de vuelta hace
    el triangulo isosceles y el ancora sale de proporciones manejables."""
    assert escape.brazo_paleta(45.0, dientes=30) == pytest.approx(45.0, rel=1e-9)
    assert escape.distancia_entre_centros(45.0, dientes=30) == pytest.approx(
        45.0 * math.sqrt(2.0), rel=1e-9
    )


def test_el_eje_del_ancora_queda_siempre_fuera_de_la_rueda():
    """Obvio y facil de romper con un signo: si la distancia saliera menor
    que el radio, el eje caeria dentro del dentado."""
    for dientes in (20, 30, 36, 48, 60):
        assert escape.distancia_entre_centros(45.0, dientes) > 45.0


def test_abarcar_mas_angulo_aleja_el_eje():
    """Y se dispara cerca de media vuelta, que es lo que impide abarcar mucho
    mas de un cuarto. Se compara por angulo y no por dientes: el abarque ronda
    siempre el cuarto, asi que mas dientes no significa mas angulo."""
    anchos = sorted(
        (escape.angulo_abarcado(d), escape.distancia_entre_centros(45.0, d))
        for d in (20, 30, 36, 48, 60)
    )
    distancias = [d for _, d in anchos]
    assert distancias == sorted(distancias)


def test_el_recorrido_del_ancora_es_el_del_pendulo():
    """La horquilla los ata, asi que el ancora barre exactamente lo que barre
    el pendulo. Ese es TODO el presupuesto angular que hay para repartir
    entre reposo, impulso y caida."""
    assert escape.recorrido_del_ancora(amplitud=0.0349) == pytest.approx(0.0698, rel=1e-9)


# --- C12 · el plano de impulso de la paleta --------------------------------
#
# Lo que sigue contrasta la forma cerrada contra una construccion geometrica
# que no comparte una sola linea de codigo con ella: intersectar el circulo
# de punta de la rueda con el arco de reposo de la paleta, y llevar el
# segundo contacto al marco de la paleta girandolo lo que la paleta gira.
# Es el mismo metodo que ya cruza la masa del kernel con la del poligono.


def _cara_por_construccion(
    radio_punta: float,
    entre: float,
    brazo: float,
    impulso: float,
    profundidad: float,
    lado: float,
) -> tuple[float, float]:
    """Angulo de la cara con la tangente del arco, y su cuerda, a pelo.

    `lado` vale +1 para la paleta de entrada, que apoya en el arco interior y
    el diente la empuja hacia fuera, y -1 para la de salida.
    """
    r_apoyo = brazo - lado * profundidad / 2.0
    r_suelta = brazo + lado * profundidad / 2.0

    def contacto(radio: float) -> tuple[float, float]:
        """Donde se cruzan el circulo de punta y el radio de la paleta."""
        y = (radio_punta**2 - radio**2 - entre**2) / (2.0 * entre)
        return math.sqrt(radio**2 - y**2), y

    def girar(punto: tuple[float, float], angulo: float) -> tuple[float, float]:
        x, y = punto
        return (
            x * math.cos(angulo) - y * math.sin(angulo),
            x * math.sin(angulo) + y * math.cos(angulo),
        )

    p1 = contacto(r_apoyo)
    p2 = girar(contacto(r_suelta), -impulso)
    dx, dy = p2[0] - p1[0], p2[1] - p1[1]
    radial = (dx * p1[0] + dy * p1[1]) / r_apoyo
    tangencial = (-dx * p1[1] + dy * p1[0]) / r_apoyo
    return math.atan2(abs(radial), abs(tangencial)), math.hypot(dx, dy)


def test_la_cara_de_impulso_coincide_con_la_construccion_geometrica() -> None:
    radio, entre, brazo = 0.045, 0.06364, 0.045
    impulso = math.radians(2.0)
    profundidad = brazo * impulso
    entrada, salida = escape.caras_de_impulso(brazo, impulso, profundidad)
    por_mano_e, _ = _cara_por_construccion(radio, entre, brazo, impulso, profundidad, +1.0)
    por_mano_s, _ = _cara_por_construccion(radio, entre, brazo, impulso, profundidad, -1.0)
    assert entrada == pytest.approx(por_mano_e, abs=math.radians(0.01))
    assert salida == pytest.approx(por_mano_s, abs=math.radians(0.01))


def test_las_dos_caras_difieren_exactamente_en_el_impulso() -> None:
    """La paleta gira mientras el diente desliza, y eso sesga la geometria.

    Es el error que invita a cortar las dos paletas iguales: no lo son, y la
    diferencia no es un residuo sino el angulo de impulso entero.
    """
    brazo, impulso = 0.045, math.radians(2.0)
    entrada, salida = escape.caras_de_impulso(brazo, impulso, brazo * impulso)
    assert salida - entrada == pytest.approx(impulso)


def test_cuando_la_profundidad_iguala_al_barrido_la_cara_media_es_de_45() -> None:
    """La eleccion `profundidad = brazo x impulso` es la que da los 45.

    No es una casualidad bonita: iguala la bajada radial al barrido
    tangencial, y la cara que une las dos es la diagonal del cuadrado.
    """
    brazo, impulso = 0.045, math.radians(2.0)
    entrada, salida = escape.caras_de_impulso(brazo, impulso, brazo * impulso)
    assert (entrada + salida) / 2.0 == pytest.approx(math.radians(45.0))


def test_una_cara_mas_tumbada_pide_menos_par_y_mas_recorrido() -> None:
    """Media la profundidad y la cara se tumba: es el compromiso del escape."""
    brazo, impulso = 0.045, math.radians(2.0)
    tumbada, _ = escape.caras_de_impulso(brazo, impulso, brazo * impulso / 2.0)
    normal, _ = escape.caras_de_impulso(brazo, impulso, brazo * impulso)
    assert tumbada < normal


def test_la_cuerda_de_la_cara_coincide_con_la_construccion() -> None:
    radio, entre, brazo = 0.045, 0.06364, 0.045
    impulso = math.radians(2.0)
    profundidad = brazo * impulso
    _, por_mano = _cara_por_construccion(radio, entre, brazo, impulso, profundidad, +1.0)
    assert escape.cuerda_de_impulso(brazo, impulso, profundidad) == pytest.approx(
        por_mano, rel=1e-3
    )


def test_la_cuerda_es_la_hipotenusa_de_bajada_y_barrido() -> None:
    brazo, impulso = 0.045, math.radians(2.0)
    cuerda = escape.cuerda_de_impulso(brazo, impulso, brazo * impulso)
    assert cuerda == pytest.approx(math.sqrt(2.0) * brazo * impulso)


def test_un_impulso_nulo_no_tiene_cara() -> None:
    with pytest.raises(ValueError, match="sin impulso"):
        escape.caras_de_impulso(0.045, 0.0, 0.001)


def test_el_arco_de_reposo_barre_el_reposo_y_el_suplementario() -> None:
    """El diente se queda en el arco esos dos tramos y no mas.

    La caida no cuenta: en ese tramo el diente va por el aire. Pero el arco
    se dibuja con ese margen de mas, porque un diente corto de sierra apoya
    antes y tiene que encontrar arco donde apoyar.
    """
    reposo, suplementario = math.radians(1.5), math.radians(1.75)
    assert escape.barrido_del_arco(reposo, suplementario) == pytest.approx(math.radians(3.25))


# --- C12 · del angulo de la punta al angulo de centro ----------------------


def _inclinacion_por_construccion(radio_punta: float, radio_fondo: float, centro: float) -> float:
    """El angulo que sale de verdad, midiendolo sobre el flanco dibujado.

    Coloca la punta en el eje, el pie al angulo de centro dado, y mide lo que
    el flanco se aparta de la direccion radial EN LA PUNTA. Es la definicion
    que usa el revisor de STEP, y por eso es la que vale de juez.
    """
    punta = (0.0, radio_punta)
    pie = (radio_fondo * math.sin(centro), radio_fondo * math.cos(centro))
    flanco = (pie[0] - punta[0], pie[1] - punta[1])
    coseno = -flanco[1] / math.hypot(*flanco)
    return math.acos(coseno)


def test_el_angulo_de_centro_devuelve_la_inclinacion_pedida() -> None:
    """La ida y la vuelta tienen que cerrar. Es el test que faltaba: la
    conversion anterior usaba `atan(altura x tan a / radio_punta)`, que trata
    el desplazamiento como si ocurriera en el radio de punta cuando ocurre en
    el de fondo, y se quedaba corta un 16 %."""
    for grados in (4.0, 8.0, 15.0, 22.0):
        pedido = math.radians(grados)
        centro = escape.angulo_de_centro(0.045, 0.038, pedido)
        assert _inclinacion_por_construccion(0.045, 0.038, centro) == pytest.approx(
            pedido, abs=math.radians(0.01)
        )


def test_la_formula_vieja_se_queda_corta() -> None:
    """Deja constancia del tamano del error, que no es un redondeo: 8 grados
    de socavado daban 1,25 de centro y la cara salia a 6,75."""
    pedido = math.radians(8.0)
    vieja = math.atan(0.007 * math.tan(pedido) / 0.045)
    buena = escape.angulo_de_centro(0.045, 0.038, pedido)
    assert vieja < buena
    assert _inclinacion_por_construccion(0.045, 0.038, vieja) == pytest.approx(
        math.radians(6.75), abs=math.radians(0.02)
    )


def test_una_cara_radial_no_tiene_angulo_de_centro() -> None:
    assert escape.angulo_de_centro(0.045, 0.038, 0.0) == pytest.approx(0.0)


def test_una_inclinacion_que_no_llega_al_fondo_se_rechaza() -> None:
    """Pasado cierto angulo el flanco sale tangente y nunca corta el circulo
    de fondo: el diente no se cierra y el perfil no existe."""
    with pytest.raises(ValueError, match="no llega al fondo"):
        escape.angulo_de_centro(0.045, 0.038, math.radians(60.0))


def test_el_flanco_es_mas_largo_que_la_altura_radial() -> None:
    """La altura del diente es el cateto; el flanco es la hipotenusa. Darle
    7 al compas deja el diente corto, que es el error que esta cota evita."""
    altura = 0.045 - 0.038
    for grados in (8.0, 15.0):
        flanco = escape.largo_del_flanco(0.045, 0.038, math.radians(grados))
        assert flanco > altura


def test_un_flanco_radial_mide_la_altura() -> None:
    assert escape.largo_del_flanco(0.045, 0.038, 0.0) == pytest.approx(0.007)


def test_el_flanco_cierra_el_triangulo_con_su_angulo_de_centro() -> None:
    """El flanco, el angulo de centro y los dos radios son el mismo triangulo
    resuelto por dos caminos: el pie tiene que caer en el circulo de fondo."""
    for grados in (4.0, 8.0, 15.0, 22.0):
        inclinacion = math.radians(grados)
        largo = escape.largo_del_flanco(0.045, 0.038, inclinacion)
        centro = escape.angulo_de_centro(0.045, 0.038, inclinacion)
        pie = (
            largo * math.sin(inclinacion),
            0.045 - largo * math.cos(inclinacion),
        )
        assert math.hypot(*pie) == pytest.approx(0.038, abs=1e-9)
        assert math.atan2(pie[0], pie[1]) == pytest.approx(centro, abs=1e-9)


def test_la_cuerda_siempre_es_menor_que_el_arco() -> None:
    for grados in (0.5, 7.2, 12.0, 60.0):
        angulo = math.radians(grados)
        assert escape.cuerda(0.045, angulo) < 0.045 * angulo
