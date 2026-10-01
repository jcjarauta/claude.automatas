"""Los perfiles de la plataforma y su DXF.

El generador y el comparador son los dos extremos del mismo bucle, así que
el test que de verdad importa es que **lo que emite uno lo apruebe el otro**,
datum incluido. Lo demás —que la tangente sea tangente, que la D muerda lo
justo— son las condiciones que se escribieron mal alguna vez.
"""

from __future__ import annotations

import itertools
import math
from pathlib import Path

import pytest

from emit.plataforma import (
    BRAZOS,
    PERFILES,
    Arco,
    Segmento,
    agujero_en_d,
    barra,
    brazo,
    contrato_mm,
    eje_pivote,
    escribir_dxf,
    mordaza,
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


def test_nada_arrolla_la_cinta_por_debajo_de_su_radio_minimo():
    """**La condición que decide cómo agarra la mordaza.**

    Un fleje de 0,05 no se puede arrollar a menos de cien veces su espesor
    sin pasarse de flexión, o sea 5 mm de radio. Eso descarta el pasador de
    arrastre pequeño que sería lo natural en un anclaje —tendría que ser de
    Ø10— y obliga a que la mordaza agarre por rozamiento.

    El tambor sí pasa, con holgura: R8 son 160 espesores.
    """
    c = contrato_mm()
    assert c["cinta_radio_minimo"] == pytest.approx(100.0 * c["cinta_espesor"])
    assert c["amplificador_tambor_radio_mecanizado"] >= c["cinta_radio_minimo"]
    for cota in ("mordaza_tornillo_diametro", "mordaza_fijacion_diametro"):
        assert c[cota] / 2 < c["cinta_radio_minimo"], (
            f"{cota} es más grande que el radio mínimo: si la cinta lo rodeara "
            "valdría como arrastre, y entonces la mordaza no es solo rozamiento"
        )


def test_los_dos_tornillos_de_la_mordaza_no_son_iguales():
    """Uno aprieta la cinta y el otro fija el bloque al sector. Siendo de
    distinto diámetro no se pueden cambiar de agujero al montar, que es el
    patrón del pasador de índice: no hacer el error improbable, hacerlo
    imposible. De paso, es lo que deja al comparador distinguirlos."""
    c = contrato_mm()
    assert c["mordaza_tornillo_diametro"] != c["mordaza_fijacion_diametro"]


def test_la_ranura_cala_mas_de_lo_que_hace_falta():
    """El recorrido de la mordaza es lo que cala el brazo, y tiene que cubrir
    de sobra lo que la máquina se mueve entre frases —3,3 grados— más lo que
    se desvíe una cinta cortada a mano."""
    c = contrato_mm()
    calaje = math.degrees(c["mordaza_recorrido"] / 2 / c["amplificador_tambor_radio"])
    assert calaje > 10.0, f"solo {calaje:.1f} grados de calaje a cada lado"


def test_la_mordaza_tapa_sus_dos_agujeros():
    """Un bloque más corto que la distancia entre tornillos deja la ranura
    fuera del material."""
    c = contrato_mm()
    assert c["mordaza_largo"] > c["mordaza_entre_tornillos"] + c["mordaza_recorrido"]
    assert c["mordaza_ancho"] > c["cinta_ancho"]


def test_el_eje_no_lleva_ningun_angulo():
    """**Lo que gana la decisión de la mordaza.** Mientras el calaje se
    mecanizaba en el eje, esta pieza llevaba un ángulo de cuatro decimales y
    había una por lado. Con el calaje en la mordaza es una barra de stock con
    un fresado, igual en los tres sitios, y su sección no tiene más cotas que
    el diámetro y la cara plana."""
    perfil = eje_pivote()
    assert len(perfil) == 2
    c = contrato_mm()
    arco = next(e for e in perfil if isinstance(e, Arco))
    assert arco.radio == pytest.approx(c["brazo_eje_diametro"] / 2)


def test_la_cara_del_eje_y_la_del_brazo_son_la_misma():
    """Si no coincidieran, el brazo no entraría o bailaría. Van juntas porque
    salen de las mismas dos cotas, y esto lo deja escrito."""
    c = contrato_mm()
    seg_eje = next(e for e in eje_pivote() if isinstance(e, Segmento))
    seg_brazo = next(
        e
        for e in agujero_en_d((0.0, 0.0), c["brazo_eje_diametro"] / 2, c["brazo_chaveta"])
        if isinstance(e, Segmento)
    )
    assert math.dist(seg_eje.a, seg_eje.b) == pytest.approx(math.dist(seg_brazo.a, seg_brazo.b))
    assert seg_eje.a[0] == pytest.approx(seg_brazo.a[0])


@pytest.mark.parametrize("cual", sorted(PERFILES))
def test_cada_perfil_nuevo_lo_aprueba_el_comparador(cual: str, tmp_path: Path):
    inf = comparar(escribir_dxf(PERFILES[cual](None), tmp_path / f"{cual}.dxf"), cual)
    assert inf.cuadra, [h.texto for h in inf.hallazgos]
    assert "totalmente definida" in inf.datum


def test_la_mordaza_envuelve_sus_agujeros_con_pared_de_sobra():
    """**El fallo que cazó una cota que faltaba.**

    El bloque estaba centrado entre los dos tornillos, que parece lo natural,
    pero la ranura llega más lejos que el segundo centro —su recorrido más su
    radio— y por el extremo derecho se salía un milímetro. En el dibujo se ve
    si alguien lo acota; mientras nadie acotara el borde no se veía, porque
    desde el datum no había cota que lo situara.

    Ahora lo sitúa `mordaza_voladizo` y lo vigila esto.
    """
    c = contrato_mm()
    izquierda = -c["mordaza_voladizo"]
    derecha = izquierda + c["mordaza_largo"]
    pared = c["mordaza_pared"]

    fin_ranura = (
        c["mordaza_entre_tornillos"]
        + c["mordaza_recorrido"] / 2
        + c["mordaza_fijacion_diametro"] / 2
    )
    assert derecha - fin_ranura >= pared, "la ranura se sale por el extremo"
    assert -c["mordaza_tornillo_diametro"] / 2 - izquierda >= pared, "el apriete se sale"

    arriba = c["mordaza_ancho"] / 2
    for agujero in ("mordaza_tornillo_diametro", "mordaza_fijacion_diametro"):
        assert arriba - c[agujero] / 2 >= pared, f"{agujero} deja el bloque sin pared a lo ancho"


def test_el_contorno_de_la_mordaza_contiene_todo_lo_demas():
    """Lo mismo medido sobre el perfil que se emite, y no sobre las cotas: si
    alguna vez el dibujo dejara de seguir al contrato, esto lo diría."""
    perfil = mordaza()
    rect = [e for e in perfil if isinstance(e, Segmento) and len(perfil) > 4][:4]
    xs = [p[0] for e in rect for p in (e.a, e.b)]
    ys = [p[1] for e in rect for p in (e.a, e.b)]
    for e in perfil:
        if not isinstance(e, Arco):
            continue
        assert min(xs) <= e.centro[0] - e.radio, "se sale por la izquierda"
        assert e.centro[0] + e.radio <= max(xs), "se sale por la derecha"
        assert min(ys) <= e.centro[1] - e.radio, "se sale por abajo"
        assert e.centro[1] + e.radio <= max(ys), "se sale por arriba"


def test_los_dos_centros_de_la_ranura_salen_de_las_otras_dos_cotas():
    """**Una cota derivada es segura si un test la ata.**

    La herramienta de ranura pide sus dos centros, no el par (centro,
    recorrido), así que restar la mitad quedaba de cuenta de cabeza. Están
    en el contrato para no hacerla, y aquí se comprueba que siguen saliendo
    de donde dicen: es el mismo trato que `brazo_chaveta_cuerda`.
    """
    c = contrato_mm()
    entre, recorrido = c["mordaza_entre_tornillos"], c["mordaza_recorrido"]
    assert c["mordaza_ranura_cerca"] == pytest.approx(entre - recorrido / 2)
    assert c["mordaza_ranura_lejos"] == pytest.approx(entre + recorrido / 2)
    assert c["mordaza_ranura_cerca"] > c["mordaza_tornillo_diametro"] / 2, (
        "la ranura empieza dentro del agujero de apriete"
    )


def test_los_agujeros_de_la_mordaza_no_se_comen_la_pared_entre_ellos():
    """**El fallo que yo no vi y encontró quien dibujaba.**

    Había un test que comprobaba la pared de cada agujero contra los BORDES
    del bloque, y ninguno que mirara los agujeros **entre sí**: con el centro
    de la ranura a 8, entre el agujero de apriete y el principio de la ranura
    quedaban 1,5 mm donde el propio contrato pide 3. La mitad, y el dibujo lo
    enseñaba sin que nada protestara.

    La lección se repite: una comprobación que mira cada rasgo contra el
    contorno no dice nada de los rasgos entre ellos. Hacen falta las dos.

    Los tramos se escriben a mano y no se deducen del perfil a propósito: la
    ranura son dos arcos que NO se tocan, y lo que hay entre ellos es la
    ranura, no una pared. Deducirlo lo confundía.
    """
    c = contrato_mm()
    pared = c["mordaza_pared"]
    apriete = c["mordaza_tornillo_diametro"] / 2
    ranura = c["mordaza_fijacion_diametro"] / 2
    tramos = [
        ("borde izquierdo", -c["mordaza_voladizo"], -c["mordaza_voladizo"]),
        ("agujero de apriete", -apriete, apriete),
        ("ranura", c["mordaza_ranura_cerca"] - ranura, c["mordaza_ranura_lejos"] + ranura),
        ("borde derecho", *(2 * (c["mordaza_largo"] - c["mordaza_voladizo"],))),
    ]
    for (que, _, fin), (siguiente, ini, _) in itertools.pairwise(tramos):
        assert ini - fin >= pared - 1e-9, (
            f"solo {ini - fin:.2f} mm entre {que} y {siguiente}, "
            f"y #cota.mordaza_pared pide {pared:g}"
        )


def test_la_mordaza_tampoco_se_queda_sin_pared_a_lo_ancho():
    """El mismo criterio en la otra dirección, donde manda la ranura."""
    c = contrato_mm()
    for agujero in ("mordaza_tornillo_diametro", "mordaza_fijacion_diametro"):
        assert c["mordaza_ancho"] / 2 - c[agujero] / 2 >= c["mordaza_pared"] - 1e-9, agujero
