"""Genera las hojas de la verificación humana de E3.

    uv run python scripts/plantillas_demo.py [carpeta]

Produce los tres archivos que hay que llevar a la copistería de una vez:

- `hoja_patron_A4.pdf` — la hoja que se mide para calibrar. **Esta primero**:
  del resto no se puede decir nada hasta saber cuánto escala la impresora.
- `plantilla_leva_A4.pdf` — una leva real en una hoja.
- `plantilla_bastidor_troceado_A4.pdf` — una pieza que no cabe en A4, para
  comprobar el solape y las marcas de registro al pegar las hojas.

Con un perfil ya medido se vuelven a generar corregidas:

    uv run python scripts/plantillas_demo.py out bench/impresoras/copi.json
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.units import a_mm
from emit.calibracion import aplicar, cargar, evaluar, hoja_patron, medidas_del_patron
from emit.layout import Formato, formato_minimo, maquetar
from emit.template import escribir_pdf
from tests.emit.piezas_de_prueba import bastidor_grande, leva


def main() -> int:
    destino = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("out")
    destino.mkdir(parents=True, exist_ok=True)
    formato = Formato.A4

    perfil = cargar(sys.argv[2]) if len(sys.argv) > 2 else None
    if perfil is not None:
        veredicto = evaluar(perfil)
        print(f"perfil: {perfil.nombre} · x {perfil.factor_x:.4f} · y {perfil.factor_y:.4f}")
        for incidencia in veredicto.incidencias:
            print(f"  [{incidencia.gravedad}] {incidencia.mensaje}")
        if not veredicto.apto:
            print("perfil no apto: no se corrige nada.")
            return 1

    def emitir(laminas: list, nombre: str) -> int:
        if perfil is not None:
            laminas = [aplicar(lamina, perfil) for lamina in laminas]
        escribir_pdf(laminas, destino / nombre)
        return len(laminas)

    ancho, alto = medidas_del_patron(formato)
    emitir([hoja_patron(formato)], "hoja_patron_A4.pdf")
    print(f"{'hoja_patron_A4.pdf':<40} patrón de {ancho:.0f} × {alto:.0f} mm  → 1 hoja")

    for pieza, nombre in (
        (leva(), "plantilla_leva_A4.pdf"),
        (bastidor_grande(), "plantilla_bastidor_troceado_A4.pdf"),
    ):
        hojas = emitir(maquetar(pieza, formato), nombre)
        print(
            f"{nombre:<40} {a_mm(pieza.ancho):6.1f} × {a_mm(pieza.alto):6.1f} mm  "
            f"→ {hojas} hoja(s) {formato.value}  "
            f"(cabría entera en {formato_minimo(pieza)})"
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
