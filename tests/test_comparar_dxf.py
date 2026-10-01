"""El comparador de DXF.

Lo que hay que atar en un verificador es lo contrario de lo habitual: que
**falle cuando debe**. Un comparador que siempre dice que sí es peor que no
tener ninguno, porque se confía en él. Por eso casi todos los tests de aquí
le pasan una pieza estropeada a propósito y exigen que la cace.
"""

from __future__ import annotations

import math
from pathlib import Path

import ezdxf
import pytest

from scripts.acotar import MM, contrato
from scripts.comparar_dxf import FICHAS, adivinar, comparar, cotas_en_mm, informe

pytestmark = pytest.mark.core


def brazo(
    tmp_path: Path,
    *,
    largo: float | None = None,
    cubo: float = 9.0,
    plana: bool = True,
    tangentes: bool = True,
    en_datum: bool = False,
) -> Path:
    """Un `brazo_proximal` en DXF, con los defectos que se le pidan.

    Es la misma geometría que exporta Onshape: dos arcos de contorno, sus dos
    tangentes exteriores, el agujero del eje en D y el del perno redondo.
    """
    c = contrato()
    largo = c["brazo_proximal"] * MM if largo is None else largo
    r1 = c["brazo_extremo_diametro"] * MM / 2
    a0, a1 = c["brazo_eje_diametro"] * MM / 2, c["brazo_perno_diametro"] * MM / 2
    ch, cu = c["brazo_chaveta"] * MM, c["brazo_chaveta_cuerda"] * MM
    x0, x1 = (0.0, largo) if en_datum else (-largo / 2, largo / 2)

    doc = ezdxf.new("R2010")
    msp = doc.modelspace()
    al = math.acos((cubo - r1) / largo)
    msp.add_arc((x0, 0), cubo, math.degrees(al), 360 - math.degrees(al))
    msp.add_arc((x1, 0), r1, -math.degrees(al), math.degrees(al))
    for s in (1, -1):
        p0 = (x0 + cubo * math.cos(al), s * cubo * math.sin(al))
        p1 = (x1 + r1 * math.cos(al), s * r1 * math.sin(al))
        # Despegar la tangente del arco la convierte en una línea cualquiera,
        # que es justo lo que pasa cuando el croquis se traza punto a punto.
        msp.add_line(p0, p1 if tangentes else (p1[0], p1[1] + 0.4))
    if plana:
        th = math.degrees(math.acos(ch / a0))
        msp.add_arc((x0, 0), a0, th, 360 - th)
        msp.add_line((x0 + ch, -cu / 2), (x0 + ch, cu / 2))
    else:
        msp.add_circle((x0, 0), a0)
    msp.add_circle((x1, 0), a1)
    destino = tmp_path / "brazo.dxf"
    doc.saveas(destino)
    return destino


def test_un_brazo_bien_dibujado_cuadra(tmp_path: Path):
    inf = comparar(brazo(tmp_path), "brazo_proximal")
    assert inf.cuadra, [h.texto for h in inf.hallazgos]
    assert len(inf.bien) == 7


def test_caza_la_cara_plana_que_falta(tmp_path: Path):
    """**El fallo que yo no vi a ojo.** Un agujero redondo donde va una D deja
    montar el brazo a cualquier ángulo, que es lo que la cara plana existe
    para impedir, y en pantalla se parecen mucho."""
    inf = comparar(brazo(tmp_path, plana=False), "brazo_proximal")
    assert not inf.cuadra
    assert any("brazo_chaveta_cuerda" in h.texto for h in inf.hallazgos)


def test_caza_medio_milimetro_de_mas_entre_centros(tmp_path: Path):
    """Lo que fija la cinemática es esta distancia. Medio milímetro no se ve
    en la pantalla y sale entero en la punta del lápiz."""
    inf = comparar(brazo(tmp_path, largo=90.5), "brazo_proximal")
    assert not inf.cuadra
    assert any("brazo_proximal pide 90" in h.texto for h in inf.hallazgos)
    assert any("90.5000" in h.texto for h in inf.hallazgos)


def test_caza_un_cubo_con_el_radio_cambiado(tmp_path: Path):
    """R8 en vez de R9 deja 3 mm de pared sobre el agujero del eje. Entra como
    huérfano, que es lo correcto: no es que falte una cota, es que hay un
    número que ningún contrato explica."""
    inf = comparar(brazo(tmp_path, cubo=8.0), "brazo_proximal")
    assert not inf.cuadra
    assert any("R8.0000" in h.texto for h in inf.hallazgos)


def test_caza_un_contorno_que_no_es_tangente(tmp_path: Path):
    """Trazar el contorno punto a punto en vez de con una relación de
    tangencia da una pieza que se ve igual y tiene un codo. Es lo que yo
    sospeché de tu croquis y no era; si alguna vez lo es, se verá aquí."""
    inf = comparar(brazo(tmp_path, tangentes=False), "brazo_proximal")
    assert not inf.cuadra
    assert any("tangentes" in h.texto for h in inf.hallazgos)


def test_no_confunde_el_proximal_con_la_palanca(tmp_path: Path):
    """Son la misma forma con otra distancia entre centros, así que es el
    par de piezas que de verdad se puede confundir."""
    assert adivinar(brazo(tmp_path)) == "brazo_proximal"
    assert adivinar(brazo(tmp_path, largo=contrato()["brazo_palanca"] * MM)) == "palanca_lapiz"


def test_un_proximal_juzgado_como_distal_no_cuadra(tmp_path: Path):
    """El distal tiene los dos extremos iguales y no lleva cara plana. Si la
    ficha equivocada diera igual, la ficha no estaría haciendo nada."""
    assert not comparar(brazo(tmp_path), "brazo_distal").cuadra


def test_toda_ficha_cita_cotas_que_existen():
    """Misma regla que las hojas: una ficha que nombra una cota borrada deja
    de comprobar ese rasgo y no se entera nadie."""
    cotas = cotas_en_mm()
    for pieza, ficha in FICHAS.items():
        for nombre in (*ficha.radios, *ficha.entre_centros, *ficha.segmentos):
            assert nombre in cotas, f"{pieza}: {nombre}"


def test_el_informe_recuerda_lo_que_no_puede_ver(tmp_path: Path):
    """Las restricciones no viajan en un DXF, así que el informe tiene que
    decirlo siempre: un croquis exacto y suelto pasa este comparador."""
    assert "totalmente definida" in informe(comparar(brazo(tmp_path), "brazo_proximal"))


def test_la_pieza_en_el_datum_se_ancla_con_dos_coincidentes(tmp_path: Path):
    """**El problema que no resuelve ninguna cota.** Un croquis importado llega
    con la forma y sin una sola restricción, y las cotas de la pieza no quitan
    los tres grados de libertad del plano: una barra acotada de 90 sigue
    pudiendo estar en cualquier sitio y a cualquier ángulo.

    Lo que sí se puede meter en el archivo es el SITIO. Con el agujero del eje
    en el origen y el otro centro sobre +X quedan dos coincidentes, y los dos
    se enganchan a geometría que ya está dibujada: no hay que construir un
    punto medio, y lo que hay que construir se olvida.
    """
    inf = comparar(brazo(tmp_path, en_datum=True), "brazo_proximal")
    assert inf.cuadra
    assert "totalmente definida" in inf.datum


def test_una_pieza_centrada_en_el_origen_cuadra_pero_avisa(tmp_path: Path):
    """Centrada es tan correcta como en el datum —el contrato dice formas y
    distancias, no en qué punto del plano se dibujan— pero para anclarla hace
    falta construir el punto medio. Se informa, no se suspende: confundir una
    convención de trabajo con una pieza mal hecha hace que se deje de mirar
    el informe."""
    inf = comparar(brazo(tmp_path), "brazo_proximal")
    assert inf.cuadra, "la geometría es correcta y eso no puede dar error"
    assert "NO está en el origen" in inf.datum


def test_toda_ficha_declara_donde_se_ancla():
    """Una pieza sin datum es una pieza que alguien va a colocar a ojo."""
    for pieza, ficha in FICHAS.items():
        assert ficha.datum, pieza
        assert ficha.datum in ficha.radios, f"{pieza}: el datum tiene que ser un rasgo suyo"
