"""Un boceto acotado por cada pieza comercial, sacado de su ficha.

    uv run python scripts/dibujar_piezas.py --out build/piezas.svg

Sirve para dibujarlas en el CAD sin tener que abrir catorce JSON: cada panel
lleva la sección, el nombre completo de cada variable y qué mide.

**El perfil que dibuja es el mismo que levanta `emit/catalogo.py`.** No puede
ser «parecido»: si el boceto enseñara una forma y el STEP otra, quien dibuje
en el CAD haría una tercera. Un test comprueba que la caja del perfil coincide
con la envolvente del sólido, que es lo que ata las dos representaciones.

Las piezas se dibujan como **envolventes**, igual que el catálogo: el
engranaje sin dientes, el muelle como el cilindro que ocupa, el rodamiento
como un anillo macizo. Para saber si caben eso basta; para pesarlos no sirve,
y el panel lo dice donde toca.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.comercial import FamiliaComercial, PiezaComercial
from core.errors import FichaIncompleta
from core.solido import densidad_de
from emit.catalogo import LARGO_POR_DEFECTO, cargar
from scripts.exportar_para_cad import mapa_de

MM = 1000.0
POR_DEFECTO = LARGO_POR_DEFECTO * MM
"""Los mm que el catálogo pone cuando una ficha no declara longitud. Aquí
hace falta el mismo número: si el boceto usara otro, el dibujo y el STEP
medirían distinto y nadie sabría cuál mirar."""

SIN_MASA_FIABLE = {
    "muelle_seguidor": "el cilindro que ocupa, no el alambre",
    "rodamiento_arbol": "anillo macizo, sin bolas ni pistas",
    "rodillo_seguidor": "anillo macizo, sin bolas ni pistas",
    "pinon_reductor": "disco sin dientes",
    "rueda_reductor": "disco sin dientes",
    "pinon_amplificador": "disco sin dientes",
    "rueda_amplificador": "disco sin dientes",
    "portaminas": "compuesto: se pesa, no se calcula",
    "anillo_lapiz": "sin la ranura ni el prisionero",
}
"""Piezas cuya envolvente **no** es el sólido real, y por qué. Asignarles
material en el CAD da una masa que parece una medida y no lo es."""


def _mm(pieza: PiezaComercial, nombre: str, por_defecto: float | None = None) -> float:
    try:
        return float(pieza.cota(nombre).valor) * MM
    except KeyError:
        if por_defecto is None:
            raise FichaIncompleta(f"{pieza.nombre} necesita '{nombre}'") from None
        return por_defecto


def perfil_de(pieza: PiezaComercial) -> tuple[list[tuple[float, float]], list[str]]:
    """Media sección (r, z) en mm, y los nombres de cota que la definen.

    Sigue rama por rama a `emit.catalogo.solido_de`: son la misma forma vista
    de dos maneras, y tienen que decir lo mismo.
    """
    f = pieza.familia

    if f in (FamiliaComercial.RODAMIENTO, FamiliaComercial.SEPARADOR):
        alto = _mm(pieza, "ancho", None) if _tiene(pieza, "ancho") else _mm(pieza, "espesor")
        ri, re = _mm(pieza, "agujero") / 2, _mm(pieza, "exterior") / 2
        usadas = ["agujero", "exterior", "ancho" if _tiene(pieza, "ancho") else "espesor"]
        return [(ri, 0), (re, 0), (re, alto), (ri, alto)], usadas

    if f is FamiliaComercial.CASQUILLO:
        ri = _mm(pieza, "agujero") / 2
        re, rv = _mm(pieza, "exterior") / 2, _mm(pieza, "valona") / 2
        largo, ev = _mm(pieza, "longitud", POR_DEFECTO), _mm(pieza, "espesor_valona", 1.0)
        return (
            [(ri, 0), (rv, 0), (rv, ev), (re, ev), (re, largo), (ri, largo)],
            ["agujero", "exterior", "valona", "longitud", "espesor_valona"],
        )

    if f in (FamiliaComercial.EJE, FamiliaComercial.PASADOR):
        r, largo = _mm(pieza, "diametro") / 2, _mm(pieza, "longitud", POR_DEFECTO)
        return [(0, 0), (r, 0), (r, largo), (0, largo)], ["diametro", "longitud"]

    if f is FamiliaComercial.MUELLE:
        r, largo = _mm(pieza, "exterior") / 2, _mm(pieza, "longitud_libre", POR_DEFECTO)
        return [(0, 0), (r, 0), (r, largo), (0, largo)], ["exterior", "longitud_libre"]

    if f is FamiliaComercial.ENGRANAJE:
        ri, re = _mm(pieza, "agujero") / 2, _mm(pieza, "exterior") / 2
        alto = _mm(pieza, "ancho", 4.0)
        return [(ri, 0), (re, 0), (re, alto), (ri, alto)], ["agujero", "exterior", "ancho"]

    if f is FamiliaComercial.INSTRUMENTO:
        r, largo = _mm(pieza, "cuerpo") / 2, _mm(pieza, "longitud", POR_DEFECTO)
        return [(0, 0), (r, 0), (r, largo), (0, largo)], ["cuerpo", "longitud"]

    if f is FamiliaComercial.FIJACION:
        if _tiene(pieza, "metrica"):
            metrica = _mm(pieza, "metrica")
            rv, largo = metrica / 2, _mm(pieza, "longitud", POR_DEFECTO)
            rc, hc = _mm(pieza, "cabeza", metrica * 1.8) / 2, metrica
            return (
                [(0, 0), (rv, 0), (rv, largo), (rc, largo), (rc, largo + hc), (0, largo + hc)],
                ["metrica", "cabeza", "longitud"],
            )
        ri, re, alto = _mm(pieza, "agujero") / 2, _mm(pieza, "exterior") / 2, _mm(pieza, "ancho")
        return [(ri, 0), (re, 0), (re, alto), (ri, alto)], ["agujero", "exterior", "ancho"]

    ancho, largo = _mm(pieza, "ancho", 100.0), _mm(pieza, "espesor")
    return [(0, 0), (ancho / 2, 0), (ancho / 2, largo), (0, largo)], ["ancho", "largo", "espesor"]


def _tiene(pieza: PiezaComercial, nombre: str) -> bool:
    try:
        pieza.cota(nombre)
    except KeyError:
        return False
    return True


def filas_de(pieza: PiezaComercial) -> list[tuple[str, str]]:
    """Lo que se rellena en el CAD: nombre entero de la variable y su valor.

    **Con su prefijo, que no es siempre el mismo.** Un archivo importado en
    Onshape crea un mapa con un único factor de conversión para todas sus
    filas, así que las longitudes van a `#pieza` con factor `1 mm` y los
    recuentos a `#pieza_num` sin unidad. Escribir `#pieza.…_dientes` da una
    variable que no existe; escribirla en el mapa de milímetros daría veinte
    milímetros de dientes. El reparto lo declara `MAPAS`, y esta hoja lo lee
    de ahí para no poder contradecirlo.

    **Y una cota que la ficha no trae no se rotula como variable.** La
    tornillería no declara `longitud`: el perfil la dibuja con un valor por
    defecto para que la sección tenga forma, pero no hay fila en el CSV y
    `#pieza.tornilleria_longitud` no existe. Se rotula el hueco.

    No son solo las cotas que dibuja el perfil. El número de dientes **no
    está en la ficha** —la ficha guarda el diámetro exterior, que es lo que
    se mide— y en cambio es exactamente lo que pide el FeatureScript de
    engranaje. Faltaba en la primera hoja y salió un piñón de 25 dientes en
    vez de 20: engrana a 2,4 en lugar de 3 y pide 29,75 mm de entre-ejes en
    vez de 28. La hoja tiene que llevar lo que se teclea, no lo que se mide.
    """
    _, usadas = perfil_de(pieza)
    # Las críticas que el perfil no dibuja van igual. El módulo de un
    # engranaje es una de ellas: la envolvente es un disco liso, así que no
    # aparece en el dibujo, y sin embargo es el primer campo del
    # FeatureScript. Lo mismo la mina del portaminas.
    nombres = usadas + [c.nombre for c in pieza.criticas if c.nombre not in usadas]
    longitudes = mapa_de("piezas_cota")
    filas = []
    for n in nombres:
        if _tiene(pieza, n):
            filas.append((f"#{longitudes}.{pieza.nombre}_{n}", f"{_mm(pieza, n, 0.0):g}"))
            continue
        # El perfil la dibuja con un valor por defecto, pero en la ficha no
        # está y por tanto tampoco en el CSV: **esa variable no existe**.
        # Imprimir su nombre manda a teclear algo que el CAD no reconoce, y
        # es el mismo fallo que los dientes con otra cara. Se rotula el
        # hueco, con el valor que el dibujo usa marcado con asterisco.
        filas.append((f"{n}: falta en la ficha", f"{_mm(pieza, n, POR_DEFECTO):g}*"))
    if pieza.dientes is not None:
        recuentos = mapa_de("piezas_num")
        filas.append((f"#{recuentos}.{pieza.nombre}_dientes", str(pieza.dientes)))
    return filas


def caja_del_perfil(pieza: PiezaComercial) -> tuple[float, float]:
    """Diámetro y altura que ocupa el perfil, en mm. Lo que compara el test."""
    puntos, _ = perfil_de(pieza)
    return 2.0 * max(r for r, _ in puntos), max(z for _, z in puntos)


# ---------------------------------------------------------------------------


def panel(pieza: PiezaComercial, x: float, y: float, ancho: float, alto: float) -> list[str]:
    puntos, _ = perfil_de(pieza)
    filas = filas_de(pieza)
    diametro, altura = caja_del_perfil(pieza)

    # El dibujo se centra en su hueco: si no, una pieza baja como el rodillo
    # queda pegada abajo y una alta como el portaminas se sale por arriba.
    hueco_alto = alto - 30.0 - 9.0 * len(filas) - 20.0
    k = min(ancho * 0.36 / max(diametro / 2, 1e-6), hueco_alto / max(altura, 1e-6), 8.0)
    cx = x + ancho / 2
    base = y + 30.0 + (hueco_alto + altura * k) / 2.0

    def media(signo: int) -> str:
        return " ".join(f"{cx + signo * r * k:.2f},{base - z * k:.2f}" for r, z in puntos)

    d = [
        f'<text class="pieza" x="{cx:.1f}" y="{y + 11:.1f}">{pieza.nombre}</text>',
        f'<text class="ref" x="{cx:.1f}" y="{y + 19:.1f}">'
        f"{pieza.designacion} · x{pieza.cantidad}</text>",
        f'<polygon class="corte" points="{media(1)}"/>',
        f'<polygon class="corte" points="{media(-1)}"/>',
        f'<line class="eje" x1="{cx:.1f}" y1="{base - altura * k - 7:.1f}" '
        f'x2="{cx:.1f}" y2="{base + 7:.1f}"/>',
        # El rótulo va arriba a la derecha y no bajo el dibujo: una pieza
        # esbelta como el portaminas ocupa todo el alto por el centro, y
        # abajo el rótulo le caía encima. La esquina siempre está libre.
        f'<text class="escala esq" x="{x + ancho - 5:.1f}" y="{y + 34:.1f}">'
        f"Ø{diametro:g} × {altura:g} mm</text>",
        f'<line class="raya" x1="{x + 4:.1f}" y1="{y + 30 + hueco_alto + 4:.1f}" '
        f'x2="{x + ancho - 4:.1f}" y2="{y + 30 + hueco_alto + 4:.1f}"/>',
    ]

    fila = y + 30.0 + hueco_alto + 14.0
    for variable, valor in filas:
        d.append(f'<text class="var" x="{x + 5:.1f}" y="{fila:.1f}">{variable}</text>')
        d.append(f'<text class="val" x="{x + ancho - 5:.1f}" y="{fila:.1f}">{valor}</text>')
        fila += 9.0

    aviso = SIN_MASA_FIABLE.get(pieza.nombre)
    if aviso:
        d.append(
            f'<text class="aviso" x="{x + 5:.1f}" y="{y + alto - 6:.1f}">'
            f"sin material: {aviso}</text>"
        )
    else:
        d.append(
            f'<text class="masa" x="{x + 5:.1f}" y="{y + alto - 6:.1f}">'
            f"{pieza.material.split(',')[0][:22]} · {_masa(pieza):.3f} g</text>"
        )
    return d


def _masa(pieza: PiezaComercial) -> float:
    """Por el teorema de Pappus sobre el perfil: gira y pesa."""
    puntos, _ = perfil_de(pieza)
    area2 = 0.0
    centro = 0.0
    for (r0, z0), (r1, z1) in zip(puntos, puntos[1:] + puntos[:1], strict=True):
        cruz = r0 * z1 - r1 * z0
        area2 += cruz
        centro += (r0 + r1) * cruz
    area = abs(area2) / 2.0
    radio = abs(centro / (3.0 * area2)) if area2 else 0.0
    volumen = 2.0 * 3.141592653589793 * radio * area  # mm³
    return volumen * 1e-9 * densidad_de(pieza.material) * 1000.0


ESTILO = """
text{font-family:Helvetica,Arial,sans-serif;fill:#1b1b1b}
.h1{font-size:11px;font-weight:bold}
.sub{font-size:5.8px;fill:#555}
.pieza{font-size:6.6px;font-weight:bold;text-anchor:middle}
.ref{font-size:5px;fill:#666;text-anchor:middle}
.escala{font-size:5.2px;fill:#b03030;text-anchor:middle}
.esq{text-anchor:end}
.var{font-size:4.9px;fill:#1b5fb0;font-family:monospace}
.val{font-size:5px;fill:#b03030;text-anchor:end}
.masa{font-size:5px;fill:#2f6f4f}
.aviso{font-size:5px;fill:#8a4a00}
.raya{stroke:#e0e0e0;stroke-width:0.5}
.corte{fill:#d9e2ef;stroke:#1b1b1b;stroke-width:0.8}
.eje{stroke:#1b5fb0;stroke-width:0.6;stroke-dasharray:6 2 1 2}
.marco{fill:none;stroke:#ddd;stroke-width:0.6}
"""


def hoja(piezas: list[PiezaComercial], columnas: int = 3) -> str:
    ancho, alto, borde = 190.0, 176.0, 12.0
    filas = (len(piezas) + columnas - 1) // columnas
    w = borde * 2 + columnas * ancho
    h = 44 + filas * alto + borde
    partes = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{w * 2:.0f}" height="{h * 2:.0f}" '
        f'viewBox="0 0 {w:.0f} {h:.0f}">',
        f"<style>{ESTILO}</style>",
        f'<rect width="{w:.0f}" height="{h:.0f}" fill="#fff"/>',
        f'<text class="h1" x="{borde}" y="20">Piezas comerciales · sección y cotas</text>',
        f'<text class="sub" x="{borde}" y="30">Generado desde docs/piezas/ con '
        "scripts/dibujar_piezas.py. En el CAD, cada cota se escribe "
        '<tspan font-family="monospace">#pieza.&lt;pieza&gt;_&lt;cota&gt;</tspan>.</text>',
        f'<text class="sub" x="{borde}" y="38">Son envolventes: exactas en lo que otra pieza '
        "toca y toscas en el resto. Donde pone «sin material», su masa no significa nada.</text>",
    ]
    for i, pieza in enumerate(piezas):
        x = borde + (i % columnas) * ancho
        y = 44 + (i // columnas) * alto
        partes.append(
            f'<rect class="marco" x="{x:.1f}" y="{y:.1f}" '
            f'width="{ancho - 4:.1f}" height="{alto - 6:.1f}" rx="3"/>'
        )
        partes += panel(pieza, x, y, ancho - 4, alto - 6)
    partes.append("</svg>")
    return "\n".join(partes)


def main(argv: list[str] | None = None) -> int:
    partes = argparse.ArgumentParser(prog="dibujar_piezas", description=__doc__)
    partes.add_argument("--out", type=Path, default=Path("build/piezas.svg"))
    partes.add_argument("--solo", nargs="*", help="nombres de pieza; por defecto, todas")
    opciones = partes.parse_args(argv)

    piezas = [p for p in cargar() if not opciones.solo or p.nombre in opciones.solo]
    if not piezas:
        print("ninguna pieza coincide", file=sys.stderr)
        return 1
    opciones.out.parent.mkdir(parents=True, exist_ok=True)
    opciones.out.write_text(hoja(piezas), encoding="utf-8")
    print(f"{len(piezas)} piezas en {opciones.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
