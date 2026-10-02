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

from compile.contratos import Contratos, Estado, Valor, cargar
from scripts.exportar_variables import (
    UNIDADES,
    Tipo,
    conversion_de,
    convertir,
    csv,
    csv_por_tipo,
    featurescript,
)

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
    autonomia = reloj.valor("energia", "autonomia").valor
    por_vuelta = reloj.valor("energia", "periodo_rueda_grande").valor
    assert reloj.valor("energia", "vueltas_tambor").valor == pytest.approx(autonomia / por_vuelta)


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
        assert anchos == {10}, f"filas con un número de columnas distinto: {sorted(anchos)}"


# ---------------------------------------------------------------------------
# Unidades y tipos: que ninguna magnitud nueva salga como número pelado
# ---------------------------------------------------------------------------


def test_todas_las_unidades_del_reloj_saben_convertirse(reloj: Contratos):
    """El reloj trajo `s`, `kg` y `N`, que el escribiente no tenía.

    Antes de la tabla de conversión los tres salían como un número sin
    unidad, indistinguibles de un número de dientes. Esto es lo que impide
    que vuelva a pasar con la siguiente magnitud que aparezca.
    """
    for contrato in reloj.contratos:
        for valor in contrato.valores:
            assert valor.unidad in UNIDADES, (
                f"'{valor.nombre}' usa '{valor.unidad}', que el exportador no convierte"
            )


def test_una_unidad_desconocida_revienta_en_vez_de_colarse():
    """Pasar por adimensional sin avisar es peor que fallar: el número llega
    al CAD con pinta de cota buena."""
    inventada = Valor(nombre="x", valor=1.0, unidad="furlong", descripcion="una")
    with pytest.raises(ValueError, match=r"no sabe convertir|furlong"):
        conversion_de(inventada)


def test_cada_magnitud_cae_en_el_tipo_que_le_toca(reloj: Contratos):
    esperado = {
        "longitud_pendulo_nominal": Tipo.LENGTH,
        "eje_diametro": Tipo.LENGTH,
        "amplitud_nominal": Tipo.ANGLE,
        "dientes_escape": Tipo.NUMBER,
        "vueltas_tambor": Tipo.NUMBER,
        "periodo_pendulo": Tipo.REFERENCIA,
        "masa_pesa": Tipo.REFERENCIA,
        "tension_cuerda_techo": Tipo.REFERENCIA,
    }
    por_nombre = {v.nombre: v for c in reloj.contratos for v in c.valores}
    for nombre, tipo in esperado.items():
        assert conversion_de(por_nombre[nombre]).tipo is tipo, f"'{nombre}' no es {tipo}"


def test_el_factor_convierte_de_verdad(reloj: Contratos):
    """La columna `factor` está para poder auditar la conversión: el valor
    del contrato por el factor tiene que dar el valor de la tabla."""
    for contrato in reloj.contratos:
        for valor in contrato.valores:
            cifra, conversion = convertir(valor)
            assert float(cifra) == pytest.approx(valor.valor * conversion.factor, rel=1e-6)


def test_el_metro_sale_en_milimetros_y_el_radian_en_grados(reloj: Contratos):
    assert UNIDADES["m"].factor == pytest.approx(1000.0)
    assert UNIDADES["m"].simbolo == "mm"
    assert UNIDADES["rad"].factor == pytest.approx(180.0 / math.pi)
    assert UNIDADES["rad"].simbolo == "deg"


def test_una_autonomia_larga_se_lee_en_horas_y_un_periodo_corto_en_segundos(reloj: Contratos):
    """108.000 s es correcto y no lo lee nadie. La elección de unidad legible
    es presentación, así que vive en la frontera y no en el contrato, que
    guarda SI."""
    autonomia = reloj.valor("energia", "autonomia")
    cifra, conversion = convertir(autonomia)
    assert conversion.simbolo == "h"
    assert float(cifra) == pytest.approx(30.0)

    periodo = reloj.valor("oscilador", "periodo_pendulo")
    cifra, conversion = convertir(periodo)
    assert conversion.simbolo == "s"
    assert float(cifra) == pytest.approx(2.0)


# ---------------------------------------------------------------------------
# Que lo que no dimensiona no pueda dimensionar
# ---------------------------------------------------------------------------


def test_una_masa_no_entra_como_cota_en_el_featurescript(reloj: Contratos):
    """Acotar un boceto con `#masa_pesa` no da ningún error en Onshape, y esa
    es justo la razón de que las magnitudes de referencia salgan como
    comentario y no como `export const`."""
    texto = featurescript(reloj, maquina="el reloj", fuente=str(RELOJ))
    for contrato in reloj.contratos:
        for valor in contrato.valores:
            declarada = f"export const {valor.nombre} =" in texto
            assert declarada is conversion_de(valor).tipo.dimensiona, (
                f"'{valor.nombre}' está del lado equivocado del FeatureScript"
            )
    assert "NO DIMENSIONA NADA" in texto
    assert "// masa_pesa = 3.5 kg" in texto


def test_lo_que_dimensiona_sigue_estando_entero(reloj: Contratos):
    texto = featurescript(reloj, maquina="el reloj", fuente=str(RELOJ))
    cotas = [
        v.nombre for c in reloj.contratos for v in c.valores if conversion_de(v).tipo.dimensiona
    ]
    assert cotas, "el reloj no tiene ni una cota, algo va mal"
    for nombre in cotas:
        assert f"export const {nombre} =" in texto


def test_hay_un_csv_por_tipo_y_suman_el_total(reloj: Contratos):
    """Con un fichero por tipo no hay desplegable de Onshape que equivocar."""
    tablas = csv_por_tipo(reloj)
    assert Tipo.REFERENCIA in tablas, "las magnitudes de producto van en su propio fichero"
    total = sum(len(texto.strip().split("\n")) - 1 for texto in tablas.values())
    assert total == len(reloj.variables())


def test_el_fichero_de_referencia_no_lleva_ninguna_cota(reloj: Contratos):
    import csv as modulo_csv

    filas = list(modulo_csv.reader(csv_por_tipo(reloj)[Tipo.REFERENCIA].strip().split("\n")))
    for fila in filas[1:]:
        assert fila[3] == Tipo.REFERENCIA.value
