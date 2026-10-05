"""Escribir un texto con una fuente monotrazo.

**Qué se comprueba y qué no.** Que las letras salgan bonitas no lo decide
un test: lo decide la fuente, que es de 1967 y está dibujada para
trazarla con una pluma. Lo que se comprueba aquí es lo que sí puede
salir mal en silencio — que la letra se apoye en la línea base, que una
no se monte sobre la siguiente, que el enlace una lo que toca y no más,
y que un carácter que la fuente no tiene se queje diciendo cuál.
"""

from __future__ import annotations

import pytest

from core.errors import LetraDesconocida
from core.tipografia import Fuente, Glifo, componer, escribir, huecos
from core.units import mm

pytestmark = pytest.mark.core


def fuente_de_prueba() -> Fuente:
    """Dos glifos de juguete, para no depender del archivo de la fuente.

    La `o` es un cuadrado de una altura de x apoyado en la línea base; la
    `n` es el mismo cuadrado partido en dos trazos que se tocan, para
    poder mirar el enlace. En unidades de fuente, con la y hacia abajo y
    la base en 9.
    """
    return Fuente(
        nombre="prueba",
        procedencia="inventada para el test",
        linea_base=9.0,
        altura_mayuscula=-12.0,
        altura_de_x=9.0,
        glifos={
            "o": Glifo(
                lado_izquierdo=0,
                avance=10,
                trazos=[[(0, 9), (0, 0), (9, 0), (9, 9), (0, 9)]],
            ),
            "n": Glifo(
                lado_izquierdo=0,
                avance=10,
                trazos=[[(0, 9), (0, 0)], [(0, 0), (9, 0)]],
            ),
            " ": Glifo(lado_izquierdo=0, avance=10, trazos=[]),
        },
    )


# ---------------------------------------------------------------------------
# Dónde cae la letra
# ---------------------------------------------------------------------------


def test_la_letra_se_apoya_en_la_linea_base_y_sube_su_altura_de_x():
    """La fuente trae la y hacia abajo y la base en 9; la escritura la
    quiere hacia arriba y apoyada en cero. Si la conversión se olvida, la
    frase sale del revés y boca abajo, que se ve; o desplazada en y, que
    no se ve porque `encajar` la vuelve a centrar."""
    escritura = escribir("o", fuente_de_prueba(), altura_de_x=mm(10.0))
    _, y0, _, y1 = escritura.limites
    assert float(y0) == pytest.approx(0.0, abs=1e-12)
    assert float(y1) == pytest.approx(0.010, rel=1e-9)


def test_la_altura_de_x_es_la_que_se_pide():
    alta = escribir("o", fuente_de_prueba(), altura_de_x=mm(20.0))
    assert float(alta.alto) == pytest.approx(0.020, rel=1e-9)


def test_la_segunda_letra_va_a_la_derecha_de_la_primera():
    """Con el avance mal aplicado las letras se montan unas sobre otras, y
    el trazo resultante sigue siendo un trazo válido: nadie protesta."""
    una = escribir("o", fuente_de_prueba(), altura_de_x=mm(10.0))
    dos = escribir("oo", fuente_de_prueba(), altura_de_x=mm(10.0))
    assert float(dos.ancho) > float(una.ancho)
    assert float(dos.ancho) == pytest.approx(float(una.ancho) + 10.0 / 9.0 * 0.010, rel=1e-9)


def test_el_espacio_separa_y_no_dibuja():
    con = escribir("o o", fuente_de_prueba(), altura_de_x=mm(10.0))
    sin = escribir("oo", fuente_de_prueba(), altura_de_x=mm(10.0))
    assert len(con.trazos) == len(sin.trazos)
    assert float(con.ancho) > float(sin.ancho)


# ---------------------------------------------------------------------------
# El enlace
# ---------------------------------------------------------------------------


def test_un_hueco_de_longitud_cero_se_une_aunque_el_enlace_sea_cero():
    """Un hueco de cero no es un enlace de la letra inglesa: es **el mismo
    recorrido de pluma guardado en dos trazos**, que es como la fuente
    almacena una «n». Dejarlos sueltos hace que la máquina levante el
    lápiz y lo vuelva a bajar en el mismo punto: 16° de la vuelta —el doble
    del arco de levantamiento— para dibujar exactamente lo mismo.

    Con enlace 0 se ve la fuente sin sus enlaces, que es para lo que está;
    partir un trazo continuo no entra en eso.
    """
    escritura = escribir("n", fuente_de_prueba(), altura_de_x=mm(10.0), enlace=0.0)
    assert len(escritura.trazos) == 1


def test_sin_enlace_no_se_salta_ningun_hueco_de_verdad():
    """Lo que enlace 0 sí hace: no unir nada que tenga separación."""
    escritura = escribir("oo", fuente_de_prueba(), altura_de_x=mm(10.0), enlace=0.0)
    assert len(escritura.trazos) == 2


def test_el_enlace_une_los_trazos_que_ya_se_tocan():
    """**Es lo que decide si una frase cabe.** Cada vuelo del lápiz se
    come grados de la vuelta, así que dos trazos que acaban y empiezan en
    el mismo punto tienen que salir como uno: levantar la pluma ahí no
    dibuja nada distinto y cuesta lo mismo que un vuelo de verdad."""
    escritura = escribir("n", fuente_de_prueba(), altura_de_x=mm(10.0))
    assert len(escritura.trazos) == 1


def test_el_enlace_no_salta_un_hueco_mayor_que_su_umbral():
    """Si uniera cualquier cosa, el punto de la i acabaría pegado a la
    letra con una raya que no existe."""
    escritura = escribir("oo", fuente_de_prueba(), altura_de_x=mm(10.0), enlace=0.05)
    assert len(escritura.trazos) == 2


# ---------------------------------------------------------------------------
# Lo que la fuente no tiene
# ---------------------------------------------------------------------------


def test_un_caracter_que_no_esta_se_queja_y_dice_cual():
    """Y no lo sustituye por su letra sin tilde. Un pedido es el nombre de
    alguien: «Begoña» con n no es un fallo menor, es otro nombre."""
    with pytest.raises(LetraDesconocida, match="ñ"):
        escribir("oñdo", fuente_de_prueba(), altura_de_x=mm(10.0))


def test_dice_todos_los_que_faltan_y_no_solo_el_primero():
    """Para no descubrirlos de uno en uno."""
    with pytest.raises(LetraDesconocida) as fallo:
        escribir("oñoü", fuente_de_prueba(), altura_de_x=mm(10.0))
    assert "ñ" in str(fallo.value)
    assert "ü" in str(fallo.value)


def test_un_texto_vacio_se_queja():
    with pytest.raises(ValueError, match="vac"):
        escribir("   ", fuente_de_prueba(), altura_de_x=mm(10.0))


# ---------------------------------------------------------------------------
# Determinismo
# ---------------------------------------------------------------------------


def test_el_mismo_texto_da_la_misma_escritura():
    """Regla 4: mismo input, misma geometría. Si esto fallara, dos pedidos
    iguales darían dos levas distintas."""
    fuente = fuente_de_prueba()
    una = escribir("ono", fuente, altura_de_x=mm(10.0))
    otra = escribir("ono", fuente, altura_de_x=mm(10.0))
    assert una.model_dump() == otra.model_dump()


# ---------------------------------------------------------------------------
# Renglones
# ---------------------------------------------------------------------------


def alto_de(escritura, indices):
    """El punto más alto y el más bajo de unos trazos, en metros."""
    ys = [float(y) for i in indices for _, y in escritura.trazos[i].puntos]
    return max(ys), min(ys)


def test_un_solo_renglon_compone_lo_mismo_que_escribir():
    """`escribir` tiene que ser `componer` visto por un lado, no otra
    implementación: dos caminos para lo mismo se separan."""
    fuente = fuente_de_prueba()
    compuesta = componer("ono", fuente, altura_de_x=mm(10.0))
    assert compuesta.escritura == escribir("ono", fuente, altura_de_x=mm(10.0))
    assert len(compuesta.renglones) == 1
    assert compuesta.renglones[0] == tuple(range(len(compuesta.escritura.trazos)))


def test_el_segundo_renglon_va_debajo_del_primero():
    """Debajo, no encima: la y de la escritura va hacia arriba, así que
    un renglón nuevo resta. Al revés se lee de abajo arriba y nadie lo
    diría mirando una sola línea."""
    compuesta = componer("oo\noo", fuente_de_prueba(), altura_de_x=mm(10.0))
    assert len(compuesta.renglones) == 2
    _, abajo_del_primero = alto_de(compuesta.escritura, compuesta.renglones[0])
    arriba_del_segundo, _ = alto_de(compuesta.escritura, compuesta.renglones[1])
    assert arriba_del_segundo < abajo_del_primero


def test_dos_renglones_no_se_tocan():
    """El interlineado sale de lo que de verdad miden las letras que hay,
    no de un número elegido: si se monta un renglón sobre otro, la frase
    se escribe y no se lee."""
    compuesta = componer("oo\noo", fuente_de_prueba(), altura_de_x=mm(10.0))
    _, abajo = alto_de(compuesta.escritura, compuesta.renglones[0])
    arriba, _ = alto_de(compuesta.escritura, compuesta.renglones[1])
    assert abajo - arriba > 0.0


def test_los_renglones_reparten_todos_los_trazos_y_ninguno_dos_veces():
    """Es el invariante que `compile.renglones.comprobar` exige: un trazo
    que falta no se escribe, y uno repetido se escribe dos veces, en dos
    cartuchos distintos."""
    compuesta = componer("ono\noo\nn", fuente_de_prueba(), altura_de_x=mm(10.0))
    todos = [i for r in compuesta.renglones for i in r]
    assert sorted(todos) == list(range(len(compuesta.escritura.trazos)))
    assert len(todos) == len(set(todos))
    assert all(r for r in compuesta.renglones)


def test_el_enlace_no_cruza_de_un_renglon_al_siguiente():
    """Un enlace grande une trazos lejanos dentro de la línea; entre
    líneas sería una raya en diagonal por toda la hoja, y además metería
    un trazo en dos renglones a la vez."""
    compuesta = componer("n\nn", fuente_de_prueba(), altura_de_x=mm(10.0), enlace=50.0)
    assert len(compuesta.renglones) == 2
    assert all(r for r in compuesta.renglones)


def test_los_dos_renglones_salen_a_la_misma_escala():
    """La composición se encaja entera una sola vez; si cada renglón
    trajera su escala, las letras de «Feliz» no medirían lo que las de
    «cumpleaños»."""
    compuesta = componer("oo\noo", fuente_de_prueba(), altura_de_x=mm(10.0))
    altos = [
        alto_de(compuesta.escritura, r)[0] - alto_de(compuesta.escritura, r)[1]
        for r in compuesta.renglones
    ]
    assert altos[0] == pytest.approx(altos[1])


def test_una_linea_en_blanco_no_crea_un_renglon_vacio():
    """Un renglón sin trazos sería un cartucho con tres levas lisas: se
    cobra y no escribe nada. `comprobar` lo rechaza aguas abajo, pero
    aquí no tiene ni que llegar a existir."""
    compuesta = componer("oo\n\n  \noo", fuente_de_prueba(), altura_de_x=mm(10.0))
    assert len(compuesta.renglones) == 2
    assert all(r for r in compuesta.renglones)


def test_un_texto_que_no_deja_ni_un_trazo_se_queja():
    with pytest.raises(ValueError, match="no hay nada que escribir"):
        componer("   \n  ", fuente_de_prueba(), altura_de_x=mm(10.0))


# ---------------------------------------------------------------------------
# Los huecos: qué se está uniendo y qué no
# ---------------------------------------------------------------------------


def test_hay_un_hueco_menos_que_trazos_en_cada_renglon():
    """Entre n trazos hay n-1 huecos. El del final de la frase al
    principio no cuenta: ese no lo decide el enlace, es el vuelo de
    regreso y lo paga la vuelta siempre."""
    f = fuente_de_prueba()
    assert [len(h) for h in huecos("ono", f, altura_de_x=mm(10.0))] == [3]
    assert [len(h) for h in huecos("on\no", f, altura_de_x=mm(10.0))] == [2, 0]


def test_los_huecos_no_cambian_con_el_enlace():
    """Es lo que permite marcarlos en el deslizante: si se movieran al
    arrastrarlo, las marcas no dirían dónde está cada hueco sino dónde
    estaba. El hueco se mide entre los trazos **crudos** de la fuente, y
    el enlace solo decide cuáles de ellos se unen.
    """
    f = fuente_de_prueba()
    assert huecos("ono", f, altura_de_x=mm(10.0)) == huecos("ono", f, altura_de_x=mm(10.0))
    # Y el mismo texto a otro tamaño da los mismos huecos, porque van en
    # alturas de x: una frase grande y una pequeña se enlazan igual.
    pequena = [h for r in huecos("ono", f, altura_de_x=mm(4.0)) for h in r]
    grande = [h for r in huecos("ono", f, altura_de_x=mm(25.0)) for h in r]
    assert pequena == pytest.approx(grande)


@pytest.mark.parametrize("enlace", [0.0, 0.2, 0.5, 1.0, 1.2, 2.0])
def test_los_huecos_predicen_cuantos_trazos_saldran(enlace):
    """**El cruce que importa.** El medidor dice «subiendo a 1,0 unes dos
    huecos más»; si esa cuenta no es la que hace el motor, el deslizante
    miente justo donde se usa para decidir.

    Un hueco por encima del enlace queda como levantada y parte el trazo;
    uno por debajo se une. Así que por renglón salen tantos trazos como
    huecos queden sin unir, más uno.
    """
    f = fuente_de_prueba()
    texto = "ono\nnoo"
    compuesta = componer(texto, f, altura_de_x=mm(10.0), enlace=enlace)
    for huecos_del_renglon, indices in zip(
        huecos(texto, f, altura_de_x=mm(10.0)), compuesta.renglones, strict=True
    ):
        quedan = sum(1 for h in huecos_del_renglon if h > enlace)
        assert len(indices) == quedan + 1


def test_no_hay_hueco_entre_un_renglon_y_el_siguiente():
    """Son cartuchos distintos: entre ellos no hay nada que enlazar, y un
    hueco ahí invitaría a subir el enlace para «ahorrar» un vuelo que no
    existe."""
    f = fuente_de_prueba()
    de_una = huecos("ononoo", f, altura_de_x=mm(10.0))
    partido = huecos("ono\nnoo", f, altura_de_x=mm(10.0))
    assert len(de_una[0]) == sum(len(h) for h in partido) + 1
