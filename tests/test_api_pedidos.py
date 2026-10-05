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
