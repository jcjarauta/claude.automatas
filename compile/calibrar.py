"""El cartucho de calibrar: tres discos redondos al radio de diseño.

Con él montado en fase cero, cada seguidor queda **exactamente en su punto
de diseño** (ψ = 0), que es donde se miden las dos cosas que se ajustan a
mano en la plataforma:

- la **orientación del collar** de cada seguidor, que pone a la vez el tope
  y la precarga del muelle: se gira hasta que la galga de `tope_galga`
  entra justa entre el pasador de tope y el seguidor, y se aprieta;
- el **calaje de los brazos**, que se fija deslizando la mordaza de la cinta
  (contrato de calaje, paso 1: «cartucho en fase cero»).

Es una herramienta de taller: va con la plataforma, no con un pedido. Sus
discos salen del mismo `sintetizar` que las levas, con el seguidor quieto,
así que su radio es el radio base de cada canal menos el rodillo, por el
mismo camino que fija el de las levas de verdad.
"""

from __future__ import annotations

import numpy as np

from compile.escribiente import SEGUIDORES, Escribiente, pieza_de_leva
from core.cam.curves import desde_muestras, rejilla
from core.cam.synth import sintetizar
from emit.pieza import Pieza


def cartucho_de_calibrar(maquina: Escribiente | None = None) -> list[Pieza]:
    """Las tres levas redondas, numeradas C-001…C-003 en el orden de
    `SEGUIDORES`, con su taladro de eje, su pasador y su marca de fase."""
    maquina = maquina or Escribiente()
    thetas = rejilla(48)
    quieto = desde_muestras(thetas, np.zeros_like(thetas), n=720)
    return [
        pieza_de_leva(
            sintetizar(quieto, maquina.seguidor(i)),
            nombre=f"disco de calibrar {nombre}",
            numero=f"C-{i + 1:03d}",
            conjunto="cartucho de calibrar",
            maquina=maquina,
        )
        for i, nombre in enumerate(SEGUIDORES)
    ]


__all__ = ["cartucho_de_calibrar"]
