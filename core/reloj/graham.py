"""C12b · el escape Graham montado: geometria y marcha.

`core/reloj/escape.py` dimensiona cada pieza por separado. Lo que ninguna
comprobacion de pieza suelta ve es lo que pasa al **montarlas y moverlas**:
si la paleta cabe entre dos dientes, si el diente apoya en su punta o en su
cara, si la rueda retrocede durante el reposo, si el diente que acaba de
pasar deja sitio a la otra paleta. Es el mismo problema que el hueco al poste
del escribiente, y se resuelve igual: montando y barriendo.

**Como se mueve.** Cinematica pura, sin masas ni tiempo (regla 1): el ancora
se gira en pasos pequenos de `theta`, que es el angulo del pendulo, y en cada
paso la rueda avanza lo que puede hasta tocar. Si el ancora no cabe donde la
lleva el pendulo, la rueda retrocede lo justo; si ni retrocediendo cabe, el
escape esta **atascado**. Si nada para la rueda, esta **desbocado**.

**Convenios**, vista desde la esfera:

- La rueda tiene el centro en el origen y gira en sentido **horario**;
  `phi > 0` es cuanto ha girado.
- El eje del ancora esta encima, en `(0, entre_centros)`; `theta > 0` es giro
  **antihorario** del ancora.
- La paleta de **entrada** es la de la izquierda: el diente que llega va
  **hacia** el eje del ancora, y por eso bloquea con la cara de fuera. La de
  **salida** es la de la derecha: el diente se **aleja** del eje, y bloquea
  con la cara de dentro.

**La paleta.** Bloqueo equidistante, como el de Graham: las dos caras de
reposo son arcos de radio `brazo` con centro en el eje del ancora. La cara de
caida esta `ancho_trabajo` mas alla, hacia el eje en la entrada y alejandose
en la salida. El plano de impulso une las dos esquinas, y la de caida entra
en la rueda `impulso` grados mas que la de reposo: es la que el diente empuja
al salir.

**Lo que no ve.** Rozamiento, energia y holguras de los ejes. Dice si la
geometria funciona, no si el pendulo recibe bastante: eso lo mide el banco R2.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, replace
from typing import Final, Literal

import numpy as np
import numpy.typing as npt
from shapely import STRtree, affinity, prepare, transform
from shapely.geometry import LineString, Point, Polygon
from shapely.ops import nearest_points, unary_union

from core.reloj.escape import angulo_de_centro, brazo_paleta, distancia_entre_centros
from core.units import Metros, Radianes, grados, mm
from core.verdict import Incidencia, Veredicto

Lado = Literal["entrada", "salida"]

PASO_THETA: Final[Radianes] = grados(0.05)
"""Paso del pendulo al barrer. Con brazo de 45 mm son 0,04 mm de recorrido de
paleta, muy por debajo de cualquier cota de las piezas."""

PASO_RUEDA: Final[Radianes] = grados(0.1)
"""Paso con que la rueda avanza buscando tope. A radio 45 son 0,08 mm: no hay
diente ni paleta tan finos como para que el paso los atraviese sin tocarlos."""

RETROCESO_TOLERADO: Final[Radianes] = grados(0.02)
"""Por debajo de esto es ruido de la discretizacion de los arcos. Un diente en
cuna retrocede unos 0,2 grados por golpe: diez veces mas."""

CAIDA_MINIMA: Final[Radianes] = grados(0.5)
"""Holgura que el diente tiene que caer libre, ademas de la punta. Por debajo,
cualquier diente con error de paso se queda sin sitio."""


# ---------------------------------------------------------------------------
# Las piezas
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class RuedaGraham:
    """La rueda de escape, con su perfil de diente.

    `socavado` es lo que la cara de ataque se aparta del radio **medido en la
    punta**. Positivo es el socavado de verdad: el pie de la cara queda
    **detras** de la punta y solo la punta toca la paleta. Negativo es una
    cuna, con el pie por delante.

    `errores`, si los hay, son el error de sierra de cada diente: cuanto se
    desplaza su punta en angulo y cuanto cambia su radio.
    """

    dientes: int
    radio_punta: Metros
    radio_fondo: Metros
    espesor_punta: Radianes
    socavado: Radianes
    dorso: Radianes
    errores: tuple[tuple[Radianes, Metros], ...] = ()

    @property
    def paso(self) -> Radianes:
        return Radianes(2.0 * math.pi / self.dientes)

    @property
    def angulo_cara(self) -> Radianes:
        """Angulo de centro del pie de la cara, con signo: + es detras."""
        a = angulo_de_centro(self.radio_punta, self.radio_fondo, abs(self.socavado))
        return Radianes(math.copysign(a, self.socavado))

    @property
    def angulo_dorso(self) -> Radianes:
        return Radianes(angulo_de_centro(self.radio_punta, self.radio_fondo, self.dorso))

    def con_error_de_sierra(self, tolerancia: Metros, semilla: int) -> RuedaGraham:
        """La misma rueda cortada a mano: cada diente con un error al azar de
        hasta `tolerancia` en la posicion de la punta y en su radio."""
        azar = np.random.default_rng(semilla)
        errores = tuple(
            (
                Radianes(float(azar.uniform(-tolerancia, tolerancia)) / self.radio_punta),
                Metros(float(azar.uniform(-tolerancia, tolerancia))),
            )
            for _ in range(self.dientes)
        )
        return replace(self, errores=errores)

    def escalada(self, k: float) -> RuedaGraham:
        return replace(
            self,
            radio_punta=Metros(self.radio_punta * k),
            radio_fondo=Metros(self.radio_fondo * k),
            errores=tuple((a, Metros(r * k)) for a, r in self.errores),
        )


@dataclass(frozen=True)
class AncoraGraham:
    """El ancora: dos paletas postizas y el yugo que las une.

    La planta -entre centros y brazo- no se elige: sale de la rueda por la
    construccion de Graham, con el eje en el cruce de las dos tangentes.
    """

    dientes: int
    radio_punta: Metros
    reposo: Radianes
    impulso: Radianes
    ancho_trabajo: Metros
    largo_dedo: Metros
    ancho_cuerpo: Metros
    largo_paleta: Metros
    yugo: Radianes
    brazo_ancho: Metros
    cubo: Metros
    eje: Metros
    pierna_hasta: Metros
    """Radio, desde el centro de la rueda, donde acaba la pierna del yugo."""

    @property
    def entre_centros(self) -> Metros:
        return Metros(distancia_entre_centros(self.radio_punta, self.dientes))

    @property
    def brazo(self) -> Metros:
        return Metros(brazo_paleta(self.radio_punta, self.dientes))

    @property
    def eje_ancora(self) -> tuple[float, float]:
        return (0.0, float(self.entre_centros))

    @property
    def desfase(self) -> Radianes:
        """Profundidad de la esquina de reposo con el pendulo vertical.

        Simetrico: cada paleta suelta cuando la otra ya ha entrado lo justo
        para recoger el diente con `reposo` de profundidad.
        """
        return Radianes((self.reposo - self.impulso) / 2.0)

    def escalada(self, k: float) -> AncoraGraham:
        def m(v: float) -> Metros:
            return Metros(v * k)

        return replace(
            self,
            radio_punta=m(self.radio_punta),
            ancho_trabajo=m(self.ancho_trabajo),
            largo_dedo=m(self.largo_dedo),
            ancho_cuerpo=m(self.ancho_cuerpo),
            largo_paleta=m(self.largo_paleta),
            brazo_ancho=m(self.brazo_ancho),
            cubo=m(self.cubo),
            eje=m(self.eje),
            pierna_hasta=m(self.pierna_hasta),
        )


@dataclass(frozen=True)
class Nariz:
    """Lo que define una paleta: sus dos esquinas y los dos radios desde el
    eje del ancora, con el pendulo vertical."""

    reposo: tuple[float, float]
    caida: tuple[float, float]
    radio_reposo: Metros
    radio_caida: Metros


# ---------------------------------------------------------------------------
# Geometria
# ---------------------------------------------------------------------------


def _polar(centro: tuple[float, float], radio: float, angulo: float) -> tuple[float, float]:
    return (centro[0] + radio * math.cos(angulo), centro[1] + radio * math.sin(angulo))


def dientes(rueda: RuedaGraham) -> list[tuple[float, Polygon]]:
    """Cada diente como poligono, con el angulo de su punta delantera.

    Bajan medio milimetro por debajo del fondo para que, unidos al disco,
    no quede una rendija.
    """
    o = (0.0, 0.0)
    fondo = rueda.radio_fondo
    hundido = fondo - mm(0.5)
    salida = []
    for k in range(rueda.dientes):
        da, dr = rueda.errores[k] if rueda.errores else (0.0, 0.0)
        a = math.pi / 2 - k * rueda.paso + da
        punta = rueda.radio_punta + dr
        pie_cara = a + rueda.angulo_cara
        pie_dorso = a + rueda.espesor_punta + rueda.angulo_dorso
        contorno = [
            _polar(o, hundido, pie_cara),
            _polar(o, fondo, pie_cara),
            _polar(o, punta, a),
            _polar(o, punta, a + rueda.espesor_punta),
            _polar(o, fondo, pie_dorso),
            _polar(o, hundido, pie_dorso),
        ]
        salida.append((a, Polygon(contorno).buffer(0)))
    return salida


def contorno_rueda(rueda: RuedaGraham, resolucion: int = 512) -> Polygon:
    """La rueda maciza: disco de fondo mas dientes. Es lo que se corta en el
    banco; los radios de aligerado los pone la pieza definitiva."""
    disco = Point(0.0, 0.0).buffer(rueda.radio_fondo + mm(0.01), resolucion // 4)
    return unary_union([disco] + [g for _, g in dientes(rueda)])


def nariz(ancora: AncoraGraham, lado: Lado) -> Nariz:
    p = ancora.eje_ancora
    psi = -3 * math.pi / 4 if lado == "entrada" else -math.pi / 4
    hacia_rueda = 1.0 if lado == "entrada" else -1.0
    brazo = ancora.brazo
    radio_caida = (
        brazo - ancora.ancho_trabajo if lado == "entrada" else brazo + ancora.ancho_trabajo
    )
    a_reposo = psi + hacia_rueda * ancora.desfase
    a_caida = a_reposo + hacia_rueda * ancora.impulso
    return Nariz(
        reposo=_polar(p, brazo, a_reposo),
        caida=_polar(p, radio_caida, a_caida),
        radio_reposo=brazo,
        radio_caida=Metros(radio_caida),
    )


def paleta(ancora: AncoraGraham, lado: Lado) -> Polygon:
    """La paleta con el pendulo vertical.

    Un dedo radial a la rueda: la nariz, de `ancho_trabajo`, entra entre los
    dientes; a `largo_dedo` de la nariz se ensancha a `ancho_cuerpo` para el
    tornillo, ya fuera del alcance de los dientes.
    """
    p = ancora.eje_ancora
    n = nariz(ancora, lado)
    hacia_rueda = 1.0 if lado == "entrada" else -1.0
    a_reposo = math.atan2(n.reposo[1] - p[1], n.reposo[0] - p[0])
    a_caida = math.atan2(n.caida[1] - p[1], n.caida[0] - p[0])
    e = ancora.largo_dedo / ancora.brazo
    arco_reposo = [
        _polar(p, n.radio_reposo, a_reposo - hacia_rueda * e * t) for t in np.linspace(0, 1, 48)
    ]
    arco_caida = [
        _polar(p, n.radio_caida, a_caida - hacia_rueda * (e + ancora.impulso) * t)
        for t in np.linspace(0, 1, 48)
    ]
    radial = np.array(n.reposo) / math.hypot(*n.reposo)
    lateral = np.array([-radial[1], radial[0]])
    extremo_reposo, extremo_caida = np.array(arco_reposo[-1]), np.array(arco_caida[-1])
    if float(np.dot(lateral, extremo_reposo - extremo_caida)) < 0:
        lateral = -lateral
    medio = (extremo_reposo + extremo_caida) / 2
    h = ancora.ancho_cuerpo / 2
    largo = ancora.largo_paleta - ancora.largo_dedo
    b1, b2 = medio + lateral * h, medio - lateral * h
    cuerpo = [tuple(b1), tuple(b1 + radial * largo), tuple(b2 + radial * largo), tuple(b2)]
    return Polygon(arco_reposo + cuerpo + arco_caida[::-1]).buffer(0)


def centro_ranura(ancora: AncoraGraham, lado: Lado) -> tuple[float, float]:
    """Donde va el tornillo de la paleta: en medio del cuerpo, que es el centro
    de la ranura de ajuste del reposo."""
    n = nariz(ancora, lado)
    radial = np.array(n.reposo) / math.hypot(*n.reposo)
    medio = (np.array(n.reposo) + np.array(n.caida)) / 2
    distancia = ancora.largo_dedo + (ancora.largo_paleta - ancora.largo_dedo) / 2
    c = medio + radial * distancia
    return (float(c[0]), float(c[1]))


def yugo(ancora: AncoraGraham) -> Polygon:
    """Cubo, dos brazos que bajan `yugo` bajo la horizontal y dos piernas que
    siguen el radio de la rueda. Nada del yugo pasa por encima de los dientes:
    la pierna acaba a `pierna_hasta` del centro de la rueda."""
    p = np.array(ancora.eje_ancora)
    partes = [Point(*p).buffer(ancora.cubo / 2, 96)]
    for lado, sx in (("entrada", -1.0), ("salida", 1.0)):
        n = nariz(ancora, lado)  # type: ignore[arg-type]
        u = np.array(n.reposo) / math.hypot(*n.reposo)
        d = np.array([sx * math.cos(ancora.yugo), -math.sin(ancora.yugo)])
        k, _ = np.linalg.solve(np.array([[d[0], -u[0]], [d[1], -u[1]]]), -p)
        esquina = p + k * d
        pie = u * ancora.pierna_hasta
        partes.append(
            LineString([tuple(p), tuple(esquina), tuple(pie)]).buffer(
                ancora.brazo_ancho / 2, cap_style=2, join_style=1
            )
        )
    cuerpo = unary_union(partes).buffer(mm(2.0)).buffer(-mm(2.0))
    return cuerpo.difference(Point(*p).buffer(ancora.eje / 2, 64))


# ---------------------------------------------------------------------------
# La marcha
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Marcha:
    """El barrido: angulo del pendulo y giro de la rueda en cada paso."""

    theta: npt.NDArray[np.float64]
    phi: npt.NDArray[np.float64]
    retroceso: npt.NDArray[np.float64]
    """Lo que la rueda ha tenido que retroceder en cada paso."""
    atasco: str | None = None
    desboque: str | None = None


class _Montaje:
    """Rueda y paletas listas para preguntar si se tocan.

    Se pregunta en el marco de la **rueda**: en vez de girar treinta dientes
    se giran dos paletas, y los dientes quedan quietos, preparados y en un
    arbol espacial. Es lo que hace que la vuelta entera tarde segundos.
    """

    def __init__(self, rueda: RuedaGraham, ancora: AncoraGraham) -> None:
        self.rueda, self.ancora = rueda, ancora
        self.dientes = [g for _, g in dientes(rueda)]
        for g in self.dientes:
            prepare(g)
        self.arbol = STRtree(self.dientes)
        self.p = np.array(ancora.eje_ancora)
        self.paletas = [paleta(ancora, "entrada"), paleta(ancora, "salida")]

    def paletas_en(self, theta: float) -> list[Polygon]:
        """Las paletas con el pendulo a `theta`, en el marco del mundo."""
        c, s_ = math.cos(theta), math.sin(theta)
        giro = np.array([[c, -s_], [s_, c]])
        p = self.p

        def mover(xy: npt.NDArray[np.float64]) -> npt.NDArray[np.float64]:
            return np.asarray((xy - p) @ giro.T + p, dtype=np.float64)

        return [transform(g, mover) for g in self.paletas]

    def libre(self, phi: float, paletas: list[Polygon]) -> bool:
        # Girar la rueda -phi es lo mismo que girar las paletas +phi.
        c, s_ = math.cos(phi), math.sin(phi)
        giro = np.array([[c, -s_], [s_, c]])
        for pal in paletas:
            en_rueda = transform(pal, lambda xy: np.asarray(xy @ giro.T, dtype=np.float64))
            for i in self.arbol.query(en_rueda):
                if self.dientes[int(i)].intersects(en_rueda):
                    return False
        return True


def _avanzar(m: _Montaje, phi: float, paletas: list[Polygon]) -> tuple[float, bool]:
    """Hasta donde gira la rueda antes de tocar. Falso si nada la para."""
    if not m.libre(phi + 1e-7, paletas):
        return phi, True
    tope = phi + 1.6 * m.rueda.paso
    a = phi
    while a < tope:
        b = a + PASO_RUEDA
        if not m.libre(b, paletas):
            for _ in range(24):
                medio = (a + b) / 2
                if m.libre(medio, paletas):
                    a = medio
                else:
                    b = medio
            return a, True
        a = b
    return a, False


def _retroceder(m: _Montaje, phi: float, paletas: list[Polygon]) -> float | None:
    """Lo minimo que la rueda tiene que volver atras para que el ancora quepa."""
    paso = grados(0.002)
    b = phi
    while not m.libre(b, paletas):
        b -= paso
        if phi - b > grados(3.0):
            return None
    # entre b (libre) y b + paso (tocando): lo justo, no un paso entero
    a = min(phi, b + paso)
    for _ in range(20):
        medio = (a + b) / 2
        if m.libre(medio, paletas):
            b = medio
        else:
            a = medio
    return b


def marcha(
    rueda: RuedaGraham,
    ancora: AncoraGraham,
    amplitud: Radianes,
    oscilaciones: int | None = None,
    paso: Radianes = PASO_THETA,
) -> Marcha:
    """Barre el pendulo de +amplitud a -amplitud y vuelta, `oscilaciones` veces.

    Por defecto, una vuelta entera de la rueda y una oscilacion mas: es lo que
    hace falta para que cada diente pase por las dos paletas.
    """
    n = rueda.dientes + 1 if oscilaciones is None else oscilaciones
    bajada = np.arange(amplitud, -amplitud - 1e-12, -paso)
    tramos = [bajada]
    for i in range(2 * n - 1):
        tramos.append((bajada if i % 2 else bajada[::-1])[1:])
    thetas = np.concatenate(tramos)

    m = _Montaje(rueda, ancora)
    paletas = m.paletas_en(float(thetas[0]))
    phi = 0.0
    for _ in range(400):
        if m.libre(phi, paletas):
            break
        phi += rueda.paso / 400
    phi, _ = _avanzar(m, phi, paletas)

    th_out: list[float] = []
    ph_out: list[float] = []
    re_out: list[float] = []
    for th in thetas:
        paletas = m.paletas_en(float(th))
        retroceso = 0.0
        if not m.libre(phi, paletas):
            atras = _retroceder(m, phi, paletas)
            if atras is None:
                return Marcha(
                    np.array(th_out),
                    np.array(ph_out),
                    np.array(re_out),
                    atasco=f"con el pendulo a {math.degrees(th):+.2f} grados la paleta no cabe "
                    "ni retrocediendo la rueda tres grados",
                )
            retroceso = phi - atras
            phi = atras
        phi, apoyada = _avanzar(m, phi, paletas)
        if not apoyada:
            return Marcha(
                np.array(th_out),
                np.array(ph_out),
                np.array(re_out),
                desboque=f"con el pendulo a {math.degrees(th):+.2f} grados ninguna paleta "
                "para la rueda",
            )
        th_out.append(float(th))
        ph_out.append(phi)
        re_out.append(retroceso)
    return Marcha(np.array(th_out), np.array(ph_out), np.array(re_out))


def contacto_en_reposo(rueda: RuedaGraham, ancora: AncoraGraham, amplitud: Radianes) -> Metros:
    """Radio, desde el centro de la rueda, del punto del diente que apoya en la
    paleta con el pendulo en el extremo. Si es menor que el de punta, el diente
    apoya en su cara y no en su punta."""
    m = marcha(rueda, ancora, amplitud, oscilaciones=1)
    paletas = unary_union(_Montaje(rueda, ancora).paletas_en(float(m.theta[0])))
    rueda_girada = affinity.rotate(
        contorno_rueda(rueda), -float(m.phi[0]), origin=(0, 0), use_radians=True
    )
    en_rueda, _ = nearest_points(rueda_girada, paletas)
    return Metros(math.hypot(en_rueda.x, en_rueda.y))


# ---------------------------------------------------------------------------
# La envolvente
# ---------------------------------------------------------------------------


def juzgar(
    rueda: RuedaGraham,
    ancora: AncoraGraham,
    amplitud: Radianes,
    oscilaciones: int | None = None,
) -> Veredicto:
    """El veredicto del escape montado. Por defecto, la vuelta entera."""
    m = marcha(rueda, ancora, amplitud, oscilaciones)
    incidencias: list[Incidencia] = []
    if m.atasco:
        incidencias.append(
            Incidencia(
                gravedad="error",
                codigo="escape_atascado",
                mensaje=m.atasco,
                sugerencia="Estrechar la paleta o tumbar menos el dorso del diente: el diente "
                "que acaba de pasar no deja sitio a la otra paleta.",
            )
        )
    if m.desboque:
        incidencias.append(
            Incidencia(
                gravedad="error",
                codigo="escape_desbocado",
                mensaje=m.desboque,
                sugerencia="Meter mas la paleta (mas reposo) o comprobar que la esquina de "
                "caida entra mas en la rueda que la de reposo.",
            )
        )
    metricas: dict[str, float] = {}
    if len(m.phi) > 2:
        saltos = np.diff(m.phi)
        caidas = saltos[saltos > grados(0.3)]
        suave = saltos[(saltos > 1e-6) & (saltos <= grados(0.3))]
        golpes = max(1, len(caidas))
        metricas = {
            "vuelta": float(m.phi[-1] - m.phi[0]),
            "avance_por_golpe": float((m.phi[-1] - m.phi[0]) / golpes),
            "caida_min": float(caidas.min()) if len(caidas) else 0.0,
            "caida_max": float(caidas.max()) if len(caidas) else 0.0,
            "impulso_rueda": float(suave.sum() / golpes),
            "retroceso_por_golpe": float(m.retroceso.sum() / golpes),
        }
        if metricas["retroceso_por_golpe"] > RETROCESO_TOLERADO:
            incidencias.append(
                Incidencia(
                    gravedad="error",
                    codigo="retroceso_en_reposo",
                    mensaje="la rueda retrocede "
                    f"{math.degrees(metricas['retroceso_por_golpe']):.2f} grados por golpe "
                    "mientras el diente esta en reposo: deja de ser un Graham",
                    sugerencia="Socavar la cara de ataque: el pie tiene que quedar detras de la "
                    "punta para que la paleta apoye solo en ella.",
                )
            )
        if not m.atasco and len(caidas) and caidas.min() - rueda.espesor_punta < CAIDA_MINIMA:
            incidencias.append(
                Incidencia(
                    gravedad="aviso",
                    codigo="caida_escasa",
                    mensaje=f"la caida libre minima es de "
                    f"{math.degrees(caidas.min() - rueda.espesor_punta):.2f} grados, ademas "
                    "de la punta",
                    sugerencia="Estrechar la paleta: cualquier diente con error de paso se "
                    "queda sin sitio.",
                )
            )
    return Veredicto(incidencias=tuple(incidencias), metricas=metricas)


__all__ = [
    "AncoraGraham",
    "Lado",
    "Marcha",
    "Nariz",
    "RuedaGraham",
    "centro_ranura",
    "contacto_en_reposo",
    "contorno_rueda",
    "dientes",
    "juzgar",
    "marcha",
    "nariz",
    "paleta",
    "yugo",
]
