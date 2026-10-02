"""El catálogo de sólidos comerciales.

**Lo que hay que comprobar no es que el sólido sea bonito: es que sus cotas
sean las de la ficha.** Toda la razón de generarlos en vez de bajarlos del
fabricante es que por construcción digan lo mismo que el compilador, y eso
se verifica midiendo la caja envolvente y comparándola con el JSON.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from core.comercial import Cota, FamiliaComercial, Fuente, PiezaComercial
from core.errors import FichaIncompleta
from core.solido import densidad_de
from core.units import mm
from emit.catalogo import caja_envolvente, cargar, escribir_catalogo, solido_de

pytestmark = pytest.mark.core

build123d = pytest.importorskip("build123d", reason="hace falta el kernel: uv sync --group cad")


def fuente() -> Fuente:
    return Fuente(proveedor="P", referencia="R", url="https://ejemplo.invalid", fecha="2026-09-30")


def pieza(familia: FamiliaComercial, **cotas: float) -> PiezaComercial:
    return PiezaComercial(
        nombre="prueba",
        familia=familia,
        designacion="X-1",
        cantidad=1,
        fuente=fuente(),
        cotas=[Cota(nombre=n, valor=mm(v)) for n, v in cotas.items()],
    )


# ---------------------------------------------------------------------------
# Las cotas del sólido son las de la ficha
# ---------------------------------------------------------------------------


def test_un_rodamiento_mide_lo_que_dice_su_ficha():
    rodamiento = pieza(FamiliaComercial.RODAMIENTO, exterior=19.0, agujero=10.0, ancho=5.0)
    x, y, z = caja_envolvente(rodamiento)
    assert (x, y, z) == pytest.approx((0.019, 0.019, 0.005))


def test_un_rodamiento_esta_hueco():
    """Si no lo estuviera, el eje no pasaría y el conjunto cerraría en falso."""
    lleno = solido_de(pieza(FamiliaComercial.EJE, diametro=19.0, longitud=5.0)).volume
    anillo = solido_de(
        pieza(FamiliaComercial.RODAMIENTO, exterior=19.0, agujero=10.0, ancho=5.0)
    ).volume
    assert anillo < lleno


def test_el_casquillo_sobresale_por_la_valona():
    """**Es la cota que decide el hueco de la leva al poste.** Si el sólido
    no la llevara, el conjunto en el CAD cerraría y la máquina real no."""
    x, y, _ = caja_envolvente(
        pieza(
            FamiliaComercial.CASQUILLO,
            agujero=8.0,
            exterior=10.0,
            valona=15.0,
            espesor_valona=1.0,
            longitud=6.0,
        )
    )
    assert x == pytest.approx(0.015)
    assert y == pytest.approx(0.015)


def test_un_engranaje_sale_como_disco_al_diametro_exterior():
    """Sin dientes a propósito: para saber si cabe no aportan nada, la pieza
    se compra hecha, y dibujarlos sería adorno con riesgo de equivocarse."""
    x, _, z = caja_envolvente(
        pieza(FamiliaComercial.ENGRANAJE, exterior=43.4, agujero=15.0, ancho=4.0, modulo=0.7)
    )
    assert x == pytest.approx(0.0434)
    assert z == pytest.approx(0.004)


def test_el_muelle_sale_como_el_cilindro_que_ocupa():
    _, _, z = caja_envolvente(pieza(FamiliaComercial.MUELLE, exterior=8.8, longitud_libre=68.0))
    assert z == pytest.approx(0.068)


def test_un_tornillo_tiene_cabeza_y_un_anillo_no():
    """Las dos formas viven en la misma familia y se distinguen por las
    cotas. Sin mirarlas, el anillo salía como un tornillo de cabeza Ø18."""
    tornillo = caja_envolvente(
        pieza(FamiliaComercial.FIJACION, metrica=3.0, cabeza=5.5, longitud=10.0)
    )
    anillo = caja_envolvente(
        pieza(FamiliaComercial.FIJACION, agujero=10.0, exterior=20.0, ancho=8.0)
    )
    assert tornillo[0] == pytest.approx(0.0055)
    assert anillo[0] == pytest.approx(0.020)
    assert anillo[2] == pytest.approx(0.008)


def test_todo_se_apoya_en_z_cero():
    """Así una pieza importada se orienta sola sobre el eje donde va."""
    for p in cargar():
        apoyo = solido_de(p).bounding_box().min.Z
        assert apoyo == pytest.approx(0.0, abs=1e-9)


# ---------------------------------------------------------------------------
# Una ficha incompleta se queja, no rellena
# ---------------------------------------------------------------------------


def test_una_cota_que_falta_es_un_error_y_dice_cual():
    """Rellenarla con un cero es cómo un agujero de Ø0 acaba en un plano."""
    with pytest.raises(FichaIncompleta, match="exterior"):
        solido_de(pieza(FamiliaComercial.RODAMIENTO, agujero=10.0, ancho=5.0))


COTAS_MINIMAS = {
    FamiliaComercial.RODAMIENTO: {"exterior": 6.0, "agujero": 3.0, "ancho": 2.5},
    FamiliaComercial.CASQUILLO: {"agujero": 8.0, "exterior": 10.0, "valona": 15.0},
    FamiliaComercial.EJE: {"diametro": 10.0, "longitud": 120.0},
    FamiliaComercial.PASADOR: {"diametro": 3.0, "longitud": 24.0},
    FamiliaComercial.MUELLE: {"exterior": 8.8, "longitud_libre": 68.0},
    FamiliaComercial.ENGRANAJE: {"exterior": 43.4, "agujero": 15.0, "ancho": 4.0},
    FamiliaComercial.SEPARADOR: {"exterior": 6.0, "agujero": 3.2, "espesor": 2.0},
    FamiliaComercial.FIJACION: {"metrica": 3.0, "cabeza": 5.5, "longitud": 10.0},
    FamiliaComercial.INSTRUMENTO: {"cuerpo": 10.0, "longitud": 150.0},
    FamiliaComercial.MATERIAL: {"ancho": 1000.0, "largo": 1000.0, "espesor": 5.0},
}


def test_ninguna_familia_del_catalogo_se_queda_sin_forma():
    """**El test que cubre el futuro.** Si alguien añade una familia al enum
    —una correa, un imán, un rodamiento axial— y se olvida del generador, no
    se descubriría hasta que una ficha de esa familia no levantara sólido.
    Aquí se descubre al añadir la familia."""
    sin_cubrir = set(FamiliaComercial) - set(COTAS_MINIMAS)
    assert not sin_cubrir, f"añade cotas mínimas de prueba para {sin_cubrir}"
    for familia, cotas in COTAS_MINIMAS.items():
        assert solido_de(pieza(familia, **cotas)).volume > 0.0, f"{familia.value} no da sólido"


# ---------------------------------------------------------------------------
# El catálogo entero
# ---------------------------------------------------------------------------


def test_todas_las_fichas_del_catalogo_levantan_un_solido():
    """Si una no levanta, es que le falta una cota: el generador es también
    un detector de fichas a medias. Ya encontró una, la del anillo."""
    piezas = cargar()
    assert len(piezas) >= 14
    for p in piezas:
        assert solido_de(p).volume > 0.0, f"{p.nombre} sale con volumen cero"


def test_las_cotas_criticas_del_catalogo_estan_en_el_solido():
    """El contrato del módulo: la envolvente es exacta en lo que otra pieza
    toca. Se comprueba contra el diámetro mayor declarado como crítico."""
    for p in cargar():
        radiales = [
            float(c.valor)
            for c in p.criticas
            if c.nombre in ("exterior", "valona", "diametro", "cuerpo", "ancho_plancha")
        ]
        if not radiales:
            continue
        x, y, _ = caja_envolvente(p)
        assert max(x, y) == pytest.approx(max(radiales), rel=1e-6), (
            f"{p.nombre}: el sólido no mide lo que dice su cota crítica"
        )


def test_se_escribe_un_step_por_pieza(tmp_path: Path):
    escritos = escribir_catalogo(cargar()[:3], tmp_path)
    assert len(escritos) == 3
    for ruta in escritos:
        assert ruta.suffix == ".step"
        assert ruta.stat().st_size > 0


def test_el_step_se_puede_volver_a_leer(tmp_path: Path):
    """Un STEP que no se reimporta no sirve para nada en un CAD."""
    from build123d import import_step

    p = next(x for x in cargar() if x.nombre == "casquillo_pivote")
    ruta = escribir_catalogo([p], tmp_path)[0]
    vuelto = import_step(str(ruta))
    ancho = vuelto.bounding_box().size.X
    assert ancho == pytest.approx(0.015, abs=1e-6)


# ---------------------------------------------------------------------------
# Las masas contrastadas contra Onshape
# ---------------------------------------------------------------------------

MASAS_VERIFICADAS = {
    "poste_pivote": 76.454,  # pendiente de rehacer en Onshape: el poste va ya por 195
    "arbol_de_levas": 73.985,
    "pasador_indice": 1.332,
    "separador_pila": 0.344,
    "casquillo_pivote": 0.388,
}
"""Gramos. **Medidos en Onshape el 2026-09-30 y coincidentes con estos.**

Son las cinco piezas comerciales cuya **envolvente es el sólido real**, que es
la condición para que su masa signifique algo. Las otras nueve no la cumplen y
por eso no están aquí: el muelle sale como el cilindro que ocupa y pesaría
32 g en vez de cuatro, un rodamiento sale como un anillo macizo sin bolas ni
pistas, y un engranaje como un disco sin dientes. Para saber si caben eso
basta y sobra; para pesarlos no sirve, y su masa buena es la del proveedor.

**El poste está a dos caminos, no a tres, desde el 2026-10-02**, y su largo
se ha movido dos veces el mismo día: 70 cuando unía dos platos, 105 al
aparecer el tercero y 195 desde que baja hasta la base y hace de pata
—27,445 → 41,167 → 76,454 g—. Los dos caminos de aquí, el polígono y OCCT,
siguen coincidiendo; el de Onshape hay que rehacerlo regenerando la pieza y
volviendo a pesar. Hasta entonces este número vale lo que valen dos caminos.

Y **no hay prisa en rehacerlo**: el largo depende de `base_al_plato`, que
está pendiente. Redibujar ahora es redibujar dos veces.

El contraste vale porque son **tres caminos que no comparten una línea de
código**: el polígono de `core/solido.py`, el kernel OCCT de build123d y el de
Onshape, cada uno con su propia integración volumétrica. Con el poste
coincidieron hasta la quinta cifra —3518,584 mm³ los tres—.

Si un número de aquí cambia, es que ha cambiado una ficha o una densidad, y el
modelo que hay dibujado en el CAD ha dejado de coincidir con el compilador.
Hay que redibujarlo, no ajustar el test.
"""


def test_las_cinco_masas_contrastadas_siguen_siendo_las_mismas():
    """Lo que congela la comprobación con el CAD.

    Sin esto, cambiar una densidad o una cota movería la masa del modelo de
    Onshape sin que nadie se enterara, y la comprobación por tres caminos se
    perdería en silencio: los dos que están en el repositorio seguirían
    coincidiendo entre sí.
    """
    for nombre, esperada in MASAS_VERIFICADAS.items():
        pieza = next(p for p in cargar() if p.nombre == nombre)
        masa = solido_de(pieza).volume * densidad_de(pieza.material) * 1000.0
        assert masa == pytest.approx(esperada, abs=0.001), (
            f"{nombre}: {masa:.3f} g ahora, {esperada:.3f} g cuando se contrastó "
            "con Onshape. Si el cambio es querido, redibuja la pieza en el CAD, "
            "comprueba la masa y actualiza este número."
        )


def test_solo_se_verifican_las_piezas_cuya_envolvente_es_el_solido():
    """Que nadie añada aquí un rodamiento por parecer fácil.

    La envolvente de un rodamiento es un anillo macizo: cabe donde cabe el
    rodamiento, que es para lo que está, pero pesa lo que no pesa. Meter su
    masa en la lista daría por verificado un número que es falso."""
    sin_envolvente_fiel = {
        "muelle_seguidor",
        "rodamiento_arbol",
        "rodillo_seguidor",
        "pinon_reductor",
        "rueda_reductor",
        "portaminas",
        "plancha_pom",
    }
    assert not (set(MASAS_VERIFICADAS) & sin_envolvente_fiel)
