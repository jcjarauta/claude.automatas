"""Maquetación 1:1: cuadro de calibración, colocación y troceado."""

from __future__ import annotations

import pytest

from core.units import a_mm
from emit.layout import (
    ALTO_CABECERA,
    LADO_CALIBRACION,
    MARGEN,
    SOLAPE,
    Formato,
    Lamina,
    Trazo,
    cabe_en_una_hoja,
    formato_minimo,
    maquetar,
)
from tests.emit.piezas_de_prueba import bastidor_grande, leva

pytestmark = pytest.mark.core


def cuadro(lamina: Lamina) -> Trazo:
    """El único cuadrilátero cerrado del cajetín es el de calibración."""
    candidatos = [
        t for t in lamina.trazos if t.tipo == "cajetin" and t.cerrado and len(t.puntos) == 4
    ]
    assert len(candidatos) == 1, f"se esperaba un cuadro de calibración, hay {len(candidatos)}"
    return candidatos[0]


def lado(trazo: Trazo) -> tuple[float, float]:
    xs = [p[0] for p in trazo.puntos]
    ys = [p[1] for p in trazo.puntos]
    return max(xs) - min(xs), max(ys) - min(ys)


# ---------------------------------------------------------------------------
# El cuadro de calibración
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("formato", list(Formato))
def test_el_cuadro_mide_cien_milimetros_exactos(formato: Formato):
    """Sin esto la plantilla es peligrosa: nadie sabría que la impresora ha
    escalado la página."""
    ancho, alto = lado(cuadro(maquetar(leva(), formato)[0]))
    assert ancho == LADO_CALIBRACION
    assert alto == LADO_CALIBRACION


def test_el_cuadro_es_cuadrado_y_no_una_regla():
    """Una regla solo delata el escalado en un eje, y hay impresoras que
    escalan distinto en x y en y."""
    ancho, alto = lado(cuadro(maquetar(leva())[0]))
    assert ancho == alto


def test_todas_las_hojas_llevan_su_cuadro():
    for lamina in maquetar(bastidor_grande(), Formato.A4):
        assert lado(cuadro(lamina)) == (LADO_CALIBRACION, LADO_CALIBRACION)


def test_el_cuadro_lleva_su_leyenda():
    textos = " ".join(t.texto for t in maquetar(leva())[0].textos)
    assert "100 mm" in textos
    assert "la impresión está escalada" in textos


def test_todas_las_hojas_avisan_de_no_ajustar_a_la_pagina():
    for lamina in maquetar(bastidor_grande(), Formato.A4):
        assert any("SIN AJUSTAR" in t.texto for t in lamina.textos)


def test_el_cuadro_cabe_dentro_de_la_pagina():
    for formato in Formato:
        lamina = maquetar(leva(), formato)[0]
        for punto in cuadro(lamina).puntos:
            assert 0.0 <= punto[0] <= lamina.ancho
            assert 0.0 <= punto[1] <= lamina.alto


# ---------------------------------------------------------------------------
# Metadatos en la hoja
# ---------------------------------------------------------------------------


def test_la_hoja_enseña_los_siete_metadatos():
    pieza = leva()
    textos = [t.texto for t in maquetar(pieza)[0].textos]
    for esperado in (
        pieza.nombre,
        pieza.numero,
        pieza.conjunto,
        pieza.material,
        f"{a_mm(pieza.espesor):.1f} mm",
        str(pieza.cantidad),
        pieza.veta.value,
    ):
        assert any(esperado in t for t in textos), f"falta '{esperado}' en la hoja"


# ---------------------------------------------------------------------------
# Colocación
# ---------------------------------------------------------------------------


def test_la_pieza_no_invade_la_cabecera():
    """Si el dibujo se mete bajo el cuadro de calibración, no se puede medir."""
    lamina = maquetar(leva(), Formato.A4)[0]
    techo = lamina.alto - ALTO_CABECERA
    for trazo in lamina.trazos:
        if trazo.tipo in ("corte", "referencia"):
            for punto in trazo.puntos:
                assert punto[1] <= techo + 1e-9


def test_la_pieza_cabe_dentro_de_los_margenes():
    lamina = maquetar(leva(), Formato.A4)[0]
    for trazo in lamina.trazos:
        if trazo.tipo == "corte":
            for x, y in trazo.puntos:
                assert MARGEN - 1e-9 <= x <= lamina.ancho - MARGEN + 1e-9
                assert MARGEN - 1e-9 <= y <= lamina.alto - ALTO_CABECERA - MARGEN + 1e-9


def test_la_geometria_conserva_su_tamaño_real():
    """La escala es 1:1 y no una aproximación: la pieza en la hoja mide lo que
    mide la pieza."""
    pieza = leva()
    lamina = maquetar(pieza, Formato.A3)[0]
    corte = next(t for t in lamina.trazos if t.tipo == "corte")
    ancho, alto = lado(corte)
    # El contorno de corte no incluye taladros ni referencias, así que se
    # compara contra el propio contorno.
    xs = [a_mm(p[0]) for p in pieza.contorno]
    ys = [a_mm(p[1]) for p in pieza.contorno]
    assert ancho == pytest.approx(max(xs) - min(xs), abs=1e-9)
    assert alto == pytest.approx(max(ys) - min(ys), abs=1e-9)


def test_la_marca_de_fase_se_dibuja_y_se_rotula():
    lamina = maquetar(leva())[0]
    assert any("FASE 0" in t.texto for t in lamina.textos)


def test_sin_marca_de_fase_no_se_rotula():
    lamina = maquetar(leva(marca_fase=None))[0]
    assert not any("FASE 0" in t.texto for t in lamina.textos)


def test_los_taladros_llevan_su_diametro_escrito():
    lamina = maquetar(leva())[0]
    assert any("Ø8.0" in t.texto for t in lamina.textos)


# ---------------------------------------------------------------------------
# Troceado
# ---------------------------------------------------------------------------


def test_una_pieza_pequeña_no_se_trocea():
    assert len(maquetar(leva(), Formato.A3)) == 1


def test_una_pieza_grande_se_trocea():
    laminas = maquetar(bastidor_grande(), Formato.A4)
    assert len(laminas) > 1


def test_las_teselas_van_numeradas_y_dicen_cuantas_son():
    laminas = maquetar(bastidor_grande(), Formato.A4)
    total = len(laminas)
    assert [lamina.indice for lamina in laminas] == [(i + 1, total) for i in range(total)]
    assert any(f"hoja 1 de {total}" in t.texto for t in laminas[0].textos)


def test_las_teselas_contiguas_solapan_lo_declarado():
    """El solape es lo que permite pegarlas: si no coincide, la pieza sale
    con un escalón."""
    pieza = bastidor_grande()
    formato = Formato.A4
    laminas = maquetar(pieza, formato)
    util_ancho = formato.medidas[0] - 2 * MARGEN

    primera = next(t for t in laminas[0].trazos if t.tipo == "corte")
    segunda = next(t for t in laminas[1].trazos if t.tipo == "corte")
    desplazamiento = primera.puntos[0][0] - segunda.puntos[0][0]
    assert desplazamiento == pytest.approx(util_ancho - SOLAPE, abs=1e-9)


def test_las_marcas_de_registro_estan_en_las_mismas_coordenadas_en_toda_tesela():
    """Dos hojas contiguas se alinean por ellas, así que tienen que coincidir."""
    laminas = maquetar(bastidor_grande(), Formato.A4)
    referencia = centros_de_marca(laminas[0])
    assert len(referencia) >= 4
    for lamina in laminas[1:]:
        assert centros_de_marca(lamina) >= referencia


def centros_de_marca(lamina: Lamina) -> set[tuple[float, float]]:
    puntos: set[tuple[float, float]] = set()
    for trazo in lamina.trazos:
        if trazo.tipo == "marca" and len(trazo.puntos) == 2:
            (x0, y0), (x1, y1) = trazo.puntos
            puntos.add((round((x0 + x1) / 2, 9), round((y0 + y1) / 2, 9)))
    return puntos


def esquinas_de(lamina: Lamina) -> set[tuple[float, float]]:
    arriba = lamina.alto - ALTO_CABECERA - MARGEN
    return {(x, y) for x in (MARGEN, lamina.ancho - MARGEN) for y in (MARGEN, arriba)}


def test_sin_trocear_no_hay_marcas_de_registro_en_las_esquinas():
    """En una hoja suelta no hay nada que alinear; solo estorbarían. La marca
    de fase usa el mismo trazo, así que se distinguen por posición."""
    lamina = maquetar(leva(), Formato.A3)[0]
    assert not (centros_de_marca(lamina) & esquinas_de(lamina))


def test_al_trocear_si_las_hay_en_las_cuatro_esquinas():
    lamina = maquetar(bastidor_grande(), Formato.A4)[0]
    assert esquinas_de(lamina) <= centros_de_marca(lamina)


# ---------------------------------------------------------------------------
# Hoja única para plóter
# ---------------------------------------------------------------------------


def test_en_hoja_unica_la_pagina_crece_hasta_que_cabe():
    laminas = maquetar(bastidor_grande(), Formato.A4, hoja_unica=True)
    assert len(laminas) == 1
    lamina = laminas[0]
    pieza = bastidor_grande()
    assert lamina.ancho >= a_mm(pieza.ancho) + 2 * MARGEN
    assert lamina.alto >= a_mm(pieza.alto) + ALTO_CABECERA + 2 * MARGEN


def test_en_hoja_unica_el_cuadro_sigue_midiendo_cien():
    lamina = maquetar(bastidor_grande(), Formato.A4, hoja_unica=True)[0]
    assert lado(cuadro(lamina)) == (LADO_CALIBRACION, LADO_CALIBRACION)


# ---------------------------------------------------------------------------
# Elección de formato
# ---------------------------------------------------------------------------


def test_el_formato_minimo_es_el_mas_pequeño_donde_cabe():
    formato = formato_minimo(leva())
    assert formato is Formato.A4
    assert cabe_en_una_hoja(leva(), Formato.A4)


def test_el_bastidor_no_cabe_en_a4_ni_en_a3():
    pieza = bastidor_grande()
    assert not cabe_en_una_hoja(pieza, Formato.A4)
    assert not cabe_en_una_hoja(pieza, Formato.A3)
    assert formato_minimo(pieza) is Formato.A1


def test_los_formatos_tienen_las_medidas_de_la_norma():
    assert Formato.A4.medidas == (210.0, 297.0)
    assert Formato.A0.medidas == (841.0, 1189.0)
    for grande, pequeno in ((Formato.A0, Formato.A1), (Formato.A3, Formato.A4)):
        assert grande.medidas[0] > pequeno.medidas[0]


def test_la_cabecera_deja_sitio_al_cuadro():
    """Requisito estructural: si la cabecera encogiera por debajo del cuadro,
    dejaría de caber sin que nadie se diera cuenta."""
    assert ALTO_CABECERA >= LADO_CALIBRACION + 2 * MARGEN - 2.0
