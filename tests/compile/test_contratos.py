"""Los contratos como dato, y que el código no se aleje de ellos.

Hay dos clases de test aquí y la segunda es la que importa. La primera
comprueba que el fichero valida. La segunda comprueba que **el número del
contrato y el que usa el compilador son el mismo**, que es todo el motivo de
haber sacado los números de la prosa: mientras estaban escritos en markdown,
nada impedía que el código derivara y el documento siguiera diciendo lo de
antes.
"""

from __future__ import annotations

import math

import numpy as np
import pytest
from pydantic import ValidationError

from compile.conjunto import Cartucho
from compile.contratos import Contrato, Contratos, Estado, Valor, cargar
from compile.escribiente import Escribiente
from core.escritura import Capacidad
from scripts.exportar_variables import csv, featurescript

pytestmark = pytest.mark.core


@pytest.fixture(scope="module")
def contratos() -> Contratos:
    return cargar()


# ---------------------------------------------------------------------------
# El fichero
# ---------------------------------------------------------------------------


def test_el_fichero_de_contratos_valida(contratos: Contratos):
    assert contratos.version
    assert len(contratos.contratos) >= 4


def test_hay_contratos_congelados_y_alguno_pendiente(contratos: Contratos):
    """El bastidor espera a E4, y esa distinción tiene que sobrevivir al
    viaje a Onshape: un valor pendiente se dibuja, no se promete."""
    nombres = {c.nombre for c in contratos.congelados}
    assert {"eje", "fase", "calaje"} <= nombres
    assert contratos.contrato("bastidor").estado is Estado.PENDIENTE


def test_un_contrato_congelado_dice_cuando_se_congelo(contratos: Contratos):
    for contrato in contratos.congelados:
        assert contrato.congelado_el, f"'{contrato.nombre}' no dice desde cuándo"


def test_una_cota_que_no_existe_falla_en_vez_de_devolver_cero(contratos: Contratos):
    with pytest.raises(KeyError, match="no define"):
        contratos.valor("eje", "diametro_inventado")
    with pytest.raises(KeyError, match="no hay contrato"):
        contratos.valor("chasis", "lo_que_sea")


def test_los_nombres_de_variable_son_validos_para_un_cad(contratos: Contratos):
    """Van a ser nombres de variable en FeatureScript, así que nada de
    espacios, tildes ni mayúsculas."""
    for nombre in contratos.variables():
        assert nombre.isascii(), f"'{nombre}' lleva algo que no es ASCII"
        assert nombre.islower(), f"'{nombre}' lleva mayúsculas"


def test_dos_contratos_no_pueden_llamar_igual_a_dos_cosas():
    """El Variable Studio de Onshape tiene un solo espacio de nombres."""
    repetido = Valor(nombre="x", valor=1.0, unidad="m", descripcion="una")
    dos = Contratos(
        version="0.0.0",
        fecha="2026-09-30",
        contratos=[
            Contrato(nombre="a", estado=Estado.PENDIENTE, porque="a", valores=[repetido]),
            Contrato(nombre="b", estado=Estado.PENDIENTE, porque="b", valores=[repetido]),
        ],
    )
    with pytest.raises(ValueError, match="dos contratos"):
        dos.variables()


def test_una_longitud_en_radianes_no_se_convierte_a_milimetros():
    """La regla 3 en la frontera con el CAD: si la unidad no cuadra, se
    rompe en vez de devolver un número que parece bueno."""
    angulo = Valor(nombre="a", valor=1.0, unidad="rad", descripcion="un ángulo")
    with pytest.raises(ValueError, match="no en metros"):
        _ = angulo.en_mm


def test_una_fecha_mal_escrita_no_pasa():
    with pytest.raises(ValidationError):
        Contratos(version="1", fecha="30 de septiembre", contratos=[])


# ---------------------------------------------------------------------------
# Que el contrato y el código digan lo mismo
# ---------------------------------------------------------------------------


def test_el_eje_del_contrato_es_el_del_compilador(contratos: Contratos):
    assert contratos.valor("eje", "eje_diametro").metros == pytest.approx(
        float(Escribiente().taladro_eje)
    )


def test_la_pila_del_contrato_sale_de_la_geometria(contratos: Contratos):
    maquina, cartucho = Escribiente(), Cartucho()
    esperada = 3.0 * float(maquina.espesor_leva) + 2.0 * float(cartucho.separador)
    assert contratos.valor("eje", "pila_altura").metros == pytest.approx(esperada)


def test_el_pasador_del_contrato_es_el_del_compilador(contratos: Contratos):
    maquina = Escribiente()
    assert contratos.valor("fase", "pasador_diametro").metros == pytest.approx(
        float(maquina.pasador_indice)
    )
    assert contratos.valor("fase", "pasador_radio").metros == pytest.approx(
        float(maquina.radio_del_pasador)
    )


def test_el_pasador_del_contrato_atraviesa_la_pila_del_contrato(contratos: Contratos):
    """Los dos números están en el mismo fichero y tienen que ser coherentes
    entre ellos, no solo con el código."""
    assert contratos.valor("fase", "pasador_longitud").valor > (
        contratos.valor("eje", "pila_altura").valor
    )


def test_el_calaje_del_contrato_es_el_que_calcula_la_maquina(contratos: Contratos):
    """Si esto se separa, la plataforma se dibuja con el brazo a un ángulo y
    la leva se sintetiza para otro. La máquina escribiría desplazada y el
    plano diría que está bien."""
    calajes = Escribiente().calajes(Capacidad().altura_levantamiento)
    for nombre, clave in (
        ("izquierdo", "calaje_izquierdo"),
        ("derecho", "calaje_derecho"),
        ("elevador", "calaje_elevador"),
    ):
        assert contratos.valor("calaje", clave).valor == pytest.approx(calajes[nombre], abs=1e-9)


def test_el_poste_del_contrato_sale_de_la_geometria(contratos: Contratos):
    maquina = Escribiente()
    esperado = float(np.hypot(float(maquina.radio_base), float(maquina.brazo_seguidor)))
    assert contratos.valor("bastidor", "poste_radio_al_arbol").metros == pytest.approx(esperado)


def test_el_obstaculo_del_contrato_es_el_del_conjunto(contratos: Contratos):
    assert contratos.valor("bastidor", "poste_diametro").metros == pytest.approx(
        2.0 * float(Cartucho().radio_poste)
    )


def test_la_caja_de_escritura_del_contrato_es_la_del_compilador(contratos: Contratos):
    maquina = Escribiente()
    assert contratos.valor("bastidor", "caja_ancho").metros == pytest.approx(
        float(maquina.caja_ancho)
    )
    assert contratos.valor("bastidor", "caja_alto").metros == pytest.approx(
        float(maquina.caja_alto)
    )


# ---------------------------------------------------------------------------
# La exportación a Onshape
# ---------------------------------------------------------------------------


def test_el_featurescript_lleva_todas_las_variables(contratos: Contratos):
    texto = featurescript(contratos)
    for nombre in contratos.variables():
        assert f"export const {nombre} =" in texto


def test_las_longitudes_salen_en_milimetros_y_los_angulos_en_grados(contratos: Contratos):
    """La conversión ocurre en la frontera, que es aquí, y no a medias por
    el camino."""
    texto = featurescript(contratos)
    assert "export const eje_diametro = 10.0000 * millimeter;" in texto
    calaje = contratos.valor("calaje", "calaje_izquierdo")
    assert f"{math.degrees(calaje.valor):.4f} * degree" in texto


def test_el_featurescript_avisa_de_lo_que_esta_pendiente(contratos: Contratos):
    """Quien dibuja tiene que saber qué cota puede moverse cuando hable E4."""
    texto = featurescript(contratos)
    assert "PENDIENTE" in texto
    assert "no se puede prometer" in texto


def test_el_featurescript_dice_que_no_se_edita_a_mano(contratos: Contratos):
    """El flujo es de un solo sentido. Lo que se edite en Onshape se pierde
    en la siguiente regeneración y deja de coincidir con el compilador."""
    assert "NO EDITAR AQUI" in featurescript(contratos)


def test_el_csv_tiene_una_fila_por_variable_mas_la_cabecera(contratos: Contratos):
    filas = csv(contratos).strip().split("\n")
    assert len(filas) == len(contratos.variables()) + 1
