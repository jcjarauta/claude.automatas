"""DXF de corte: unidades, capas, kerf y comparación byte a byte."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import ezdxf
import pytest

from core.units import a_mm, mm
from emit.dxf import CAPAS, Kerf, escribir_dxf, escribir_dxfs
from tests.emit.piezas_de_prueba import juego_pequeno, leva

pytestmark = pytest.mark.core

REFERENCIA = Path(__file__).resolve().parents[1] / "golden" / "leva.dxf"


def escribir(tmp_path: Path, kerf: Kerf | None = None) -> Path:
    return escribir_dxf(leva(), tmp_path / "leva.dxf", kerf)


def contorno(ruta: Path) -> list[tuple[float, float]]:
    espacio = ezdxf.readfile(ruta).modelspace()
    polilinea = next(e for e in espacio if e.dxftype() == "LWPOLYLINE" and e.dxf.layer == "CORTE")
    return [(p[0], p[1]) for p in polilinea.get_points("xy")]


def medidas(puntos: list[tuple[float, float]]) -> tuple[float, float]:
    xs = [p[0] for p in puntos]
    ys = [p[1] for p in puntos]
    return max(xs) - min(xs), max(ys) - min(ys)


def nominal() -> tuple[float, float]:
    """Lo que mide el contorno de corte de la leva de prueba, en mm.

    No se usa `Pieza.ancho`: esa caja incluye taladros y referencias, y aquí
    se compara contra el contorno, que es lo único que lleva la capa CORTE.
    """
    return medidas([(a_mm(x), a_mm(y)) for x, y in leva().contorno])


# ---------------------------------------------------------------------------
# El archivo
# ---------------------------------------------------------------------------


def test_el_dxf_declara_milimetros(tmp_path: Path):
    """Un DXF sin unidades lo interpreta cada programa a su manera, y la
    pieza sale a escala de pulgada sin que nadie lo note."""
    doc = ezdxf.readfile(escribir(tmp_path))
    assert doc.header["$INSUNITS"] == 4


def test_la_geometria_va_en_milimetros_y_a_tamaño_real(tmp_path: Path):
    ancho, alto = medidas(contorno(escribir(tmp_path)))
    assert (ancho, alto) == pytest.approx(nominal(), abs=1e-6)


def test_el_contorno_sale_como_polilinea_y_no_como_spline(tmp_path: Path):
    """Mucho software de láser no traga splines, o los aproxima a su manera
    y sin decirlo."""
    tipos = {e.dxftype() for e in ezdxf.readfile(escribir(tmp_path)).modelspace()}
    assert "SPLINE" not in tipos
    assert "LWPOLYLINE" in tipos


def test_cada_cosa_en_su_capa(tmp_path: Path):
    """En el láser cada capa lleva su potencia: el corte atraviesa, el
    rótulo solo marca."""
    doc = ezdxf.readfile(escribir(tmp_path))
    assert set(CAPAS) <= {capa.dxf.name for capa in doc.layers}
    usadas = {e.dxf.layer for e in doc.modelspace()}
    assert {"CORTE", "TALADRO", "REFERENCIA", "FASE", "ROTULO"} <= usadas


def test_el_contorno_esta_cerrado(tmp_path: Path):
    espacio = ezdxf.readfile(escribir(tmp_path)).modelspace()
    polilinea = next(e for e in espacio if e.dxftype() == "LWPOLYLINE" and e.dxf.layer == "CORTE")
    assert polilinea.closed


def test_el_taladro_sale_con_su_diametro(tmp_path: Path):
    circulos = [
        e
        for e in ezdxf.readfile(escribir(tmp_path)).modelspace()
        if e.dxftype() == "CIRCLE" and e.dxf.layer == "TALADRO"
    ]
    assert len(circulos) == 1
    assert circulos[0].dxf.radius == pytest.approx(4.0)


def test_el_rotulo_lleva_los_metadatos(tmp_path: Path):
    textos = [
        e.dxf.text for e in ezdxf.readfile(escribir(tmp_path)).modelspace() if e.dxftype() == "TEXT"
    ]
    assert len(textos) == 1
    for esperado in ("C-001", "leva x", "POM", "5.0 mm"):
        assert esperado in textos[0]


# ---------------------------------------------------------------------------
# Kerf
# ---------------------------------------------------------------------------


def test_sin_kerf_medido_se_corta_por_la_linea_nominal(tmp_path: Path):
    """Y se dice en el archivo, para que quien lo reciba lo sepa."""
    ancho, _ = medidas(contorno(escribir(tmp_path)))
    assert ancho == pytest.approx(nominal()[0], abs=1e-6)
    texto = next(
        e.dxf.text for e in ezdxf.readfile(escribir(tmp_path)).modelspace() if e.dxftype() == "TEXT"
    )
    assert "KERF SIN MEDIR" in texto


def test_el_kerf_agranda_el_contorno_medio_ancho_por_lado(tmp_path: Path):
    """La herramienta se lleva medio kerf a cada lado: para que la pieza
    salga a medida, el corte va por fuera."""
    nominal_ancho, nominal_alto = nominal()
    ancho, alto = medidas(contorno(escribir(tmp_path, Kerf(anchura=0.0002, medido=True))))
    assert ancho == pytest.approx(nominal_ancho + 0.2, abs=0.02)
    assert alto == pytest.approx(nominal_alto + 0.2, abs=0.02)


def test_el_kerf_encoge_los_taladros(tmp_path: Path):
    """Al revés que el contorno. Compensar los dos igual deja el agujero con
    un kerf entero de holgura."""
    ruta = escribir(tmp_path, Kerf(anchura=0.0002, medido=True))
    circulo = next(
        e
        for e in ezdxf.readfile(ruta).modelspace()
        if e.dxftype() == "CIRCLE" and e.dxf.layer == "TALADRO"
    )
    assert circulo.dxf.radius == pytest.approx(4.0 - 0.1)


def test_un_taladro_que_no_sobrevive_al_kerf_se_dice(tmp_path: Path):
    pequeño = leva()
    with pytest.raises(ValueError, match="no sobrevive"):
        escribir_dxf(pequeño, tmp_path / "x.dxf", Kerf(anchura=0.020, medido=True))


def test_el_kerf_medido_se_anota_en_el_archivo(tmp_path: Path):
    ruta = escribir(tmp_path, Kerf(anchura=0.0002, medido=True))
    texto = next(e.dxf.text for e in ezdxf.readfile(ruta).modelspace() if e.dxftype() == "TEXT")
    assert "kerf medido" in texto


def test_el_kerf_se_lee_del_banco(tmp_path: Path):
    datos = {"medido": True, "por_defecto_mm": 0.15, "materiales": {"POM 5 mm|5.0": 0.18}}
    ruta = tmp_path / "kerf.json"
    ruta.write_text(json.dumps(datos), encoding="utf-8")
    assert Kerf.desde(ruta, "POM 5 mm", 5.0).anchura == pytest.approx(0.00018)
    assert Kerf.desde(ruta, "otro", 9.0).anchura == pytest.approx(0.00015)


def test_el_banco_del_repositorio_todavia_no_tiene_kerf_medido():
    """Cuando esto falle será porque E4 ya midió, y habrá que quitarlo."""
    kerf = Kerf.desde(Path("bench/kerf.json"))
    assert not kerf.medido
    assert kerf.anchura == 0.0


# ---------------------------------------------------------------------------
# Varias piezas y determinismo
# ---------------------------------------------------------------------------


def test_un_archivo_por_pieza(tmp_path: Path):
    """En el láser cada una se corta por su cuenta, y mezclarlas obliga a
    separarlas a mano."""
    rutas = escribir_dxfs(juego_pequeno(), tmp_path)
    assert len(rutas) == 5
    assert len({r.name for r in rutas}) == 5


def test_sin_piezas_no_hay_nada_que_exportar(tmp_path: Path):
    with pytest.raises(ValueError, match="no hay piezas"):
        escribir_dxfs([], tmp_path)


def test_el_mismo_perfil_da_los_mismos_bytes(tmp_path: Path):
    """Regla 4: mismo input, mismo DXF. Sin esto no hay forma de saber si un
    pedido repetido salió igual."""
    huellas = {
        hashlib.sha256(escribir(tmp_path / f"v{i}").read_bytes()).hexdigest() for i in range(4)
    }
    assert len(huellas) == 1


@pytest.mark.golden
def test_coincide_con_la_referencia_guardada(tmp_path: Path):
    """Si el cambio es querido:  uv run python scripts/regenerar_golden.py"""
    assert REFERENCIA.exists(), f"falta {REFERENCIA.name}"
    actual = hashlib.sha256(escribir(tmp_path).read_bytes()).hexdigest()
    assert actual == hashlib.sha256(REFERENCIA.read_bytes()).hexdigest(), (
        "el DXF ya no coincide con la referencia. Si es intencionado, regenera con: "
        "uv run python scripts/regenerar_golden.py"
    )


def test_una_pieza_sin_marca_de_fase_no_dibuja_la_capa(tmp_path: Path):
    ruta = escribir_dxf(leva(marca_fase=None), tmp_path / "sin.dxf")
    usadas = {e.dxf.layer for e in ezdxf.readfile(ruta).modelspace()}
    assert "FASE" not in usadas


def test_la_carpeta_se_crea_sola(tmp_path: Path):
    assert escribir_dxf(leva(), tmp_path / "a" / "b" / "leva.dxf").exists()


def test_un_espesor_distinto_cambia_el_rotulo(tmp_path: Path):
    ruta = escribir_dxf(leva(espesor=mm(9.0)), tmp_path / "g.dxf")
    texto = next(e.dxf.text for e in ezdxf.readfile(ruta).modelspace() if e.dxftype() == "TEXT")
    assert "9.0 mm" in texto
