"""«Hola Mundo» con florituras: la prueba de capacidad del escribiente.

Es el pedido que se pidió para probar las tolerancias y las medidas nuevas,
y fue **el primero que no se podía fabricar**: la leva izquierda —la más
pequeña de la pila escalonada— se socava. Este test estaba escrito para
saltar el día que dejara de rechazarse, y saltó con el criterio de la
envolvente (docs/propuesta_dimensionado.md, fase 1): el rodillo sigue sin
entrar en algún tramo, pero la leva que sí se corta redondea la letra menos
de un cuarto de milímetro en el papel.

Lo que dice la auditoría (docs/auditoria_conjunto.md, A9): la exigencia
sobre la leva crece con el cuadrado de la tinta por grado y con la inversa
del radio de cada giro de la letra. «Hola Mundo» en cursiva lleva unos
450 mm de tinta en una vuelta. Sin la rúbrica, 342, y eso sí cabe desde el cabestrante 8:1.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from compile.escribiente import compilar
from scripts.exportar_para_cad import leer

pytestmark = pytest.mark.core

PEDIDO = Path(__file__).resolve().parents[2] / "demo" / "hola_mundo.json"


def test_el_pedido_esta_al_dia_con_su_generador():
    import json

    from scripts.escritura_hola_mundo import pedido

    assert json.loads(PEDIDO.read_text(encoding="utf-8")) == json.loads(json.dumps(pedido()))


def test_hola_mundo_con_florituras_cabe_recortando_la_leva_izquierda():
    """Sigue socavándose la leva pequeña de la pila, la izquierda; se corta su
    envolvente, y lo que redondea en el papel queda dentro de lo tolerable."""
    from compile.escribiente import SOCAVADO_TOLERABLE

    compilacion = compilar(leer(PEDIDO))
    v = compilacion.veredicto
    assert v.apto, [i.codigo for i in v.errores]
    assert "socavado_tolerable" in {i.codigo for i in v.avisos}
    assert v.metricas["radio_curvatura_min_izquierdo"] < v.metricas["radio_curvatura_min_derecho"]
    assert v.metricas["error_trazo_maximo"] <= SOCAVADO_TOLERABLE


SIN_RUBRICA = PEDIDO.with_name("hola_mundo_sin_rubrica.json")


def test_hola_mundo_sin_rubrica_cabe_en_una_vuelta():
    """**Varias palabras en una vuelta**, que es para lo que se subió la
    capacidad (brazos 55/50/45 y cabestrante 8:1): las dos palabras con los
    lazos de la H, la l y la d, 342 mm de tinta. Con los brazos 59/52/45 y
    la relación 6 cabían unos 190. La rúbrica sigue sin caber."""
    import json

    from scripts.escritura_hola_mundo import pedido_sin_rubrica

    datos = json.loads(SIN_RUBRICA.read_text(encoding="utf-8"))
    assert datos == json.loads(json.dumps(pedido_sin_rubrica()))
    v = compilar(leer(SIN_RUBRICA)).veredicto
    assert v.apto, [i.codigo for i in v.errores]
