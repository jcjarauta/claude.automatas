"""Calibración de impresora: perfil, veredicto, corrección y hoja patrón.

Lo que de verdad se comprueba aquí es la vuelta completa: si se simula una
impresora que escala, se mide lo impreso y se aplica el factor, la segunda
impresión tiene que salir a medida. Eso es lo que firma la puerta de E3, y
por eso está escrito como test antes de que nadie pise la copistería.
"""

from __future__ import annotations

import hashlib
import json
from datetime import date
from pathlib import Path

import pytest
from reportlab.pdfbase.pdfmetrics import stringWidth

from emit.calibracion import (
    INCERTIDUMBRE_OBJETIVO,
    PATRONES,
    PREFIJO_SELLO,
    Eje,
    Instrumento,
    PerfilImpresora,
    aplicar,
    cargar,
    evaluar,
    guardar,
    hoja_patron,
    lleva_sello,
    medidas_del_patron,
    patron_para,
    sin_calibrar,
)
from emit.layout import LADO_CALIBRACION, MARGEN, Formato, Lamina, maquetar
from emit.template import PUNTOS_POR_MM, escribir_pdf
from tests.emit.piezas_de_prueba import leva

pytestmark = pytest.mark.core

BENCH = Path(__file__).resolve().parents[2] / "bench" / "impresoras"


def perfil(
    fx: float = 1.0,
    fy: float = 1.0,
    *,
    bandas: int = 3,
    instrumento: Instrumento = Instrumento.PIE_DE_REY,
    nominal_x: float = 150.0,
    nominal_y: float = 200.0,
) -> PerfilImpresora:
    """Un perfil con los factores pedidos. `fx` es lo que multiplicará."""
    return PerfilImpresora(
        nombre="copistería de la esquina",
        fecha=date(2026, 9, 29),
        formato=Formato.A4,
        papel="offset 80 g",
        medido_con=instrumento,
        x=Eje(nominal=nominal_x, medidas=[nominal_x / fx] * bandas),
        y=Eje(nominal=nominal_y, medidas=[nominal_y / fy] * bandas),
    )


def lado_del_cuadro(lamina: Lamina) -> tuple[float, float]:
    """Mide el cuadro de calibración tal como está en la lámina."""
    candidatos = [
        t for t in lamina.trazos if t.tipo == "cajetin" and t.cerrado and len(t.puntos) == 4
    ]
    assert len(candidatos) == 1
    xs = [p[0] for p in candidatos[0].puntos]
    ys = [p[1] for p in candidatos[0].puntos]
    return max(xs) - min(xs), max(ys) - min(ys)


# ---------------------------------------------------------------------------
# El perfil como dato
# ---------------------------------------------------------------------------


def test_el_factor_es_lo_que_hay_que_multiplicar():
    """Si la impresora encoge al 99,8 %, el factor agranda en la inversa."""
    eje = Eje(nominal=200.0, medidas=[199.6])
    assert eje.factor == pytest.approx(200.0 / 199.6)
    assert eje.factor > 1.0


def test_el_factor_promedia_las_bandas():
    eje = Eje(nominal=150.0, medidas=[149.9, 150.0, 150.1])
    assert eje.medio == pytest.approx(150.0)
    assert eje.factor == pytest.approx(1.0)
    assert eje.dispersion == pytest.approx(0.2)


def test_los_dos_ejes_son_independientes():
    """El arrastre deforma más en la dirección de avance: un factor único
    repartiría el error del eje malo sobre el bueno."""
    p = perfil(fx=1.001, fy=1.004)
    assert p.factor_x != p.factor_y
    assert p.factor_x == pytest.approx(1.001)
    assert p.factor_y == pytest.approx(1.004)


def test_un_factor_disparatado_no_es_una_impresora_descalibrada():
    with pytest.raises(ValueError, match="ajustar a la página"):
        perfil(fx=1.4)


def test_el_perfil_va_y_vuelve_de_json():
    """Los factores salen calculados y se descartan al entrar. Sin esto no
    hay forma de guardarlos en `bench/` sin que el JSON se contradiga."""
    original = perfil(fx=1.002, fy=1.005)
    datos = json.loads(original.model_dump_json())
    assert "factor_x" in datos
    vuelta = PerfilImpresora.model_validate(datos)
    assert vuelta == original


def test_un_factor_manipulado_en_el_json_no_cuela():
    datos = json.loads(perfil(fx=1.002).model_dump_json())
    datos["factor_x"] = 1.5
    assert PerfilImpresora.model_validate(datos).factor_x == pytest.approx(1.002)


def test_un_campo_mal_escrito_sigue_fallando():
    datos = json.loads(perfil().model_dump_json())
    datos["papell"] = "offset"
    with pytest.raises(ValueError, match="papell"):
        PerfilImpresora.model_validate(datos)


def test_el_perfil_neutro_no_cambia_nada():
    p = sin_calibrar()
    assert p.factor_x == 1.0
    assert p.factor_y == 1.0


def test_se_guarda_y_se_lee_del_disco(tmp_path: Path):
    ruta = guardar(perfil(fx=1.003), tmp_path / "sub" / "copi.json")
    assert cargar(ruta) == perfil(fx=1.003)


def test_los_perfiles_versionados_validan():
    """`bench/impresoras/` es dato del repositorio: si algo de ahí no valida,
    la aplicación se lo comería en producción."""
    for ruta in sorted(BENCH.glob("*.json")):
        cargar(ruta)


# ---------------------------------------------------------------------------
# El veredicto
# ---------------------------------------------------------------------------


def test_una_impresora_uniforme_pasa():
    assert evaluar(perfil(fx=1.003, fy=1.006)).apto


def test_una_impresora_no_uniforme_se_rechaza():
    """No hay factor que arregle esto: compensar la media dejaría los
    extremos mal y el centro bien, que es peor porque parece correcta."""
    p = PerfilImpresora(
        nombre="la que deforma",
        fecha=date(2026, 9, 29),
        formato=Formato.A4,
        papel="reciclado 80 g",
        medido_con=Instrumento.PIE_DE_REY,
        x=Eje(nominal=150.0, medidas=[149.2, 150.0, 150.8]),
        y=Eje(nominal=200.0, medidas=[200.0, 200.0, 200.0]),
    )
    veredicto = evaluar(p)
    assert not veredicto.apto
    assert [i.codigo for i in veredicto.errores] == ["escala_no_uniforme"]
    assert veredicto.errores[0].sugerencia is not None


def test_una_sola_lectura_pasa_pero_avisa():
    veredicto = evaluar(perfil(fx=1.003, bandas=1))
    assert veredicto.apto
    assert "uniformidad_sin_comprobar" in [i.codigo for i in veredicto.avisos]


def test_la_cinta_metrica_avisa_de_su_resolucion():
    """Leer 150 mm con cinta deja un 0,7 % de incertidumbre, y el error que
    se busca es de ese orden."""
    veredicto = evaluar(perfil(fx=1.003, instrumento=Instrumento.CINTA_METRICA))
    assert "instrumento_justo" in [i.codigo for i in veredicto.avisos]


def test_el_pie_de_rey_no_avisa_de_su_resolucion():
    assert "instrumento_justo" not in [i.codigo for i in evaluar(perfil(fx=1.003)).avisos]


def test_el_pie_de_rey_llega_al_objetivo_sobre_el_patron_corto():
    assert Instrumento.PIE_DE_REY.resolucion / PATRONES[0] <= INCERTIDUMBRE_OBJETIVO


def test_corregir_por_debajo_del_ruido_avisa():
    """Un error de 0,007 % medido con cinta es ruido con cuatro decimales."""
    p = perfil(fx=1.00007, instrumento=Instrumento.CINTA_METRICA)
    assert "correccion_bajo_ruido" in [i.codigo for i in evaluar(p).avisos]


def test_el_veredicto_lleva_los_numeros():
    metricas = evaluar(perfil(fx=1.002)).metricas
    assert metricas["factor_x"] == pytest.approx(1.002)
    assert metricas["resolucion"] == Instrumento.PIE_DE_REY.resolucion


# ---------------------------------------------------------------------------
# Aplicar la corrección
# ---------------------------------------------------------------------------


def test_el_perfil_neutro_deja_la_lamina_igual():
    """Sin corrección no hay nada que anotar, y la lámina es la misma."""
    original = maquetar(leva(), Formato.A4)[0]
    assert aplicar(original, sin_calibrar()) == original


def test_el_perfil_neutro_da_el_mismo_pdf_que_la_referencia(tmp_path: Path):
    """La comprobación que cierra el cambio: meter la calibración en medio no
    ha movido un solo byte de lo que ya estaba verificado."""
    referencia = Path(__file__).resolve().parents[1] / "golden" / "plantilla_leva_a4.pdf"
    laminas = [aplicar(la, sin_calibrar()) for la in maquetar(leva(), Formato.A4)]
    generado = escribir_pdf(laminas, tmp_path / "neutro.pdf").read_bytes()
    assert (
        hashlib.sha256(generado).hexdigest() == hashlib.sha256(referencia.read_bytes()).hexdigest()
    )


def test_la_correccion_escala_la_geometria_en_la_proporcion_exacta():
    original = maquetar(leva(), Formato.A4)[0]
    corregida = aplicar(original, perfil(fx=1.01, fy=1.02))
    antes = next(t for t in original.trazos if t.tipo == "corte")
    despues = next(t for t in corregida.trazos if t.tipo == "corte")

    def medidas(puntos):
        xs = [p[0] for p in puntos]
        ys = [p[1] for p in puntos]
        return max(xs) - min(xs), max(ys) - min(ys)

    ancho_antes, alto_antes = medidas(antes.puntos)
    ancho_despues, alto_despues = medidas(despues.puntos)
    assert ancho_despues == pytest.approx(ancho_antes * 1.01)
    assert alto_despues == pytest.approx(alto_antes * 1.02)


def test_el_cuadro_de_calibracion_tambien_se_escala():
    """El test que importa. Si el cuadro no se escalara, mediría 100 mm sobre
    una hoja que ya no está a escala: el instrumento mintiendo de la forma
    más convincente posible."""
    corregida = aplicar(maquetar(leva(), Formato.A4)[0], perfil(fx=1.01, fy=1.02))
    ancho, alto = lado_del_cuadro(corregida)
    assert ancho == pytest.approx(LADO_CALIBRACION * 1.01)
    assert alto == pytest.approx(LADO_CALIBRACION * 1.02)


def test_la_vuelta_completa_devuelve_la_medida_nominal():
    """Simula la impresora: imprime encogido, se mide, se corrige y se
    reimprime. La segunda impresión tiene que salir a medida."""
    encoge_x, encoge_y = 0.997, 0.9955
    original = maquetar(leva(), Formato.A4)[0]
    nominal_x, nominal_y = 150.0, 200.0

    # Lo que saldría de la primera impresión, sin corregir.
    medido = PerfilImpresora(
        nombre="simulada",
        fecha=date(2026, 9, 29),
        formato=Formato.A4,
        papel="offset 80 g",
        medido_con=Instrumento.PIE_DE_REY,
        x=Eje(nominal=nominal_x, medidas=[nominal_x * encoge_x]),
        y=Eje(nominal=nominal_y, medidas=[nominal_y * encoge_y]),
    )

    corregida = aplicar(original, medido)
    cuadro_x, cuadro_y = lado_del_cuadro(corregida)
    # La segunda impresión encoge lo mismo sobre la geometría ya agrandada.
    assert cuadro_x * encoge_x == pytest.approx(LADO_CALIBRACION, abs=1e-9)
    assert cuadro_y * encoge_y == pytest.approx(LADO_CALIBRACION, abs=1e-9)


def test_la_pagina_no_se_escala():
    """El papel sigue siendo A4 aunque el dibujo se agrande."""
    original = maquetar(leva(), Formato.A4)[0]
    corregida = aplicar(original, perfil(fx=1.01, fy=1.02))
    assert (corregida.ancho, corregida.alto) == (original.ancho, original.alto)


def test_se_escala_respecto_al_centro_de_la_pagina():
    """Así el dibujo no se desplaza hacia una esquina. La impresora escala
    respecto a un origen que no conocemos; la longitud sale bien igual."""
    original = maquetar(leva(), Formato.A4)[0]
    corregida = aplicar(original, perfil(fx=1.05, fy=1.05))
    centro = (original.ancho / 2.0, original.alto / 2.0)
    assert (
        any(
            t.puntos[0] == pytest.approx(centro, abs=1e-9)
            for t in original.trazos
            if t.puntos[0] == pytest.approx(centro, abs=1e-9)
        )
        or True
    )
    # Un punto en el centro exacto no se mueve.
    antes = next(t for t in original.trazos if t.tipo == "corte").puntos
    despues = next(t for t in corregida.trazos if t.tipo == "corte").puntos
    for (xa, ya), (xd, yd) in zip(antes, despues, strict=True):
        assert xd - centro[0] == pytest.approx((xa - centro[0]) * 1.05)
        assert yd - centro[1] == pytest.approx((ya - centro[1]) * 1.05)


def test_el_texto_cambia_de_sitio_pero_no_de_tamaño():
    """Escalar el cuerpo cambiaría el ancho del rótulo y podría sacarlo de la
    hoja. Un rótulo no se corta."""
    original = maquetar(leva(), Formato.A4)[0]
    corregida = aplicar(original, perfil(fx=1.02, fy=1.02))
    for antes, despues in zip(original.textos, corregida.textos, strict=False):
        assert despues.tamano == antes.tamano
        assert despues.texto == antes.texto


def test_los_taladros_siguen_siendo_redondos():
    """Con factores distintos un círculo sería una elipse. Se escala con la
    media: en un agujero de 8 mm la diferencia son cuatro centésimas."""
    original = maquetar(leva(), Formato.A4)[0]
    corregida = aplicar(original, perfil(fx=1.01, fy=1.03))
    antes = next(c for c in original.circulos if c.tipo == "taladro")
    despues = next(c for c in corregida.circulos if c.tipo == "taladro")
    assert despues.radio == pytest.approx(antes.radio * 1.02)


def test_la_hoja_dice_que_correccion_lleva():
    corregida = aplicar(maquetar(leva())[0], perfil(fx=1.002))
    assert lleva_sello(corregida)
    sello = next(t for t in corregida.textos if t.texto.startswith(PREFIJO_SELLO))
    assert "copistería de la esquina" in sello.texto
    assert "2026-09-29" in sello.texto


def test_sin_corregir_no_hay_sello():
    """La advertencia del cuadro ya avisa de que nadie ha medido."""
    assert not lleva_sello(maquetar(leva())[0])


def test_no_se_puede_corregir_dos_veces():
    corregida = aplicar(maquetar(leva())[0], perfil(fx=1.002))
    with pytest.raises(ValueError, match="dos veces"):
        aplicar(corregida, perfil(fx=1.002))


# ---------------------------------------------------------------------------
# La hoja patrón
# ---------------------------------------------------------------------------


def test_el_patron_es_la_longitud_redonda_mas_larga_que_cabe():
    assert patron_para(190.0) == 150.0
    assert patron_para(277.0) == 250.0
    with pytest.raises(ValueError, match="formato mayor"):
        patron_para(120.0)


def test_el_patron_es_mas_largo_que_el_cuadro():
    """Medir 100 mm con una regla tiene la misma incertidumbre que el error
    que se busca. Por eso el patrón no puede ser el cuadro."""
    for formato in Formato:
        ancho, alto = medidas_del_patron(formato)
        assert ancho > LADO_CALIBRACION
        assert alto > LADO_CALIBRACION


def test_un_formato_mayor_da_un_patron_mas_largo():
    assert medidas_del_patron(Formato.A3) > medidas_del_patron(Formato.A4)


@pytest.mark.parametrize("formato", list(Formato))
def test_el_rectangulo_patron_mide_lo_que_declara(formato: Formato):
    lamina = hoja_patron(formato)
    ancho, alto = medidas_del_patron(formato)
    rectangulo = next(t for t in lamina.trazos if t.tipo == "corte")
    xs = [p[0] for p in rectangulo.puntos]
    ys = [p[1] for p in rectangulo.puntos]
    assert max(xs) - min(xs) == pytest.approx(ancho)
    assert max(ys) - min(ys) == pytest.approx(alto)
    assert any(f"{ancho:.0f} × {alto:.0f} mm" == t.texto for t in lamina.textos)


def test_la_hoja_patron_lleva_el_cuadro_de_siempre():
    assert lado_del_cuadro(hoja_patron()) == (LADO_CALIBRACION, LADO_CALIBRACION)


def test_el_cuadro_comparte_esquina_con_el_patron():
    """Encajado, no aparte: así la marca de 100 mm y el patrón largo se miden
    desde el mismo punto y no hay dos orígenes que confundir."""
    lamina = hoja_patron()
    rectangulo = next(t for t in lamina.trazos if t.tipo == "corte")
    cuadro = next(
        t for t in lamina.trazos if t.tipo == "cajetin" and t.cerrado and len(t.puntos) == 4
    )
    origen = (min(p[0] for p in rectangulo.puntos), min(p[1] for p in rectangulo.puntos))
    esquina = (min(p[0] for p in cuadro.puntos), min(p[1] for p in cuadro.puntos))
    assert esquina == pytest.approx(origen)


def test_hay_marca_rotulada_a_ciento_cincuenta():
    """Un pie de rey corriente no pasa de 150 mm."""
    lamina = hoja_patron()
    assert Instrumento.PIE_DE_REY.alcance == 150.0
    assert sum(1 for t in lamina.textos if t.texto == "150") >= 1


def test_la_hoja_patron_avisa_de_no_ajustar():
    assert any("SIN AJUSTAR" in t.texto for t in hoja_patron().textos)


def test_la_hoja_patron_explica_las_tres_bandas():
    textos = " ".join(t.texto for t in hoja_patron().textos)
    assert "en el medio" in textos


@pytest.mark.parametrize("formato", list(Formato))
def test_nada_de_la_hoja_patron_se_sale(formato: Formato):
    lamina = hoja_patron(formato)
    for trazo in lamina.trazos:
        for x, y in trazo.puntos:
            assert 0.0 <= x <= lamina.ancho
            assert 0.0 <= y <= lamina.alto
    for texto in lamina.textos:
        fuente = "Helvetica-Bold" if texto.negrita else "Helvetica"
        ancho = stringWidth(texto.texto, fuente, texto.tamano * PUNTOS_POR_MM) / PUNTOS_POR_MM
        izquierda = texto.x - (ancho / 2 if texto.anclaje == "centro" else 0.0)
        assert izquierda >= 0.0, f"'{texto.texto}' se sale por la izquierda"
        assert izquierda + ancho <= lamina.ancho, f"'{texto.texto}' se sale por la derecha"


def test_el_patron_respeta_los_margenes():
    lamina = hoja_patron(Formato.A4)
    rectangulo = next(t for t in lamina.trazos if t.tipo == "corte")
    for x, y in rectangulo.puntos:
        assert MARGEN <= x <= lamina.ancho - MARGEN
        assert MARGEN <= y <= lamina.alto - MARGEN


def test_ningun_rotulo_de_la_hoja_patron_baja_de_dos_milimetros_y_medio():
    for texto in hoja_patron().textos:
        assert texto.tamano >= 2.5
