"""Primitivas de acotación para los planos que se copian en el CAD.

Las comparten `dibujar_plano_cabestrante.py` y `dibujar_plano_brazos.py`.
Están aquí y no duplicadas en cada uno porque una cota con la flecha de un
tamaño en un plano y de otro en el siguiente se lee como si fueran dos
documentos distintos, y son el mismo juego de piezas.

No es una biblioteca de dibujo técnico: es lo justo para poner una línea de
cota, una de radio y una auxiliar. Si hiciera falta más, el sitio es un CAD.
"""

from __future__ import annotations

import json
import math
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
CONTRATOS = RAIZ / "docs" / "contratos.json"
MM = 1000.0
"""De metros a milímetros. Regla 3: el contrato está en SI y el plano en mm."""


def contrato() -> dict[str, float]:
    """Todos los valores del contrato por su nombre, en unidades SI."""
    datos = json.loads(CONTRATOS.read_text(encoding="utf-8"))
    return {v["nombre"]: float(v["valor"]) for g in datos["contratos"] for v in g["valores"]}


ESTILO = """
text{font-family:Helvetica,Arial,sans-serif;fill:#1b1b1b}
.h1{font-size:12px;font-weight:bold}
.sub{font-size:5.8px;fill:#555}
.vista{font-size:7px;font-weight:bold;text-anchor:middle}
.nota{font-size:5.2px;fill:#555;text-anchor:middle}
.notal{font-size:5.2px;fill:#555}
.aviso{font-size:5.2px;fill:#8a4a00}
.marco{fill:none;stroke:#ddd;stroke-width:0.6}
.corte{fill:#dde5ee;stroke:#1b1b1b;stroke-width:0.9}
.contorno{fill:none;stroke:#1b1b1b;stroke-width:0.9}
.cinta{fill:none;stroke:#b03030;stroke-width:1.6;stroke-linecap:round}
.eje{stroke:#1b5fb0;stroke-width:0.5;stroke-dasharray:7 2 1.2 2}
.aux{stroke:#9aa7b4;stroke-width:0.4}
.cotaln{stroke:#b03030;stroke-width:0.45}
.cotatx{font-size:5.4px;fill:#b03030;text-anchor:middle}
.cotatxi{font-size:5.4px;fill:#b03030}
.var{font-size:4.8px;fill:#1b5fb0;font-family:monospace;text-anchor:middle}
.varl{font-size:4.8px;fill:#1b5fb0;font-family:monospace}
.cotavar{font-size:4.8px;fill:#1b5fb0;font-family:monospace}
"""

FLECHA = (
    '<marker id="f" markerWidth="7" markerHeight="7" refX="6.4" refY="2.2" orient="auto">'
    '<path d="M0,0 L6.6,2.2 L0,4.4 z" fill="#b03030"/></marker>'
)


def cota_h(x0: float, x1: float, y: float, texto: str, variable: str = "") -> list[str]:
    """Cota horizontal: línea con flechas a los dos lados y el número encima."""
    d = [
        f'<line class="cotaln" marker-start="url(#f)" marker-end="url(#f)" '
        f'x1="{x0:.2f}" y1="{y:.2f}" x2="{x1:.2f}" y2="{y:.2f}"/>',
        f'<text class="cotatx" x="{(x0 + x1) / 2:.2f}" y="{y - 2.5:.2f}">{texto}</text>',
    ]
    if variable:
        d.append(f'<text class="var" x="{(x0 + x1) / 2:.2f}" y="{y + 6:.2f}">{variable}</text>')
    return d


def cota_v(y0: float, y1: float, x: float, texto: str, variable: str = "") -> list[str]:
    """Cota vertical, con el número girado para que se lea de abajo arriba."""
    ym = (y0 + y1) / 2
    d = [
        f'<line class="cotaln" marker-start="url(#f)" marker-end="url(#f)" '
        f'x1="{x:.2f}" y1="{y0:.2f}" x2="{x:.2f}" y2="{y1:.2f}"/>',
        f'<text class="cotatx" x="{x - 3:.2f}" y="{ym:.2f}" '
        f'transform="rotate(-90 {x - 3:.2f} {ym:.2f})">{texto}</text>',
    ]
    if variable:
        d.append(
            f'<text class="var" x="{x + 4:.2f}" y="{ym:.2f}" '
            f'transform="rotate(-90 {x + 4:.2f} {ym:.2f})">{variable}</text>'
        )
    return d


def auxiliar(x0: float, y0: float, x1: float, y1: float) -> str:
    return f'<line class="aux" x1="{x0:.2f}" y1="{y0:.2f}" x2="{x1:.2f}" y2="{y1:.2f}"/>'


def radial(cx: float, cy: float, r: float, ang: float, texto: str, variable: str = "") -> list[str]:
    """Cota de radio: una flecha desde el centro hasta el arco.

    `variable` va debajo del número porque una cota circular sin el nombre al
    lado invita a teclear el radio en un campo de diámetro, que es el error
    documentado en CLAUDE.md: la mitad, y sin un solo aviso.
    """
    x1, y1 = cx + r * math.cos(ang), cy + r * math.sin(ang)
    xt, yt = cx + (r + 9) * math.cos(ang), cy + (r + 9) * math.sin(ang)
    d = [
        f'<line class="cotaln" marker-end="url(#f)" x1="{cx:.2f}" y1="{cy:.2f}" '
        f'x2="{x1:.2f}" y2="{y1:.2f}"/>',
        f'<text class="cotatx" x="{xt:.2f}" y="{yt:.2f}">{texto}</text>',
    ]
    if variable:
        d.append(
            f'<text class="cotavar" x="{xt:.2f}" y="{yt + 5.4:.2f}" '
            f'text-anchor="middle">{variable}</text>'
        )
    return d


def arco(cx: float, cy: float, r: float, a0: float, a1: float) -> str:
    x0, y0 = cx + r * math.cos(a0), cy + r * math.sin(a0)
    x1, y1 = cx + r * math.cos(a1), cy + r * math.sin(a1)
    grande = 1 if (a1 - a0) % (2 * math.pi) > math.pi else 0
    return f"M {x0:.2f},{y0:.2f} A {r:.2f},{r:.2f} 0 {grande} 1 {x1:.2f},{y1:.2f}"


__all__ = [
    "CONTRATOS",
    "ESTILO",
    "FLECHA",
    "MM",
    "RAIZ",
    "arco",
    "auxiliar",
    "contrato",
    "cota_h",
    "cota_v",
    "radial",
]
