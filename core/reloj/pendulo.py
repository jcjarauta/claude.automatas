"""C11 · el pendulo compuesto: periodo, energia y factor de calidad.

**El unico modulo del proyecto donde el tiempo es una magnitud.** Ver la regla
del tiempo en `docs/reloj/expediente.md`: el segundo entra por el oscilador y
no sale de aqui.

Por que no vale el pendulo simple
---------------------------------
La formula de libro, `T = 2*pi*sqrt(L/g)`, supone toda la masa en un punto a
distancia L. En un pendulo real la varilla tiene masa repartida y la lenteja
tiene tamano, y las dos cosas tiran del periodo en sentidos contrarios:

- la masa de la varilla esta **mas arriba** que la lenteja, asi que sube menos
  el momento de inercia de lo que sube... no: sube el inercia menos de lo que
  sube el momento recuperador, y el conjunto oscila **mas deprisa**;
- por eso un pendulo real de 994 mm de lenteja bate algo mas rapido que 2 s, y
  hay que alargarlo para compensar.

De ahi la forma general,

    T = 2*pi*sqrt(I_O / (m*g*d))

con `I_O` el momento de inercia respecto al punto de suspension y `d` la
distancia de la suspension al centro de masas del conjunto.

Que se mide y que se estima
---------------------------
El periodo y la energia salen de la geometria y son fiables. El **factor de
calidad no**: depende del amortiguamiento interno del fleje y del apriete de
su mordaza, que no estan en ninguna tabla. Lo que si se puede acotar es el
arrastre del aire, y sirve para saber **donde no esta** el problema:
`calidad_por_el_aire` da varios miles, asi que lo que limite el Q real sera la
suspension. Esa es la conclusion que decide donde mirar en R1.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Final

from core.units import Julios, Kilogramos, Metros, Radianes

G: Final[float] = 9.80665
"""Aceleracion de la gravedad, m/s2. Valor normal; la local cambia el periodo
en menos de una parte en mil, que son 40 s/dia y los absorbe la tuerca."""

DENSIDAD_AIRE: Final[float] = 1.2
"""kg/m3 a 20 C y nivel del mar."""

ARRASTRE_LENTEJA: Final[float] = 1.1
"""Coeficiente de un cilindro corto moviendose de canto."""

ARRASTRE_VARILLA: Final[float] = 1.2
"""Coeficiente de un fleje plano de canto al aire."""

SEGUNDOS_POR_DIA: Final[float] = 86400.0


@dataclass(frozen=True)
class Pendulo:
    """Lenteja puntual mas varilla uniforme, medidas desde el punto de flexion.

    `varilla_desde` y `varilla_hasta` son las distancias al punto de flexion
    del muelle, no al canto del soporte: el pivote efectivo cae a mitad del
    tramo libre y es de ahi de donde cuelga todo.
    """

    masa_lenteja: Kilogramos
    centro_lenteja: Metros
    masa_varilla: Kilogramos
    varilla_desde: Metros
    varilla_hasta: Metros

    @property
    def largo_varilla(self) -> float:
        return self.varilla_hasta - self.varilla_desde

    @property
    def centro_varilla(self) -> float:
        return (self.varilla_desde + self.varilla_hasta) / 2.0

    @property
    def masa(self) -> float:
        return self.masa_lenteja + self.masa_varilla

    @property
    def centro_de_masas(self) -> float:
        """Distancia del punto de flexion al centro de masas del conjunto."""
        return (
            self.masa_lenteja * self.centro_lenteja + self.masa_varilla * self.centro_varilla
        ) / self.masa

    @property
    def inercia(self) -> float:
        """Momento de inercia respecto al punto de suspension, kg*m2.

        La varilla aporta su inercia propia mas el termino de Steiner. Para
        una barra uniforme la inercia propia es m*l^2/12, y con la barra
        colgada de un extremo los dos terminos juntos dan el clasico m*l^2/3.
        """
        propia = self.masa_varilla * self.largo_varilla**2 / 12.0
        return (
            self.masa_lenteja * self.centro_lenteja**2
            + propia
            + self.masa_varilla * self.centro_varilla**2
        )

    def periodo(self) -> float:
        """Segundos por oscilacion completa, en angulo pequeno."""
        return 2.0 * math.pi * math.sqrt(self.inercia / (self.masa * G * self.centro_de_masas))

    def longitud_equivalente(self) -> float:
        """El largo del pendulo simple que bate igual. Es lo que hay que
        comparar con `longitud_pendulo_nominal`, y no la posicion de la
        lenteja."""
        return self.inercia / (self.masa * self.centro_de_masas)

    def energia(self, amplitud: Radianes) -> Julios:
        """Energia almacenada en el punto de retorno.

        Es la que se reparte entre potencial y cinetica a lo largo del ciclo,
        y la referencia contra la que se mide lo que pierde.
        """
        return Julios(self.masa * G * self.centro_de_masas * (1.0 - math.cos(amplitud)))

    def perdida_por_ciclo(self, amplitud: Radianes, calidad: float) -> Julios:
        """Lo que hay que reponerle cada oscilacion, por definicion de Q."""
        return Julios(2.0 * math.pi * self.energia(amplitud) / calidad)

    def potencia_de_mantenimiento(self, amplitud: Radianes, calidad: float) -> float:
        """Vatios. Sale en microvatios, y esa es la cifra que ordena el plan:
        mantener el pendulo no cuesta casi nada, asi que la pesa la decide el
        rozamiento de todo lo demas."""
        return self.perdida_por_ciclo(amplitud, calidad) / self.periodo()

    def perdida_por_el_aire(
        self,
        amplitud: Radianes,
        frente_lenteja: Metros,
        alto_lenteja: Metros,
        ancho_varilla: Metros,
    ) -> Julios:
        """Energia que se lleva el aire en un ciclo, con arrastre cuadratico.

        Integrando F = 1/2 * rho * Cd * A * v^2 sobre el ciclo con
        v(theta) = r*w*sqrt(A0^2 - theta^2), cada elemento a radio r aporta
        (4/3)*rho*Cd*w^2*A0^3 por su r^3. De ahi que la lenteja, que esta al
        final, pese tanto mas que la varilla entera.
        """
        w = 2.0 * math.pi / self.periodo()
        comun = (4.0 / 3.0) * DENSIDAD_AIRE * w**2 * amplitud**3
        area = frente_lenteja * alto_lenteja
        lenteja = comun * ARRASTRE_LENTEJA * area * self.centro_lenteja**3
        # La varilla se integra a lo largo: cada franja aporta su r^3.
        varilla = (
            comun
            * ARRASTRE_VARILLA
            * ancho_varilla
            * (self.varilla_hasta**4 - self.varilla_desde**4)
            / 4.0
        )
        return Julios(lenteja + varilla)

    def calidad_por_el_aire(
        self,
        amplitud: Radianes,
        frente_lenteja: Metros,
        alto_lenteja: Metros,
        ancho_varilla: Metros,
    ) -> float:
        """El Q que daria el pendulo si el aire fuese su unica perdida.

        **No es una prediccion del Q real**: es una cota superior, y su valor
        esta en que dice donde NO esta el problema. Si sale en varios miles,
        lo que limita es la suspension.
        """
        perdida = self.perdida_por_el_aire(amplitud, frente_lenteja, alto_lenteja, ancho_varilla)
        return 2.0 * math.pi * self.energia(amplitud) / perdida

    def deriva_por_milimetro(self) -> float:
        """Segundos al dia que gana el reloj por cada milimetro que se acorta.

        De dT/T = dL/(2L). Es LA cifra del proyecto: sobre un metro, un
        milimetro son casi tres cuartos de minuto al dia.
        """
        return SEGUNDOS_POR_DIA * 0.001 / (2.0 * self.longitud_equivalente())


def centro_para_periodo(
    periodo: float,
    masa_lenteja: Kilogramos,
    densidad_varilla: float,
    ancho_varilla: Metros,
    espesor_varilla: Metros,
    flexion_a_varilla: Metros,
    centro_bajo_varilla: Metros,
) -> float:
    """C11 al reves: donde va el centro de la lenteja para batir `periodo`.

    Es la direccion que usa el compilador, porque el periodo se **elige** y la
    posicion se **calcula**. Y no tiene solucion cerrada: la varilla es mas
    larga cuanto mas abajo va la lenteja, asi que su masa y su inercia
    dependen de la incognita. Se resuelve por biseccion, que converge seguro
    porque el periodo crece de forma monotona con la distancia.

    Devuelve metros del punto de flexion al centro de masas de la lenteja.
    """

    def periodo_de(centro: float) -> float:
        largo = centro - flexion_a_varilla - centro_bajo_varilla
        masa = densidad_varilla * largo * ancho_varilla * espesor_varilla
        return Pendulo(
            masa_lenteja=masa_lenteja,
            centro_lenteja=Metros(centro),
            masa_varilla=Kilogramos(max(masa, 1.0e-12)),
            varilla_desde=flexion_a_varilla,
            varilla_hasta=Metros(flexion_a_varilla + largo),
        ).periodo()

    # El pendulo simple es siempre una cota inferior: la varilla solo puede
    # acelerarlo, asi que la solucion real esta por debajo. Se abre el
    # intervalo hacia arriba hasta encerrarla.
    bajo = G * periodo**2 / (4.0 * math.pi**2)
    alto = bajo * 1.5
    for _ in range(200):
        medio = (bajo + alto) / 2.0
        if periodo_de(medio) < periodo:
            bajo = medio
        else:
            alto = medio
    return (bajo + alto) / 2.0
