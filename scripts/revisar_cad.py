"""Compara lo que salio del CAD -un DXF o un STEP- contra el contrato.

    uv run python scripts/revisar_cad.py --pieza varilla boceto.dxf
    uv run python scripts/revisar_cad.py --pieza varilla pieza.step

El DXF dice lo que hay en el boceto; el STEP dice lo que hay en el solido, y
no son lo mismo. Un taladro que falta en el boceto se ve en los dos, pero un
rebaje que se extruyo mal solo se ve en el STEP. Por eso se revisan los dos.

**Para que sirve.** El flujo es de un solo sentido: se toca el JSON, se
regenera la tabla, se dibuja. Nada impide que alguien acote a mano dentro de
Onshape, y si lo hace, el dibujo y el compilador dejan de decir lo mismo sin
que nadie se entere hasta que la pieza esta cortada. Esto lo caza en un
segundo.

Es la verificacion automatica de la metodologia aplicada al lado del CAD:
mide la geometria que salio del dibujo y la cruza con la cota del contrato.
"""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path

import ezdxf

from compile.contratos import Contratos, cargar

PATRON = re.compile(r"#(\d+)\s*=\s*([A-Z_0-9]+)\s*\((.*?)\)\s*;", re.S)
"""Una entidad de STEP. El formato es plano y sin anidar entidades, asi que
una expresion regular basta y no hace falta el kernel OCCT, que son 800 MB y
una dependencia opcional del proyecto."""

RELOJ = Path("docs/reloj/contratos.json")
HOLGURA = 0.01
"""Milimetros. Un DXF trae los numeros en doble precision, asi que lo que se
busca es coincidencia exacta; esta holgura es para el redondeo, no para la
fabricacion."""


@dataclass(frozen=True)
class Medida:
    """Una cota medida en el dibujo frente a la que dice el contrato."""

    que: str
    contrato: float
    dibujo: float | None

    @property
    def pasa(self) -> bool:
        return self.dibujo is not None and abs(self.dibujo - self.contrato) <= HOLGURA


def _entidades(ruta: Path) -> dict[str, tuple[str, str]]:
    """Las entidades del STEP, por numero. En metros, que es como las escribe."""
    texto = ruta.read_text(encoding="utf-8", errors="replace")
    return {n: (tipo, args) for n, tipo, args in PATRON.findall(texto)}


def _numeros(args: str) -> list[float]:
    return [float(x) for x in re.findall(r"-?\d+\.\d*(?:[eE][-+]?\d+)?", args)]


def _medidas_varilla_step(c: Contratos, ruta: Path) -> list[Medida]:
    """Mide el solido: caja envolvente y agujeros cilindricos."""
    ent = _entidades(ruta)
    puntos = [_numeros(a) for t, a in ent.values() if t == "CARTESIAN_POINT"]
    puntos = [p for p in puntos if len(p) == 3]
    ejes = {
        n: _numeros(ent[a.split(",")[1].strip().lstrip("#")][1])
        for n, (t, a) in ent.items()
        if t == "AXIS2_PLACEMENT_3D" and a.split(",")[1].strip().lstrip("#") in ent
    }

    mm = 1000.0
    largo = (max(p[0] for p in puntos) - min(p[0] for p in puntos)) * mm
    ancho = (max(p[1] for p in puntos) - min(p[1] for p in puntos)) * mm
    espesor = (max(p[2] for p in puntos) - min(p[2] for p in puntos)) * mm

    v = c.contrato("pendulo")
    medidas = [
        Medida("largo de la caja", v.valor("varilla_largo").en_mm, largo),
        Medida("ancho de la caja", v.valor("varilla_ancho").en_mm, ancho),
        Medida("espesor de la caja", v.valor("varilla_espesor").en_mm, espesor),
    ]

    # Cada cilindro es un agujero. Se agrupan por diametro.
    cilindros: list[tuple[float, list[float]]] = []
    for t, a in ent.values():
        if t != "CYLINDRICAL_SURFACE":
            continue
        trozos = [x.strip() for x in a.split(",")]
        radio = float(trozos[-1])
        centro = ejes.get(trozos[-2].lstrip("#"), [0.0, 0.0, 0.0])
        cilindros.append((radio * 2.0 * mm, [x * mm for x in centro]))

    taladro = v.valor("varilla_taladro_diametro").en_mm
    de_sujecion = sorted((d for d, _ in cilindros if abs(d - taladro) <= HOLGURA))
    medidas.append(Medida("taladros de sujecion, cuantos", 2.0, float(len(de_sujecion))))
    for titulo, clave in (
        ("taladro cerca, al extremo", "varilla_taladro_cerca"),
        ("taladro lejos, al extremo", "varilla_taladro_lejos"),
    ):
        esperado = v.valor(clave).en_mm
        cerca = [
            c0[0]
            for d, c0 in cilindros
            if abs(d - taladro) <= HOLGURA and abs(c0[0] - esperado) <= HOLGURA
        ]
        medidas.append(Medida(titulo, esperado, cerca[0] if cerca else None))

    vastago = v.valor("varilla_vastago_diametro").en_mm
    hallado = [c0 for d, c0 in cilindros if abs(d - vastago) <= HOLGURA]
    medidas.append(Medida("taladro del vastago, diametro", vastago, vastago if hallado else None))

    # La profundidad: el taladro entra por el extremo de abajo, asi que se
    # mide del fondo del cilindro al final de la pieza. Un taladro del
    # diametro correcto pero corto pasaria la comprobacion de arriba.
    if hallado:
        fondo = min(c0[0] for c0 in hallado)
        medidas.append(
            Medida(
                "taladro del vastago, profundidad",
                v.valor("varilla_vastago_profundidad").en_mm,
                largo - fondo,
            )
        )
        medidas.append(Medida("taladro del vastago, al eje del ancho", ancho / 2.0, hallado[0][1]))
        medidas.append(
            Medida("taladro del vastago, al eje del espesor", espesor / 2.0, hallado[0][2])
        )
    return medidas


def _medidas_varilla(c: Contratos, ruta: Path) -> list[Medida]:
    doc = ezdxf.readfile(ruta)
    espacio = doc.modelspace()
    lineas = [e for e in espacio if e.dxftype() == "LINE"]
    circulos = [e for e in espacio if e.dxftype() == "CIRCLE"]

    xs = [v for e in lineas for v in (e.dxf.start.x, e.dxf.end.x)]
    ys = [v for e in lineas for v in (e.dxf.start.y, e.dxf.end.y)]
    largo = max(xs) - min(xs) if xs else None
    ancho = max(ys) - min(ys) if ys else None

    v = c.contrato("pendulo")
    medidas = [
        Medida("largo del contorno", v.valor("varilla_largo").en_mm, largo),
        Medida("ancho del contorno", v.valor("varilla_ancho").en_mm, ancho),
    ]

    # Los taladros, ordenados por su distancia al extremo de referencia.
    taladros = sorted(circulos, key=lambda e: e.dxf.center.x)
    esperados = (
        ("taladro cerca", "varilla_taladro_cerca"),
        ("taladro lejos", "varilla_taladro_lejos"),
    )
    for i, (titulo, clave) in enumerate(esperados):
        centro = taladros[i].dxf.center.x - min(xs) if i < len(taladros) else None
        medidas.append(Medida(f"{titulo}, al extremo", v.valor(clave).en_mm, centro))
    diametro = v.valor("varilla_taladro_diametro").en_mm
    for i, titulo in enumerate(("diametro del taladro cerca", "diametro del taladro lejos")):
        d = 2.0 * taladros[i].dxf.radius if i < len(taladros) else None
        medidas.append(Medida(titulo, diametro, d))

    # Centrados en el ancho: lo que deja pared igual a los dos lados.
    if ancho is not None:
        for i, titulo in enumerate(("taladro cerca, al eje", "taladro lejos, al eje")):
            y = taladros[i].dxf.center.y - min(ys) if i < len(taladros) else None
            medidas.append(Medida(titulo, ancho / 2.0, y))
    return medidas


REVISORES = {"varilla": _medidas_varilla}
REVISORES_STEP = {"varilla": _medidas_varilla_step}


def informe(medidas: list[Medida]) -> tuple[str, bool]:
    lineas = [f"{'que':34s} {'contrato':>10s} {'dibujo':>10s}   "]
    lineas.append("-" * 64)
    todo = True
    for m in medidas:
        dibujo = "AUSENTE" if m.dibujo is None else f"{m.dibujo:10.3f}"
        marca = "ok" if m.pasa else ("FALTA" if m.dibujo is None else "NO COINCIDE")
        todo = todo and m.pasa
        lineas.append(f"{m.que:34s} {m.contrato:10.3f} {dibujo:>10s}   {marca}")
    lineas.append("")
    faltan = [m.que for m in medidas if m.dibujo is None]
    discrepan = [m.que for m in medidas if m.dibujo is not None and not m.pasa]
    if todo:
        lineas.append("El dibujo dice lo mismo que el contrato.")
    else:
        # Dos diagnosticos distintos, y conviene no mezclarlos: una cota que
        # no coincide es un numero tecleado a mano o un contrato sin
        # regenerar; una que falta es una operacion que nadie ha hecho.
        if faltan:
            lineas.append(f"FALTAN OPERACIONES en el CAD: {', '.join(faltan)}.")
        if discrepan:
            lineas.append(
                f"NO COINCIDEN: {', '.join(discrepan)}. O se acoto a mano, o el "
                "contrato cambio y falta regenerar."
            )
    return "\n".join(lineas), todo


def main(argv: list[str] | None = None) -> int:
    partes = argparse.ArgumentParser(prog="revisar_cad", description=__doc__)
    partes.add_argument("fichero", type=Path)
    partes.add_argument("--pieza", default="varilla", choices=sorted(REVISORES))
    partes.add_argument("--contratos", type=Path, default=RELOJ)
    opciones = partes.parse_args(argv)

    es_step = opciones.fichero.suffix.lower() in (".step", ".stp")
    tabla = REVISORES_STEP if es_step else REVISORES
    medidas = tabla[opciones.pieza](cargar(opciones.contratos), opciones.fichero)
    texto, todo = informe(medidas)
    print(texto)
    return 0 if todo else 1


if __name__ == "__main__":
    sys.exit(main())
