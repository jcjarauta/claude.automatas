"""Qué CSV hay que reimportar.

Lo que hay que atar es que **no se quede corto**: una cota nueva que no
aparezca en `REIMPORTAR.md` se queda fuera de Onshape, y el que la teclee ve
el campo en rojo sin saber por qué. Que sobre un archivo cuesta un susto; que
falte una fila cuesta una pieza.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.csv_pendientes import IMPORTADO, estado, informe, pendientes
from scripts.exportar_para_cad import MAPAS, main
from scripts.marcar_importado import marcar

pytestmark = pytest.mark.core


@pytest.fixture
def paquete(tmp_path: Path) -> Path:
    assert main(["demo/hola.json", "--out", str(tmp_path / "paquete")]) == 0
    return tmp_path / "paquete"


@pytest.fixture
def aparte(tmp_path: Path, paquete: Path, monkeypatch) -> Path:
    """Una copia del paquete y un estado propio, para poder estropearlos.

    El estado real vive en `docs/importado.json` y dice lo que hay en el
    Onshape de verdad: un test que lo tocara dejaría al siguiente informe
    mintiendo sobre la máquina que existe.
    """
    archivo = tmp_path / "importado.json"
    archivo.write_text(IMPORTADO.read_text(encoding="utf-8"), encoding="utf-8")
    monkeypatch.setattr("scripts.csv_pendientes.IMPORTADO", archivo)
    monkeypatch.setattr("scripts.marcar_importado.IMPORTADO", archivo)
    destino = tmp_path / "cad"
    destino.mkdir()
    for f in paquete.glob("*.csv"):
        (destino / f.name).write_bytes(f.read_bytes())
    marcar(destino)
    return destino


def test_lo_que_esta_marcado_como_importado_no_sale(aparte: Path):
    """Si no ha cambiado nada, no se reimporta nada. Es la mitad del valor:
    la otra forma de equivocarse es reimportar de más."""
    assert pendientes(aparte) == []


def test_una_cota_nueva_sale_en_el_informe(aparte: Path):
    """**El fallo que no se puede permitir.** Una cota que entra al contrato y
    no al informe se queda fuera de Onshape."""
    ruta = aparte / "variables_cota.csv"
    ruta.write_text(
        ruta.read_text(encoding="utf-8") + "cota_inventada,1.0000,mm,x,y,,z\n", encoding="utf-8"
    )
    cambios = pendientes(aparte)
    assert [c.archivo for c in cambios] == ["variables_cota"]
    assert cambios[0].altas == ["cota_inventada"]
    assert "cota_inventada" in informe(cambios, MAPAS)


def test_una_cota_que_cambia_de_valor_dice_de_cuanto_a_cuanto(aparte: Path):
    """Un informe que solo diga «ha cambiado» obliga a reconstruir el porqué a
    mano, que es el trabajo que esto quita."""
    ruta = aparte / "variables_cota.csv"
    ruta.write_text(
        ruta.read_text(encoding="utf-8").replace("radio_base,55.0000", "radio_base,56.0000"),
        encoding="utf-8",
    )
    distintas = pendientes(aparte)[0].distintas
    assert ("radio_base", "55.0000", "56.0000") in distintas


def test_una_cota_que_se_va_se_dice_aparte(aparte: Path):
    """Reimportar encima NO borra la clave vieja: se queda en el mapa hasta que
    se borre la tabla entera. No rompe nada mientras nadie la referencie, pero
    hay que saberlo antes de buscar por qué existe una variable que el contrato
    ya no tiene."""
    ruta = aparte / "variables_cota.csv"
    ruta.write_text(
        "\n".join(
            x
            for x in ruta.read_text(encoding="utf-8").splitlines()
            if not x.startswith("radio_base,")
        )
        + "\n",
        encoding="utf-8",
    )
    cambios = pendientes(aparte)
    assert "radio_base" in cambios[0].bajas
    assert "se va" in informe(cambios, MAPAS)


def test_el_estado_cubre_los_cinco_csv_que_se_importan():
    """Uno que falte en `docs/importado.json` nunca saldría en el informe, y
    el que lo lee daría por bueno que no ha cambiado."""
    assert set(estado()) == set(MAPAS)


def test_el_paquete_trae_el_informe(paquete: Path):
    """Es el cuarto artefacto del bucle: sin él, qué reimportar vuelve a ser
    algo que alguien tiene que acordarse de decir."""
    assert (paquete / "REIMPORTAR.md").exists()


def test_el_estado_guarda_el_contenido_y_no_solo_el_hash():
    """Un hash dice que algo cambió y no qué."""
    datos = json.loads(IMPORTADO.read_text(encoding="utf-8"))["archivos"]
    for nombre, v in datos.items():
        assert v.get("contenido"), f"{nombre}: sin contenido no hay detalle posible"
