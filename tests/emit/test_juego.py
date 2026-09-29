"""Varias piezas en una hoja, elección de formato y separación de escalas.

Una hoja por pieza desperdicia papel y obliga a barajar treinta folios en el
taller. Agrupar solo vale si se puede demostrar que las piezas no se pisan, que
cada una sigue llevando sus metadatos y que nada se sale de la hoja.
"""

from __future__ import annotations

import pytest
from reportlab.pdfbase.pdfmetrics import stringWidth

from core.units import a_mm
from emit.layout import (
    ALTO_CABECERA,
    LADO_CALIBRACION,
    MARGEN,
    SEPARACION,
    Formato,
    Lamina,
    Trazo,
    formato_minimo_juego,
    maquetar,
    maquetar_juego,
)
from emit.template import PUNTOS_POR_MM, escribir_pdf
from tests.emit.piezas_de_prueba import bastidor_grande, juego_pequeno, leva, rectangular

pytestmark = pytest.mark.core


def cajas(lamina: Lamina) -> list[tuple[float, float, float, float]]:
    """Caja envolvente de cada contorno de corte de la hoja."""

    def caja(t: Trazo) -> tuple[float, float, float, float]:
        xs = [p[0] for p in t.puntos]
        ys = [p[1] for p in t.puntos]
        return min(xs), min(ys), max(xs), max(ys)

    return [caja(t) for t in lamina.trazos if t.tipo == "corte"]


def se_pisan(a: tuple[float, ...], b: tuple[float, ...]) -> bool:
    return a[0] < b[2] and b[0] < a[2] and a[1] < b[3] and b[1] < a[3]


def ancho_real(texto: str, tamano: float, negrita: bool) -> float:
    fuente = "Helvetica-Bold" if negrita else "Helvetica"
    return stringWidth(texto, fuente, tamano * PUNTOS_POR_MM) / PUNTOS_POR_MM


# ---------------------------------------------------------------------------
# Agrupar
# ---------------------------------------------------------------------------


def test_las_piezas_pequeñas_comparten_hoja():
    """Cinco piezas chicas que antes eran cinco documentos."""
    laminas = maquetar_juego(juego_pequeno(), Formato.A4)
    assert len(laminas) == 1
    assert len(cajas(laminas[0])) == 5


def test_las_piezas_no_se_pisan():
    for lamina in maquetar_juego(juego_pequeno(), Formato.A4):
        contornos = cajas(lamina)
        for i, a in enumerate(contornos):
            for b in contornos[i + 1 :]:
                assert not se_pisan(a, b)


def test_entre_dos_piezas_cabe_la_sierra():
    """Dos contornos pegados obligan a cortar dos veces por el mismo sitio."""
    contornos = cajas(maquetar_juego(juego_pequeno(), Formato.A4)[0])
    for i, a in enumerate(contornos):
        for b in contornos[i + 1 :]:
            separadas_en_x = a[2] + SEPARACION <= b[0] + 1e-9 or b[2] + SEPARACION <= a[0] + 1e-9
            separadas_en_y = a[3] + SEPARACION <= b[1] + 1e-9 or b[3] + SEPARACION <= a[1] + 1e-9
            assert separadas_en_x or separadas_en_y


def test_cada_pieza_lleva_sus_metadatos_al_lado():
    """El conjunto va en la cabecera porque es común; los otros seis viajan
    con su pieza. En una hoja con cinco contornos, saber cuál es de 5 mm y
    cuál de 9 es lo que evita cortarlo del tablero equivocado."""
    piezas = juego_pequeno()
    textos = " ".join(t.texto for t in maquetar_juego(piezas, Formato.A4)[0].textos)
    assert piezas[0].conjunto in textos
    for pieza in piezas:
        assert pieza.numero in textos
        assert pieza.nombre in textos
        assert f"{a_mm(pieza.espesor):.1f} mm" in textos
        assert f"×{pieza.cantidad}" in textos
        assert pieza.veta.value in textos
        assert pieza.material.split()[0] in textos


def test_la_hoja_agrupada_lleva_su_cuadro_y_su_advertencia():
    lamina = maquetar_juego(juego_pequeno(), Formato.A4)[0]
    cuadrados = [
        t for t in lamina.trazos if t.tipo == "cajetin" and t.cerrado and len(t.puntos) == 4
    ]
    assert len(cuadrados) == 1
    xs = [p[0] for p in cuadrados[0].puntos]
    assert max(xs) - min(xs) == LADO_CALIBRACION
    assert any("SIN AJUSTAR" in t.texto for t in lamina.textos)


def test_nada_invade_la_cabecera_ni_los_margenes():
    for lamina in maquetar_juego(juego_pequeno(), Formato.A4):
        techo = lamina.alto - ALTO_CABECERA
        for trazo in lamina.trazos:
            if trazo.tipo == "corte":
                for x, y in trazo.puntos:
                    assert MARGEN - 1e-9 <= x <= lamina.ancho - MARGEN + 1e-9
                    assert MARGEN - 1e-9 <= y <= techo + 1e-9


def test_ningun_rotulo_se_sale_de_la_hoja_agrupada():
    """El rótulo de una pieza puede ser más ancho que la pieza. Se recorta
    antes de salirse: un rótulo cortado por el borde no dice nada."""
    piezas = [
        *juego_pequeno(),
        rectangular(
            "pieza con un nombre larguísimo que no cabe de ninguna manera",
            "X-999",
            40.0,
            20.0,
            material="contrachapado marino de okoumé de nueve milímetros",
        ),
    ]
    for formato in (Formato.A4, Formato.A3):
        for lamina in maquetar_juego(piezas, formato):
            for texto in lamina.textos:
                ancho = ancho_real(texto.texto, texto.tamano, texto.negrita)
                izquierda = texto.x - (ancho / 2 if texto.anclaje == "centro" else 0.0)
                assert izquierda >= -0.5, f"'{texto.texto}' se sale por la izquierda"
                assert izquierda + ancho <= lamina.ancho + 0.5, f"'{texto.texto}' se sale"


def test_muchas_piezas_pasan_a_la_hoja_siguiente_y_van_numeradas():
    piezas = [rectangular(f"tapa {i}", f"T-{i:03d}", 90.0, 60.0) for i in range(12)]
    laminas = maquetar_juego(piezas, Formato.A4)
    total = len(laminas)
    assert total > 1
    assert [lamina.indice for lamina in laminas] == [(i + 1, total) for i in range(total)]
    assert sum(len(cajas(lamina)) for lamina in laminas) == 12


def test_una_pieza_grande_se_trocea_aparte_con_su_cabecera_entera():
    """No se agrupa lo que no cabe: se trocea, y entonces la hoja habla de
    una sola pieza y puede volver a llevar los siete metadatos."""
    laminas = maquetar_juego([*juego_pequeno(), bastidor_grande()], Formato.A4)
    propias = len(maquetar(bastidor_grande(), Formato.A4))
    assert len(laminas) == 1 + propias
    assert any("bastidor" in t.texto for t in laminas[-1].textos)


def test_una_sola_pieza_tambien_vale():
    assert len(maquetar_juego([leva()], Formato.A4)) == 1


def test_un_juego_vacio_no_se_maqueta():
    with pytest.raises(ValueError, match="no hay piezas"):
        maquetar_juego([])


def test_piezas_de_conjuntos_distintos_se_declaran_como_tales():
    piezas = [
        rectangular("a", "A-1", 40.0, 30.0, conjunto="escribiente"),
        rectangular("b", "B-1", 40.0, 30.0, conjunto="cartucho hola"),
    ]
    textos = " ".join(t.texto for t in maquetar_juego(piezas, Formato.A4)[0].textos)
    assert "2 conjuntos" in textos


# ---------------------------------------------------------------------------
# Formato por trabajo
# ---------------------------------------------------------------------------


def test_el_formato_minimo_del_juego_lo_manda_la_pieza_mayor():
    assert formato_minimo_juego(juego_pequeno()) is Formato.A4
    assert formato_minimo_juego([*juego_pequeno(), bastidor_grande()]) is Formato.A1


def test_si_ninguna_hoja_admite_todo_no_hay_formato_minimo():
    enorme = rectangular("tablero", "Z-1", 1500.0, 1500.0)
    assert formato_minimo_juego([enorme]) is None


@pytest.mark.parametrize("formato", list(Formato))
def test_el_juego_se_maqueta_en_cualquier_formato(formato: Formato):
    laminas = maquetar_juego(juego_pequeno(), formato)
    assert all(lamina.ancho == formato.medidas[0] for lamina in laminas)
    assert sum(len(cajas(lamina)) for lamina in laminas) == 5


def test_una_hoja_mayor_gasta_menos_hojas():
    piezas = [rectangular(f"tapa {i}", f"T-{i:03d}", 90.0, 60.0) for i in range(12)]
    assert len(maquetar_juego(piezas, Formato.A2)) < len(maquetar_juego(piezas, Formato.A4))


# ---------------------------------------------------------------------------
# Planos y documentación no comparten documento
# ---------------------------------------------------------------------------


def test_las_plantillas_salen_siempre_a_tamaño_real():
    for lamina in maquetar_juego(juego_pequeno(), Formato.A4):
        assert lamina.escala == 1.0
    for lamina in maquetar(leva(), Formato.A4):
        assert lamina.escala == 1.0


def test_un_documento_no_mezcla_escalas(tmp_path):
    """Un papel con una vista a escala libre al lado de un contorno a tamaño
    real acaba con alguien cortando por la vista."""
    plantilla = maquetar(leva(), Formato.A4)[0]
    vista = Lamina(ancho=210.0, alto=297.0, escala=0.5)
    with pytest.raises(ValueError, match="no mezcla escalas"):
        escribir_pdf([plantilla, vista], tmp_path / "mezclado.pdf")


def test_un_documento_de_una_sola_escala_se_escribe(tmp_path):
    vista = Lamina(ancho=210.0, alto=297.0, escala=0.5)
    assert escribir_pdf([vista, vista], tmp_path / "dossier.pdf").exists()
