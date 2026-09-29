"""El paquete de fabricación: qué archivos salen y qué lleva cada uno."""

from __future__ import annotations

import hashlib
from datetime import date
from pathlib import Path

import pytest
from pypdf import PdfReader

from emit.calibracion import Eje, Instrumento, PerfilImpresora, sin_calibrar
from emit.layout import Formato
from emit.paquete import FORMATO_POR_DEFECTO, escribir_paquete, formato_del_pedido
from emit.template import PUNTOS_POR_MM
from tests.emit.piezas_de_prueba import bastidor_grande, juego_pequeno, rectangular

pytestmark = pytest.mark.core


def perfil(fx: float, fy: float) -> PerfilImpresora:
    return PerfilImpresora(
        nombre="copistería de la esquina",
        fecha=date(2026, 9, 29),
        formato=Formato.A4,
        papel="offset 80 g",
        medido_con=Instrumento.PIE_DE_REY,
        x=Eje(nominal=150.0, medidas=[150.0 / fx]),
        y=Eje(nominal=200.0, medidas=[200.0 / fy]),
    )


# ---------------------------------------------------------------------------
# Qué se escribe
# ---------------------------------------------------------------------------


def test_el_paquete_escribe_las_plantillas(tmp_path: Path):
    paquete = escribir_paquete(juego_pequeno(), tmp_path)
    assert paquete.plantillas == tmp_path / "plantillas.pdf"
    assert paquete.plantillas.exists()
    assert paquete.hojas == len(PdfReader(paquete.plantillas).pages)


def test_el_dossier_todavia_no_existe_y_se_dice(tmp_path: Path):
    """`None` es la forma honesta de decirlo. Se construye en E6."""
    assert escribir_paquete(juego_pequeno(), tmp_path).dossier is None
    assert not (tmp_path / "dossier.pdf").exists()


def test_las_plantillas_y_la_documentacion_no_comparten_archivo(tmp_path: Path):
    paquete = escribir_paquete(juego_pequeno(), tmp_path)
    assert paquete.plantillas.name == "plantillas.pdf"
    assert paquete.dossier is None or paquete.dossier != paquete.plantillas


def test_las_plantillas_declaran_su_escala_en_los_metadatos(tmp_path: Path):
    info = PdfReader(escribir_paquete(juego_pequeno(), tmp_path).plantillas).metadata
    assert info is not None
    assert "1:1" in str(info.get("/Title", ""))
    assert "100" in str(info.get("/Subject", ""))


def test_un_paquete_sin_piezas_no_es_un_paquete(tmp_path: Path):
    with pytest.raises(ValueError, match="sin piezas"):
        escribir_paquete([], tmp_path)


# ---------------------------------------------------------------------------
# El formato lo elige el pedido
# ---------------------------------------------------------------------------


def test_sin_decir_nada_sale_la_hoja_mas_pequeña_donde_todo_cabe():
    assert formato_del_pedido(juego_pequeno()) is Formato.A4
    assert formato_del_pedido([*juego_pequeno(), bastidor_grande()]) is Formato.A1


def test_lo_que_pide_el_pedido_manda():
    assert formato_del_pedido(juego_pequeno(), Formato.A2) is Formato.A2


def test_si_nada_admite_la_pieza_entera_hay_que_trocear_igual():
    """Y entonces más vale la hoja que cualquier copistería tiene a mano."""
    enorme = rectangular("tablero", "Z-1", 1500.0, 1500.0)
    assert formato_del_pedido([enorme]) is FORMATO_POR_DEFECTO


def test_el_paquete_dice_en_que_formato_salio(tmp_path: Path):
    paquete = escribir_paquete(juego_pequeno(), tmp_path, formato=Formato.A3)
    assert paquete.formato is Formato.A3
    caja = PdfReader(paquete.plantillas).pages[0].mediabox
    assert float(caja.width) / PUNTOS_POR_MM == pytest.approx(297.0, abs=1e-3)


def test_una_hoja_mayor_gasta_menos_hojas(tmp_path: Path):
    piezas = [rectangular(f"tapa {i}", f"T-{i:03d}", 90.0, 60.0) for i in range(12)]
    pequeña = escribir_paquete(piezas, tmp_path / "a", formato=Formato.A4)
    grande = escribir_paquete(piezas, tmp_path / "b", formato=Formato.A2)
    assert grande.hojas < pequeña.hojas


# ---------------------------------------------------------------------------
# Con perfil de impresora
# ---------------------------------------------------------------------------


def test_sin_perfil_no_se_corrige_nada(tmp_path: Path):
    assert escribir_paquete(juego_pequeno(), tmp_path).perfil is None


def test_con_perfil_el_paquete_dice_para_que_impresora(tmp_path: Path):
    paquete = escribir_paquete(juego_pequeno(), tmp_path, perfil=perfil(1.002, 1.004))
    assert paquete.perfil == "copistería de la esquina"


def test_el_perfil_neutro_da_el_mismo_archivo_que_no_pasar_ninguno(tmp_path: Path):
    uno = escribir_paquete(juego_pequeno(), tmp_path / "uno").plantillas.read_bytes()
    otro = escribir_paquete(
        juego_pequeno(), tmp_path / "otro", perfil=sin_calibrar()
    ).plantillas.read_bytes()
    assert hashlib.sha256(uno).hexdigest() == hashlib.sha256(otro).hexdigest()


def test_el_paquete_es_determinista(tmp_path: Path):
    huellas = {
        hashlib.sha256(
            escribir_paquete(juego_pequeno(), tmp_path / f"v{i}").plantillas.read_bytes()
        ).hexdigest()
        for i in range(3)
    }
    assert len(huellas) == 1
