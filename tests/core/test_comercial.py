"""Las fichas de las piezas que se compran hechas.

El bloque final es la verificación de la regla 6 convertida en test: las
fichas del catálogo se cargan desde `docs/piezas/` y tienen que validar. Si
alguien cambia el modelo de forma que una deje de encajar, la suite lo dice.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from core.comercial import Cota, FamiliaComercial, Fuente, PiezaComercial
from core.units import mm

pytestmark = pytest.mark.core

CATALOGO = Path(__file__).resolve().parents[2] / "docs" / "piezas"


def fuente(**cambios: object) -> Fuente:
    datos: dict[str, object] = {
        "proveedor": "Proveedor",
        "referencia": "REF-1",
        "url": "https://ejemplo.invalid/ref-1",
        "fecha": "2026-09-29",
    }
    datos.update(cambios)
    return Fuente.model_validate(datos)


def pieza(**cambios: object) -> PiezaComercial:
    datos: dict[str, object] = {
        "nombre": "prueba",
        "familia": FamiliaComercial.RODAMIENTO,
        "designacion": "ABC-123",
        "cantidad": 1,
        "fuente": fuente(),
        "cotas": [Cota(nombre="agujero", valor=mm(3.0), critica=True)],
    }
    datos.update(cambios)
    return PiezaComercial.model_validate(datos)


# ---------------------------------------------------------------------------
# El modelo
# ---------------------------------------------------------------------------


def test_una_pieza_sin_cotas_no_es_una_ficha():
    """Una referencia sin cotas de interfaz no sirve para diseñar: es una
    línea de un albarán."""
    with pytest.raises(ValidationError):
        pieza(cotas=[])


def test_la_fuente_exige_fecha_en_formato_reconocible():
    """Una cota sin fecha no se puede volver a comprobar."""
    with pytest.raises(ValidationError):
        fuente(fecha="septiembre de 2026")


def test_una_cota_se_pide_por_nombre_y_falla_si_no_esta():
    """Devolver cero por una cota que falta es cómo un agujero de Ø0 acaba
    en un plano."""
    p = pieza()
    assert float(p.cota("agujero").valor) == pytest.approx(0.003)
    with pytest.raises(KeyError, match="no declara la cota"):
        p.cota("valona")


def test_las_cotas_criticas_se_pueden_listar():
    """Son las que otra pieza del diseño toca, y las que hay que volver a
    mirar cuando se cambia de proveedor."""
    p = pieza(
        cotas=[
            Cota(nombre="agujero", valor=mm(3.0), critica=True),
            Cota(nombre="chaflan", valor=mm(0.3)),
        ]
    )
    assert [c.nombre for c in p.criticas] == ["agujero"]


def test_los_dientes_de_un_engranaje_salen_de_sus_dos_cotas():
    """`da = m·(Z+2)`. La ficha guarda el exterior porque es lo que se mide
    con el pie de rey; el CAD pide Z, que es lo que no se puede medir sin
    contar."""
    p = pieza(
        familia=FamiliaComercial.ENGRANAJE,
        cotas=[
            Cota(nombre="modulo", valor=mm(0.7), critica=True),
            Cota(nombre="exterior", valor=mm(15.4), critica=True),
        ],
    )
    assert p.dientes == 20


def test_lo_que_no_es_un_engranaje_no_tiene_dientes():
    """Devolver cero aquí sería un engranaje de cero dientes en un formulario
    del CAD. No tener dientes y tener cero no es lo mismo."""
    assert pieza().dientes is None


def test_un_engranaje_al_que_le_falta_una_cota_no_se_inventa_los_dientes():
    """Falla al pedir la cota, como cualquier otra. La alternativa es un
    piñón plausible y equivocado."""
    p = pieza(
        familia=FamiliaComercial.ENGRANAJE,
        cotas=[Cota(nombre="modulo", valor=mm(0.7), critica=True)],
    )
    with pytest.raises(KeyError, match="no declara la cota"):
        _ = p.dientes


def test_una_ficha_es_inmutable():
    with pytest.raises(ValidationError):
        pieza().nombre = "otra"  # type: ignore[misc]


# ---------------------------------------------------------------------------
# El catálogo de verdad
# ---------------------------------------------------------------------------


def catalogo() -> list[PiezaComercial]:
    return [
        PiezaComercial.model_validate(json.loads(ruta.read_text(encoding="utf-8")))
        for ruta in sorted(CATALOGO.glob("*.json"))
    ]


def test_todas_las_fichas_del_catalogo_validan():
    piezas = catalogo()
    assert len(piezas) >= 14, "faltan fichas del despiece"


def test_el_nombre_del_fichero_es_el_de_la_pieza():
    """Para poder encontrarla sin abrirla."""
    for ruta in sorted(CATALOGO.glob("*.json")):
        p = PiezaComercial.model_validate(json.loads(ruta.read_text(encoding="utf-8")))
        assert p.nombre == ruta.stem


def test_toda_cota_del_catalogo_tiene_fuente_con_enlace():
    """Una cota sin enlace es una cota inventada dentro de seis meses. Es la
    lección de la valona del casquillo, que se anotó como Ø12 y son Ø15."""
    for p in catalogo():
        assert p.fuente.url.startswith("http"), f"{p.nombre} no dice de dónde sale"
        assert p.fuente.referencia


def test_lo_no_verificado_esta_marcado_y_se_puede_contar():
    sin_verificar = [p.nombre for p in catalogo() if not p.fuente.verificado]
    assert "poste_pivote" in sin_verificar, "el precio del poste sigue sin confirmarse"


def test_toda_pieza_declara_al_menos_una_cota_critica_o_dice_por_que():
    """Una pieza sin ninguna cota crítica es sospechosa: o no la toca nada,
    y entonces por qué está, o se ha olvidado marcarla."""
    sin_criticas = {p.nombre for p in catalogo() if not p.criticas}
    assert sin_criticas <= {"muelle_seguidor", "tornilleria"}, (
        f"estas piezas no declaran ninguna cota crítica: {sin_criticas}"
    )
