"""Que la máquina que se calcula y la que se compra sean la misma.

**Este es el fichero que justifica que las fichas existan.** El compilador
tiene los diámetros escritos como números en `Escribiente` y `Cartucho`; el
catálogo los tiene como cotas de un proveedor concreto, con su enlace. Si los
dos no coinciden, la geometría se está calculando sobre una pieza que no es
la que va a llegar en la caja.

Es exactamente el error que ya se cometió una vez: la valona del casquillo se
anotó como Ø12, acabó copiada en tres documentos y en el cálculo del hueco al
poste, y el fabricante dice Ø15. Un test que compare las dos cifras lo habría
cazado el primer día.
"""

from __future__ import annotations

import json
import math
from pathlib import Path

import pytest

from compile.conjunto import Cartucho
from compile.escribiente import Escribiente
from core.comercial import PiezaComercial

pytestmark = pytest.mark.core

CATALOGO = Path(__file__).resolve().parents[2] / "docs" / "piezas"


def pieza(nombre: str) -> PiezaComercial:
    ruta = CATALOGO / f"{nombre}.json"
    return PiezaComercial.model_validate(json.loads(ruta.read_text(encoding="utf-8")))


def cota(nombre_pieza: str, nombre_cota: str) -> float:
    return float(pieza(nombre_pieza).cota(nombre_cota).valor)


CONTRATOS = Path(__file__).resolve().parents[2] / "docs" / "contratos.json"


def contrato(nombre: str) -> float:
    """Un valor de `docs/contratos.json` por su nombre, sea del grupo que sea."""
    datos = json.loads(CONTRATOS.read_text(encoding="utf-8"))
    for grupo in datos["contratos"]:
        for valor in grupo["valores"]:
            if valor["nombre"] == nombre:
                return float(valor["valor"])
    raise KeyError(f"el contrato no declara '{nombre}'")


# ---------------------------------------------------------------------------
# Lo que el compilador supone, contra lo que dice el catálogo
# ---------------------------------------------------------------------------


def test_el_rodillo_del_calculo_es_el_rodamiento_que_se_compra():
    """`radio_rodillo` decide la curvatura mínima del perfil y si hay
    socavado. Si no fuera el radio del MR63, el perfil saldría mal cortado."""
    assert float(Escribiente().radio_rodillo) == pytest.approx(
        cota("rodillo_seguidor", "exterior") / 2.0
    )


def test_el_taladro_del_eje_es_el_arbol_que_se_compra():
    assert float(Escribiente().taladro_eje) == pytest.approx(cota("arbol_de_levas", "diametro"))


def test_el_rodamiento_del_arbol_encaja_en_el_arbol():
    """Dos piezas de catálogo entre ellas, sin pasar por el código."""
    assert cota("rodamiento_arbol", "agujero") == pytest.approx(cota("arbol_de_levas", "diametro"))


def test_el_pasador_de_indice_es_el_pasador_que_se_compra():
    assert float(Escribiente().pasador_indice) == pytest.approx(cota("pasador_indice", "diametro"))


def test_el_espesor_de_la_leva_es_el_de_la_plancha_que_se_compra():
    assert float(Escribiente().espesor_leva) == pytest.approx(cota("plancha_pom", "espesor"))


def test_el_separador_de_la_pila_es_el_que_se_compra():
    assert float(Cartucho().separador) == pytest.approx(cota("separador_pila", "espesor"))


def test_el_obstaculo_del_conjunto_es_la_valona_del_casquillo_real():
    """**El test que faltaba.** `Cartucho.radio_poste` no es el radio del
    poste: es el del obstáculo que ve la leva al girar, que es la valona del
    casquillo. Tiene que ser la del casquillo que está en el despiece."""
    assert float(Cartucho().radio_poste) == pytest.approx(cota("casquillo_pivote", "valona") / 2.0)


def test_el_casquillo_encaja_en_el_poste():
    assert cota("casquillo_pivote", "agujero") == pytest.approx(cota("poste_pivote", "diametro"))


# ---------------------------------------------------------------------------
# Coherencia interna del catálogo
# ---------------------------------------------------------------------------


def test_los_engranajes_son_del_mismo_modulo():
    """Dos engranajes de módulo distinto no engranan. Es un fallo tonto y
    caro, porque no se descubre hasta tenerlos en la mano."""
    assert cota("rueda_reductor", "modulo") == pytest.approx(cota("pinon_reductor", "modulo"))


def test_los_dientes_salen_del_diametro_exterior_y_dan_la_relacion():
    """En un engranaje recto, el exterior vale m·(Z+2). Comprobarlo cruza dos
    cotas del catálogo y confirma de paso que la reducción es 3:1.

    Va por `PiezaComercial.dientes` y no repitiendo la cuenta aquí, porque es
    la misma que escribe la fila del CSV que se importa al CAD: si el test
    tuviera su propia copia, podrían discrepar y el que se rellena a mano es
    el del CAD.
    """
    dientes_rueda = pieza("rueda_reductor").dientes
    dientes_pinon = pieza("pinon_reductor").dientes
    assert dientes_rueda == 60
    assert dientes_pinon == 20
    assert dientes_rueda / dientes_pinon == pytest.approx(3.0)


def test_el_entre_ejes_del_reductor_sale_de_las_cotas_y_cuadra_con_el_contrato():
    """m·(Z1+Z2)/2. Es la cota que el bastidor tiene que respetar, y está en
    `docs/contratos.json`: esto cruza las dos, que es lo que impide que el
    contrato siga diciendo 28 cuando alguien cambie de engranaje."""
    modulo = cota("rueda_reductor", "modulo")
    entre_ejes = modulo * (60 + 20) / 2.0
    assert entre_ejes == pytest.approx(0.028)
    assert entre_ejes == pytest.approx(contrato("reductor_entre_ejes"))


def test_el_amplificador_tiene_la_relacion_que_usa_el_compilador():
    """El cabestrante da la relación por el cociente de radios, y el
    compilador la usa como escalar. Si el contrato y `Escribiente` dejaran de
    coincidir, la leva se sintetizaría para una amplificación que la máquina
    no hace."""
    sector = contrato("amplificador_sector_radio")
    tambor = contrato("amplificador_tambor_radio")
    assert sector / tambor == pytest.approx(Escribiente().relacion)
    assert sector / tambor == pytest.approx(contrato("relacion_varillaje"))


def test_la_cinta_no_toca_ni_las_levas_vecinas_ni_el_sector_de_al_lado():
    """Dos holguras de conjunto que ninguna envolvente de C3 mira.

    Los sectores van en los postes, a 123,085 mm entre vecinos, así que dos
    de radio 48 dejan 27 mm. Y el entre-ejes tiene que superar la suma de
    radios o el sector y el tambor se tocarían en vez de tangentear."""
    sector = contrato("amplificador_sector_radio")
    tambor = contrato("amplificador_tambor_radio")
    entre_ejes = contrato("amplificador_entre_ejes")
    radio_poste = contrato("poste_radio_al_arbol")
    entre_postes = 2.0 * radio_poste * math.sin(contrato("poste_reparto") / 2.0)
    assert entre_postes - 2.0 * sector > contrato("holgura_minima")
    assert entre_ejes - (sector + tambor) > contrato("holgura_minima")


def test_la_pila_del_cartucho_sale_de_las_piezas_reales():
    """Tres levas del espesor de la plancha más dos separadores. Es el
    contrato de eje comprobado contra el catálogo en vez de contra sí mismo."""
    altura = 3.0 * cota("plancha_pom", "espesor") + 2.0 * cota("separador_pila", "espesor")
    assert altura == pytest.approx(0.019)


def test_el_pasador_atraviesa_la_pila_entera():
    """**Este test encontró un fallo de despiece.**

    El contrato de fase promete que las tres levas quedan caladas entre sí
    por un solo pasador. La pila mide 19 mm y el pasador elegido era de 16:
    no llegaba a la tercera leva. No se habría visto hasta montarlo, porque
    en el plano cada leva lleva su taladro y parecen bien.

    Ahora el pasador es de 24 y le sobran 5 mm para el plato de arrastre.
    """
    pila = 3.0 * cota("plancha_pom", "espesor") + 2.0 * cota("separador_pila", "espesor")
    largo = cota("pasador_indice", "longitud")
    assert largo > pila, f"el pasador de {largo * 1000:.0f} mm no cala la pila de {pila * 1000:.0f}"
    assert largo - pila >= 0.004, "no queda pasador suficiente para el plato de arrastre"
