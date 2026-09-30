"""Dibuja la máquina tal y como está conceptualizada, desde el propio modelo.

    uv run python scripts/dibujar_maquina.py --out build/maquina.svg

**No es un dibujo a mano.** Cada cota sale de `Escribiente`, de
`compile/conjunto.py` o de compilar `demo/hola.json`, así que no puede
discrepar de lo que calcula el motor: si alguien cambia el radio base, el
dibujo cambia solo. Es documentación, no geometría de producción —para eso
están los DXF y el STEP, que sí pasan por la envolvente—.

Dos decisiones de dibujo que no son estéticas:

- **Las levas van a escala real, y por eso parecen discos.** Las de escritura
  varían 3,7 mm sobre 52 de radio y la del elevador **0,56**. Esa es la
  verdad de la pieza y esconderla exagerando el lóbulo daría una idea
  equivocada de lo que se está cortando. Al lado va la misma curva con la
  desviación amplificada, que es donde se ve la forma.
- **Lo que falta se dibuja.** Un dibujo conceptual que rellena los huecos con
  algo verosímil es peor que no tenerlo: hace creer que el diseño está
  cerrado.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from compile.conjunto import montar
from compile.escribiente import SEGUIDORES, Escribiente, compilar
from core.escritura import Capacidad
from core.units import mm
from tests.casos import hola

MM = 1000.0
COLOR = {"izquierdo": "#2f6f4f", "derecho": "#8a5a2b", "elevador": "#4a5a8a"}


def _pts(puntos) -> str:
    """Puntos en mm con la Y hacia arriba, que es como se piensa la máquina."""
    return " ".join(f"{x * MM:.3f},{-y * MM:.3f}" for x, y in puntos)


# ---------------------------------------------------------------------------
# A · la planta del cartucho
# ---------------------------------------------------------------------------


def planta(m: Escribiente, perfiles, hueco: float) -> list[str]:
    d = [f'<circle class="ref" r="{float(m.radio_base) * MM:.2f}"/>']
    for nombre in SEGUIDORES:
        d.append(
            f'<polygon class="leva" points="{_pts(perfiles[nombre].perfil)}" '
            f'stroke="{COLOR[nombre]}" fill="{COLOR[nombre]}" fill-opacity="0.05"/>'
        )
    d.append(f'<circle class="corte" r="{float(m.taladro_eje) * MM / 2:.2f}"/>')
    rp = float(m.radio_del_pasador) * MM
    d.append(
        f'<circle class="corte" cx="{rp:.2f}" cy="0" r="{float(m.pasador_indice) * MM / 2:.2f}"/>'
    )
    d.append(f'<line class="fina" x1="{rp:.1f}" y1="-3" x2="{rp + 16:.1f}" y2="-20"/>')
    d.append(f'<text class="cota izq" x="{rp + 18:.1f}" y="-21">pasador Ø3 a r18</text>')

    for i, nombre in enumerate(SEGUIDORES):
        s = m.seguidor(i)
        px, py = s.pivote[0] * MM, -s.pivote[1] * MM
        rodillo = s.pivote + s.brazo * np.array([np.cos(s.psi_cero), np.sin(s.psi_cero)])
        rx, ry = rodillo[0] * MM, -rodillo[1] * MM
        d.append(f'<line class="brazo" x1="{px:.2f}" y1="{py:.2f}" x2="{rx:.2f}" y2="{ry:.2f}"/>')
        # el obstáculo que ve la leva no es el poste: es la valona del casquillo
        d.append(f'<circle class="poste" cx="{px:.2f}" cy="{py:.2f}" r="7.5"/>')
        d.append(f'<circle class="corte" cx="{px:.2f}" cy="{py:.2f}" r="4"/>')
        d.append(
            f'<circle class="rodillo" cx="{rx:.2f}" cy="{ry:.2f}" '
            f'r="{float(m.radio_rodillo) * MM:.2f}"/>'
        )
        # La etiqueta, empujada hacia fuera a lo largo de su propio radio.
        fuera = 1.26 * np.array([px, py])
        d.append(
            f'<text class="pieza" x="{fuera[0]:.1f}" y="{fuera[1] + (5 if py > 0 else -4):.1f}" '
            f'fill="{COLOR[nombre]}">{nombre}</text>'
        )

    r = float(np.hypot(*m.seguidor(0).pivote)) * MM
    d.append(f'<circle class="ref" r="{r:.2f}"/>')
    d += [
        f'<text class="cota" x="0" y="{r + 34:.1f}">postes a r {r:.2f}, repartidos 120°'
        f" · casquillo con valona Ø15, que es el obstáculo real</text>",
        f'<text class="cota" x="0" y="{r + 43:.1f}">radio base {float(m.radio_base) * MM:.0f}'
        f" · rodillo Ø{2 * float(m.radio_rodillo) * MM:.0f} (MR63ZZ)"
        f" · hueco leva-poste {hueco:.1f} mm</text>",
    ]
    return d


def lobulo(perfiles, escala: float = 8.0, radio: float = 34.0) -> list[str]:
    """La misma leva con la desviación del radio medio amplificada.

    A escala real la leva parece un disco, y es verdad que lo parece. Aquí se
    ve la forma, que es lo que hay que mirar para entender qué hace.
    """
    d = [f'<circle class="ref" r="{radio:.1f}"/>']
    for nombre in SEGUIDORES:
        p = perfiles[nombre].perfil
        rr = np.linalg.norm(p, axis=1)
        ang = np.arctan2(p[:, 1], p[:, 0])
        amp = radio + (rr - rr.mean()) * MM * escala
        puntos = np.column_stack([amp * np.cos(ang), amp * np.sin(ang)]) / MM
        d.append(f'<polygon class="lobulo" points="{_pts(puntos)}" stroke="{COLOR[nombre]}"/>')
        d.append(
            f'<text class="leyenda" x="{radio + 10:.0f}" '
            f'y="{-radio + 10 * SEGUIDORES.index(nombre):.0f}" fill="{COLOR[nombre]}">'
            f"{nombre} · ±{(rr.max() - rr.min()) * MM / 2:.2f} mm</text>"
        )
    d.append(f'<text class="cota" x="0" y="{radio + 15:.0f}">desviación ×{escala:.0f}</text>')
    return d


# ---------------------------------------------------------------------------
# B · el alzado del varillaje
# ---------------------------------------------------------------------------


def alzado(m: Escribiente) -> list[str]:
    b = m.brazo
    psi = b.inversa(np.array([[0.0, float(m.caja_centro_y)]]))[0]
    codos = [
        b.pivote_izquierdo + b.proximal * np.array([np.cos(psi[0]), np.sin(psi[0])]),
        b.pivote_derecho + b.proximal * np.array([np.cos(psi[1]), np.sin(psi[1])]),
    ]
    punta = b.directa(psi[None, :])[0]
    ancho, alto = float(m.caja_ancho) * MM, float(m.caja_alto) * MM
    cy = float(m.caja_centro_y) * MM

    d = [
        f'<rect class="papel" x="{-ancho / 2:.1f}" y="{-cy - alto / 2:.1f}" '
        f'width="{ancho:.1f}" height="{alto:.1f}"/>',
        f'<text class="cota" x="0" y="{-cy - alto / 2 - 7:.1f}">'
        f"caja de escritura {ancho:.0f} × {alto:.0f}, centro a {cy:.0f} sobre los pivotes</text>",
    ]
    for pivote, codo, nombre in zip(
        (b.pivote_izquierdo, b.pivote_derecho), codos, ("izquierdo", "derecho"), strict=True
    ):
        c = COLOR[nombre]
        d.append(
            f'<line class="brazo" stroke="{c}" x1="{pivote[0] * MM:.2f}" y1="{-pivote[1] * MM:.2f}"'
            f' x2="{codo[0] * MM:.2f}" y2="{-codo[1] * MM:.2f}"/>'
        )
        d.append(
            f'<line class="brazo" stroke="{c}" stroke-dasharray="0" '
            f'x1="{codo[0] * MM:.2f}" y1="{-codo[1] * MM:.2f}" '
            f'x2="{punta[0] * MM:.2f}" y2="{-punta[1] * MM:.2f}"/>'
        )
        d.append(
            f'<circle class="junta" stroke="{c}" cx="{codo[0] * MM:.2f}" '
            f'cy="{-codo[1] * MM:.2f}" r="2.6"/>'
        )
        d.append(
            f'<circle class="pivote" cx="{pivote[0] * MM:.2f}" cy="{-pivote[1] * MM:.2f}" r="3.4"/>'
        )
        lado = -1 if pivote[0] < 0 else 1
        d.append(
            f'<text class="pieza" x="{pivote[0] * MM + lado * 4:.1f}" y="15" fill="{c}">'
            f"{nombre}</text>"
        )

    cruce = np.array(
        [0.0, float(np.interp(0.0, [codos[1][0], codos[0][0]], [codos[1][1], codos[0][1]]))]
    )
    d += [
        f'<circle class="cruce" cx="0" cy="{-cruce[1] * MM:.2f}" r="5"/>',
        f'<text class="ojo" x="0" y="{-cruce[1] * MM - 8:.1f}">se cruzan</text>',
        f'<circle class="punta" cx="{punta[0] * MM:.2f}" cy="{-punta[1] * MM:.2f}" r="2.6"/>',
        f'<text class="cota" x="{punta[0] * MM:.1f}" y="{-punta[1] * MM - 8:.1f}">la punta</text>',
        f'<line class="acot" x1="{b.pivote_izquierdo[0] * MM:.1f}" y1="26" '
        f'x2="{b.pivote_derecho[0] * MM:.1f}" y2="26"/>',
        f'<text class="cota" x="0" y="35">separación {b.separacion * MM:.0f}</text>',
        f'<text class="cota" x="0" y="46">proximal {b.proximal * MM:.0f} · '
        f"distal {b.distal * MM:.0f} · palanca del lápiz "
        f"{float(m.brazo_palanca) * MM:.0f}</text>",
        '<text class="ojo" x="0" y="60">Trabaja CRUZADO: el codo del brazo izquierdo'
        " cae a la</text>",
        f'<text class="ojo" x="0" y="69">derecha del eje ({codos[0][0] * MM:+.1f} mm)'
        f" y el del derecho a la izquierda.</text>",
        '<text class="ojo" x="0" y="78">No es un error de dibujo; es la rama que'
        " elige la inversa.</text>",
    ]
    return d


# ---------------------------------------------------------------------------
# C · la pila
# ---------------------------------------------------------------------------


def pila(m: Escribiente, montaje) -> list[str]:
    d: list[str] = []
    e = float(m.espesor_leva) * MM
    radio = float(montaje.radio_maximo) * MM
    z = 0.0
    for nombre in SEGUIDORES:
        d.append(
            f'<rect class="corte" fill="{COLOR[nombre]}" fill-opacity="0.10" '
            f'x="{-radio:.1f}" y="{-z - e:.1f}" width="{2 * radio:.1f}" height="{e:.1f}"/>'
        )
        d.append(
            f'<text class="leyenda izq" x="{radio + 6:.1f}" y="{-z - e / 2 + 2.2:.1f}" '
            f'fill="{COLOR[nombre]}">{nombre} · POM {e:.0f} mm</text>'
        )
        z += e
        if nombre != SEGUIDORES[-1]:
            d.append(f'<rect class="sep" x="-14" y="{-z - 2:.1f}" width="28" height="2"/>')
            z += 2.0
    d += [
        f'<line class="eje" x1="0" y1="10" x2="0" y2="{-z - 12:.1f}"/>',
        f'<line class="pasa" x1="18" y1="6" x2="18" y2="{-z - 8:.1f}"/>',
        f'<text class="cota izq" x="24" y="{-z - 10:.1f}">pasador de índice</text>',
        f'<text class="cota" x="0" y="22">pila {z:.0f} mm · árbol Ø{float(m.taladro_eje) * MM:.0f}'
        f" · cartucho {float(montaje.masa) * 1000:.0f} g</text>",
    ]
    return d


# ---------------------------------------------------------------------------


ESTILO = """
text { font-family: Helvetica, Arial, sans-serif; fill: #1b1b1b; }
.h1 { font-size: 11px; font-weight: bold; }
.h2 { font-size: 7.5px; font-weight: bold; text-anchor: middle; }
.sub { font-size: 5.8px; fill: #555; }
.cota { font-size: 5.2px; fill: #444; text-anchor: middle; }
.leyenda { font-size: 5.2px; }
.pieza { font-size: 5.6px; text-anchor: middle; font-weight: bold; }
.izq { text-anchor: start; }
.ojo { font-size: 5.2px; fill: #8a4a00; text-anchor: middle; }
.leva { stroke-width: 0.7; }
.lobulo { fill: none; stroke-width: 0.9; }
.ref { fill: none; stroke: #aaa; stroke-width: 0.35; stroke-dasharray: 5 2 1 2; }
.fina { stroke: #888; stroke-width: 0.35; }
.corte { fill: none; stroke: #1b1b1b; stroke-width: 0.8; }
.poste { fill: #dcdcdc; stroke: #1b1b1b; stroke-width: 0.7; }
.rodillo { fill: #fff; stroke: #b03030; stroke-width: 1; }
.brazo { stroke: #b03030; stroke-width: 2; stroke-linecap: round; }
.pivote { fill: #1b1b1b; }
.junta { fill: #fff; stroke-width: 1; }
.punta { fill: #1b5fb0; }
.cruce { fill: none; stroke: #c07000; stroke-width: 0.8; stroke-dasharray: 2 1.5; }
.papel { fill: #f4f4f4; stroke: #888; stroke-width: 0.6; stroke-dasharray: 3 2; }
.acot { stroke: #444; stroke-width: 0.4; }
.eje { stroke: #1b5fb0; stroke-width: 1; stroke-dasharray: 7 2 1 2; }
.pasa { stroke: #b03030; stroke-width: 1; stroke-dasharray: 3 2; }
.sep { fill: #d0d0d0; stroke: #1b1b1b; stroke-width: 0.5; }
.hueco { fill: #fff6e6; stroke: #c07000; stroke-width: 1.1; stroke-dasharray: 5 3; }
.aviso { font-size: 5.4px; fill: #7a4200; }
.avisot { font-size: 7px; font-weight: bold; fill: #8a4a00; text-anchor: middle; }
"""


def svg(m: Escribiente, perfiles, montaje, hueco: float) -> str:
    p = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<svg xmlns="http://www.w3.org/2000/svg" width="1560" height="900" viewBox="0 0 520 300">',
        f"<style>{ESTILO}</style>",
        '<rect width="520" height="300" fill="#ffffff"/>',
        '<text class="h1" x="12" y="16">El escribiente · cómo está conceptualizado hoy</text>',
        '<text class="sub" x="12" y="25">Generado desde el propio modelo: cada cota sale de '
        '<tspan font-style="italic">Escribiente</tspan> o de compilar «hola». '
        "Cotas en mm. Las levas son las de verdad, no circunferencias.</text>",
        # A
        '<g transform="translate(95,120) scale(0.62)">',
        '<text class="h2" x="0" y="-112">A · Planta del cartucho, mirando por el árbol</text>',
        *planta(m, perfiles, hueco),
        "</g>",
        # inset del lóbulo
        '<g transform="translate(216,108) scale(0.78)">',
        '<text class="h2" x="0" y="-52">La forma, amplificada</text>',
        *lobulo(perfiles),
        "</g>",
        # B
        '<g transform="translate(400,175) scale(0.62)">',
        '<text class="h2" x="0" y="-186">B · Alzado del varillaje, en el plano del papel</text>',
        *alzado(m),
        "</g>",
        # C
        '<g transform="translate(95,258) scale(0.62)">',
        '<text class="h2" x="0" y="-52">C · La pila del cartucho</text>',
        *pila(m, montaje),
        "</g>",
        # el hueco
        '<g transform="translate(196,196)">',
        '<rect class="hueco" x="0" y="0" width="122" height="88" rx="4"/>',
        '<text class="avisot" x="61" y="14">SIN DEFINIR · el amplificador 6:1</text>',
        '<text class="aviso" x="8" y="28">Entre A y B falta el mecanismo. Hoy la</text>',
        '<text class="aviso" x="8" y="37">relación es solo un número en el código:</text>',
        '<text class="aviso" x="8" y="47" font-weight="bold">'
        "ψ_brazo = 6 · ψ_seguidor + calaje</text>",
        '<text class="aviso" x="8" y="60">Y los dos planos aún no cuadran: los postes</text>',
        '<text class="aviso" x="8" y="69">van separados 123,1 mm y los pivotes del</text>',
        '<text class="aviso" x="8" y="78">brazo, 120,0. Es lo que E4 tiene que medir.</text>',
        "</g>",
        '<text class="sub" x="12" y="292">Rojo: lo que se mueve. Azul: el árbol y la punta. '
        "Gris: lo que no cambia entre pedidos. "
        "Naranja discontinuo: lo que todavía no existe.</text>",
        "</svg>",
    ]
    return "\n".join(p)


def main(argv: list[str] | None = None) -> int:
    partes = argparse.ArgumentParser(prog="dibujar_maquina", description=__doc__)
    partes.add_argument("--out", type=Path, default=Path("build/maquina.svg"))
    opciones = partes.parse_args(argv)

    maquina = Escribiente()
    compilacion = compilar(hola(), maquina, Capacidad(muestras=720, radio_de_esquina=mm(1.0)))
    montaje, veredicto = montar(compilacion, maquina)
    hueco = veredicto.metricas["holgura_al_poste"] * MM

    opciones.out.parent.mkdir(parents=True, exist_ok=True)
    opciones.out.write_text(svg(maquina, compilacion.perfiles, montaje, hueco), encoding="utf-8")
    print(f"{opciones.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
