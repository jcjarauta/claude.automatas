"""Las fichas de fabricación: la de grupo y una por pieza, deterministas,
con cada cota enlazada a la variable de su clase, y comprobadas leyendo lo
que de verdad se ha dibujado en el PDF."""

from __future__ import annotations

import re

import pytest

pytest.importorskip("build123d", reason="hace falta el kernel: uv sync --group cad")

MM = 72.0 / 25.4


@pytest.fixture(scope="module")
def amplificador():
    from scripts.fichas import preparar

    return preparar("amplificador")


@pytest.fixture(scope="module")
def paginas(amplificador, tmp_path_factory):
    """El texto de cada hoja del PDF sin comprimir: (x, y, texto) en mm."""
    from emit.fichas import escribir_fichas

    ruta = tmp_path_factory.mktemp("fichas") / "f.pdf"
    datos = escribir_fichas(amplificador, ruta, "commit prueba", comprimir=False).read_bytes()
    flujos = re.findall(rb"stream\r?\n(.*?)endstream", datos, re.S)
    hojas = []
    for flujo in flujos:
        t = flujo.decode("latin-1")
        if " Tj" not in t:
            continue
        textos = [
            (float(x) / MM, float(y) / MM, s)
            for x, y, s in re.findall(r"1 0 0 1 ([\d.\-]+) ([\d.\-]+) Tm \((.*?)\) Tj", t)
        ]
        hojas.append(textos)
    return hojas


def test_el_grupo_lleva_sus_piezas_su_tornilleria_y_sus_lagunas(amplificador):
    nombres = [p.nombre for p in amplificador.piezas]
    assert nombres == ["eje_pivote", "calzo_sector", "tambor", "sector", "mordaza"]
    assert [p.marca for p in amplificador.piezas] == [1, 2, 3, 4, 5]
    designaciones = {k.designacion for k in amplificador.comerciales}
    assert "DIN 912 M4 × 16" in designaciones
    assert not any("ejes de la mesa" in k.para for k in amplificador.comerciales)
    # La cinta es un comercial del grupo (C-AMP-01), no una laguna.
    assert amplificador.sin_ficha == ()
    assert any(k.codigo == "C-AMP-01" for k in amplificador.comerciales)
    # El despiece es el grupo entero: los dos canales.
    assert {n for _, n, _ in amplificador.despiece} >= {"sector_1", "sector_2"}


def test_a1_un_diametro_no_se_nombra_con_una_distancia(amplificador):
    """El calzo tiene un cubo de Ø22 y un tornillo a 22 del centro: el
    diámetro salía con el nombre de la distancia."""
    from emit.fichas import variable_de
    from emit.plataforma import LISTADO

    calzo, c = LISTADO["calzo_sector"], amplificador.contrato
    assert variable_de(22.0, calzo, c, "diametro") == "calzo_sector_cubo_diametro"
    assert variable_de(22.0, calzo, c, "distancia") == "union_sector_seguidor_cerca"
    assert variable_de(3.2, calzo, c, "distancia") == ""


def test_a1_si_casan_dos_de_la_misma_clase_lo_dice():
    from emit.fichas import variable_de
    from emit.plataforma import Ficha, Variable

    ficha = Ficha(
        "prueba",
        1,
        (Variable("cota", "a_diametro", "Ø uno"), Variable("cota", "b_diametro", "Ø otro")),
    )
    assert variable_de(5.0, ficha, {"a": 2.5, "b": 2.5}, "diametro").startswith("ambigua")


def test_a2_un_contorno_exterior_no_entra_en_la_tabla_de_taladros(amplificador):
    from emit.fichas import rasgos

    calzo = next(p for p in amplificador.piezas if p.nombre == "calzo_sector")
    r = rasgos(calzo.solido)
    assert [round(t.diametro, 2) for t in r.taladros] == [16.0, 3.2, 3.2]
    assert any(a.entero and round(2 * a.r, 2) == 22.0 for a in r.contorno)
    tambor = next(p for p in amplificador.piezas if p.nombre == "tambor")
    assert [t.tipo for t in rasgos(tambor.solido).taladros] == ["en D"]


def test_a4_cada_hoja_lleva_el_commit(paginas, amplificador):
    assert len(paginas) == 1 + len(amplificador.piezas)
    for hoja in paginas:
        assert any("commit prueba" in s for _, _, s in hoja)


def test_a6_cada_taladro_de_la_tabla_tiene_su_letra_en_la_planta(paginas, amplificador):
    """Leído del PDF: si un taladro está en la tabla, su letra está dibujada
    dentro de la celda de la planta."""
    from emit.fichas import CELDAS

    px, py, pw, ph = CELDAS["planta"]
    for hoja, pieza in zip(paginas[1:], amplificador.piezas, strict=True):
        cabecera = [y for x, y, s in hoja if s == "Taladro" and x > 180]
        if not cabecera:
            continue
        en_tabla = {
            s for x, y, s in hoja if 186 < x < 189 and y < cabecera[0] and re.fullmatch("[A-Z]", s)
        }
        en_planta = {
            s
            for x, y, s in hoja
            if px <= x <= px + pw and py <= y <= py + ph and re.fullmatch("[A-Z]", s)
        }
        assert en_tabla, pieza.nombre
        assert en_tabla <= en_planta, f"{pieza.nombre}: faltan {sorted(en_tabla - en_planta)}"


def test_a7_la_pieza_de_revolucion_lleva_seccion_y_no_dos_vistas_iguales(amplificador):
    """El tambor: alzado y perfil eran el mismo rectángulo. La sección por el
    eje enseña la pared entre el agujero y el canto, dos caras rayadas."""
    from emit.fichas import caras_cortadas, cortar

    tambor = next(p for p in amplificador.piezas if p.nombre == "tambor")
    caras = caras_cortadas(cortar(tambor.solido))
    assert len(caras) == 2
    paredes = sorted(f.bounds[2] - f.bounds[0] for f in caras)
    # Del agujero (R5) al canto, y de la cara plana (a 4 del eje) al canto.
    assert paredes == pytest.approx([6.975 - 5.0, 6.975 - 4.0], abs=0.01)


def test_el_pdf_es_determinista(amplificador, tmp_path):
    from emit.fichas import escribir_fichas

    a = escribir_fichas(amplificador, tmp_path / "a.pdf", "commit x").read_bytes()
    b = escribir_fichas(amplificador, tmp_path / "b.pdf", "commit x").read_bytes()
    assert a == b


def test_a4_las_plantillas_y_el_patron_tambien_llevan_la_version(tmp_path):
    """Toda hoja que se imprime suelta lleva el commit, también las de 1:1."""
    import zlib

    from emit.layout import Lamina
    from emit.template import escribir_pdf

    ruta = escribir_pdf([Lamina(ancho=210.0, alto=297.0)], tmp_path / "p.pdf", "commit prueba")
    datos = ruta.read_bytes()
    textos = b""
    for flujo in re.findall(rb"stream\r?\n(.*?)endstream", datos, re.S):
        try:
            textos += zlib.decompress(flujo)
        except zlib.error:
            textos += flujo
    assert b"commit prueba" in textos


def test_b4_cada_hoja_dice_que_no_se_mide_sobre_ella(paginas):
    from emit.estilo import NO_MEDIR

    for hoja in paginas:
        assert any(s == NO_MEDIR for _, _, s in hoja)


def test_b5_las_fichas_y_las_hojas_svg_comparten_estilo():
    """Un solo estilo: los colores de las cotas de las fichas y de las hojas
    SVG salen del mismo módulo."""
    from emit import estilo, fichas
    from scripts import acotar

    assert fichas.COTA is estilo.COTA
    assert estilo.COTA in acotar.ESTILO
    assert estilo.COTA in acotar.FLECHA
    assert "$" not in acotar.ESTILO


def test_b5_cada_cota_lleva_la_fila_de_su_variable_y_no_su_nombre(paginas, amplificador):
    """Los nombres de variable se quedan en la tabla, donde se leen para
    teclear; en el dibujo va el número de su fila."""
    from emit.fichas import CELDAS

    px, py, pw, ph = CELDAS["planta"]
    tambor = paginas[1 + [p.nombre for p in amplificador.piezas].index("tambor")]
    en_planta = [
        s for x, y, s in tambor if px <= x <= px + pw and py <= y <= py + ph and "#cota" in s
    ]
    assert not en_planta
    assert any(s == "Ref." for _, _, s in tambor)
