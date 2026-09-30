"""El golden del perfil **compilado**, que es el que faltaba.

`tests/emit/test_dxf.py` guarda una leva sintética: vigila el escritor de DXF
y no la geometría que sale del compilador. Con eso, cambiar el front-end de
escritura movía los tres perfiles de un pedido real sin que saltara ninguna
comparación byte a byte —pasó dos veces seguidas, con el arreglo del vuelo y
con el redondeo de esquinas— y la etapa E5 daba por cumplido un criterio que
decía «los DXF de los casos de referencia».

Aquí se compilan **cuatro** casos, no uno, y de cada uno se guarda el sha256
de sus tres DXF más los números de cabecera. El hash es la comparación byte a
byte; los números están para poder decir **qué** se ha movido, porque un
golden que solo dice «ha cambiado» obliga a reconstruir el porqué a mano.

Si el cambio es querido:  uv run python scripts/regenerar_golden.py
"""

from __future__ import annotations

import json

import pytest

from tests.casos import CASOS, GOLDEN, manifiesto

pytestmark = pytest.mark.golden


@pytest.mark.parametrize("nombre", sorted(CASOS))
def test_el_pedido_compilado_no_ha_cambiado(nombre: str):
    ruta = GOLDEN / f"{nombre}.json"
    assert ruta.exists(), f"falta {ruta.name}: regenera con scripts/regenerar_golden.py"
    guardado = json.loads(ruta.read_text(encoding="utf-8"))
    ahora = manifiesto(nombre)

    # Primero lo que se lee, para que el fallo diga qué pasó y no solo que pasó.
    for clave in ("apto", "errores", "avisos", "tramos", "calajes_grados"):
        assert ahora[clave] == guardado[clave], f"{nombre}: ha cambiado «{clave}»"
    for clave in ("error_trazo_mm", "desviacion_de_lo_capturado_mm"):
        assert ahora[clave] == pytest.approx(guardado[clave], abs=1e-6), (
            f"{nombre}: {clave} pasa de {guardado[clave]} a {ahora[clave]}"
        )
    for antes, despues in zip(guardado["levas"], ahora["levas"], strict=True):
        for clave in (
            "radio_maximo_mm",
            "radio_minimo_mm",
            "curvatura_minima_mm",
            "presion_maxima_grados",
        ):
            assert despues[clave] == pytest.approx(antes[clave], abs=1e-6), (
                f"{nombre}/{antes['canal']}: {clave} pasa de {antes[clave]} a {despues[clave]}"
            )
        assert despues["puntos_del_contorno"] == antes["puntos_del_contorno"]

    # Y al final el byte a byte, que caza lo que los números no miran.
    for antes, despues in zip(guardado["levas"], ahora["levas"], strict=True):
        assert despues["sha256"] == antes["sha256"], (
            f"{nombre}/{antes['canal']}: el DXF ya no es el mismo aunque la geometría "
            "medida cuadre. Mira el rótulo, las capas o el orden de las entidades"
        )


def test_los_cuatro_casos_tensan_cosas_distintas():
    """Un golden de cuatro casos iguales vigila lo mismo cuatro veces. Esto
    comprueba que siguen siendo distintos: si alguien toca un caso y lo deja
    como otro, el golden pierde cobertura sin que se note."""
    guardados = [json.loads((GOLDEN / f"{n}.json").read_text(encoding="utf-8")) for n in CASOS]
    assert {g["apto"] for g in guardados} == {True, False}, (
        "hace falta al menos un caso que no quepa: si no, nadie vigila el "
        "camino del veredicto negativo"
    )
    assert len({len(g["tramos"]) for g in guardados}) >= 3
