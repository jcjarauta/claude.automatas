"""La fuente del repositorio, contrastada contra lo que ya estaba a mano.

`scripts/escritura_feliz_cumpleanos.py` lleva trece glifos **copiados a
mano** de la Hershey cursiva, uno a uno, para que «Feliz cumpleaños»
saliera igual en cada máquina. `docs/fuentes/cursiva.json` trae los
noventa y seis, extraídos del paquete con un script.

Son dos caminos que no comparten una línea de código: uno pasó por los
ojos de una persona y el otro por `scripts/extraer_fuente.py`. Si los
trece coinciden al entero, la extracción de los otros ochenta y tres es
de fiar; y si algún día dejan de coincidir, es que una de las dos se ha
movido y hay que mirar cuál.
"""

from __future__ import annotations

import pytest

from compile.texto import cargar_fuente
from scripts.escritura_feliz_cumpleanos import GLIFOS

pytestmark = pytest.mark.core


def test_los_trece_glifos_copiados_a_mano_son_los_de_la_fuente():
    fuente = cargar_fuente("cursiva")
    for letra, (lado_izquierdo, avance, trazos) in GLIFOS.items():
        glifo = fuente.glifos[letra]
        assert glifo.lado_izquierdo == lado_izquierdo, letra
        assert glifo.avance == avance, letra
        assert [[tuple(p) for p in t] for t in glifo.trazos] == [
            [tuple(p) for p in t] for t in trazos
        ], letra


def test_la_fuente_trae_el_abecedario_entero_y_los_digitos():
    """Si falta una letra se descubre con el pedido de alguien delante."""
    fuente = cargar_fuente("cursiva")
    for letra in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789 .,-":
        assert letra in fuente.glifos, letra


def test_la_fuente_dice_de_dónde_viene():
    """Es de dominio público con petición de atribución, y eso viaja con
    el dato y no en un comentario del código que la extrajo."""
    fuente = cargar_fuente("cursiva")
    assert "Hershey" in fuente.procedencia
