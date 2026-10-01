"""El listado de piezas y variables de `docs/metodologia.md`.

Una tabla de variables en un documento es un artefacto que alguien teclea,
así que vale lo mismo que una hoja de bocetos: si dice una cota que no
existe, o un valor que ya no es, no se entera nadie hasta que hay una pieza
cortada. Aquí se cruza contra el contrato y contra el propio código.
"""

from __future__ import annotations

import json

import pytest

from emit.plataforma import LISTADO, contrato_mm, tabla_markdown
from scripts.comparar_dxf import FICHAS, cotas_en_mm
from scripts.listado_piezas import METODOLOGIA, con_listado

pytestmark = pytest.mark.core


def _matriz(nombre: str) -> str:
    """El nombre sin el sufijo del gemelo. `brazo_eje_diametro_radio` y
    `brazo_eje_diametro` son la misma cota escrita para dos campos."""
    for sufijo in ("_radio", "_diametro"):
        if nombre.endswith(sufijo) and nombre.removesuffix(sufijo).endswith(
            ("_radio", "_diametro")
        ):
            return nombre.removesuffix(sufijo)
    return nombre


def test_el_documento_esta_al_dia():
    """**El test que justifica generar la tabla.** Si alguien toca el contrato
    o `LISTADO` y no regenera, esto lo dice; sin él, generar la tabla solo
    cambia dónde envejece.

    Se arregla con `uv run python scripts/listado_piezas.py --escribir`.
    """
    actual = METODOLOGIA.read_text(encoding="utf-8")
    assert actual == con_listado(actual), (
        "docs/metodologia.md no coincide con emit.plataforma.LISTADO; "
        "regenera con scripts/listado_piezas.py --escribir"
    )


def test_toda_variable_del_listado_existe_y_se_puede_teclear():
    """Misma regla que las hojas: lo que se imprime se teclea, así que tiene
    que existir en el CSV que se importa. Los gemelos cuentan, que son los que
    hay que escribir en un campo de radio."""
    cotas = cotas_en_mm()
    for pieza, ficha in LISTADO.items():
        for v in ficha.variables:
            assert v.mapa in ("cota", "angulo", "num"), f"{pieza}: mapa «{v.mapa}»"
            assert v.nombre in cotas or v.nombre in contrato_mm(), f"{pieza}: {v.nombre}"


def test_los_angulos_no_se_cuelan_en_el_mapa_de_milimetros():
    """Un calaje tecleado como milímetros no da un aviso: da una máquina que
    escribe torcido. El prefijo de la tabla es lo único que lo separa, y sale
    de `LISTADO` a mano, así que se cruza contra la unidad del contrato."""
    datos = json.loads((METODOLOGIA.parent / "contratos.json").read_text(encoding="utf-8"))
    unidad = {v["nombre"]: v["unidad"] for g in datos["contratos"] for v in g["valores"]}
    for pieza, ficha in LISTADO.items():
        for v in ficha.variables:
            esperada = unidad.get(v.nombre) or unidad.get(_matriz(v.nombre))
            assert esperada is not None, f"{pieza}: {v.nombre} no está en el contrato"
            assert (v.mapa == "angulo") == (esperada == "rad"), f"{pieza}: {v.nombre}"


def test_cada_pieza_con_ficha_de_comparador_esta_en_el_listado():
    """Las dos listas describen las mismas piezas desde lados distintos —una
    para comprobar, otra para teclear—. Una pieza en una y no en la otra es
    una que se dibuja sin guía o que se comprueba sin que nadie la dibuje."""
    assert set(LISTADO) == set(FICHAS)


def test_toda_cota_que_el_perfil_resuelve_la_comprueba_el_comparador():
    """Lo que el DXF trae resuelto tiene que estar vigilado: es geometría que
    nadie va a volver a mirar. Lo que no trae —espesor, calaje— se teclea y lo
    vigila quien acota."""
    for pieza, ficha in LISTADO.items():
        f = FICHAS[pieza]
        comprobadas = set(f.radios) | set(f.entre_centros) | set(f.segmentos)
        if f.cara_plana:
            comprobadas.add(f.cara_plana)
        if f.ranura:
            comprobadas.add(f.ranura[0])
        if f.voladizo:
            comprobadas.add(f.voladizo)
        for v in ficha.variables:
            if not (v.en_el_perfil and v.mapa == "cota"):
                continue
            # El listado y la ficha pueden nombrar la misma cota por su
            # gemelo: la tabla dice el diámetro porque es lo que pide el
            # campo de un círculo, y el comparador mide el radio.
            assert _matriz(v.nombre) in {_matriz(n) for n in comprobadas}, (
                f"{pieza}: {v.nombre} se dibuja y no se comprueba"
            )


def test_la_tabla_sale_con_coma_decimal():
    """La hoja, el plano y el informe se leen en el mismo taller: un
    separador que cambia de sitio invita a leer 47.975 como cuarenta y siete
    mil."""
    tabla = tabla_markdown()
    assert "47,975" in tabla
    assert "47.975" not in tabla
