"""Los acentos, compuestos desde los propios trazos de la fuente.

**Por qué hay que componerlos.** La Hershey de 1967 se distribuye con 96
glifos, los del ASCII, y ninguna de sus 32 variantes trae una letra
acentuada. Sin acentos la máquina no escribe medio listín de nombres de
aquí —ni «Begoña», ni «Sebastià», ni «Anaïs»—, que es justo lo que un
cliente pide.

**Y por qué no los dibuja nadie a mano.** Regla 4: la geometría de
producción no la inventa un modelo de lenguaje. Así que cada marca es un
trazo que la fuente ya tiene y cada cota de colocación está **medida**
sobre la propia fuente. Lo que se comprueba aquí es eso: que no se haya
colado un número elegido.
"""

from __future__ import annotations

import itertools
import math
import unicodedata

import pytest

from core.errors import LetraDesconocida
from core.tipografia import ACENTOS, DECIMALES, Fuente, Glifo, acentuar, componer, huecos
from core.units import mm

pytestmark = pytest.mark.core

PUNTO = [(4.0, -5.0), (5.0, -5.0), (5.0, -4.0), (4.0, -4.0), (4.0, -5.0)]
"""El punto de la i del juguete: un cuadradito de 1×1 con su base a 4
unidades por encima del alto de la x. Es la **única** marca que una fuente
monotrazo dibuja ya sobre una minúscula, así que de él salen las dos cotas
de colocación."""


def fuente_de_prueba() -> Fuente:
    """Un juguete con lo justo: tres letras y las cinco marcas.

    No se usa la fuente del disco a propósito —`core/` es puro— y además
    así se comprueba la **regla** y no el dibujo de 1967: si mañana entra
    otra fuente monotrazo, lo que tiene que seguir valiendo es esto.
    """
    cuadrado = [(0.0, 9.0), (0.0, 0.0), (9.0, 0.0), (9.0, 9.0), (0.0, 9.0)]
    return Fuente(
        nombre="prueba",
        procedencia="inventada para el test",
        linea_base=9.0,
        altura_mayuscula=-12.0,
        altura_de_x=9.0,
        glifos={
            "a": Glifo(lado_izquierdo=0, avance=10, trazos=[cuadrado]),
            "c": Glifo(lado_izquierdo=0, avance=10, trazos=[cuadrado[:4]]),
            "n": Glifo(lado_izquierdo=0, avance=10, trazos=[cuadrado]),
            "i": Glifo(
                lado_izquierdo=0,
                avance=6,
                trazos=[PUNTO, [(4.0, 0.0), (4.0, 9.0), (5.0, 9.0)]],
            ),
            # Las marcas, con la misma forma que en la Hershey: el acento
            # agudo y el grave son las dos ramas del `^`; la diéresis son
            # dos puntos de la i separados como las comillas; la tilde es
            # una onda de dos pasadas, y la cedilla, la coma.
            "'": Glifo(lado_izquierdo=0, avance=4, trazos=[[(0.0, -5.0), (0.0, -1.0)]]),
            "^": Glifo(
                lado_izquierdo=-8,
                avance=16,
                trazos=[[(0.0, -14.0), (-8.0, 0.0)], [(0.0, -14.0), (8.0, 0.0)]],
            ),
            '"': Glifo(
                lado_izquierdo=-8,
                avance=16,
                trazos=[[(-4.0, -12.0), (-4.0, -5.0)], [(4.0, -12.0), (4.0, -5.0)]],
            ),
            "~": Glifo(
                lado_izquierdo=-9,
                avance=20,
                trazos=[
                    [(-9.0, 1.0), (-3.0, -2.0), (3.0, 2.0), (9.0, -1.0)],
                    [(-9.0, 2.0), (-3.0, -1.0), (3.0, 3.0), (9.0, 0.0)],
                ],
            ),
            ",": Glifo(lado_izquierdo=0, avance=4, trazos=[[(0.0, 4.0), (1.0, 9.0)]]),
        },
    )


def caja(trazos: list[list[tuple[float, float]]]) -> tuple[float, float, float, float]:
    xs = [x for t in trazos for x, _ in t]
    ys = [y for t in trazos for _, y in t]
    return min(xs), max(xs), min(ys), max(ys)


def marca_de(glifo: Glifo, letra: str) -> list[list[tuple[float, float]]]:
    """Los trazos que el acento añadió, que van **delante** de la letra."""
    fuente = fuente_de_prueba()
    tope = fuente.linea_base - fuente.altura_de_x
    quedan = [t for t in fuente.glifos[letra].trazos if not all(y < tope for _, y in t)]
    return [[(x, y) for x, y in t] for t in glifo.trazos[: len(glifo.trazos) - len(quedan)]]


def largo(trazo: list[tuple[float, float]]) -> float:
    return sum(math.dist(a, b) for a, b in itertools.pairwise(trazo))


@pytest.fixture
def compuestos() -> dict[str, Glifo]:
    return acentuar(fuente_de_prueba())


def test_la_tabla_de_acentos_solo_nombra_marcas_que_existen(compuestos: dict[str, Glifo]) -> None:
    """Cada letra de la tabla sale compuesta, o la tabla miente."""
    assert set(compuestos) == {c for c, (base, _) in ACENTOS.items() if base in "acni"}


def test_el_acentuado_es_su_base_entera_mas_la_marca(compuestos: dict[str, Glifo]) -> None:
    """La letra no se retoca: se le añade un trazo encima.

    Es lo que hace que el acento sea barato de revisar —la «a» de «á» es
    byte a byte la «a»— y lo que impide que una composición mal hecha
    deforme la letra sin que se note.
    """
    base = fuente_de_prueba().glifos["a"]
    assert compuestos["á"].trazos[-len(base.trazos) :] == base.trazos
    assert len(compuestos["á"].trazos) == len(base.trazos) + 1


def test_la_i_pierde_el_punto_y_no_cuesta_un_trazo_mas(compuestos: dict[str, Glifo]) -> None:
    """«í» no es la i más el acento: es la i **sin su punto** más el acento.

    Dejarle el punto pondría dos marcas encima. Y como se va una y entra
    otra, la í acentuada **sale gratis**: mismo número de trazos que la i,
    o sea la misma cuenta de levantadas y los mismos grados de θ.
    """
    i = fuente_de_prueba().glifos["i"]
    assert len(compuestos["í"].trazos) == len(i.trazos)
    assert PUNTO not in compuestos["í"].trazos
    assert i.trazos[1] in compuestos["í"].trazos


def test_la_marca_va_centrada_sobre_la_tinta_de_la_letra(compuestos: dict[str, Glifo]) -> None:
    """Centrada sobre la **tinta**, no sobre la celda.

    No es una elección: es lo que la propia fuente hace con el punto de la
    i, y se comprueba ahí mismo en `test_las_dos_cotas_salen_del_punto_de_la_i`.
    """
    for letra in "áàñ":
        base = fuente_de_prueba().glifos[ACENTOS[letra][0]]
        bx0, bx1, _, _ = caja([[(x, y) for x, y in t] for t in base.trazos])
        mx0, mx1, _, _ = caja(marca_de(compuestos[letra], ACENTOS[letra][0]))
        assert (mx0 + mx1) / 2 == pytest.approx((bx0 + bx1) / 2, abs=10**-DECIMALES)


def test_las_dos_cotas_salen_del_punto_de_la_i(compuestos: dict[str, Glifo]) -> None:
    """El hueco sobre la letra es el que la fuente deja sobre la i.

    Es la única respuesta que la fuente da a «a qué altura va una marca
    sobre una minúscula», así que no hace falta elegir ninguna: aquí son
    cuatro unidades, cuatro novenos de altura de x.
    """
    fuente = fuente_de_prueba()
    tope_de_x = fuente.linea_base - fuente.altura_de_x
    hueco = tope_de_x - max(y for _, y in PUNTO)
    for letra in "áàñ":
        base = fuente.glifos[ACENTOS[letra][0]]
        _, _, by0, _ = caja([[(x, y) for x, y in t] for t in base.trazos])
        _, _, _, my1 = caja(marca_de(compuestos[letra], ACENTOS[letra][0]))
        assert by0 - my1 == pytest.approx(hueco, abs=10**-DECIMALES)


def test_el_agudo_y_el_grave_son_la_misma_rama_reflejada(compuestos: dict[str, Glifo]) -> None:
    """Un grave es un agudo del revés. Lo son por construcción, no por
    parecerse: son las dos ramas del mismo `^`, que la fuente dibuja
    simétricas."""
    agudo = compuestos["á"].trazos[0]
    grave = compuestos["à"].trazos[0]
    eje = sum(x for x, _ in agudo) / len(agudo)
    reflejado = [(2 * eje - x, y) for x, y in agudo]
    assert sorted(reflejado) == pytest.approx(sorted(grave), abs=10**-DECIMALES)


def test_el_agudo_sube_a_la_derecha_y_el_grave_baja(compuestos: dict[str, Glifo]) -> None:
    """La rama se elige por su inclinación y no por el orden en que la
    fuente la guarda, que es lo que convertiría un acento en el otro sin
    que nada protestara."""
    for letra, signo in (("á", +1), ("à", -1)):
        (x0, y0), (x1, y1) = compuestos[letra].trazos[0][0], compuestos[letra].trazos[0][-1]
        # La y de la fuente va hacia abajo.
        assert signo * (-(y1 - y0)) / (x1 - x0) > 0


@pytest.mark.parametrize(
    ("letra", "trazos_de_mas"),
    [("á", 1), ("à", 1), ("â", 1), ("ã", 1), ("ç", 1), ("ä", 2), ("í", 0), ("ï", 1)],
)
def test_lo_que_cuesta_cada_marca_en_trazos(
    compuestos: dict[str, Glifo], letra: str, trazos_de_mas: int
) -> None:
    """La cuenta que decide si un nombre cabe, en el glifo.

    Cuatro de las cinco marcas son un trazo: el agudo, el grave, la tilde y
    la cedilla. El circunflejo también, aunque sean dos ramas, porque salen
    del mismo vértice. La **diéresis son dos**, que es el único acento caro.
    Y sobre la i no se suman: sustituyen al punto, así que «í» sale gratis y
    «ï» cuesta uno.

    En la palabra puede costar uno más, porque la marca parte el enlace de
    la cursiva. Eso se mide con la fuente de verdad, en `tests/compile/`.
    """
    base = fuente_de_prueba().glifos[ACENTOS[letra][0]]
    assert len(compuestos[letra].trazos) - len(base.trazos) == trazos_de_mas


def test_el_circunflejo_es_un_solo_trazo(compuestos: dict[str, Glifo]) -> None:
    """Las dos ramas del `^` salen del mismo vértice, así que son un solo
    recorrido de pluma: se sube por una y se baja por la otra. Dejarlas
    sueltas haría levantar el lápiz en lo alto del acento para nada —16° de
    la vuelta— y pondría a «â» a dos trazos del presupuesto."""
    a = fuente_de_prueba().glifos["a"]
    assert len(compuestos["â"].trazos) == len(a.trazos) + 1
    assert len(compuestos["â"].trazos[0]) == 3
    assert compuestos["â"].trazos[0][1][1] < compuestos["â"].trazos[0][0][1]


def test_la_marca_mide_lo_que_mide_el_apostrofo(compuestos: dict[str, Glifo]) -> None:
    """El `^` entero es una marca de catorce unidades: puesta sobre una
    letra taparía el renglón de arriba. Se recorta a lo que mide el `'`,
    que es la otra marca que la fuente dibuja a altura de acento."""
    apostrofo = largo(list(fuente_de_prueba().glifos["'"].trazos[0]))
    for letra in "áà":
        assert largo(list(compuestos[letra].trazos[0])) == pytest.approx(
            apostrofo, abs=10**-DECIMALES
        )


def test_la_dieresis_son_dos_puntos_de_la_i(compuestos: dict[str, Glifo]) -> None:
    """Y no las comillas, que en esta fuente miden siete unidades de alto
    y sobre una «u» se leerían como un doble prima. De las comillas se
    toma solo **la separación**."""
    marca = compuestos["ï"].trazos[:2]
    assert len(marca) == 2
    izquierdo, derecho = (caja([[(x, y) for x, y in t]]) for t in marca)
    assert derecho[0] - izquierdo[0] == pytest.approx(8.0)
    for t in marca:
        assert len(t) == len(PUNTO)
        assert largo(list(t)) == pytest.approx(largo(PUNTO))


def test_la_tilde_es_una_sola_pasada(compuestos: dict[str, Glifo]) -> None:
    """El `~` de la fuente son dos pasadas de la misma onda, que es como
    se engorda un trazo con pluma. La segunda dibujaría lo mismo otra vez
    y costaría una levantada: la «ñ» cuesta **un** trazo, no dos."""
    n = fuente_de_prueba().glifos["n"]
    assert len(compuestos["ñ"].trazos) == len(n.trazos) + 1


def test_la_cedilla_cuelga_de_la_linea_base(compuestos: dict[str, Glifo]) -> None:
    """A diferencia de las de arriba no lleva hueco: una cedilla separada
    de la c se lee como una coma suelta detrás de la letra."""
    fuente = fuente_de_prueba()
    _, _, my0, my1 = caja(marca_de(compuestos["ç"], "c"))
    assert my0 == pytest.approx(fuente.linea_base, abs=10**-DECIMALES)
    assert my1 > fuente.linea_base


def test_el_acentuado_conserva_el_avance_y_el_lado_de_su_base(
    compuestos: dict[str, Glifo],
) -> None:
    """La marca vuela sobre los vecinos si hace falta, como en cualquier
    tipografía. Moverle el avance a la «ñ» separaría la palabra entera."""
    fuente = fuente_de_prueba()
    for letra, (base, _) in ACENTOS.items():
        if letra in compuestos:
            assert compuestos[letra].avance == fuente.glifos[base].avance
            assert compuestos[letra].lado_izquierdo == fuente.glifos[base].lado_izquierdo


def test_una_fuente_sin_las_marcas_se_queja() -> None:
    """Y dice cuáles faltan. Una fuente monotrazo sin `^` no puede dar
    acentos, y quedarse callada dejaría una fuente a medias en el
    catálogo."""
    fuente = fuente_de_prueba()
    sin_marcas = fuente.model_copy(
        update={"glifos": {k: v for k, v in fuente.glifos.items() if k not in "^~"}}
    )
    with pytest.raises(LetraDesconocida, match=r"\^"):
        acentuar(sin_marcas)


def test_un_acento_nunca_se_enlaza_con_su_letra() -> None:
    """Para dibujar un acento se levanta el lápiz. Siempre, cueste lo que
    cueste y esté donde esté la marca.

    No es una distancia, es lo que **es** una marca, y por eso no lo puede
    decidir el enlace. Pasó con «Mònica»: el grave acababa a 0,497 alturas
    de x del arranque de la «o» y el valle de la cursiva está en 0,50, así
    que por tres milésimas se unían y la máquina bajaba una raya recta desde
    el acento hasta dentro de la letra. Se veía bien y era un trazo que la
    letra no tiene.
    """
    fuente = fuente_de_prueba()
    entera = fuente.model_copy(update={"glifos": {**fuente.glifos, **acentuar(fuente)}})
    for enlace in (0.0, 0.5, 2.0):
        suelta = componer("a", entera, altura_de_x=mm(10.0), enlace=enlace)
        acentuada = componer("á", entera, altura_de_x=mm(10.0), enlace=enlace)
        assert len(acentuada.escritura.trazos) == len(suelta.escritura.trazos) + 1, (
            f"con enlace {enlace} la marca se ha pegado a la letra"
        )


def test_los_huecos_que_se_ensenan_son_los_que_el_enlace_decide() -> None:
    """Un hueco contra una marca no se puede unir, así que no sale en la
    lista: pintarlo bajo el deslizante prometería una unión que no va a
    ocurrir, que es justo lo que el deslizante existe para no hacer."""
    fuente = fuente_de_prueba()
    entera = fuente.model_copy(update={"glifos": {**fuente.glifos, **acentuar(fuente)}})
    assert huecos("aa", entera, altura_de_x=mm(10.0)) == huecos("áa", entera, altura_de_x=mm(10.0))


def test_el_texto_descompuesto_se_escribe_igual() -> None:
    """«á» se teclea de dos maneras —un carácter, o una «a» y una tilde
    suelta— y un portapapeles de macOS manda la segunda. Sin normalizar,
    el mismo nombre copiado de dos sitios da dos pedidos distintos, y uno
    de ellos dice que la fuente no tiene la letra."""
    fuente = fuente_de_prueba()
    entera = fuente.model_copy(update={"glifos": {**fuente.glifos, **acentuar(fuente)}})
    juntos = componer("á", entera, altura_de_x=mm(10.0))
    sueltos = componer(unicodedata.normalize("NFD", "á"), entera, altura_de_x=mm(10.0))
    assert len(unicodedata.normalize("NFD", "á")) == 2
    assert [t.puntos for t in juntos.escritura.trazos] == [
        t.puntos for t in sueltos.escritura.trazos
    ]
