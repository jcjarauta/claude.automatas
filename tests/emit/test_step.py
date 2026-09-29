"""STEP: el sólido 3-D y el contraste contra el cálculo barato.

El valor de estos tests no es comprobar que build123d funciona —eso es cosa
suya— sino **contrastar dos caminos independientes**: la masa que mide el
kernel a partir del sólido y la que sale de integrar el polígono en
`core/solido.py`. Si coinciden, las fórmulas de Green están bien puestas; y
si un día dejan de coincidir, uno de los dos ha cambiado sin avisar.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from compile.conjunto import montar
from compile.escribiente import Escribiente, compilar
from core.escritura import Escritura, Trazo
from core.solido import densidad_de
from core.units import a_mm, mm
from emit.step import (
    MARCA_PROFUNDIDAD,
    cartucho,
    disponible,
    escribir_step,
    masa_del_solido,
    solido_de_pieza,
)
from tests.emit.piezas_de_prueba import juego_pequeno, leva

pytestmark = [
    pytest.mark.core,
    pytest.mark.skipif(
        not disponible(),
        reason="build123d es opcional por su tamaño: uv sync --group cad",
    ),
]


def trazo(*puntos: tuple[float, float]) -> Trazo:
    return Trazo(puntos=[(mm(x), mm(y)) for x, y in puntos])


def hola() -> Escritura:
    return Escritura(
        nombre="hola",
        trazos=[
            trazo((0.0, 0.0), (0.0, 20.0)),
            trazo((0.0, 10.0), (8.0, 10.0), (8.0, 0.0)),
            trazo((14.0, 0.0), (14.0, 12.0), (20.0, 12.0), (20.0, 0.0), (14.0, 0.0)),
            trazo((26.0, 0.0), (26.0, 20.0)),
        ],
    )


# ---------------------------------------------------------------------------
# El contraste que justifica todo lo demás
# ---------------------------------------------------------------------------


@pytest.mark.slow
def test_el_kernel_y_el_poligono_pesan_lo_mismo():
    """Dos caminos que no comparten una sola línea de código: el kernel mide
    el volumen del sólido y `core/solido.py` integra el polígono."""
    maquina = Escribiente()
    compilacion = compilar(hola(), maquina)
    montaje, _ = montar(compilacion, maquina)

    del_kernel = masa_del_solido(cartucho(compilacion.piezas), densidad_de(maquina.material_leva))
    assert del_kernel == pytest.approx(float(montaje.masa), rel=1e-3)


def test_una_pieza_suelta_tambien_cuadra():
    pieza = leva()
    solido = solido_de_pieza(pieza)
    volumen = float(solido.volume) * 1e-9
    from core.solido import area, descontar_taladro

    superficie, _ = descontar_taladro(
        pieza.contorno, pieza.taladros[0].centro, pieza.taladros[0].diametro
    )
    esperado = (area(pieza.contorno) - superficie) * float(pieza.espesor)
    # El avellanado de la fase quita un poco más, así que el sólido pesa menos.
    assert volumen < esperado
    assert volumen == pytest.approx(esperado, rel=0.01)


# ---------------------------------------------------------------------------
# La geometría
# ---------------------------------------------------------------------------


def test_el_solido_tiene_el_espesor_de_la_pieza():
    pieza = leva()
    caja = solido_de_pieza(pieza).bounding_box()
    alto = float(caja.max.Z) - float(caja.min.Z)
    assert alto == pytest.approx(a_mm(pieza.espesor))


def test_el_solido_mide_lo_que_mide_la_pieza():
    pieza = leva()
    caja = solido_de_pieza(pieza).bounding_box()
    xs = [a_mm(x) for x, _ in pieza.contorno]
    ys = [a_mm(y) for _, y in pieza.contorno]
    ancho = float(caja.max.X) - float(caja.min.X)
    alto = float(caja.max.Y) - float(caja.min.Y)
    assert ancho == pytest.approx(max(xs) - min(xs), abs=1e-6)
    assert alto == pytest.approx(max(ys) - min(ys), abs=1e-6)


def test_el_taladro_atraviesa():
    """Si no atravesara, el eje no entraría y nadie lo vería hasta el montaje."""
    solido = solido_de_pieza(leva())
    caras = len(solido.faces())
    sin_taladro = solido_de_pieza(leva(taladros=[]))
    assert caras > len(sin_taladro.faces())


def test_la_marca_de_fase_se_rebaja_y_no_atraviesa():
    pieza = leva()
    con = solido_de_pieza(pieza).volume
    sin = solido_de_pieza(leva(marca_fase=None)).volume
    quitado = sin - con
    assert quitado > 0.0
    assert quitado < a_mm(pieza.espesor) * 20.0
    assert a_mm(pieza.espesor) > MARCA_PROFUNDIDAD


def test_sin_marca_de_fase_no_se_rebaja_nada():
    assert solido_de_pieza(leva(marca_fase=None)).volume > solido_de_pieza(leva()).volume


# ---------------------------------------------------------------------------
# El cartucho apilado
# ---------------------------------------------------------------------------


def test_las_piezas_se_apilan_con_su_separacion():
    piezas = juego_pequeno()[:3]
    conjunto = cartucho(piezas, separacion=2.0)
    caja = conjunto.bounding_box()
    esperado = sum(a_mm(p.espesor) for p in piezas) + 2.0 * (len(piezas) - 1)
    alto = float(caja.max.Z) - float(caja.min.Z)
    assert alto == pytest.approx(esperado)


def test_el_cartucho_empieza_en_cero():
    base = float(cartucho(juego_pequeno()[:2]).bounding_box().min.Z)
    assert base == pytest.approx(0.0)


def test_sin_piezas_no_hay_cartucho():
    with pytest.raises(ValueError, match="no hay piezas"):
        cartucho([])


# ---------------------------------------------------------------------------
# El archivo
# ---------------------------------------------------------------------------


@pytest.mark.slow
def test_el_step_se_escribe_y_es_brep(tmp_path: Path):
    """B-rep y no malla: es lo que permite acotar y emparejar en un CAD. Un
    STEP de OCCT lo declara en su cabecera."""
    ruta = escribir_step(juego_pequeno()[:2], tmp_path / "sub" / "cartucho.step")
    assert ruta.exists()
    cabecera = ruta.read_text(encoding="utf-8", errors="ignore")[:2000]
    assert "ISO-10303-21" in cabecera
    assert "Open CASCADE" in cabecera


def test_sin_piezas_no_se_escribe_nada(tmp_path: Path):
    with pytest.raises(ValueError, match="no hay piezas"):
        escribir_step([], tmp_path / "vacio.step")
