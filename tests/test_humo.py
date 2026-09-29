"""Que el proyecto arranca: todos los paquetes importan."""

from __future__ import annotations

import importlib

import pytest

PAQUETES = [
    "core",
    "core.cam",
    "core.actors",
    "core.energy",
    "compile",
    "emit",
    "api",
]


@pytest.mark.core
@pytest.mark.parametrize("nombre", PAQUETES)
def test_el_paquete_importa(nombre: str) -> None:
    modulo = importlib.import_module(nombre)
    assert modulo.__doc__, f"{nombre} no tiene docstring: di para qué sirve"
