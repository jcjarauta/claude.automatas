"""C12 · el escape de ancora Graham.

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

    La construccion clasica del ancora pone el eje donde cada
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


def barrido_del_arco(reposo: float, suplementario: float) -> float:
    """Radianes que el diente pasa apoyado en el arco de reposo.

    Son los dos tramos en que la rueda no se mueve: el reposo propiamente
    dicho y el arco suplementario que el pendulo sigue recorriendo despues.
    La caida no cuenta porque en ese tramo el diente va por el aire.

    Multiplicado por el radio del arco da el **largo de la superficie de
    reposo**, que es la cota que el dibujo necesita: una paleta con el arco
    corto deja el diente en el vacio al final del suplementario y el escape
    se dispara solo.
    """
    return reposo + suplementario


def cuerda_de_impulso(brazo: float, impulso: float, profundidad: float) -> float:
    """Largo del plano de impulso de la paleta.

    El contacto baja `profundidad` en radio mientras la paleta barre
    `brazo x impulso` en tangencial, y el plano que une los dos extremos es
    la hipotenusa. Con la eleccion del contrato los dos catetos son iguales y
    la cuerda sale `raiz de dos` veces uno de ellos.
    """
    return math.hypot(profundidad, brazo * impulso)


def caras_de_impulso(brazo: float, impulso: float, profundidad: float) -> tuple[float, float]:
    """Inclinacion de los dos planos de impulso, en radianes.

    Devuelve `(entrada, salida)`, medidos **contra la tangente del arco de
    reposo** de cada paleta, que es la referencia que se puede trazar: el
    arco ya esta dibujado y la tangente sale de prolongarlo.

    La parte facil es la media: `atan(profundidad / (brazo x impulso))`, la
    diagonal del rectangulo que forman la bajada radial y el barrido
    tangencial. Con `profundidad = brazo x impulso` son 45 grados justos.

    La parte que no es obvia, y que es la razon de que esta funcion exista en
    vez de una constante, es que **las dos paletas no son iguales**: la
    paleta gira mientras el diente desliza sobre ella, asi que en el marco
    propio de la paleta la geometria sale sesgada hacia un lado en la entrada
    y hacia el otro en la salida. El sesgo no es un residuo de calculo, es el
    angulo de impulso **entero**, repartido mitad y mitad:

        entrada = media - impulso / 2
        salida  = media + impulso / 2

    Cortar las dos a la media -que es lo que invita a hacer un dibujo
    simetrico- deja cada una a un grado de donde va, y un grado sobre dos de
    impulso es la mitad del tramo en que entra energia.
    """
    if impulso <= 0.0:
        raise ValueError("una paleta sin impulso no tiene plano de impulso")
    media = math.atan2(profundidad, brazo * impulso)
    return media - impulso / 2.0, media + impulso / 2.0


def angulo_de_centro(radio_punta: float, radio_fondo: float, inclinacion: float) -> float:
    """Angulo de centro que subtiende un flanco recto de la punta al fondo.

    `inclinacion` es lo que el flanco se aparta de la direccion radial
    **medido en la punta**, que es como se define el socavado de la cara y la
    inclinacion del dorso, y como lo mide el revisor sobre el STEP. Lo que
    devuelve es el angulo entre el radio por la punta y el radio por el pie,
    que es lo que se teclea en un croquis.

    La conversion ingenua -`atan(altura x tan(inclinacion) / radio_punta)`- es
    la trampa: trata el desplazamiento tangencial como si ocurriera a radio de
    punta, cuando ocurre al bajar hasta el de fondo. Con punta 45, fondo 38 y
    8 grados se queda en 1,25 en vez de 1,49, y la cara sale cortada a 6,75.

    La buena sale de cortar la recta con el circulo de fondo. Con la punta en
    el eje y `t` el largo del flanco:

        t^2 - 2 R cos(a) t + (R^2 - r^2) = 0

    y de las dos raices vale la corta, que es la que cruza el circulo de
    fondo viniendo de la punta.
    """
    if inclinacion == 0.0:
        return 0.0
    coseno = math.cos(inclinacion)
    discriminante = radio_punta**2 * coseno**2 - (radio_punta**2 - radio_fondo**2)
    if discriminante <= 0.0:
        raise ValueError(
            f"un flanco a {math.degrees(inclinacion):.1f} grados no llega al fondo: "
            "sale tangente al circulo de fondo y el diente no se cierra"
        )
    largo = radio_punta * coseno - math.sqrt(discriminante)
    return math.atan2(largo * math.sin(inclinacion), radio_punta - largo * coseno)
