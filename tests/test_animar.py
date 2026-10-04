"""La animación del escribiente: que el árbol del visor mueva las piezas
adonde las pone `colocar`, y que todo salga del perfil cortado."""

from __future__ import annotations

import math
from itertools import pairwise
from pathlib import Path

import numpy as np
import pytest

pytest.importorskip("build123d", reason="hace falta el kernel: uv sync --group cad")

RAIZ = Path(__file__).resolve().parents[1]
FOTOGRAMAS = 24


@pytest.fixture(scope="module")
def animacion():
    from scripts.animar import construir

    return construir(RAIZ / "demo" / "hola.json", FOTOGRAMAS)


def test_cada_pieza_animada_cae_donde_la_pone_colocar(animacion):
    """**La prueba de que la animación no miente.** En varios fotogramas, cada
    pieza recompuesta desde su nodo —con el giro o la traslación de su pista—
    tiene el centro de masas donde lo tiene la misma pieza en `colocar` para
    ese ángulo, calculado por el perfil cortado. Un signo cambiado, un pivote
    mal puesto o el distal mal anidado salen aquí."""
    from compile.conjunto import estados
    from compile.escribiente import SEGUIDORES, Escribiente, compilar
    from emit.montaje import colocar, taller
    from emit.plataforma import contrato_mm
    from scripts.animar import nodos_en
    from scripts.exportar_para_cad import leer

    raiz, _, _ = animacion
    c = contrato_mm()
    maquina = Escribiente()
    compilacion = compilar(leer(RAIZ / "demo" / "hola.json"), maquina)
    thetas = np.linspace(0.0, 2.0 * np.pi, FOTOGRAMAS, endpoint=False)
    todos = estados(compilacion, maquina, thetas, camino="contacto")
    seguidores = [maquina.seguidor(i) for i in range(len(SEGUIDORES))]
    hecho = taller(c)
    revisadas = 0
    for k in (5, 11, 17):
        reales = {
            p.nombre: p.solido
            for p in colocar(list(compilacion.piezas), seguidores, todos[k], c, hecho)
        }
        for nombre_nodo, (nodo, ubicacion) in nodos_en(raiz, k).items():
            if nodo.pista is None or nombre_nodo == "punta_del_lapiz":
                continue
            for nombre, local in nodo.piezas:
                if nombre.startswith("tinta"):
                    continue
                animada = (ubicacion * local).center()
                real = reales[nombre].center()
                d = math.dist((animada.X, animada.Y, animada.Z), (real.X, real.Y, real.Z))
                assert d < 0.02, f"{nombre} en el fotograma {k}: a {d:.3f} mm de colocar"
                revisadas += 1
    assert revisadas > 40


def test_hay_una_pista_por_parte_que_se_mueve_y_un_valor_por_fotograma(animacion):
    from scripts.animar import rutas

    raiz, tiempos, _ = animacion
    pistas = rutas(raiz)
    for esperado in (
        "/escribiente/arbol",
        "/escribiente/manivela",
        "/escribiente/balancin",
        "/escribiente/seguidor_1",
        "/escribiente/brazo_1/distal_1",
        "/escribiente/mesa",
        "/escribiente/punta_del_lapiz",
    ):
        assert esperado in pistas, esperado
    for ruta, (_, valores) in pistas.items():
        assert len(valores) == len(tiempos), ruta
    assert tiempos[0] == 0.0
    assert tiempos[-1] < 2.0  # una vuelta del árbol son 2 s a 90 rpm de manivela


def test_la_tinta_es_lo_que_escriben_las_levas_cortadas(animacion):
    """La tinta sobre la mesa sale del recorrido por contacto: tantos puntos
    de tinta como puntos apoyados tiene la vuelta, ni uno más."""
    raiz, _, recorridos = animacion
    (recorrido,) = recorridos
    mesa = next(h for h in raiz.hijos if h.nombre == "mesa")
    assert recorrido.camino.startswith("perfil cortado")
    escritos = set()
    for trozo in mesa.hijos:
        for _, linea in trozo.piezas:
            escritos |= {(round(v.X, 6), round(v.Y, 6)) for v in linea.vertices()}
    assert len(escritos) == int(recorrido.apoyado.sum())


def test_la_tinta_sale_cuando_la_punta_pasa_y_se_borra_al_volver(animacion):
    """La escritura «orgánica»: en el fotograma 0 el papel está en blanco, cada
    trozo sube al papel en el fotograma siguiente al suyo y no vuelve a bajar,
    y al acabar la vuelta está toda la frase."""
    from scripts.animar import HUNDIDO, construir

    raiz, tiempos, _ = animacion
    mesa = next(h for h in raiz.hijos if h.nombre == "mesa")
    assert mesa.hijos
    for trozo in mesa.hijos:
        k = int(trozo.nombre.rsplit("_", 1)[1])
        _, valores = trozo.pista
        assert valores[0] == -HUNDIDO
        assert all(v == -HUNDIDO for v in valores[: k + 1])
        assert all(v == 0.0 for v in valores[k + 1 :])
    con_reposo, tiempos_r, _ = construir(RAIZ / "demo" / "hola.json", FOTOGRAMAS, reposo=0.5)
    assert len(tiempos_r) == len(tiempos) + 1
    mesa_r = next(h for h in con_reposo.hijos if h.nombre == "mesa")
    assert all(t.pista[1][-1] == 0.0 for t in mesa_r.hijos)


FELIZ = RAIZ / "demo" / "feliz_cumpleanos.json"


@pytest.fixture(scope="module")
def dos_cartuchos():
    from scripts.animar import construir

    return construir(FELIZ, FOTOGRAMAS)


def _pista(raiz, nombre):
    from scripts.animar import rutas

    return next(v for r, v in rutas(raiz).items() if r.endswith("/" + nombre))


def test_con_renglones_se_anima_un_cartucho_por_vuelta(dos_cartuchos):
    """Dos vueltas y un cambio entre ellas: el fin de la primera y el momento
    en que el primer cartucho ya ha salido y el segundo aún no ha entrado."""
    raiz, tiempos, recorridos = dos_cartuchos
    assert len(recorridos) == 2
    assert len(tiempos) == 2 * FOTOGRAMAS + 2
    assert all(b > a for a, b in pairwise(tiempos))
    _, uno = _pista(raiz, "cartucho_1")
    _, dos = _pista(raiz, "cartucho_2")
    dentro = [0.0, 0.0, 0.0]
    escribe_el_segundo = FOTOGRAMAS + 2 + 5
    assert uno[5] == dentro
    assert dos[5] != dentro
    assert uno[FOTOGRAMAS + 1] != dentro
    assert dos[FOTOGRAMAS + 1] != dentro
    assert dos[escribe_el_segundo] == dentro
    assert uno[escribe_el_segundo] != dentro
    # El que espera fuera no gira; el que escribe gira con el árbol.
    _, giro_2 = _pista(raiz, "giro_2")
    _, arbol = _pista(raiz, "arbol")
    assert giro_2[5] == 360.0
    assert giro_2[escribe_el_segundo] == arbol[escribe_el_segundo]


def test_el_segundo_cartucho_cae_donde_lo_pone_colocar(dos_cartuchos):
    """Lo mismo que se pide a la animación de una vuelta, en la segunda: las
    levas del segundo cartucho donde las pone `colocar` con su compilación."""
    from compile.conjunto import estados
    from compile.escribiente import SEGUIDORES, Escribiente
    from compile.renglones import compilar_por_renglones, leer_pedido
    from emit.montaje import colocar, taller
    from emit.plataforma import contrato_mm
    from scripts.animar import nodos_en

    raiz, _, _ = dos_cartuchos
    c = contrato_mm()
    maquina = Escribiente()
    pedido = leer_pedido(FELIZ)
    segunda = compilar_por_renglones(pedido.escritura, pedido.renglones, maquina)[1]
    thetas = np.linspace(0.0, 2.0 * np.pi, FOTOGRAMAS, endpoint=False)
    todos = estados(segunda, maquina, thetas, camino="contacto")
    seguidores = [maquina.seguidor(i) for i in range(len(SEGUIDORES))]
    f = 7
    reales = {
        p.nombre: p.solido
        for p in colocar(list(segunda.piezas), seguidores, todos[f], c, taller(c))
    }
    nodo, ubicacion = nodos_en(raiz, FOTOGRAMAS + 2 + f)["giro_2"]
    levas = [(n, solido) for n, solido in nodo.piezas if n.startswith("leva_")]
    assert len(levas) == 3
    for nombre, local in levas:
        animada = (ubicacion * local).center()
        real = reales[nombre].center()
        d = math.dist((animada.X, animada.Y, animada.Z), (real.X, real.Y, real.Z))
        assert d < 0.02, f"{nombre}: a {d:.3f} mm de colocar"


def test_la_tinta_de_la_primera_vuelta_se_queda_en_la_segunda(dos_cartuchos):
    from scripts.animar import HUNDIDO

    raiz, _, _ = dos_cartuchos
    mesa = next(h for h in raiz.hijos if h.nombre == "mesa")
    primera = [t for t in mesa.hijos if t.nombre.startswith("tinta_1_")]
    segunda = [t for t in mesa.hijos if t.nombre.startswith("tinta_2_")]
    assert primera
    assert segunda
    for trozo in primera:
        _, valores = trozo.pista
        assert valores[0] == -HUNDIDO
        assert all(v == 0.0 for v in valores[FOTOGRAMAS:])
    for trozo in segunda:
        _, valores = trozo.pista
        assert all(v == -HUNDIDO for v in valores[: FOTOGRAMAS + 2])
