"""«Hola Mundo» con florituras: la prueba de capacidad del escribiente.

Es el pedido que se pidió para probar las tolerancias y las medidas nuevas,
y **hoy no es fabricable**: la leva izquierda —la más pequeña de la pila
escalonada— se socava. No es un error del compilador, es el límite de la
máquina, y este test lo deja escrito. El día que algo de la máquina cambie
y deje de socavarse, salta: y entonces hay un juego de levas nuevo.

Lo que dice la auditoría (docs/auditoria_conjunto.md, A9): la exigencia
sobre la leva crece con el cuadrado de la tinta por grado y con la inversa
del radio de cada giro de la letra. «Hola Mundo» en cursiva lleva unos
450 mm de tinta en una vuelta; los pedidos que caben, de 60 a 141.
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


def test_hola_mundo_con_florituras_no_cabe_en_una_vuelta():
    compilacion = compilar(leer(PEDIDO))
    v = compilacion.veredicto
    assert not v.apto
    assert "perfil_autointersecado" in {i.codigo for i in v.errores}
    # Y lo que manda es la leva pequeña de la pila: la izquierda.
    assert v.metricas["radio_curvatura_min_izquierdo"] < v.metricas["radio_curvatura_min_derecho"]
