"""El catálogo de letras: qué tiene que cumplir una fuente para entrar.

**Por qué hay un catálogo y no una sola fuente.** Porque de las treinta y
dos Hershey solo dos caras latinas sirven, y eso hay que poder demostrarlo:
las demás dibujan cada letra con **dos pasadas paralelas** —son duplex, que
es como se engorda un trazo con pluma— y en esta máquina cada pasada es una
levantada más, o sea grados de la vuelta del árbol que no escriben nada.

Lo que se comprueba aquí es lo que decide si una fuente puede entrar, y lo
que se equivocaría en silencio si entrara mal.
"""

from __future__ import annotations

import itertools
import math

import pytest

from compile.texto import cargar_fuente, fuentes, huecos_de
from core.tipografia import ACENTOS, PuntoDeFuente, acentuar

NOMBRES = (
    "Arrels Juan Carlos Montserrat Begoña Núria Francesc "
    "Sebastià Anaïs Martí Joaquín Mònica Nicolás"
)
"""Los nombres que de verdad llegan, no un juego de caracteres."""

BANDA = 0.04
"""Cuánto se puede mover el enlace sin que cambie lo que une, en alturas de
x. Es la definición de valle puesta en un número: si un hueco cae dentro de
esta banda, el umbral no está en el valle sino encima de una decisión."""


@pytest.fixture(params=fuentes())
def nombre(request: pytest.FixtureRequest) -> str:
    """Cada fuente del catálogo pasa por todo lo de abajo."""
    return str(request.param)


def test_hay_mas_de_una_letra_que_elegir() -> None:
    """Un selector con una sola opción no es un selector."""
    assert len(fuentes()) >= 2


def test_el_alto_de_la_x_de_cada_fuente_es_el_que_mide_su_x(nombre: str) -> None:
    """**Se mide sobre la x**, no se deduce de la línea base.

    Coinciden en la cursiva —su x arranca en y = 0— y no en la de palo seco,
    que sube a -5 y mide 14 donde la línea base dice 9. Es la unidad del
    enlace y de la escala de partida, así que equivocarla un 56 % se arrastra
    a la frase entera sin que nada proteste: `encajar` la vuelve a escalar
    para que quepa en la caja, de modo que el tamaño final sale bien y lo que
    sale mal es todo lo que se mide en alturas de x.
    """
    f = cargar_fuente(nombre)
    arriba = min(y for t in f.glifos["x"].trazos for _, y in t)
    assert f.altura_de_x == pytest.approx(f.linea_base - arriba)


def test_el_enlace_de_cada_fuente_cae_en_un_valle(nombre: str) -> None:
    """Un umbral que se puede mover sin que cambie nada es un valle; uno que
    parte el grupo por la mitad es un número elegido.

    Medido sobre los nombres de la casa: la cursiva deja una banda vacía de
    0,108 alturas de x alrededor de su 0,5 —el último enlace dibujado está en
    0,458 y la primera levantada en 0,567— y la de palo seco, de 0,357, que
    es su hueco más corto: por debajo no hay nada porque no enlaza.
    """
    f = cargar_fuente(nombre)
    cerca = [
        h
        for linea in huecos_de(NOMBRES, fuente=nombre)
        for h in linea
        if abs(h - f.enlace) <= BANDA
    ]
    assert not cerca, f"«{nombre}» tiene huecos pegados a su enlace: {sorted(cerca)[:4]}"


def test_ninguna_fuente_dibuja_una_letra_con_dos_pasadas(nombre: str) -> None:
    """La prueba que deja fuera a treinta de las treinta y dos.

    Una fuente duplex dibuja el mismo trazo dos veces, desplazado, para que
    parezca más gruesa. Con una pluma eso es tinta; con esta máquina es **una
    levantada más por pasada**, y el techo está entre cinco y siete trazos.
    Se detecta sin saber el nombre de la fuente: dos trazos de un glifo que
    se recorren a menos de un quinto de la altura de x uno del otro son la
    misma pasada.
    """
    f = cargar_fuente(nombre)
    tope = f.altura_de_x * 0.2
    for letra in "abcdefghijklmnopqrstuvwxyz":
        trazos = [[(float(x), float(y)) for x, y in t] for t in f.glifos[letra].trazos]
        for a, b in itertools.combinations(trazos, 2):
            assert not _son_la_misma_pasada(a, b, tope), f"«{nombre}» dibuja la «{letra}» dos veces"


def test_cada_fuente_escribe_los_nombres_de_la_casa(nombre: str) -> None:
    """Incluidos los acentos. Una fuente que no los tenga no entra: «Begoña»
    con ene no es un fallo menor, es otro nombre."""
    assert cargar_fuente(nombre).faltan(NOMBRES) == []


def test_los_acentos_del_disco_son_los_que_compone_el_nucleo(nombre: str) -> None:
    """El cruce de las dos listas, para cada fuente: la regla vive en
    `core/` y el dato congelado en `docs/fuentes/`. Si falla, lo que toca es
    `uv run python scripts/extraer_fuente.py`, no ajustar el test."""
    f = cargar_fuente(nombre)
    base = f.model_copy(update={"glifos": {c: g for c, g in f.glifos.items() if c not in ACENTOS}})
    assert len(base.glifos) == 96
    assert acentuar(base) == {c: g for c, g in f.glifos.items() if c in ACENTOS}


def _son_la_misma_pasada(a: list[PuntoDeFuente], b: list[PuntoDeFuente], tope: float) -> bool:
    if len(a) < 2 or len(b) < 2:
        return False
    ida = max(_a_la_polilinea(p, b) for p in a)
    vuelta = max(_a_la_polilinea(p, a) for p in b)
    return max(ida, vuelta) <= tope


def _a_la_polilinea(punto: PuntoDeFuente, polilinea: list[PuntoDeFuente]) -> float:
    """Lo más cerca que el punto pasa de la polilínea."""
    px, py = punto
    mejor = math.inf
    for (ax, ay), (bx, by) in itertools.pairwise(polilinea):
        dx, dy = bx - ax, by - ay
        largo = dx * dx + dy * dy
        t = 0.0 if largo == 0 else max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / largo))
        mejor = min(mejor, math.hypot(px - (ax + t * dx), py - (ay + t * dy)))
    return mejor
