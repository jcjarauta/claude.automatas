"""Geometría compartida por los tests de emisores.

Una pieza real, hecha con el núcleo, para no probar la maquetación contra un
polígono inventado que no se parece a lo que va a salir de verdad.
"""

from __future__ import annotations

import numpy as np

from core.cam.curves import desde_muestras, rejilla
from core.cam.synth import Seguidor, sintetizar
from core.units import Metros, grados, mm
from emit.pieza import Pieza, Polilinea, Taladro, Veta


def perfil_de_leva(
    amplitud_grados: float = 12.0, muestras: int = 180
) -> list[tuple[Metros, Metros]]:
    thetas = rejilla(48)
    psi = desde_muestras(thetas, grados(amplitud_grados) * np.sin(thetas), n=muestras)
    seguidor = Seguidor.bien_puesto(radio_base=mm(40.0), brazo=mm(60.0), radio_rodillo=mm(4.0))
    perfil = sintetizar(psi, seguidor)
    return [(Metros(x), Metros(y)) for x, y in perfil.perfil]


def leva(**cambios: object) -> Pieza:
    """La leva de referencia de los tests. `cambios` sustituye campos."""
    contorno = perfil_de_leva()
    campos: dict[str, object] = {
        "nombre": "leva x",
        "numero": "C-001",
        "conjunto": "cartucho hola",
        "material": "POM 5 mm",
        "espesor": mm(5.0),
        "cantidad": 1,
        "veta": Veta.INDIFERENTE,
        "contorno": contorno,
        "taladros": [Taladro(centro=(Metros(0.0), Metros(0.0)), diametro=mm(8.0))],
        "referencias": [
            Polilinea(puntos=[(Metros(-0.05), Metros(0.0)), (Metros(0.05), Metros(0.0))])
        ],
        "marca_fase": contorno[0],
    }
    campos.update(cambios)
    return Pieza(**campos)  # type: ignore[arg-type]


def bastidor_grande() -> Pieza:
    """Una pieza que no cabe en A4 ni en A3: obliga a trocear."""
    ancho, alto = 0.520, 0.380
    return Pieza(
        nombre="bastidor",
        numero="B-001",
        conjunto="escribiente",
        material="contrachapado de abedul 9 mm",
        espesor=mm(9.0),
        cantidad=1,
        veta=Veta.LARGO,
        contorno=[
            (Metros(0.0), Metros(0.0)),
            (Metros(ancho), Metros(0.0)),
            (Metros(ancho), Metros(alto)),
            (Metros(0.0), Metros(alto)),
        ],
        taladros=[Taladro(centro=(Metros(0.040), Metros(0.040)), diametro=mm(6.0))],
    )
