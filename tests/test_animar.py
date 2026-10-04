"""La animación del escribiente: que el árbol del visor mueva las piezas
adonde las pone `colocar`, y que todo salga del perfil cortado."""

from __future__ import annotations

import math
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
    """La tinta sobre la mesa sale del recorrido por contacto, y tiene tantos
    trazos como el pedido."""
    raiz, _, recorrido = animacion
    mesa = next(h for h in raiz.hijos if h.nombre == "mesa")
    tinta = [n for n, _ in mesa.piezas if n.startswith("tinta")]
    assert recorrido.camino.startswith("perfil cortado")
    assert len(tinta) == recorrido.tramos()[0]
