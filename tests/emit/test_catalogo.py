"""El catálogo de sólidos comerciales.

**Lo que hay que comprobar no es que el sólido sea bonito: es que sus cotas
sean las de la ficha.** Toda la razón de generarlos en vez de bajarlos del
fabricante es que por construcción digan lo mismo que el compilador, y eso
se verifica midiendo la caja envolvente y comparándola con el JSON.
"""

from __future__ import annotations

import contextlib
from pathlib import Path

import pytest

from core.comercial import Cota, FamiliaComercial, Fuente, PiezaComercial
from core.errors import FichaIncompleta
from core.solido import densidad_de
from core.units import a_mm, mm
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
    assert (x, y, z) == pytest.approx((19.0, 19.0, 5.0))


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
    assert x == pytest.approx(15.0)
    assert y == pytest.approx(15.0)


def test_un_engranaje_sale_como_disco_al_diametro_exterior():
    """Sin dientes a propósito: para saber si cabe no aportan nada, la pieza
    se compra hecha, y dibujarlos sería adorno con riesgo de equivocarse."""
    x, _, z = caja_envolvente(
        pieza(FamiliaComercial.ENGRANAJE, exterior=43.4, agujero=15.0, ancho=4.0, modulo=0.7)
    )
    assert x == pytest.approx(43.4)
    assert z == pytest.approx(4.0)


def test_el_muelle_sale_como_el_cilindro_que_ocupa():
    _, _, z = caja_envolvente(pieza(FamiliaComercial.MUELLE, exterior=8.8, longitud_libre=68.0))
    assert z == pytest.approx(68.0)


def test_un_tornillo_tiene_cabeza_y_un_anillo_no():
    """Las dos formas viven en la misma familia y se distinguen por las
    cotas. Sin mirarlas, el anillo salía como un tornillo de cabeza Ø18."""
    tornillo = caja_envolvente(
        pieza(FamiliaComercial.FIJACION, metrica=3.0, cabeza=5.5, longitud=10.0)
    )
    anillo = caja_envolvente(
        pieza(FamiliaComercial.FIJACION, agujero=10.0, exterior=20.0, ancho=8.0)
    )
    assert tornillo[0] == pytest.approx(5.5)
    assert anillo[0] == pytest.approx(20.0)
    assert anillo[2] == pytest.approx(8.0)


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
            if c.nombre
            in ("exterior", "valona", "diametro", "cuerpo", "agarre_diametro", "ancho_plancha")
        ]
        if not radiales:
            continue
        x, y, _ = caja_envolvente(p)
        assert max(x, y) == pytest.approx(a_mm(max(radiales)), rel=1e-6), (
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
    assert ancho == pytest.approx(15.0, abs=1e-6)


# ---------------------------------------------------------------------------
# Las masas contrastadas contra Onshape
# ---------------------------------------------------------------------------

MASAS_VERIFICADAS = {
    "poste_pivote": 70.573,  # sin contrastar: 76,454 · 180/195, con base_al_plato ESTIMADO
    "arbol_de_levas": 65.353,  # la barra de los tres ejes: 73,985 · 106/120
    "pasador_indice": 1.332,
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
        # El sólido viene en mm³ (§ A_MM); la densidad, en kg/m³.
        volumen = solido_de(pieza).volume / 1000.0**3
        masa = volumen * densidad_de(pieza.material) * 1000.0
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


# ---------------------------------------------------------------------------
# La unidad que declara el archivo, que es la que lee el CAD
# ---------------------------------------------------------------------------

PREFIJOS_SI = {"": 1.0, "MILLI": 1e-3, "CENTI": 1e-2, "DECI": 1e-1, "KILO": 1e3}
"""Lo que vale en metros un número escrito en la unidad que declara el STEP."""


def _unidad_y_mayor_coordenada(ruta: Path) -> tuple[float, float]:
    """Cuánto mide en metros la unidad del archivo, y su mayor coordenada.

    Se lee el STEP **como texto**, igual que lo lee un CAD cualquiera, y no
    a través del kernel que lo escribió. Esa es toda la gracia: el kernel
    escribe y relee con el mismo criterio, así que un desajuste entre la
    cabecera y los números le resulta invisible.
    """
    import re

    texto = ruta.read_text(encoding="utf-8", errors="replace")
    unidad = re.search(
        r"LENGTH_UNIT\(\)[^;]*?SI_UNIT\(\s*(?:\.(\w+)\.|\$)\s*,\s*\.METRE\.",
        texto,
        re.DOTALL,
    )
    assert unidad is not None, f"{ruta.name} no declara LENGTH_UNIT: ningún CAD sabrá qué lee"
    factor = PREFIJOS_SI[unidad.group(1) or ""]

    # **Solo los puntos de TRES componentes.** Un punto del espacio de
    # parámetros de una superficie también se escribe como CARTESIAN_POINT,
    # y el de una circunferencia llega a 2π = 6,283: colado entre los del
    # modelo, un cilindro de Ø6 parecía medir 6,283.
    mayor = 0.0
    for punto in re.finditer(r"CARTESIAN_POINT\('[^']*',\(([^)]*)\)\)", texto):
        numeros = punto.group(1).split(",")
        if len(numeros) != 3:
            continue
        for numero in numeros:
            # Un punto puede llevar una referencia en vez de un número.
            with contextlib.suppress(ValueError):
                mayor = max(mayor, abs(float(numero)))
    return factor, mayor


def test_el_step_mide_lo_mismo_leido_con_la_unidad_que_declara(tmp_path: Path):
    """**La comprobación que faltaba, y por la que el catálogo entero salió
    mil veces pequeño.**

    El sólido se construía con las cotas en metros —el poste con radio
    0,004 y largo 0,195— y `export_step` escribía una cabecera que declara
    `SI_UNIT(.MILLI.,.METRE.)`. El archivo decía milímetros y llevaba
    metros dentro: las catorce referencias entraban en cualquier CAD a una
    milésima de su tamaño.

    Ninguno de los tests que ya había lo veía. `caja_envolvente` compara
    metros contra metros por los dos lados, y el de ida y vuelta pasa por
    `import_step`, que **comete el mismo error que el exportador**: escribe
    y relee el mismo número y da igual lo que diga la cabecera. Es la
    familia del `text-anchor`: una comprobación que modela al lector tiene
    que leer como lee él.

    El cerco: en todas estas formas —cilindros apoyados en Z = 0 y planchas
    centradas en XY— la mayor coordenada es o el radio mayor o la altura
    total, así que la mayor dimensión de la envolvente está entre una y dos
    veces esa coordenada. Un factor mil rompe el cerco por goleada.
    """
    for p in cargar():
        ruta = escribir_catalogo([p], tmp_path)[0]
        factor, coordenada = _unidad_y_mayor_coordenada(ruta)
        coordenada_mm = coordenada * factor / 1e-3
        dimension_mm = max(caja_envolvente(p))
        assert coordenada_mm <= dimension_mm * (1 + 1e-6), (
            f"{p.nombre}: el archivo dice {coordenada_mm:.4g} mm donde la pieza "
            f"mide {dimension_mm:.4g} mm — la cabecera y los números no concuerdan"
        )
        assert dimension_mm <= coordenada_mm * 2 * (1 + 1e-6), (
            f"{p.nombre}: el archivo dice {coordenada_mm:.4g} mm donde la pieza "
            f"mide {dimension_mm:.4g} mm — la cabecera y los números no concuerdan"
        )


def test_el_poste_mide_en_el_archivo_lo_que_dice_el_contrato(tmp_path: Path):
    """El caso concreto. El poste es un cilindro más alto que ancho, así que
    su mayor coordenada **es** su largo, en metros y no en milímetros, que es
    lo que salía. Fue 195 hasta que el portaminas fijó `base_al_plato`; ahora
    es lo que diga `poste_largo`."""
    from emit.plataforma import contrato_mm

    poste = next(x for x in cargar() if x.nombre == "poste_pivote")
    factor, coordenada = _unidad_y_mayor_coordenada(escribir_catalogo([poste], tmp_path)[0])
    assert coordenada * factor == pytest.approx(contrato_mm()["poste_largo"] / 1000.0, rel=1e-9)
