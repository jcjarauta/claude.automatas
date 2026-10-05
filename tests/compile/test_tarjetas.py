"""El catálogo de tarjetas, cruzado contra lo que la máquina sabe escribir.

**El techo no se declara, se mide, y no es el que parecía.** La primera
versión de esto iba a copiar en la ficha un «hasta 24 mm de alto escrito»,
sacado de un barrido que movía el ancho y el alto a la vez. Medido un eje
cada vez, ese número **no existe**: con «hola» tecleada, una caja de
75,7 × 30 falla y una de 85 × 33,7 —más grande— pasa. No hay umbral de
tamaño.

Lo que sí es monótono es la **relación de curvatura**, que baja según la
caja crece: 2,34 a 22 mm, 2,13 a 24, 1,96 a 26, 1,07 a 30. Por debajo de
1 el rodillo no entra; entre 28 y 30 el recorte de la envolvente falla y
sale error, y a partir de 31 vuelve a funcionar con relación 1,00 —el
rodillo justo sin entrar y la leva cortada—. Ese «pasa» no es un formato
entregable, es un filo.

Por eso el listón no es `apto`: es **que no haya que recortar ninguna
leva**. Una leva recortada escribe la letra redondeada y cuánto solo lo
dice la simulación; un formato del catálogo no puede depender de eso.

El catálogo, entonces, no promete nada por escrito: lo promete este test,
compilando los casos de referencia en cada formato. Es el cruce de siempre
—dos cosas que describen lo mismo desde lados distintos— y evita el fallo
que lo motivó: con la caja que el contrato trae hoy, «hola» tecleada lleva
meses sin poder fabricarse y nada protestaba.
"""

from __future__ import annotations

import pytest

from compile.escribiente import compilar
from compile.tarjetas import cargar_tarjeta, maquina_para, tarjetas
from core.tarjeta import Tarjeta
from core.units import Metros, a_mm
from tests.casos import CASOS

pytestmark = pytest.mark.core

ESCRIBIBLES = ("tecleada", "alta", "hola", "firma", "puntos")
"""Los casos que cualquier formato del catálogo tiene que escribir.

`apretada` no está a propósito: no cabe en ninguna caja y su sitio es el
golden del veredicto negativo. `alta` sí, y es el que de verdad juzga el
formato: su relación de curvatura es la más justa de los cinco, así que es
el primero que se queda sin rodillo cuando la caja crece.
"""


def todas() -> list[Tarjeta]:
    return [cargar_tarjeta(n) for n in tarjetas()]


def test_el_catalogo_no_esta_vacio():
    """Un catálogo vacío haría pasar todos los demás tests sin comprobar
    nada, que es la forma más tonta de tener cobertura."""
    assert tarjetas()


@pytest.mark.parametrize("nombre", tarjetas())
def test_la_caja_sale_del_papel_menos_los_margenes(nombre):
    """Declarar la caja además del papel permitiría que se contradijeran.
    Aquí solo se declara el margen y la caja se deriva, así que lo que se
    comprueba es que la derivación tiene sentido: una caja dentro del
    papel y con los dos lados positivos."""
    t = cargar_tarjeta(nombre)
    assert 0.0 < t.caja_ancho < float(t.papel_ancho)
    assert 0.0 < t.caja_alto < float(t.papel_alto)


@pytest.mark.parametrize("nombre", tarjetas())
@pytest.mark.parametrize("caso", ESCRIBIBLES)
def test_todo_formato_del_catalogo_escribe_los_casos_de_referencia(nombre, caso):
    """**El test de techos.** Si un formato no escribe estos, no entra en
    el catálogo: el fallo salta al añadirlo y no en el primer pedido.

    Dos listones, y el segundo es el que importa. Sin errores, claro; y
    **sin recortar ninguna leva**, porque una leva recortada escribe la
    letra redondeada y cuánto solo sale de recorrerla. Ofrecer un formato
    que dependa de eso es ofrecerlo sin saber qué entrega.

    Se usa el camino corto porque el largo tarda cuarenta y cinco segundos
    por caso recortado, y aquí hay cinco casos por formato.
    """
    maquina = maquina_para(cargar_tarjeta(nombre))
    veredicto = compilar(CASOS[caso](), maquina=maquina, simular_el_trazo=False).veredicto
    assert veredicto.apto, f"la tarjeta «{nombre}» no escribe «{caso}»: " + "; ".join(
        f"{i.codigo} — {i.mensaje}" for i in veredicto.errores
    )
    recortadas = int(veredicto.metricas.get("levas_recortadas", 0))
    assert recortadas == 0, (
        f"la tarjeta «{nombre}» escribe «{caso}» recortando {recortadas} leva(s): la letra "
        f"sale redondeada y cuánto no se sabe sin simular. Achica la caja"
    )


def test_el_catalogo_y_el_contrato_no_dicen_todavia_lo_mismo():
    """**Esto no es una comprobación, es un aviso con fecha de caducidad.**

    La tarjeta `a7_apaisado` del catálogo es el mismo papel del contrato
    con 3 mm más de margen delante y detrás: caja de 80 × 24 en vez de
    80 × 30. El contrato —`caja_alto` en `docs/contratos.json`— sigue
    diciendo 30, y con 30 el caso `alta` no se puede fabricar.

    La regla 9 dice que un contrato congelado no se toca sin decirlo, así
    que el cambio está **propuesto y sin hacer**. Este test fija la
    discrepancia para que no se olvide: el día que `caja_alto` baje, falla,
    y lo que hay que hacer entonces es borrarlo.
    """
    from compile.escribiente import Escribiente

    contrato = Escribiente()
    catalogo = cargar_tarjeta("a7_apaisado")

    assert a_mm(contrato.caja_alto) == pytest.approx(30.0), (
        "el contrato ha cambiado: si `caja_alto` ya no es 30, borra este test"
    )
    assert a_mm(Metros(catalogo.caja_alto)) == pytest.approx(24.0)

    # Y la razón de que no sean iguales, medida y no afirmada.
    veredicto = compilar(CASOS["alta"](), maquina=contrato, simular_el_trazo=False).veredicto
    assert not veredicto.apto
    assert "perfil_autointersecado" in {i.codigo for i in veredicto.errores}
