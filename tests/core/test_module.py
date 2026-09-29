"""La ficha de módulo y el cableado de una máquina.

El bloque final es la verificación humana de E1 convertida en test: las cuatro
fichas del catálogo se cargan desde `docs/modulos/` y tienen que validar. Si
alguien cambia el modelo de forma que una deje de encajar, la suite lo dice.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from core.module import (
    Balance,
    Canal,
    EnvolventePropia,
    Ergonomia,
    Fabricacion,
    Familia,
    FichaModulo,
    Identidad,
    InterfazMecanica,
    Maquina,
    ModoFallo,
    ModuloMontado,
    Proceso,
)
from core.program import PistaContinua, Programa
from core.units import AnguloCiclo, Julios, Longitud, NewtonMetro, Newtons, grados, mm

pytestmark = pytest.mark.core

CATALOGO = Path(__file__).resolve().parents[2] / "docs" / "modulos"


# ---------------------------------------------------------------------------
# Constructores de apoyo
# ---------------------------------------------------------------------------


def interfaz() -> InterfazMecanica:
    return InterfazMecanica(ancho=mm(100.0), alto=mm(40.0), fondo=mm(20.0))


def fabricacion() -> Fabricacion:
    return Fabricacion(material="contrachapado 4 mm", proceso=Proceso.LASER, n_piezas=1)


def balance_consume() -> Balance:
    return Balance(
        signo="consume",
        par_pico=NewtonMetro(0.5),
        par_medio=NewtonMetro(0.2),
        energia_ciclo=Julios(1.0),
    )


def ficha(
    nombre: str,
    familia: Familia,
    canales: list[Canal],
    *,
    balance: Balance | None = None,
    ergonomia: Ergonomia | None = None,
    envolvente: EnvolventePropia | None = None,
) -> FichaModulo:
    return FichaModulo(
        identidad=Identidad(nombre=nombre, familia=familia, version="0.1.0"),
        interfaz=interfaz(),
        canales=canales,
        balance=balance or balance_consume(),
        envolvente=envolvente or EnvolventePropia(),
        modo_fallo=ModoFallo.CEDE_BLANDO,
        ergonomia=ergonomia,
        fabricacion=fabricacion(),
    )


def canal(nombre: str, rol: str) -> Canal:
    return Canal(nombre=nombre, rol=rol, tipo="continuo", unidad="m")  # type: ignore[arg-type]


def programa_de(*canales: str) -> Programa:
    return Programa(
        nombre="prueba",
        pistas=[
            PistaContinua(
                canal=c,
                unidad="m",
                thetas=[AnguloCiclo(0.0), grados(180.0)],
                valores=[0.0, 0.01],
            )
            for c in canales
        ],
    )


def maquina(*modulos: FichaModulo, canales_programa: tuple[str, ...]) -> Maquina:
    return Maquina(
        nombre="prueba",
        modulos=[ModuloMontado(ficha=f) for f in modulos],
        programa=programa_de(*canales_programa),
    )


# ---------------------------------------------------------------------------
# Ida y vuelta
# ---------------------------------------------------------------------------


def test_una_ficha_sobrevive_a_json_identica():
    original = ficha("leva_x", Familia.MEMORIA, [canal("x", "produce")])
    assert FichaModulo.model_validate_json(original.model_dump_json()) == original


def test_una_maquina_sobrevive_a_json_identica():
    original = maquina(
        ficha("leva_x", Familia.MEMORIA, [canal("x", "produce")]),
        ficha("brazo", Familia.ACTUADOR, [canal("x", "consume")]),
        canales_programa=("x",),
    )
    assert Maquina.model_validate_json(original.model_dump_json()) == original


# ---------------------------------------------------------------------------
# Coherencia de la ficha
# ---------------------------------------------------------------------------


def test_una_fuente_humana_sin_ergonomia_es_rechazada():
    with pytest.raises(ValidationError, match="no declara"):
        ficha(
            "pedal",
            Familia.FUENTE_HUMANA,
            [],
            balance=Balance(
                signo="aporta",
                par_pico=NewtonMetro(-20.0),
                par_medio=NewtonMetro(-10.0),
                energia_ciclo=Julios(-100.0),
            ),
        )


def test_un_modulo_que_no_es_humano_no_lleva_ergonomia():
    ergo = Ergonomia(
        postura="sentado",
        recorrido=mm(340.0),
        curva_fuerza=[(0.0, Newtons(80.0)), (1.0, Newtons(200.0))],
        ciclo_trabajo="continuo",
    )
    with pytest.raises(ValidationError, match="sobra"):
        ficha("leva_x", Familia.MEMORIA, [canal("x", "produce")], ergonomia=ergo)


def test_el_signo_del_balance_debe_cuadrar_con_los_valores():
    """Lo que aporta va en negativo. Es lo que permite sumar sin casos especiales."""
    with pytest.raises(ValidationError, match="no cuadra con signo"):
        Balance(
            signo="aporta",
            par_pico=NewtonMetro(25.0),
            par_medio=NewtonMetro(12.0),
            energia_ciclo=Julios(180.0),
        )


def test_un_modulo_no_declara_dos_veces_el_mismo_canal():
    with pytest.raises(ValidationError, match="dos veces el canal"):
        ficha("raro", Familia.MEMORIA, [canal("x", "produce"), canal("x", "consume")])


def test_la_curva_de_fuerza_va_normalizada_de_cero_a_uno():
    with pytest.raises(ValidationError, match="normalizada"):
        Ergonomia(
            postura="sentado",
            recorrido=mm(340.0),
            curva_fuerza=[(0.1, Newtons(80.0)), (0.9, Newtons(200.0))],
            ciclo_trabajo="continuo",
        )


# ---------------------------------------------------------------------------
# Cableado de la máquina
# ---------------------------------------------------------------------------


def test_una_maquina_bien_cableada_valida():
    m = maquina(
        ficha("leva_x", Familia.MEMORIA, [canal("x", "produce")]),
        ficha("seguidor_x", Familia.TRANSMISION, [canal("x", "consume")]),
        ficha("brazo", Familia.ACTUADOR, [canal("x", "consume")]),
        canales_programa=("x",),
    )
    assert len(m.modulos) == 3


def test_un_canal_no_puede_tener_dos_productores():
    with pytest.raises(ValidationError, match="un solo productor"):
        maquina(
            ficha("leva_x", Familia.MEMORIA, [canal("x", "produce")]),
            ficha("leva_x_bis", Familia.MEMORIA, [canal("x", "produce")]),
            ficha("brazo", Familia.ACTUADOR, [canal("x", "consume")]),
            canales_programa=("x",),
        )


def test_un_canal_consumido_sin_productor_es_rechazado():
    with pytest.raises(ValidationError, match="nadie produce"):
        maquina(
            ficha("brazo", Familia.ACTUADOR, [canal("x", "consume")]),
            canales_programa=("x",),
        )


def test_una_pista_que_ningun_modulo_produce_es_rechazada():
    with pytest.raises(ValidationError, match="ningún módulo produce"):
        maquina(
            ficha("leva_x", Familia.MEMORIA, [canal("x", "produce")]),
            ficha("brazo", Familia.ACTUADOR, [canal("x", "consume")]),
            canales_programa=("x", "y"),
        )


def test_un_modulo_que_produce_un_canal_sin_pista_es_rechazado():
    with pytest.raises(ValidationError, match="sin pista en el programa"):
        maquina(
            ficha("leva_x", Familia.MEMORIA, [canal("x", "produce")]),
            ficha("leva_y", Familia.MEMORIA, [canal("y", "produce")]),
            ficha("brazo", Familia.ACTUADOR, [canal("x", "consume")]),
            canales_programa=("x",),
        )


def test_varios_modulos_pueden_consumir_el_mismo_canal():
    """Un canal es la señal, no el cable: la leva lo produce y todo lo que
    hay aguas abajo lo consume."""
    m = maquina(
        ficha("leva_x", Familia.MEMORIA, [canal("x", "produce")]),
        ficha("seguidor_x", Familia.TRANSMISION, [canal("x", "consume")]),
        ficha("brazo", Familia.ACTUADOR, [canal("x", "consume")]),
        ficha("puntero", Familia.ACTUADOR, [canal("x", "consume")]),
        canales_programa=("x",),
    )
    assert len(m.modulos) == 4


# ---------------------------------------------------------------------------
# El catálogo real: verificación humana de E1, hecha test
# ---------------------------------------------------------------------------


def fichas_del_catalogo() -> list[Path]:
    return sorted(CATALOGO.glob("*.json"))


def test_el_catalogo_no_esta_vacio():
    assert fichas_del_catalogo(), f"no hay fichas en {CATALOGO}"


@pytest.mark.parametrize("ruta", fichas_del_catalogo(), ids=lambda p: p.stem)
def test_cada_ficha_del_catalogo_valida(ruta: Path):
    FichaModulo.model_validate_json(ruta.read_text(encoding="utf-8"))


@pytest.mark.parametrize("ruta", fichas_del_catalogo(), ids=lambda p: p.stem)
def test_el_nombre_del_fichero_coincide_con_el_de_la_ficha(ruta: Path):
    datos = json.loads(ruta.read_text(encoding="utf-8"))
    assert datos["identidad"]["nombre"] == ruta.stem


def test_las_cuatro_fichas_cubren_familias_distintas():
    """La prueba de fuego de E1: el mismo formulario para módulos que no se
    parecen en nada."""
    familias = {
        FichaModulo.model_validate_json(r.read_text(encoding="utf-8")).identidad.familia
        for r in fichas_del_catalogo()
    }
    assert {
        Familia.ACTUADOR,
        Familia.MEMORIA,
        Familia.TRANSMISION,
        Familia.FUENTE_HUMANA,
    } <= familias


def test_el_radio_de_rodillo_vive_en_el_seguidor():
    """C3 lo necesita para el offset y la curvatura, y es del seguidor, no
    de la leva. Es la consecuencia de partir leva y seguidor en dos módulos."""
    seguidor = FichaModulo.model_validate_json(
        (CATALOGO / "seguidor_resistencia.json").read_text(encoding="utf-8")
    )
    leva = FichaModulo.model_validate_json(
        (CATALOGO / "leva_resistencia.json").read_text(encoding="utf-8")
    )
    assert seguidor.envolvente.radio_rodillo == Longitud(mm(4.0))
    assert leva.envolvente.radio_rodillo is None


def test_la_leva_produce_y_el_seguidor_consume_el_mismo_canal():
    leva = FichaModulo.model_validate_json(
        (CATALOGO / "leva_resistencia.json").read_text(encoding="utf-8")
    )
    seguidor = FichaModulo.model_validate_json(
        (CATALOGO / "seguidor_resistencia.json").read_text(encoding="utf-8")
    )
    assert leva.canales_por_rol("produce") == seguidor.canales_por_rol("consume")


def test_la_estacion_de_pedal_no_consume_ningun_canal():
    """Una fuente no lee el programa: lo mueve. Que la ficha le sirva igual es
    lo que demuestra que es ficha de módulo y no de actuador."""
    pedal = FichaModulo.model_validate_json(
        (CATALOGO / "estacion_pedal.json").read_text(encoding="utf-8")
    )
    assert pedal.canales == []
    assert pedal.cinematica is None
    assert pedal.balance.signo == "aporta"
    assert pedal.ergonomia is not None
