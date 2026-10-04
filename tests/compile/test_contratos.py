"""Los contratos como dato, y que el código no se aleje de ellos.

Hay dos clases de test aquí y la segunda es la que importa. La primera
comprueba que el fichero valida. La segunda comprueba que **el número del
contrato y el que usa el compilador son el mismo**, que es todo el motivo de
haber sacado los números de la prosa: mientras estaban escritos en markdown,
nada impedía que el código derivara y el documento siguiera diciendo lo de
antes.
"""

from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np
import pytest
from pydantic import ValidationError

from compile.conjunto import Cartucho
from compile.contratos import Contrato, Contratos, Estado, Valor, cargar
from compile.escribiente import Escribiente
from core.comercial import PiezaComercial
from core.escritura import Capacidad
from core.units import mm
from emit.plataforma import contrato_mm
from scripts.exportar_variables import csv, featurescript

PIEZAS = Path(__file__).resolve().parents[2] / "docs" / "piezas"

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
    assert contratos.valor("bastidor", "poste_obstaculo_diametro").metros == pytest.approx(
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


def test_el_marco_del_cinco_barras_pone_cada_pivote_a_la_distancia_del_cabestrante(
    contratos: Contratos,
):
    """**«Una eleccion de empaquetado» que no es libre.**

    `CLAUDE.md` decia que el marco del cinco barras va en (-16,225, -28,103)
    girado 150 grados y que eso «lleva los pivotes junto a sus postes». Es
    mucho mas fuerte que eso: deja cada pivote a **68,000 mm exactos** de su
    poste, que es `amplificador_entre_ejes`, la distancia que el cabestrante
    necesita entre el sector y el tambor. Mover el marco rompe el
    amplificador.

    El giro vivia solo en la prosa —estaban la x y la y en el contrato y no
    el angulo—, y sin el no se puede situar un solo agujero del bastidor.
    """
    import math

    c = {
        n: contratos.valor("bastidor", n).metros
        for n in (
            "brazo_origen_x",
            "brazo_origen_y",
            "brazo_separacion",
            "poste_radio_al_arbol",
            "amplificador_entre_ejes",
            "caja_centro_y",
        )
    }
    giro = contratos.valor("bastidor", "brazo_origen_giro").radianes
    reparto = contratos.valor("bastidor", "poste_reparto").radianes

    cos, sen = math.cos(giro), math.sin(giro)

    def al_arbol(x: float, y: float) -> tuple[float, float]:
        return c["brazo_origen_x"] + cos * x - sen * y, c["brazo_origen_y"] + sen * x + cos * y

    postes = [
        (
            c["poste_radio_al_arbol"] * math.cos(reparto * i),
            c["poste_radio_al_arbol"] * math.sin(reparto * i),
        )
        for i in range(3)
    ]
    for signo in (-1.0, 1.0):
        pivote = al_arbol(signo * c["brazo_separacion"] / 2.0, 0.0)
        cerca = min(math.dist(pivote, p) for p in postes)
        assert cerca == pytest.approx(c["amplificador_entre_ejes"], abs=1e-6), (
            f"el pivote queda a {cerca * 1000:.3f} mm de su poste y el cabestrante "
            f"pide {c['amplificador_entre_ejes'] * 1000:.3f}"
        )

    # Y el centro del papel cae donde dice la prosa: 132,5 mm del arbol.
    papel = al_arbol(0.0, c["caja_centro_y"])
    assert math.hypot(*papel) == pytest.approx(0.1325, abs=1e-4)


def test_los_pivotes_en_polares_son_los_mismos_que_salen_de_la_transformacion(
    contratos: Contratos,
):
    """`platina_pivote_al_arbol` y sus dos angulos son DERIVADOS.

    Existen porque el CAD situa un agujero en polares y resolver la
    transformacion del marco del cinco barras de cabeza se falla, igual que
    `brazo_chaveta_cuerda` existe porque hacer la raiz a mano se falla. Pero
    un derivado que nadie cruza con su origen es un numero suelto mas, asi
    que aqui se rehace la cuenta.

    Y de paso queda escrito lo que se vio al calcularlo: los dos pivotes caen
    al **mismo radio** y a angulos simetricos respecto de la bisectriz de 60
    grados entre el poste 1 y el 2.
    """
    import math

    c = {
        n: contratos.valor("bastidor", n).metros
        for n in (
            "brazo_origen_x",
            "brazo_origen_y",
            "brazo_separacion",
            "platina_pivote_al_arbol",
        )
    }
    giro = contratos.valor("bastidor", "brazo_origen_giro").radianes
    cos, sen = math.cos(giro), math.sin(giro)

    angulos = {}
    for signo, lado in ((-1.0, "izquierdo"), (1.0, "derecho")):
        x = signo * c["brazo_separacion"] / 2.0
        punto = (c["brazo_origen_x"] + cos * x, c["brazo_origen_y"] + sen * x)
        assert math.hypot(*punto) == pytest.approx(c["platina_pivote_al_arbol"], abs=1e-9)
        angulos[lado] = math.atan2(punto[1], punto[0])
        declarado = contratos.valor("bastidor", f"platina_pivote_angulo_{lado}").radianes
        assert angulos[lado] == pytest.approx(declarado, abs=1e-9)

    # 1e-7 y no 1e-9: los dos angulos se guardan redondeados a nueve
    # decimales, que a 68 mm de radio son 70 nanometros. El redondeo es del
    # dato, no de la cuenta.
    bisectriz = math.radians(60.0)
    assert (angulos["izquierdo"] + angulos["derecho"]) / 2.0 == pytest.approx(bisectriz, abs=1e-7)


def test_los_tres_rodillos_cuelgan_a_un_paso_de_pila_cada_uno(contratos: Contratos):
    """Los tres seguidores van en UN plano y cada rodillo baja a su leva.

    El brazo del seguidor pasa por encima de las levas, así que no cabe en
    el plano de la suya. De ahí que los tres descuelgues sean distintos, y
    que se diferencien en exactamente un paso de pila —una leva más un
    separador— y no en cualquier cosa. Y el orden lo pone la pila: la leva
    de arriba baja un paso, la de abajo tres.
    """
    from compile.escribiente import ORDEN_EN_LA_PILA, SEGUIDORES

    paso = float(Escribiente().espesor_leva) + float(Cartucho().separador)
    for canal, nombre in enumerate(SEGUIDORES, start=1):
        bajada = contratos.valor("bastidor", f"rodillo_descuelgue_{canal}").metros
        pasos_hasta_arriba = len(ORDEN_EN_LA_PILA) - ORDEN_EN_LA_PILA.index(nombre)
        assert bajada == pytest.approx(pasos_hasta_arriba * paso, abs=1e-9), nombre


def test_los_brazos_del_contrato_son_los_de_la_maquina(contratos: Contratos):
    """Los tres agujeros de rodillo del seguidor y los tres brazos con los
    que se sintetizan las levas son el mismo número."""
    from compile.escribiente import SEGUIDORES

    m = Escribiente()
    nombres = {
        "izquierdo": "brazo_seguidor_izquierdo",
        "derecho": "brazo_seguidor_derecho",
        "elevador": "brazo_seguidor",
    }
    for i, canal in enumerate(SEGUIDORES):
        assert contratos.valor("bastidor", nombres[canal]).metros == pytest.approx(
            float(m.brazos_de_canal[i]), abs=1e-12
        ), canal


def test_el_septimo_agujero_de_la_platina_deja_pared_a_todos_los_demas():
    """**El apoyo del eje de la manivela no puede comerse otro agujero.**

    La platina pasó de seis agujeros a siete, y el nuevo —el rodamiento de
    la manivela, a 28 del árbol— cae cerca del alojamiento central: entre
    los dos Ø19 quedan 9 mm de pared. Es el caso crítico, y es el que este
    test vigila: comprobar un rasgo contra el contorno no dice nada de los
    rasgos entre sí, que es la trampa que destapó la mordaza.
    """
    c = contrato_mm()
    minima = c["holgura_minima"]
    t = c["platina_manivela_angulo"]
    mx, my = c["reductor_entre_ejes"] * math.cos(t), c["reductor_entre_ejes"] * math.sin(t)
    radio_manivela = c["rodamiento_arbol_alojamiento_diametro"] / 2

    # Contra el alojamiento del árbol, que está en el centro.
    pared = c["reductor_entre_ejes"] - 2 * radio_manivela
    assert pared >= minima, f"entre los dos Ø19 quedan {pared:.2f} mm"

    vecinos = [
        (c["poste_radio_al_arbol"], c["poste_reparto"] * i, c["poste_eje_diametro"])
        for i in range(3)
    ] + [
        (c["platina_pivote_al_arbol"], c[f"platina_pivote_angulo_{lado}"], c["brazo_eje_diametro"])
        for lado in ("izquierdo", "derecho")
    ]
    for radio, angulo, diametro in vecinos:
        x, y = radio * math.cos(angulo), radio * math.sin(angulo)
        pared = math.hypot(x - mx, y - my) - radio_manivela - diametro / 2
        assert pared >= minima, f"el agujero a ({x:.1f}, {y:.1f}) deja {pared:.2f} mm"


def test_el_volante_gira_dentro_de_la_silueta_del_plato():
    """No es estética sola: un volante que sobresale es un disco de latón de
    294 g girando al alcance de una manga. Centrado a 28 y con Ø104 llega a
    80 del árbol, y el plato mide 85 de radio."""
    c = contrato_mm()
    llega = c["reductor_entre_ejes"] + c["volante_diametro"] / 2
    assert llega <= c["platina_diametro"] / 2


def test_el_volante_no_puede_ir_en_la_bahia():
    """Va encima del plato 3, y no es un gusto: centrado en el eje de la
    manivela, a 28 del árbol, un volante de R52 tendría el árbol DENTRO, y la
    rueda Z60, que va en el árbol en esa misma bahía, lo solaparía. Su ficha
    lo ponía «en la bahía del reductor, junto al piñón» hasta 2026-10-04."""
    c = contrato_mm()
    assert c["reductor_entre_ejes"] < c["volante_diametro"] / 2


def test_la_bahia_del_reductor_cabe_lo_que_se_apila_dentro():
    """La bahía la fija lo que lleva dentro, no un número redondo: el ancho
    del engranaje —piñón y rueda en el mismo plano— y una holgura de 2 por
    arriba y por abajo. Si alguien ensancha el engranaje sin tocar la bahía,
    el plato 3 se apoya encima de él."""
    c = contrato_mm()
    ficha = PiezaComercial.model_validate(
        json.loads((PIEZAS / "pinon_reductor.json").read_text(encoding="utf-8"))
    )
    ancho = float(ficha.cota("ancho").valor) * 1000.0
    apilado = ancho + 2 * 2.0
    assert c["reductor_bahia"] >= apilado, (
        f"la bahía mide {c['reductor_bahia']:g} y dentro se apilan {apilado:g}"
    )


def test_el_poste_es_la_cadena_vertical_entera_y_no_un_numero_heredado():
    """**El poste ya no sostiene el bastidor: es la pata de la máquina.**

    Valió 70 cuando unía dos platos, 105 al aparecer el tercero y 195 desde
    que baja hasta la base. Los dos primeros eran números heredados —«70 de
    antes»— y dentro de ellos vivía sin declarar el vano entre el plato 1 y
    el plato 2, que es donde van la pila, los seguidores, el sector y la
    cinta. Ahora cada sumando es una cota y el largo es su suma.

    Que los tres platos sigan siendo la misma pieza es la consecuencia: si
    la base se sujetara con pilares propios, el plato 1 llevaría tres
    agujeros que los otros dos no tienen.
    """
    c = contrato_mm()
    cadena = (
        c["base_poste_empotrado"]
        + c["base_al_plato"]
        + 3 * c["platina_espesor"]
        + c["poste_vano"]
        + c["reductor_bahia"]
    )
    assert c["poste_largo"] == pytest.approx(cadena, abs=1e-9), (
        f"poste_largo dice {c['poste_largo']:g} y la cadena da {cadena:g}"
    )
    # Y el vano tiene que tragarse lo que lleva dentro, que es lo que el
    # número heredado no garantizaba.
    dentro = 2.0 + c["pila_altura"] + c["seguidor_espesor"] + c["amplificador_sector_espesor"]
    assert c["poste_vano"] >= dentro, (
        f"el vano mide {c['poste_vano']:g} y dentro se apilan {dentro:g}"
    )


def _postes_en_el_marco_de_la_base(c: dict[str, float]) -> list[tuple[float, float]]:
    """Los tres postes alrededor del árbol, con +Y hacia el papel.

    El marco de la base es el del cinco barras, y el de la leva está girado
    `brazo_orientacion` respecto de él: por eso los postes, que en el marco
    de la leva van a 0, 120 y 240, aquí caen a -150, -30 y +90. El de +90
    es el de delante, en el eje de simetría.
    """
    giro = c["brazo_origen_giro"]
    return [
        (
            c["poste_radio_al_arbol"] * math.cos(c["poste_reparto"] * i - giro),
            c["poste_radio_al_arbol"] * math.sin(c["poste_reparto"] * i - giro),
        )
        for i in range(3)
    ]


def test_el_marco_de_la_base_es_el_del_cinco_barras_y_sale_simetrico():
    """**La máquina no tenía frente declarado**, y lo tiene de balde.

    El centro de la caja de escritura cae a 240° exactos del árbol en el
    marco de la leva, porque la caja está sobre el eje +Y del cinco barras y
    ese marco está girado 150°. Visto desde el cinco barras, entonces, el
    árbol queda sobre el eje de simetría y todo lo demás sale por parejas:
    los dos pivotes a ±60, dos postes atrás y uno delante.

    Es lo que convierte la base en un rectángulo centrado y no en una tabla
    con la máquina de medio lado.
    """
    c = contrato_mm()
    giro = c["brazo_origen_giro"]
    # El árbol, en el marco del cinco barras.
    arbol = (
        math.cos(giro) * -c["brazo_origen_x"] + math.sin(giro) * -c["brazo_origen_y"],
        -math.sin(giro) * -c["brazo_origen_x"] + math.cos(giro) * -c["brazo_origen_y"],
    )
    assert arbol[0] == pytest.approx(0.0, abs=1e-5), f"el árbol se va {arbol[0]:.4f} del eje"
    assert arbol[1] < 0.0, "el árbol tiene que quedar DETRÁS de la línea de pivotes"
    assert c["caja_centro_y"] - arbol[1] == pytest.approx(c["papel_al_arbol"], abs=1e-6)

    postes = _postes_en_el_marco_de_la_base(c)
    delante = [p for p in postes if p[1] > 0.0]
    assert len(delante) == 1, "tiene que haber UN poste delante y dos detrás"
    assert delante[0][0] == pytest.approx(0.0, abs=1e-9)
    detras = sorted(p for p in postes if p[1] <= 0.0)
    assert detras[0][0] == pytest.approx(-detras[1][0], abs=1e-9)
    assert detras[0][1] == pytest.approx(detras[1][1], abs=1e-9)


def test_los_tres_agujeros_de_la_base_son_un_triangulo_equilatero():
    """La base no tiene árbol que poner en el origen, así que su datum es un
    poste. Como los tres están a 120° del árbol, el triángulo es equilátero y
    se acota con **un lado y 60°** en vez de con tres polares: tres números
    menos que teclear y ninguno que pueda contradecir a otro."""
    c = contrato_mm()
    postes = _postes_en_el_marco_de_la_base(c)
    lados = [math.dist(postes[i], postes[(i + 1) % 3]) for i in range(3)]
    for lado in lados:
        assert lado == pytest.approx(c["base_entre_postes"], abs=1e-9)
    assert c["base_entre_postes"] == pytest.approx(
        c["poste_radio_al_arbol"] * math.sqrt(3.0), abs=1e-9
    )
    assert c["base_postes_angulo"] == pytest.approx(math.radians(60.0), abs=1e-12)


def test_la_base_deja_diez_milimetros_de_nogal_alrededor_de_todo():
    """**La planta la cierran el plato por detrás y la tarjeta por delante.**

    No es un rectángulo elegido: es lo que ocupa la máquina más un margen
    igual a las cuatro puntas. Y de paso deja dicho que los 210 × 160 de la
    ficha de producto se escribieron antes de saber dónde cae el papel: el
    fondo se queda 115 mm corto.
    """
    c = contrato_mm()
    margen = 10.0
    r = c["platina_diametro"] / 2.0
    # A los lados manda el plato; delante, la tarjeta; detrás, el plato.
    assert c["base_ancho"] / 2.0 - r >= margen
    assert c["base_arbol_al_borde_trasero"] - r >= margen
    delantero = c["base_fondo"] - c["base_arbol_al_borde_trasero"]
    assert delantero - (c["papel_al_arbol"] + c["papel_fondo"] / 2.0) >= margen
    assert c["base_ancho"] / 2.0 - c["papel_ancho"] / 2.0 >= margen


def test_la_tarjeta_cabe_la_caja_de_escritura_y_no_pisa_el_plato():
    """El papel se centra en lo que se escribe, no en la tabla. Un A7
    apaisado deja 12,5 a los lados de los 80 de la caja y 22 delante y
    detrás de los 30, y su borde cercano queda fuera del plato: si entrara
    debajo, la tarjeta no se podría poner ni quitar sin mover la máquina."""
    c = contrato_mm()
    assert c["papel_ancho"] > c["caja_ancho"]
    assert c["papel_fondo"] > c["caja_alto"]
    cerca = c["papel_al_arbol"] - c["papel_fondo"] / 2.0
    assert cerca - c["platina_diametro"] / 2.0 >= 10.0, (
        f"la tarjeta se mete bajo el plato: le faltan {cerca - c['platina_diametro'] / 2.0:.2f} mm"
    )


def test_la_base_situa_su_contorno_desde_el_poste_datum():
    """Ancho y fondo dicen cuánto mide la tabla y **ninguno dice dónde cae el
    agujero dentro de ella**. Es la lección de `mordaza_voladizo` en las dos
    direcciones: el rectángulo se puede dibujar centrado entre los postes —que
    es lo natural— y entonces la máquina se va 23 mm hacia atrás sin que el
    dibujo enseñe nada raro."""
    c = contrato_mm()
    postes = _postes_en_el_marco_de_la_base(c)
    datum = min(postes)  # el de atrás a la izquierda, que es el del origen
    assert c["base_poste_al_borde_izquierdo"] == pytest.approx(
        c["base_ancho"] / 2.0 + datum[0], abs=1e-9
    )
    assert c["base_poste_al_borde_trasero"] == pytest.approx(
        c["base_arbol_al_borde_trasero"] + datum[1], abs=1e-9
    )


def test_la_planta_dice_por_donde_pasa_la_mano():
    """**El volante queda dentro de la tabla y la manivela no, y eso es un
    dato de la planta, no un defecto.**

    El eje de la manivela está a 28 del árbol y, en el marco de la base, a
    120°: ni atrás ni en el eje, sino arriba a la izquierda. Es la
    consecuencia de haberlo colocado en el marco de la LEVA —a -90° allí— sin
    que nadie mirara dónde cae eso visto desde quien escribe.

    De ahí salen tres números que conviene tener delante antes de poner la
    máquina en una mesa: el volante gira entero dentro de la tabla, el pomo
    de la manivela se sale 19 mm por la izquierda, y en su paso de delante
    cruza 29 mm sobre la tarjeta, a 190 mm de altura. No choca con nada; lo
    que hace es que la mano pase por encima de lo escrito una vez por vuelta.

    Moverlo a -90° del marco de la BASE lo dejaría atrás y simétrico, y
    costaría redibujar la platina, que ya está entregada. El número está aquí
    para que esa decisión se tome con él delante y no por sorpresa.
    """
    c = contrato_mm()
    giro, t = c["brazo_origen_giro"], c["platina_manivela_angulo"]
    eje = (
        c["reductor_entre_ejes"] * math.cos(t - giro),
        c["reductor_entre_ejes"] * math.sin(t - giro),
    )
    media, atras = c["base_ancho"] / 2.0, -c["base_arbol_al_borde_trasero"]

    # El volante, entero dentro: son 294 g de latón al alcance de una manga.
    assert eje[1] - c["volante_diametro"] / 2.0 > atras
    assert abs(eje[0]) + c["volante_diametro"] / 2.0 < media

    # La manivela, no, y por dónde.
    r = c["manivela_entre_centros"]
    assert -(eje[0] - r) - media == pytest.approx(19.0, abs=0.5)
    assert (eje[1] - r) - atras == pytest.approx(19.2, abs=0.5)
    sobre_la_tarjeta = (eje[1] + r) - (c["papel_al_arbol"] - c["papel_fondo"] / 2.0)
    assert sobre_la_tarjeta == pytest.approx(28.8, abs=0.5)


# ---------------------------------------------------------------------------
# El contrato de cartucho
# ---------------------------------------------------------------------------


def _mm(contratos: Contratos, contrato: str, nombre: str) -> float:
    return contratos.valor(contrato, nombre).metros * 1000.0


def test_lo_que_hay_bajo_las_levas_es_el_cubo_y_el_muñon(contratos: Contratos):
    """El hueco entre el plato 1 y la primera leva no es un número suelto:
    es la holgura del muñón, su horquilla y el cubo del cartucho."""
    suma = sum(
        _mm(contratos, "cartucho", n)
        for n in ("munon_holgura", "munon_horquilla_alto", "cubo_espesor")
    )
    assert _mm(contratos, "bastidor", "leva_sobre_plato") == pytest.approx(suma)


def test_el_pasador_atraviesa_el_cubo_y_la_pila_justo(contratos: Contratos):
    pila = _mm(contratos, "eje", "pila_altura")
    assert _mm(contratos, "fase", "pasador_longitud") == pytest.approx(
        pila + _mm(contratos, "cartucho", "cubo_espesor")
    )
    assert (
        _mm(contratos, "cartucho", "cartucho_eje_largo")
        > pila
        + _mm(contratos, "cartucho", "cubo_espesor")
        + _mm(contratos, "cartucho", "garra_ranura_profundidad")
        - 1e-9
    )


def test_el_radio_maximo_del_cartucho_sale_del_hueco_entre_postes(contratos: Contratos):
    """Entre los dos postes traseros cabe el cartucho con su holgura de paso.
    Lo que el compilador vigila es lo que el bastidor permite."""
    poste = _mm(contratos, "bastidor", "poste_radio_al_arbol")
    hueco = 2.0 * poste * math.sin(math.pi / 3.0) - 8.0  # menos el poste de Ø8
    radio = _mm(contratos, "cartucho", "cartucho_radio_maximo")
    assert (
        radio <= hueco / 2.0 - 2.0 * _mm(contratos, "cartucho", "cartucho_holgura_de_paso") + 1e-9
    )
    assert float(Escribiente().radio_maximo_cartucho) * 1000.0 == pytest.approx(radio)


def test_el_cartucho_sale_lejos_del_tercer_poste(contratos: Contratos):
    angulo = contratos.valor("cartucho", "cartucho_salida_angulo").valor
    x, y = Escribiente().seguidor(2).pivote
    assert angulo == pytest.approx(math.atan2(-y, -x))


def test_la_ranura_de_la_garra_solo_entra_de_una_manera(contratos: Contratos):
    """Descentrada más de lo que mide de ancho la mitad, la ranura girada
    180° no se solapa con la de verdad: la lengüeta solo entra en fase cero.
    Y cabe en la cabeza del eje sin salirse del Ø10."""
    ancho = _mm(contratos, "cartucho", "garra_ranura_ancho")
    fuera = _mm(contratos, "cartucho", "garra_ranura_desplazamiento")
    assert 2.0 * fuera >= ancho  # girada media vuelta no coincide
    assert fuera + ancho / 2.0 < _mm(contratos, "eje", "eje_diametro") / 2.0 - 1.0  # pared
    assert _mm(contratos, "cartucho", "garra_carrera") > _mm(
        contratos, "cartucho", "garra_ranura_profundidad"
    )


def test_una_leva_demasiado_grande_no_deja_salir_el_cartucho():
    from compile.escribiente import compilar

    estrecha = Escribiente(radio_maximo_cartucho=mm(45.0))
    from tests.casos import hola

    v = compilar(hola(), estrecha).veredicto
    assert "cartucho_no_sale" in {i.codigo for i in v.incidencias}
    assert "cartucho_no_sale" not in {i.codigo for i in compilar(hola()).veredicto.incidencias}


# ---------------------------------------------------------------------------
# El tope del seguidor
# ---------------------------------------------------------------------------


def test_el_tope_del_compilador_es_el_del_contrato(contratos: Contratos):
    assert Escribiente().tope_seguidor == pytest.approx(
        contratos.valor("bastidor", "tope_giro").valor
    )


def test_ninguna_frase_de_referencia_lleva_un_seguidor_al_tope():
    from compile.escribiente import SEGUIDORES, compilar
    from tests.casos import firma, hola, puntos

    m = Escribiente()
    for caso in (hola, firma, puntos):
        v = compilar(caso()).veredicto
        assert "seguidor_contra_tope" not in {i.codigo for i in v.incidencias}, caso.__name__
        for nombre in SEGUIDORES:
            assert v.metricas[f"giro_hacia_dentro_{nombre}"] < m.tope_seguidor - m.margen_al_tope


def test_un_tope_demasiado_cerca_salta():
    from compile.escribiente import compilar
    from tests.casos import hola

    v = compilar(hola(), Escribiente(tope_seguidor=0.01)).veredicto
    assert "seguidor_contra_tope" in {i.codigo for i in v.incidencias}


def test_el_angulo_de_la_placa_de_tope_es_el_que_para_el_seguidor_en_su_giro():
    """La placa se gira `tope_angulo` respecto del brazo del seguidor. Con
    ese ángulo, el seguidor —el contorno de su barra, la más larga de las
    tres— toca el pasador de tope justo al girar `tope_giro`, y en reposo le
    sobra hueco. Derivado: si cambia la barra o el brazo de la placa, este
    test dice el ángulo nuevo."""
    from shapely import affinity
    from shapely.geometry import Point

    c = contrato_mm()
    largo = max(c["brazo_seguidor"], c["brazo_seguidor_derecho"], c["brazo_seguidor_izquierdo"])
    barra = (
        Point(0, 0)
        .buffer(c["seguidor_cubo_diametro"] / 2, 512)
        .union(Point(largo, 0).buffer(c["seguidor_extremo_diametro"] / 2, 512))
        .convex_hull
    )
    phi = c["tope_angulo"]
    pasador = Point(c["tope_brazo"] * math.cos(phi), c["tope_brazo"] * math.sin(phi))
    r = c["tope_pasador_diametro"] / 2

    def hueco(giro: float) -> float:
        return affinity.rotate(barra, giro, origin=(0, 0), use_radians=True).distance(pasador) - r

    assert hueco(c["tope_giro"]) == pytest.approx(0.0, abs=0.01)
    assert hueco(0.0) > 1.0


def test_el_casquillo_del_rodillo_llena_el_descuelgue(contratos: Contratos):
    """Del rodillo a la cara baja del seguidor, en cada canal; y su radio es
    el que vigila el compilador al escalonar la pila."""
    c = contrato_mm()
    for n in (1, 2, 3):
        esperado = c[f"rodillo_descuelgue_{n}"] - 2.5 / 2.0 - c["seguidor_espesor"] / 2.0
        assert c[f"casquillo_rodillo_largo_{n}"] == pytest.approx(esperado), n
    assert float(Escribiente().radio_eje_rodillo) * 1000.0 == pytest.approx(
        c["casquillo_rodillo_diametro"] / 2.0
    )
