"""El boceto de cada pieza comercial.

**Lo que hay que atar es que el perfil dibujado y el sólido del catálogo sean
la misma forma.** Si el boceto enseñara una cosa y el STEP otra, quien dibuje
en el CAD haría una tercera, y las tres discreparían sin que nada lo dijera.
Son dos representaciones de la misma ficha y tienen que medir lo mismo.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from emit.catalogo import cargar
from scripts.dibujar_piezas import (
    SIN_MASA_FIABLE,
    caja_del_perfil,
    filas_de,
    hoja,
    main,
    perfil_de,
)

build123d = pytest.importorskip("build123d", reason="hace falta el kernel: uv sync --group cad")

from emit.catalogo import caja_envolvente  # noqa: E402


@pytest.mark.parametrize("pieza", cargar(), ids=lambda p: p.nombre)
def test_el_perfil_dibujado_mide_lo_mismo_que_el_solido(pieza):
    """El contrato entre `scripts/dibujar_piezas.py` y `emit/catalogo.py`.

    El boceto se dibuja rama por rama como el generador de sólidos, y esto es
    lo que impide que una de las dos se quede atrás cuando se toque la otra.
    """
    diametro, altura = caja_del_perfil(pieza)
    x, y, z = caja_envolvente(pieza)
    if pieza.familia.value == "material":
        return  # la plancha es un prisma, no una pieza de revolución
    assert diametro == pytest.approx(max(x, y) * 1000.0, rel=1e-6), pieza.nombre
    assert altura == pytest.approx(z * 1000.0, rel=1e-6), pieza.nombre


def test_cada_pieza_declara_al_menos_dos_cotas():
    """Un perfil con una sola cota no describe nada."""
    for pieza in cargar():
        _, usadas = perfil_de(pieza)
        assert len(usadas) >= 2, pieza.nombre


def test_la_hoja_lleva_el_nombre_entero_de_cada_variable():
    """Es para lo que se usa: se copia del papel al campo de cota. Con el
    nombre corto habría que reconstruirlo a mano, y ahí es donde se falla."""
    texto = hoja(cargar())
    assert "#pieza.rodillo_seguidor_exterior" in texto
    assert "#pieza.casquillo_pivote_valona" in texto


def test_la_hoja_lleva_toda_cota_critica_aunque_el_perfil_no_la_dibuje():
    """La envolvente de un engranaje es un disco liso, así que el **módulo**
    no sale en el dibujo. Y es el primer campo del FeatureScript. Lo que
    manda para esta hoja no es qué se ve, es qué se teclea."""
    texto = hoja(cargar())
    assert "#pieza.pinon_reductor_modulo" in texto
    assert "#pieza.portaminas_mina" in texto
    for pieza in cargar():
        variables = {v for v, _ in filas_de(pieza)}
        for c in pieza.criticas:
            assert f"{pieza.nombre}_{c.nombre}" in variables, f"{pieza.nombre}.{c.nombre}"


def test_la_hoja_lleva_los_dientes_de_cada_engranaje():
    """**El dato que faltaba y costó un piñón.** El FeatureScript de
    engranaje de Onshape no pide el diámetro exterior, que es lo que guarda
    la ficha: pide Z. Con la hoja anterior había que despejarlo de cabeza
    mientras se rellenaba el formulario, y salió un piñón de 25 dientes en
    vez de 20 —relación 2,4 en lugar de 3, entre-ejes 29,75 en vez de 28—.
    No avisa nada: el engranaje sale bonito y no encaja.
    """
    texto = hoja(cargar())
    engranajes = [p for p in cargar() if p.dientes is not None]
    assert [p.nombre for p in engranajes] == ["pinon_reductor", "rueda_reductor"]
    for pieza in engranajes:
        assert f"#pieza.{pieza.nombre}_dientes" in texto
    assert ">20<" in texto
    assert ">60<" in texto


def test_se_avisa_donde_la_masa_no_significa_nada():
    """Siete de las catorce tienen envolvente tosca a propósito. Asignarles
    material en el CAD daría un número con aspecto de medida."""
    texto = hoja(cargar())
    # Con los dos puntos: «sin material» a secas sale también en la
    # cabecera de la hoja, y contaría una de más.
    assert texto.count("sin material:") == len(SIN_MASA_FIABLE)
    for nombre in SIN_MASA_FIABLE:
        assert nombre in texto


def test_se_puede_pedir_una_sola_pieza(tmp_path: Path):
    destino = tmp_path / "una.svg"
    assert main(["--out", str(destino), "--solo", "rodillo_seguidor"]) == 0
    texto = destino.read_text(encoding="utf-8")
    assert "rodillo_seguidor" in texto
    assert "portaminas" not in texto
