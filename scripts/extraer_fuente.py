"""Saca una fuente Hershey a `docs/fuentes/<nombre>.json`, como dato.

    uv run python scripts/extraer_fuente.py cursiva

**Por qué la fuente es un archivo del repo y no un paquete.** Un pedido
tiene que salir igual en cada máquina y dentro de cinco años: si los
glifos vienen de una dependencia, basta con que el paquete cambie una
coordenada para que la leva de un cliente deje de ser la que se le
entregó. Aquí la fuente entra una vez, se versiona y se congela, igual
que el kerf o los precios.

El paquete `HersheyFonts` solo hace falta para ejecutar ESTO, y por eso
no está en las dependencias del proyecto: se instala a mano el día que
haya que añadir una fuente.

    uv pip install Hershey-Fonts

**La fuente es de dominio público**: A. V. Hershey, U.S. National Bureau
of Standards, 1967. La transcripción a formato legible por máquina es de
James Hurt, distribuida con la petición de citar a ambos. Va en el JSON.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

RAIZ = Path(__file__).resolve().parent.parent
DESTINO = RAIZ / "docs" / "fuentes"

FUENTES = {"cursiva": "cursive"}
"""Nombre nuestro -> nombre en el paquete. Solo lo que usamos: una fuente
que no se va a trazar con una pluma no pinta nada aquí."""

ATRIBUCION = (
    "A. V. Hershey, U.S. National Bureau of Standards, 1967. "
    "Transcripción de James Hurt. Dominio público, con atribución."
)


def extraer(cual: str) -> dict[str, object]:
    from HersheyFonts import HersheyFonts

    hershey = HersheyFonts()
    hershey.load_default_font(FUENTES[cual])
    letras = list(hershey.all_glyphs)
    glifos = {}
    for letra, glifo in zip(letras, hershey.glyphs_for_text("".join(letras)), strict=True):
        trazos = [[[int(x), int(y)] for x, y in trazo] for trazo in glifo.strokes]
        glifos[letra] = {
            "lado_izquierdo": int(glifo.left_offset),
            "avance": int(glifo.char_width),
            "trazos": trazos,
        }
    primero = next(iter(hershey.glyphs_for_text(letras[0])))
    return {
        "nombre": cual,
        "procedencia": ATRIBUCION,
        "linea_base": float(primero.base_line),
        "altura_mayuscula": float(primero.cap_line),
        "altura_de_x": float(primero.base_line),
        "glifos": glifos,
    }


def main(argv: list[str] | None = None) -> int:
    partes = argparse.ArgumentParser(prog="extraer_fuente", description=__doc__)
    partes.add_argument("fuente", choices=sorted(FUENTES), nargs="?", default="cursiva")
    opciones = partes.parse_args(argv)
    DESTINO.mkdir(parents=True, exist_ok=True)
    ruta = DESTINO / f"{opciones.fuente}.json"
    datos = extraer(opciones.fuente)
    ruta.write_text(json.dumps(datos, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"{len(datos['glifos'])} glifos en {ruta.relative_to(RAIZ)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
