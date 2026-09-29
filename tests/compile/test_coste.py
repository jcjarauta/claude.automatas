"""Lo que cuesta un escribiente, y de dónde sale cada número.

Dos cosas se comprueban aquí y son de naturaleza distinta. El **recorrido de
la herramienta** es geometría y tiene respuesta exacta: un círculo fresado
por fuera con una fresa de radio r recorre la circunferencia del círculo más
2·pi·r, y eso se contrasta contra la fórmula cerrada. El **precio** es dato,
y lo único que se puede comprobar de un dato es que se lee, que se normaliza
igual para todos y que nadie lo inventa por el camino.
"""

from __future__ import annotations

import json
import math
from pathlib import Path

import pytest

from compile.coste import (
    IVA,
    Fresado,
    Tarifa,
    cargar_precios,
    con_iva,
    recorrido,
    tiempo_de_fresado,
    valorar,
)
from compile.escribiente import Escribiente, compilar
from core.escritura import Escritura, Trazo
from core.units import mm
from emit.pieza import Pieza, Taladro, Veta

PRECIOS = Path("bench/precios.json")


def hola() -> Escritura:
    datos = json.loads(Path("demo/hola.json").read_text(encoding="utf-8"))
    return Escritura(
        nombre=datos["nombre"],
        trazos=[
            Trazo(puntos=[(mm(float(x)), mm(float(y))) for x, y in trazo])
            for trazo in datos["trazos"]
        ],
    )


def disco(radio_mm: float, lados: int = 2048, taladros: list[Taladro] | None = None) -> Pieza:
    angulos = [2.0 * math.pi * i / lados for i in range(lados)]
    return Pieza(
        nombre="disco de prueba",
        numero="T-001",
        conjunto="pruebas",
        material="POM 5 mm",
        espesor=mm(5.0),
        cantidad=1,
        veta=Veta.INDIFERENTE,
        contorno=[(mm(radio_mm * math.cos(a)), mm(radio_mm * math.sin(a))) for a in angulos],
        taladros=taladros or [],
    )


# ---------------------------------------------------------------------------
# Recorrido: esto es geometría y tiene respuesta exacta
# ---------------------------------------------------------------------------


def test_el_contorno_se_recorre_por_fuera_y_por_eso_es_mas_largo_que_la_pieza():
    """La fresa va por el centro de su propio diámetro, desplazada hacia
    fuera medio diámetro. En un círculo eso son 2·pi·r_fresa de más, y es
    el error que se comete al presupuestar con el perímetro de la pieza."""
    fresado = Fresado(diametro_fresa=mm(3.0))
    camino = recorrido(disco(50.0), mm(5.0), fresado)
    nominal = 2.0 * math.pi * 0.050
    esperado = nominal + 2.0 * math.pi * 0.0015
    assert camino.contorno == pytest.approx(esperado, rel=1e-3)
    assert camino.contorno > nominal


def test_un_taladro_mayor_que_la_fresa_se_interpola_y_uno_igual_se_pincha():
    """Con fresa de Ø3, el Ø10 del eje se hace dando vueltas y el Ø3 del
    pasador se hace bajando en vertical. Son dos tiempos muy distintos y
    confundirlos es lo que hace que un presupuesto se quede corto."""
    fresado = Fresado(diametro_fresa=mm(3.0))
    grande = disco(50.0, taladros=[Taladro(centro=(mm(0.0), mm(0.0)), diametro=mm(10.0))])
    justo = disco(50.0, taladros=[Taladro(centro=(mm(0.0), mm(0.0)), diametro=mm(3.0))])
    # Interpolado: una vuelta por pasada sobre el círculo medio, Ø10 - Ø3.
    assert recorrido(grande, mm(5.0), fresado).taladros == pytest.approx(math.pi * 0.007)
    assert recorrido(grande, mm(5.0), fresado).pinchazos == 0.0
    # Pinchado: se baja el espesor entero de una vez, sin dar vueltas.
    assert recorrido(justo, mm(5.0), fresado).pinchazos == pytest.approx(0.005)
    assert recorrido(justo, mm(5.0), fresado).taladros == 0.0


def test_una_pieza_mas_gruesa_pide_mas_pasadas_y_mas_tiempo():
    fresado = Fresado(profundidad_por_pasada=mm(2.0))
    fino = tiempo_de_fresado([disco(50.0)], mm(4.0), fresado)
    grueso = tiempo_de_fresado([disco(50.0)], mm(8.0), fresado)
    assert grueso > fino


def test_el_tiempo_no_depende_de_cuantos_vertices_tenga_el_poligono():
    """Un perfil de leva se guarda con 720 muestras y podría guardarse con
    7200. Lo que se fresa es el mismo canto: si el tiempo cambiara con el
    muestreo, el presupuesto dependería de un detalle de representación."""
    fresado = Fresado()
    poco = tiempo_de_fresado([disco(50.0, lados=360)], mm(5.0), fresado)
    mucho = tiempo_de_fresado([disco(50.0, lados=7200)], mm(5.0), fresado)
    assert mucho == pytest.approx(poco, rel=1e-3)


def test_doblar_el_avance_reduce_el_tiempo_a_la_mitad():
    lento = Fresado(avance_por_diente=mm(0.03))
    rapido = Fresado(avance_por_diente=mm(0.06))
    assert tiempo_de_fresado([disco(50.0)], mm(5.0), rapido) == pytest.approx(
        tiempo_de_fresado([disco(50.0)], mm(5.0), lento) / 2.0
    )


# ---------------------------------------------------------------------------
# Tarifa: lo que manda no es la hora, es el mínimo
# ---------------------------------------------------------------------------


def test_la_preparacion_se_paga_una_vez_por_lote_y_no_por_pieza():
    """Es toda la diferencia entre cortar las tres levas de un pedido en un
    amarre o en tres, y es la partida mayor del cartucho."""
    tarifa = Tarifa(euros_por_hora=55.0, preparacion_minutos=15.0)
    una = tarifa.coste(60.0)
    tres = tarifa.coste(180.0)
    assert tres < 3.0 * una


def test_el_minimo_facturable_se_impone_cuando_el_trabajo_es_diminuto():
    tarifa = Tarifa(euros_por_hora=55.0, preparacion_minutos=0.0, minimo_facturable=30.0)
    assert tarifa.coste(60.0) == pytest.approx(30.0)


def test_sin_minimo_el_coste_es_proporcional_al_tiempo():
    tarifa = Tarifa(euros_por_hora=60.0, preparacion_minutos=0.0, minimo_facturable=0.0)
    assert tarifa.coste(1800.0) == pytest.approx(30.0)


# ---------------------------------------------------------------------------
# Precios: lo único comprobable de un dato es que no se inventa
# ---------------------------------------------------------------------------


def test_todo_se_normaliza_a_iva_incluido():
    """Arrels no repercute IVA en la mayor parte de su actividad, así que el
    IVA soportado es coste. Mezclar precios con y sin IVA en la misma suma
    es un error del 21 % que no se ve."""
    assert con_iva(100.0, iva_incluido=True) == pytest.approx(100.0)
    assert con_iva(100.0, iva_incluido=False) == pytest.approx(100.0 * (1.0 + IVA))


def test_el_fichero_de_precios_se_lee_y_lleva_fecha():
    precios = cargar_precios(PRECIOS)
    assert precios.fecha
    assert precios.cartucho
    assert precios.plataforma


def test_toda_linea_de_precio_lleva_fuente():
    """Un precio sin enlace es un precio inventado dentro de seis meses."""
    precios = cargar_precios(PRECIOS)
    for linea in precios.cartucho + precios.plataforma:
        assert linea.url, f"{linea.concepto} no dice de dónde sale"


def test_lo_no_verificado_esta_marcado_y_se_puede_contar():
    precios = cargar_precios(PRECIOS)
    sin_verificar = [linea for linea in precios.plataforma if not linea.verificado]
    assert all(linea.pedir for linea in sin_verificar), "lo no verificado dice qué hay que pedir"


# ---------------------------------------------------------------------------
# La valoración entera
# ---------------------------------------------------------------------------


def test_la_valoracion_del_cartucho_separa_material_de_mecanizado():
    valoracion = valorar(compilar(hola()), Escribiente(), cargar_precios(PRECIOS))
    assert valoracion.material_del_cartucho > 0.0
    assert valoracion.mecanizado > 0.0
    assert valoracion.cartucho == pytest.approx(
        valoracion.material_del_cartucho + valoracion.mecanizado + valoracion.comercial_del_cartucho
    )


def test_el_mecanizado_pesa_mas_que_el_material_de_las_levas():
    """Es la conclusión que cambia dónde mirar: la plancha de POM es
    calderilla y el tiempo de máquina no."""
    valoracion = valorar(compilar(hola()), Escribiente(), cargar_precios(PRECIOS))
    assert valoracion.mecanizado > 5.0 * valoracion.material_del_cartucho


def test_una_frase_mas_larga_no_encarece_el_corte_de_forma_apreciable():
    """El perímetro de la leva apenas cambia con la frase —lo que cambia es
    la ondulación, no el tamaño—, así que el precio del cartucho es estable
    y se puede dar antes de compilar."""
    corta = valorar(compilar(hola()), Escribiente(), cargar_precios(PRECIOS))
    larga_escritura = Escritura(
        nombre="hola hola",
        trazos=[*hola().trazos, Trazo(puntos=[(mm(x), mm(2.0)) for x in (40.0, 50.0, 60.0)])],
    )
    larga = valorar(compilar(larga_escritura), Escribiente(), cargar_precios(PRECIOS))
    assert larga.mecanizado == pytest.approx(corta.mecanizado, rel=0.15)


def test_la_maquina_propia_se_amortiza_y_el_informe_dice_en_cuanto():
    valoracion = valorar(compilar(hola()), Escribiente(), cargar_precios(PRECIOS))
    assert valoracion.pedidos_para_amortizar(2249.0) > 0
    # Más barato por pedido significa que hacen falta más pedidos para pagarla.
    barata = valoracion.pedidos_para_amortizar(1000.0)
    cara = valoracion.pedidos_para_amortizar(4000.0)
    assert cara > barata


def test_el_total_de_la_maquina_suma_cartucho_y_plataforma():
    valoracion = valorar(compilar(hola()), Escribiente(), cargar_precios(PRECIOS))
    assert valoracion.total == pytest.approx(valoracion.cartucho + valoracion.plataforma)


def test_el_tiempo_cuadra_con_el_volumen_arrancado():
    """Contraste por un segundo camino, que no comparte una línea de código
    con el primero: el desbaste tiene que arrancar todo el material de la
    ranura, y a una tasa de arranque conocida eso da un tiempo. El del
    modelo es mayor porque incluye el acabado, pero del mismo orden. Si se
    separaran, uno de los dos estaría mal planteado."""
    fresado = Fresado()
    pieza = disco(50.0, taladros=[Taladro(centro=(mm(0.0), mm(0.0)), diametro=mm(10.0))])
    espesor = mm(5.0)

    volumen = 2.0 * math.pi * 0.050 * float(fresado.diametro_fresa) * float(
        espesor
    ) + math.pi * 0.005**2 * float(espesor)
    tasa = (
        float(fresado.diametro_fresa)
        * float(fresado.profundidad_por_pasada)
        * fresado.avance
        * fresado.rendimiento
    )
    por_volumen = volumen / tasa
    por_recorrido = tiempo_de_fresado([pieza], espesor, fresado)

    assert por_recorrido > por_volumen, "el acabado tiene que costar algo"
    assert por_recorrido < 2.5 * por_volumen, "y no puede costar más que el desbaste entero"
