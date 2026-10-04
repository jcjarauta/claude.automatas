"""El comparador de DXF.

Lo que hay que atar en un verificador es lo contrario de lo habitual: que
**falle cuando debe**. Un comparador que siempre dice que sí es peor que no
tener ninguno, porque se confía en él. Por eso casi todos los tests de aquí
le pasan una pieza estropeada a propósito y exigen que la cace.
"""

from __future__ import annotations

import math
import tempfile
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
    cara_al_reves: bool = False,
    eje: float | None = None,
    chaveta: float | None = None,
) -> Path:
    """Un `brazo_proximal` en DXF, con los defectos que se le pidan.

    Es la misma geometría que exporta Onshape: dos arcos de contorno, sus dos
    tangentes exteriores, el agujero del eje en D y el del perno redondo.
    """
    c = contrato()
    largo = c["brazo_proximal"] * MM if largo is None else largo
    r1 = c["brazo_extremo_diametro"] * MM / 2
    a0 = c["brazo_eje_diametro"] * MM / 2 if eje is None else eje
    a1 = c["brazo_perno_diametro"] * MM / 2
    ch = c["brazo_chaveta"] * MM if chaveta is None else chaveta
    cu = 2.0 * math.sqrt(a0**2 - ch**2)
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
        signo = -1.0 if cara_al_reves else 1.0
        th = math.degrees(math.acos(ch / a0))
        desde, hasta = (th, 360 - th) if not cara_al_reves else (180 + th, 180 - th)
        msp.add_arc((x0, 0), a0, desde, hasta)
        msp.add_line((x0 + signo * ch, -cu / 2), (x0 + signo * ch, cu / 2))
    else:
        msp.add_circle((x0, 0), a0)
    msp.add_circle((x1, 0), a1)
    destino = tmp_path / "brazo.dxf"
    doc.saveas(destino)
    return destino


def test_un_brazo_bien_dibujado_cuadra(tmp_path: Path):
    inf = comparar(brazo(tmp_path), "brazo_proximal")
    assert inf.cuadra, [h.texto for h in inf.hallazgos]
    assert len(inf.bien) == 8, "la cara plana con signo es una comprobación más"


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
    """Eran la misma forma con otra distancia entre centros, y ese era el par
    que de verdad se podía confundir.

    **Ya no lo son**: la palanca cuelga del eje del balancín, que es de 4
    porque el brazo de entrada mide 6,33, así que su cubo y su cara plana
    son otros. Lo que antes las separaba era un número y ahora las separan
    cuatro: el test sigue valiendo y además es más fácil de pasar, que es lo
    que uno quiere de un par de piezas parecidas.
    """
    c = contrato()
    assert adivinar(brazo(tmp_path)) == "brazo_proximal"
    palanca = brazo(
        tmp_path,
        largo=c["brazo_palanca"] * MM,
        cubo=c["balancin_cubo_diametro"] * MM / 2,
        eje=c["balancin_eje_diametro"] * MM / 2,
        chaveta=c["balancin_chaveta"] * MM,
    )
    assert adivinar(palanca) == "palanca_lapiz"


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


def test_caza_la_cara_plana_mirando_al_lado_contrario(tmp_path: Path):
    """**La cuerda sola no sitúa la cara.** En un agujero de Ø10 una cuerda de
    6 cae a 4 del centro, pero puede caer a +4 o a -4, y con la cara al otro
    lado el brazo se cala media vuelta girado: misma pieza en el croquis,
    otra distinta montada. El comparador lo dejaba pasar hasta que el cruce
    con `emit.plataforma.LISTADO` enseñó que esa cota no la miraba nadie.
    """
    inf = comparar(brazo(tmp_path, cara_al_reves=True), "brazo_proximal")
    assert not inf.cuadra
    assert any("media vuelta" in h.texto for h in inf.hallazgos)


def test_caza_un_contorno_centrado_donde_no_toca(tmp_path: Path):
    """**El fallo que encontró una cota dibujada.**

    El bloque de la mordaza estaba centrado entre sus dos tornillos, que
    parece lo natural, y por el extremo derecho la ranura se salía un
    milímetro. Desde el datum no había cota que situara el borde, así que
    nada lo decía: ni el dibujo, que no lo acotaba, ni el comparador.
    """
    import ezdxf

    from emit.plataforma import contrato_mm, mordaza
    from scripts.comparar_dxf import comparar as comparar_pieza

    c = contrato_mm()
    doc = ezdxf.new("R2010")
    msp = doc.modelspace()
    for e in mordaza(c):
        if hasattr(e, "a"):
            # El contorno se desplaza: el bloque centrado entre los tornillos.
            dx = c["mordaza_voladizo"] - c["mordaza_largo"] / 2 + c["mordaza_entre_tornillos"] / 2
            mover = abs(e.a[0] - e.b[0]) > 1e-9 or abs(e.a[1]) > c["mordaza_ancho"] / 2 - 1e-9
            d = dx if mover else 0.0
            msp.add_line((e.a[0] + d, e.a[1]), (e.b[0] + d, e.b[1]))
        else:
            msp.add_arc(e.centro, e.radio, math.degrees(e.desde), math.degrees(e.hasta))
    ruta = tmp_path / "torcida.dxf"
    doc.saveas(ruta)
    inf = comparar_pieza(ruta, "mordaza")
    assert not inf.cuadra
    assert any("mordaza_voladizo" in h.texto for h in inf.hallazgos)


def test_un_lado_partido_en_dos_sigue_siendo_un_lado(tmp_path: Path):
    """**Un falso positivo sobre cómo se dibujó, no sobre qué se dibujó.**

    Onshape parte las verticales de un rectángulo por el eje de simetría, y
    el comparador veía cuatro segmentos de 5 donde hay dos de 10. Lo que se
    compara tiene que ser la pieza; si el comparador opina del estilo de
    croquis, se le deja de hacer caso.
    """
    import ezdxf

    from emit.plataforma import Segmento, contrato_mm, mordaza
    from scripts.comparar_dxf import comparar as comparar_pieza

    c = contrato_mm()
    doc = ezdxf.new("R2010")
    msp = doc.modelspace()
    for e in mordaza(c):
        if isinstance(e, Segmento):
            # Cada lado, partido por su punto medio.
            medio = ((e.a[0] + e.b[0]) / 2, (e.a[1] + e.b[1]) / 2)
            msp.add_line(e.a, medio)
            msp.add_line(medio, e.b)
        else:
            msp.add_arc(e.centro, e.radio, math.degrees(e.desde), math.degrees(e.hasta))
    ruta = tmp_path / "partida.dxf"
    doc.saveas(ruta)
    inf = comparar_pieza(ruta, "mordaza")
    assert inf.cuadra, [h.texto for h in inf.hallazgos]


def test_caza_los_dos_diametros_cambiados(tmp_path: Path):
    """El M3 de apriete y el M4 de la ranura son distintos a propósito —para
    que no se puedan cambiar de agujero al MONTAR— pero al dibujar sí se
    pueden cambiar, y entonces la pieza es otra."""
    import ezdxf

    from emit.plataforma import Segmento, contrato_mm, mordaza
    from scripts.comparar_dxf import comparar as comparar_pieza

    c = contrato_mm()
    apriete, fijacion = c["mordaza_tornillo_diametro"] / 2, c["mordaza_fijacion_diametro"] / 2
    doc = ezdxf.new("R2010")
    msp = doc.modelspace()
    for e in mordaza(c):
        if isinstance(e, Segmento):
            y = [apriete if p[1] > 0 else -apriete if p[1] < 0 else 0.0 for p in (e.a, e.b)]
            dentro = abs(abs(e.a[1]) - fijacion) < 1e-9
            msp.add_line((e.a[0], y[0] if dentro else e.a[1]), (e.b[0], y[1] if dentro else e.b[1]))
        else:
            radio = fijacion if abs(e.radio - apriete) < 1e-9 else apriete
            msp.add_arc(e.centro, radio, math.degrees(e.desde), math.degrees(e.hasta))
    ruta = tmp_path / "cambiados.dxf"
    doc.saveas(ruta)
    inf = comparar_pieza(ruta, "mordaza")
    assert not inf.cuadra
    assert any("mordaza_tornillo_diametro" in h.texto for h in inf.hallazgos)


def test_dos_cotas_que_valen_lo_mismo_son_un_solo_grupo():
    """**Dos rasgos del mismo tamano no se distinguen midiendo.**

    En el seguidor, los tres pasos de rodillo y los dos del sector son los cinco
    Ø3,2, y el alojamiento del casquillo y el extremo del brazo son los dos
    Ø10. Pidiendolos por separado, cada cota se llevaba TODOS los que casan
    y sobraba, y la siguiente no encontraba ninguno y faltaba: cuatro quejas
    sobre un dibujo correcto, y ninguna cierta.

    Lo que identifica un rasgo es donde esta, no cuanto mide, y de eso se
    encargan `desde_datum` y `entre_centros`.
    """
    from emit.plataforma import escribir_dxf, seguidor

    destino = Path(tempfile.mkdtemp()) / "seguidor.dxf"
    escribir_dxf(seguidor(), destino)
    inf = comparar(destino, "seguidor")
    assert inf.cuadra, [h.texto for h in inf.hallazgos]
    assert any("R1.6 ×5" in b for b in inf.bien), inf.bien

    # El otro choque que tenia esta pieza —alojamiento del casquillo y extremo
    # del brazo, los dos Ø10— se quito cambiando el extremo a Ø11, porque ahi
    # SI hacia dano: uno es un circulo entero y el otro un arco de contorno, y
    # la hoja los rotulaba con el mismo «R5». Los tres Ø3,2 se quedan: son el
    # mismo paso de M3 y los distingue su posicion, que esta acotada.


def test_la_distancia_entre_dos_centros_ya_situados_no_es_una_cota():
    """Con cinco agujeros en linea hay **diez pares** y solo cuatro cotas.

    Un centro situado desde el datum —o por un `entre_centros` medido desde
    el— ya no pide nada mas: lo que haya entre dos situados es una resta, no
    una cota que falte. Sin esto el seguidor sacaba seis huerfanas estando
    entero, y seis quejas falsas esconden la verdadera.
    """
    from emit.plataforma import escribir_dxf, seguidor

    destino = Path(tempfile.mkdtemp()) / "seguidor.dxf"
    escribir_dxf(seguidor(), destino)
    inf = comparar(destino, "seguidor")
    assert not [h for h in inf.hallazgos if h.gravedad == "huerfano"], inf.hallazgos

    # Pero un agujero que NO esta situado sigue cantando.
    from emit.plataforma import circulo

    suelto = seguidor() + circulo((30.0, 4.0), 1.5)
    otro = Path(tempfile.mkdtemp()) / "suelto.dxf"
    escribir_dxf(suelto, otro)
    assert [h for h in comparar(otro, "seguidor").hallazgos if h.gravedad == "huerfano"]
