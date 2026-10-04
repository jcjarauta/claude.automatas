"""C4 aplicado al escribiente: cuánto error llega de verdad a la punta.

`core/tolerance.py` monta la cadena. Este módulo la rellena con la geometría
del escribiente y la recorre entera, y es lo que convierte «±0,05 mm en el
canto» en un número que se puede prometer o no.

**Por qué hacía falta.** El compilador sabía decir que el trazo simulado se
desvía 0,108 mm, y ese número se estaba leyendo como la precisión de la
máquina. No lo es: es la precisión del **modelo**, o sea lo que se pierde por
muestrear la leva en 720 puntos e interpolar entre ellos. La máquina real
suma a eso lo que se desvía la pieza cortada, el juego de cada pivote y el
desgaste, todo multiplicado por lo que el varillaje amplifica.

**Lo que amplifica, y cuánto.** Con relación 6:1, brazo proximal de 90 mm y
brazo de seguidor de 45 mm, un error radial en el canto de la leva llega a la
punta multiplicado por unas **doce veces**. Los ±0,05 mm que se le piden al
taller son 0,6 mm en el papel: casi seis veces el error del modelo. **La
precisión de este producto no la decide el compilador**, y eso no se veía
hasta poner los dos números en la misma tabla.

**Y el amplificador 6:1 entra por un sitio distinto.** Su error nace dentro
de la transmisión, así que está medido en el lado del brazo y **no lo divide
la relación**, a diferencia del error de canto. Ahí la palanca a la punta son
172,5 mm, y eso hace que el mecanismo importe mucho más de lo que parece: un
par de engranajes de calidad 8d, con 0,08 mm de juego de flanco sobre un
piñón de 7 mm de radio, daba 1,98 mm en la punta y se convertía en el término
dominante de toda la cadena —el peor caso pasaba de 2,8 a 6,7 mm—.

Por eso el amplificador es un **cabestrante de cinta** y no engranajes. Una
cinta anclada por los dos extremos no tiene juego, solo elasticidad: 0,046
mm en la punta, dos órdenes de magnitud menos, y el corte vuelve a ser el
término dominante. El dato y su cuenta están en `bench/transmision.json`.

**Dos totales, y sirven para cosas distintas.** El peor caso suma todo como
si conspirara en el mismo sentido, y es lo que hay que usar para prometerle
una tolerancia a un cliente. El cuadrático compone en raíz de la suma de
cuadrados, que es lo que se mide en la práctica cuando las holguras son
independientes. La diferencia entre los dos es grande y decir cuál se usa no
es una formalidad.

**Aviso sobre lo que hay debajo.** De las contribuciones, **tres no están
medidas**: el error de perfil es la tolerancia que pedimos, no la que nos
dan; la holgura de pivote es una estimación de catálogo; y el de la transmisión
es una cuenta de elasticidad con un módulo elástico de manual y un factor 3
por el asiento de los anclajes que no sale de ningún sitio. Las mide E4.
Hasta entonces esto sirve para decidir arquitectura —si la relación 6:1 es
demasiado, si hace falta apretar al taller— y no para prometer una cota.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from pydantic import BaseModel, ConfigDict, Field

from compile.escribiente import SEGUIDORES, Compilacion, Escribiente
from core.tolerance import CadenaTolerancias, Contribucion, cadena
from core.units import Longitud, LongitudConCero, Radianes, mm

RAIZ = Path(__file__).resolve().parents[1]
RUTA_DE_LA_TRANSMISION = RAIZ / "bench" / "transmision.json"

MUESTRAS_DE_LA_CADENA = 36
"""En cuántas posiciones del ciclo se monta la cadena. La amplificación
cambia con la postura del varillaje —cerca de la singularidad se dispara— así
que se recorre el ciclo y se toma la peor, no una posición cualquiera."""


def juego_del_amplificador(ruta: Path = RUTA_DE_LA_TRANSMISION) -> Radianes:
    """Lo que la transmisión 6:1 pierde entre el seguidor y el brazo.

    En radianes **de brazo**, que es donde se mide: la transmisión está en
    medio, así que su error ya sale por el lado rápido y no lo divide la
    relación. Es el error de un factor seis que `core/tolerance.py` tiene
    pinchado con un test.

    **Depende del mecanismo, y por eso es un dato y no una constante.** Un
    par de engranajes de calidad 8d daba 1,1 × 10⁻² rad —1,98 mm en la
    punta, el término dominante de toda la cadena—. Una cinta anclada por
    los dos extremos no tiene juego, solo elasticidad, y da 2,7 × 10⁻⁴:
    0,046 mm. Son dos órdenes de magnitud y es lo que decidió el mecanismo.

    Vive en `bench/transmision.json` con la cuenta de la que sale. Si el
    archivo no está, devuelve cero —una máquina de transmisión directa no
    tiene este término— y no inventa uno.
    """
    if not ruta.exists():
        return Radianes(0.0)
    datos = json.loads(ruta.read_text(encoding="utf-8"))
    return Radianes(float(datos.get("juego_rad", 0.0)))


class Holguras(BaseModel):
    """De dónde viene el error, aparte del modelo.

    **Ninguno de estos dos números está medido.** Son la tolerancia que se
    pide y una estimación de catálogo, y los sustituirá el banco de E4. Van
    aquí, con nombre y valor por defecto, para que se vea qué se está
    suponiendo en vez de que quede escondido en una constante.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    error_de_perfil: Longitud = mm(0.05)
    """Lo que se desvía el canto cortado del canto teórico.

    Es la tolerancia que se le pide al taller, no la que se ha comprobado que
    da. Incluye el error de la máquina, el kerf mal compensado y el desgaste
    de la herramienta a lo largo del lote."""

    holgura_de_pivote: Radianes = Radianes(2.0e-4)
    """Juego angular de cada articulación, en radianes.

    Estimación: un rodamiento miniatura con una decena de micras de juego
    radial, sobre un brazo de unos 45 mm, da del orden de 2 × 10⁻⁴ rad. Es la
    contribución que **más incertidumbre tiene** y la que impide subir la
    relación del varillaje, porque se amplifica igual que todo lo demás."""

    desgaste: LongitudConCero = mm(0.0)
    """Cuánto se ha comido el canto de la leva. Cero en una máquina nueva;
    lo que mida E4 después de unos miles de ciclos."""

    juego_del_amplificador: Radianes = Field(default_factory=juego_del_amplificador)
    """Juego de flanco del par de engranajes 6:1, en radianes de brazo.

    **No lo divide la relación**, a diferencia del error de perfil: nace
    dentro de la transmisión y ya está medido en el lado del brazo. Es el
    error de un factor seis que `core/tolerance.py` tiene pinchado con un
    test.

    Sale de `bench/juego_de_flanco.json` y del radio primitivo del piñón, y
    hoy es una **estimación**, no una medida: el catálogo da la calidad del
    dentado y no la desviación de espesor de diente.

    Y puede valer cero sin cambiar los engranajes: el juego solo se abre
    cuando el engrane se descarga. Un muelle que mantenga el brazo apoyado
    siempre contra el mismo flanco lo cierra, a cambio de sumar su par al
    que pide la leva. Eso no está diseñado todavía."""


@dataclass(frozen=True)
class Presupuesto:
    """El error que cabe esperar en la punta, y de dónde sale cada parte."""

    cadena: CadenaTolerancias
    theta_peor: float
    """En qué punto del ciclo se ha evaluado la cadena: el peor."""

    @property
    def peor_caso(self) -> float:
        """Todo conspirando en el mismo sentido. Lo que se promete."""
        return self.cadena.peor_caso

    @property
    def cuadratica(self) -> float:
        """Holguras independientes. Lo que se suele medir."""
        return self.cadena.cuadratica

    @property
    def dominante(self) -> Contribucion | None:
        """Por dónde empezar a mejorar."""
        return self.cadena.dominante


def _angulos_de_presion(compilacion: Compilacion) -> tuple[float, ...]:
    """El peor ángulo de presión de cada leva, que es donde más amplifica."""
    return tuple(
        float(compilacion.veredicto.metricas.get(f"angulo_presion_max_{nombre}", 0.0))
        for nombre in SEGUIDORES[:2]
    )


def presupuesto_de_error(
    compilacion: Compilacion,
    maquina: Escribiente,
    holguras: Holguras | None = None,
) -> Presupuesto:
    """Monta la cadena en el peor punto del ciclo y la devuelve entera.

    Solo entran los **dos brazos**: el elevador mueve el lápiz en vertical y
    su error no desplaza el trazo sobre el papel, lo levanta antes o después.
    Eso se juzga en otro sitio.

    El varillaje **amplifica** en vez de reducir, así que la `reduccion` de
    C4 entra como `1/relacion`. No es un apaño de signo: es exactamente lo
    que significa que el seguidor barra un sexto de lo que barre el brazo.
    """
    holguras = holguras or Holguras()
    if not compilacion.perfiles or compilacion.simulacion is None:
        raise ValueError("no hay nada que presupuestar: la compilación no llegó a simular")

    # Cada brazo con su seguidor: la pila escalonada les da brazos distintos,
    # y el más largo amplifica menos el error del canto.
    brazos = (
        float(maquina.brazos_de_canal[SEGUIDORES.index("izquierdo")]),
        float(maquina.brazos_de_canal[SEGUIDORES.index("derecho")]),
    )
    presiones = _angulos_de_presion(compilacion)
    error_de_canto = float(holguras.error_de_perfil) + float(holguras.desgaste)

    # La amplificación cambia con la postura, así que se recorre el ciclo.
    simulacion = compilacion.simulacion
    indices = np.linspace(0, len(simulacion.thetas) - 1, MUESTRAS_DE_LA_CADENA, dtype=int)
    peor: CadenaTolerancias | None = None
    theta_peor = 0.0
    for indice in indices:
        psi = maquina.brazo.inversa(simulacion.puntos[indice : indice + 1])
        aqui = cadena(
            maquina.brazo,
            psi,
            brazos_seguidor=brazos,
            angulos_presion=presiones,
            error_perfil=error_de_canto,
            holgura_pivote=float(holguras.holgura_de_pivote),
            reduccion=1.0 / maquina.relacion,
            juego_de_la_transmision=float(holguras.juego_del_amplificador),
        )
        if peor is None or aqui.peor_caso > peor.peor_caso:
            peor = aqui
            theta_peor = float(simulacion.thetas[indice])

    if peor is None:  # pragma: no cover - MUESTRAS_DE_LA_CADENA > 0 por construcción
        raise ValueError("no se pudo montar la cadena en ninguna posición del ciclo")

    # El error del modelo ya está en la punta: no lo amplifica nadie, porque
    # es lo que el simulador mide en el papel. Entra con amplificación 1.
    del_modelo = Contribucion(
        nombre="muestreo del modelo",
        magnitud=simulacion.error_maximo,
        amplificacion=1.0,
    )
    return Presupuesto(
        cadena=CadenaTolerancias(contribuciones=(*peor.contribuciones, del_modelo)),
        theta_peor=theta_peor,
    )


def amplificacion_del_canto(maquina: Escribiente) -> float:
    """Cuánto multiplica el varillaje un error radial en el canto de la leva.

    La cuenta corta, sin corregir por ángulo de presión:

        relacion × brazo proximal / brazo del seguidor = 6 × 90 / 52 ≈ 10,4

    con el brazo de seguidor más corto de los dos que mueven la punta, que es
    el que más amplifica.

    Sirve para hablar con el taller —«cada centésima que os paséis son doce
    en el papel»— y para comprobar de cabeza lo que devuelve la cadena.
    """
    corto = min(
        float(maquina.brazos_de_canal[SEGUIDORES.index(n)]) for n in ("izquierdo", "derecho")
    )
    return maquina.relacion * float(maquina.proximal) / corto


__all__ = [
    "MUESTRAS_DE_LA_CADENA",
    "RUTA_DE_LA_TRANSMISION",
    "Holguras",
    "Presupuesto",
    "amplificacion_del_canto",
    "juego_del_amplificador",
    "presupuesto_de_error",
]
