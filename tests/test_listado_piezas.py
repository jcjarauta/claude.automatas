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

_CONTRATO = json.loads((METODOLOGIA.parent / "contratos.json").read_text(encoding="utf-8"))


def _matriz(nombre: str) -> str:
    """El nombre sin el sufijo del gemelo. `brazo_eje_diametro_radio` y
    `brazo_eje_diametro` son la misma cota escrita para dos campos.

    Un gemelo es base + sufijo **donde la base está en el contrato**, y eso
    se mira, no se adivina. Antes se exigía que la base terminara también en
    «_radio» o «_diametro», y entonces `amplificador_sector_radio_mecanizado_
    diametro` no reducía a nada: el gemelo del canto del sector quedaba fuera
    de los dos cruces que dependen de esto.

    `_positivo` es el tercero: el gemelo de un ángulo negativo, que existe
    porque el campo de ángulo del CAD no acepta el signo.
    """
    del_contrato = {v["nombre"] for g in _CONTRATO["contratos"] for v in g["valores"]}
    for sufijo in ("_radio", "_diametro", "_positivo"):
        base = nombre.removesuffix(sufijo)
        if base != nombre and base in del_contrato:
            return base
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
    vigila quien acota.

    **Y los ángulos cuentan igual que las longitudes.** La platina es la
    primera pieza que sitúa agujeros en polares, y un ángulo que el DXF trae
    resuelto y nadie comprueba es exactamente el fallo que este cruce existe
    para cazar: el reparto a 120° se ve bien a 119 como se vería a 120.
    """
    for pieza, ficha in LISTADO.items():
        f = FICHAS[pieza]
        comprobadas = set(f.radios) | set(f.entre_centros) | set(f.segmentos)
        if f.cara_plana:
            comprobadas.add(f.cara_plana)
        if f.ranura:
            comprobadas.add(f.ranura[0])
        if f.voladizo:
            comprobadas.add(f.voladizo)
        if f.retranqueo:
            comprobadas.add(f.retranqueo)
        comprobadas |= set(f.desde_datum)
        # Un agujero en polares lo sitúan DOS cotas, y el comparador las mira
        # las dos: la distancia al centro y el ángulo desde +X.
        comprobadas |= {radio for radio, _, _ in f.polares}
        angulos = {angulo for _, angulo, _ in f.polares}
        if f.cara_plana_angulo:
            angulos.add(f.cara_plana_angulo)
        for v in ficha.variables:
            if not v.en_el_perfil:
                continue
            if v.mapa == "angulo":
                # Por la matriz, como las longitudes: el listado nombra el
                # gemelo en positivo —que es lo que se teclea— y el
                # comparador mide el ángulo con su signo.
                assert _matriz(v.nombre) in {_matriz(a) for a in angulos}, (
                    f"{pieza}: {v.nombre} se dibuja y no se comprueba"
                )
                continue
            if v.mapa != "cota":
                continue
            # El listado y la ficha pueden nombrar la misma cota por su
            # gemelo: la tabla dice el diámetro porque es lo que pide el
            # campo de un círculo, y el comparador mide el radio.
            assert _matriz(v.nombre) in {_matriz(n) for n in comprobadas}, (
                f"{pieza}: {v.nombre} se dibuja y no se comprueba"
            )


def test_la_tabla_sale_con_coma_decimal():
    """La hoja, el plano y el informe se leen en el mismo taller: un
    separador que cambia de sitio invita a leer 55.975 como cincuenta y cinco
    mil."""
    tabla = tabla_markdown()
    assert "111,95" in tabla
    assert "43,897" in tabla
    assert "55.975" not in tabla
