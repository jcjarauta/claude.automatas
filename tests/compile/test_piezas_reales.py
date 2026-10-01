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


def _existe(nombre: str) -> bool:
    try:
        contrato(nombre)
    except KeyError:
        return False
    return True


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


def test_el_contrato_y_el_compilador_dicen_lo_mismo_de_la_maquina():
    """**El cruce que faltaba, y es el que sostiene todo el paquete de CAD.**

    `docs/contratos.json` es lo que se importa al Variable Studio y con lo que
    se dibuja la plataforma; `Escribiente` es con lo que se sintetizan las
    levas. Nadie comprobaba que coincidieran. Si se tocara uno solo, el CAD
    dibujaría una máquina y el compilador cortaría levas para otra, y no
    saltaría nada hasta tener las piezas encima de la mesa.
    """
    maquina = Escribiente()
    for cota_, atributo in (
        ("brazo_separacion", "separacion"),
        ("brazo_proximal", "proximal"),
        ("brazo_distal", "distal"),
        ("brazo_palanca", "brazo_palanca"),
        ("brazo_seguidor", "brazo_seguidor"),
        ("radio_base", "radio_base"),
        ("rodillo_radio", "radio_rodillo"),
        ("caja_ancho", "caja_ancho"),
        ("caja_alto", "caja_alto"),
        ("caja_centro_y", "caja_centro_y"),
        ("eje_diametro", "taladro_eje"),
        ("pasador_diametro", "pasador_indice"),
        ("pasador_radio", "radio_del_pasador"),
    ):
        assert contrato(cota_) == pytest.approx(float(getattr(maquina, atributo))), cota_
    assert contrato("relacion_varillaje") == pytest.approx(maquina.relacion)


def test_el_canto_mecanizado_sale_de_la_fibra_neutra_y_no_al_reves():
    """**La trampa del cabestrante, y cuesta un cuarto de milímetro.**

    La relación la da el cociente de los radios por los que pasa la FIBRA
    NEUTRA de la cinta, no el de los cantos torneados. Como la cinta va por
    fuera de los dos, los dos cantos miden medio espesor menos — y restar lo
    mismo a dos números no conserva su cociente. Mecanizar 48 y 8 con una
    cinta de 0,05 da 5,9844 en vez de 6: un 0,26 % de escala de menos en todo lo que
    escriba la máquina, sistemático y sin un solo aviso.
    """
    espesor = contrato("cinta_espesor")
    for pieza_ in ("sector", "tambor"):
        neutra = contrato(f"amplificador_{pieza_}_radio")
        canto = contrato(f"amplificador_{pieza_}_radio_mecanizado")
        assert canto == pytest.approx(neutra - espesor / 2.0)
    # Y el cociente que importa es el de las fibras, que vale 6 exacto...
    fibras = contrato("amplificador_sector_radio") / contrato("amplificador_tambor_radio")
    assert fibras == pytest.approx(Escribiente().relacion)
    # ...mientras que el de los cantos NO, y por eso no se mecaniza a 48 y 8.
    cantos = contrato("amplificador_sector_radio_mecanizado") / contrato(
        "amplificador_tambor_radio_mecanizado"
    )
    assert cantos != pytest.approx(fibras, rel=1e-4)


def test_la_cinta_no_la_sujeta_nada_mas_que_sus_anclajes():
    """**Por que ni el sector ni el tambor llevan pestanas.**

    El tambor se dibujo primero con dos y el sector sin nada, y la pregunta
    obvia es por que uno si y el otro no. La respuesta es que ninguno las
    necesita: la cinta va anclada por los dos extremos, asi que no puede
    andar axialmente sin estirarse. Lo que de verdad la mantiene en su sitio
    es que los dos asientos sean coplanarios, y una pestana no arregla una
    desalineacion: roza contra ella.

    Por eso el contrato no declara ninguna pestana y si declara cuanto
    pueden desalinearse los dos asientos. SIN MEDIR: los 0,2 mm son un
    criterio, no una medida, y es de lo primero que tiene que mirar E4.
    """
    con_pestana = [
        n
        for n in ("amplificador_tambor_pestana_radio", "amplificador_sector_garganta")
        if _existe(n)
    ]
    assert not con_pestana, f"alguien ha vuelto a poner pestanas: {con_pestana}"
    assert contrato("amplificador_coplanaridad") > 0.0
    assert contrato("amplificador_tambor_ancho") > contrato("cinta_ancho")


def test_la_cinta_no_se_pasa_de_flexion_al_arrollar_el_tambor():
    """Una cinta que se dobla millones de veces quiere r/t >= 100. Con el
    fleje de 0,1 que se eligió primero y un tambor de R 8 salían 80, y
    1206 MPa de flexión; con 0,05, 160 y 603 MPa."""
    espesor = contrato("cinta_espesor")
    radio = contrato("amplificador_tambor_radio")
    assert radio / espesor >= 100.0
    assert 193e9 * espesor / (2.0 * radio) < 800e6


def test_la_cinta_cabe_en_el_canto_del_sector():
    """La cinta corre por el canto del sector: más ancha que el canto, se
    sale. Hoy los dos valen 5, y por eso son dos cotas y no una: si alguien
    estrechara la cinta, el sector NO tiene que adelgazarse con ella."""
    assert contrato("cinta_ancho") <= contrato("amplificador_sector_espesor")
    # Y el espesor del sector es el de la plancha que se compra, de una pieza.
    assert contrato("amplificador_sector_espesor") == pytest.approx(cota("plancha_pom", "espesor"))


def test_la_cinta_abraza_el_lado_opuesto_al_tambor():
    """**Donde la cinta toca el sector, medido y no razonado.**

    El punto de tangencia es aquel cuyo radio es perpendicular a la cinta.
    Imponiendo esa perpendicularidad sale cos(t) = (R-r)/a, o sea 53,97
    grados desde la direccion al tambor; y de los dos arcos que separan los
    dos puntos de tangencia, el que la cinta abraza es el de 252 grados, que
    pasa por el lado OPUESTO al tambor. Lo confirma la formula de correa
    abierta, pi + 2*gamma con sin(gamma) = (R-r)/a.

    El sector, al final, es un disco entero: la muesca de 80 grados que se
    llego a dibujar en el lado libre no compraba nada, porque el ramal sale
    tangente y se aleja, el tambor queda a 10 mm del borde y los discos
    vecinos se llevan 27.

    Este test existe porque se escribio dos veces mal: primero con el seno en
    vez del coseno, que ponia la tangencia a 126 grados, y despues con el
    material en el lado libre. Las dos veces por razonar en vez de medir.
    """
    sector = contrato("amplificador_sector_radio")
    tambor = contrato("amplificador_tambor_radio")
    entre = contrato("amplificador_entre_ejes")
    tang = contrato("amplificador_tangencia")
    assert tang == pytest.approx(math.acos((sector - tambor) / entre))
    assert math.degrees(tang) < 90.0, "la tangencia cae del lado del tambor"
    abrazado = 2.0 * (math.pi - tang)
    gamma = math.asin((sector - tambor) / entre)
    assert abrazado == pytest.approx(math.pi + 2.0 * gamma)
    assert math.degrees(abrazado) == pytest.approx(252.06, abs=0.01)
    # El vano libre es el cateto, y sale igual por los dos caminos.
    assert contrato("amplificador_vano_libre") == pytest.approx(entre * math.sin(tang))
    assert contrato("amplificador_vano_libre") == pytest.approx(entre * math.cos(gamma))


def test_una_mordaza_en_cada_pieza_y_no_las_dos_en_el_sector():
    """**El arreglo del anclaje no estaba abierto: lo cerraban estos numeros.**

    `docs/contratos.md` dio por abiertos dos arreglos, las dos mordazas en el
    sector con la cinta rodeando el tambor o una en cada pieza. Solo cabe el
    segundo: dos en el sector obligan a que uno de los dos ramales cruce, y un
    ramal cruzado tiene otro vano y otro abrazado.

    El contrato trae los de la correa ABIERTA, a seis decimales y por dos
    caminos que no se hablan: el vano y el arco del sector. Los de la cruzada
    no aparecen por ningun lado.

    La leccion es la de siempre aqui: antes de declarar algo abierto, mirar si
    los numeros que ya estan escritos lo deciden.
    """
    sector = contrato("amplificador_sector_radio")
    tambor = contrato("amplificador_tambor_radio")
    entre = contrato("amplificador_entre_ejes")
    abierta = math.sqrt(entre**2 - (sector - tambor) ** 2)
    cruzada = math.sqrt(entre**2 - (sector + tambor) ** 2)
    assert contrato("amplificador_vano_libre") == pytest.approx(abierta)
    assert contrato("amplificador_vano_libre") != pytest.approx(cruzada, abs=1e-3)

    gamma = math.asin((sector - tambor) / entre)
    gamma_cruzada = math.asin((sector + tambor) / entre)
    abraza = 2.0 * (math.pi - contrato("amplificador_tangencia"))
    assert abraza == pytest.approx(math.pi + 2.0 * gamma)
    assert abraza != pytest.approx(math.pi + 2.0 * gamma_cruzada, abs=1e-3)

    # Y el tambor abraza mas que la correa abierta: ese sobrante es lo que
    # paga el barrido del brazo y el anclaje, y es lo unico que queda por
    # repartir cuando se dibuje el tambor.
    assert contrato("amplificador_tambor_abrazado") > math.pi - 2.0 * gamma


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
