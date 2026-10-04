"""El plano de conjunto: dónde va cada pieza, en planta y en alzado.

    uv run python scripts/dibujar_conjunto.py --out build/conjunto.svg

Es la lámina de la que cuelga el dossier de montaje, y como todas las de
este repo **se genera desde `docs/contratos.json`**: si una cota se mueve,
el conjunto se mueve con ella. Un plano de conjunto dibujado a mano es el
que primero miente, porque es el que menos se vuelve a mirar.

Dos vistas y una sola escala:

- **Planta**, en el marco del cinco barras, que es el de la base: el árbol
  queda sobre el eje de simetría y todo sale por parejas.
- **Alzado**, mirando desde la izquierda, con la pila vertical entera: de la
  tabla de nogal a la manivela.

Y un despiece con globos, que es lo que convierte un dibujo en una lista de
lo que hay que tener encima de la mesa antes de empezar.
"""

from __future__ import annotations

import argparse
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from emit.montaje import alturas
from emit.plataforma import LISTADO, contrato_mm

RAIZ = Path(__file__).resolve().parent.parent


def planta(c: dict[str, float]) -> dict[str, tuple[float, float]]:
    """Dónde cae cada cosa en el marco del cinco barras."""
    giro = c["brazo_origen_giro"]
    arbol = (
        math.cos(giro) * -c["brazo_origen_x"] + math.sin(giro) * -c["brazo_origen_y"],
        -math.sin(giro) * -c["brazo_origen_x"] + math.cos(giro) * -c["brazo_origen_y"],
    )
    sitios = {"arbol": arbol}
    for i in range(3):
        t = c["poste_reparto"] * i - giro
        sitios[f"poste{i + 1}"] = (
            arbol[0] + c["poste_radio_al_arbol"] * math.cos(t),
            arbol[1] + c["poste_radio_al_arbol"] * math.sin(t),
        )
    sitios["pivote_izq"] = (-c["brazo_separacion"] / 2, 0.0)
    sitios["pivote_der"] = (c["brazo_separacion"] / 2, 0.0)
    t = c["platina_manivela_angulo"] - giro
    sitios["manivela"] = (
        arbol[0] + c["reductor_entre_ejes"] * math.cos(t),
        arbol[1] + c["reductor_entre_ejes"] * math.sin(t),
    )
    sitios["punta"] = (0.0, c["caja_centro_y"])
    sitios["tirante"] = (c["tirante_x"], c["tirante_y"])
    sitios["balancin"] = (c["balancin_eje_x"], sitios["poste3"][1] - c["brazo_seguidor"])
    return sitios


ESTILO = """
text{font-family:'DejaVu Sans',Helvetica,sans-serif;fill:#1b1b1b}
.h1{font-size:15px;font-weight:700}.h2{font-size:10px;font-weight:700}
.sub{font-size:7.6px;fill:#555}.leg{font-size:7.4px}.legb{font-size:7.4px;font-weight:700}
.nt{font-size:6.6px;fill:#fff;font-weight:700}
.cab{font-size:7.4px;font-weight:700;fill:#555}
line,path{fill:none;stroke:#1b1b1b;stroke-width:0.8}
.eje{stroke:#1b5fb0;stroke-width:0.45;stroke-dasharray:7 2 1.2 2}
.oculta{stroke:#1b1b1b;stroke-width:0.45;stroke-dasharray:2.5 1.8}
.movil{stroke:#b03030;stroke-width:1.9;stroke-linecap:round}
.lapiz{stroke:#1b5fb0;stroke-width:2.1;stroke-linecap:round}
.guia{stroke:#aaa;stroke-width:0.4}
rect,circle{stroke:#1b1b1b;stroke-width:0.8;fill:#fff}
.mad{fill:#e9dcc6}.pla{fill:#f2ead8}.pom{fill:#c9c9c9}.lat{fill:#e4d9a8}
.leva{fill:#464646}.papel{fill:#fcfcfc}.vacio{fill:none}
.globo{fill:#b03030;stroke:none}
"""


class Lamina:
    def __init__(self) -> None:
        self.d: list[str] = []
        self.globos: list[tuple[int, str]] = []

    def add(self, s: str) -> None:
        self.d.append(s)

    def rect(self, x, y, w, h, cl="vacio"):
        self.add(f'<rect class="{cl}" x="{x:.2f}" y="{y:.2f}" width="{w:.2f}" height="{h:.2f}"/>')

    def circ(self, x, y, r, cl="vacio"):
        self.add(f'<circle class="{cl}" cx="{x:.2f}" cy="{y:.2f}" r="{r:.2f}"/>')

    def ln(self, x1, y1, x2, y2, cl="g"):
        self.add(f'<line class="{cl}" x1="{x1:.2f}" y1="{y1:.2f}" x2="{x2:.2f}" y2="{y2:.2f}"/>')

    def globo(self, n, x, y, dx, dy, texto):
        self.ln(x, y, x + dx, y + dy, "guia")
        self.add(f'<circle class="globo" cx="{x + dx:.2f}" cy="{y + dy:.2f}" r="6.2"/>')
        self.add(
            f'<text class="nt" x="{x + dx:.2f}" y="{y + dy + 2.4:.2f}" '
            f'style="text-anchor:middle">{n}</text>'
        )
        self.globos.append((n, texto))


def dibujar(c: dict[str, float]) -> str:
    z, s = alturas(c), planta(c)
    lam = Lamina()
    k = 1.0
    arbol = s["arbol"]
    rp, rl = c["platina_diametro"] / 2, c["radio_base"] + 1.0

    # ------------------------------------------------------------------ planta
    px0, py0 = 190.0, 335.0

    def en_planta(x, y):
        return px0 + x * k, py0 - y * k

    lam.add(f'<text class="h2" x="{px0 - 120:.0f}" y="{py0 - 190:.0f}">PLANTA</text>')
    lam.add(
        f'<text class="sub" x="{px0 - 120:.0f}" y="{py0 - 180:.0f}">'
        "marco del cinco barras · el papel ARRIBA, hacia quien escribe</text>"
    )
    b0 = en_planta(-c["base_ancho"] / 2, arbol[1] - c["base_arbol_al_borde_trasero"])
    b1 = en_planta(
        c["base_ancho"] / 2, arbol[1] - c["base_arbol_al_borde_trasero"] + c["base_fondo"]
    )
    lam.rect(b0[0], b1[1], b1[0] - b0[0], b0[1] - b1[1], "mad")
    m0 = en_planta(-c["mesa_ancho"] / 2, c["caja_centro_y"] - c["mesa_fondo"] / 2)
    m1 = en_planta(c["mesa_ancho"] / 2, c["caja_centro_y"] + c["mesa_fondo"] / 2)
    lam.rect(m0[0], m1[1], m1[0] - m0[0], m0[1] - m1[1], "lat")
    t0 = en_planta(-c["papel_ancho"] / 2, c["caja_centro_y"] - c["papel_fondo"] / 2)
    t1 = en_planta(c["papel_ancho"] / 2, c["caja_centro_y"] + c["papel_fondo"] / 2)
    lam.rect(t0[0], t1[1], t1[0] - t0[0], t0[1] - t1[1], "papel")
    k0 = en_planta(-c["caja_ancho"] / 2, c["caja_centro_y"] - c["caja_alto"] / 2)
    k1 = en_planta(c["caja_ancho"] / 2, c["caja_centro_y"] + c["caja_alto"] / 2)
    lam.add(
        f'<rect class="oculta" fill="none" x="{k0[0]:.2f}" y="{k1[1]:.2f}" '
        f'width="{k1[0] - k0[0]:.2f}" height="{k0[1] - k1[1]:.2f}"/>'
    )
    lam.circ(*en_planta(*arbol), rp * k, "pla")
    lam.circ(*en_planta(*arbol), rl * k, "leva")
    # El volante y los seguidores están POR ENCIMA de las levas, así que se
    # dibujan después: al revés, el disco de la leva se los comía y el plano
    # decía que no existen.
    lam.circ(*en_planta(*s["manivela"]), c["volante_diametro"] / 2 * k, "lat")
    for i in (1, 2, 3):
        pz = s[f"poste{i}"]
        lam.circ(*en_planta(*pz), c["poste_obstaculo_diametro"] / 2 * k, "pom")
        ang = math.atan2(arbol[1] - pz[1], arbol[0] - pz[0])
        rod = (
            pz[0] + c["brazo_seguidor"] * math.cos(ang),
            pz[1] + c["brazo_seguidor"] * math.sin(ang),
        )
        lam.ln(*en_planta(*pz), *en_planta(*rod), "movil")
        lam.circ(*en_planta(*rod), c["rodillo_radio"] * k, "vacio")
    for lado in ("izq", "der"):
        piv = s[f"pivote_{lado}"]
        lam.circ(*en_planta(*piv), c["brazo_cubo_diametro"] / 2 * k, "lat")
    psi = _codos(c, s)
    for codo in psi:
        lam.ln(*en_planta(*codo[0]), *en_planta(*codo[1]), "movil")
        lam.ln(*en_planta(*codo[1]), *en_planta(*s["punta"]), "movil")
        lam.circ(*en_planta(*codo[1]), 2.0, "vacio")
    lam.circ(*en_planta(*s["punta"]), 2.6, "lapiz")
    lam.ln(
        *en_planta(0.0, s["poste3"][1] - c["levantamiento_pasador_al_pivote"]),
        *en_planta(c["balancin_eje_x"], s["poste3"][1] - c["levantamiento_pasador_al_pivote"]),
        "movil",
    )
    lam.ln(
        *en_planta(c["balancin_eje_x"], s["poste3"][1] - c["levantamiento_pasador_al_pivote"]),
        *en_planta(c["balancin_eje_x"], c["tirante_y"]),
        "movil",
    )
    lam.ln(
        *en_planta(c["balancin_eje_x"], c["tirante_y"]),
        *en_planta(c["tirante_x"], c["tirante_y"]),
        "movil",
    )
    lam.circ(*en_planta(c["tirante_x"], c["tirante_y"]), c["tirante_diametro"] / 2 * k + 0.6, "lat")
    lam.ln(*en_planta(0, arbol[1] - rp - 12), *en_planta(0, c["caja_centro_y"] + 60), "eje")
    return _alzado_y_leyenda(lam, c, z, s, k, arbol)


def _codos(c, s):
    """Los dos codos del cinco barras con la punta en el centro de la caja."""
    import numpy as np

    from compile.escribiente import Escribiente

    b = Escribiente().brazo
    psi = b.inversa(np.array([[0.0, c["caja_centro_y"] / 1000.0]]))[0]
    salida = []
    for i, lado in enumerate(("izq", "der")):
        piv = s[f"pivote_{lado}"]
        codo = (
            piv[0] + c["brazo_proximal"] * math.cos(psi[i]),
            piv[1] + c["brazo_proximal"] * math.sin(psi[i]),
        )
        salida.append((piv, codo))
    return salida


def _alzado_y_leyenda(lam, c, z, s, k, arbol):
    ax0, ay0 = 540.0, 380.0

    def en_alzado(y, zz):
        return ax0 + y * k, ay0 - zz * k

    lam.add(f'<text class="h2" x="{ax0 - 150:.0f}" y="{ay0 - 232:.0f}">ALZADO</text>')
    lam.add(
        f'<text class="sub" x="{ax0 - 150:.0f}" y="{ay0 - 222:.0f}">'
        "mismo eje Y y misma escala que la planta · el papel a la derecha</text>"
    )

    def banda(y0, y1, zz, cl, ancho_extra=0.0):
        a, b = en_alzado(y0 - ancho_extra, zz[1]), en_alzado(y1 + ancho_extra, zz[0])
        lam.rect(a[0], a[1], b[0] - a[0], b[1] - a[1], cl)

    trasero = arbol[1] - c["base_arbol_al_borde_trasero"]
    banda(trasero, trasero + c["base_fondo"], z["base"], "mad")
    banda(arbol[1] - rp_(c), arbol[1] + rp_(c), z["plato1"], "pla")
    banda(arbol[1] - rp_(c), arbol[1] + rp_(c), z["plato2"], "pla")
    banda(arbol[1] - rp_(c), arbol[1] + rp_(c), z["plato3"], "pla")
    for i in range(3):
        zz = z["levas"][0] + i * 7.0
        banda(arbol[1] - c["radio_base"], arbol[1] + c["radio_base"], (zz, zz + 5.0), "leva")
    banda(arbol[1] - 20, s["poste3"][1], z["seguidores"], "pom")
    banda(
        s["manivela"][1] - c["volante_diametro"] / 2,
        s["manivela"][1] + c["volante_diametro"] / 2,
        (z["bahia"][0] + 7, z["bahia"][0] + 13),
        "lat",
    )
    banda(
        c["caja_centro_y"] - c["mesa_fondo"] / 2,
        c["caja_centro_y"] + c["mesa_fondo"] / 2,
        z["mesa"],
        "lat",
    )
    # el árbol y los postes, de parte a parte
    for yy, z0, z1, w in (
        (arbol[1], z["plato1"][0] - 4, z["plato3"][1] + 6, c["eje_diametro"]),
        (s["poste3"][1], z["poste"][0], z["poste"][1], c["poste_eje_diametro"]),
        (s["manivela"][1], z["plato2"][0], z["plato3"][1] + 26, c["brazo_eje_diametro"]),
    ):
        a, b = en_alzado(yy - w / 2, z1), en_alzado(yy + w / 2, z0)
        lam.rect(a[0], a[1], b[0] - a[0], b[1] - a[1], "lat")
    # el varillaje y el lápiz
    zb = z["plato1"][0] - 5.0
    lam.ln(*en_alzado(arbol[1], zb), *en_alzado(c["caja_centro_y"], zb), "movil")
    lam.ln(
        *en_alzado(c["caja_centro_y"], zb), *en_alzado(c["caja_centro_y"], z["mesa"][1]), "lapiz"
    )
    # la cadena del levantamiento
    zbal = z["balancin"][0]
    lam.ln(
        *en_alzado(s["poste3"][1] - c["levantamiento_pasador_al_pivote"], z["seguidores"][1]),
        *en_alzado(c["tirante_y"], zbal),
        "movil",
    )
    lam.ln(*en_alzado(c["tirante_y"], zbal), *en_alzado(c["tirante_y"], z["mesa"][0]), "movil")
    # la manivela
    lam.ln(
        *en_alzado(s["manivela"][1], z["plato3"][1] + 20),
        *en_alzado(s["manivela"][1] + c["manivela_entre_centros"], z["plato3"][1] + 20),
        "movil",
    )

    etiquetas = [
        (1, "base", *en_alzado(trasero + 30, z["base"][0] / 2), -26, 20),
        (2, "platina_levas", *en_alzado(arbol[1] - rp_(c) + 14, z["plato1"][0] + 4.5), -34, 16),
        (3, "seguidor", *en_alzado(arbol[1] - 14, z["seguidores"][0] + 2.5), -44, -14),
        (4, "sector", *en_alzado(s["poste3"][1] - 26, z["sector"][0] + 2.5), 16, -46),
        (5, "balancin", *en_alzado(c["tirante_y"] - 30, zbal), 34, -32),
        (6, "palanca_lapiz", *en_alzado(c["tirante_y"], zbal), 54, -14),
        (7, "volante", *en_alzado(s["manivela"][1], z["bahia"][0] + 10), -52, 10),
        (8, "manivela", *en_alzado(s["manivela"][1] + 70, z["plato3"][1] + 20), 30, 14),
        (9, "eje_pivote", *en_alzado(arbol[1] + 34, z["plato1"][1]), 30, -38),
        (10, "mordaza", *en_alzado(s["poste3"][1] - 44, z["sector"][1]), -16, -58),
    ]
    for n, pieza, px, py, dx, dy in etiquetas:
        lam.globo(n, px, py, dx, dy, pieza)
    return lam


def rp_(c):
    return c["platina_diametro"] / 2


def despiece() -> list[tuple[int, str, int, str, str]]:
    """El despiece, en el orden en que se monta: de abajo arriba.

    Sale de `LISTADO`, que es de donde salen también las hojas de pieza, así
    que una pieza nueva aparece aquí el mismo día. Escrito a mano se
    quedaría una fuera, y la que falta en un despiece es justo la que no
    está encima de la mesa cuando hace falta.
    """
    orden = [
        "base",
        "platina_levas",
        "casquillo_rueda",
        "eje_manivela",
        "eje_pivote",
        "seguidor",
        "sector",
        "tambor",
        "mordaza",
        "balancin",
        "palanca_lapiz",
        "brazo_proximal",
        "brazo_distal",
        "volante",
        "manivela",
    ]
    assert set(orden) == set(LISTADO), "el despiece y el listado se han separado"
    return [
        (i + 1, n, LISTADO[n].cantidad, LISTADO[n].material, LISTADO[n].proceso)
        for i, n in enumerate(orden)
    ]


def svg(c: dict[str, float] | None = None) -> str:
    c = contrato_mm() if c is None else c
    lam = dibujar(c)
    ancho, alto = 980.0, 620.0
    filas = despiece()
    total = sum(f[2] for f in filas)
    cab = [
        '<text class="h1" x="16" y="24">El escribiente · plano de conjunto</text>',
        '<text class="sub" x="16" y="38">Generado desde docs/contratos.json con '
        "scripts/dibujar_conjunto.py. Rojo: lo que se mueve. Azul: el lápiz y los ejes. "
        "La altura entera cuelga de base_al_plato, que sigue PENDIENTE.</text>",
        f'<text class="cab" x="706" y="72">DESPIECE · {len(filas)} piezas, {total} unidades</text>',
    ]
    y = 86.0
    for n, pieza, cant, material, proceso in filas:
        cab.append(f'<text class="legb" x="706" y="{y:.0f}">{n}</text>')
        cab.append(f'<text class="leg" x="720" y="{y:.0f}">{pieza} · ×{cant}</text>')
        cab.append(f'<text class="sub" x="728" y="{y + 8:.0f}">{material} · {proceso}</text>')
        y += 19
    cab.append(
        f'<text class="sub" x="706" y="{y + 6:.0f}">Más 14 referencias comerciales: '
        "ver docs/ficha-producto.md §2c</text>"
    )
    return (
        f'<?xml version="1.0" encoding="UTF-8"?>\n'
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{ancho * 2:.0f}" '
        f'height="{alto * 2:.0f}" viewBox="0 0 {ancho:.0f} {alto:.0f}">'
        f"<style>{ESTILO}</style>"
        f'<rect x="0" y="0" width="{ancho:.0f}" height="{alto:.0f}" fill="#fff" stroke="none"/>'
        + "".join(cab)
        + "".join(lam.d)
        + "</svg>\n"
    )


def main(argv: list[str] | None = None) -> int:
    partes = argparse.ArgumentParser(prog="dibujar_conjunto", description=__doc__)
    partes.add_argument("--out", type=Path, default=RAIZ / "build" / "conjunto.svg")
    opciones = partes.parse_args(argv)
    opciones.out.parent.mkdir(parents=True, exist_ok=True)
    opciones.out.write_text(svg(), encoding="utf-8")
    print(f"conjunto en {opciones.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
