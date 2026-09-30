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
    assert "1. **Monta la biblioteca de materiales**" in guia
    assert "2. **Importa `variables.csv`" in guia
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


def test_la_tabla_de_materiales_sale_de_core(paquete: Path):
    """La misma tabla con la que el compilador calcula la masa. Si el CAD
    usara otras densidades, la masa del modelo y la del polígono discreparían
    y no habría forma de saber cuál miente."""
    from core.solido import DENSIDADES

    materiales = (paquete / "materiales.csv").read_text(encoding="utf-8")
    assert materiales.startswith("Category,Name,Density [kg/m^3]")
    for nombre, densidad in DENSIDADES.items():
        assert f",{nombre},{densidad:.0f}" in materiales


def test_las_cotas_comerciales_viajan_para_poder_dibujarlas(paquete: Path):
    """Sin esto, una pieza comercial solo puede entrar como STEP mudo: un
    cambio de referencia no movería nada."""
    piezas = (paquete / "piezas.csv").read_text(encoding="utf-8")
    assert "casquillo_pivote_valona,15.0000,mm" in piezas
    assert "rodillo_seguidor_exterior,6.0000,mm" in piezas
    assert piezas.count("\n") > 40


def test_las_variables_van_partidas_por_unidad(paquete: Path):
    """**El CAD aplica un único factor de conversión a todo el archivo que
    importa.** Con las 29 cotas en un solo CSV, o los cinco ángulos entran
    como milímetros o las veinte longitudes como grados. Y un calaje leído
    como milímetros no da un aviso: da una máquina que escribe torcido.

    Quien sabe de qué unidad es cada cota es el contrato, no quien marca
    casillas en una interfaz."""
    cota = (paquete / "variables_cota.csv").read_text(encoding="utf-8")
    angulo = (paquete / "variables_angulo.csv").read_text(encoding="utf-8")
    numero = (paquete / "variables_num.csv").read_text(encoding="utf-8")

    assert "radio_base,55.0000,mm" in cota
    assert "calaje_izquierdo" in angulo
    assert "relacion_varillaje" in numero
    # y ninguna se cuela en el archivo de otra unidad
    assert "calaje_izquierdo" not in cota
    assert "radio_base" not in angulo


def test_un_csv_que_se_importa_no_lleva_cabecera_ni_comentarios(paquete: Path):
    """**Lo que rompía la importación en Onshape.**

    El Variable Studio lee «todos los valores» sin saber que la primera fila
    es un rótulo, así que la cabecera entra en el mapa como una clave
    `nombre` cuyo valor es el texto `valor`. Con el factor de conversión
    puesto, multiplicar ese texto por 1 mm **hace fallar la regeneración de
    toda la variable**, y el error que sale no menciona la cabecera.

    Un «#» al principio tampoco es un comentario para el CAD: es otra fila.
    """
    for nombre in ("variables_cota.csv", "variables_angulo.csv", "piezas_cota.csv"):
        primera = (paquete / nombre).read_text(encoding="utf-8").split("\n")[0]
        assert not primera.startswith("#"), f"{nombre} empieza por comentario"
        assert not primera.startswith("nombre,"), f"{nombre} lleva cabecera"
        assert primera.split(",")[2] in ("mm", "deg", ""), f"{nombre}: la fila 0 no es un dato"


def test_los_archivos_legibles_si_llevan_cabecera(paquete: Path):
    """Los que no se importan se leen, y sin cabecera no se entienden."""
    for nombre in ("variables.csv", "piezas.csv", "materiales.csv"):
        primera = (paquete / nombre).read_text(encoding="utf-8").split("\n")[0]
        assert primera.startswith(("nombre,", "Category,")), f"{nombre} sin cabecera"


def test_una_tolerancia_con_coma_no_parte_la_fila():
    """La del pasador de índice es «m6 en el plato metálico, deslizante en el
    POM». Sin comillas parte la fila en dos columnas de más, y no se veía
    porque las dos primeras —que son las que el CAD lee— quedaban en su
    sitio."""
    import csv as _csv
    import io

    from compile.contratos import cargar
    from scripts.exportar_variables import csv as exportar

    for fila in _csv.reader(io.StringIO(exportar(cargar()))):
        assert len(fila) == 7, f"fila con {len(fila)} columnas: {fila}"


def test_una_unidad_desconocida_se_queja_en_vez_de_colarse():
    """Si mañana un contrato trae newtons, tiene que saltar al exportar y no
    acabar en el archivo de los milímetros."""
    from scripts.exportar_para_cad import por_unidad

    with pytest.raises(ValueError, match="newton"):
        por_unidad("nombre,valor,unidad\nempuje,12,newton\n")


def test_cada_cota_circular_tiene_sus_dos_formas(paquete: Path):
    """**Onshape acota el diámetro por defecto.** Meter `#cota.radio_base` en
    una cota de diámetro da una leva de 27,5 mm en vez de 55: la mitad, y sin
    un solo aviso. Con las dos formas no hay nada que recordar ni nada que
    multiplicar — se escribe la que pida el campo.

    Mismo patrón que el pasador de índice: no hacer el error improbable,
    hacerlo imposible."""
    filas = dict((f[0], float(f[1])) for f in _leer(paquete / "variables_cota.csv"))
    assert filas["radio_base"] == pytest.approx(55.0)
    assert filas["radio_base_diametro"] == pytest.approx(110.0)
    assert filas["eje_diametro"] == pytest.approx(10.0)
    assert filas["eje_diametro_radio"] == pytest.approx(5.0)
    # Solo los gemelos: `eje_diametro` acaba en «_diametro» y es una cota
    # del contrato, no una derivada. Lo que distingue a un gemelo es que su
    # base existe.
    gemelos = 0
    for nombre, valor in filas.items():
        for sufijo, factor in (("_diametro", 2.0), ("_radio", 0.5)):
            base = nombre.removesuffix(sufijo)
            if nombre.endswith(sufijo) and base in filas:
                assert valor == pytest.approx(factor * filas[base]), nombre
                gemelos += 1
    assert gemelos == 7, f"esperaba 7 cotas circulares con gemelo, hay {gemelos}"


def test_el_gemelo_dice_que_es_derivado(paquete: Path):
    """Para que nadie lo corrija a mano creyendo que es una cota del
    contrato: si el radio cambia, el diámetro sale solo."""
    for fila in _leer(paquete / "variables_cota.csv"):
        if fila[0] == "radio_base_diametro":
            assert fila[-1].startswith("derivada de radio_base")
            return
    raise AssertionError("no está el gemelo de radio_base")


def _leer(ruta: Path) -> list[list[str]]:
    import csv as _csv

    return list(_csv.reader(ruta.read_text(encoding="utf-8").splitlines()))
