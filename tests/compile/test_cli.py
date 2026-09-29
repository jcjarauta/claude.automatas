"""Un pedido, un comando: qué archivos salen y qué dice el informe."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from compile.cli import leer_escritura, main
from compile.escribiente import Escribiente, compilar
from compile.informe import informe, resumen
from core.escritura import Escritura, Trazo
from core.units import mm

pytestmark = pytest.mark.core

DEMO = Path("demo/hola.json")


def trazo(*puntos: tuple[float, float]) -> Trazo:
    return Trazo(puntos=[(mm(x), mm(y)) for x, y in puntos])


def imposible(tmp_path: Path) -> Path:
    ruta = tmp_path / "imposible.json"
    ruta.write_text(
        json.dumps(
            {
                "nombre": "demasiado",
                "trazos": [[[i, 0], [i, 5]] for i in range(60)],
            }
        ),
        encoding="utf-8",
    )
    return ruta


# ---------------------------------------------------------------------------
# Entrada
# ---------------------------------------------------------------------------


def test_la_entrada_viene_en_milimetros():
    """El cliente dibuja en milímetros; a metros se pasa en la frontera."""
    escritura = leer_escritura(DEMO)
    assert escritura.nombre == "hola"
    assert len(escritura.trazos) == 4
    assert float(escritura.ancho) < 0.1


def test_el_demo_del_repositorio_compila():
    assert compilar(leer_escritura(DEMO)).veredicto.apto


# ---------------------------------------------------------------------------
# Salida
# ---------------------------------------------------------------------------


def test_un_comando_deja_el_paquete_entero(tmp_path: Path):
    assert main([str(DEMO), "--out", str(tmp_path)]) == 0
    for esperado in ("informe.md", "plantillas.pdf", "programa.json"):
        assert (tmp_path / esperado).exists(), f"falta {esperado}"
    assert len(list(tmp_path.glob("*.dxf"))) == 3


def test_sin_dxf_solo_sale_el_papel(tmp_path: Path):
    main([str(DEMO), "--out", str(tmp_path), "--sin-dxf"])
    assert (tmp_path / "plantillas.pdf").exists()
    assert list(tmp_path.glob("*.dxf")) == []


def test_el_programa_guardado_se_puede_volver_a_leer(tmp_path: Path):
    """Es el contrato de datos de E1: el programa viaja en JSON."""
    from core.program import Programa

    main([str(DEMO), "--out", str(tmp_path)])
    datos = json.loads((tmp_path / "programa.json").read_text(encoding="utf-8"))
    vuelta = Programa.model_validate(datos)
    assert vuelta.canales == {"punta.x", "punta.y", "levantamiento"}


def test_la_carpeta_de_salida_se_crea_sola(tmp_path: Path):
    destino = tmp_path / "a" / "b"
    assert main([str(DEMO), "--out", str(destino)]) == 0
    assert (destino / "informe.md").exists()


def test_compilar_dos_veces_da_los_mismos_archivos(tmp_path: Path):
    """Regla 4: mismo input, mismo DXF, byte a byte."""
    main([str(DEMO), "--out", str(tmp_path / "uno")])
    main([str(DEMO), "--out", str(tmp_path / "otro")])
    for nombre in ("L-001.dxf", "plantillas.pdf", "informe.md", "programa.json"):
        assert (tmp_path / "uno" / nombre).read_bytes() == (tmp_path / "otro" / nombre).read_bytes()


# ---------------------------------------------------------------------------
# Un pedido que no se puede fabricar
# ---------------------------------------------------------------------------


def test_un_pedido_que_no_cabe_sale_con_codigo_uno(tmp_path: Path):
    """Así un script sabe que ese pedido no se fabrica sin leer el informe."""
    assert main([str(imposible(tmp_path)), "--out", str(tmp_path / "out")]) == 1


def test_un_pedido_que_no_cabe_escribe_el_informe_igual(tmp_path: Path):
    """Es justo cuando más falta hace."""
    destino = tmp_path / "out"
    main([str(imposible(tmp_path)), "--out", str(destino)])
    texto = (destino / "informe.md").read_text(encoding="utf-8")
    assert "NO APTO" in texto
    assert "capacidad_superada" in texto
    assert "Qué hacer" in texto


# ---------------------------------------------------------------------------
# El informe
# ---------------------------------------------------------------------------


def test_el_informe_dice_lo_que_hay_que_saber_para_montar():
    compilacion = compilar(leer_escritura(DEMO))
    texto = informe(compilacion, Escribiente())
    assert "APTO" in texto
    for nombre in compilacion.perfiles:
        assert nombre in texto
    assert "Calaje" in texto
    assert "Error máximo del trazo" in texto
    assert f"{Escribiente().relacion:g}:1" in texto


def test_el_informe_no_promete_lo_que_no_ha_medido():
    texto = informe(compilar(leer_escritura(DEMO)), Escribiente())
    assert "kerf" in texto.lower()
    assert "E4" in texto


def test_el_informe_de_un_pedido_sin_levas_no_se_rompe():
    maquina = Escribiente(caja_ancho=mm(600.0), caja_alto=mm(200.0))
    compilacion = compilar(
        Escritura(nombre="grande", trazos=[trazo((0.0, 0.0), (10.0, 10.0))]), maquina
    )
    texto = informe(compilacion, maquina)
    assert "NO APTO" in texto
    assert "ninguna leva" in texto


def test_el_resumen_cabe_en_una_linea():
    linea = resumen(compilar(leer_escritura(DEMO)))
    assert "\n" not in linea
    assert "APTO" in linea
