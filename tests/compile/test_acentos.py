"""Los acentos de la fuente que hay en el disco.

El núcleo tiene la **regla** y `tests/compile/test_fuentes.py` cruza la
regla contra el archivo de cada fuente. Lo que queda aquí es **lo que
cuesta**, que es lo que decide si un nombre cabe.
"""

from __future__ import annotations

from compile.texto import cargar_fuente, composicion_de

NOMBRES = (
    "Begoña Núria Sebastià Anaïs Martí Joaquín Mònica Francesc Jordi Montserrat Josep Maria Nicolás"
)
"""Nombres de los de aquí, con lo que el castellano y el catalán traen:
tilde de ñ, acento agudo y grave, diéresis y cedilla. Es la lista que de
verdad llega en un pedido, no un juego de caracteres."""


def test_un_acento_puede_costar_dos_levantadas_y_no_una() -> None:
    """«cada acento es un trazo más» es verdad en el glifo y **mentira en
    la palabra**.

    La marca va delante de la letra, así que se mete entre la letra
    anterior y esta y parte el enlace que la cursiva traía dibujado: se
    paga la marca y se paga el enlace perdido. «Begoña» cuesta dos
    levantadas más que «Begona», no una.

    Importa porque el techo medido está entre cinco y siete trazos: dos de
    más es la diferencia entre un nombre que cabe y uno que no.
    """
    assert len(composicion_de("Begoña").escritura.trazos) == 8
    assert len(composicion_de("Begona").escritura.trazos) == 6


def test_la_tilde_de_la_ene_no_cuesta_dos_trazos() -> None:
    """El `~` de la fuente son dos pasadas de la misma onda. Copiadas tal
    cual, «ñ» costaría dos levantadas y dibujaría la onda dos veces."""
    assert len(cargar_fuente().glifos["ñ"].trazos) == len(cargar_fuente().glifos["n"].trazos) + 1
