"""C9 · Lo que una persona puede dar en una manivela, ángulo a ángulo.

Una manivela no da par constante. Cambia con el ángulo del brazo, con la
altura a la que está el eje y con si se gira con una mano o con las dos, y
esa variación es la que decide si la escritura sale limpia o a tirones: el
par disponible tiene que cubrir al pedido **en cada grado**, no de media.

El modelo de aquí es deliberadamente pobre y está declarado como tal: una
curva con un suelo y una variación sinusoidal por vuelta de manivela.

    T(φ) = T_max · (suelo + (1 - suelo) · |sin(φ + fase)|)

Se parece a lo que mide un ergómetro de manivela pero **no es un dato
medido**. En cuanto el banco registre una curva real, ese fichero manda y
esto queda de valor por defecto, igual que pasa con el kerf y con las
densidades. Está en `bench/` el sitio donde irá.

Lo que sí es exacto es la transmisión: si la manivela da `n` vueltas por
cada vuelta del árbol, el par en el árbol se multiplica por `n` y por el
rendimiento. Ahí está la respuesta a si hace falta un reductor.
"""

from __future__ import annotations

import numpy as np
import numpy.typing as npt
from pydantic import BaseModel, ConfigDict, Field

from core.units import Angulo, NewtonMetro, Par, Radianes

Arreglo = npt.NDArray[np.float64]


class Manivela(BaseModel):
    """Lo que da la persona, en su propio eje."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    par_maximo: Par = NewtonMetro(4.0)
    """N·m en el punto bueno del giro. Cuatro newton·metro es lo que hace sin
    esforzarse un adulto con una manivela de 100 mm, empujando con unos 40 N."""
    suelo: float = Field(default=0.45, gt=0.0, le=1.0)
    """Qué fracción del máximo queda en el punto malo. Con 1 la manivela daría
    lo mismo en todo el giro, que es lo que hace un motor y no una persona."""
    fase: Angulo = Radianes(0.0)
    """Dónde cae el punto bueno respecto del cero del árbol. Es un grado de
    libertad del montaje: girar la manivela sobre su eje mueve esta curva y
    puede sacar de apuros un pedido justo."""

    def par(self, theta_arbol: Arreglo, relacion: float = 1.0) -> Arreglo:
        """Par disponible en el **eje de la manivela**, en N·m.

        `theta_arbol` es el ángulo del árbol maestro; con una relación
        distinta de uno, la manivela ha dado `relacion` veces esa vuelta.
        """
        angulo = relacion * np.asarray(theta_arbol, dtype=np.float64) + float(self.fase)
        variacion = self.suelo + (1.0 - self.suelo) * np.abs(np.sin(angulo))
        return np.asarray(float(self.par_maximo) * variacion)


class Transmision(BaseModel):
    """De la manivela al árbol maestro."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    relacion: float = Field(default=1.0, ge=1.0, le=50.0)
    """Vueltas de manivela por vuelta del árbol. Uno es manivela calada
    directamente en el eje. Más es un reductor: multiplica el par disponible
    por el mismo factor, y multiplica también las vueltas que hay que dar."""
    rendimiento: float = Field(default=0.9, gt=0.0, le=1.0)
    """Lo que se queda la transmisión. Un par de engranajes rectos bien
    hechos anda por 0,95; una correa con tensor, por 0,9."""

    def disponible(self, manivela: Manivela, theta_arbol: Arreglo) -> Arreglo:
        """Par disponible **en el árbol maestro**, en N·m.

        Es donde hay que compararlo con lo que piden las levas: el reductor
        multiplica el par y divide la velocidad, y por eso una frase que no
        se puede girar a mano con relación 1 puede girarse con relación 3.
        """
        return np.asarray(
            manivela.par(theta_arbol, self.relacion) * self.relacion * self.rendimiento
        )


def relacion_minima(
    manivela: Manivela,
    pedido: Arreglo,
    thetas: Arreglo,
    rendimiento: float = 0.9,
    margen: float = 1.3,
    maxima: float = 50.0,
) -> float | None:
    """La relación más pequeña con la que el par disponible cubre al pedido.

    Se prueban relaciones enteras porque un reductor de 2,7:1 no se compra
    hecho. `margen` es cuánto hay que sobrar: girar una manivela al límite de
    lo que uno puede no es girarla, es forcejear con ella, y eso sale en el
    papel.

    Devuelve `None` si ni la relación máxima llega: entonces el problema no
    es de transmisión, es que la máquina pide demasiado.
    """
    demanda = np.max(np.asarray(pedido, dtype=np.float64))
    if demanda <= 0.0:
        return 1.0
    for relacion in range(1, int(maxima) + 1):
        transmision = Transmision(relacion=float(relacion), rendimiento=rendimiento)
        if float(np.min(transmision.disponible(manivela, thetas))) >= margen * demanda:
            return float(relacion)
    return None


__all__ = ["Manivela", "Transmision", "relacion_minima"]
