"""Dibuja perfiles de leva en SVG para revisarlos a ojo.

Es la mitad humana de la puerta de E2: hay levas que salen mal de una forma
que se ve antes de calcular nada, y hay números correctos que producen una
pieza absurda. Esto no valida nada por sí solo; sirve para mirar.

No usa ninguna biblioteca de dibujo: escribe el SVG a mano desde los arreglos
que devuelve el núcleo. Así no entra una dependencia nueva por una
herramienta de desarrollo.

    uv run python scripts/dibujar_perfiles.py [destino.svg]
"""

from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from core.cam.curves import desde_muestras, rejilla
from core.cam.envelope import evaluar
from core.cam.synth import PerfilLeva, Seguidor, sintetizar
from core.units import TAU, a_grados, a_mm, grados, mm
from core.verdict import Veredicto

ANCHO_PANEL = 250
ALTO_PANEL = 330
COLUMNAS = 5
MARGEN = 18
ALTO_PSI = 58


@dataclass(frozen=True)
class Caso:
    titulo: str
    radio_base: float
    brazo: float
    radio_rodillo: float
    psi: np.ndarray


def _sinusoide(amplitud_grados: float, n: int = 96) -> np.ndarray:
    return grados(amplitud_grados) * np.sin(rejilla(n))


def _subida_reposo_bajada(amplitud_grados: float, n: int = 96) -> np.ndarray:
    """Ley cicloidal: sube, se queda, baja, se queda.

    Más parecida a lo que pide una escritura real que una sinusoide, y es el
    caso clásico de doble detención de la literatura de levas.
    """
    t = rejilla(n) / TAU
    valores = np.zeros_like(t)
    subida = (t >= 0.0) & (t < 0.25)
    reposo = (t >= 0.25) & (t < 0.5)
    bajada = (t >= 0.5) & (t < 0.75)
    u = (t[subida] - 0.0) / 0.25
    valores[subida] = u - np.sin(TAU * u) / TAU
    valores[reposo] = 1.0
    u = (t[bajada] - 0.5) / 0.25
    valores[bajada] = 1.0 - (u - np.sin(TAU * u) / TAU)
    return grados(amplitud_grados) * valores


CASOS = [
    Caso("oscilación ±4°", mm(40.0), mm(60.0), mm(4.0), _sinusoide(4.0)),
    Caso("oscilación ±8°", mm(40.0), mm(60.0), mm(4.0), _sinusoide(8.0)),
    Caso("oscilación ±12°", mm(40.0), mm(60.0), mm(4.0), _sinusoide(12.0)),
    Caso("oscilación ±16°", mm(40.0), mm(60.0), mm(4.0), _sinusoide(16.0)),
    Caso("oscilación ±22°", mm(40.0), mm(60.0), mm(4.0), _sinusoide(22.0)),
    Caso("base 28 mm, ±12°", mm(28.0), mm(60.0), mm(4.0), _sinusoide(12.0)),
    Caso("base 60 mm, ±16°", mm(60.0), mm(60.0), mm(4.0), _sinusoide(16.0)),
    Caso("rodillo 10 mm, ±12°", mm(40.0), mm(60.0), mm(10.0), _sinusoide(12.0)),
    Caso("rodillo 18 mm, ±12°", mm(40.0), mm(60.0), mm(18.0), _sinusoide(12.0)),
    Caso("cicloidal ±10°", mm(40.0), mm(60.0), mm(4.0), _subida_reposo_bajada(10.0)),
]


def _resolver(caso: Caso) -> tuple[PerfilLeva, Veredicto]:
    seguidor = Seguidor.bien_puesto(caso.radio_base, caso.brazo, caso.radio_rodillo)
    funcion = desde_muestras(rejilla(caso.psi.size), caso.psi, n=720)
    perfil = sintetizar(funcion, seguidor)
    return perfil, evaluar(perfil)


def _camino(puntos: np.ndarray, cx: float, cy: float, escala: float) -> str:
    x = cx + puntos[:, 0] * escala
    y = cy - puntos[:, 1] * escala  # en SVG la y crece hacia abajo
    partes = [f"M {x[0]:.2f} {y[0]:.2f}"]
    partes += [f"L {xi:.2f} {yi:.2f}" for xi, yi in zip(x[1:], y[1:], strict=True)]
    partes.append("Z")
    return " ".join(partes)


def _panel(indice: int, caso: Caso) -> str:
    perfil, veredicto = _resolver(caso)
    col = indice % COLUMNAS
    fila = indice // COLUMNAS
    x0 = MARGEN + col * ANCHO_PANEL
    y0 = MARGEN + fila * ALTO_PANEL

    # Hay que dejar sitio para el título arriba y las dos líneas de texto
    # abajo, o se salen del panel y la fila siguiente las tapa.
    alto_leva = ALTO_PANEL - ALTO_PSI - 100
    cx = x0 + ANCHO_PANEL / 2
    cy = y0 + 34 + alto_leva / 2
    escala = (min(ANCHO_PANEL, alto_leva) / 2 - 12) / max(perfil.radio_maximo, 1e-9)

    trazo = "#1d7a4c" if veredicto.apto else "#b3261e"
    fondo = "#f3f8f5" if veredicto.apto else "#fdf0ef"

    presion = a_grados(veredicto.metricas["angulo_presion_max"])
    ratio = veredicto.metricas["ratio_curvatura"]

    # ψ(θ) debajo: la trayectoria de la que sale esta leva
    py0 = y0 + 34 + alto_leva + 16
    amplitud = float(np.max(np.abs(perfil.psi))) or 1.0
    px = x0 + 16 + (perfil.thetas / TAU) * (ANCHO_PANEL - 32)
    py = py0 + ALTO_PSI / 2 - (perfil.psi / amplitud) * (ALTO_PSI / 2 - 6)
    psi_path = "M " + " L ".join(f"{a:.2f} {b:.2f}" for a, b in zip(px, py, strict=True))

    estado = "apto" if veredicto.apto else veredicto.incidencias[0].codigo.replace("_", " ")

    return f"""  <g>
    <rect x="{x0}" y="{y0}" width="{ANCHO_PANEL - 8}" height="{ALTO_PANEL - 8}"
          rx="8" fill="{fondo}" stroke="#d8d8d2" stroke-width="0.5"/>
    <text x="{x0 + 14}" y="{y0 + 20}" font-size="12" font-weight="500"
          fill="#2c2c2a">{caso.titulo}</text>
    <circle cx="{cx:.2f}" cy="{cy:.2f}" r="{caso.radio_base * escala:.2f}"
            fill="none" stroke="#c9c7bf" stroke-width="0.6" stroke-dasharray="3 3"/>
    <path d="{_camino(perfil.paso, cx, cy, escala)}" fill="none"
          stroke="#a8a69e" stroke-width="0.7" stroke-dasharray="4 3"/>
    <path d="{_camino(perfil.perfil, cx, cy, escala)}" fill="{trazo}" fill-opacity="0.10"
          stroke="{trazo}" stroke-width="1.6"/>
    <circle cx="{cx:.2f}" cy="{cy:.2f}" r="2.5" fill="#5f5e5a"/>
    <path d="{psi_path}" fill="none" stroke="#3a6ea5" stroke-width="1.2"/>
    <line x1="{x0 + 16}" y1="{py0 + ALTO_PSI / 2:.1f}" x2="{x0 + ANCHO_PANEL - 16}"
          y2="{py0 + ALTO_PSI / 2:.1f}" stroke="#d8d8d2" stroke-width="0.5"/>
    <text x="{x0 + 14}" y="{py0 + ALTO_PSI + 14:.1f}" font-size="10" fill="#5f5e5a">
      ψ(θ) · presión {presion:.0f}° · ρ/r {ratio:.1f} · ⌀{a_mm(perfil.radio_maximo) * 2:.0f} mm
    </text>
    <text x="{x0 + 14}" y="{py0 + ALTO_PSI + 27:.1f}" font-size="10" font-weight="500"
          fill="{trazo}">{estado}</text>
  </g>"""


def svg() -> str:
    ancho = MARGEN * 2 + COLUMNAS * ANCHO_PANEL
    filas = (len(CASOS) + COLUMNAS - 1) // COLUMNAS
    alto = MARGEN * 2 + filas * ALTO_PANEL + 26
    paneles = "\n".join(_panel(i, c) for i, c in enumerate(CASOS))
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{ancho}" height="{alto}"
     viewBox="0 0 {ancho} {alto}" font-family="system-ui, sans-serif">
  <rect width="{ancho}" height="{alto}" fill="#ffffff"/>
{paneles}
  <text x="{MARGEN}" y="{alto - 14}" font-size="11" fill="#5f5e5a">
    Perfil en trazo grueso · curva de paso discontinua · círculo base punteado ·
    ψ(θ) en azul, una vuelta completa · verde apto, rojo no apto
  </text>
</svg>
"""


def main() -> int:
    destino = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("out/perfiles.svg")
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text(svg(), encoding="utf-8")
    print(f"escrito {destino}")
    for caso in CASOS:
        perfil, veredicto = _resolver(caso)
        marca = "OK " if veredicto.apto else "NO "
        print(
            f"  {marca}{caso.titulo:<22} "
            f"presión {a_grados(veredicto.metricas['angulo_presion_max']):5.1f}°  "
            f"ρ/r {veredicto.metricas['ratio_curvatura']:5.1f}  "
            f"⌀ {a_mm(perfil.radio_maximo) * 2:5.1f} mm"
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
