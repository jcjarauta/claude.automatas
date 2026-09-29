"""Calibración de impresora: hoja patrón, perfil y corrección de escala.

Una impresora no imprime a escala. El error típico está entre el 0,2 y el 1 %,
y es **sistemático**: la misma máquina con el mismo papel se equivoca siempre
igual. Lo sistemático se compensa. La deriva —humedad, fusor, arrastre— no, y
por eso el cuadro de 100 mm sigue en todas las hojas aunque haya perfil
aplicado: **compensar no es verificar**.

Dos factores y no uno, porque el arrastre del papel deforma más en la
dirección de avance que a lo ancho, y un factor único repartiría el error del
eje malo sobre el bueno.

El patrón de medida es más largo que el cuadro. Leer 100 mm con una regla da
un error de unos ±0,25 mm, o sea un 0,25 %, del mismo orden que el error que
se busca: calibrar sobre 100 mm no mejora casi nada. De ahí que la hoja patrón
lleve un rectángulo de 150 × 200 mm en A4, con la marca de 100 mm dentro, y
que el perfil anote con qué instrumento se midió.

El recorrido completo, que es lo que firma la puerta de E3:

    hoja_patron() -> imprimir -> medir -> PerfilImpresora -> aplicar()
    -> reimprimir -> el cuadro mide 100 mm

`aplicar()` es geometría pura sobre una `Lamina` ya maquetada. No sabe de PDF.
"""

from __future__ import annotations

import json
from datetime import date
from enum import StrEnum
from pathlib import Path
from typing import Annotated, Final

from pydantic import BaseModel, ConfigDict, Field, computed_field, model_validator

from core.verdict import Incidencia, Veredicto
from emit.layout import (
    LADO_CALIBRACION,
    MARGEN,
    Circulo,
    Formato,
    Lamina,
    Texto,
    Trazo,
    cuadro_de_calibracion,
)

# ---------------------------------------------------------------------------
# Instrumentos y patrones
# ---------------------------------------------------------------------------


class Instrumento(StrEnum):
    """Con qué se mide la hoja patrón. Fija la incertidumbre de la medida."""

    PIE_DE_REY = "pie_de_rey"
    CINTA_METRICA = "cinta_metrica"
    REGLA = "regla"

    @property
    def resolucion(self) -> float:
        """Milímetros de lectura. No es la precisión del aparato sino lo que
        de verdad se distingue apoyándolo sobre una hoja impresa."""
        return {
            Instrumento.PIE_DE_REY: 0.05,
            Instrumento.CINTA_METRICA: 1.0,
            Instrumento.REGLA: 0.5,
        }[self]

    @property
    def alcance(self) -> float:
        """Hasta dónde llega. Un pie de rey corriente no pasa de 150 mm, y por
        eso la hoja patrón lleva marcas intermedias rotuladas."""
        return {
            Instrumento.PIE_DE_REY: 150.0,
            Instrumento.CINTA_METRICA: 3000.0,
            Instrumento.REGLA: 300.0,
        }[self]


PATRONES: Final[tuple[float, ...]] = (150.0, 200.0, 250.0, 300.0, 400.0, 500.0, 750.0, 1000.0)
"""Longitudes redondas admitidas para el rectángulo patrón. Redondas a
propósito: un patrón de 187,3 mm invita a equivocarse al apuntar la medida."""

ALTO_TITULO: Final[float] = 52.0
"""Milímetros reservados arriba de la hoja patrón para el título, las
instrucciones y los huecos que se rellenan a mano."""

INCERTIDUMBRE_OBJETIVO: Final[float] = 0.001
"""Una milésima. Por encima de esto el instrumento no distingue el error que
se quiere corregir y la calibración deja de valer la pena."""

MARGEN_FACTOR: Final[float] = 0.1
"""Un factor fuera de ±10 % no es una impresora descalibrada: es una medida
mal tomada, o la página impresa con ajuste automático."""

PREFIJO_SELLO: Final[str] = "corregido para"

FRACCION_BANDA: Final[float] = 0.55
"""Dónde cae la banda del medio, como fracción del patrón. No es 0,5 a
propósito: la mitad de 200 son 100, justo donde va una marca rotulada, y la
banda le pasaría por encima. Con 0,55 ninguna longitud de `PATRONES` cae en un
múltiplo de 50."""


def patron_para(disponible: float) -> float:
    """La longitud redonda más larga que cabe. Cuanto más larga, mejor mide."""
    validos = [p for p in PATRONES if p <= disponible]
    if not validos:
        raise ValueError(
            f"en {disponible:.1f} mm no cabe ni el patrón más corto ({PATRONES[0]:.0f} mm). "
            "Usa un formato mayor."
        )
    return max(validos)


# ---------------------------------------------------------------------------
# El perfil
# ---------------------------------------------------------------------------

Medida = Annotated[float, Field(gt=0.0, le=2000.0)]


class Eje(BaseModel):
    """Lo medido en una dirección: lo que se dibujó y lo que se leyó.

    Se guarda la medida cruda y no solo el factor, para poder recalcular el
    día que se discuta un número. Tres lecturas —principio, medio y final—
    son las que delatan un error no uniforme dentro de la hoja; con una sola
    el perfil vale, pero nadie ha comprobado la uniformidad.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    nominal: Medida
    """Milímetros dibujados en la hoja patrón."""
    medidas: list[Medida] = Field(min_length=1, max_length=3)
    """Milímetros leídos. Una por banda."""

    @property
    def medio(self) -> float:
        return sum(self.medidas) / len(self.medidas)

    @property
    def dispersion(self) -> float:
        """Cuánto se separan las bandas entre sí. Es lo que no se compensa."""
        return max(self.medidas) - min(self.medidas)

    @property
    def factor(self) -> float:
        """Por cuánto hay que multiplicar el dibujo para que salga a medida."""
        return self.nominal / self.medio

    @property
    def error_relativo(self) -> float:
        return abs(self.medio - self.nominal) / self.nominal


class PerfilImpresora(BaseModel):
    """Una impresora, un papel, una fecha y dos factores.

    Es dato, no código: vive como JSON en `bench/impresoras/`, igual que el
    kerf, y lo genera la interfaz a partir de una medida humana.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    @model_validator(mode="before")
    @classmethod
    def _descartar_factores_entrantes(cls, datos: object) -> object:
        """`factor_x` y `factor_y` salen en el JSON pero nunca entran.

        Mismo patrón que `Veredicto.apto`: son campos calculados a partir de
        las medidas, se serializan para que quien lea el JSON no tenga que
        dividir, y se descartan al leer. Así la ida y vuelta funciona y no
        existe forma de guardar un perfil cuyo factor contradiga sus medidas.
        """
        if isinstance(datos, dict):
            return {k: v for k, v in datos.items() if k not in ("factor_x", "factor_y")}
        return datos

    nombre: str = Field(min_length=1)
    """Cómo se la reconoce: copistería, modelo, sala."""
    fecha: date
    formato: Formato
    papel: str = Field(min_length=1)
    """Gramaje y tipo. Papel distinto, arrastre distinto."""
    medido_con: Instrumento
    x: Eje
    y: Eje
    notas: str = ""

    @model_validator(mode="after")
    def _factores_plausibles(self) -> PerfilImpresora:
        for nombre, eje in (("x", self.x), ("y", self.y)):
            if abs(eje.factor - 1.0) > MARGEN_FACTOR:
                raise ValueError(
                    f"el factor en {nombre} sale {eje.factor:.3f}, más de un "
                    f"{MARGEN_FACTOR:.0%} fuera de 1. Eso no es una impresora "
                    "descalibrada: revisa si mediste en las unidades correctas y "
                    "si imprimiste al 100 %, sin ajustar a la página."
                )
        return self

    @computed_field  # type: ignore[prop-decorator]
    @property
    def factor_x(self) -> float:
        return self.x.factor

    @computed_field  # type: ignore[prop-decorator]
    @property
    def factor_y(self) -> float:
        return self.y.factor


def sin_calibrar(formato: Formato = Formato.A4) -> PerfilImpresora:
    """Perfil neutro: factores 1. Lo que se usa mientras nadie haya medido."""
    return PerfilImpresora(
        nombre="sin calibrar",
        fecha=date(1970, 1, 1),
        formato=formato,
        papel="desconocido",
        medido_con=Instrumento.REGLA,
        x=Eje(nominal=100.0, medidas=[100.0]),
        y=Eje(nominal=100.0, medidas=[100.0]),
        notas="nadie ha medido esta impresora",
    )


def cargar(ruta: Path | str) -> PerfilImpresora:
    return PerfilImpresora.model_validate_json(Path(ruta).read_text(encoding="utf-8"))


def guardar(perfil: PerfilImpresora, ruta: Path | str) -> Path:
    destino = Path(ruta)
    destino.parent.mkdir(parents=True, exist_ok=True)
    datos = json.loads(perfil.model_dump_json())
    destino.write_text(
        json.dumps(datos, indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8"
    )
    return destino


# ---------------------------------------------------------------------------
# El juez
# ---------------------------------------------------------------------------


def evaluar(perfil: PerfilImpresora) -> Veredicto:
    """¿Sirve esta impresora, y sirve la medida que se ha tomado?

    Mismo patrón que el resto de envolventes del proyecto: una magnitud
    comparada con un límite, y un veredicto con motivo y sugerencia en vez de
    una excepción. Aquí hay tres magnitudes:

    - **Uniformidad.** Si el error no es el mismo en las tres bandas, no hay
      factor que lo arregle. Compensar la media dejaría la pieza mal en los
      extremos y bien en el centro, que es peor que no compensar, porque
      parecería correcta.
    - **Resolución del instrumento.** Si la lectura no distingue el error, el
      factor es ruido con cuatro decimales.
    - **Error frente a incertidumbre.** Si lo que se quiere corregir es más
      pequeño que lo que se sabe medir, aplicar el factor puede empeorar.
    """
    incidencias: list[Incidencia] = []
    resolucion = perfil.medido_con.resolucion

    for nombre, eje in (("x", perfil.x), ("y", perfil.y)):
        if len(eje.medidas) == 1:
            incidencias.append(
                Incidencia(
                    gravedad="aviso",
                    codigo="uniformidad_sin_comprobar",
                    mensaje=(
                        f"en {nombre} solo hay una lectura, así que nadie ha comprobado "
                        "si la impresora deforma igual en toda la hoja"
                    ),
                    sugerencia="mide también en la banda del medio y en la del otro extremo",
                )
            )
        elif eje.dispersion > 2.0 * resolucion:
            incidencias.append(
                Incidencia(
                    gravedad="error",
                    codigo="escala_no_uniforme",
                    mensaje=(
                        f"en {nombre} las bandas difieren {eje.dispersion:.2f} mm, más del "
                        f"doble de lo que resuelve el instrumento ({resolucion:.2f} mm). "
                        "El error no es uniforme dentro de la hoja"
                    ),
                    sugerencia=(
                        "no la compenses: un factor medio dejaría los extremos mal y el "
                        "centro bien. Prueba otro papel, u otra impresora"
                    ),
                )
            )

        incertidumbre = resolucion / eje.nominal
        if incertidumbre > INCERTIDUMBRE_OBJETIVO:
            incidencias.append(
                Incidencia(
                    gravedad="aviso",
                    codigo="instrumento_justo",
                    mensaje=(
                        f"medir {eje.nominal:.0f} mm con {perfil.medido_con.value} deja una "
                        f"incertidumbre del {incertidumbre:.2%}, por encima del "
                        f"{INCERTIDUMBRE_OBJETIVO:.1%} que se busca"
                    ),
                    sugerencia="mide con pie de rey sobre la marca rotulada de 150 mm",
                )
            )
        if 0.0 < eje.error_relativo < incertidumbre:
            incidencias.append(
                Incidencia(
                    gravedad="aviso",
                    codigo="correccion_bajo_ruido",
                    mensaje=(
                        f"en {nombre} el error medido ({eje.error_relativo:.2%}) es menor que "
                        f"la incertidumbre de la lectura ({incertidumbre:.2%}): corregir "
                        "puede empeorar"
                    ),
                    sugerencia="deja el factor en 1 en este eje, o mide con algo más fino",
                )
            )

    return Veredicto(
        incidencias=tuple(incidencias),
        metricas={
            "factor_x": perfil.factor_x,
            "factor_y": perfil.factor_y,
            "dispersion_x": perfil.x.dispersion,
            "dispersion_y": perfil.y.dispersion,
            "resolucion": resolucion,
        },
    )


# ---------------------------------------------------------------------------
# Aplicar la corrección
# ---------------------------------------------------------------------------


def _sello(perfil: PerfilImpresora) -> Texto:
    """Qué corrección lleva la hoja. Sin esto, dos impresiones de la misma
    pieza con perfiles distintos son indistinguibles sobre la mesa."""
    return Texto(
        MARGEN,
        4.0,
        f"{PREFIJO_SELLO} {perfil.nombre} · x {perfil.factor_x:.4f} · "
        f"y {perfil.factor_y:.4f} · {perfil.fecha.isoformat()}",
        2.8,
    )


def lleva_sello(lamina: Lamina) -> bool:
    return any(t.texto.startswith(PREFIJO_SELLO) for t in lamina.textos)


def aplicar(lamina: Lamina, perfil: PerfilImpresora) -> Lamina:
    """Predeforma la lámina para que salga a medida de esa impresora.

    Se escala respecto al **centro de la página**, no respecto a una esquina.
    La impresora escala respecto a un origen que no conocemos, así que la
    posición del dibujo puede quedar desplazada medio milímetro; la longitud,
    que es lo que se corta, sale bien en cualquier caso.

    El tamaño del texto no se toca: un rótulo no se corta, y escalarlo
    cambiaría su ancho y podría sacarlo de la hoja. Los taladros sí se
    escalan, con la media de los dos factores: con factores distintos un
    círculo sería una elipse, y la diferencia en un agujero de 8 mm son cuatro
    centésimas, muy por debajo de la broca.

    El tamaño de página no se escala. El papel sigue siendo A4.

    Un perfil neutro devuelve la lámina tal cual, sin sello: no se ha
    corregido nada, y el PDF tiene que salir byte a byte como el de siempre.
    """
    if perfil.factor_x == 1.0 and perfil.factor_y == 1.0:
        return lamina
    if lleva_sello(lamina):
        raise ValueError(
            "esta lámina ya lleva una corrección aplicada. Aplicar dos veces "
            "duplicaría el factor. Vuelve a maquetar desde la pieza."
        )

    fx, fy = perfil.factor_x, perfil.factor_y
    cx, cy = lamina.ancho / 2.0, lamina.alto / 2.0
    medio = (fx + fy) / 2.0

    def coord(v: float, centro: float, factor: float) -> float:
        # El factor 1 devuelve el valor intacto en vez de pasarlo por la
        # cuenta: `c + (v - c) * 1.0` no da exactamente `v` en coma flotante,
        # y un perfil neutro tiene que dejar el PDF byte a byte como estaba.
        return v if factor == 1.0 else centro + (v - centro) * factor

    def punto(p: tuple[float, float]) -> tuple[float, float]:
        return (coord(p[0], cx, fx), coord(p[1], cy, fy))

    return Lamina(
        ancho=lamina.ancho,
        alto=lamina.alto,
        trazos=tuple(
            Trazo(t.tipo, tuple(punto(p) for p in t.puntos), t.cerrado) for t in lamina.trazos
        ),
        circulos=tuple(Circulo(c.tipo, punto(c.centro), c.radio * medio) for c in lamina.circulos),
        textos=(
            *(
                Texto(*punto((t.x, t.y)), t.texto, t.tamano, t.negrita, t.anclaje)
                for t in lamina.textos
            ),
            _sello(perfil),
        ),
        indice=lamina.indice,
    )


# ---------------------------------------------------------------------------
# La hoja patrón
# ---------------------------------------------------------------------------


def medidas_del_patron(formato: Formato) -> tuple[float, float]:
    """Ancho y alto del rectángulo patrón que cabe en ese formato."""
    ancho_pagina, alto_pagina = formato.medidas
    return (
        patron_para(ancho_pagina - 2 * MARGEN),
        patron_para(alto_pagina - 2 * MARGEN - ALTO_TITULO),
    )


def _regla(
    x0: float,
    y0: float,
    largo: float,
    *,
    vertical: bool,
    desde: float,
) -> tuple[list[Trazo], list[Texto]]:
    """Marcas de 10 en 10 sobre un borde, rotuladas cada 50.

    Empieza en `desde` y no en cero porque el primer tramo lo cubre el cuadro
    de calibración, que ya trae sus marcas: repetirlas sería dibujar dos
    líneas en el mismo sitio.
    """
    trazos: list[Trazo] = []
    textos: list[Texto] = []
    d = desde
    while d <= largo + 1e-9:
        redonda = abs(d % 50.0) < 1e-9
        brazo = 8.0 if redonda else 4.0
        if vertical:
            trazos.append(Trazo("marca", ((x0, y0 + d), (x0 + brazo, y0 + d))))
            if redonda:
                textos.append(Texto(x0 - 9.0, y0 + d - 1.0, f"{d:.0f}", 2.8, True))
        else:
            trazos.append(Trazo("marca", ((x0 + d, y0), (x0 + d, y0 + brazo))))
            if redonda:
                textos.append(Texto(x0 + d, y0 - 5.0, f"{d:.0f}", 2.8, True, "centro"))
        d += 10.0
    return trazos, textos


def _cruz(x: float, y: float, brazo: float = 4.0) -> list[Trazo]:
    return [
        Trazo("marca", ((x - brazo, y), (x + brazo, y))),
        Trazo("marca", ((x, y - brazo), (x, y + brazo))),
    ]


def hoja_patron(formato: Formato = Formato.A4) -> Lamina:
    """La hoja que se imprime, se mide y se convierte en `PerfilImpresora`.

    Lleva un rectángulo de medidas redondas con el cuadro de 100 mm encajado
    en su esquina —el mismo cuadro de todas las plantillas, solo que aquí se
    prolonga hasta el patrón largo— y tres bandas por eje: los dos bordes y el
    medio. Si las tres no coinciden, la impresora deforma de forma no
    uniforme y no hay factor que la salve.
    """
    ancho_pagina, alto_pagina = formato.medidas
    ancho, alto = medidas_del_patron(formato)

    x0 = (ancho_pagina - ancho) / 2.0
    y0 = MARGEN + 6.0

    trazos: list[Trazo] = []
    textos: list[Texto] = []
    circulos: list[Circulo] = []

    # -- rectángulo patrón y sus bandas -------------------------------------
    trazos.append(
        Trazo(
            "corte",
            ((x0, y0), (x0 + ancho, y0), (x0 + ancho, y0 + alto), (x0, y0 + alto)),
            cerrado=True,
        )
    )
    for x, y in ((x0, y0), (x0 + ancho, y0), (x0, y0 + alto), (x0 + ancho, y0 + alto)):
        trazos += _cruz(x, y)

    saliente = 7.0
    ym = y0 + alto * FRACCION_BANDA
    xm = x0 + ancho * FRACCION_BANDA
    trazos.append(Trazo("marca", ((x0 - saliente, ym), (x0, ym))))
    trazos.append(Trazo("marca", ((x0 + ancho, ym), (x0 + ancho + saliente, ym))))
    trazos.append(Trazo("marca", ((xm, y0 - saliente), (xm, y0))))
    trazos.append(Trazo("marca", ((xm, y0 + alto), (xm, y0 + alto + saliente))))

    # Las dos medidas juntas y sobre el rectángulo, centradas. El alto no se
    # rotula junto a su eje porque esta capa no gira texto, y el hueco de la
    # izquierda se queda sin sitio en cuanto el patrón ocupa casi toda la hoja.
    medida = f"{ancho:.0f} × {alto:.0f} mm"
    textos.append(Texto(x0 + ancho / 2.0, y0 + alto + 10.0, medida, 4.5, True, "centro"))

    # -- el cuadro de siempre, encajado en la esquina -----------------------
    cuadro = cuadro_de_calibracion(x0, y0)
    trazos += cuadro.trazos
    textos += cuadro.textos

    reglas_x, rotulos_x = _regla(x0, y0, ancho, vertical=False, desde=LADO_CALIBRACION)
    reglas_y, rotulos_y = _regla(x0, y0, alto, vertical=True, desde=LADO_CALIBRACION)
    trazos += reglas_x + reglas_y
    textos += rotulos_x + rotulos_y

    # -- título e instrucciones ---------------------------------------------
    y = alto_pagina - MARGEN - 5.0
    textos.append(Texto(MARGEN, y, "HOJA PATRÓN DE CALIBRACIÓN", 5.5, True))
    y -= 7.0
    textos.append(Texto(MARGEN, y, "IMPRIMIR AL 100 %, SIN AJUSTAR A LA PÁGINA", 4.0, True))
    y -= 6.5
    for linea in (
        f"1. Mide el ancho ({ancho:.0f} mm) en tres sitios: por el borde de arriba, por",
        "   las marcas que sobresalen en el medio, y por el borde de abajo.",
        f"2. Mide el alto ({alto:.0f} mm) igual: izquierda, marcas del medio y derecha.",
        "3. Con pie de rey, mide hasta la marca de 150 mm en vez del borde.",
        "4. Introduce las seis medidas en la aplicación, vuelve a imprimir y",
        "   comprueba que el cuadro de 100 mm mide 100 mm.",
    ):
        textos.append(Texto(MARGEN, y, linea, 3.2))
        y -= 4.6
    y -= 2.0
    textos.append(Texto(MARGEN, y, "impresora: ______________________", 3.2))
    textos.append(Texto(MARGEN + 70.0, y, "papel: ______________", 3.2))
    textos.append(Texto(MARGEN + 130.0, y, "fecha: ____________", 3.2))

    return Lamina(
        ancho=ancho_pagina,
        alto=alto_pagina,
        trazos=tuple(trazos),
        circulos=tuple(circulos),
        textos=tuple(textos),
    )


__all__ = [
    "ALTO_TITULO",
    "INCERTIDUMBRE_OBJETIVO",
    "MARGEN_FACTOR",
    "PATRONES",
    "PREFIJO_SELLO",
    "Eje",
    "Instrumento",
    "Medida",
    "PerfilImpresora",
    "aplicar",
    "cargar",
    "evaluar",
    "guardar",
    "hoja_patron",
    "lleva_sello",
    "medidas_del_patron",
    "patron_para",
    "sin_calibrar",
]
