"""La hoja de una pieza: el tercero de los tres artefactos del bucle.

`docs/metodologia.md` §2d pide por pieza un DXF, una tabla y un boceto, y dice
que no se reparten. Lo que se ata aquí es eso: que ninguna pieza salga del
paquete con dos de los tres, y que lo que la hoja dibuja sea exactamente lo
que el comparador va a mirar después.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from emit.plataforma import LISTADO, contrato_mm
from scripts.comparar_dxf import FICHAS, cotas_en_mm
from scripts.dibujar_pieza import PERFIL_DE, hoja, main

pytestmark = pytest.mark.core


def test_ninguna_pieza_sale_con_dos_de_los_tres_artefactos():
    """**La regla del bucle, hecha test.** Una pieza con DXF y sin tabla se
    dibuja tecleando números leídos del dibujo; con tabla y sin boceto se
    dibuja sin entender la pieza. Las dos cosas son de donde vienen los
    errores que este bucle existe para evitar."""
    for pieza in PERFIL_DE:
        assert pieza in LISTADO, f"{pieza}: tiene forma y no tiene tabla"
        assert pieza in FICHAS, f"{pieza}: tiene forma y nadie la comprueba"
        assert LISTADO[pieza].porque, f"{pieza}: la hoja saldría sin explicar nada"


def test_la_hoja_solo_rotula_variables_que_existen():
    """Misma regla que las demás hojas: lo que se imprime se teclea."""
    # `cotas_en_mm` solo trae longitudes, con sus gemelos; los ángulos están
    # en el contrato y no en ella, así que hacen falta los dos.
    existen = cotas_en_mm().keys() | contrato_mm().keys()
    nombres = re.findall(r"#(?:cota|angulo|num)\.([a-z0-9_]+)", hoja())
    assert len(nombres) >= 20
    for nombre in nombres:
        assert nombre in existen, nombre


def test_la_hoja_dibuja_lo_que_el_comparador_mira():
    """**La propiedad que hace útil la hoja.** Las cotas que rotula salen de
    `FICHAS`, no de una lista aparte, así que una cota que el comparador no
    vigile tampoco aparece dibujada. Si alguna vez divergen, es que alguien
    puso una cota en un sitio y no en el otro."""
    texto = hoja()
    for pieza in PERFIL_DE:
        for nombre in FICHAS[pieza].radios:
            matriz = nombre.removesuffix("_radio").removesuffix("_diametro")
            assert matriz in texto or nombre in texto, f"{pieza}: {nombre} no sale en la hoja"


def test_cada_hoja_dice_como_se_ancla_y_que_hay_que_comprobar():
    """Los dos pasos que no puede hacer el compilador: anclar y mirar que el
    croquis quede definido."""
    texto = hoja()
    assert "DATUM" in texto
    assert "DOS coincidentes" in texto
    assert "totalmente definida" in texto


def test_se_escribe_donde_se_le_pide(tmp_path: Path):
    destino = tmp_path / "pieza.svg"
    assert main(["mordaza", "--out", str(destino)]) == 0
    texto = destino.read_text(encoding="utf-8")
    assert texto.startswith("<?xml")
    assert "mordaza" in texto
    assert "eje_pivote" not in texto, "se pidió una pieza y han salido dos"


def test_cada_pieza_declara_por_donde_se_extruye():
    """**Un perfil 2D no es una pieza.** Sin la tercera dimensión la hoja
    enseña un contorno y el espesor se queda en la tabla, que es donde menos
    se mira; y un espesor que no se ve en el dibujo se extruye al que tenga
    puesto el CAD por defecto."""
    cotas = contrato_mm()
    for pieza, ficha in LISTADO.items():
        clase, cota = ficha.solido
        assert clase in ("plancha", "barra"), f"{pieza}: sólido «{clase}»"
        assert cota in cotas, f"{pieza}: {cota} no está en el contrato"


def test_la_hoja_dibuja_las_dos_vistas():
    texto = hoja()
    assert "planta" in texto
    assert "sección A-A" in texto, "falta la sección de las planchas"
    assert "alzado" in texto, "falta el alzado de las barras"


def test_la_hoja_acota_todo_lo_que_la_ficha_declara():
    """No las principales: **todas**. Lo que no aparece dibujado se teclea de
    la tabla sin saber a qué rasgo corresponde.

    **Y tiene que estar DIBUJADA, no solo en la tabla.** La primera versión
    de este test buscaba el nombre en cualquier parte de la hoja, y la tabla
    se lo daba: `mordaza_voladizo` pasaba sin que ninguna línea de cota la
    señalara, que es justo lo que había que cazar. Por eso los rótulos que
    cuelgan de una cota llevan su propia clase.
    """
    for pieza in PERFIL_DE:
        texto, f = hoja([pieza]), FICHAS[pieza]
        esperadas = set(f.segmentos) | set(f.entre_centros)
        if f.cara_plana:
            esperadas.add(f.cara_plana)
        if f.ranura:
            esperadas.add(f.ranura[0])
        if f.voladizo:
            esperadas.add(f.voladizo)
        esperadas |= set(f.desde_datum)
        esperadas.add(LISTADO[pieza].solido[1])
        # Los radios van en la leyenda, con el nombre que pide el campo:
        # diámetro si es un agujero, radio si es un arco de contorno.
        esperadas |= {n.removesuffix("_radio") for n in f.radios} | set(f.radios)
        dibujadas = set(re.findall(r'class="cotavar"[^>]*>[^<]*#cota\.([a-z0-9_]+)<', texto))
        # Una cota circular vale dibujada en cualquiera de sus dos formas: la
        # leyenda pone la que pide el campo, no la que diga la ficha.
        faltan = {
            c for c in esperadas if not ({c, f"{c}_radio", c.removesuffix("_radio")} & dibujadas)
        }
        assert not faltan, f"{pieza}: en la tabla pero sin acotar en el dibujo: {sorted(faltan)}"


def test_una_pieza_simetrica_lo_dice_en_el_dibujo():
    """A lo alto no hay cota que sitúe el contorno, hay una simetría. Si no
    se dibuja, el que acota tiene que deducirla, y deducir es de donde salen
    los errores que este bucle evita."""
    assert "simétrico respecto del eje" in hoja(["mordaza"])


def test_cada_radio_dice_su_variable_en_la_leyenda():
    """**El fallo que puso un Ø4 donde iba el Ø3.** La flecha decía «Ø3» y la
    tabla tenía dos diámetros: emparejarlos era de cabeza. Juntos no caben
    —un nombre de variable es más ancho que la pieza— así que el número va en
    la flecha y el nombre en una leyenda al lado.

    Y el nombre es el que pide el campo: diámetro para un agujero, que es como
    Onshape acota un círculo, y radio para un arco de contorno.
    """
    texto = hoja(["mordaza"])
    assert "Ø3 → #cota.mordaza_tornillo_diametro" in texto
    assert "R2 → #cota.mordaza_fijacion_diametro_radio" in texto


# Ancho de carácter de cada clase, en px: Helvetica a 5.4 y monospace a 4.8.
_ANCHO = {"cotatx": 2.90, "cotavar": 2.88, "var": 2.88}


def _rotulos(svg: str) -> list[tuple[str, float, float, float, float]]:
    """Las cajas de los rótulos que viven en la banda de encima de la planta.

    Son los que pueden taparse entre sí: el número de cada radio, la leyenda
    que lo empareja con su variable, y la marca DATUM. Las cotas de la pila de
    abajo van una por nivel y no compiten por el sitio.
    """
    cajas = []
    patron = r'<text class="(cotatx|cotavar|var)"([^>]*)>([^<]*)</text>'
    for clase, atributos, texto in re.findall(patron, svg):
        if "rotate" in atributos:
            continue
        interesa = (clase == "cotatx" and texto[:1] in "ØR") or (
            clase == "cotavar" and "→" in texto
        )
        if not (interesa or texto == "DATUM"):
            continue
        x = float(re.search(r' x="([-\d.]+)"', atributos).group(1))
        y = float(re.search(r' y="([-\d.]+)"', atributos).group(1))
        ancla = (re.search(r'text-anchor="(\w+)"', atributos) or [None, None])[1]
        if ancla is None:
            ancla = "start" if clase == "cotavar" else "middle"
        ancho = len(texto) * _ANCHO[clase]
        alto = 5.4 if clase == "cotatx" else 4.8
        x0 = x if ancla == "start" else x - ancho / 2 if ancla == "middle" else x - ancho
        cajas.append((texto, x0, y - 0.78 * alto, x0 + ancho, y + 0.22 * alto))
    return cajas


def test_dos_rotulos_de_la_banda_de_arriba_no_se_tapan():
    """**Un rótulo encima de otro miente sin avisar.** El «R2» de la ranura de
    la mordaza aterrizaba a 18 px del «Ø3» del datum y más cerca del agujero
    que NO describe que del que sí, y de ahí salió un Ø4 dibujado en el datum:
    la hoja decía la verdad y se leía al revés.

    Mirar el dibujo no lo caza —los dos rótulos estaban, y cada uno con su
    flecha—; hay que medir dónde cae cada caja. Por eso esto se comprueba y no
    se revisa."""
    for pieza in PERFIL_DE:
        cajas = _rotulos(hoja([pieza]))
        assert len(cajas) >= 2, f"{pieza}: la banda de arriba está vacía"
        for i, (ta, ax0, ay0, ax1, ay1) in enumerate(cajas):
            for tb, bx0, by0, bx1, by1 in cajas[i + 1 :]:
                solapa = ax0 < bx1 and bx0 < ax1 and ay0 < by1 and by0 < ay1
                assert not solapa, f"{pieza}: «{ta}» se tapa con «{tb}»"
