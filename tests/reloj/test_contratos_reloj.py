"""Los contratos del reloj, y que no se separen de los del escribiente.

Hay tres clases de test aquí y la segunda es la que justifica el fichero.

La primera comprueba que el fichero valida y que sus nombres sirven para un
CAD. La segunda comprueba que **las cotas que las dos máquinas comparten
dicen lo mismo en los dos ficheros**: están escritas dos veces a propósito,
porque cada máquina tiene su documento de Onshape y su tabla de variables, y
lo único que impide que deriven en silencio es esto. La tercera comprueba que
las cotas derivadas siguen saliendo de las que las generan, que es lo que se
rompe cuando alguien corrige un número a mano y se olvida de los otros tres.
"""

from __future__ import annotations

import math
from pathlib import Path

import pytest

from compile.contratos import Contratos, Estado, cargar
from scripts.exportar_variables import csv

RELOJ = Path("docs/reloj/contratos.json")

GRAVEDAD = 9.81
"""m/s². Local a propósito: el núcleo del reloj todavía no existe y este test
no debe inventarle una constante que luego no coincida con la suya."""

# Las cotas que el reloj y el escribiente comparten porque son la misma pieza
# física: el árbol del reloj tiene que entrar en el agujero del escribiente el
# día que se acoplen.
COMPARTIDAS = ("eje_diametro", "eje_sentido_horario")


@pytest.fixture(scope="module")
def reloj() -> Contratos:
    return cargar(RELOJ)


@pytest.fixture(scope="module")
def escribiente() -> Contratos:
    return cargar()


# ---------------------------------------------------------------------------
# El fichero
# ---------------------------------------------------------------------------


def test_el_fichero_del_reloj_valida(reloj: Contratos):
    assert reloj.version
    nombres = {c.nombre for c in reloj.contratos}
    assert {"oscilador", "escape", "tren", "energia", "eje"} <= nombres


def test_los_nombres_sirven_para_un_variable_studio(reloj: Contratos):
    """Un nombre con tilde o con mayúscula no es una variable de FeatureScript,
    y `variables()` además revienta si dos contratos llaman igual a dos cosas."""
    for nombre in reloj.variables():
        assert nombre.isascii(), f"'{nombre}' lleva algo que no es ASCII"
        assert nombre.islower(), f"'{nombre}' lleva mayúsculas"


def test_un_contrato_congelado_dice_cuando_se_congelo(reloj: Contratos):
    for contrato in reloj.congelados:
        assert contrato.congelado_el, f"'{contrato.nombre}' no dice desde cuándo"


# ---------------------------------------------------------------------------
# Que las dos máquinas digan lo mismo de lo que comparten
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("clave", COMPARTIDAS)
def test_el_contrato_de_eje_es_el_mismo_en_las_dos_maquinas(
    clave: str, reloj: Contratos, escribiente: Contratos
):
    """Dos tablas de variables, dos documentos de Onshape, un solo número.

    Si esto falla, alguien ha tocado el eje en un lado y no en el otro, y el
    reloj dejará de poder mover nada del escribiente sin que nada avise hasta
    que las dos piezas estén cortadas.
    """
    assert reloj.valor("eje", clave).valor == pytest.approx(
        escribiente.valor("eje", clave).valor
    ), f"'{clave}' no coincide entre {RELOJ} y el fichero del escribiente"


def test_las_dos_maquinas_no_comparten_mas_nombres_de_los_declarados(
    reloj: Contratos, escribiente: Contratos
):
    """Un nombre repetido que NO esté en COMPARTIDAS es una colisión de
    vocabulario: dos cosas distintas llamadas igual. Separar los documentos de
    Onshape protege de mezclarlas al dibujar, pero no de confundirlas al
    hablar, y esto último también cuesta dinero."""
    comunes = set(reloj.variables()) & set(escribiente.variables())
    assert comunes == set(COMPARTIDAS), (
        f"nombres compartidos sin declarar: {sorted(comunes - set(COMPARTIDAS))}"
    )


# ---------------------------------------------------------------------------
# Que las derivadas sigan saliendo de las que las generan
# ---------------------------------------------------------------------------


def test_la_longitud_del_pendulo_sale_del_periodo(reloj: Contratos):
    """Es la raíz de la cadena causal entera: si estas dos se separan, el
    reloj se diseña para un periodo y anda a otro."""
    periodo = reloj.valor("oscilador", "periodo_pendulo").valor
    esperada = GRAVEDAD * periodo**2 / (4.0 * math.pi**2)
    assert reloj.valor("oscilador", "longitud_pendulo_nominal").metros == pytest.approx(
        esperada, abs=5e-4
    )


def test_la_vuelta_de_la_rueda_de_escape_sale_de_sus_dientes(reloj: Contratos):
    """Un diente escapa por oscilación completa, no por golpe."""
    dientes = reloj.valor("escape", "dientes_escape").valor
    periodo = reloj.valor("oscilador", "periodo_pendulo").valor
    assert reloj.valor("escape", "vuelta_rueda_escape").valor == pytest.approx(dientes * periodo)


def test_el_ancora_abarca_un_medio_diente_impar(reloj: Contratos):
    """La regla no es `dientes/4 + 0,5`: es el medio diente impar **más
    próximo** a `dientes/4`. Con 30 dientes, 30/4 ya vale 7,5 y sumarle medio
    da 8, que es entero — y con un abarque entero las dos paletas trabajan en
    fase en vez de alternarse, que es justo lo que un escape no puede hacer.
    La suma solo hace falta cuando `dientes/4` cae entero, como con 32."""
    dientes = reloj.valor("escape", "dientes_escape").valor
    abarque = reloj.valor("escape", "abarque_ancora").valor
    assert abarque == pytest.approx(round(dientes / 4.0 - 0.5) + 0.5)
    assert abarque % 1.0 == pytest.approx(0.5), "un abarque entero no alterna las paletas"


def test_las_vueltas_del_tambor_salen_de_la_autonomia(reloj: Contratos):
    horas = reloj.valor("energia", "autonomia_horas").valor
    por_vuelta = reloj.valor("energia", "horas_por_vuelta_rueda_grande").valor
    assert reloj.valor("energia", "vueltas_tambor").valor == pytest.approx(horas / por_vuelta)


def test_la_cuerda_sale_de_la_caida_y_de_la_polea(reloj: Contratos):
    caida = reloj.valor("energia", "caida_disponible").metros
    ramales = reloj.valor("energia", "ramales_polea").valor
    assert reloj.valor("energia", "longitud_cuerda").metros == pytest.approx(caida * ramales)


def test_el_tambor_da_la_cuerda_en_las_vueltas_que_dice(reloj: Contratos):
    """La comprobación de conjunto del tambor: si no cuadra, el reloj se para
    antes de la autonomía prometida o la cuerda sobra y se enreda."""
    cuerda = reloj.valor("energia", "longitud_cuerda").metros
    vueltas = reloj.valor("energia", "vueltas_tambor").valor
    diametro = reloj.valor("energia", "diametro_tambor").metros
    assert math.pi * diametro * vueltas == pytest.approx(cuerda, rel=5e-3)


def test_la_tension_de_cuerda_sale_del_techo_y_no_de_la_prevision(reloj: Contratos):
    """La cuerda se compra para el techo. Dimensionarla con la previsión es
    exactamente el error que el techo existe para evitar."""
    techo = reloj.valor("energia", "masa_pesa_techo").valor
    ramales = reloj.valor("energia", "ramales_polea").valor
    assert reloj.valor("energia", "tension_cuerda_techo").valor == pytest.approx(
        techo * GRAVEDAD / ramales, rel=1e-3
    )


def test_la_prevision_de_la_pesa_cabe_bajo_el_techo(reloj: Contratos):
    assert (
        reloj.valor("energia", "masa_pesa").valor < reloj.valor("energia", "masa_pesa_techo").valor
    )


def test_la_pesa_sigue_rotulada_como_prevision(reloj: Contratos):
    """La trampa de «confundir una previsión con un precio», aplicada a una
    masa: mientras R2 no la mida, el número es nuestro y tiene que decirlo.
    Cuando se mida, se cambia el valor, se quita el rótulo y el contrato pasa
    a congelado."""
    assert reloj.contrato("energia").estado is Estado.PENDIENTE
    assert "PREVISION" in reloj.valor("energia", "masa_pesa").tolerancia


def test_los_ejes_de_salida_giran_a_lo_que_dicen(reloj: Contratos):
    """Lo que el reloj le promete a cualquier autómata que se cuelgue de él."""
    assert reloj.valor("eje", "eje_central_vueltas_por_hora").valor == pytest.approx(1.0)
    assert reloj.valor("eje", "eje_programa_vueltas_por_hora").valor == pytest.approx(1.0 / 24.0)


# ---------------------------------------------------------------------------
# La exportación
# ---------------------------------------------------------------------------


def test_el_csv_del_reloj_tiene_una_fila_por_variable(reloj: Contratos):
    filas = csv(reloj).strip().split("\n")
    assert len(filas) == len(reloj.variables()) + 1


def test_una_tolerancia_con_coma_no_parte_la_fila(reloj: Contratos, escribiente: Contratos):
    """`m6 en el plato metálico, deslizante en el POM` lleva coma, y sin
    entrecomillar añadía una columna fantasma que Onshape importaba corrida."""
    import csv as modulo_csv

    for contratos in (reloj, escribiente):
        filas = list(modulo_csv.reader(csv(contratos).strip().split("\n")))
        anchos = {len(f) for f in filas}
        assert anchos == {7}, f"filas con un número de columnas distinto: {sorted(anchos)}"
