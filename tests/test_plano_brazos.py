"""El plano de los tres brazos.

Lo que hay que atar en un plano que se copia a mano no es cómo se ve: es que
cada cota exista, que la pieza se pueda fabricar con ellas y que la propiedad
en la que se apoya —que el proximal sirva para los dos lados— sea cierta y no
una coincidencia de los números de hoy.
"""

from __future__ import annotations

import math
import re
from pathlib import Path

import pytest

from scripts.acotar import MM, contrato
from scripts.dibujar_plano_brazos import VARIABLES, hoja, main, medidas, obround, valor_de

pytestmark = pytest.mark.core


def test_los_dos_calajes_suman_media_vuelta_y_por_eso_el_brazo_es_uno():
    """**La propiedad que ahorra una pieza del despiece.**

    Los dos calajes suman exactamente -180 grados, que es lo que significa
    que las dos posturas sean simétricas respecto del eje Y. El espejo de una
    chapa plana es la misma chapa volteada, así que se corta un proximal y
    valen los dos lados.

    No es casualidad ni redondeo: sale de que el cinco barras es simétrico y
    de que el calaje se mide con la punta en el CENTRO de la caja. Si alguien
    moviera esa referencia, dejarían de sumar y harían falta dos piezas; por
    eso esto es un test y no un comentario.
    """
    c = contrato()
    assert c["calaje_izquierdo"] + c["calaje_derecho"] == pytest.approx(-math.pi, abs=1e-9)


def test_el_cubo_deja_pared_sobre_el_agujero_del_eje():
    """Un agujero de Ø10 en una barra de 12 de ancho deja 1 mm de pared y se
    rompe. Por eso ese extremo lleva cubo."""
    c = contrato()
    pared = (c["brazo_cubo_diametro"] - c["brazo_eje_diametro"]) / 2.0
    assert pared >= 0.003, "menos de 3 mm de pared sobre el agujero del eje"
    assert c["brazo_cubo_diametro"] > c["brazo_extremo_diametro"]


def test_la_cara_plana_cala_sin_comerse_el_agujero():
    """La cara plana tiene que morder lo suficiente para transmitir el par y
    no tanto como para dejar el agujero sin apoyo. Entre el 60 y el 95 % del
    radio es el rango sensato; a 4 de un radio de 5 da una cuerda de 6."""
    c = contrato()
    radio = c["brazo_eje_diametro"] / 2.0
    assert 0.60 * radio < c["brazo_chaveta"] < 0.95 * radio
    cuerda = 2.0 * math.sqrt(radio**2 - c["brazo_chaveta"] ** 2)
    assert cuerda == pytest.approx(c["brazo_chaveta_cuerda"])


def test_el_distal_tiene_los_dos_extremos_iguales():
    """Es una biela: gira libre en los dos pernos, no cala nada. Que los dos
    extremos salgan iguales es la consecuencia, y si dejaran de serlo sería
    que alguien le ha puesto un calaje que no necesita."""
    c = contrato()
    _, r0, r1, a0, a1 = medidas(c, "distal")
    assert r0 == r1
    assert a0 == a1


def test_cada_brazo_cabe_entre_sus_dos_cubos():
    """Si la distancia entre centros fuera menor que la suma de los radios de
    los cubos, el contorno se cruzaría consigo mismo y la tangente que lo
    dibuja no existiría."""
    c = contrato()
    for cual in ("proximal", "distal", "palanca"):
        largo, r0, r1, _, _ = medidas(c, cual)
        assert largo > r0 + r1, cual
        assert abs((r0 - r1) / largo) <= 1.0, cual


def test_el_contorno_se_cierra():
    """El obround son dos arcos y dos tangentes; una tangente mal puesta deja
    el camino abierto y el CAD lo importa como una línea suelta."""
    camino = obround(0.0, 0.0, 90.0, 9.0, 6.0, 1.0)
    assert camino.startswith("M ")
    assert camino.rstrip().endswith("Z")
    assert camino.count("A ") == 2


def test_la_cara_plana_va_a_cero_grados_porque_si_no_el_proximal_son_dos_piezas():
    """**El ángulo de la cara plana no es una preferencia de dibujo.**

    El proximal sirve para los dos lados porque se voltea, y voltear una
    chapa la refleja respecto de su propio eje. El contorno es simétrico y
    los dos agujeros están sobre el eje, así que lo único que puede romper
    la simetría es la cara plana: a un ángulo t, la volteada la tiene a -t y
    las dos piezas dejan de ser la misma.

    Vale cero, con la normal apuntando al otro cubo. Lo otro que vale es pi,
    con la normal al revés; cualquier valor entre medias devuelve el brazo
    derecho al despiece.
    """
    angulo = contrato()["brazo_chaveta_angulo"] % math.pi
    assert angulo == pytest.approx(0.0, abs=1e-9) or angulo == pytest.approx(math.pi, abs=1e-9)


def test_la_cuerda_rotulada_es_la_que_sale_de_las_otras_dos_cotas():
    """Está en el contrato para no hacer la raíz de cabeza, así que lo que hay
    que vigilar es que no se quede atrás si alguien mueve el agujero o el
    plano."""
    c = contrato()
    radio = c["brazo_eje_diametro"] / 2.0
    assert c["brazo_chaveta_cuerda"] == pytest.approx(
        2.0 * math.sqrt(radio**2 - c["brazo_chaveta"] ** 2)
    )


def test_cada_variable_que_rotula_existe_en_el_contrato_o_es_su_gemela():
    """Lo que se imprime se teclea, así que tiene que existir.

    **Con una excepción que el contrato no conoce**: los gemelos en radio y
    en diámetro los fabrica el exportador, no el contrato, y son los que hay
    que teclear en un campo de radio. Aquí se acepta el gemelo y se exige que
    su matriz esté; el cruce contra el CSV de verdad —que es donde el gemelo
    sí aparece— lo hace `tests/test_paquete_cad.py`.
    """
    c, texto = contrato(), hoja()
    # Buscando `#` a secas salen los colores del CSS, así que se pide el
    # prefijo del mapa: es además lo que distingue una variable del CAD.
    nombres = re.findall(r"#(?:cota|angulo|num|pieza|pieza_num)\.([a-z0-9_]+)", texto)
    assert len(nombres) >= 20, "la hoja apenas rotula variables"
    for nombre in nombres:
        matrices = {nombre.removesuffix("_radio"), nombre.removesuffix("_diametro")}
        assert nombre in c or matrices & c.keys(), nombre


def test_la_hoja_dice_el_valor_que_dice_el_contrato():
    """Una tabla de variables con el número cambiado es peor que no tenerla:
    se teclea el número y no el nombre. El gemelo también, que es la mitad."""
    c = contrato()
    assert valor_de(c, "cota", "brazo_cubo_diametro_radio") == pytest.approx(9.0)
    assert valor_de(c, "cota", "brazo_extremo_diametro_radio") == pytest.approx(6.0)
    assert valor_de(c, "angulo", "calaje_izquierdo") == pytest.approx(
        math.degrees(c["calaje_izquierdo"])
    )


def test_la_hoja_rotula_todas_las_cotas_de_cada_brazo():
    """**El hueco que abrió esto.** Faltaban por parametrizar el ángulo de la
    cara plana, su cuerda y los dos radios de contorno, y una cota que no
    está en la tabla se teclea a ojo desde el dibujo."""
    for cual in ("proximal", "palanca"):
        nombres = {n for _, n, _ in VARIABLES[cual]}
        assert {
            f"brazo_{cual}",
            "brazo_eje_diametro",
            "brazo_cubo_diametro_radio",
            "brazo_extremo_diametro_radio",
            "brazo_perno_diametro",
            "brazo_espesor",
            "brazo_chaveta",
            "brazo_chaveta_cuerda",
            "brazo_chaveta_angulo",
        } <= nombres, cual


def test_la_hoja_dice_que_los_ejes_no_tienen_plano():
    """Con la cara plana del brazo a cero, TODO el calaje se mecaniza en el
    eje, y ese plano no existe. Decirlo en la hoja es lo que impide que
    alguien dé los brazos por terminados."""
    texto = hoja()
    assert "FALTA UNA PIEZA" in texto
    assert "eje" in texto.lower()


def test_el_plano_dice_lo_que_no_esta_decidido():
    assert "SIN DEFINIR" in hoja()


def test_se_escribe_donde_se_le_pide(tmp_path: Path):
    destino = tmp_path / "brazos.svg"
    assert main(["--out", str(destino)]) == 0
    texto = destino.read_text(encoding="utf-8")
    assert texto.startswith("<?xml")
    assert f"{contrato()['brazo_distal'] * MM:g}" in texto
