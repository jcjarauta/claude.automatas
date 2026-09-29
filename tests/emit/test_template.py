"""El PDF: tamaño de página, escala exacta y comparación contra referencia.

El PDF trabaja en puntos de 1/72 de pulgada, así que un milímetro son
2,834645... puntos, un número que no termina. La biblioteca lo escribe con
siete cifras significativas, de modo que la geometría no sale exacta al bit
sino con un error de nanómetros. Los márgenes de estos tests están puestos en
micras, que ya es mil veces más fino que el kerf del láser.
"""

from __future__ import annotations

import hashlib
import re
from pathlib import Path

import pytest
from pypdf import PdfReader

from emit.layout import LADO_CALIBRACION, Formato, maquetar
from emit.template import PUNTOS_POR_MM, escribir_pdf
from tests.emit.piezas_de_prueba import bastidor_grande, leva

pytestmark = pytest.mark.core

REFERENCIA = Path(__file__).resolve().parents[1] / "golden" / "plantilla_leva_a4.pdf"
TOLERANCIA_MM = 1e-3
"""Una micra. El kerf del láser es unas ciento cincuenta veces mayor."""


def escribir(tmp_path: Path, pieza=None, formato: Formato = Formato.A4) -> Path:
    return escribir_pdf(maquetar(pieza or leva(), formato), tmp_path / "p.pdf")


def caminos_cerrados(ruta: Path, pagina: int = 0) -> list[list[tuple[float, float]]]:
    """Extrae del flujo del PDF los contornos cerrados, en milímetros.

    Se lee el documento de verdad, no la lámina: lo que se imprime es esto.
    """
    flujo = PdfReader(ruta).pages[pagina].get_contents().get_data().decode("latin-1")
    caminos = []
    for bloque in re.findall(r"n ((?:-?[\d.]+ -?[\d.]+ [ml] )+)h", flujo):
        numeros = [float(x) / PUNTOS_POR_MM for x in re.findall(r"-?[\d.]+", bloque)]
        caminos.append(list(zip(numeros[0::2], numeros[1::2], strict=True)))
    return caminos


def medidas(camino: list[tuple[float, float]]) -> tuple[float, float]:
    xs = [p[0] for p in camino]
    ys = [p[1] for p in camino]
    return max(xs) - min(xs), max(ys) - min(ys)


# ---------------------------------------------------------------------------
# Tamaño de página
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("formato", "esperado"),
    [(Formato.A4, (210.0, 297.0)), (Formato.A3, (297.0, 420.0)), (Formato.A0, (841.0, 1189.0))],
)
def test_el_pdf_declara_el_tamaño_de_pagina_correcto(
    tmp_path: Path, formato: Formato, esperado: tuple[float, float]
):
    caja = PdfReader(escribir(tmp_path, formato=formato)).pages[0].mediabox
    assert float(caja.width) / PUNTOS_POR_MM == pytest.approx(esperado[0], abs=TOLERANCIA_MM)
    assert float(caja.height) / PUNTOS_POR_MM == pytest.approx(esperado[1], abs=TOLERANCIA_MM)


def test_la_pagina_empieza_en_el_origen(tmp_path: Path):
    """Un MediaBox desplazado movería todo el dibujo sin que se note."""
    caja = PdfReader(escribir(tmp_path)).pages[0].mediabox
    assert float(caja.left) == 0.0
    assert float(caja.bottom) == 0.0


def test_hay_una_pagina_por_lamina(tmp_path: Path):
    laminas = maquetar(bastidor_grande(), Formato.A4)
    ruta = escribir_pdf(laminas, tmp_path / "troceado.pdf")
    assert len(PdfReader(ruta).pages) == len(laminas)
    assert len(laminas) > 1


# ---------------------------------------------------------------------------
# Escala 1:1 medida sobre el documento
# ---------------------------------------------------------------------------


def test_el_cuadro_de_calibracion_mide_cien_milimetros_en_el_pdf(tmp_path: Path):
    """No basta con que la lámina diga 100: lo que se imprime es el PDF."""
    cuadrilateros = [c for c in caminos_cerrados(escribir(tmp_path)) if len(c) == 4]
    assert len(cuadrilateros) == 1
    ancho, alto = medidas(cuadrilateros[0])
    assert ancho == pytest.approx(LADO_CALIBRACION, abs=TOLERANCIA_MM)
    assert alto == pytest.approx(LADO_CALIBRACION, abs=TOLERANCIA_MM)


def test_el_error_de_escala_esta_muy_por_debajo_de_lo_medible(tmp_path: Path):
    """Concreta cuánto: el kerf del láser son unas 150 micras."""
    cuadro = next(c for c in caminos_cerrados(escribir(tmp_path)) if len(c) == 4)
    ancho, alto = medidas(cuadro)
    assert abs(ancho - LADO_CALIBRACION) < 1e-4
    assert abs(alto - LADO_CALIBRACION) < 1e-4


def test_el_contorno_de_la_pieza_conserva_su_tamaño_en_el_pdf(tmp_path: Path):
    pieza = leva()
    contorno = max(caminos_cerrados(escribir(tmp_path)), key=len)
    ancho, alto = medidas(contorno)
    xs = [p[0] * 1000.0 for p in pieza.contorno]
    ys = [p[1] * 1000.0 for p in pieza.contorno]
    assert ancho == pytest.approx(max(xs) - min(xs), abs=TOLERANCIA_MM)
    assert alto == pytest.approx(max(ys) - min(ys), abs=TOLERANCIA_MM)


def test_todas_las_hojas_de_un_troceado_llevan_su_cuadro(tmp_path: Path):
    laminas = maquetar(bastidor_grande(), Formato.A4)
    ruta = escribir_pdf(laminas, tmp_path / "troceado.pdf")
    for pagina in range(len(laminas)):
        cuadrilateros = [c for c in caminos_cerrados(ruta, pagina) if len(c) == 4]
        anchos = [medidas(c)[0] for c in cuadrilateros]
        assert any(abs(a - LADO_CALIBRACION) < TOLERANCIA_MM for a in anchos)


# ---------------------------------------------------------------------------
# Determinismo y referencia guardada
# ---------------------------------------------------------------------------


def test_el_mismo_contenido_da_los_mismos_bytes(tmp_path: Path):
    """Sin esto no habría forma de comparar contra una referencia: el PDF
    lleva fecha de creación e identificador aleatorio si no se le pide lo
    contrario."""
    huellas = {
        hashlib.sha256(escribir(tmp_path / f"v{i}").read_bytes()).hexdigest() for i in range(5)
    }
    assert len(huellas) == 1


def test_coincide_con_la_referencia_guardada(tmp_path: Path):
    """Detecta que algo ha cambiado en la geometría sin que nadie lo dijera.

    Si el cambio es querido, se regenera:
        uv run python scripts/regenerar_golden.py
    """
    assert REFERENCIA.exists(), (
        f"falta {REFERENCIA.name}. Genérala con: uv run python scripts/regenerar_golden.py"
    )
    actual = escribir(tmp_path).read_bytes()
    assert (
        hashlib.sha256(actual).hexdigest() == hashlib.sha256(REFERENCIA.read_bytes()).hexdigest()
    ), (
        "el PDF ya no coincide con la referencia. Si el cambio es intencionado, "
        "regenera con: uv run python scripts/regenerar_golden.py"
    )


# ---------------------------------------------------------------------------
# Detalles del documento
# ---------------------------------------------------------------------------


def test_el_pdf_avisa_en_sus_metadatos_de_no_ajustar(tmp_path: Path):
    """Quien lo abra en un visor lo ve en las propiedades del documento."""
    info = PdfReader(escribir(tmp_path)).metadata
    assert info is not None
    assert "100" in str(info.get("/Subject", ""))


def test_no_se_puede_escribir_un_pdf_sin_laminas(tmp_path: Path):
    with pytest.raises(ValueError, match="vacía"):
        escribir_pdf([], tmp_path / "vacio.pdf")


def test_el_pdf_se_crea_aunque_la_carpeta_no_exista(tmp_path: Path):
    ruta = escribir_pdf(maquetar(leva()), tmp_path / "a" / "b" / "p.pdf")
    assert ruta.exists()


# ---------------------------------------------------------------------------
# Legibilidad
# ---------------------------------------------------------------------------


def _ancho_real(texto: str, tamano_mm: float, negrita: bool) -> float:
    """Ancho en milímetros según las métricas de la fuente que se usa."""
    from reportlab.pdfbase.pdfmetrics import stringWidth

    fuente = "Helvetica-Bold" if negrita else "Helvetica"
    return stringWidth(texto, fuente, tamano_mm * PUNTOS_POR_MM) / PUNTOS_POR_MM


@pytest.mark.parametrize("formato", [Formato.A4, Formato.A3])
@pytest.mark.parametrize("pieza_nombre", ["leva", "bastidor"])
def test_ningun_texto_se_sale_de_la_hoja(formato: Formato, pieza_nombre: str):
    """Un rótulo cortado deja la plantilla sin el dato que hacía falta. Pasó
    con la advertencia de impresión en A4, que en una línea no cabía."""
    pieza = leva() if pieza_nombre == "leva" else bastidor_grande()
    for lamina in maquetar(pieza, formato):
        for texto in lamina.textos:
            ancho = _ancho_real(texto.texto, texto.tamano, texto.negrita)
            izquierda = texto.x - (ancho / 2 if texto.anclaje == "centro" else 0.0)
            assert izquierda >= -0.5, f"'{texto.texto}' se sale por la izquierda"
            assert izquierda + ancho <= lamina.ancho + 0.5, (
                f"'{texto.texto}' se sale por la derecha: acaba en "
                f"{izquierda + ancho:.1f} mm y la hoja mide {lamina.ancho:.0f} mm"
            )


def test_ningun_texto_baja_de_dos_milimetros_y_medio():
    """Por debajo de eso no se lee impreso."""
    for lamina in maquetar(leva(), Formato.A4):
        for texto in lamina.textos:
            assert texto.tamano >= 2.5
