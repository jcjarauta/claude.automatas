"""La explosión, declarada y medida.

Nada se coloca a ojo: cada grupo declara hacia dónde se monta y cuánto se
separan sus piezas (`emit.explosion.EXPLOSIONES`), y la distancia de cada
bloque en la explosión de la máquina se deriva. Aquí se miden las cajas de
lo que se dibuja: los bloques no se solapan, y los globos ni se pisan entre
ellos ni tapan ninguna pieza.
"""

from __future__ import annotations

import itertools

import pytest

from emit.explosion import EXPLOSIONES, Globo, ancla_de, colocar_globos, solapan
from emit.montaje import GRUPOS


def _sin_pisarse(globos: list[Globo], cajas: dict[str, tuple[float, float, float, float]]):
    pisados = [
        (a.clave, b.clave)
        for a, b in itertools.combinations(globos, 2)
        if solapan(a.caja(), b.caja())
    ]
    tapados = [(g.clave, n) for g in globos for n, c in cajas.items() if solapan(g.caja(), c)]
    return pisados, tapados


def test_todo_grupo_declara_su_explosion():
    assert set(EXPLOSIONES) == {g.nombre for g in GRUPOS}
    assert EXPLOSIONES["bastidor"].eje_conjunto == (0.0, 0.0, 0.0), "la base no se mueve"
    assert all(e.separacion > 0 for e in EXPLOSIONES.values())


def test_los_globos_van_fuera_y_no_se_pisan_aunque_sus_piezas_esten_juntas():
    anclas = [(str(k), (50.0, 50.0 + 0.1 * k)) for k in range(6)]
    globos = colocar_globos(anclas, 0.0, 100.0, 3.0)
    pisados, tapados = _sin_pisarse(globos, {"pieza": (0.0, 0.0, 100.0, 100.0)})
    assert not pisados
    assert not tapados


def test_el_ancla_cae_sobre_la_pieza_y_no_en_su_hueco():
    aro = [[(0.0, 0.0), (10.0, 0.0), (10.0, 10.0), (0.0, 10.0), (0.0, 0.0)]]
    x, y = ancla_de(aro)
    assert (x, y) in aro[0]


@pytest.fixture(scope="module")
def maquina():
    pytest.importorskip("build123d", reason="hace falta el kernel: uv sync --group cad")
    from scripts.dossier import datos

    return datos("commit prueba").piezas


@pytest.mark.slow
def test_la_explosion_de_conjunto_no_solapa_bloques_ni_tapa_con_globos(maquina):
    from emit.explosion import esquema_de_conjunto

    e = esquema_de_conjunto(maquina)
    assert set(e.cajas) == set(e.distancias) == {g.clave for g in e.globos}
    solapados = [
        (a, b) for (a, ca), (b, cb) in itertools.combinations(e.cajas.items(), 2) if solapan(ca, cb)
    ]
    assert not solapados
    pisados, tapados = _sin_pisarse(e.globos, e.cajas)
    assert not pisados
    assert not tapados


@pytest.mark.slow
def test_la_distancia_de_cada_bloque_es_la_justa(maquina):
    """Derivada, no puesta: un paso menos y el bloque tocaría a otro."""
    from emit.explosion import explosionar_conjunto

    _, distancias = explosionar_conjunto(maquina)
    assert distancias["bastidor"] == 0
    assert all(d >= 0 for d in distancias.values())
    assert list(distancias) == [g for g in EXPLOSIONES if g in distancias]


@pytest.fixture(scope="module", params=["amplificador", "cinco_barras", "portalapiz"])
def grupo(request):
    pytest.importorskip("build123d", reason="hace falta el kernel: uv sync --group cad")
    from scripts.fichas import preparar

    return preparar(request.param)


@pytest.mark.slow
def test_cada_pieza_del_despiece_sube_su_rango_por_la_separacion(grupo):
    """El orden del despiece es el de las marcas: el de montaje."""
    from emit.explosion import _unitario
    from emit.fichas import base_de

    e = EXPLOSIONES[grupo.grupo.nombre]
    eje = _unitario(e.eje)
    marcas = sorted({m for m, _, _ in grupo.despiece})
    colocadas = dict(grupo.contexto)
    fichadas = {p.nombre for p in grupo.piezas}
    for marca, nombre, solido in grupo.despiece:
        assert base_de(nombre) in fichadas
        paso = marcas.index(marca) * e.separacion
        antes, despues = colocadas[nombre].bounding_box().min, solido.bounding_box().min
        movido = (despues.X - antes.X, despues.Y - antes.Y, despues.Z - antes.Z)
        assert movido == pytest.approx(tuple(paso * x for x in eje), abs=1e-6), nombre


@pytest.mark.slow
def test_los_globos_del_despiece_no_se_pisan_ni_tapan_piezas(grupo):
    from emit.fichas import DESPIECE, despiece_en_hoja

    e = despiece_en_hoja(grupo)
    assert {g.clave for g in e.globos} == {str(p.marca) for p in grupo.piezas}
    pisados, tapados = _sin_pisarse(e.globos, e.cajas)
    assert not pisados
    assert not tapados
    x, _, w, _ = DESPIECE
    for g in e.globos:
        gx0, _, gx1, _ = g.caja()
        assert x <= gx0, f"el globo {g.clave} se sale del despiece"
        assert gx1 <= x + w, f"el globo {g.clave} se sale del despiece"
