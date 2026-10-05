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
