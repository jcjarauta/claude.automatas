"""El paquete de importación al CAD.

Lo que se comprueba no es que los archivos existan: es que **el paquete diga
en qué orden se usan**. Todo lo que lleva dentro existía ya, repartido en
tres comandos que escribían en tres sitios, y por eso nadie lo usaba. Un
montón de archivos sin orden no es un paquete de importación.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.exportar_para_cad import main


@pytest.fixture
def paquete(tmp_path: Path) -> Path:
    assert main(["demo/hola.json", "--out", str(tmp_path)]) == 0
    return tmp_path


def test_lleva_las_cotas_que_comparten_el_compilador_y_el_cad(paquete: Path):
    fs = (paquete / "variables.fs").read_text(encoding="utf-8")
    assert "export const eje_diametro" in fs
    assert "NO EDITAR AQUI" in fs, "sin esto alguien las edita dentro del CAD"
    assert (paquete / "variables.csv").exists()


def test_los_bocetos_del_cartucho_van_sin_rotulo(paquete: Path):
    """El `TEXT` de DXF no es una entidad de boceto: el CAD importa bien la
    geometría y suelta un «no se ha podido importar la entidad desconocida».
    El aviso confunde, y el rótulo en el CAD no sirve para nada."""
    import ezdxf

    dxfs = sorted((paquete / "cartucho").glob("*.dxf"))
    assert len(dxfs) == 3
    for ruta in dxfs:
        tipos = {e.dxftype() for e in ezdxf.readfile(ruta).modelspace()}
        assert "TEXT" not in tipos, f"{ruta.name} lleva rótulo"
        assert tipos, f"{ruta.name} salió vacío"


def test_el_calaje_viaja_con_el_paquete(paquete: Path):
    """Montar un brazo al ángulo equivocado escribe basura, y es un error que
    no se ve hasta que la máquina dibuja."""
    calajes = (paquete / "calajes.md").read_text(encoding="utf-8")
    for brazo in ("izquierdo", "derecho", "elevador"):
        assert brazo in calajes


def test_la_hoja_de_ruta_dice_el_orden_y_de_quien_es_cada_pieza(paquete: Path):
    guia = (paquete / "README.md").read_text(encoding="utf-8")
    assert "1. **Pega `variables.fs`" in guia
    assert "un solo sentido" in guia, "hay que decir que lo editado en el CAD se pierde"
    assert "La plataforma se dibuja dentro del CAD" in guia


def test_un_pedido_que_no_cabe_escribe_el_paquete_pero_avisa(tmp_path: Path):
    """Mismo criterio que el CLI: los archivos se escriben igual, porque un
    pedido que no cabe también hay que poder mirarlo, pero el código de
    salida dice que no se fabrica."""
    from tests.casos import apretada

    entrada = tmp_path / "apretada.json"
    entrada.write_text(
        json.dumps(
            {
                "nombre": "apretada",
                "trazos": [
                    [[x * 1000.0, y * 1000.0] for x, y in t.coordenadas] for t in apretada().trazos
                ],
            }
        ),
        encoding="utf-8",
    )
    salida = tmp_path / "fuera"
    assert main([str(entrada), "--out", str(salida)]) == 1
    assert (salida / "README.md").exists()
