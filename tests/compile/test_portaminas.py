"""El portaminas decide dónde va el plato 1.

El portalápiz agarra una franja fija del lápiz —del pie del tubo de la punta
al tope de la pinza— y esa franja tiene que caer sobre el plástico liso: ni
sobre el agarre metálico de delante, que es más gordo y moleteado, ni sobre
el clip de arriba. Con la punta sobre el papel, eso es una ventana para
`base_al_plato`.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from compile.contratos import cargar
from compile.portaminas import Portaminas, recomendar, ventana

PIEZAS = Path(__file__).resolve().parents[2] / "docs" / "piezas"


def _contrato_mm():
    return {
        k: v.valor * (1000.0 if v.unidad == "m" else 1.0) for k, v in cargar().variables().items()
    }


def test_la_ventana_sale_del_agarre_y_del_clip():
    c = _contrato_mm()
    lapiz = Portaminas(longitud=150.0, cuerpo=8.0, agarre=40.0, clip=50.0, agarre_diametro=9.0)
    v = ventana(lapiz, c)
    # Abajo: la pinza tiene que librar el agarre con holgura_minima; el tubo
    # pasa por encima del agarre, que cabe por él.
    tope = c["horquilla_espesor"] + c["poste_horquilla_alto"]
    pie_de_la_pinza = tope - c["pinza_largo"]
    fin_del_agarre = c["mesa_altura"] + lapiz.agarre + c["holgura_minima"]
    assert v.minimo == pytest.approx(fin_del_agarre - pie_de_la_pinza)
    # Arriba: el tope de la pinza tiene que quedar por debajo del clip.
    pie_del_clip = c["mesa_altura"] + lapiz.longitud - lapiz.clip - c["holgura_minima"]
    assert v.maximo == pytest.approx(pie_del_clip - tope)


def test_un_clip_largo_deja_el_75_fuera():
    """El caso que obliga a medir: 150 de largo y 50 de clip ponen el máximo
    en 72, y con 75 la pinza aprieta sobre el clip."""
    c = _contrato_mm()
    v = ventana(
        Portaminas(longitud=150.0, cuerpo=8.0, agarre=40.0, clip=50.0, agarre_diametro=9.0), c
    )
    assert not v.admite(75.0)


def test_un_agarre_que_no_pasa_por_el_tubo_estrecha_la_ventana():
    """Si el agarre metálico no cabe por el tubo, el tubo también tiene que
    quedar por encima de él, y el mínimo sube."""
    c = _contrato_mm()
    fino = ventana(Portaminas(150.0, 8.0, 40.0, 50.0, agarre_diametro=9.0), c)
    gordo = ventana(Portaminas(150.0, 8.0, 40.0, 50.0, agarre_diametro=10.5), c)
    assert gordo.minimo > fino.minimo
    assert gordo.maximo - gordo.minimo < 2.0, "con 150 de largo y 50 de clip queda 1 mm"


def test_sin_ventana_no_hay_recomendacion():
    c = _contrato_mm()
    with pytest.raises(ValueError, match="no cabe"):
        recomendar(Portaminas(120.0, 8.0, 60.0, 40.0, agarre_diametro=9.0), c, actual=75.0)


def test_se_recomienda_lo_mas_cerca_de_lo_que_hay():
    """Mover el plato 1 mueve la máquina entera: se recomienda el valor de la
    ventana más cercano al actual, que con 75 dentro no cambia nada."""
    c = _contrato_mm()
    holgado = Portaminas(longitud=170.0, cuerpo=8.0, agarre=30.0, clip=40.0, agarre_diametro=9.0)
    assert recomendar(holgado, c, actual=75.0) == pytest.approx(75.0)
    justo = Portaminas(longitud=150.0, cuerpo=8.0, agarre=40.0, clip=50.0, agarre_diametro=9.0)
    assert recomendar(justo, c, actual=75.0) == pytest.approx(ventana(justo, c).maximo)


def test_un_cuerpo_que_no_pasa_por_el_tubo_no_vale():
    c = _contrato_mm()
    with pytest.raises(ValueError, match="tubo"):
        ventana(
            Portaminas(longitud=150.0, cuerpo=10.5, agarre=40.0, clip=50.0, agarre_diametro=9.0), c
        )


def test_el_contrato_cuadra_con_el_portaminas_medido():
    """Mientras el portaminas esté sin medir no hay nada que cruzar: la pinza
    lleva el nominal y `base_al_plato` sus 75. En cuanto el catálogo traiga
    las cuatro medidas, el contrato tiene que estar dentro de la ventana y
    la pinza al cuerpo medido."""
    ficha = json.loads((PIEZAS / "portaminas.json").read_text(encoding="utf-8"))
    cotas = {k["nombre"]: k for k in ficha["cotas"]}
    if "SIN MEDIR" in cotas["cuerpo"]["tolerancia"] or not {
        "agarre",
        "clip",
        "agarre_diametro",
    } <= set(cotas):
        pytest.skip("el portaminas está sin medir: scripts/medir_portaminas.py")
    c = _contrato_mm()
    lapiz = Portaminas.del_catalogo(ficha)
    assert ventana(lapiz, c).admite(c["base_al_plato"])
    assert c["pinza_agujero_diametro"] == pytest.approx(lapiz.cuerpo + 0.1)


def test_medir_escribe_todo_lo_que_cuelga(tmp_path):
    """El script, sobre copias: con un portaminas medido cierra la pinza, el
    plato 1, el poste y el tirante, y el catálogo deja de decir SIN MEDIR."""
    import shutil

    from compile.levantamiento import tirante_largo
    from scripts.medir_portaminas import aplicar

    raiz = Path(__file__).resolve().parents[2]
    contratos = tmp_path / "contratos.json"
    shutil.copy(raiz / "docs" / "contratos.json", contratos)
    piezas = tmp_path / "piezas"
    piezas.mkdir()
    for n in ("portaminas", "poste_pivote"):
        shutil.copy(PIEZAS / f"{n}.json", piezas / f"{n}.json")

    lapiz = Portaminas(longitud=152.0, cuerpo=8.1, agarre=38.0, clip=50.0, agarre_diametro=9.0)
    antes = _contrato_mm()
    esperado = recomendar(lapiz, antes, antes["base_al_plato"])
    elegido = aplicar(lapiz, contratos, piezas, hoy="2026-10-04")
    c = {k: v.valor * 1000.0 for k, v in cargar(contratos).variables().items() if v.unidad == "m"}
    assert c["base_al_plato"] == pytest.approx(elegido)
    assert c["base_al_plato"] == pytest.approx(esperado)
    assert c["pinza_agujero_diametro"] == pytest.approx(8.2)
    assert c["tirante_largo"] == pytest.approx(tirante_largo(cargar(contratos)) * 1000.0)
    ficha = json.loads((piezas / "portaminas.json").read_text(encoding="utf-8"))
    assert all("SIN MEDIR" not in k["tolerancia"] for k in ficha["cotas"])
    poste = json.loads((piezas / "poste_pivote.json").read_text(encoding="utf-8"))
    largo = next(k for k in poste["cotas"] if k["nombre"] == "longitud")["valor"] * 1000.0
    assert largo == pytest.approx(c["poste_largo"])


def test_con_el_portaminas_estimado_se_toma_el_centro():
    """Con números estimados se elige el centro de la ventana: es lo que deja
    sitio a los dos lados cuando llegue la pieza real."""
    c = _contrato_mm()
    lapiz = Portaminas(152.0, 8.0, 40.0, 50.0, agarre_diametro=9.0)
    v = ventana(lapiz, c)
    assert recomendar(lapiz, c, actual=75.0, modo="centro") == pytest.approx(
        (v.minimo + v.maximo) / 2
    )
