"""El conjunto en 3D: los sólidos de la plataforma y dónde va cada uno.

**Lo que hay que comprobar no es que el montaje se vea bien**, que es
justo lo que no caza nada en este proyecto. Es que la máquina montada en
tres dimensiones diga lo mismo que el compilador dice en el plano, por un
camino que no comparte una línea de código con él.
"""

from __future__ import annotations

import math
from pathlib import Path

import pytest

from emit.montaje import bucles
from emit.plataforma import LISTADO, contrato_mm

pytestmark = pytest.mark.core

RAIZ = Path(__file__).resolve().parent.parent.parent


# ---------------------------------------------------------------------------
# Partir un perfil en lazos, que no necesita kernel
# ---------------------------------------------------------------------------


def test_todo_perfil_de_la_plataforma_se_parte_en_lazos_cerrados():
    """Un perfil es una lista plana: el contorno delante y los agujeros
    detrás, encadenados. Si un elemento no enlaza con el siguiente no hay
    sólido que levantar, y conviene saberlo aquí y no dentro del kernel,
    donde el error sale como «no llegó a formar un sólido»."""
    from emit.montaje import perfil_y_espesor

    c = contrato_mm()
    for nombre in LISTADO:
        perfil, espesor = perfil_y_espesor(nombre, c)
        lazos = bucles(perfil)
        assert lazos, nombre
        assert sum(len(x) for x in lazos) == len(perfil), nombre
        assert espesor > 0.0, nombre


def test_un_circulo_entero_es_un_lazo_de_un_solo_elemento():
    """Empieza y acaba en el mismo punto, así que se cierra solo. Si no se
    tratara aparte, un agujero redondo se tragaría el elemento siguiente."""
    from emit.plataforma import circulo

    assert len(bucles(circulo((0.0, 0.0), 5.0))) == 1


def test_un_perfil_que_no_cierra_se_queja():
    """Antes que devolver medio contorno y que el fallo salga tres capas
    más abajo convertido en otra cosa."""
    from emit.plataforma import Segmento

    with pytest.raises(ValueError, match="sin cerrar"):
        bucles([Segmento((0.0, 0.0), (10.0, 0.0))])


def test_el_eje_de_pivote_llega_del_collar_al_circlip_en_los_dos_brazos():
    """El eje de pivote atraviesa el proximal —con su collar de 3 debajo— y
    sube hasta el tambor, que va en el plano del sector. Si la pila sube, el
    tambor sube con ella y un eje del largo de antes deja de atravesar el
    proximal: nadie lo vería en el barrido, porque un eje corto no choca con
    nada. Pasó al subir la pila 8 mm para el cubo del cartucho."""
    from emit.montaje import alturas

    c = contrato_mm()
    z = alturas(c)
    tope = z["tambor"][1] + 1.5
    pide = [tope - (z[f"proximal_{n}"][0] - 3.0) for n in (1, 2)]
    assert c["eje_pivote_largo"] >= max(pide) - 1e-9, pide
    assert c["eje_pivote_largo"] - max(pide) < 1.0, "sobra más de un milímetro de barra"


# ---------------------------------------------------------------------------
# Los sólidos
# ---------------------------------------------------------------------------

build123d = pytest.importorskip("build123d", reason="hace falta el kernel: uv sync --group cad")


def test_cada_pieza_de_la_plataforma_levanta_un_solido_de_su_tamano():
    """La caja del sólido tiene que ser la del perfil más su espesor. Es lo
    que impide que un lazo se quede fuera o que el espesor se tome de otra
    cota: las dos cosas dan un sólido con buena pinta."""
    from emit.montaje import perfil_y_espesor, solido_de

    c = contrato_mm()
    for nombre in LISTADO:
        _, espesor = perfil_y_espesor(nombre, c)
        caja = solido_de(nombre, c).bounding_box()
        assert pytest.approx(espesor, rel=1e-9) == caja.size.Z, nombre
        assert pytest.approx(0.0, abs=1e-9) == caja.min.Z, f"{nombre} no apoya en Z = 0"


def test_los_agujeros_se_restan_y_no_se_suman():
    """Un lazo interior mal tratado da una pieza maciza, y una pieza maciza
    cabe donde cabe la agujereada: no se nota hasta que se monta el eje."""
    from emit.montaje import solido_de

    c = contrato_mm()
    disco = 3.141592653589793 * (c["platina_diametro"] / 2) ** 2 * c["platina_espesor"]
    assert solido_de("platina_levas", c).volume < disco * 0.98


def test_los_arcos_entran_como_arcos_y_no_como_polilinea():
    """Un cubo de Ø18 facetado mide menos que uno redondo, y lo que decide
    un barrido de interferencia es justo esa diferencia. Se comprueba
    contra el área exacta del semicírculo del extremo."""
    from emit.montaje import solido_de

    c = contrato_mm()
    ancho = solido_de("brazo_distal", c).bounding_box().size.Y
    # El distal es curvo: de lo más bajo del cubo de la punta a lo más alto
    # del arco, que está a la flecha más medio ancho del brazo.
    esperado = c["distal_punta_diametro"] / 2 + c["distal_flecha"] + c["brazo_extremo_diametro"] / 2
    assert ancho == pytest.approx(esperado, rel=1e-6)


# ---------------------------------------------------------------------------
# El tercer camino sobre el hueco al poste
# ---------------------------------------------------------------------------


def test_el_hueco_al_poste_en_3d_coincide_con_el_que_mide_el_compilador():
    """**El motivo de todo este módulo.**

    `compile/conjunto.py` mide el hueco en el plano: la leva como un radio
    máximo y el poste como un círculo del radio del OBSTÁCULO —la valona
    del casquillo, Ø15—. Aquí se mide en tres dimensiones, con el perfil
    de leva entero, los sólidos de verdad y el poste real, que es un eje de
    Ø8. Entre los dos no hay una línea de código compartida.

    La diferencia esperada es exactamente la de los dos radios, 7,5 - 4 =
    3,5 mm. Si no cuadra, o el montaje coloca algo donde no va o el plano
    mide lo que no es; con los números delante se sabe cuál.

    El barrido es de doce ángulos y el del plano recorre toda la leva, así
    que el de aquí sale **optimista por unas centésimas**: no encuentra el
    peor ángulo exacto, cae al lado. Por eso la tolerancia es de dos
    décimas y no de una micra, y aun así un error de colocación se mide en
    milímetros y no se cuela.
    """
    from compile.conjunto import barrer, montar
    from compile.escribiente import Escribiente, compilar
    from scripts.exportar_para_cad import leer

    compilacion = compilar(leer(RAIZ / "demo" / "hola.json"))
    maquina = Escribiente()
    plano, _ = montar(compilacion, maquina)
    radio_obstaculo = contrato_mm()["poste_obstaculo_diametro"] / 2
    radio_poste = contrato_mm()["poste_eje_diametro"] / 2
    esperado = plano.holgura_al_poste * 1000.0 + (radio_obstaculo - radio_poste)

    roces = barrer(
        compilacion,
        maquina,
        pasos=12,
        entre=lambda a, b: a.startswith("leva") and b.startswith("poste"),
    )
    assert roces, "el barrido no encontró ni un par leva-poste: algo no se está colocando"
    assert roces[0].holgura == pytest.approx(esperado, abs=0.2), (
        f"en 3D la leva se queda a {roces[0].holgura:.3f} mm del poste "
        f"({roces[0].una} y {roces[0].otra}, theta {roces[0].theta:.3f} rad) y el plano "
        f"dice {esperado:.3f}. Uno de los dos coloca mal."
    )


def test_la_caja_envolvente_del_montaje_cabe_en_la_base():
    """Nada puede salirse de la tabla por los lados mientras gira, salvo el
    pomo de la manivela, que se sale a propósito y está documentado.

    **Se mide con la máquina a escuadra con la base.** El montaje vive en el
    marco de la leva, donde la base va girada; comparar cajas ahí era
    comparar contra la caja de un rectángulo girado, mucho más grande que
    él, y este test pasaba con los sectores fuera de la tabla 14,5 mm por
    cada lado. Lo encontró la vista agrupada del visor (auditoría A1), y se
    resolvió ensanchando la base de 190 a 240: el sector trabaja con la cinta
    justo hacia fuera de la base, así que recortarlo no servía.
    """
    from build123d import Rot

    from compile.conjunto import piezas_en
    from compile.escribiente import Escribiente, compilar
    from scripts.exportar_para_cad import leer

    compilacion = compilar(leer(RAIZ / "demo" / "hola.json"))
    a_escuadra = Rot(Z=90.0 - math.degrees(contrato_mm()["cartucho_salida_angulo"]))
    piezas = [(p.nombre, a_escuadra * p.solido) for p in piezas_en(compilacion, Escribiente(), 0.0)]
    base = next(s for n, s in piezas if n == "base").bounding_box()
    fuera = []
    for nombre, solido in piezas:
        caja = solido.bounding_box()
        sobra = max(
            base.min.X - caja.min.X,
            caja.max.X - base.max.X,
            base.min.Y - caja.min.Y,
            caja.max.Y - base.max.Y,
        )
        if sobra > 1e-6:
            fuera.append(f"{nombre}: {sobra:.1f} mm")
    assert not fuera, "se sale de la base: " + ", ".join(fuera)


CONTACTOS_A_PROPOSITO = {
    frozenset({"rueda", "pinon"}),
    frozenset({"mesa", "portaminas"}),
}
"""Los dos pares que se tocan porque tienen que tocarse: el engrane —los
discos al diámetro exterior del catálogo se meten dos módulos— y la mina
sobre el papel al escribir, que absorbe la precarga de la flexura."""


@pytest.mark.slow
def test_la_maquina_entera_no_choca_en_todo_el_ciclo():
    """**La prueba de que se puede fabricar y montar.** Todas las piezas —la
    plataforma, la transmisión, la cadena del levantamiento y el portalápiz—
    en doce ángulos del árbol, movidas por la leva real, y ningún par que se
    atraviese salvo los dos que se tocan a propósito.

    Lo que encontró la primera vez: los proximales solapados donde se cruzan,
    el balancín metido en la leva 3, el volante atravesado por el árbol, la
    bieleta cruzando el balancín, el lápiz en el mismo eje que el perno de la
    punta y los distales rectos pasando por el poste 3. Y, en cuanto entraron
    los rodillos con sus ejes, el eje del rodillo de abajo atravesando las dos
    levas de encima: de ahí la pila escalonada. Y, en cuanto entró la cinta,
    la tuerca del rodillo izquierdo cortándola y la cinta rozando los
    seguidores que cruza: de ahí el calzo del sector y los ejes avellanados.
    """
    from compile.conjunto import barrer
    from compile.escribiente import Escribiente, compilar
    from scripts.exportar_para_cad import leer

    raiz = Path(__file__).resolve().parents[2]
    compilacion = compilar(leer(raiz / "demo" / "hola.json"))
    roces = barrer(compilacion, Escribiente(), pasos=12, cerca=1.0)
    # Que el detector ve solapes: el engrane se mete dos módulos y tiene que
    # salir con holgura NEGATIVA. Con `distance_to` solo salía 0.
    engrane = next(r for r in roces if {r.una, r.otra} == {"rueda", "pinon"})
    assert engrane.holgura < -1.0, engrane
    # Cada rodillo toca SU leva en todo el ciclo, sin meterse: la leva del
    # compilador y el seguidor del montaje cuadran por caminos distintos.
    for n in (1, 2, 3):
        contacto = next(r for r in roces if {r.una, r.otra} == {f"leva_{n}", f"rodillo_{n}"})
        assert abs(contacto.holgura) < 0.01, contacto
    # Y cada cinta toca su sector y su tambor en todo el ciclo, sin meterse:
    # la trayectoria se recalcula en cada estado.
    for n in (1, 2):
        for polea in (f"sector_{n}", f"tambor_{n}"):
            contacto = next(r for r in roces if {r.una, r.otra} == {f"cinta_{n}", polea})
            assert abs(contacto.holgura) < 0.01, contacto
    choques = [
        r
        for r in roces
        if r.holgura < 0 and frozenset({r.una, r.otra}) not in CONTACTOS_A_PROPOSITO
    ]
    assert not choques, "\n".join(
        f"{r.una} con {r.otra}: {r.holgura:.3f} en θ = {math.degrees(r.theta):.0f}°"
        for r in choques
    )


CARTUCHO = ("leva_", "eje_cartucho", "cubo", "separador_", "pasador_indice")
"""Lo que sale con el cartucho: las levas y el metal que las enhebra."""


def _volumen_comun(una, otra) -> float:
    from compile.conjunto import _volumen_comun as comun

    return comun(una, otra)


def _del_cartucho(nombre: str) -> bool:
    return nombre.startswith(CARTUCHO)


def _cartucho_y_resto(theta: float = 0.0):
    from compile.conjunto import piezas_en
    from compile.escribiente import Escribiente, compilar
    from scripts.exportar_para_cad import leer

    piezas = piezas_en(compilar(leer(RAIZ / "demo" / "hola.json")), Escribiente(), theta)
    cartucho = [p.solido for p in piezas if _del_cartucho(p.nombre)]
    solido = cartucho[0]
    for otro in cartucho[1:]:
        solido = solido + otro
    return solido, [p for p in piezas if not _del_cartucho(p.nombre)]


@pytest.mark.slow
def test_el_cartucho_sale_por_detras_entre_los_dos_postes():
    """**El cartucho se puede cambiar sin desmontar la máquina.**

    El cartucho entero —las tres levas, su eje, el cubo, los separadores y el
    pasador—, en fase cero, sale en línea recta por el hueco entre los postes
    1 y 2 sin tocar nada: ni postes, ni platos, ni seguidores, ni los ejes de
    los rodillos. El tetón sale por la boca de la U del muñón y la ranura de
    la cabeza se desliza bajo la lengüeta de la garra, porque las dos van a
    lo largo de la dirección de salida.
    """
    from build123d import Pos

    c = contrato_mm()
    cartucho, resto = _cartucho_y_resto()
    a = c["cartucho_salida_angulo"]
    radio = c["cartucho_radio_maximo"]
    pasos = int((c["poste_radio_al_arbol"] / 2.0 + radio) // 10.0) + 2
    for paso in range(1, pasos + 1):
        d = paso * 10.0
        movido = Pos(d * math.cos(a), d * math.sin(a), 0.0) * cartucho
        for pieza in resto:
            if movido.distance_to(pieza.solido) > 1e-9:
                continue
            # Tocar sí: el cubo se desliza apoyado en lo alto del muñón. Meterse no.
            assert _volumen_comun(movido, pieza.solido) < 1e-3, (
                f"a {d:g} mm el cartucho se mete en {pieza.nombre}"
            )


@pytest.mark.slow
def test_el_cartucho_solo_entra_en_fase_cero():
    """La garra y la U solo dejan pasar el cartucho en fase cero. Girado
    media vuelta, la lengüeta choca con la cabeza del eje del cartucho y no
    entra: el error de fase deja de ser posible."""
    from build123d import Pos, Rot

    cartucho, resto = _cartucho_y_resto()
    garra = next(p.solido for p in resto if p.nombre == "garra")
    munon = next(p.solido for p in resto if p.nombre == "munon")
    # Bien puesto, ni la garra ni el muñón se meten en el cartucho.
    assert _volumen_comun(cartucho, garra) < 1e-3
    assert _volumen_comun(cartucho, munon) < 1e-3
    # Girado media vuelta sobre su eje, la lengüeta cae en la cabeza maciza.
    girado = Rot(Z=180.0) * cartucho
    assert _volumen_comun(girado, garra) > 1.0, "girado tendría que chocar con la lengüeta"
    # Y a medio meter, el tetón girado tampoco encuentra la boca de la U.
    c_a = contrato_mm()["cartucho_salida_angulo"]
    medio = Pos(4.0 * math.cos(c_a), 4.0 * math.sin(c_a), 0.0) * Rot(Z=180.0) * cartucho
    assert _volumen_comun(medio, garra) > 1.0


def test_toda_pieza_colocada_cae_en_un_solo_grupo():
    """La auditoría de conjunto va por subsistemas. Una pieza sin grupo no la
    audita nadie, y una en dos grupos se cuenta dos veces: las dos cosas
    saltan aquí el día que se añade una pieza al montaje."""
    from compile.conjunto import piezas_en
    from compile.escribiente import Escribiente, compilar
    from emit.montaje import GRUPOS, grupo_de
    from scripts.exportar_para_cad import leer

    piezas = piezas_en(compilar(leer(RAIZ / "demo" / "hola.json")), Escribiente(), 0.0)
    usados = {grupo_de(p.nombre).nombre for p in piezas}
    assert usados == {g.nombre for g in GRUPOS}, "hay un grupo sin piezas"
    # El bastidor no se mueve; el cartucho gira entero.
    for p in piezas:
        g = grupo_de(p.nombre).nombre
        if g == "bastidor":
            assert not p.movil, p.nombre
        if g == "cartucho":
            assert p.movil, p.nombre


def test_los_agujeros_de_la_mordaza_en_el_sector_son_los_de_la_cinta():
    """El sector lleva un agujero de mordaza por canal, detrás, en el centro
    de los 252° que abraza la cinta. Sale de dónde cae el tambor de cada
    canal respecto del brazo del seguidor; si cambia el cinco barras o el
    seguidor, el contrato tiene que cambiar con él."""
    from compile.escribiente import Escribiente
    from emit.montaje import _del_cinco_barras

    c = contrato_mm()
    m = Escribiente()
    al = _del_cinco_barras(c)
    radial = c["amplificador_sector_radio_mecanizado"] - c["mordaza_ancho"] / 2.0
    hueco = c["mordaza_entre_tornillos"] + c["mordaza_voladizo"] - c["mordaza_largo"] / 2.0
    sep = c["brazo_separacion"] / 2.0
    for i, (lado, x) in enumerate((("izquierdo", -sep), ("derecho", sep))):
        s = m.seguidor(i)
        px, py = s.pivote[0] * 1000.0, s.pivote[1] * 1000.0
        tx, ty = al((x, 0.0))
        atras = math.atan2(ty - py, tx - px) + math.pi - s.psi_cero
        hx = radial * math.cos(atras) + hueco * math.cos(atras + math.pi / 2.0)
        hy = radial * math.sin(atras) + hueco * math.sin(atras + math.pi / 2.0)
        assert math.hypot(hx, hy) == pytest.approx(c["sector_mordaza_al_centro"], abs=1e-4)
        assert math.atan2(hy, hx) == pytest.approx(c[f"sector_mordaza_angulo_{lado}"], abs=1e-6)


def test_el_montaje_coloca_las_piezas_que_dice_el_listado():
    """Cuántas unidades de cada pieza fabricada hay en el 3D tiene que ser lo
    que dice su ficha: es lo que se corta y lo que se compra. Cazó los
    collares, que el listado contaba 21 con el plato 3 sin collar encima."""
    from collections import Counter

    from compile.conjunto import piezas_en
    from compile.escribiente import Escribiente, compilar
    from scripts.exportar_para_cad import leer

    piezas = piezas_en(compilar(leer(RAIZ / "demo" / "hola.json")), Escribiente(), 0.0)
    nombres = [p.nombre for p in piezas]
    cuenta = Counter()
    for nombre in nombres:
        for pieza in ("collar", "mordaza", "calzo_sector", "sector", "tambor", "seguidor"):
            if nombre.startswith(pieza + "_") and not nombre.startswith(("sector_mordaza",)):
                cuenta[pieza] += 1
    for pieza in ("mordaza", "calzo_sector", "sector", "tambor", "seguidor"):
        assert cuenta[pieza] == LISTADO[pieza].cantidad, pieza
    assert cuenta["collar"] == LISTADO["collar"].cantidad
