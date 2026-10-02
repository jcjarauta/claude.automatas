"""El comparador, leyendo el STEP del sólido en vez del DXF del croquis.

Los dos archivos dicen cosas distintas y por eso se miran los dos. El DXF es
el croquis y llega antes, que es cuando arreglarlo es gratis. El STEP llega
después y trae lo único que un contorno no puede traer: el **espesor**.

Como en el resto del comparador, casi todo lo de aquí le pasa una pieza
estropeada a propósito y exige que la cace. Y hay un archivo **real**: el
que volvió de Onshape con dos agujeros cambiados de sitio. Un lector hecho
con expresiones regulares se cae con la primera variación de formato, y esa
variación no sale nunca en un archivo que escribo yo.
"""

from __future__ import annotations

import math
from pathlib import Path

import pytest

from emit.plataforma import contrato_mm
from scripts.comparar_dxf import comparar, informe, leer_step

pytestmark = pytest.mark.core

DATOS = Path(__file__).parent / "datos"


def _step(
    ruta: Path,
    agujeros: list[tuple[float, float, float]],
    *,
    espesor: float = 9.0,
    unidad: str = "m",
) -> Path:
    """Un STEP mínimo: los círculos de las dos caras de un disco agujereado.

    Lleva solo lo que el lector mira —puntos, ejes, círculos y el bloque de
    unidades—, porque lo que se prueba aquí es el lector y no OCCT. Los
    `agujeros` van en milímetros, como (x, y, radio); `unidad` decide si el
    archivo los declara en metros o en milímetros, que es la trampa que
    multiplica una pieza por mil sin avisar.
    """
    k = 0.001 if unidad == "m" else 1.0
    prefijo = "$" if unidad == "m" else ".MILLI."
    lineas, n = [], 100
    for x, y, r in agujeros:
        for z in (0.0, espesor):
            lineas += [
                f"#{n}=CARTESIAN_POINT('',({x * k:.12g},{y * k:.12g},{z * k:.12g}));",
                f"#{n + 1}=DIRECTION('',(0.,0.,1.));",
                f"#{n + 2}=DIRECTION('',(1.,0.,0.));",
                f"#{n + 3}=AXIS2_PLACEMENT_3D('',#{n},#{n + 1},#{n + 2});",
                f"#{n + 4}=CIRCLE('',#{n + 3},{r * k:.12g});",
            ]
            n += 5
    ruta.write_text(
        "ISO-10303-21;\nHEADER;\nENDSEC;\nDATA;\n"
        + "\n".join(lineas)
        + f"\n#9=(\nLENGTH_UNIT()\nNAMED_UNIT(*)\nSI_UNIT({prefijo},.METRE.)\n);\n"
        + "ENDSEC;\nEND-ISO-10303-21;\n",
        encoding="utf-8",
    )
    return ruta


def platina(tmp_path: Path, **kw) -> Path:
    """La platina buena, sacada del contrato igual que la saca el perfil."""
    c = contrato_mm()
    agujeros = [
        (0.0, 0.0, c["platina_diametro"] / 2),
        (0.0, 0.0, c["rodamiento_arbol_alojamiento_diametro"] / 2),
    ]
    for i in range(3):
        t = c["poste_reparto"] * i
        r = c["poste_radio_al_arbol"]
        agujeros.append((r * math.cos(t), r * math.sin(t), c["poste_eje_diametro"] / 2))
    for cota in ("platina_pivote_angulo_izquierdo", "platina_pivote_angulo_derecho"):
        t, r = c[cota], c["platina_pivote_al_arbol"]
        agujeros.append((r * math.cos(t), r * math.sin(t), c["brazo_eje_diametro"] / 2))
    t, r = c["platina_manivela_angulo"], c["reductor_entre_ejes"]
    agujeros.append(
        (
            r * math.cos(t),
            r * math.sin(t),
            c["rodamiento_arbol_alojamiento_diametro"] / 2,
        )
    )
    return _step(tmp_path / "platina.step", agujeros, **kw)


def test_el_step_de_la_platina_cuadra(tmp_path: Path):
    inf = comparar(platina(tmp_path), "platina_levas")
    assert inf.cuadra, informe(inf)


def test_el_espesor_es_lo_que_el_croquis_no_puede_traer(tmp_path: Path):
    """**El motivo de leer STEP.** Un contorno correcto extruido a lo que el
    CAD tuviera por defecto da una pieza que se ve bien y no entra en la
    pila, y el DXF no puede decir nada: el espesor no viaja en un croquis."""
    inf = comparar(platina(tmp_path, espesor=12.0), "platina_levas")
    assert not inf.cuadra
    assert any("platina_espesor" in h.texto and "12" in h.texto for h in inf.hallazgos), informe(
        inf
    )


def test_el_espesor_sale_del_archivo_y_no_de_la_ficha(tmp_path: Path):
    _, _, _, espesor = leer_step(platina(tmp_path, espesor=9.0))
    assert espesor == pytest.approx(9.0)


def test_un_step_en_milimetros_mide_lo_mismo_que_uno_en_metros(tmp_path: Path):
    """**La unidad se lee, no se supone.** Onshape exporta en metros y la
    mitad de los CAD en milímetros: dar por hecho uno de los dos multiplica
    la pieza por mil, y mil veces una cota correcta sigue pareciendo una
    cota. Es la trampa de las unidades con otro disfraz."""
    inf = comparar(platina(tmp_path, unidad="mm"), "platina_levas")
    assert inf.cuadra, informe(inf)


def test_un_step_que_no_declara_su_unidad_se_para(tmp_path: Path):
    """Antes que inventarse un factor, no leer el archivo."""
    ruta = platina(tmp_path)
    ruta.write_text(ruta.read_text(encoding="utf-8").replace("LENGTH_UNIT()", ""), encoding="utf-8")
    with pytest.raises(ValueError, match="unidad"):
        leer_step(ruta)


def test_un_solido_trae_cada_rasgo_dos_veces_y_se_compara_una_cara(tmp_path: Path):
    """Siete agujeros y un contorno son ocho círculos, no dieciséis. Contar
    las dos caras invita a buscar el error donde no está."""
    entidades, circulares, _, _ = leer_step(platina(tmp_path))
    assert entidades == {"CIRCLE": 8}
    assert len(circulares) == 8


def test_el_que_volvio_de_onshape_con_los_dos_agujeros_cambiados():
    """**El archivo real, y el fallo que justificó todo esto.**

    El tercer poste y el pivote izquierdo volvieron cada uno en el sitio del
    otro, los dos con su radio y su diámetro correctos. El dibujo se ve
    perfecto: lo que está mal es qué agujero hay en cada sitio, y eso no se
    mira, se mide.

    El informe tiene que decir **qué hay en su lugar**, no solo que falta:
    con «el peor se queda a 2,85 mm» hay que reconstruir a mano cuál de los
    cuatro agujeros es el culpable.
    """
    inf = comparar(DATOS / "platina_levas_cambiada.step", "platina_levas")
    assert not inf.cuadra
    faltan = [h.texto for h in inf.hallazgos if h.gravedad == "falta"]
    assert any("poste" in t and "Ø10" in t for t in faltan), informe(inf)
    assert any("pivote" in t and "Ø8" in t for t in faltan), informe(inf)
    # Y lo que SÍ está no se acusa de sobrar: los dos postes buenos y el
    # pivote derecho quedan situados aunque su grupo falle.
    assert sum(h.gravedad == "huerfano" for h in inf.hallazgos) == 2, informe(inf)


def test_el_que_volvio_de_onshape_bueno():
    """**El archivo real por el lado que pasa**, que es el que no se vigilaba.

    El resto de esta prueba, salvo el vecino de arriba, le da al lector STEP
    archivos que escribo yo: por construcción traen el formato que el lector
    espera, así que no dicen nada sobre si sigue entendiendo lo que exporta
    Onshape. Y un archivo roto tampoco lo dice —falla igual si el lector no
    entiende nada—.

    Lo que caza este es el fallo contrario y más silencioso: que el lector
    deje de reconocer una pieza **correcta**. Eso no rompe ningún camino de
    error; rompe el día que alguien entrega una pieza buena y el comparador
    le dice que no cuadra.
    """
    inf = comparar(DATOS / "platina_levas_buena.step", "platina_levas")
    assert inf.cuadra, informe(inf)
    # Y que pase por el motivo bueno: los ocho círculos y el espesor del
    # contrato, no una comparación que se quedó sin rasgos que mirar.
    entidades, circulares, _, espesor = leer_step(DATOS / "platina_levas_buena.step")
    assert entidades == {"CIRCLE": 8}
    assert len(circulares) == 8
    assert espesor == pytest.approx(contrato_mm()["platina_espesor"], abs=1e-6)


def test_el_mismo_archivo_real_trae_el_espesor_bueno():
    """Para que el caso de prueba no pase por el motivo equivocado: de lo
    que trae el archivo real, lo único que está mal son los dos agujeros."""
    _, _, _, espesor = leer_step(DATOS / "platina_levas_cambiada.step")
    assert espesor == pytest.approx(contrato_mm()["platina_espesor"], abs=1e-6)
