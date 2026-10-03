"""La geometria del escape del banco R2, leida de `docs/reloj/escape-r2.json`.

Vive aqui y no en `core/` porque lee un fichero. Es una **propuesta**, no un
contrato: el contrato del escape sigue en `docs/reloj/contratos.json` y no
pasa la envolvente de conjunto (ver `docs/reloj/cambios.md`, 2026-10-03).

`escala` agranda todo menos el eje, que es la varilla calibrada de todo el
reloj. Los angulos no cambian al escalar; lo que cambia es cuanto pesa el
error de sierra, que es en milimetros.
"""

from __future__ import annotations

import json
from pathlib import Path

from core.reloj.graham import AncoraGraham, RuedaGraham
from core.units import Metros, Radianes, grados, mm

RUTA = Path(__file__).resolve().parent.parent / "docs" / "reloj" / "escape-r2.json"


def valores(ruta: Path = RUTA) -> dict[str, float]:
    datos = json.loads(ruta.read_text(encoding="utf-8"))
    return {k: float(v["valor"]) for k, v in datos["valores"].items()}


def amplitud(ruta: Path = RUTA) -> Radianes:
    return grados(valores(ruta)["amplitud"])


def geometria(escala: float = 1.0, ruta: Path = RUTA) -> tuple[RuedaGraham, AncoraGraham]:
    v = valores(ruta)

    def largo(nombre: str) -> Metros:
        return mm(v[nombre] * escala)

    dientes = int(v["dientes"])
    rueda = RuedaGraham(
        dientes=dientes,
        radio_punta=largo("radio_punta"),
        radio_fondo=largo("radio_fondo"),
        espesor_punta=grados(v["espesor_punta"]),
        socavado=grados(v["socavado"]),
        dorso=grados(v["dorso"]),
    )
    ancora = AncoraGraham(
        dientes=dientes,
        radio_punta=largo("radio_punta"),
        reposo=grados(v["reposo"]),
        impulso=grados(v["impulso"]),
        ancho_trabajo=largo("ancho_trabajo"),
        largo_dedo=largo("largo_dedo"),
        ancho_cuerpo=largo("ancho_cuerpo"),
        largo_paleta=largo("largo_paleta"),
        yugo=grados(v["yugo"]),
        brazo_ancho=largo("brazo_ancho"),
        cubo=largo("cubo"),
        eje=mm(v["eje"]),
        pierna_hasta=largo("pierna_hasta"),
    )
    return rueda, ancora


__all__ = ["RUTA", "amplitud", "geometria", "valores"]
