"""El plano de conjunto: que exista, que salga del contrato y que no mienta.

Es la lámina de la que cuelga el dossier de montaje, así que el fallo caro
no es que salga feo: es que se quede una pieza fuera del despiece. La que
falta en un despiece es justo la que no está encima de la mesa cuando hace
falta.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from emit.plataforma import LISTADO, contrato_mm
from scripts.dibujar_conjunto import alturas, despiece, main, planta, svg

pytestmark = pytest.mark.core


def test_el_despiece_lleva_todas_las_piezas_y_ninguna_de_mas():
    """El cruce de siempre: dos listas que describen lo mismo desde lados
    distintos. El despiece ordena por montaje y `LISTADO` por bucle de
    pieza, y si una entra en uno y no en el otro, salta."""
    filas = despiece()
    assert {f[1] for f in filas} == set(LISTADO)
    assert [f[0] for f in filas] == list(range(1, len(LISTADO) + 1))
    for _, pieza, cantidad, material, proceso in filas:
        assert cantidad == LISTADO[pieza].cantidad
        assert material, f"{pieza}: sin material"
        assert proceso, f"{pieza}: sin proceso"


def test_la_pila_vertical_sale_de_la_cadena_declarada():
    """Ni un número suelto: mover `base_al_plato` tiene que mover la lámina
    entera. Si alguna altura estuviera escrita a mano, aquí se quedaría."""
    c = contrato_mm()
    z = alturas(c)
    assert z["plato1"][0] == c["base_al_plato"]
    assert z["plato2"][0] - z["plato1"][1] == pytest.approx(c["poste_vano"])
    assert z["plato3"][0] - z["plato2"][1] == pytest.approx(c["reductor_bahia"])
    assert z["poste"][1] - z["poste"][0] == pytest.approx(c["poste_largo"])
    movido = alturas({**c, "base_al_plato": c["base_al_plato"] + 10.0})
    assert movido["plato3"][1] - z["plato3"][1] == pytest.approx(10.0)


def test_la_planta_sale_simetrica_respecto_del_eje():
    """El marco del cinco barras es el de la base, así que el árbol cae
    sobre el eje y los pivotes y dos de los postes salen por parejas. Si
    algún día deja de ser cierto, la lámina estaría dibujando otra máquina."""
    s = planta(contrato_mm())
    assert s["arbol"][0] == pytest.approx(0.0, abs=1e-5)
    assert s["pivote_izq"][0] == pytest.approx(-s["pivote_der"][0])
    assert s["poste1"][0] == pytest.approx(-s["poste2"][0])
    # 1e-5 y no 1e-9: el origen del marco va redondeado a nueve decimales
    # en el contrato, y a 71 mm de radio eso son medias micras.
    assert s["poste3"][0] == pytest.approx(0.0, abs=1e-5)


def test_la_lamina_rotula_solo_piezas_que_existen():
    """Un globo que nombra una pieza que no está en el listado es un globo
    que manda a buscar algo que nadie ha dibujado."""
    texto = svg()
    nombres = set(re.findall(r"\b([a-z_]+) · ×\d+", texto))
    assert nombres == set(LISTADO)


def test_se_escribe_donde_se_le_pide(tmp_path: Path):
    destino = tmp_path / "conjunto.svg"
    assert main(["--out", str(destino)]) == 0
    assert destino.read_text(encoding="utf-8").startswith("<?xml")
