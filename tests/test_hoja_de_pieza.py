"""La hoja de una pieza: el tercero de los tres artefactos del bucle.

`docs/metodologia.md` §2d pide por pieza un DXF, una tabla y un boceto, y dice
que no se reparten. Lo que se ata aquí es eso: que ninguna pieza salga del
paquete con dos de los tres, y que lo que la hoja dibuja sea exactamente lo
que el comparador va a mirar después.
"""

from __future__ import annotations

import math
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
        if f.retranqueo:
            esperadas.add(f.retranqueo)
        esperadas |= set(f.desde_datum)
        esperadas.add(LISTADO[pieza].solido[1])
        # Los radios van en la leyenda, con el nombre que pide el campo:
        # diámetro si es un agujero, radio si es un arco de contorno.
        esperadas |= {n.removesuffix("_radio") for n in f.radios} | set(f.radios)
        # Una leyenda puede nombrar VARIAS cotas en el mismo rótulo, cuando
        # dos rasgos valen lo mismo: hay que sacarlas todas y no solo la
        # última, que es lo que hacía anclar la captura al «<» de cierre.
        dibujadas = {
            n
            for trozo in re.findall(r'class="cotavar"[^>]*>([^<]*)<', texto)
            for n in re.findall(r"#cota\.([a-z0-9_]+)", trozo)
        }
        # Una cota circular vale dibujada en cualquiera de sus dos formas: la
        # leyenda pone la que pide el campo, no la que diga la ficha.
        faltan = {
            c
            for c in esperadas
            if not ({c, f"{c}_radio", f"{c}_diametro", c.removesuffix("_radio")} & dibujadas)
        }
        assert not faltan, f"{pieza}: en la tabla pero sin acotar en el dibujo: {sorted(faltan)}"


def test_el_porque_de_una_ficha_no_lleva_markdown():
    """La hoja es un SVG, no un markdown: unos asteriscos puestos para
    resaltar salen impresos tal cual —«**Un brazo más.**»— y lo que iba a
    destacar queda peor que sin nada. Para eso están las mayúsculas, que es
    lo que usan las demás fichas."""
    for pieza, ficha in LISTADO.items():
        assert "**" not in ficha.porque, f"{pieza}: el porqué lleva markdown"
        assert "`" not in ficha.porque, f"{pieza}: el porqué lleva markdown"


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
        # Los de las polares llevan grado y van sueltos alrededor de la
        # planta, que es donde más sitio hay y más fácil es taparse: el del
        # pivote derecho y el de los postes salen los dos casi en horizontal.
        interesa = (clase == "cotatx" and (texto[:1] in "ØR" or "°" in texto)) or (
            clase == "cotavar" and "→" in texto
        )
        if not (interesa or texto == "DATUM"):
            continue
        x = float(re.search(r' x="([-\d.]+)"', atributos).group(1))
        y = float(re.search(r' y="([-\d.]+)"', atributos).group(1))
        # Del `style`, que es donde el renderizador lo mira: un atributo
        # `text-anchor` pierde contra la clase y no mueve el texto.
        assert 'text-anchor="' not in atributos, f"anclaje por atributo, no se aplica: {texto}"
        ancla = (re.search(r"text-anchor:(\w+)", atributos) or [None, None])[1]
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


def _por_pieza() -> tuple[dict[str, set[str]], set[str]]:
    """Para cada cota de la FICHA, en qué piezas es círculo entero y en cuáles arco.

    Las cotas salen de `FICHAS[pieza].radios` y no de barrer el contrato
    buscando el número. Barrerlo es la trampa documentada —con ochenta cotas
    cualquier número redondo encuentra una que lo explique— y aquí lo
    enseñó sola: `brazo_espesor` vale 3, igual que el radio del agujero del
    perno, y salía acusado de ser un radio mal rotulado.

    Hacen falta los dos conjuntos porque **el mismo rasgo es las dos cosas
    según la pieza**: el Ø10 es un agujero redondo en el tambor y una
    sección con cara plana en el eje de pivote, donde el radio es correcto.
    """
    from emit.plataforma import Arco

    c = contrato_mm()
    cotas = cotas_en_mm()
    enteros: dict[str, set[str]] = {}
    arcos: set[str] = set()
    for pieza, forma in PERFIL_DE.items():
        declaradas = FICHAS[pieza].radios
        for e in forma(c):
            if not isinstance(e, Arco):
                continue
            entero = abs(e.hasta - e.desde - 2 * math.pi) <= 1e-9
            for nombre in declaradas:
                if abs(cotas[nombre] - e.radio) > 1e-6:
                    continue
                if entero:
                    enteros.setdefault(nombre, set()).add(pieza)
                else:
                    arcos.add(nombre)
    return enteros, arcos


def test_un_circulo_entero_se_teclea_en_diametro_y_nadie_rotula_su_radio():
    """**De aquí salieron el sector y el tambor a la mitad, el mismo día.**

    La herramienta de círculo de Onshape acota el DIÁMETRO. El contrato
    guarda los dos cantos del cabestrante como radio —47,975 y 7,975— y la
    hoja del cabestrante los rotulaba así: metidos en el campo, las dos
    piezas salieron exactamente a la mitad, sin un solo aviso.

    Los gemelos ya existían y no sirvieron de nada, porque lo que se teclea
    es lo que la hoja pone, no lo que el CSV ofrece. Así que la regla no es
    «que exista el gemelo», es **que ninguna hoja rotule el radio de un
    círculo entero**.

    Una pieza sin perfil no entra aquí, y eso es justo lo que les pasaba a
    estas dos: estaban fuera del bucle, así que nada las miraba.
    """
    from scripts import dibujar_plano_brazos, dibujar_plano_cabestrante

    enteros, arcos = _por_pieza()
    assert "amplificador_sector_radio_mecanizado" in enteros, "el canto del sector"
    assert "amplificador_tambor_radio_mecanizado" in enteros, "el canto del tambor"

    def reclama(donde: str, texto: str, prohibidas: set[str]) -> None:
        for nombre in re.findall(r"#cota\.([a-z0-9_]+)", texto):
            assert nombre not in prohibidas, (
                f"{donde}: rotula #cota.{nombre}, que es el RADIO de un círculo entero. "
                f"En el campo de diámetro sale la mitad: pon «{nombre}_diametro» si "
                f"existe, o el nombre que ya está en diámetro."
            )

    # La hoja de cada pieza se mira contra SU perfil, que es lo preciso.
    for pieza in PERFIL_DE:
        reclama(f"hoja de {pieza}", hoja([pieza]), {n for n, p in enteros.items() if pieza in p})

    # Los dos planos a mano dibujan varias piezas, así que solo se les exige
    # lo que es círculo entero en alguna y arco en ninguna.
    siempre = set(enteros) - arcos
    for donde, texto in (
        ("plano_cabestrante", dibujar_plano_cabestrante.hoja()),
        ("plano_brazos", dibujar_plano_brazos.hoja()),
    ):
        reclama(donde, texto, siempre)

    for pieza, ficha in LISTADO.items():
        prohibidas = {n for n, p in enteros.items() if pieza in p}
        for v in ficha.variables:
            if v.mapa == "cota" and v.en_el_perfil:
                assert v.nombre not in prohibidas, f"{pieza}: el listado manda teclear un radio"


def test_el_alzado_de_una_barra_solo_dibuja_la_cara_plana_si_la_pieza_la_tiene():
    """El alzado de barra daba por hecho que toda barra lleva cara plana.

    La llevaba la única que había —el eje de pivote— y al entrar el tambor,
    que es una barra torneada sin ningún fresado, su hoja salió con una línea
    y el rótulo «cara plana». Dibujar un rasgo que la pieza no tiene es peor
    que no dibujarlo: se mecaniza."""
    for pieza, ficha in FICHAS.items():
        if pieza not in PERFIL_DE:
            continue
        tiene = "cara plana" in hoja([pieza])
        assert tiene == bool(ficha.cara_plana), (
            f"{pieza}: la hoja {'la' if tiene else 'no la'} dibuja"
        )


def test_un_rasgo_repetido_dice_cuantos_hay_en_la_flecha():
    """**La directriz señala uno, y los otros se quedan sin acotar.**

    El seguidor tiene tres Ø3,2 —el eje del rodillo y los dos tornillos al
    sector— y un solo rótulo: quien lo dibujó acotó ese y dejó los otros dos
    sueltos, con un «Ø?» escrito al lado en la captura. La leyenda decía los
    nombres pero no cuántos eran.

    «3× Ø3,2» es además como se rotula un repetido en cualquier plano, y la
    leyenda reparte el recuento entre las cotas que comparten el valor.
    """
    texto = hoja(["seguidor"])
    assert "3× Ø3.2" in texto
    assert "#cota.union_sector_seguidor_diametro ×2" in texto
    assert "#cota.seguidor_rodillo_diametro ×1" in texto
    # Y lo que solo aparece una vez no lleva recuento, que seria ruido.
    assert "1× " not in texto


def test_la_leyenda_de_arriba_no_se_mete_dentro_del_dibujo():
    """**La banda de arriba tiene que quedar ENCIMA de la planta, y eso se
    mide en la hoja, no en la fórmula que la coloca.**

    `ox`, `oy` son el (0, 0) de la pieza en la hoja, pero el alto reservado
    se medía contra la SEMICAJA, como si el datum estuviera siempre en el
    centro. En una barra, un disco o la mordaza lo está —son simétricos
    respecto de su datum— así que las dos cuentas daban lo mismo y la
    diferencia no existía.

    La base es la primera pieza que no lo es: su datum es un poste y queda a
    59 de un borde y a 216 del otro. La planta subía 43 mm sobre su sitio y
    el segundo renglón de la leyenda salía escrito sobre el borde de la
    tabla, con el mismo aspecto inocente que tenía el «R2» de la mordaza.

    Se mide sobre el SVG y no sobre las variables que lo colocan: una
    comprobación que modela el render y no mira lo que el render mira no es
    que no cace nada, es que dice que todo está bien.
    """
    svg = hoja()
    # Los renglones de la leyenda son los únicos `cotavar` con flecha: los
    # demás son rótulos de cota, que sí van pegados al dibujo a propósito.
    leyenda = [
        float(y)
        for y, texto in re.findall(r'<text class="cotavar"[^>]*y="([0-9.]+)"[^>]*>([^<]*)', svg)
        if "→" in texto
    ]
    assert leyenda, "la hoja ya no trae leyenda: el test se ha quedado sin objeto"

    dibujo = [float(y) for y in re.findall(r'<line class="contorno"[^>]*y1="([0-9.]+)"', svg)]
    dibujo += [
        float(cy) - float(r)
        for cy, r in re.findall(r'<circle class="contorno"[^>]*cy="([0-9.]+)" r="([0-9.]+)"', svg)
    ]
    assert dibujo

    # Cada renglón tiene que estar por encima de TODO lo que se dibuja
    # debajo de él en su propio panel. Como los paneles se apilan, basta con
    # exigir que ningún renglón caiga dentro de los 3 mm que rodean una
    # línea de contorno: un solape real son décimas, no milímetros.
    for y in leyenda:
        cerca = [t for t in dibujo if abs(t - y) < 3.0]
        assert not cerca, f"un renglón de leyenda a y={y} se monta sobre el contorno {cerca}"
