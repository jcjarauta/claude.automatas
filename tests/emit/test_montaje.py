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
    pomo de la manivela, que se sale 19 mm a propósito y está documentado.
    El montaje todavía no lleva la manivela, así que aquí no hay excepción
    que hacer: si algo asoma, es un error de colocación."""
    from compile.conjunto import piezas_en
    from compile.escribiente import Escribiente, compilar
    from scripts.exportar_para_cad import leer

    compilacion = compilar(leer(RAIZ / "demo" / "hola.json"))
    piezas = piezas_en(compilacion, Escribiente(), 0.0)
    base = next(p for p in piezas if p.nombre == "base").solido.bounding_box()
    for pieza in piezas:
        caja = pieza.solido.bounding_box()
        assert caja.min.X >= base.min.X - 1e-6, pieza.nombre
        assert caja.max.X <= base.max.X + 1e-6, pieza.nombre
        assert caja.min.Y >= base.min.Y - 1e-6, pieza.nombre
        assert caja.max.Y <= base.max.Y + 1e-6, pieza.nombre


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
    punta y los distales rectos pasando por el poste 3.
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
    choques = [
        r
        for r in roces
        if r.holgura < 0 and frozenset({r.una, r.otra}) not in CONTACTOS_A_PROPOSITO
    ]
    assert not choques, "\n".join(
        f"{r.una} con {r.otra}: {r.holgura:.3f} en θ = {math.degrees(r.theta):.0f}°"
        for r in choques
    )
