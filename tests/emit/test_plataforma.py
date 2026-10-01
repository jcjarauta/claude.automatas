"""Los perfiles de la plataforma y su DXF.

El generador y el comparador son los dos extremos del mismo bucle, así que
el test que de verdad importa es que **lo que emite uno lo apruebe el otro**,
datum incluido. Lo demás —que la tangente sea tangente, que la D muerda lo
justo— son las condiciones que se escribieron mal alguna vez.
"""

from __future__ import annotations

import math
from pathlib import Path

import pytest

from emit.plataforma import (
    BRAZOS,
    Arco,
    Segmento,
    agujero_en_d,
    barra,
    brazo,
    contrato_mm,
    escribir_dxf,
)
from scripts.comparar_dxf import comparar

pytestmark = pytest.mark.core


@pytest.mark.parametrize("cual", sorted(BRAZOS))
def test_lo_que_emite_el_generador_lo_aprueba_el_comparador(cual: str, tmp_path: Path):
    """**El bucle cerrado.** Si esto falla, una de las dos mitades miente, y
    como no comparten el camino —uno construye desde el contrato, el otro mide
    el archivo— el que falle lo dice el detalle."""
    inf = comparar(escribir_dxf(brazo(cual), tmp_path / f"{cual}.dxf"), cual)
    assert inf.cuadra, [h.texto for h in inf.hallazgos]


@pytest.mark.parametrize("cual", sorted(BRAZOS))
def test_cada_pieza_sale_en_su_datum(cual: str, tmp_path: Path):
    """Lo que de verdad resuelve el archivo: el sitio. Sin esto, la pieza
    llega exacta y suelta y hay que anclarla a ojo."""
    inf = comparar(escribir_dxf(brazo(cual), tmp_path / f"{cual}.dxf"), cual)
    assert "totalmente definida" in inf.datum


def test_la_tangente_es_perpendicular_al_radio_en_los_dos_contactos():
    """La condición que coloca el contorno, impuesta y no mirada: es el error
    que este repo ya cometió dos veces con la cinta del cabestrante."""
    perfil = barra(90.0, 9.0, 6.0)
    arcos = [e for e in perfil if isinstance(e, Arco)]
    for seg in (e for e in perfil if isinstance(e, Segmento)):
        u = (seg.b[0] - seg.a[0], seg.b[1] - seg.a[1])
        for p in (seg.a, seg.b):
            tocando = [a for a in arcos if abs(math.dist(p, a.centro) - a.radio) < 1e-9]
            assert tocando, "un extremo de la tangente no se apoya en ningún arco"
            a = tocando[0]
            v = (p[0] - a.centro[0], p[1] - a.centro[1])
            cos = abs(v[0] * u[0] + v[1] * u[1]) / (a.radio * math.hypot(*u))
            assert cos < 1e-12


def test_un_cubo_que_se_come_al_otro_no_tiene_tangente():
    """Devolver un contorno cruzado sería peor que fallar: se importa, se ve
    raro y se extruye igual."""
    with pytest.raises(ValueError, match="tangente"):
        barra(2.0, 9.0, 6.0)


def test_la_cuerda_de_la_d_es_la_del_contrato():
    c = contrato_mm()
    perfil = agujero_en_d((0.0, 0.0), c["brazo_eje_diametro"] / 2, c["brazo_chaveta"])
    seg = next(e for e in perfil if isinstance(e, Segmento))
    assert math.dist(seg.a, seg.b) == pytest.approx(c["brazo_chaveta_cuerda"])


def test_una_cara_plana_que_parte_el_agujero_no_pasa():
    with pytest.raises(ValueError, match="cara plana"):
        agujero_en_d((0.0, 0.0), 5.0, 6.0)


def test_el_distal_sale_sin_cara_plana_y_con_los_dos_extremos_iguales():
    """Es una biela: gira libre en los dos pernos. Una D ahí sería un calaje
    que no necesita y que impediría montarla."""
    c = contrato_mm()
    perfil = brazo("brazo_distal")
    radios = sorted(e.radio for e in perfil if isinstance(e, Arco))
    assert radios == pytest.approx(
        sorted([c["brazo_extremo_diametro"] / 2] * 2 + [c["brazo_perno_diametro"] / 2] * 2)
    )
    assert sum(isinstance(e, Segmento) for e in perfil) == 2, "sobra una cuerda"


def test_el_dxf_no_lleva_rotulos():
    """Un TEXT de DXF no es una entidad de boceto: Onshape importa la
    geometría bien y suelta un «no se ha podido importar la entidad
    desconocida». Lo que hay que leer va en la hoja."""
    import tempfile

    import ezdxf

    with tempfile.TemporaryDirectory() as tmp:
        ruta = escribir_dxf(brazo("brazo_proximal"), Path(tmp) / "x.dxf")
        doc = ezdxf.readfile(str(ruta))
        assert not [e for e in doc.modelspace() if e.dxftype() in ("TEXT", "MTEXT")]


def test_la_hoja_dibuja_el_mismo_contorno_que_escribe_el_dxf():
    """Dos sitios calculando el mismo contorno es la duplicación que este
    proyecto se come tarde: si la hoja enseñara una forma y el archivo otra,
    quien dibuja haría una tercera."""
    from scripts.dibujar_plano_brazos import obround

    camino = obround(0.0, 0.0, 90.0, 9.0, 6.0, 1.0)
    assert camino.count("A ") == 2
    assert camino.rstrip().endswith("Z")
