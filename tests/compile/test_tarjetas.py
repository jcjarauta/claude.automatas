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


# ---------------------------------------------------------------------------
# La tarjeta por defecto, y que llegue hasta el paquete
# ---------------------------------------------------------------------------


def test_la_tarjeta_por_defecto_es_la_del_contrato():
    """El gemelo positivo del test que se borró al bajar `caja_alto`.

    La interfaz ofrece `a7_apaisado` por defecto y el CLI, sin tarjeta en el
    pedido, usa `Escribiente()`. Si las dos cajas se separaran, la vista
    previa y el paquete dirían cosas distintas **sin que nada protestara**,
    que es exactamente lo que pasó durante meses con los 30 de alto.
    """
    from api.main import TARJETA_POR_DEFECTO
    from compile.escribiente import Escribiente

    contrato = Escribiente()
    defecto = maquina_para(cargar_tarjeta(TARJETA_POR_DEFECTO))
    assert float(defecto.caja_ancho) == pytest.approx(float(contrato.caja_ancho))
    assert float(defecto.caja_alto) == pytest.approx(float(contrato.caja_alto))


def test_la_tarjeta_del_pedido_llega_al_compilador():
    """**La trampa de este cambio.** El paquete lo escribe el CLI con SU
    máquina, así que una tarjeta que se quedara en la interfaz daría una
    vista previa con una caja y un DXF con otra. Por eso va en el JSON del
    pedido, como los renglones, y no en un argumento.
    """
    import json
    import tempfile
    from pathlib import Path

    from compile.renglones import leer_pedido

    with tempfile.TemporaryDirectory() as tmp:
        ruta = Path(tmp) / "pedido.json"
        ruta.write_text(
            json.dumps({"nombre": "x", "trazos": [[[0, 0], [10, 5]]], "tarjeta": "a7_apaisado"}),
            encoding="utf-8",
        )
        assert leer_pedido(ruta).tarjeta == "a7_apaisado"

        ruta.write_text(
            json.dumps({"nombre": "x", "trazos": [[[0, 0], [10, 5]]]}), encoding="utf-8"
        )
        assert leer_pedido(ruta).tarjeta is None, "sin tarjeta, la caja del contrato"


@pytest.mark.parametrize("nombre", tarjetas())
def test_cada_tarjeta_da_una_geometria_distinta(nombre):
    """Dos formatos tienen que dar dos cartuchos. Si la tarjeta se perdiera
    por el camino, los perfiles saldrían iguales y nadie lo notaría hasta
    tener las levas cortadas."""
    from compile.escribiente import Escribiente

    base = compilar(CASOS["tecleada"](), simular_el_trazo=False)
    suyo = compilar(
        CASOS["tecleada"](), maquina=maquina_para(cargar_tarjeta(nombre)), simular_el_trazo=False
    )
    igual_que_el_contrato = float(cargar_tarjeta(nombre).caja_ancho) == pytest.approx(
        float(Escribiente().caja_ancho)
    )
    perfiles_iguales = all(
        float(base.perfiles[k].radio_maximo) == pytest.approx(float(suyo.perfiles[k].radio_maximo))
        for k in base.perfiles
    )
    assert perfiles_iguales == igual_que_el_contrato


def test_el_informe_dice_que_papel_hay_que_poner():
    """«Tamaño en el papel: 65,0 × 18,5 mm» dice lo que mide la letra y
    **no qué tarjeta meter**, que es lo que necesita quien monta. Son dos
    cosas distintas: el trazo se encaja conservando la proporción, así que
    casi nunca llena la caja.
    """
    from compile.informe import informe

    tarjeta = cargar_tarjeta("tarjeta_de_visita")
    compilacion = compilar(
        CASOS["tecleada"](), maquina=maquina_para(tarjeta), simular_el_trazo=False
    )
    texto = informe(compilacion, maquina_para(tarjeta), tarjeta=tarjeta)
    assert "tarjeta de visita" in texto
    assert "85 × 55 mm" in texto, "el papel, que es lo que hay que ir a buscar"
    assert "65 × 20 mm" in texto, "y la caja, que es donde cae la letra"


def test_sin_tarjeta_el_informe_sigue_diciendo_algo_accionable():
    """Un pedido anterior al catálogo, o el CLI a pelo. Decir solo el
    tamaño del trazo dejaría a quien monta sin saber qué papel sirve; la
    caja del contrato sí lo dice: cualquiera que la contenga con margen."""
    from compile.escribiente import Escribiente
    from compile.informe import informe

    compilacion = compilar(CASOS["tecleada"](), simular_el_trazo=False)
    texto = informe(compilacion, Escribiente())
    assert "80 × 24 mm" in texto
    assert "contrato" in texto
