"""El acotado único: lineal, radial y angular, en SVG y en PDF."""

from __future__ import annotations

import math

import pytest

from emit import acotado, estilo
from emit.acotado import Arco, Linea, Punta, Rotulo, angular, grados, lineal, radial

pytestmark = pytest.mark.core


def test_la_cota_angular_tiene_sus_dos_rayos_su_arco_y_sus_dos_flechas():
    """La primitiva que faltaba: sin ella no se podía acotar ningún ángulo."""
    v = (10.0, 20.0)
    cota = angular(v, math.radians(10), math.radians(70), 15.0, "60°")
    lineas = [p for p in cota if isinstance(p, Linea)]
    arcos = [p for p in cota if isinstance(p, Arco)]
    puntas = [p for p in cota if isinstance(p, Punta)]
    assert len(lineas) == 2
    assert len(arcos) == 1
    assert len(puntas) == 2
    arco = arcos[0]
    assert arco.desde == pytest.approx(math.radians(10))
    assert arco.hasta == pytest.approx(math.radians(70))
    # Cada flecha cae en un extremo del arco y apunta por su tangente, hacia fuera.
    for punta, a in zip(puntas, (arco.desde, arco.hasta), strict=True):
        assert punta.en[0] == pytest.approx(v[0] + 15 * math.cos(a))
        assert punta.en[1] == pytest.approx(v[1] + 15 * math.sin(a))
        radial_x, radial_y = math.cos(a), math.sin(a)
        assert punta.hacia[0] * radial_x + punta.hacia[1] * radial_y == pytest.approx(0.0)
    # Los rayos van por los dos lados del ángulo.
    for linea, a in zip(lineas, (arco.desde, arco.hasta), strict=True):
        dx, dy = linea.b[0] - v[0], linea.b[1] - v[1]
        assert math.atan2(dy, dx) == pytest.approx(a)


def test_el_arco_va_por_el_camino_corto_aunque_se_den_al_reves():
    cota = angular((0.0, 0.0), math.radians(350), math.radians(20), 10.0, "30°")
    arco = next(p for p in cota if isinstance(p, Arco))
    assert arco.hasta - arco.desde == pytest.approx(math.radians(30))


def test_un_angulo_negativo_se_rotula_sin_signo():
    """El campo de ángulo del CAD no acepta signo: se teclea el gemelo
    `_positivo`, y el lado lo dice dónde cae el rasgo."""
    assert grados(math.radians(-58.407)) == "58,41°"
    assert grados(math.radians(29.75)) == "29,75°"


def test_lineal_y_radial_dicen_su_numero_y_su_referencia():
    cota = lineal((0.0, 0.0), (20.0, 0.0), (0.0, -6.0), "20", "3")
    textos = [p.texto for p in cota if isinstance(p, Rotulo)]
    assert textos == ["20", "3"]
    cota = radial((0.0, 0.0), 5.0, 45.0, "Ø10 h6", "1")
    assert [p.texto for p in cota if isinstance(p, Rotulo)] == ["Ø10 h6", "1"]
    assert all(p.color == estilo.COTA for p in cota if isinstance(p, Punta | Linea))


def test_las_dos_traducciones_escriben_lo_mismo(tmp_path):
    cota = angular((50.0, 50.0), 0.0, math.radians(29.75), 20.0, grados(math.radians(29.75)), "7")
    svg = "".join(acotado.a_svg(cota))
    assert "29,75°" in svg
    assert estilo.COTA in svg

    from reportlab.pdfgen import canvas

    ruta = tmp_path / "a.pdf"
    cv = canvas.Canvas(str(ruta), pageCompression=0)
    acotado.a_pdf(cv, cota)
    cv.showPage()
    cv.save()
    datos = ruta.read_bytes()
    # reportlab escribe lo que no es ASCII en octal: el grado sale como \260.
    assert rb"(29,75\260) Tj" in datos
    assert b"(7) Tj" in datos
