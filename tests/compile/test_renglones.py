"""Un cartucho por renglón, todos a la misma escala y con los mismos calajes."""

from __future__ import annotations

import json

import numpy as np
import pytest

from compile.escribiente import Escribiente, compilar, encajar_en_la_caja
from compile.renglones import compilar_por_renglones, comprobar, leer_pedido
from core.escritura import Escritura, Trazo
from core.units import mm

pytestmark = pytest.mark.core


def trazo(*puntos: tuple[float, float]) -> Trazo:
    return Trazo(puntos=[(mm(x), mm(y)) for x, y in puntos])


def dos_renglones() -> Escritura:
    """Arriba una onda corta; abajo una más larga. Si cada renglón se
    encajara por su cuenta, la corta saldría estirada hasta el ancho de la
    caja."""
    arriba = [(x, 20.0 + 3.0 * np.sin(x / 4.0)) for x in np.linspace(0.0, 40.0, 30)]
    abajo = [(x, 3.0 * np.sin(x / 5.0)) for x in np.linspace(0.0, 60.0, 40)]
    return Escritura(nombre="dos", trazos=[trazo(*arriba), trazo(*abajo)])


def caja(puntos: list[tuple[float, float]]) -> np.ndarray:
    p = np.array([[float(x), float(y)] for x, y in puntos])
    return np.concatenate([p.min(0), p.max(0)])


def test_los_renglones_reparten_los_trazos():
    comprobar(((0, 1), (2,)), 3)
    for malo in (((0,), (2,)), ((0, 1), (1, 2)), ((0, 1, 2), ()), ((0, 1, 2, 3),)):
        with pytest.raises(ValueError, match=r"renglón|reparten"):
            comprobar(malo, 3)


def test_todos_los_cartuchos_llevan_los_mismos_calajes():
    """Los calajes son de la máquina —contrato congelado—: los brazos se
    calan una vez y valen para todos los renglones."""
    e = dos_renglones()
    una = compilar(e)
    cartuchos = compilar_por_renglones(e, ((0,), (1,)))
    assert len(cartuchos) == 2
    for c in cartuchos:
        assert c.calajes == una.calajes


def test_cada_renglon_cae_donde_lo_pone_la_composicion_entera():
    """Mismo sitio y misma escala que en la frase entera: el renglón corto no
    se estira, y el de arriba queda arriba."""
    e = dos_renglones()
    maquina = Escribiente()
    colocada = encajar_en_la_caja(e, maquina)
    cartuchos = compilar_por_renglones(e, ((0,), (1,)), maquina)
    for indice, c in enumerate(cartuchos):
        esperada = caja(colocada.trazos[indice].puntos)
        obtenida = caja(c.escritura.trazos[0].puntos)
        assert np.allclose(obtenida, esperada, atol=mm(0.2))
    arriba = caja(cartuchos[0].escritura.trazos[0].puntos)
    abajo = caja(cartuchos[1].escritura.trazos[0].puntos)
    assert arriba[1] > abajo[3]
    assert arriba[2] - arriba[0] < 0.8 * float(maquina.caja_ancho)


def test_cada_cartucho_tiene_su_veredicto_y_su_nombre():
    cartuchos = compilar_por_renglones(dos_renglones(), ((0,), (1,)))
    assert [c.escritura.nombre for c in cartuchos] == ["dos_1", "dos_2"]
    for c in cartuchos:
        assert c.veredicto.apto, [i.codigo for i in c.veredicto.errores]
        assert len(c.piezas) == 3


def test_el_pedido_lee_sus_renglones(tmp_path):
    ruta = tmp_path / "p.json"
    trazos = [[[0, 0], [10, 0]], [[0, 5], [10, 5]]]
    ruta.write_text(json.dumps({"nombre": "p", "trazos": trazos, "renglones": [[1], [0]]}))
    pedido = leer_pedido(ruta)
    assert pedido.renglones == ((1,), (0,))
    ruta.write_text(json.dumps({"nombre": "p", "trazos": trazos}))
    assert leer_pedido(ruta).renglones is None
    ruta.write_text(json.dumps({"nombre": "p", "trazos": trazos, "renglones": [[0]]}))
    with pytest.raises(ValueError, match="reparten"):
        leer_pedido(ruta)
