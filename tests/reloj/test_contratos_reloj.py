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
    angulo = list(modulo_csv.reader(tabla_onshape(reloj)[Tipo.ANGLE].strip().split("\n")))
    assert angulo[1][2] == "2 deg"


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


def test_la_cadena_del_pendulo_suma_la_longitud_nominal(reloj: Contratos):
    """Del punto de flexión del muelle al extremo de la varilla, más la
    varilla, más lo que hay del extremo al centro de la lenteja = 994.

    El largo de la varilla es DERIVADO de esta suma, no una elección. Antes
    lo era de `varilla_sobre_flexion`, que era una suposición marcada
    PENDIENTE; la ficha del muelle la sustituyó y el largo cambió solo. Este
    test es lo que hace que ese cambio no pueda pasar en silencio."""
    nominal = reloj.valor("oscilador", "longitud_pendulo_nominal").en_mm
    flexion = reloj.valor("suspension", "muelle_flexion_a_varilla").en_mm
    largo = reloj.valor("pendulo", "varilla_largo").en_mm
    centro = reloj.valor("lenteja", "lenteja_centro_bajo_varilla").en_mm
    assert flexion + largo + centro == pytest.approx(nominal)


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
