"""El camino corto: el veredicto sin recorrer las levas.

`compilar(..., simular_el_trazo=False)` para justo antes de la simulación y
devuelve lo que se sabe hasta ahí. Medido con «Gracias»: lo que va delante
tarda medio segundo y la simulación cuarenta y cinco, así que ese corte es lo
que permite contestar «¿cabe?» mientras se teclea.

Lo que hay que defender no es la velocidad —eso se mide, no se afirma— sino
que **las dos salidas no puedan contradecirse**. Una vista previa que diga
que cabe algo que luego no cabe es peor que no tener vista previa: se deja de
mirar a la segunda vez.
"""

from __future__ import annotations

import pytest

from compile.escribiente import compilar
from core.units import TAU
from tests.casos import CASOS

pytestmark = pytest.mark.core

FALTA_MEDIR = "falta_medir_el_trazo"
"""La única incidencia que existe en el camino corto y no en el largo: el
largo, en su lugar, trae el número medido."""


def _codigos(veredicto) -> set[str]:
    return {i.codigo for i in veredicto.incidencias}


# ---------------------------------------------------------------------------
# La forma de lo que devuelve
# ---------------------------------------------------------------------------


def test_el_camino_corto_no_simula_ni_dibuja_piezas():
    """Lo que se salta tiene que verse: `None` es una respuesta, cero no.

    Si devolviera una `Simulacion` vacía, quien la leyera creería que el
    error de trazo es cero y lo enseñaría como tal.
    """
    corta = compilar(CASOS["hola"](), simular_el_trazo=False)
    assert corta.simulacion is None
    assert corta.piezas == []
    assert set(corta.perfiles) == {"izquierdo", "derecho", "elevador"}
    assert "error_trazo_maximo" not in corta.veredicto.metricas


@pytest.mark.parametrize("nombre", sorted(CASOS))
def test_el_reparto_suma_una_vuelta_exacta(nombre):
    """El medidor enseña los 360° partidos en tinta y vuelo, así que tienen
    que sumar la vuelta: si no, la barra miente sobre lo que queda."""
    corta = compilar(CASOS[nombre](), simular_el_trazo=False)
    total = sum(float(t.arco) for t in corta.tramos)
    assert total == pytest.approx(TAU, rel=1e-12)


@pytest.mark.parametrize("nombre", sorted(CASOS))
def test_hay_tantos_vuelos_como_trazos(nombre):
    """Un vuelo por trazo, incluido el de regreso al principio: la vuelta
    cierra. Sin esto el reparto tendría un hueco sin asignar."""
    corta = compilar(CASOS[nombre](), simular_el_trazo=False)
    trazos = [t for t in corta.tramos if t.clase == "trazo"]
    vuelos = [t for t in corta.tramos if t.clase == "vuelo"]
    assert len(trazos) == len(vuelos) == len(CASOS[nombre]().trazos)


# ---------------------------------------------------------------------------
# Lo que de verdad importa: que no se contradigan
# ---------------------------------------------------------------------------


@pytest.mark.slow
@pytest.mark.parametrize("nombre", sorted(CASOS))
def test_la_vista_previa_no_dice_nada_que_el_pedido_desmienta(nombre):
    """Contra los **cuatro** casos de referencia, no contra el que se tenga
    abierto: cada uno tensa una cosa distinta y uno de ellos no cabe.

    Es el cruce de siempre —dos salidas que describen lo mismo desde sitios
    distintos— y aquí tiene una dirección: el camino corto es un prefijo del
    largo, así que cada incidencia suya tiene que estar también en el otro.
    """
    escritura = CASOS[nombre]()
    corta = compilar(escritura, simular_el_trazo=False)
    larga = compilar(escritura)

    assert _codigos(corta.veredicto) - {FALTA_MEDIR} <= _codigos(larga.veredicto)
    if not corta.veredicto.apto:
        assert not larga.veredicto.apto, "la vista previa rechaza algo que el pedido acepta"
    assert corta.tramos == larga.tramos
    assert corta.calajes == larga.calajes


@pytest.mark.slow
@pytest.mark.parametrize("nombre", sorted(CASOS))
def test_falta_medir_aparece_justo_cuando_el_pedido_tiene_que_medir(nombre):
    """El aviso no es decorativo: marca los casos en los que el camino corto
    **no puede** dar la respuesta.

    Una leva recortada escribe la letra redondeada, y si eso se admite o no
    lo decide un número que solo sale de recorrerla. En el camino largo ese
    mismo caso acaba en `socavado_tolerable` —cabe— o en
    `perfil_autointersecado` —no cabe—, y desde el corto son el mismo estado:
    «falta medir».
    """
    escritura = CASOS[nombre]()
    corta = compilar(escritura, simular_el_trazo=False)
    larga = compilar(escritura)

    falta = FALTA_MEDIR in _codigos(corta.veredicto)
    decide = {"socavado_tolerable", "perfil_autointersecado"} & _codigos(larga.veredicto)
    assert falta == bool(decide), (
        f"{nombre}: la vista previa dice falta_medir={falta} y el pedido resuelve con {decide}"
    )
