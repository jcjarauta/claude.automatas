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
from core.reloj.escape import (
    brazo_paleta,
    distancia_entre_centros,
    par_con_rendimiento,
    par_minimo_teorico,
)
from core.reloj.pendulo import Pendulo
from core.units import Julios, Kilogramos, Metros, Radianes
from scripts.exportar_variables import (
    CABECERA_ONSHAPE,
    COLUMNA_VALOR,
    COLUMNAS_COTA,
    FACTOR_ONSHAPE,
    NOMBRE_MAPA,
    UNIDADES,
    Tipo,
    conversion_de,
    convertir,
    csv,
    csv_por_tipo,
    descripcion_corta,
    featurescript,
    gemelo,
    tabla_cota,
    tabla_onshape,
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
    diametro = reloj.valor("energia", "tambor_diametro").metros
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
    del contrato por el factor tiene que dar el valor de la tabla.

    La tolerancia es la del **redondeo que declara la propia unidad**, no una
    fija: un ángulo pequeño como el adelanto de la punta —1,2524°— cae fuera de
    cualquier tolerancia relativa apretada solo por escribirse con cuatro
    decimales, y eso no es un error de conversión."""
    for contrato in reloj.contratos:
        for valor in contrato.valores:
            cifra, conversion = convertir(valor)
            esperado = valor.valor * conversion.factor
            redondeo = 0.5 * 10.0 ** (-conversion.decimales)
            assert float(cifra) == pytest.approx(esperado, abs=redondeo, rel=1e-9), valor.nombre


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


# ---------------------------------------------------------------------------
# La hoja que se teclea en el Variable Studio
# ---------------------------------------------------------------------------


def test_la_hoja_de_onshape_tiene_las_columnas_de_la_tabla(reloj: Contratos):
    """Cuatro columnas y en su orden: la tabla del Variable Studio tiene esas
    y no las diez del CSV completo."""
    import csv as modulo_csv

    for texto in tabla_onshape(reloj).values():
        filas = list(modulo_csv.reader(texto.strip().split("\n")))
        assert filas[0] == CABECERA_ONSHAPE
        assert {len(f) for f in filas} == {4}


def test_la_hoja_de_onshape_no_lleva_ninguna_magnitud_de_referencia(reloj: Contratos):
    """Es el punto entero de haber separado por tipo: una masa no puede
    acabar en el Variable Studio, porque allí nada impide acotar con ella."""
    import csv as modulo_csv

    tablas = tabla_onshape(reloj)
    assert Tipo.REFERENCIA not in tablas
    # Lo que no puede haber es una FILA con ese nombre. Citarlo en la
    # descripcion de otra variable si vale: `vueltas_tambor` se explica como
    # `autonomia / periodo_rueda_grande` y eso es exactamente lo que hay que
    # poder leer en la celda.
    filas = [f for texto in tablas.values() for f in modulo_csv.reader(texto.strip().split("\n"))]
    nombres = {f[0] for f in filas[1:]}
    for nombre in ("masa_pesa", "periodo_pendulo", "tension_cuerda_techo", "autonomia"):
        assert nombre not in nombres, f"'{nombre}' no puede estar en el Variable Studio"


def test_la_hoja_de_onshape_lleva_todas_las_cotas(reloj: Contratos):
    todas = "\n".join(tabla_onshape(reloj).values())
    esperadas = [
        v.nombre for c in reloj.contratos for v in c.valores if conversion_de(v).tipo.dimensiona
    ]
    for nombre in esperadas:
        assert nombre in todas


def test_el_valor_se_escribe_con_su_unidad_y_sin_ceros_de_cola(reloj: Contratos):
    import csv as modulo_csv

    filas = list(modulo_csv.reader(tabla_onshape(reloj)[Tipo.LENGTH].strip().split("\n")))
    por_nombre = {f[0]: f[2] for f in filas[1:]}
    assert por_nombre["longitud_pendulo_nominal"] == "994 mm"
    assert por_nombre["eje_diametro"] == "10 mm"
    # Por nombre y no por indice: el orden de los contratos cambia cuando una
    # cota se mueve de sitio, y un test que depende del orden falla por eso y
    # no por lo que vigila.
    angulo = list(modulo_csv.reader(tabla_onshape(reloj)[Tipo.ANGLE].strip().split("\n")))
    por_angulo = {f[0]: f[2] for f in angulo[1:]}
    assert por_angulo["amplitud_nominal"] == "3 deg"
    assert por_angulo["rueda_escape_paso_angular"] == "12 deg"


def test_la_descripcion_corta_cabe_en_una_celda_y_sigue_diciendo_algo():
    assert descripcion_corta("Del punto de flexion al centro de masas. Y mas cosas aqui") == (
        "Del punto de flexion al centro de masas"
    )
    # Una primera frase demasiado corta no dice nada: se sigue leyendo.
    assert descripcion_corta("Propuesta. El suelo lo pone la separacion").startswith(
        "Propuesta. El"
    )
    largo = descripcion_corta("palabra " * 40)
    assert len(largo) <= 70
    assert largo.endswith("\u2026")


# ---------------------------------------------------------------------------
# Los CSV que Onshape importa como MAPA, uno por tipo
# ---------------------------------------------------------------------------


def _filas(texto: str) -> list[list[str]]:
    import csv as modulo_csv

    return list(modulo_csv.reader(texto.strip().split("\n")))


def test_hay_un_fichero_por_tipo_y_cada_uno_lleva_solo_el_suyo(reloj: Contratos):
    """Tres ficheros y no uno porque **el factor de conversión es por
    variable**: el mapa de longitudes se importa con factor 1 mm y el de
    ángulos con 1 deg. Mezclados no hay factor que valga para los dos."""
    tablas = tabla_cota(reloj)
    assert set(tablas) == {Tipo.LENGTH, Tipo.ANGLE, Tipo.NUMBER}
    unidades = {tipo: {f[2] for f in _filas(texto)} for tipo, texto in tablas.items()}
    assert unidades[Tipo.LENGTH] == {"mm"}
    assert unidades[Tipo.ANGLE] == {"deg"}
    assert unidades[Tipo.NUMBER] == {""}


def test_cada_tipo_tiene_su_factor_y_su_nombre_de_mapa():
    assert FACTOR_ONSHAPE[Tipo.LENGTH] == "1 mm"
    assert FACTOR_ONSHAPE[Tipo.ANGLE] == "1 deg"
    assert NOMBRE_MAPA[Tipo.LENGTH] == "cota"
    assert set(NOMBRE_MAPA) == {Tipo.LENGTH, Tipo.ANGLE, Tipo.NUMBER}


def test_las_claves_del_mapa_no_se_repiten(reloj: Contratos):
    """Se importa como mapa con la clave en la columna 0. Dos filas con la
    misma clave y una gana en silencio."""
    for tipo, texto in tabla_cota(reloj).items():
        claves = [f[0] for f in _filas(texto)]
        assert len(claves) == len(set(claves)), f"clave repetida en {tipo}"


def test_ningun_fichero_lleva_cabecera(reloj: Contratos):
    """La clave sale de la columna 0, así que una cabecera metería una
    entrada llamada «nombre» en el mapa."""
    for texto in tabla_cota(reloj).values():
        assert _filas(texto)[0][0] != COLUMNAS_COTA[0]


def test_siete_columnas_y_el_valor_en_la_uno(reloj: Contratos):
    """Las mismas siete y en el mismo orden que el fichero del escribiente,
    para que el índice de columna sea el mismo en las dos máquinas."""
    for texto in tabla_cota(reloj).values():
        filas = _filas(texto)
        assert {len(f) for f in filas} == {7}
    cotas = {f[0]: f[COLUMNA_VALOR] for f in _filas(tabla_cota(reloj)[Tipo.LENGTH])}
    assert cotas["longitud_pendulo_nominal"] == "994.0000"


def test_no_se_cuela_ninguna_magnitud_de_referencia(reloj: Contratos):
    claves = {f[0] for texto in tabla_cota(reloj).values() for f in _filas(texto)}
    for nombre in ("masa_pesa", "periodo_pendulo", "autonomia", "tension_cuerda_techo"):
        assert nombre not in claves


def test_cada_diametro_lleva_su_radio_detras_y_al_reves(reloj: Contratos):
    filas = _filas(tabla_cota(reloj)[Tipo.LENGTH])
    por_nombre = {f[0]: f for f in filas}
    assert por_nombre["eje_diametro"][COLUMNA_VALOR] == "10.0000"
    assert por_nombre["eje_diametro_radio"][COLUMNA_VALOR] == "5.0000"
    assert por_nombre["tambor_diametro_radio"][COLUMNA_VALOR] == "42.5000"
    nombres = [f[0] for f in filas]
    assert nombres[nombres.index("eje_diametro") + 1] == "eje_diametro_radio"


def test_el_gemelo_se_decide_por_el_nombre_y_no_por_el_significado():
    """`taladro_eje` también es un diámetro y no lleva gemelo. Lo que decide
    no es lo que la cota es, sino cómo se llama: así se puede leer el fichero
    y saber cuáles hay sin conocer la pieza."""
    assert gemelo("eje_diametro", 10.0) == ("eje_diametro_radio", 5.0)
    assert gemelo("radio_base", 55.0) == ("radio_base_diametro", 110.0)
    assert gemelo("taladro_eje", 10.0) is None
    assert gemelo("cinta_espesor", 0.05) is None


def test_la_descripcion_del_gemelo_dice_de_donde_sale(reloj: Contratos):
    por_nombre = {f[0]: f for f in _filas(tabla_cota(reloj)[Tipo.LENGTH])}
    assert por_nombre["eje_diametro_radio"][6].startswith("derivada de eje_diametro")
    assert por_nombre["eje_diametro_radio"][5] == por_nombre["eje_diametro"][5]


# ---------------------------------------------------------------------------
# La pieza 1.1, la primera que se corta
# ---------------------------------------------------------------------------


def test_la_cadena_del_pendulo_suma_hasta_el_centro_de_la_lenteja(reloj: Contratos):
    """Del punto de flexión del muelle al extremo de la varilla, más la
    varilla, más lo que hay del extremo al centro de la lenteja.

    **La suma NO es `longitud_pendulo_nominal`.** Los 994 son la longitud
    equivalente —la del péndulo simple que bate 2 s— y el centro de la
    lenteja va 13 mm más abajo, porque la varilla tiene masa y acelera el
    conjunto. Confundir las dos es el error que C11 existe para evitar.

    El largo de la varilla es DERIVADO de esta suma, no una elección."""
    centro = reloj.valor("pendulo", "lenteja_centro_a_flexion").en_mm
    flexion = reloj.valor("suspension", "muelle_flexion_a_varilla").en_mm
    largo = reloj.valor("pendulo", "varilla_largo").en_mm
    bajo = reloj.valor("lenteja", "lenteja_centro_bajo_varilla").en_mm
    assert flexion + largo + bajo == pytest.approx(centro, abs=0.01)


def test_la_lenteja_va_mas_abajo_que_la_longitud_equivalente(reloj: Contratos):
    """C11 en una linea. Si alguien vuelve a poner el centro en 994, el reloj
    adelanta nueve minutos al dia y la tuerca no llega a corregirlo."""
    assert (
        reloj.valor("pendulo", "lenteja_centro_a_flexion").en_mm
        > reloj.valor("oscilador", "longitud_pendulo_nominal").en_mm
    )


def test_el_contrato_bate_dos_segundos_segun_c11(reloj: Contratos):
    """El test que cruza el contrato con el nucleo. Monta el pendulo con las
    cotas del JSON y comprueba que el periodo sale a 2 s dentro de lo que la
    tuerca puede corregir."""
    m = reloj.valor
    largo = m("pendulo", "varilla_largo").valor
    masa_varilla = (
        m("pendulo", "varilla_densidad").valor
        * largo
        * m("pendulo", "varilla_ancho").valor
        * m("pendulo", "varilla_espesor").valor
    )
    flexion = m("suspension", "muelle_flexion_a_varilla").valor
    p = Pendulo(
        masa_lenteja=Kilogramos(m("lenteja", "lenteja_masa").valor),
        centro_lenteja=Metros(m("pendulo", "lenteja_centro_a_flexion").valor),
        masa_varilla=Kilogramos(masa_varilla),
        varilla_desde=Metros(flexion),
        varilla_hasta=Metros(flexion + largo),
    )
    objetivo = m("oscilador", "periodo_pendulo").valor
    deriva = abs(p.periodo() - objetivo) * 43200.0  # segundos al dia
    assert deriva < 60.0, f"el contrato se desvia {deriva:.0f} s/dia del periodo pedido"


def test_el_recorrido_de_la_tuerca_cubre_lo_que_queda(reloj: Contratos):
    """Lo que la construccion no acierta lo tiene que poder la regulacion. Si
    no, el reloj no se puede poner en hora por mucho que se gire la tuerca."""
    m = reloj.valor
    largo = m("pendulo", "varilla_largo").valor
    masa_varilla = (
        m("pendulo", "varilla_densidad").valor
        * largo
        * m("pendulo", "varilla_ancho").valor
        * m("pendulo", "varilla_espesor").valor
    )
    flexion = m("suspension", "muelle_flexion_a_varilla").valor
    p = Pendulo(
        masa_lenteja=Kilogramos(m("lenteja", "lenteja_masa").valor),
        centro_lenteja=Metros(m("pendulo", "lenteja_centro_a_flexion").valor),
        masa_varilla=Kilogramos(masa_varilla),
        varilla_desde=Metros(flexion),
        varilla_hasta=Metros(flexion + largo),
    )
    deriva = abs(p.periodo() - m("oscilador", "periodo_pendulo").valor) * 43200.0
    alcance = 10.0 * m("oscilador", "paso_tuerca_regulacion").en_mm * p.deriva_por_milimetro()
    assert alcance > deriva * 2.0


def test_el_punto_de_flexion_es_la_mitad_del_tramo_libre(reloj: Contratos):
    """El pivote efectivo de un muelle de suspensión no está en el amarre
    sino en el centro del tramo que flexa. Es una aproximación: depende de la
    rigidez frente al peso de la lenteja, y R1 la mide."""
    assert reloj.valor("suspension", "muelle_flexion_a_varilla").en_mm == pytest.approx(
        reloj.valor("suspension", "muelle_largo_libre").en_mm / 2.0
    )


def test_el_muelle_llega_a_los_dos_amarres(reloj: Contratos):
    """Tiene que cubrir el tramo libre, lo que entra en el soporte y lo que
    solapa la varilla hasta pasar su segundo taladro."""
    libre = reloj.valor("suspension", "muelle_largo_libre").en_mm
    lejos = reloj.valor("pendulo", "varilla_taladro_lejos").en_mm
    assert reloj.valor("suspension", "muelle_largo").en_mm >= libre + lejos + 10.0


def test_los_tornillos_del_soporte_no_atraviesan_el_muelle(reloj: Contratos):
    """Taladrar un fleje de 0,1 mm es crear la línea por donde va a romper.
    Los dos tornillos pasan a los lados, no por él."""
    sep = reloj.valor("suspension", "soporte_tornillo_separacion").en_mm
    tornillo = reloj.valor("suspension", "soporte_tornillo_diametro").en_mm
    muelle = reloj.valor("suspension", "muelle_ancho").en_mm
    holgura = sep / 2.0 - tornillo / 2.0 - muelle / 2.0
    assert holgura >= 2.0, f"solo {holgura:.1f} mm entre el tornillo y el canto del fleje"


def test_los_tornillos_dejan_pared_hasta_el_borde_del_bloque(reloj: Contratos):
    ancho = reloj.valor("suspension", "soporte_ancho").en_mm
    sep = reloj.valor("suspension", "soporte_tornillo_separacion").en_mm
    tornillo = reloj.valor("suspension", "soporte_tornillo_diametro").en_mm
    assert ancho / 2.0 - sep / 2.0 - tornillo / 2.0 >= 3.0


def test_el_soporte_es_mas_ancho_que_el_muelle(reloj: Contratos):
    assert (
        reloj.valor("suspension", "soporte_ancho").en_mm
        > reloj.valor("suspension", "muelle_ancho").en_mm
    )


def test_los_dos_taladros_quedan_dentro_del_solape_del_muelle(reloj: Contratos):
    """Los dos aprietan el muelle contra la varilla, así que el fleje tiene
    que llegar a cubrirlos. Un taladro fuera del solape no aprieta nada: deja
    el muelle sujeto por un solo punto y el péndulo gira sobre sí mismo."""
    libre = reloj.valor("suspension", "muelle_largo_libre").en_mm
    solape = reloj.valor("suspension", "muelle_largo").en_mm - libre
    radio = reloj.valor("pendulo", "varilla_taladro_diametro").en_mm / 2.0
    for clave in ("varilla_taladro_cerca", "varilla_taladro_lejos"):
        assert reloj.valor("pendulo", clave).en_mm + radio < solape, f"{clave} se sale del muelle"


def test_los_taladros_no_se_comen_el_ancho_de_la_varilla(reloj: Contratos):
    """Un taladro centrado deja pared a los lados. Con Ø4,2 en 15 de ancho
    quedan 5,4 a cada lado, que es de sobra."""
    ancho = reloj.valor("pendulo", "varilla_ancho").en_mm
    taladro = reloj.valor("pendulo", "varilla_taladro_diametro").en_mm
    assert (ancho - taladro) / 2.0 >= 3.0


def test_los_dos_taladros_no_se_pisan(reloj: Contratos):
    cerca = reloj.valor("pendulo", "varilla_taladro_cerca").en_mm
    lejos = reloj.valor("pendulo", "varilla_taladro_lejos").en_mm
    taladro = reloj.valor("pendulo", "varilla_taladro_diametro").en_mm
    assert lejos - cerca > taladro


# ---------------------------------------------------------------------------
# La pieza 1.2, la lenteja, y el vastago que la sostiene
# ---------------------------------------------------------------------------

PLOMO = 11340.0
MADERA = 500.0
"""kg/m³, nominales de tabla. Se sustituyen por el peso real en R1: el plomo
fundido en casa trae huecos y la madera depende de la humedad."""


def _masa_lenteja(reloj: Contratos) -> float:
    """La masa que sale de las cotas. No se teclea en ningún sitio."""
    cilindro = math.pi / 4.0
    v_cavidad = (
        cilindro
        * reloj.valor("lenteja", "lenteja_cavidad_diametro").metros ** 2
        * reloj.valor("lenteja", "lenteja_cavidad_profundidad").metros
    )
    v_total = (
        cilindro
        * reloj.valor("lenteja", "lenteja_diametro").metros ** 2
        * reloj.valor("lenteja", "lenteja_espesor").metros
    )
    return v_cavidad * PLOMO + (v_total - v_cavidad) * MADERA


def test_la_masa_de_la_lenteja_sale_de_sus_cotas(reloj: Contratos):
    """Es el `core/solido.py` del escribiente aplicado aquí: la masa es una
    consecuencia de la geometría, no un número aparte que pueda derivar."""
    assert reloj.valor("lenteja", "lenteja_masa").valor == pytest.approx(
        _masa_lenteja(reloj), rel=0.01
    )


def test_la_lenteja_pesa_lo_que_el_pendulo_necesita(reloj: Contratos):
    """Alrededor de un kilo. Más ligera, el escape la perturba; más pesada,
    el muelle de suspensión trabaja de más."""
    assert 0.8 < reloj.valor("lenteja", "lenteja_masa").valor < 1.3


def test_la_cavidad_del_plomo_deja_pared_fondo_y_tapa(reloj: Contratos):
    """Si la cavidad llega al borde, el plomo se sale por un lado al vaciar."""
    pared = (
        reloj.valor("lenteja", "lenteja_diametro").en_mm
        - reloj.valor("lenteja", "lenteja_cavidad_diametro").en_mm
    ) / 2.0
    resto = (
        reloj.valor("lenteja", "lenteja_espesor").en_mm
        - reloj.valor("lenteja", "lenteja_cavidad_profundidad").en_mm
    )
    assert pared >= 5.0, "poca pared alrededor del plomo"
    assert resto >= 5.0, "poco fondo y tapa"


def test_la_lenteja_pasa_sobre_el_vastago_sin_roscarse(reloj: Contratos):
    """Sube y baja con la tuerca. Si el agujero fuera justo, rozaría y la
    regulación dejaría de ser fina."""
    hueco = (
        reloj.valor("lenteja", "lenteja_taladro_diametro").en_mm
        - reloj.valor("pendulo", "vastago_diametro").en_mm
    )
    assert 0.2 <= hueco <= 1.0


def test_el_vastago_entra_en_la_varilla_lo_que_dice(reloj: Contratos):
    dentro = reloj.valor("pendulo", "varilla_vastago_profundidad").en_mm
    fuera = reloj.valor("pendulo", "vastago_saliente").en_mm
    assert reloj.valor("pendulo", "vastago_largo").en_mm == pytest.approx(dentro + fuera)


def test_el_vastago_se_empotra_cinco_diametros(reloj: Contratos):
    """La unión trabaja a flexión: es el punto donde la varilla de madera
    entrega el par a una varilla de 6 mm."""
    dentro = reloj.valor("pendulo", "varilla_vastago_profundidad").en_mm
    assert dentro >= 5.0 * reloj.valor("pendulo", "vastago_diametro").en_mm


def test_el_taladro_del_vastago_cabe_en_el_espesor_de_la_varilla(reloj: Contratos):
    """Un taladro de Ø6,2 en un listón de 8 deja 0,9 mm de pared a cada lado.
    Es poco, y por eso está aquí: si el espesor baja, salta."""
    pared = (
        reloj.valor("pendulo", "varilla_espesor").en_mm
        - reloj.valor("pendulo", "varilla_vastago_diametro").en_mm
    ) / 2.0
    assert pared >= 0.8, f"solo quedan {pared:.1f} mm de pared alrededor del vastago"


def test_el_recorrido_de_la_tuerca_cubre_el_error_de_montaje(reloj: Contratos):
    """El vástago saliente menos lo que ocupa la lenteja es el recorrido útil.
    Tiene que dar al menos ±5 min/día, que es lo que puede fallar el montaje
    mientras el punto de flexión del muelle siga sin ficha."""
    saliente = reloj.valor("pendulo", "vastago_saliente").metros
    espesor = reloj.valor("lenteja", "lenteja_espesor").metros
    nominal = reloj.valor("oscilador", "longitud_pendulo_nominal").metros
    recorrido = (saliente - espesor) / 2.0
    segundos_por_dia = 0.5 * recorrido / nominal * 86400.0
    assert segundos_por_dia >= 300.0, f"solo {segundos_por_dia:.0f} s/dia de margen"


def test_la_posicion_lateral_de_los_taladros_es_derivada(reloj: Contratos):
    """«Centrado» no es una cota: en el taller se marca desde el canto con un
    lápiz, y hace falta el número. Sale del ancho y la separación, así que si
    alguno de los dos se mueve y este no, el boceto miente."""
    ancho = reloj.valor("suspension", "soporte_ancho").en_mm
    sep = reloj.valor("suspension", "soporte_tornillo_separacion").en_mm
    lado = reloj.valor("suspension", "soporte_tornillo_al_lado").en_mm
    assert lado == pytest.approx((ancho - sep) / 2.0, abs=0.01)


def test_la_placa_de_apriete_mide_lo_mismo_de_ancho_que_el_bloque(reloj: Contratos):
    """Se taladran juntos. Si no coinciden de ancho, los taladros tampoco."""
    assert reloj.valor("suspension", "soporte_placa_ancho").en_mm == pytest.approx(
        reloj.valor("suspension", "soporte_ancho").en_mm, abs=0.01
    )


def test_la_placa_pasa_de_los_tornillos(reloj: Contratos):
    """Si la placa se queda por debajo de la línea de tornillos, el fleje
    empieza a flexar donde la placa acaba y no donde dice el contrato: el
    datum del péndulo se mueve sin que nadie lo vea."""
    alto = reloj.valor("suspension", "soporte_placa_alto").en_mm
    canto = reloj.valor("suspension", "soporte_tornillo_al_canto").en_mm
    tornillo = reloj.valor("suspension", "soporte_tornillo_diametro").en_mm
    assert alto - canto - tornillo / 2.0 >= 3.0


def test_la_placa_no_sobresale_del_bloque(reloj: Contratos):
    assert (
        reloj.valor("suspension", "soporte_placa_alto").en_mm
        <= reloj.valor("suspension", "soporte_alto").en_mm
    )


# --- 1.3 · el fleje -----------------------------------------------------


def test_el_largo_del_fleje_es_la_suma_de_sus_tres_zonas(reloj: Contratos):
    """Empotrado, libre y solape. El largo no se elige: es lo que miden las
    tres juntas, y si alguna se mueve la tira se corta a otra medida."""
    v = reloj.contrato("suspension")
    suma = (
        v.valor("muelle_empotrado").en_mm
        + v.valor("muelle_largo_libre").en_mm
        + v.valor("muelle_solape").en_mm
    )
    assert v.valor("muelle_largo").en_mm == pytest.approx(suma, abs=0.01)


def test_los_taladros_del_fleje_caen_sobre_los_de_la_varilla(reloj: Contratos):
    """Se taladran de una pasada, fleje y varilla juntos. Si las dos cotas no
    salen de la misma cuenta, el fleje se taladra en el sitio equivocado y ya
    no hay forma de arreglarlo: un agujero de mas en un fleje de 0,1 lo
    inutiliza."""
    v = reloj.contrato("suspension")
    hasta_la_varilla = v.valor("muelle_empotrado").en_mm + v.valor("muelle_largo_libre").en_mm
    for del_fleje, de_la_varilla in (
        ("muelle_taladro_cerca", "varilla_taladro_cerca"),
        ("muelle_taladro_lejos", "varilla_taladro_lejos"),
    ):
        assert v.valor(del_fleje).en_mm == pytest.approx(
            hasta_la_varilla + reloj.valor("pendulo", de_la_varilla).en_mm, abs=0.01
        ), del_fleje


def test_el_fleje_se_taladra_solo_donde_no_flexa(reloj: Contratos):
    """LA regla del fleje. Un agujero donde el muelle flexa es la linea por
    la que va a romper; donde solo tira, no pasa nada: la carga son 12 N
    sobre 1,2 mm2, unos 10 MPa frente a los 1.500 del acero de muelle.

    Asi que los dos taladros tienen que caer enteros por debajo del tramo
    libre, con su radio incluido."""
    v = reloj.contrato("suspension")
    muerto = v.valor("muelle_empotrado").en_mm + v.valor("muelle_largo_libre").en_mm
    radio = v.valor("muelle_taladro_diametro").en_mm / 2.0
    assert v.valor("muelle_taladro_cerca").en_mm - radio >= muerto


def test_el_ultimo_taladro_deja_fleje_por_debajo(reloj: Contratos):
    v = reloj.contrato("suspension")
    radio = v.valor("muelle_taladro_diametro").en_mm / 2.0
    sobra = v.valor("muelle_largo").en_mm - v.valor("muelle_taladro_lejos").en_mm - radio
    assert sobra >= 2.0


def test_el_taladro_del_fleje_deja_material_a_los_lados(reloj: Contratos):
    v = reloj.contrato("suspension")
    ancho = v.valor("muelle_ancho").en_mm
    taladro = v.valor("muelle_taladro_diametro").en_mm
    assert (ancho - taladro) / 2.0 >= 3.0


def test_la_placa_cubre_todo_el_tramo_empotrado(reloj: Contratos):
    """Si la placa se queda corta, el fleje empieza a flexar donde acaba la
    placa y el tramo libre deja de ser el que dice el contrato."""
    v = reloj.contrato("suspension")
    assert v.valor("soporte_placa_alto").en_mm >= v.valor("muelle_empotrado").en_mm


def test_el_fleje_no_se_corta_mas_corto_que_la_varilla_que_tapa(reloj: Contratos):
    """El solape tiene que cubrir el taladro de abajo de la varilla."""
    v = reloj.contrato("suspension")
    radio = reloj.valor("pendulo", "varilla_taladro_diametro").en_mm / 2.0
    assert (
        v.valor("muelle_solape").en_mm
        >= reloj.valor("pendulo", "varilla_taladro_lejos").en_mm + radio
    )


# --- 1.5 · el anclaje al bastidor ---------------------------------------


def test_el_anclaje_usa_la_misma_broca_que_el_muelle(reloj: Contratos):
    """Cuatro agujeros en el bloque y una sola broca. Cambiar de broca a
    mitad de una pieza es una ocasion de equivocarse que no aporta nada."""
    assert reloj.valor("anclaje", "anclaje_tornillo_diametro").en_mm == pytest.approx(
        reloj.valor("suspension", "soporte_tornillo_diametro").en_mm, abs=0.01
    )


def test_los_cuatro_taladros_del_bloque_caen_en_dos_lineas(reloj: Contratos):
    """Misma separacion y misma distancia al canto lateral que los del
    muelle: la plantilla de taladrado es una, no dos."""
    for del_anclaje, del_muelle in (
        ("anclaje_tornillo_separacion", "soporte_tornillo_separacion"),
        ("anclaje_tornillo_al_lado", "soporte_tornillo_al_lado"),
    ):
        assert reloj.valor("anclaje", del_anclaje).en_mm == pytest.approx(
            reloj.valor("suspension", del_muelle).en_mm, abs=0.01
        ), del_anclaje


def test_el_anclaje_cabe_en_el_bloque(reloj: Contratos):
    """Por arriba: tiene que quedar pared entre el taladro y el canto."""
    alto = reloj.valor("suspension", "soporte_alto").en_mm
    datum = reloj.valor("anclaje", "anclaje_al_datum").en_mm
    radio = reloj.valor("anclaje", "anclaje_tornillo_diametro").en_mm / 2.0
    assert alto - datum - radio >= 3.0


def test_el_anclaje_no_pisa_la_placa_ni_el_fleje(reloj: Contratos):
    """La cabeza del tornillo de anclaje queda en la cara de delante, que es
    donde van la placa y el fleje. Si se solapan, el bloque no asienta."""
    datum = reloj.valor("anclaje", "anclaje_al_datum").en_mm
    radio = reloj.valor("anclaje", "anclaje_tornillo_diametro").en_mm / 2.0
    for estorbo in ("soporte_placa_alto", "muelle_empotrado"):
        assert datum - radio >= reloj.valor("suspension", estorbo).en_mm, estorbo


def test_el_anclaje_esta_por_encima_de_la_mitad_del_bloque(reloj: Contratos):
    """El peso del pendulo cuelga por delante del bastidor, asi que el bloque
    tiende a volcar: se apoya por el canto de abajo y tira de los tornillos.
    Puestos abajo, el tornillo trabaja a arrancamiento con poco brazo."""
    assert (
        reloj.valor("anclaje", "anclaje_al_datum").en_mm
        > reloj.valor("suspension", "soporte_alto").en_mm / 2.0
    )


def test_las_dos_filas_de_taladros_no_son_simetricas(reloj: Contratos):
    """Si las dos filas estan a la misma distancia de sus cantos, el bloque
    se puede montar del reves y el patron de taladros es identico. Nadie lo
    ve en el taladro, y el canto de apriete acaba arriba: el datum del
    pendulo se va al otro extremo y el reloj no da la hora.

    Con 10 y 32 en un bloque de 40, darle la vuelta da 8 y 30. No encaja, y
    eso es el seguro."""
    alto = reloj.valor("suspension", "soporte_alto").en_mm
    muelle = reloj.valor("suspension", "soporte_tornillo_al_canto").en_mm
    anclaje = reloj.valor("anclaje", "anclaje_al_datum").en_mm
    assert abs(muelle + anclaje - alto) >= 2.0, (
        "las dos filas quedan simetricas respecto a la mitad del bloque: "
        "montado del reves da el mismo patron"
    )


# --- 1.6 · la escuadra del banco R1 -------------------------------------


def test_la_escuadra_respeta_el_contrato_de_anclaje(reloj: Contratos):
    """Lo que hace util el banco: el bloque se atornilla aqui igual que se
    atornillara al bastidor. Si la escuadra inventara su propia separacion,
    habria que volver a taladrar el bloque al pasar de uno a otro."""
    banco = reloj.contrato("banco_pendulo")
    sep = reloj.valor("anclaje", "anclaje_tornillo_separacion").en_mm
    libre = banco.valor("escuadra_mordaza_libre").en_mm
    ancho = banco.valor("escuadra_ancho").en_mm
    assert ancho >= sep + 2.0 * libre


def test_el_taladro_de_la_escuadra_es_guia_y_no_paso(reloj: Contratos):
    """El tornillo rosca en la madera de la tabla, asi que el agujero tiene
    que ser MAS ESTRECHO que el del bloque. Igualarlos es el error que deja
    el bloque suelto y el pendulo bailando."""
    assert (
        reloj.valor("banco_pendulo", "escuadra_taladro_diametro").en_mm
        < reloj.valor("anclaje", "anclaje_tornillo_diametro").en_mm
    )


def test_bajo_el_bloque_cabe_el_fleje_entero(reloj: Contratos):
    """Lo que se mira en R1 es como flexa el fleje. Si la tabla acaba antes,
    no se ve."""
    banco = reloj.contrato("banco_pendulo")
    bajo_el_canto = (
        banco.valor("escuadra_alto").en_mm - banco.valor("escuadra_bloque_al_canto").en_mm
    )
    fleje = (
        reloj.valor("suspension", "muelle_largo").en_mm
        - reloj.valor("suspension", "muelle_empotrado").en_mm
    )
    assert bajo_el_canto > fleje


def test_el_bloque_cabe_en_la_escuadra_por_arriba(reloj: Contratos):
    """El bloque sobresale hacia arriba desde su canto de apriete: tiene que
    quedar tabla por encima para los dos tornillos de anclaje."""
    banco = reloj.contrato("banco_pendulo")
    assert (
        banco.valor("escuadra_bloque_al_canto").en_mm
        >= reloj.valor("suspension", "soporte_alto").en_mm
    )


def test_los_tirafondos_tienen_canto_de_sobra_por_arriba(reloj: Contratos):
    """El taladro mas alto queda cerca del canto de arriba de la tabla, y un
    tirafondo demasiado al borde revienta el canto del tablero en vez de
    agarrar. La regla de taller son dos diametros y medio."""
    banco = reloj.contrato("banco_pendulo")
    tornillo = reloj.valor("anclaje", "anclaje_tornillo_diametro").en_mm
    al_canto = (
        banco.valor("escuadra_bloque_al_canto").en_mm
        - reloj.valor("anclaje", "anclaje_al_datum").en_mm
    )
    assert al_canto >= 2.5 * tornillo


def test_el_taladro_de_la_escuadra_se_acota_desde_sus_propios_cantos(reloj: Contratos):
    """El datum del pendulo es el canto de apriete del BLOQUE, que en esta
    pieza no es ningun borde. Quien la corta solo puede medir desde los
    cantos de la tabla, asi que las dos distancias tienen que existir y salir
    de la cuenta, no del pulso."""
    banco = reloj.contrato("banco_pendulo")
    assert banco.valor("escuadra_taladro_al_canto").en_mm == pytest.approx(
        banco.valor("escuadra_bloque_al_canto").en_mm
        - reloj.valor("anclaje", "anclaje_al_datum").en_mm,
        abs=0.01,
    )
    assert banco.valor("escuadra_taladro_al_lado").en_mm == pytest.approx(
        (
            banco.valor("escuadra_ancho").en_mm
            - reloj.valor("anclaje", "anclaje_tornillo_separacion").en_mm
        )
        / 2.0,
        abs=0.01,
    )


def test_el_taladro_cae_dentro_de_la_franja_util(reloj: Contratos):
    """Entre las dos franjas de mordaza. Si no, la mordaza pisa el tornillo."""
    banco = reloj.contrato("banco_pendulo")
    assert (
        banco.valor("escuadra_taladro_al_lado").en_mm > banco.valor("escuadra_mordaza_libre").en_mm
    )


# --- 2.1 · la rueda de escape -------------------------------------------


def test_el_paso_del_diente_sale_del_diametro(reloj: Contratos):
    r = reloj.contrato("rueda_escape")
    dientes = reloj.valor("escape", "dientes_escape").valor
    assert r.valor("rueda_escape_paso_diente").en_mm == pytest.approx(
        math.pi * r.valor("rueda_escape_diametro").en_mm / dientes, abs=0.01
    )


def test_el_diente_se_puede_cortar_a_mano(reloj: Contratos):
    """LA envolvente de esta pieza, y la que fija el diámetro. Por debajo de
    8 mm de arco, la segueta no entra entre dos dientes sin astillar el
    contrachapado, y una punta astillada cambia el reposo del escape."""
    assert reloj.valor("rueda_escape", "rueda_escape_paso_diente").en_mm >= 8.0


def test_el_fondo_sale_del_diametro_y_la_altura(reloj: Contratos):
    r = reloj.contrato("rueda_escape")
    assert r.valor("rueda_escape_diametro_fondo").en_mm == pytest.approx(
        r.valor("rueda_escape_diametro").en_mm - 2.0 * r.valor("rueda_escape_altura_diente").en_mm,
        abs=0.01,
    )


def test_el_diente_no_es_mas_alto_que_ancho(reloj: Contratos):
    """Un diente más alto que su base es una astilla esperando a romperse, y
    la punta del diente es justo donde apoya la paleta."""
    r = reloj.contrato("rueda_escape")
    base = (
        math.pi
        * r.valor("rueda_escape_diametro_fondo").en_mm
        / reloj.valor("escape", "dientes_escape").valor
    )
    assert r.valor("rueda_escape_altura_diente").en_mm <= base


def test_el_cubo_deja_material_alrededor_del_eje(reloj: Contratos):
    r = reloj.contrato("rueda_escape")
    pared = (
        r.valor("rueda_escape_cubo_diametro").en_mm - r.valor("rueda_escape_eje_diametro").en_mm
    ) / 2.0
    assert pared >= 3.0


def test_el_cubo_no_llega_al_fondo_del_diente(reloj: Contratos):
    """Entre el cubo y el fondo del diente tiene que quedar disco: es lo que
    aguanta el par, y en contrachapado de 4 no sobra."""
    r = reloj.contrato("rueda_escape")
    corona = (
        r.valor("rueda_escape_diametro_fondo").en_mm - r.valor("rueda_escape_cubo_diametro").en_mm
    ) / 2.0
    assert corona >= 10.0


def test_la_rueda_usa_el_eje_congelado(reloj: Contratos):
    assert reloj.valor("rueda_escape", "rueda_escape_eje_diametro").en_mm == pytest.approx(
        reloj.valor("eje", "eje_diametro").en_mm, abs=0.01
    )


def test_el_paso_angular_es_una_vuelta_entre_los_dientes(reloj: Contratos):
    assert reloj.valor("rueda_escape", "rueda_escape_paso_angular").valor == pytest.approx(
        2.0 * math.pi / reloj.valor("escape", "dientes_escape").valor, abs=1e-6
    )


def test_el_socavado_cabe_en_el_paso(reloj: Contratos):
    """Si la punta se inclina más de lo que mide el paso, el diente invade al
    de al lado y deja de haber hueco donde meter la segueta."""
    r = reloj.contrato("rueda_escape")
    assert 0.0 < r.valor("rueda_escape_socavado").valor < r.valor("rueda_escape_paso_angular").valor


def test_el_par_que_pide_el_escape_cabe_de_sobra_en_la_pesa(reloj: Contratos):
    """Cruza C12 con la previsión de la pesa: incluso con el rendimiento más
    pesimista, el par que hace falta en el eje de escape es ridículo frente a
    lo que da el tambor. Si esto fallara, el reloj no sería viable."""
    # La pérdida sale del péndulo del contrato y no de un número tecleado: la
    # amplitud la mueve al cuadrado, y con 27 µJ escritos a mano este test
    # seguiría pasando después de subirla.
    m = reloj.valor
    largo = m("pendulo", "varilla_largo").valor
    masa_varilla = (
        m("pendulo", "varilla_densidad").valor
        * largo
        * m("pendulo", "varilla_ancho").valor
        * m("pendulo", "varilla_espesor").valor
    )
    flexion = m("suspension", "muelle_flexion_a_varilla").valor
    pendulo = Pendulo(
        masa_lenteja=Kilogramos(m("lenteja", "lenteja_masa").valor),
        centro_lenteja=Metros(m("pendulo", "lenteja_centro_a_flexion").valor),
        masa_varilla=Kilogramos(masa_varilla),
        varilla_desde=Metros(flexion),
        varilla_hasta=Metros(flexion + largo),
    )
    perdida = pendulo.perdida_por_ciclo(
        Radianes(m("ancora", "amplitud_nominal").valor), calidad=1500.0
    )
    ideal = par_minimo_teorico(Julios(perdida), int(reloj.valor("escape", "dientes_escape").valor))
    pesimista = par_con_rendimiento(ideal, rendimiento=0.02)
    assert pesimista < 0.02, "el escape pediría más par del que un reloj de pared entrega"


def test_el_socavado_desplaza_la_punta_poco(reloj: Contratos):
    """La cota es el ángulo de la CARA con el radio, no un ángulo central, y
    confundirlos da dos dientes distintos: con 8° de cara la punta se mueve
    1 mm de arco; leído como ángulo central se movería 6, y la cara saldría a
    44° del radio en vez de a 8. Este test fija la lectura."""
    r = reloj.contrato("rueda_escape")
    altura = r.valor("rueda_escape_altura_diente").en_mm
    desplaza = altura * math.tan(r.valor("rueda_escape_socavado").valor)
    assert desplaza < r.valor("rueda_escape_paso_diente").en_mm / 4.0


def test_el_vuelco_de_la_rueda_esta_declarado(reloj: Contratos):
    """Un disco plano se puede montar del revés y los dientes miran al otro
    lado. Que no se pueda impedir no significa que no haya que decirlo: sin
    convenio de desde dónde se mira, el dibujo no tiene sentido de giro."""
    assert reloj.valor("rueda_escape", "rueda_escape_vuelco_cambia_el_sentido").valor == 1.0


# --- 2.2 · el áncora ----------------------------------------------------


def test_la_distancia_entre_centros_sale_de_la_rueda(reloj: Contratos):
    """No se elige: la fija la construcción clásica, que pone el eje donde
    cada brazo queda perpendicular al radio de la rueda en el contacto."""
    radio = reloj.valor("rueda_escape", "rueda_escape_diametro").en_mm / 2.0
    dientes = int(reloj.valor("escape", "dientes_escape").valor)
    assert reloj.valor("ancora", "ancora_entre_centros").en_mm == pytest.approx(
        distancia_entre_centros(radio, dientes), abs=0.01
    )


def test_el_brazo_sale_de_la_rueda(reloj: Contratos):
    radio = reloj.valor("rueda_escape", "rueda_escape_diametro").en_mm / 2.0
    dientes = int(reloj.valor("escape", "dientes_escape").valor)
    assert reloj.valor("ancora", "ancora_brazo").en_mm == pytest.approx(
        brazo_paleta(radio, dientes), abs=0.01
    )


def test_el_triangulo_del_escape_es_rectangulo(reloj: Contratos):
    """La comprobación que lo ata todo: centro de rueda, contacto y eje del
    áncora forman un triángulo rectángulo en el contacto. Si no, la paleta
    empuja contra el eje en vez de en la dirección del movimiento."""
    radio = reloj.valor("rueda_escape", "rueda_escape_diametro").en_mm / 2.0
    brazo = reloj.valor("ancora", "ancora_brazo").en_mm
    entre = reloj.valor("ancora", "ancora_entre_centros").en_mm
    assert radio**2 + brazo**2 == pytest.approx(entre**2, rel=1e-4)


def test_el_eje_del_ancora_no_cae_dentro_de_la_rueda(reloj: Contratos):
    assert (
        reloj.valor("ancora", "ancora_entre_centros").en_mm
        > reloj.valor("rueda_escape", "rueda_escape_diametro").en_mm / 2.0
    )


def test_el_recorrido_del_ancora_es_el_del_pendulo(reloj: Contratos):
    assert reloj.valor("ancora", "ancora_recorrido").valor == pytest.approx(
        2.0 * reloj.valor("ancora", "amplitud_nominal").valor, abs=1e-6
    )


def test_el_presupuesto_angular_cierra(reloj: Contratos):
    """LA envolvente del escape, y la que estaba mal planteada.

    El barrido se reparte en cuatro, no en dos: reposo, impulso, caída y
    **arco suplementario**. Ese último es el tramo en que el diente apoya en
    el ARCO de reposo, centrado en el eje del áncora: el péndulo sigue girando
    sin mover la rueda. En un retroceso ese tramo no existe y la rueda
    retrocede, y esa es la diferencia entre los dos escapes.

    La envolvente anterior repartía el barrido entre reposo e impulso como si
    el suplementario no existiera, y por eso daba un reposo de 0,6°, la mitad
    de lo que recomienda cualquier fuente."""
    a = reloj.contrato("ancora")
    partes = sum(
        a.valor(k).valor
        for k in ("ancora_reposo", "ancora_impulso", "ancora_caida", "ancora_suplementario")
    )
    assert partes == pytest.approx(a.valor("ancora_recorrido").valor, abs=1e-6)


def test_queda_arco_suplementario_de_colchon(reloj: Contratos):
    """El suplementario es lo que absorbe que la pesa varíe. Sin él, cualquier
    cambio de rozamiento mueve la amplitud, y la amplitud mueve la marcha por
    error circular."""
    assert math.degrees(reloj.valor("ancora", "ancora_suplementario").valor) >= 1.0


def test_el_trabajo_cabe_en_el_barrido(reloj: Contratos):
    a = reloj.contrato("ancora")
    trabajo = sum(a.valor(k).valor for k in ("ancora_reposo", "ancora_impulso", "ancora_caida"))
    assert trabajo < a.valor("ancora_recorrido").valor


def test_los_dos_arcos_de_reposo_difieren_en_el_impulso(reloj: Contratos):
    """Lo que hace deadbeat a un Graham son dos radios, uno por paleta,
    centrados en el eje del áncora y separados por la profundidad del impulso.
    Si fuesen iguales no habría plano que empujar; si no fuesen arcos, la
    rueda retrocedería."""
    a = reloj.contrato("ancora")
    prof = a.valor("ancora_impulso_profundidad").en_mm
    brazo = a.valor("ancora_brazo").en_mm
    assert prof == pytest.approx(brazo * a.valor("ancora_impulso").valor, abs=0.01)
    assert a.valor("ancora_arco_entrada").en_mm == pytest.approx(brazo - prof / 2.0, abs=0.01)
    assert a.valor("ancora_arco_salida").en_mm == pytest.approx(brazo + prof / 2.0, abs=0.01)


def test_un_reposo_de_cero_no_es_un_escape(reloj: Contratos):
    """`docs/reloj/plan-de-diseno.md`: con reposo cero el veredicto es
    negativo, porque un escape sin reposo se dispara con cualquier vibración.
    Aquí se comprueba que el contrato no lo permite."""
    assert reloj.valor("ancora", "ancora_reposo").valor > 0.0


def test_la_ranura_da_recorrido_de_sobra_al_reposo(reloj: Contratos):
    """La ranura es lo que convierte «un pelín más» en una cota repetible.
    Tiene que cubrir varias veces el reposo buscado, o no hay margen para
    encontrarlo."""
    brazo = reloj.valor("ancora", "ancora_brazo").en_mm
    recorrido = reloj.valor("ancora", "ancora_ranura_largo").en_mm / brazo
    assert recorrido > 3.0 * reloj.valor("ancora", "ancora_reposo").valor


def test_el_ancora_y_la_rueda_salen_del_mismo_tablero(reloj: Contratos):
    assert reloj.valor("ancora", "ancora_espesor").en_mm == pytest.approx(
        reloj.valor("rueda_escape", "rueda_escape_espesor").en_mm, abs=0.01
    )


def test_el_brazo_es_mas_ancho_que_su_ranura(reloj: Contratos):
    pared = (
        reloj.valor("ancora", "ancora_brazo_ancho").en_mm
        - reloj.valor("ancora", "ancora_ranura_ancho").en_mm
    ) / 2.0
    assert pared >= 2.5


def test_el_reposo_es_mayor_que_el_error_de_sierra(reloj: Contratos):
    """El límite por abajo, y el que hace que el escape sea viable en madera.
    Si el reposo medido en el brazo es menor que lo que se desvía un diente
    cortado a mano (±0,3 mm, la tolerancia declarada de la rueda), hay dientes
    que no llegan a apoyar y el escape se dispara solo en algunos."""
    arco = (
        reloj.valor("ancora", "ancora_brazo").en_mm * reloj.valor("ancora", "ancora_reposo").valor
    )
    assert arco > 0.3


def test_la_ranura_empieza_donde_dice_la_cuenta(reloj: Contratos):
    """Acaba en la punta del brazo, así que su principio es lo único que hay
    que marcar. Derivarlo evita restar con un lápiz."""
    a = reloj.contrato("ancora")
    assert a.valor("ancora_ranura_al_eje").en_mm == pytest.approx(
        a.valor("ancora_brazo_material").en_mm - a.valor("ancora_ranura_largo").en_mm, abs=0.01
    )


def test_la_madera_del_brazo_acaba_antes_del_contacto(reloj: Contratos):
    """La paleta va atornillada sobre la cara y es la que llega al diente. Si
    el brazo llegase hasta el contacto, la paleta no tendría nada que ajustar
    y el escape dejaría de ser regulable."""
    a = reloj.contrato("ancora")
    salva = a.valor("ancora_brazo").en_mm - a.valor("ancora_brazo_material").en_mm
    assert 3.0 <= salva <= a.valor("ancora_ranura_largo").en_mm


def test_la_rueda_pasa_por_delante_del_cubo_del_ancora(reloj: Contratos):
    """EL LÍMITE DE CONJUNTO del escape, y no lo ve ninguna envolvente de
    pieza: la rueda gira a 45 mm de su centro y el cubo del áncora está a
    63,64 de ahí. Es el equivalente del hueco al poste del escribiente."""
    a = reloj.contrato("ancora")
    hueco = (
        a.valor("ancora_entre_centros").en_mm
        - reloj.valor("rueda_escape", "rueda_escape_diametro").en_mm / 2.0
        - a.valor("ancora_cubo_diametro").en_mm / 2.0
    )
    assert a.valor("ancora_hueco_a_la_rueda").en_mm == pytest.approx(hueco, abs=0.01)
    assert hueco >= 3.0


def test_la_ranura_no_llega_al_cubo(reloj: Contratos):
    a = reloj.contrato("ancora")
    assert (
        a.valor("ancora_ranura_al_eje").en_mm - a.valor("ancora_cubo_diametro").en_mm / 2.0 >= 5.0
    )


def test_la_caja_del_ancora_sale_de_sus_brazos(reloj: Contratos):
    a = reloj.contrato("ancora")
    brazo = a.valor("ancora_brazo_material").en_mm
    medio = a.valor("ancora_angulo_brazos").valor / 2.0
    assert a.valor("ancora_caja_ancho").en_mm == pytest.approx(
        2.0 * brazo * math.sin(medio) + a.valor("ancora_brazo_ancho").en_mm, abs=0.1
    )
    assert a.valor("ancora_caja_alto").en_mm == pytest.approx(
        brazo * math.cos(medio)
        + a.valor("ancora_cubo_diametro").en_mm / 2.0
        + a.valor("ancora_brazo_ancho").en_mm / 2.0,
        abs=0.1,
    )


def test_el_ancora_y_la_rueda_comparten_collar(reloj: Contratos):
    assert reloj.valor("ancora", "ancora_cubo_diametro").en_mm == pytest.approx(
        reloj.valor("rueda_escape", "rueda_escape_cubo_diametro").en_mm, abs=0.01
    )


def test_el_diente_se_define_con_tres_angulos(reloj: Contratos):
    """Socavado, ángulo incluido y espesor de punta. La demostración de
    Wolfram los parametriza por separado y tiene razón: dicen cosas distintas
    y los tres hacen falta para cortar el diente."""
    r = reloj.contrato("rueda_escape")
    for clave in (
        "rueda_escape_socavado",
        "rueda_escape_angulo_incluido",
        "rueda_escape_espesor_punta",
    ):
        assert r.valor(clave).valor > 0.0


def test_la_punta_del_diente_no_es_un_filo(reloj: Contratos):
    """Medio grado de espesor a radio 45 son 0,39 mm de material, y es justo
    donde apoya la paleta. Dibujar la punta afilada promete un filo que el
    contrachapado no da."""
    r = reloj.contrato("rueda_escape")
    radio = r.valor("rueda_escape_diametro").en_mm / 2.0
    assert radio * r.valor("rueda_escape_espesor_punta").valor >= 0.3


def test_los_tres_angulos_del_diente_caben_en_el_paso(reloj: Contratos):
    """Socavado y espesor de punta se reparten el paso angular con el hueco
    por donde entra la segueta. Si se lo comen entero, no hay hueco."""
    r = reloj.contrato("rueda_escape")
    gastado = r.valor("rueda_escape_espesor_punta").valor + math.atan(
        r.valor("rueda_escape_altura_diente").en_mm
        * math.tan(r.valor("rueda_escape_socavado").valor)
        / (r.valor("rueda_escape_diametro").en_mm / 2.0)
    )
    assert gastado < r.valor("rueda_escape_paso_angular").valor / 2.0


def test_el_fondo_relativo_sale_de_los_dos_diametros(reloj: Contratos):
    r = reloj.contrato("rueda_escape")
    assert r.valor("rueda_escape_fondo_relativo").valor == pytest.approx(
        r.valor("rueda_escape_diametro_fondo").en_mm / r.valor("rueda_escape_diametro").en_mm,
        abs=0.001,
    )


def test_la_rueda_lleva_radios_y_no_es_un_disco(reloj: Contratos):
    """Este es el eje más rápido del reloj: la masa que se le quite vale por
    el cuadrado de la velocidad en la inercia que hay que vencer."""
    radios = reloj.valor("rueda_escape", "rueda_escape_radios").valor
    assert radios in (3.0, 4.0, 5.0, 6.0)


def test_el_dorso_se_lleva_lo_que_la_cuna_deja(reloj: Contratos):
    """El ángulo incluido es la cuña de la punta, no una cota suelta: entre la
    cara y el dorso reparten el diente, y el dorso se lleva lo que queda."""
    r = reloj.contrato("rueda_escape")
    assert r.valor("rueda_escape_dorso_inclinacion").valor == pytest.approx(
        r.valor("rueda_escape_angulo_incluido").valor - r.valor("rueda_escape_socavado").valor,
        abs=1e-6,
    )


def test_los_dos_angulos_centrales_salen_de_los_de_la_punta(reloj: Contratos):
    """El socavado y el dorso se miden EN LA PUNTA; el boceto se construye
    desde el centro. Las dos conversiones son lo que se teclea al trazar, y
    por eso están declaradas en vez de calcularse con un lápiz."""
    r = reloj.contrato("rueda_escape")
    radio = r.valor("rueda_escape_diametro").en_mm / 2.0
    altura = r.valor("rueda_escape_altura_diente").en_mm
    for central, punta in (
        ("rueda_escape_punta_adelanto", "rueda_escape_socavado"),
        ("rueda_escape_dorso_retraso", "rueda_escape_dorso_inclinacion"),
    ):
        assert r.valor(central).valor == pytest.approx(
            math.atan(altura * math.tan(r.valor(punta).valor) / radio), abs=1e-6
        ), central


def test_el_diente_deja_hueco_para_la_sierra(reloj: Contratos):
    """LA envolvente de fabricación que faltaba. El dorso NO llega al fondo
    del diente siguiente: si llegase, el perfil sería una onda continua y no
    habría por dónde meter la segueta. El hueco tiene que dar al menos para
    girar la hoja, que son unos 3 mm."""
    r = reloj.contrato("rueda_escape")
    hueco = r.valor("rueda_escape_hueco_angular").valor
    assert hueco == pytest.approx(
        r.valor("rueda_escape_paso_angular").valor
        - r.valor("rueda_escape_punta_adelanto").valor
        - r.valor("rueda_escape_espesor_punta").valor
        - r.valor("rueda_escape_dorso_retraso").valor,
        abs=1e-6,
    )
    arco = r.valor("rueda_escape_diametro_fondo").en_mm / 2.0 * hueco
    assert arco >= 3.0, f"el hueco entre dientes son {arco:.1f} mm y la segueta no gira"


def test_el_diente_no_invade_al_de_al_lado(reloj: Contratos):
    r = reloj.contrato("rueda_escape")
    ocupa = (
        r.valor("rueda_escape_punta_adelanto").valor
        + r.valor("rueda_escape_espesor_punta").valor
        + r.valor("rueda_escape_dorso_retraso").valor
    )
    assert ocupa < r.valor("rueda_escape_paso_angular").valor / 2.0


def test_los_radios_dejan_pasar_el_cubo(reloj: Contratos):
    r = reloj.contrato("rueda_escape")
    assert r.valor("rueda_escape_radio_ancho").en_mm < r.valor("rueda_escape_cubo_diametro").en_mm


def test_la_cuerda_entre_dientes_no_es_el_paso_de_arco(reloj: Contratos):
    """Lo que mide un pie de rey es la CUERDA, no el arco. A este tamaño la
    diferencia es 0,17 décimas y da igual; al escalar la rueda, no."""
    r = reloj.contrato("rueda_escape")
    radio = r.valor("rueda_escape_diametro").en_mm / 2.0
    cuerda = r.valor("rueda_escape_cuerda_diente").en_mm
    assert cuerda == pytest.approx(
        2.0 * radio * math.sin(r.valor("rueda_escape_paso_angular").valor / 2.0), abs=0.01
    )
    assert cuerda < r.valor("rueda_escape_paso_diente").en_mm


def test_la_medida_de_verificacion_salta_cinco_dientes(reloj: Contratos):
    """LA medida con la que se comprueba una rueda cortada: el error de
    lectura del pie de rey se reparte entre cinco dientes en vez de caer sobre
    uno, y pasa del 0,5 % al 0,11 %."""
    r = reloj.contrato("rueda_escape")
    radio = r.valor("rueda_escape_diametro").en_mm / 2.0
    assert r.valor("rueda_escape_cuerda_cinco").en_mm == pytest.approx(
        2.0 * radio * math.sin(5.0 * r.valor("rueda_escape_paso_angular").valor / 2.0), abs=0.01
    )


def test_con_treinta_dientes_la_verificacion_vale_el_radio(reloj: Contratos):
    """Cinco pasos de 12° son 60° exactos, y la cuerda de 60° vale el radio.
    Que la medida de comprobación salga en 45,000 clavados no es casualidad:
    es lo que hace que se pueda cantar de memoria en el taller."""
    r = reloj.contrato("rueda_escape")
    if reloj.valor("escape", "dientes_escape").valor != 30.0:
        pytest.skip("la coincidencia es propia de 30 dientes")
    assert r.valor("rueda_escape_cuerda_cinco").en_mm == pytest.approx(
        r.valor("rueda_escape_diametro").en_mm / 2.0, abs=0.01
    )
