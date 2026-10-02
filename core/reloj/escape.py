"""C12 · el escape de ancora de retroceso.

Lo que decide este modulo es **cuanto par hay que meter por el eje de la rueda
de escape** para que el pendulo no se pare. De ese numero cuelga el tren
entero, el tambor y la pesa, y por eso `docs/reloj/metodologia.md` pone el
banco de escape (R2) antes que el tren y no despues.

El calculo de aqui es una **cota inferior**, y conviene decirlo claro: supone
que toda la energia que entrega la rueda llega al pendulo. En un reloj de
madera llega entre el 2 y el 12 %, asi que el par real es entre ocho y
cincuenta veces mayor. El valor de este modulo no es predecir: es saber que
esperar del banco, y detectar que algo va mal si la medida se sale del rango.

Aqui no hay segundos salvo en `vuelta_de_la_rueda`, que traduce el periodo del
oscilador a la vuelta de la rueda y es la frontera: de ahi abajo todo son
angulos y relaciones.
"""

from __future__ import annotations

import math

from core.units import Julios, NewtonMetro


def vuelta_de_la_rueda(dientes: int, periodo: float) -> float:
    """Segundos por vuelta de la rueda de escape.

    Un diente escapa por oscilacion completa, asi que la vuelta son `dientes`
    oscilaciones. Con 30 y 2 s salen 60 s, y de ahi que la aguja de segundos
    se monte directamente en este eje sin ninguna rueda de por medio.
    """
    return dientes * periodo


def angulo_de_impulso(dientes: int) -> float:
    """Radianes que avanza la rueda en cada impulso.

    Hay **dos** impulsos por oscilacion, uno por paleta, y entre los dos la
    rueda avanza un diente entero. Olvidar el dos es el error que duplica el
    par calculado.
    """
    return 2.0 * math.pi / dientes / 2.0


def par_minimo_teorico(perdida_por_ciclo: Julios, dientes: int) -> NewtonMetro:
    """Par ideal en el eje de la rueda, sin ninguna perdida.

    La rueda entrega `par x angulo` en cada impulso y el pendulo necesita
    recuperar `perdida_por_ciclo` en cada oscilacion, repartida entre los dos
    impulsos.
    """
    return NewtonMetro(perdida_por_ciclo / 2.0 / angulo_de_impulso(dientes))


def par_con_rendimiento(par_ideal: NewtonMetro, rendimiento: float) -> NewtonMetro:
    """El par que hay que poner de verdad, dado un rendimiento global.

    `rendimiento` es la fraccion de lo que entra por el eje que acaba en el
    pendulo: el resto se lo comen el reposo del escape, el deslizamiento de
    las paletas y los pivotes. En madera anda entre 0,02 y 0,12.
    """
    if not 0.0 < rendimiento <= 1.0:
        raise ValueError(f"un rendimiento de {rendimiento} no es fisico")
    return NewtonMetro(par_ideal / rendimiento)


def abarque(dientes: int) -> float:
    """Dientes que abarca el ancora, de punta de paleta a punta de paleta.

    Tiene que ser un **entero y medio**, nunca un entero: con un abarque
    entero las dos paletas caen en la misma fase del diente y el escape deja
    de alternar -una soltaria justo cuando la otra tendria que recoger-. Y lo
    mas cerca posible de un cuarto de los dientes, que es lo que deja las dos
    paletas a un cuarto de vuelta y el ancora con proporciones manejables.

    La formula es la misma que vigila `tests/reloj/test_contratos_reloj.py`
    sobre `abarque_ancora`: el nucleo y el contrato no pueden redondear
    distinto, o uno de los dos miente.
    """
    return round(dientes / 4.0 - 0.5) + 0.5


def angulo_abarcado(dientes: int) -> float:
    """Radianes de rueda que hay entre las dos paletas."""
    return abarque(dientes) * 2.0 * math.pi / dientes


def distancia_entre_centros(radio_punta: float, dientes: int) -> float:
    """Del centro de la rueda al eje del ancora.

    La construccion clasica del ancora de retroceso pone el eje donde cada
    brazo queda **perpendicular al radio de la rueda** en el punto de
    contacto: asi la paleta empuja en la direccion del movimiento y no contra
    el eje. Eso hace el triangulo centro-contacto-eje rectangulo en el
    contacto, y la distancia sale de la hipotenusa.

    Se dispara cuando el abarque se acerca a media vuelta, y eso es lo que
    impide abarcar mucho mas de un cuarto de rueda.
    """
    return radio_punta / math.cos(angulo_abarcado(dientes) / 2.0)


def brazo_paleta(radio_punta: float, dientes: int) -> float:
    """Del eje del ancora al punto de contacto de la paleta.

    Es el cateto del mismo triangulo. Con 30 dientes y abarque 7,5 el angulo
    es de un cuarto de vuelta, el triangulo sale isosceles y el brazo mide
    justo el radio de la rueda.
    """
    return radio_punta * math.tan(angulo_abarcado(dientes) / 2.0)


def recorrido_del_ancora(amplitud: float) -> float:
    """Radianes que barre el ancora en una oscilacion, de extremo a extremo.

    La horquilla ata ancora y pendulo, asi que es el doble de la amplitud. Y
    es **todo** el presupuesto angular que hay: reposo, impulso y caida salen
    de aqui, no se suman a ello.
    """
    return 2.0 * amplitud
