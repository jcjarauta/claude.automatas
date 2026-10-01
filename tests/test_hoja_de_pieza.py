"""La hoja de una pieza: el tercero de los tres artefactos del bucle.

`docs/metodologia.md` §2d pide por pieza un DXF, una tabla y un boceto, y dice
que no se reparten. Lo que se ata aquí es eso: que ninguna pieza salga del
paquete con dos de los tres, y que lo que la hoja dibuja sea exactamente lo
que el comparador va a mirar después.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from emit.plataforma import LISTADO, contrato_mm
from scripts.comparar_dxf import FICHAS, cotas_en_mm
from scripts.dibujar_pieza import PERFIL_DE, hoja, main

pytestmark = pytest.mark.core


def test_ninguna_pieza_sale_con_dos_de_los_tres_artefactos():
    """**La regla del bucle, hecha test.** Una pieza con DXF y sin tabla se
    dibuja tecleando números leídos del dibujo; con tabla y sin boceto se
    dibuja sin entender la pieza. Las dos cosas son de donde vienen los
    errores que este bucle existe para evitar."""
    for pieza in PERFIL_DE:
        assert pieza in LISTADO, f"{pieza}: tiene forma y no tiene tabla"
        assert pieza in FICHAS, f"{pieza}: tiene forma y nadie la comprueba"
        assert LISTADO[pieza].porque, f"{pieza}: la hoja saldría sin explicar nada"


def test_la_hoja_solo_rotula_variables_que_existen():
    """Misma regla que las demás hojas: lo que se imprime se teclea."""
    # `cotas_en_mm` solo trae longitudes, con sus gemelos; los ángulos están
    # en el contrato y no en ella, así que hacen falta los dos.
    existen = cotas_en_mm().keys() | contrato_mm().keys()
    nombres = re.findall(r"#(?:cota|angulo|num)\.([a-z0-9_]+)", hoja())
    assert len(nombres) >= 20
    for nombre in nombres:
        assert nombre in existen, nombre


def test_la_hoja_dibuja_lo_que_el_comparador_mira():
    """**La propiedad que hace útil la hoja.** Las cotas que rotula salen de
    `FICHAS`, no de una lista aparte, así que una cota que el comparador no
    vigile tampoco aparece dibujada. Si alguna vez divergen, es que alguien
    puso una cota en un sitio y no en el otro."""
    texto = hoja()
    for pieza in PERFIL_DE:
        for nombre in FICHAS[pieza].radios:
            matriz = nombre.removesuffix("_radio").removesuffix("_diametro")
            assert matriz in texto or nombre in texto, f"{pieza}: {nombre} no sale en la hoja"


def test_cada_hoja_dice_como_se_ancla_y_que_hay_que_comprobar():
    """Los dos pasos que no puede hacer el compilador: anclar y mirar que el
    croquis quede definido."""
    texto = hoja()
    assert "DATUM" in texto
    assert "DOS coincidentes" in texto
    assert "totalmente definida" in texto


def test_se_escribe_donde_se_le_pide(tmp_path: Path):
    destino = tmp_path / "pieza.svg"
    assert main(["mordaza", "--out", str(destino)]) == 0
    texto = destino.read_text(encoding="utf-8")
    assert texto.startswith("<?xml")
    assert "mordaza" in texto
    assert "eje_pivote" not in texto, "se pidió una pieza y han salido dos"


def test_cada_pieza_declara_por_donde_se_extruye():
    """**Un perfil 2D no es una pieza.** Sin la tercera dimensión la hoja
    enseña un contorno y el espesor se queda en la tabla, que es donde menos
    se mira; y un espesor que no se ve en el dibujo se extruye al que tenga
    puesto el CAD por defecto."""
    cotas = contrato_mm()
    for pieza, ficha in LISTADO.items():
        clase, cota = ficha.solido
        assert clase in ("plancha", "barra"), f"{pieza}: sólido «{clase}»"
        assert cota in cotas, f"{pieza}: {cota} no está en el contrato"


def test_la_hoja_dibuja_las_dos_vistas():
    texto = hoja()
    assert "planta" in texto
    assert "sección A-A" in texto, "falta la sección de las planchas"
    assert "alzado" in texto, "falta el alzado de las barras"


def test_la_hoja_acota_todo_lo_que_la_ficha_declara():
    """No las principales: **todas**. Lo que no aparece dibujado se teclea de
    la tabla sin saber a qué rasgo corresponde."""
    for pieza in PERFIL_DE:
        texto, f = hoja([pieza]), FICHAS[pieza]
        esperadas = set(f.segmentos) | set(f.entre_centros)
        if f.cara_plana:
            esperadas.add(f.cara_plana)
        if f.ranura:
            esperadas.add(f.ranura[0])
        esperadas.add(LISTADO[pieza].solido[1])
        for cota in esperadas:
            assert f"#cota.{cota}" in texto, f"{pieza}: {cota} no está acotada en el boceto"
