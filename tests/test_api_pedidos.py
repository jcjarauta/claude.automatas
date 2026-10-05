"""La interfaz local de pedidos.

Lo que se comprueba aquí es **la frontera**, no la geometría: que un
texto entre y salgan trazos, que un carácter que la fuente no tiene se
conteste como respuesta y no como caída del servidor, y que no se pueda
sacar un archivo de fuera de la carpeta del pedido.

Compilar un pedido entero tarda segundos y ya tiene quien lo vigile en
`tests/golden/`: aquí no se repite.
"""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.core

pytest.importorskip("fastapi", reason="hace falta la interfaz: uv sync --group web")
pytest.importorskip("httpx", reason="hace falta httpx para el cliente de prueba")

from fastapi.testclient import TestClient  # noqa: E402

from api.main import app  # noqa: E402

cliente = TestClient(app)


def test_la_pagina_se_sirve():
    respuesta = cliente.get("/")
    assert respuesta.status_code == 200
    assert "Escribiente" in respuesta.text


def test_un_texto_devuelve_sus_trazos_y_su_tamano():
    respuesta = cliente.post("/api/trazos", json={"texto": "Arrels"})
    assert respuesta.status_code == 200
    datos = respuesta.json()
    assert datos["trazos"]
    assert all(len(t) >= 2 for t in datos["trazos"])
    assert datos["ancho_mm"] > 0
    assert datos["alto_mm"] > 0


def test_una_letra_que_la_fuente_no_tiene_es_una_respuesta_y_no_una_caida():
    """422 y el motivo en claro. Con un 500 el cliente vería «error del
    servidor» donde lo que pasa es que su nombre lleva eñe."""
    respuesta = cliente.post("/api/trazos", json={"texto": "Begoña"})
    assert respuesta.status_code == 422
    assert "ñ" in respuesta.json()["detail"]


def test_el_enlace_cambia_cuantos_trazos_salen():
    """Es el mando que de verdad decide si una frase cabe, así que tiene
    que llegar hasta el núcleo y no quedarse en el formulario."""
    sueltos = cliente.post("/api/trazos", json={"texto": "Arrels", "enlace": 0.0}).json()
    unidos = cliente.post("/api/trazos", json={"texto": "Arrels", "enlace": 0.5}).json()
    assert len(sueltos["trazos"]) > len(unidos["trazos"])


def test_no_se_puede_descargar_nada_de_fuera_de_la_carpeta_del_pedido():
    """Corre en local, pero «en local» dura hasta que alguien lo expone."""
    for intento in ("../../pyproject.toml", "..%2F..%2Fpyproject.toml"):
        assert cliente.get(f"/api/pedido/cualquiera/{intento}").status_code == 404


def test_un_texto_vacio_no_pasa_de_la_puerta():
    assert cliente.post("/api/trazos", json={"texto": "   "}).status_code == 422
    assert cliente.post("/api/trazos", json={"texto": ""}).status_code == 422


# ---------------------------------------------------------------------------
# El medidor de capacidad
# ---------------------------------------------------------------------------


def test_el_reparto_de_la_vuelta_suma_360_grados():
    """La barra del medidor se dibuja con estos dos números: si no suman la
    vuelta, enseña una proporción que no existe."""
    datos = cliente.post("/api/capacidad", json={"texto": "Arrels"}).json()
    reparto = datos["reparto"]
    assert reparto["tinta_grados"] + reparto["vuelo_grados"] == pytest.approx(360.0, abs=0.2)
    assert reparto["trazos"] >= 1


def test_el_estado_tiene_tres_valores_y_no_dos():
    """`Veredicto.apto` es un booleano honesto —no se ha encontrado ningún
    error— pero en la vista previa «no he encontrado» no es «cabe»: faltan
    por recorrer las levas recortadas. Un sí/no aquí prometería el número
    que justamente no se ha calculado."""
    assert cliente.post("/api/capacidad", json={"texto": "Arrels"}).json()["estado"] == "si"
    assert cliente.post("/api/capacidad", json={"texto": "Gracias"}).json()["estado"] == (
        "falta_medir"
    )


def test_cada_vuelo_del_lapiz_se_come_grados_de_la_vuelta():
    """Es la razón de ser del medidor: lo que decide que una frase quepa no
    es su longitud sino cuántas veces levanta el lápiz. Sin enlazar,
    «Arrels» son seis trazos; enlazado, dos."""
    sueltos = cliente.post("/api/capacidad", json={"texto": "Arrels", "enlace": 0.0}).json()
    unidos = cliente.post("/api/capacidad", json={"texto": "Arrels", "enlace": 0.5}).json()
    assert sueltos["reparto"]["vuelo_grados"] > unidos["reparto"]["vuelo_grados"]
    assert sueltos["reparto"]["tinta_grados"] < unidos["reparto"]["tinta_grados"]


def test_medir_la_capacidad_no_escribe_nada_en_disco():
    """Se llama en cada pausa al teclear. Si dejara carpetas, una tarde de
    pruebas llenaría `build/pedidos` de basura."""
    from api.main import PEDIDOS

    antes = sorted(p.name for p in PEDIDOS.iterdir()) if PEDIDOS.exists() else []
    cliente.post("/api/capacidad", json={"texto": "Montserrat"})
    despues = sorted(p.name for p in PEDIDOS.iterdir()) if PEDIDOS.exists() else []
    assert antes == despues


def test_una_frase_desbordada_no_pinta_una_barra_tranquilizadora():
    """Cuando los mínimos pasan de la vuelta, `repartir` ya no reparte:
    devuelve un corte proporcional para poder enseñar algo. Pintado como
    presupuesto sale una barra con más tinta que la de una frase que casi
    cabe, justo debajo de un «no cabe». El número que manda es cuánto piden
    los mínimos."""
    datos = cliente.post("/api/capacidad", json={"texto": "Feliz aniversari Montserrat"}).json()
    assert datos["estado"] == "no"
    assert datos["reparto"]["cabe_por_minimos"] == 0.0
    assert datos["reparto"]["necesario_grados"] > 360.0

    cabe = cliente.post("/api/capacidad", json={"texto": "Arrels"}).json()
    assert cabe["reparto"]["cabe_por_minimos"] == 1.0
    assert cabe["reparto"]["necesario_grados"] < 360.0


# ---------------------------------------------------------------------------
# Renglones: un salto de línea es un cartucho más
# ---------------------------------------------------------------------------


def test_sin_saltos_de_linea_sigue_habiendo_un_solo_cartucho():
    """El camino de siempre tiene que seguir siendo literalmente el de
    siempre: es el 90 % de los pedidos y lo vigila el golden."""
    datos = cliente.post("/api/capacidad", json={"texto": "Arrels"}).json()
    assert datos["cartuchos"] == 1
    assert datos["levas"] == 3
    assert len(datos["renglones"]) == 1


def test_cada_salto_de_linea_es_un_cartucho_y_tres_levas_mas():
    """El coste tiene que salir en la respuesta, no deducirlo quien mire:
    partir una frase no es maquetar, es fabricar otro cartucho."""
    datos = cliente.post("/api/capacidad", json={"texto": "Feliz\naniversari"}).json()
    assert datos["cartuchos"] == 2
    assert datos["levas"] == 6


def test_el_estado_del_pedido_es_el_del_peor_renglon():
    """La frase se entrega entera: que dos de tres quepan no sirve de nada.
    Aquí el primero sale limpio y el segundo no, y manda el segundo."""
    datos = cliente.post("/api/capacidad", json={"texto": "Feliz\nMontserrat"}).json()
    estados = [r["estado"] for r in datos["renglones"]]
    assert estados[0] == "si"
    assert estados[1] == "falta_medir"
    assert datos["estado"] == "falta_medir"


def test_partir_en_renglones_salva_una_frase_que_no_cabia():
    """Es para lo que existen. De una tirada, los mínimos de 22 trazos
    piden 484° y no hay reparto posible; en tres renglones, dos salen
    limpios y el tercero solo queda por medir."""
    frase = "Feliz aniversari Montserrat"
    entera = cliente.post("/api/capacidad", json={"texto": frase}).json()
    assert entera["estado"] == "no"

    partida = cliente.post("/api/capacidad", json={"texto": frase.replace(" ", "\n")}).json()
    assert partida["estado"] != "no"
    assert [r["estado"] for r in partida["renglones"]][:2] == ["si", "si"]


def test_una_linea_en_blanco_no_se_cobra_como_cartucho():
    """Tres levas lisas que no escriben nada. Lo filtra la composición, y
    aquí se comprueba que llega filtrado hasta la respuesta."""
    datos = cliente.post("/api/capacidad", json={"texto": "Arrels\n\n  \nFeliz"}).json()
    assert datos["cartuchos"] == 2


def test_el_salto_de_linea_no_se_busca_en_la_fuente():
    """La fuente no tiene «\\n» y no tiene por qué: un salto de línea es
    maquetación, no una letra. Si se comprobara con el resto del texto,
    cualquier frase de dos renglones daría «la fuente no tiene»."""
    assert cliente.post("/api/capacidad", json={"texto": "Arrels\nFeliz"}).status_code == 200


# ---------------------------------------------------------------------------
# El trazo simulado, partido
# ---------------------------------------------------------------------------


@pytest.mark.slow
def test_el_trazo_simulado_llega_partido_y_sin_rayas_inventadas():
    """`Simulacion.escritos` quita los puntos en vuelo, así que unir lo que
    queda con una polilínea traza rayas de una letra a otra que la máquina
    no dibuja; con dos renglones, una diagonal entre dos cartuchos que ni
    siquiera comparten vuelta.

    `emit.patron` ya partía el recorrido para el papel —«sin partirlo, la
    hoja mostraría líneas que la máquina no dibuja»— y lo que faltaba era
    que la pantalla mirase lo mismo. Se comprueba por dentro de cada tramo:
    entre dos puntos seguidos la punta avanza décimas, así que un salto
    grande es una raya inventada.
    """
    import itertools
    import math

    datos = cliente.post("/api/pedido", json={"texto": "Arrels\nFeliz"}).json()
    tinta = datos["simulado"]["tinta"]
    assert len(tinta) > 2, "el recorrido tiene que venir en tramos, no de una tirada"
    assert datos["simulado"]["vuelo"], "el vuelo también se dibuja, punteado"

    saltos = [math.dist(a, b) for tramo in tinta for a, b in itertools.pairwise(tramo)]
    assert max(saltos) < 2.0, f"dentro de un tramo la punta da un salto de {max(saltos):.1f} mm"


# ---------------------------------------------------------------------------
# Las marcas del enlace
# ---------------------------------------------------------------------------


def test_los_huecos_no_se_mueven_al_arrastrar_el_enlace():
    """Es lo que permite marcarlos en el deslizante. Si cambiaran, las
    marcas dirían dónde estaba cada hueco y no dónde está."""
    sueltos = cliente.post("/api/trazos", json={"texto": "Montserrat", "enlace": 0.0}).json()
    unidos = cliente.post("/api/trazos", json={"texto": "Montserrat", "enlace": 1.2}).json()
    assert sueltos["huecos"] == unidos["huecos"]
    assert len(sueltos["trazos"]) > len(unidos["trazos"])


def test_los_huecos_dicen_cuantos_trazos_van_a_salir():
    """El cruce que sostiene el medidor: el deslizante promete «uniendo
    tantos» y el motor tiene que hacer esa misma cuenta. Un hueco por
    encima del enlace queda sin unir y parte el trazo."""
    for enlace in (0.0, 0.5, 1.0, 1.2):
        datos = cliente.post("/api/trazos", json={"texto": "Montserrat", "enlace": enlace}).json()
        quedan = sum(1 for h in datos["huecos"] if h > enlace)
        assert len(datos["trazos"]) == quedan + 1, f"con enlace {enlace}"


def test_el_valle_que_publica_la_interfaz_es_el_del_nucleo():
    """La página marca el valle en el deslizante y el motor lo usa por
    defecto. Dos números iguales en dos sitios se separan: la página lee
    el del núcleo en vez de llevar su propio 0,5."""
    from core.tipografia import ENLACE

    assert cliente.get("/api/fuentes").json()["enlace"] == ENLACE


def test_la_tinta_deja_poner_en_porcentaje_lo_que_el_enlace_inventa():
    """«7 huecos forzados» suena a poco; «64 mm, el 12 % de la tinta»
    no. Sin la longitud trazada no se puede decir la segunda."""
    datos = cliente.post("/api/trazos", json={"texto": "Montserrat"}).json()
    assert datos["tinta_mm"] > 0
    # Y es una longitud de verdad, no la caja: una cursiva recorre mucho
    # más de lo que mide de ancho.
    assert datos["tinta_mm"] > datos["ancho_mm"]
