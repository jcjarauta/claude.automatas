"""Los acentos de la fuente que hay en el disco.

El núcleo tiene la **regla**; aquí se mira el **archivo**, que es lo que de
verdad acaba en una leva. Son dos cosas distintas y por eso se cruzan: la
fuente se compone una vez al extraerla y se congela, así que lo único que
puede pasar en silencio es que alguien la retoque a mano o que se cambie la
regla y se olvide regenerarla.
"""

from __future__ import annotations

import json

from compile.texto import FUENTES, cargar_fuente, composicion_de
from core.tipografia import ACENTOS, Fuente, acentuar

NOMBRES = (
    "Begoña Núria Sebastià Anaïs Martí Joaquín Mònica Francesc Jordi Montserrat Josep Maria Nicolás"
)
"""Nombres de los de aquí, con lo que el castellano y el catalán traen:
tilde de ñ, acento agudo y grave, diéresis y cedilla. Es la lista que de
verdad llega en un pedido, no un juego de caracteres."""


def test_la_fuente_del_disco_trae_los_acentos_que_compone_el_nucleo() -> None:
    """Se recompone desde los 96 glifos de 1967 que hay en el mismo archivo
    y tiene que salir **lo mismo**, al bit.

    Es el cruce de dos listas que describen la misma cosa desde lados
    distintos: la regla, en `core/`, y el dato congelado, en `docs/`. Si
    falla, lo que toca es `uv run python scripts/extraer_fuente.py cursiva`,
    no ajustar el test.
    """
    crudo = json.loads((FUENTES / "cursiva.json").read_text(encoding="utf-8"))
    sin_acentos = {
        **crudo,
        "glifos": {c: g for c, g in crudo["glifos"].items() if c not in ACENTOS},
    }
    assert len(sin_acentos["glifos"]) == 96
    assert acentuar(Fuente.model_validate(sin_acentos)) == {
        c: g for c, g in cargar_fuente().glifos.items() if c in ACENTOS
    }


def test_la_fuente_escribe_los_nombres_de_la_casa() -> None:
    """Sin esto la máquina escribe «Begona», que no es un fallo menor: es
    otro nombre."""
    assert cargar_fuente().faltan(NOMBRES) == []


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
