"""El regulador del reloj en movimiento: péndulo, áncora y rueda de escape.

**Aquí el tiempo es de verdad**, y es el único sitio del repositorio fuera de
`core/reloj/pendulo.py` donde lo es. La excepción a la regla 1 está declarada
en `docs/reloj/expediente.md` («La regla del tiempo») y la defiende
`tests/reloj/test_arquitectura_reloj.py`: `core/` sigue sin un solo `dt`, y
lo que este módulo integra en el tiempo lo toma de funciones de θ del núcleo
(`core/reloj/contacto.py`, C11 y `core/solido.py`).

Dos grados de libertad: el péndulo con el áncora, `θ` (antihorario), y la
rueda, `φ` (horario). Dos modos, y el paso de uno a otro por eventos de
`solve_ivp`, nunca a ojo:

**En contacto** con una paleta: `φ = g(θ) + k·paso`, la ligadura que da la
tabla de contacto. Cubre el bloqueo —`g` plana: la rueda quieta y la normal
por el eje del áncora, así que solo frena el rozamiento— y el impulso —`g`
inclinada—, y también el retroceso: si el péndulo no llega al final del
impulso, `θ'` cambia de signo y la paleta empuja la rueda hacia atrás contra
su par. Con la fuerza normal `N` y el rozamiento de Coulomb en la tangente:

    J·φ'' = M_neto - N·a_r          (rueda, horario)
    I·θ'' = Γ(θ) - c·θ' + N·a_a     (péndulo y áncora, antihorario)
    φ''   = g'·θ'' + g''·θ'²         (ligadura)

con `a_r = (r × (n - mu·s·t))_z` y `a_a = -((r - A) × (n - mu·s·t))_z`, y `s` el
signo suavizado del deslizamiento. Despejado, la inercia equivalente es
`I + J·g'·a_a/a_r`, que sin rozamiento es la de libro `I + J·g'²`. El
contacto se pierde si `N` cae a cero o si el diente pasa la esquina.

**Libre**, la caída: la rueda gira con su par y el péndulo oscila solo. El
evento es que la holgura a una de las dos paletas llegue a cero; ahí hay un
choque con restitución `e` en la normal y rozamiento de Coulomb en la
tangente. Si tras el choque la velocidad de separación es pequeña, el diente
se queda: contacto.

**El péndulo**: C11 con el áncora y la horquilla, gravedad no lineal
(`sin θ`) y amortiguamiento viscoso del Q de R1. **La rueda**: su inercia
desde su polígono, el par motor constante y el rozamiento de su eje, que
carga con la pesa y la rueda.

**Supuesto, no decisión**: el eje del áncora y la flexión del péndulo son
coaxiales (ver `bench/reloj/escape_dinamica.json`). La altura del eje del
áncora es cota del paso 6.
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Any, Final, Literal

import numpy as np
import numpy.typing as npt
from scipy.integrate import solve_ivp
from scipy.interpolate import PchipInterpolator
from scipy.optimize import brentq
from shapely.geometry import Polygon

from compile.escape_r2 import geometria
from core.reloj.contacto import TablaDeContacto, tabla_de_contacto
from core.reloj.graham import AncoraGraham, RuedaGraham, contorno_rueda, paleta, yugo
from core.reloj.pendulo import SEGUNDOS_POR_DIA, G, Pendulo
from core.solido import DENSIDADES
from core.units import Kilogramos, Metros, Radianes, grados

RAIZ = Path(__file__).resolve().parent.parent
CONTRATOS = RAIZ / "docs" / "reloj" / "contratos.json"
BANCO_ESCAPE = RAIZ / "bench" / "reloj" / "escape_dinamica.json"
BANCO_PENDULO = RAIZ / "bench" / "reloj" / "pendulo.json"

Arreglo = npt.NDArray[np.float64]
Lado = Literal["entrada", "salida"]
OTRA: Final[dict[str, Lado]] = {"entrada": "salida", "salida": "entrada"}

AMPLITUD_DE_TABLA: Final[float] = grados(8.8)
"""Hasta dónde se tabula el contacto: justo por debajo del límite de la
geometría R2 (`amplitud_limite`: 8,84°, donde el cuerpo de la paleta llega a
los dientes y `graham.juzgar` da el escape por atascado). Más allá la
simulación se para y lo dice."""

PASO_DE_TABLA: Final[float] = grados(0.01)

V_DESLIZAMIENTO: Final[float] = 1.0e-5
"""m/s. Por debajo, el rozamiento de Coulomb se suaviza (tanh): sin esto el
signo salta y el integrador se atasca en el bloqueo, donde la rueda está
quieta y la paleta apenas se mueve en los extremos."""

W_EJE: Final[float] = 1.0e-3
"""rad/s. Lo mismo para el rozamiento del eje de la rueda."""

SEPARACION_MINIMA: Final[float] = 2.0e-4
"""m/s. Tras un choque, una separación más lenta que esto es quedarse: los
rebotes que vendrían después se acortan sin fin (Zenón) y no cambian nada."""

HOLGURA_DE_EVENTO: Final[float] = 1.0e-9
"""rad. Lo que el diente puede entrar en la paleta antes de que cuente como
choque: nada, pero distinto de cero."""

HORQUILLA: Final[dict[str, float]] = {"largo": 0.150, "ancho": 0.010, "espesor": 0.002}
"""PROVISIONAL (ver el JSON del banco): pletina de latón del eje del áncora a
la varilla. No hay contrato de horquilla todavía."""


# ---------------------------------------------------------------------------
# Lo que se lee: contratos y banco
# ---------------------------------------------------------------------------


def contratos_reloj(ruta: Path = CONTRATOS) -> dict[str, float]:
    """Todas las cotas de los contratos del reloj, por nombre, en SI."""
    datos = json.loads(ruta.read_text(encoding="utf-8"))
    return {
        v["nombre"]: float(v["valor"])
        for c in datos["contratos"]
        for v in c.get("valores", [])
        if isinstance(v.get("valor"), int | float)
    }


@dataclass(frozen=True)
class Estimados:
    """Lo incierto, del JSON del banco: nada de esto es una cota."""

    rozamiento_paleta: float
    restitucion: float
    rozamiento_eje_rueda: float
    radio_polea: float
    calidad: float


def estimados(escape: Path = BANCO_ESCAPE, pendulo: Path = BANCO_PENDULO) -> Estimados:
    e = json.loads(escape.read_text(encoding="utf-8"))["estimado"]
    p = json.loads(pendulo.read_text(encoding="utf-8"))["estimado"]
    return Estimados(
        rozamiento_paleta=float(e["rozamiento_paleta"]["valor"]),
        restitucion=float(e["restitucion"]["valor"]),
        rozamiento_eje_rueda=float(e["rozamiento_eje_rueda"]["valor"]),
        radio_polea=float(e["radio_polea_banco"]["valor"]),
        calidad=float(p["calidad_prevista"]),
    )


def pendulo_c11(c: dict[str, float] | None = None) -> Pendulo:
    """El péndulo de los contratos, como lo monta C11."""
    c = contratos_reloj() if c is None else c
    desde = c["muelle_flexion_a_varilla"]
    largo = c["varilla_largo"]
    masa_varilla = c["varilla_densidad"] * largo * c["varilla_ancho"] * c["varilla_espesor"]
    return Pendulo(
        masa_lenteja=Kilogramos(c["lenteja_masa"]),
        centro_lenteja=Metros(c["lenteja_centro_a_flexion"]),
        masa_varilla=Kilogramos(masa_varilla),
        varilla_desde=Metros(desde),
        varilla_hasta=Metros(desde + largo),
    )


# ---------------------------------------------------------------------------
# Masas e inercias desde los polígonos
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Cuerpo:
    """Masa, inercia respecto de su eje y primer momento (Σm·x, Σm·y) con el
    eje en el origen: lo que piden la ecuación del giro y la gravedad."""

    masa: float
    inercia: float
    momento: tuple[float, float]

    def __add__(self, otro: Cuerpo) -> Cuerpo:
        return Cuerpo(
            self.masa + otro.masa,
            self.inercia + otro.inercia,
            (self.momento[0] + otro.momento[0], self.momento[1] + otro.momento[1]),
        )


def cuerpo_de_poligono(
    figura: Polygon, espesor: float, densidad: float, eje: tuple[float, float]
) -> Cuerpo:
    """Un prisma de planta `figura` (con sus agujeros) respecto de `eje`.

    Exacto por Green, como `core/solido.py`, pero restando cada hueco como
    otro polígono: el yugo lleva el agujero del eje y no es un círculo
    alrededor de nada en particular."""
    from core.solido import area, centroide, momento_polar

    def de(anillo: Any) -> tuple[float, float, tuple[float, float]]:
        xy = np.asarray(anillo.coords, dtype=np.float64)[:-1]
        a = area(xy)
        cx, cy = centroide(xy)
        return a, momento_polar(xy, eje), (a * (cx - eje[0]), a * (cy - eje[1]))

    a, j, (sx, sy) = de(figura.exterior)
    for hueco in figura.interiors:
        ah, jh, (hx, hy) = de(hueco)
        a, j, sx, sy = a - ah, j - jh, sx - hx, sy - hy
    k = espesor * densidad
    return Cuerpo(a * k, j * k, (sx * k, sy * k))


def horquilla(ancora: AncoraGraham) -> Polygon:
    """PROVISIONAL: la pletina que baja del eje del áncora a la varilla."""
    x0, y0 = ancora.eje_ancora
    h = HORQUILLA
    return Polygon(
        [
            (x0 - h["ancho"] / 2, y0),
            (x0 + h["ancho"] / 2, y0),
            (x0 + h["ancho"] / 2, y0 - h["largo"]),
            (x0 - h["ancho"] / 2, y0 - h["largo"]),
        ]
    )


@dataclass(frozen=True)
class Regulador:
    """Todo lo que la dinámica necesita, ya calculado, en SI."""

    escala: float
    rueda: RuedaGraham
    ancora: AncoraGraham
    tablas: dict[str, TablaDeContacto]
    pendulo: Pendulo
    oscilante: Cuerpo
    """Péndulo + áncora + horquilla, respecto del eje del áncora."""
    inercia_rueda: float
    masa_rueda: float
    estimados: Estimados
    radio_eje: float

    @property
    def omega0(self) -> float:
        return math.sqrt(-G * self.oscilante.momento[1] / self.oscilante.inercia)

    @property
    def amortiguamiento(self) -> float:
        """c = I·ω₀/Q: el viscoso que da el Q de R1 a amplitud pequeña."""
        return self.oscilante.inercia * self.omega0 / self.estimados.calidad

    def periodo_pequeno(self) -> float:
        return 2.0 * math.pi / self.omega0


def regulador(escala: float = 1.0, amplitud_de_tabla: float = AMPLITUD_DE_TABLA) -> Regulador:
    """El regulador del banco R2 a `escala` (1 o 2), con las tablas de contacto."""
    rueda, ancora = geometria(escala)
    c = contratos_reloj()
    madera = DENSIDADES["contrachapado de abedul"]
    laton = DENSIDADES["latón"]
    espesor = c["ancora_espesor"]
    eje = ancora.eje_ancora

    p = pendulo_c11(c)
    pend = Cuerpo(p.masa, p.inercia, (0.0, -p.masa * p.centro_de_masas))
    piezas = cuerpo_de_poligono(yugo(ancora), espesor, madera, eje)
    for lado in ("entrada", "salida"):
        piezas = piezas + cuerpo_de_poligono(paleta(ancora, lado), espesor, laton, eje)
    piezas = piezas + cuerpo_de_poligono(horquilla(ancora), HORQUILLA["espesor"], laton, eje)

    disco = contorno_rueda(rueda)
    radio_eje = float(ancora.eje) / 2
    from shapely.geometry import Point

    disco = disco.difference(Point(0.0, 0.0).buffer(radio_eje, 64))
    r = cuerpo_de_poligono(disco, espesor, madera, (0.0, 0.0))

    tablas = {
        lado: tabla_de_contacto(rueda, ancora, lado, amplitud_de_tabla, PASO_DE_TABLA)  # type: ignore[arg-type]
        for lado in ("entrada", "salida")
    }
    return Regulador(
        escala=escala,
        rueda=rueda,
        ancora=ancora,
        tablas=tablas,
        pendulo=p,
        oscilante=pend + piezas,
        inercia_rueda=r.inercia,
        masa_rueda=r.masa,
        estimados=estimados(),
        radio_eje=radio_eje,
    )


# ---------------------------------------------------------------------------
# La ligadura, interpolada
# ---------------------------------------------------------------------------


class Ligadura:
    """La tabla de una paleta lista para el integrador: `g`, `g'`, `g''` y la
    geometría del contacto en cualquier `θ` de su dominio.

    PCHIP y no un spline cúbico: en la esquina del arco al plano de impulso
    la pendiente salta de 0 a -1,45, y un cúbico oscila antes y después,
    inventando un retroceso en pleno reposo."""

    def __init__(self, t: TablaDeContacto) -> None:
        ok = np.isfinite(t.phi)
        # El dominio es un intervalo: el diente toca hasta que pasa la esquina.
        idx = np.flatnonzero(ok)
        self.desde, self.hasta = float(t.theta[idx[0]]), float(t.theta[idx[-1]])
        th = t.theta[idx]
        self.g = PchipInterpolator(th, t.phi[idx])
        self.dg = self.g.derivative()
        self.d2g = self.g.derivative(2)
        self.th = th
        self.punto = t.punto[idx]
        self.normal = t.normal[idx]
        self.eje = np.array(t.eje_ancora)
        # Hacia qué lado se suelta: donde el dominio acaba en el interior de
        # la rejilla (el otro extremo es el borde de la tabla).
        self.suelta_por_abajo = self.desde > float(t.theta[0]) + 1e-9

    def dentro(self, theta: float) -> bool:
        return self.desde <= theta <= self.hasta

    def geometria(self, theta: float) -> tuple[Arreglo, Arreglo]:
        cx = np.interp(theta, self.th, self.punto[:, 0])
        cy = np.interp(theta, self.th, self.punto[:, 1])
        nx = np.interp(theta, self.th, self.normal[:, 0])
        ny = np.interp(theta, self.th, self.normal[:, 1])
        n = np.array([nx, ny])
        return np.array([cx, cy]), n / np.linalg.norm(n)


# ---------------------------------------------------------------------------
# La dinámica
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Parametros:
    """Lo que se puede variar en una simulación."""

    par: float
    """N·m en el eje de la rueda: el de la pesa."""
    rozamiento_paleta: float
    restitucion: float
    rozamiento_eje: float
    """Coeficiente del eje de la rueda; 0 lo apaga."""
    radio_polea: float
    calidad: float | None
    """None: sin amortiguamiento."""
    escape: bool = True
    """False: el péndulo solo, para los tests de conservación y periodo."""


def parametros(reg: Regulador, par: float, **cambios: Any) -> Parametros:
    e = reg.estimados
    p = Parametros(
        par=par,
        rozamiento_paleta=e.rozamiento_paleta,
        restitucion=e.restitucion,
        rozamiento_eje=e.rozamiento_eje_rueda,
        radio_polea=e.radio_polea,
        calidad=e.calidad,
    )
    return replace(p, **cambios)


@dataclass
class Historia:
    """Lo que sale de una simulación, muestreado y con sus sucesos."""

    t: list[float] = field(default_factory=list)
    theta: list[float] = field(default_factory=list)
    omega: list[float] = field(default_factory=list)
    phi: list[float] = field(default_factory=list)
    big_omega: list[float] = field(default_factory=list)
    modo: list[str] = field(default_factory=list)
    """'reposo', 'impulso' o 'caida' en cada muestra."""
    lado: list[str] = field(default_factory=list)
    """La paleta que toca en cada muestra; vacío en la caída."""
    sucesos: list[tuple[float, str, float]] = field(default_factory=list)
    """(t, qué, valor): choques con su energía, sueltas, separaciones."""
    potencia: list[float] = field(default_factory=list)
    """W que el contacto da al péndulo (N·a_a·θ'): positiva en el impulso,
    negativa en el reposo, que frena."""
    disipada: list[float] = field(default_factory=list)
    """W que se lleva el amortiguamiento del péndulo (c·θ'²)."""
    fin: str = ""
    final: tuple[float, float] = (math.nan, math.nan)
    """(θ, θ') donde ha parado."""
    t_final: float = math.nan
    """El instante exacto en que ha parado, del evento: las muestras van cada
    pocos milisegundos y la marcha pide microsegundos."""

    def arrays(self) -> dict[str, Arreglo]:
        return {
            k: np.asarray(getattr(self, k), dtype=np.float64)
            for k in ("t", "theta", "omega", "phi", "big_omega", "potencia", "disipada")
        }


class Simulador:
    """Integra el regulador por tramos entre sucesos."""

    def __init__(self, reg: Regulador, p: Parametros) -> None:
        self.reg, self.p = reg, p
        self.lig = {lado: Ligadura(t) for lado, t in reg.tablas.items()}
        self.I = reg.oscilante.inercia
        self.Sx, self.Sy = reg.oscilante.momento
        self.J = reg.inercia_rueda
        self.c = 0.0 if p.calidad is None else self.I * reg.omega0 / p.calidad
        self.A = np.array(reg.ancora.eje_ancora)
        self.paso = float(reg.rueda.paso)
        # Rozamiento del eje: carga radial = la pesa (par/radio de polea) y la
        # rueda; brazo = el radio del eje.
        carga = p.par / p.radio_polea + reg.masa_rueda * G
        self.par_eje = p.rozamiento_eje * carga * reg.radio_eje

    # -- fuerzas ----------------------------------------------------------------

    def gravedad(self, theta: float, omega: float) -> float:
        par = -G * (self.Sx * math.cos(theta) - self.Sy * math.sin(theta))
        return par - self.c * omega

    def par_neto(self, big_omega: float) -> float:
        return self.p.par - self.par_eje * math.tanh(big_omega / W_EJE)

    def _brazos(
        self, c: Arreglo, n: Arreglo, omega: float, big_omega: float
    ) -> tuple[float, float]:
        """(a_r, a_a) con el rozamiento en el sentido del deslizamiento."""
        t = np.array([-n[1], n[0]])
        v_diente = big_omega * np.array([c[1], -c[0]])
        r = c - self.A
        v_paleta = omega * np.array([-r[1], r[0]])
        desliza = float(np.dot(v_diente - v_paleta, t))
        sigma = math.tanh(desliza / V_DESLIZAMIENTO) if self.p.rozamiento_paleta else 0.0
        f = n - self.p.rozamiento_paleta * sigma * t
        a_r = float(c[0] * f[1] - c[1] * f[0])
        a_a = -float(r[0] * f[1] - r[1] * f[0])
        return a_r, a_a

    def contacto(self, lado: str, theta: float, omega: float) -> tuple[float, float, float]:
        """(θ'', N, Ω) en contacto con `lado`."""
        lig = self.lig[lado]
        g1 = float(lig.dg(theta))
        g2 = float(lig.d2g(theta))
        big_omega = g1 * omega
        c, n = lig.geometria(theta)
        a_r, a_a = self._brazos(c, n, omega, big_omega)
        m = self.par_neto(big_omega)
        k = a_a / a_r
        acel = (self.gravedad(theta, omega) + k * (m - self.J * g2 * omega**2)) / (
            self.I + k * self.J * g1
        )
        normal = (m - self.J * (g1 * acel + g2 * omega**2)) / a_r
        return acel, normal, big_omega

    def modo_de(self, lado: str, theta: float) -> str:
        return "impulso" if abs(float(self.lig[lado].dg(theta))) > 1e-3 else "reposo"

    # -- simulación ---------------------------------------------------------------

    def simular(
        self,
        theta0: float,
        duracion: float,
        muestras_por_segundo: float = 200.0,
        omega0: float = 0.0,
        parar_en_extremo: int | None = None,
    ) -> Historia:
        """Desde el péndulo soltado en `theta0` y la rueda bloqueada.

        `parar_en_extremo`: para en el n-ésimo extremo positivo después del
        de partida (el mapa de Poincaré)."""
        h = Historia()
        self._arranque = 0.75 * self.reg.periodo_pequeno()
        if not self.p.escape:
            return self._libre_sin_escape(theta0, omega0, duracion, muestras_por_segundo, h)
        lado = "entrada" if self.lig["entrada"].dentro(theta0) else "salida"
        if not self.lig[lado].dentro(theta0):
            raise ValueError(f"con θ = {math.degrees(theta0):.2f}° ninguna paleta toca")
        estado: dict[str, Any] = {
            "modo": "contacto",
            "lado": lado,
            "k": 0,
            "t": 0.0,
            "y": np.array([theta0, omega0]),
        }
        extremos = 0
        rebotes = 0
        while estado["t"] < duracion - 1e-12:
            if estado["modo"] == "contacto":
                fin, extremos = self._tramo_contacto(
                    estado, duracion, muestras_por_segundo, h, extremos, parar_en_extremo
                )
            else:
                fin, extremos = self._tramo_libre(
                    estado, duracion, muestras_por_segundo, h, extremos, parar_en_extremo
                )
                rebotes = rebotes + 1 if fin == "rebote" else 0
                if rebotes > 50:
                    h.fin = "rebotes sin fin"
                    return h
            if fin in ("fin", "extremo", "fuera"):
                if fin == "fuera":
                    h.fin = "fuera de la tabla: la amplitud pasa de la geometría mirada"
                elif fin == "extremo":
                    h.fin = "extremo"
                break
        if not h.fin:
            h.fin = "duración"
        y = estado["y"]
        h.final = (float(y[0]), float(y[1]))
        h.t_final = float(estado["t"])
        return h

    def _guardar(
        self, h: Historia, sol: Any, t0: float, t1: float, mps: float, f: Any, lado: str = ""
    ) -> None:
        n = max(2, int((t1 - t0) * mps))
        ts = np.linspace(t0, t1, n, endpoint=False) if t1 > t0 else np.array([t0])
        for tt in ts:
            y = sol.sol(tt)
            th, om, ph, bo, modo, pot = f(y)
            h.potencia.append(pot)
            h.disipada.append(self.c * om * om)
            h.t.append(float(tt))
            h.theta.append(th)
            h.omega.append(om)
            h.phi.append(ph)
            h.big_omega.append(bo)
            h.modo.append(modo)
            h.lado.append(lado)

    def _tramo_contacto(
        self,
        e: dict[str, Any],
        duracion: float,
        mps: float,
        h: Historia,
        extremos: int,
        parar: int | None,
    ) -> tuple[str, int]:
        lado, k = e["lado"], e["k"]
        lig = self.lig[lado]

        def f(t: float, y: Arreglo) -> list[float]:
            acel, _, _ = self.contacto(lado, float(y[0]), float(y[1]))
            return [float(y[1]), acel]

        def normal_cero(t: float, y: Arreglo) -> float:
            return self.contacto(lado, float(y[0]), float(y[1]))[1]

        normal_cero.terminal = True  # type: ignore[attr-defined]
        normal_cero.direction = -1  # type: ignore[attr-defined]

        def suelta(t: float, y: Arreglo) -> float:
            return float(y[0]) - (lig.desde if lig.suelta_por_abajo else lig.hasta)

        suelta.terminal = True  # type: ignore[attr-defined]
        suelta.direction = -1 if lig.suelta_por_abajo else 1  # type: ignore[attr-defined]

        def borde(t: float, y: Arreglo) -> float:
            return float(y[0]) - (lig.hasta if lig.suelta_por_abajo else lig.desde)

        borde.terminal = True  # type: ignore[attr-defined]
        borde.direction = 1 if lig.suelta_por_abajo else -1  # type: ignore[attr-defined]

        arranque = self._arranque

        def extremo(t: float, y: Arreglo) -> float:
            # Soltado desde el extremo, θ' sale de cero hacia negativo: eso no
            # es un extremo. Hasta tres cuartos de periodo, cuando θ' ya es
            # positivo seguro, el evento vale +1; así no hay salto que el
            # integrador confunda con un cruce.
            if t < arranque or y[0] <= 0:
                return 1.0
            return float(y[1])

        extremo.terminal = parar is not None  # type: ignore[attr-defined]
        extremo.direction = -1  # type: ignore[attr-defined]

        t0 = e["t"]
        sol = solve_ivp(
            f,
            (t0, duracion),
            e["y"],
            method="DOP853",
            rtol=1e-10,
            atol=1e-13,
            dense_output=True,
            events=[normal_cero, suelta, borde, extremo],
            max_step=0.02,
        )
        t1 = float(sol.t[-1])

        def muestra(y: Arreglo) -> tuple[float, float, float, float, str, float]:
            th, om = float(y[0]), float(y[1])
            acel, _, _ = self.contacto(lado, th, om)
            return (
                th,
                om,
                float(lig.g(th)) + k * self.paso,
                float(lig.dg(th)) * om,
                self.modo_de(lado, th),
                (self.I * acel - self.gravedad(th, om)) * om,
            )

        # Si el tramo se ha parado en un extremo que no es el pedido, se sigue.
        sucesos = [(i, float(ts[0])) for i, ts in enumerate(sol.t_events) if len(ts)]
        if sol.status == 1 and sucesos:
            i, te = min(sucesos, key=lambda s: s[1])
            if i == 3:
                extremos += 1
                if parar is not None and extremos >= parar:
                    self._guardar(h, sol, t0, te, mps, muestra, lado)
                    e["t"], e["y"] = te, sol.sol(te)
                    return "extremo", extremos
        self._guardar(h, sol, t0, t1, mps, muestra, lado)
        y1 = sol.y[:, -1]
        th1, om1 = float(y1[0]), float(y1[1])
        e["t"] = t1
        if sol.status == 0:
            e["y"] = y1
            return "fin", extremos
        i = min(sucesos, key=lambda s: s[1])[0]
        if i == 2:
            e["y"] = y1
            return "fuera", extremos
        # Normal a cero o el diente pasa la esquina: caída libre.
        h.sucesos.append((t1, "suelta" if i == 1 else "separa", th1))
        e["modo"] = "libre"
        e["y"] = np.array([th1, om1, float(lig.g(th1)) + k * self.paso, float(lig.dg(th1)) * om1])
        e["desde"] = (lado, k)
        return ("suelta" if i == 1 else "separa"), extremos

    def _holgura(self, lado: str, k: int, theta: float, phi: float) -> float:
        lig = self.lig[lado]
        th = min(max(theta, lig.desde), lig.hasta)
        g = float(lig.g(th)) + k * self.paso - phi
        if not lig.dentro(theta):
            # Fuera del dominio esa paleta no para la rueda: holgura grande,
            # que crece al alejarse para que el evento no vea un cero falso.
            return g + 1.0 + abs(theta - th)
        return g

    def _tramo_libre(
        self,
        e: dict[str, Any],
        duracion: float,
        mps: float,
        h: Historia,
        extremos: int,
        parar: int | None,
    ) -> tuple[str, int]:
        lado_antes, k_antes = e["desde"]
        # Las dos paletas que pueden recoger la rueda: la misma (rebote) y la
        # otra con el diente siguiente.
        candidatos = [(lado_antes, k_antes)]
        if lado_antes == "entrada":
            candidatos.append(("salida", k_antes))
        else:
            candidatos.append(("entrada", k_antes + 1))

        def f(t: float, y: Arreglo) -> list[float]:
            th, om, _, bo = (float(v) for v in y)
            return [om, self.gravedad(th, om) / self.I, bo, self.par_neto(bo) / self.J]

        eventos: list[Any] = []
        th0, ph0 = float(e["y"][0]), float(e["y"][2])
        for lado, k in candidatos:
            # El margen se mide desde donde arranca el tramo: tras un choque la
            # holgura empieza en -margen, y el evento tiene que arrancar en
            # positivo para ver el cruce siguiente.
            margen = max(HOLGURA_DE_EVENTO, HOLGURA_DE_EVENTO - self._holgura(lado, k, th0, ph0))

            def toca(
                t: float, y: Arreglo, lado: str = lado, k: int = k, margen: float = margen
            ) -> float:
                # El margen hace que el tramo arranque siempre en positivo: tras
                # un rebote o una separación la holgura empieza en cero, y el
                # diente vuelve a tocar en menos de un milisegundo. Sin él, el
                # integrador no ve el cruce y la rueda atraviesa la paleta.
                return self._holgura(lado, k, float(y[0]), float(y[2])) + margen

            toca.terminal = True  # type: ignore[attr-defined]
            toca.direction = -1  # type: ignore[attr-defined]
            eventos.append(toca)

        arranque = self._arranque

        def extremo(t: float, y: Arreglo) -> float:
            # Soltado desde el extremo, θ' sale de cero hacia negativo: eso no
            # es un extremo. Hasta tres cuartos de periodo, cuando θ' ya es
            # positivo seguro, el evento vale +1; así no hay salto que el
            # integrador confunda con un cruce.
            if t < arranque or y[0] <= 0:
                return 1.0
            return float(y[1])

        extremo.terminal = parar is not None  # type: ignore[attr-defined]
        extremo.direction = -1  # type: ignore[attr-defined]
        eventos.append(extremo)

        t0 = e["t"]
        sol = solve_ivp(
            f,
            (t0, duracion),
            e["y"],
            method="DOP853",
            rtol=1e-10,
            atol=1e-13,
            dense_output=True,
            events=eventos,
            max_step=0.005,
        )

        def muestra(y: Arreglo) -> tuple[float, float, float, float, str, float]:
            return float(y[0]), float(y[1]), float(y[2]), float(y[3]), "caida", 0.0

        sucesos = [(i, float(ts[0])) for i, ts in enumerate(sol.t_events) if len(ts)]
        if sol.status == 1 and sucesos:
            i, te = min(sucesos, key=lambda s: s[1])
            if i == len(eventos) - 1:
                extremos += 1
                if parar is not None and extremos >= parar:
                    self._guardar(h, sol, t0, te, mps, muestra)
                    e["t"], e["y"] = te, sol.sol(te)
                    return "extremo", extremos
        t1 = float(sol.t[-1])
        self._guardar(h, sol, t0, t1, mps, muestra)
        e["t"] = t1
        y1 = sol.y[:, -1]
        if sol.status == 0:
            e["y"] = y1
            return "fin", extremos
        i = min(sucesos, key=lambda s: s[1])[0]
        lado, k = candidatos[i]
        return self._choque(e, h, lado, k, y1), extremos

    def _choque(self, e: dict[str, Any], h: Historia, lado: str, k: int, y: Arreglo) -> str:
        """Restitución en la normal, Coulomb en la tangente. Devuelve 'pega'
        si el diente se queda (contacto) o 'rebote'."""
        th, om, ph, bo = (float(v) for v in y)
        c, n = self.lig[lado].geometria(th)
        r = c - self.A
        h_r = float(c[0] * n[1] - c[1] * n[0])
        h_a = float(r[0] * n[1] - r[1] * n[0])
        v_n = -bo * h_r - om * h_a  # < 0: el diente se acerca a la paleta
        a_r, a_a = self._brazos(c, n, om, bo)
        rigidez = a_r * h_r / self.J - a_a * h_a / self.I
        impulso = -(1.0 + self.p.restitucion) * v_n / rigidez
        bo2 = bo - impulso * a_r / self.J
        om2 = om + impulso * a_a / self.I
        energia = 0.5 * self.J * (bo**2 - bo2**2) + 0.5 * self.I * (om**2 - om2**2)
        h.sucesos.append((e["t"], f"choque {lado}", energia))
        v_n2 = -bo2 * h_r - om2 * h_a
        if v_n2 < SEPARACION_MINIMA:
            e["modo"], e["lado"], e["k"] = "contacto", lado, k
            e["y"] = np.array([th, om2])
            return "pega"
        e["y"] = np.array([th, om2, ph, bo2])
        e["desde"] = (lado, k)
        return "rebote"

    def _libre_sin_escape(
        self, theta0: float, omega0: float, duracion: float, mps: float, h: Historia
    ) -> Historia:
        def f(t: float, y: Arreglo) -> list[float]:
            return [float(y[1]), self.gravedad(float(y[0]), float(y[1])) / self.I]

        sol = solve_ivp(
            f,
            (0.0, duracion),
            [theta0, omega0],
            method="DOP853",
            rtol=1e-11,
            atol=1e-14,
            dense_output=True,
        )
        for tt in np.linspace(0.0, duracion, max(2, int(duracion * mps)), endpoint=False):
            th, om = (float(v) for v in sol.sol(tt))
            h.t.append(float(tt))
            h.theta.append(th)
            h.omega.append(om)
            h.phi.append(0.0)
            h.big_omega.append(0.0)
            h.modo.append("libre")
            h.lado.append("")
            h.potencia.append(0.0)
            h.disipada.append(self.c * float(om) ** 2)
        h.fin = "duración"
        return h


# ---------------------------------------------------------------------------
# Lo que se mide de una simulación
# ---------------------------------------------------------------------------


def extremos(h: Historia) -> tuple[Arreglo, Arreglo]:
    """(tiempos, amplitudes) de cada extremo positivo, interpolado."""
    t = np.asarray(h.t)
    th = np.asarray(h.theta)
    om = np.asarray(h.omega)
    i = np.flatnonzero((om[:-1] > 0) & (om[1:] <= 0) & (th[:-1] > 0))
    ts, amps = [], []
    for j in i:
        # Parábola por tres puntos alrededor del máximo.
        if 0 < j < len(t) - 1:
            a, b, c = th[j - 1], th[j], th[j + 1]
            den = a - 2 * b + c
            d = 0.5 * (a - c) / den if den != 0 else 0.0
            ts.append(float(t[j] + d * (t[j + 1] - t[j])))
            amps.append(float(b - 0.25 * (a - c) * d))
    return np.asarray(ts), np.asarray(amps)


def periodo_medido(h: Historia, ultimos: int = 10) -> float:
    """Periodo medio entre los cruces por cero ascendentes del final."""
    t = np.asarray(h.t)
    th = np.asarray(h.theta)
    i = np.flatnonzero((th[:-1] < 0) & (th[1:] >= 0))
    cruces = t[i] - th[i] * (t[i + 1] - t[i]) / (th[i + 1] - th[i])
    cruces = cruces[-(ultimos + 1) :]
    if len(cruces) < 2:
        return math.nan
    return float(np.mean(np.diff(cruces)))


def marcha_dia(periodo: float, nominal: float = 2.0) -> float:
    """s/día que adelanta (+) o atrasa (-) un reloj con este periodo."""
    return SEGUNDOS_POR_DIA * (nominal / periodo - 1.0)


def ciclo(sim: Simulador, amplitud: float) -> tuple[float, float]:
    """Poincaré: (amplitud, periodo) del extremo positivo siguiente al soltar
    el péndulo en `amplitud` con la rueda bloqueada. El periodo es el tiempo
    hasta ese extremo: una oscilación completa."""
    h = sim.simular(amplitud, duracion=4.0 * sim.reg.periodo_pequeno(), parar_en_extremo=1)
    if h.fin == "extremo":
        return h.final[0], h.t_final
    if h.fin.startswith("fuera"):
        return math.inf, math.nan
    # Sin un extremo positivo en cuatro periodos: el péndulo se ha parado.
    return 0.0, math.nan


def amplitud_limite(
    reg: Regulador, desde: float = grados(3.0), hasta: float = grados(12.0)
) -> float:
    """La mayor amplitud a la que la geometría sigue funcionando, según la
    envolvente de conjunto (`graham.juzgar`), por bisección a 0,05°."""
    from core.reloj.graham import juzgar

    def vale(a: float) -> bool:
        return not juzgar(reg.rueda, reg.ancora, Radianes(a), oscilaciones=2).incidencias

    if not vale(desde):
        return math.nan
    if vale(hasta):
        return hasta
    a, b = desde, hasta
    while b - a > grados(0.05):
        m = (a + b) / 2
        if vale(m):
            a = m
        else:
            b = m
    return a


def balance(reg: Regulador, p: Parametros, amplitud: float) -> dict[str, float]:
    """Julios por oscilación, soltando en `amplitud` con la rueda bloqueada:
    lo que entrega la rueda y adónde va."""
    sim = Simulador(reg, p)
    h = sim.simular(amplitud, 4 * reg.periodo_pequeno(), 20000.0, parar_en_extremo=1)
    t = np.asarray(h.t)
    dt = np.diff(t, append=h.t_final)
    potencia = np.asarray(h.potencia)
    modo = np.asarray(h.modo)
    phi = np.asarray(h.phi)
    giro = float(phi[-1] - phi[0])
    energia = -G * reg.oscilante.momento[1] * (1.0 - math.cos(amplitud))
    return {
        "trabajo_de_la_rueda": p.par * giro,
        "al_pendulo_en_el_impulso": float(np.sum((potencia * dt)[modo == "impulso"])),
        "rozamiento_del_reposo": float(-np.sum((potencia * dt)[modo == "reposo"])),
        "amortiguamiento_del_pendulo": float(np.sum(np.asarray(h.disipada) * dt)),
        "choques": float(sum(v for _, q, v in h.sucesos if q.startswith("choque"))),
        "eje_de_la_rueda": sim.par_eje * giro,
        "energia_del_pendulo": energia,
    }


def mapa(sim: Simulador, amplitud: float) -> float:
    """La amplitud de `ciclo`, para buscar puntos fijos."""
    return ciclo(sim, amplitud)[0]


def amplitud_estable(
    reg: Regulador, p: Parametros, desde: float = grados(1.8), hasta: float = grados(7.5)
) -> float:
    """La amplitud a la que la energía de los impulsos iguala la que se pierde:
    el punto fijo estable del mapa. `nan` si no la hay en el intervalo."""
    sim = Simulador(reg, p)

    def exceso(a: float) -> float:
        return mapa(sim, a) - a

    alto = exceso(hasta)
    if not math.isfinite(alto) or alto > 0:
        return math.nan
    bajo = exceso(desde)
    if bajo < 0:
        return math.nan
    return float(brentq(exceso, desde, hasta, xtol=grados(0.001)))


PAR_MAXIMO_DE_BUSQUEDA: Final[float] = 2.0e-2
"""N·m. Tres veces el tope de C12 (6,5 mN·m): si con esto no se llega, no es
cuestión de pesa."""


def _con(reg: Regulador, par: float, con_eje: bool, cambios: dict[str, Any]) -> Parametros:
    return parametros(reg, par, **({} if con_eje else {"rozamiento_eje": 0.0}), **cambios)


def par_para_amplitud(
    reg: Regulador, amplitud: float, con_eje: bool = True, **cambios: Any
) -> float:
    """El par en el eje de la rueda que mantiene `amplitud`. `nan` si ni con
    `PAR_MAXIMO_DE_BUSQUEDA` se llega: en un escape de reposo con rozamiento
    seco la amplitud se satura, porque el rozamiento del arco crece con el
    par lo mismo que el impulso."""

    def exceso(par: float) -> float:
        return mapa(Simulador(reg, _con(reg, par, con_eje, cambios)), amplitud) - amplitud

    if exceso(PAR_MAXIMO_DE_BUSQUEDA) < 0:
        return math.nan
    return float(brentq(exceso, 2.0e-4, PAR_MAXIMO_DE_BUSQUEDA, xtol=1e-7))


def par_de_parada(
    reg: Regulador,
    con_eje: bool = True,
    desde: float = 2.0e-4,
    hasta: float = 6.5e-3,
    **cambios: Any,
) -> float:
    """El par por debajo del cual el regulador se para: no hay amplitud
    estable. Es lo que mide el banco bajando la pesa hasta que deja de
    andar."""

    def anda(par: float) -> bool:
        return math.isfinite(amplitud_estable(reg, _con(reg, par, con_eje, cambios)))

    if not anda(hasta):
        return math.nan
    a, b = desde, hasta
    for _ in range(14):
        m = math.sqrt(a * b)
        if anda(m):
            b = m
        else:
            a = m
    return b


def amplitud_de_arranque(reg: Regulador, p: Parametros) -> float:
    """La amplitud desde la que arranca solo: el punto fijo inestable del
    mapa. Por debajo, el péndulo no llega a soltar el diente, los impulsos
    se devuelven con el retroceso y se para."""
    sim = Simulador(reg, p)

    def exceso(a: float) -> float:
        return mapa(sim, a) - a

    abajo, arriba = grados(0.5), grados(2.2)
    if exceso(abajo) > 0 or exceso(arriba) < 0:
        return math.nan
    return float(brentq(exceso, abajo, arriba, xtol=grados(0.001)))


def periodo_libre(reg: Regulador, amplitud: float) -> float:
    """El periodo del péndulo solo, sin escape ni amortiguamiento, a esa
    amplitud: lo que el error circular deja, y contra lo que se mide el error
    propio del escape."""
    sim = Simulador(reg, parametros(reg, 0.0, escape=False, calidad=None))
    h = sim.simular(amplitud, 3.2 * reg.periodo_pequeno(), muestras_por_segundo=4000)
    return periodo_medido(h, ultimos=2)


@dataclass(frozen=True)
class Marcha:
    """El regulador en régimen con un par."""

    par: float
    amplitud: float
    periodo: float
    marcha: float
    """s/día frente a 2 s."""
    error_circular: float
    """s/día del péndulo solo a esa amplitud frente a 2 s."""

    @property
    def error_escape(self) -> float:
        """s/día que pone el escape, quitado el error circular."""
        return self.marcha - self.error_circular


def en_regimen(reg: Regulador, p: Parametros) -> Marcha:
    a = amplitud_estable(reg, p)
    if not math.isfinite(a):
        return Marcha(p.par, math.nan, math.nan, math.nan, math.nan)
    _, t = ciclo(Simulador(reg, p), a)
    return Marcha(p.par, a, t, marcha_dia(t), marcha_dia(periodo_libre(reg, a)))


__all__ = [
    "Cuerpo",
    "Estimados",
    "Historia",
    "Ligadura",
    "Marcha",
    "Parametros",
    "Regulador",
    "Simulador",
    "amplitud_de_arranque",
    "amplitud_estable",
    "amplitud_limite",
    "balance",
    "ciclo",
    "contratos_reloj",
    "cuerpo_de_poligono",
    "en_regimen",
    "estimados",
    "extremos",
    "horquilla",
    "mapa",
    "marcha_dia",
    "par_de_parada",
    "par_para_amplitud",
    "parametros",
    "pendulo_c11",
    "periodo_libre",
    "periodo_medido",
    "regulador",
]
