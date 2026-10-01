"""Perfiles de las piezas prismáticas de la plataforma, y su DXF.

El reparto con Onshape decía que la plataforma se dibuja a mano. Sigue
siendo verdad en lo que importa —el vínculo con el contrato lo pone quien
acota, y por eso la pieza sigue siendo paramétrica— pero la **forma** la
entrega este módulo. Construir una tangente exterior entre dos círculos
desiguales o un agujero en D a mano es donde están los errores, y es trabajo
que no hace falta repetir por pieza.

El bucle entero está en `docs/metodologia.md` §2d: generar, dibujar, que el
CAD diga «totalmente definida», comparar.

**El sitio es la mitad del valor.** Un croquis importado llega exacto y
suelto, y las cotas de la pieza no quitan los tres grados de libertad del
plano. Aquí cada pieza se emite con su rasgo datum en el ORIGEN y el centro
siguiente sobre +X, que deja el anclaje en dos coincidentes enganchados a
geometría que ya está dibujada.

**En su propio marco, no en el de la máquina.** El contrato tiene la
transformada (`brazo_origen_*`, `brazo_orientacion`), pero emitir el brazo
donde de verdad va lo deja girado -3,749°, miserable de acotar, y además el
mismo brazo ocupa DOS posiciones. No hay una posición.

Regla 3: el contrato entra en SI y aquí se cruza a milímetros, como en
`emit/dxf.py` y `emit/layout.py`. Nada de medias tintas aguas abajo.
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass
from pathlib import Path

from ezdxf.filemanagement import new as nuevo_dxf

RAIZ = Path(__file__).resolve().parent.parent
CONTRATOS = RAIZ / "docs" / "contratos.json"
MM = 1000.0

Punto = tuple[float, float]


@dataclass(frozen=True)
class Arco:
    centro: Punto
    radio: float
    desde: float
    hasta: float
    """En radianes, sentido antihorario de `desde` a `hasta`."""


@dataclass(frozen=True)
class Segmento:
    a: Punto
    b: Punto


Perfil = list[Arco | Segmento]


def contrato_mm() -> dict[str, float]:
    """Las longitudes del contrato en mm y los ángulos en radianes."""
    datos = json.loads(CONTRATOS.read_text(encoding="utf-8"))
    return {
        v["nombre"]: float(v["valor"]) * (MM if v["unidad"] == "m" else 1.0)
        for g in datos["contratos"]
        for v in g["valores"]
    }


def barra(largo: float, r0: float, r1: float) -> Perfil:
    """Contorno de una barra de dos cubos: dos arcos y sus tangentes.

    El datum —el cubo de r0— va en el origen y el otro en (largo, 0). Los
    radios pueden ser distintos, así que las tangentes no son paralelas: el
    punto de contacto sale de imponer la perpendicularidad al radio, que da
    `cos t = (r0 - r1) / largo`. Es la misma condición que coloca la cinta en
    el cabestrante, y es la que se escribió mal dos veces por razonar sobre
    el dibujo en vez de resolverla.
    """
    if largo <= abs(r0 - r1):
        raise ValueError("un cubo se come al otro: no hay tangente exterior")
    t = math.acos((r0 - r1) / largo)
    arriba = ((r0 * math.cos(t), r0 * math.sin(t)), (largo + r1 * math.cos(t), r1 * math.sin(t)))
    abajo = ((largo + r1 * math.cos(-t), r1 * math.sin(-t)), (r0 * math.cos(-t), r0 * math.sin(-t)))
    return [
        Arco((0.0, 0.0), r0, t, 2 * math.pi - t),
        Segmento(abajo[1], abajo[0]),
        Arco((largo, 0.0), r1, -t, t),
        Segmento(arriba[1], arriba[0]),
    ]


def agujero_en_d(centro: Punto, radio: float, chaveta: float) -> Perfil:
    """El agujero que cala: un arco y la cuerda de la cara plana.

    La cara mira al otro cubo —normal en +X, `brazo_chaveta_angulo` = 0— y no
    es una elección: a cualquier otro ángulo el brazo deja de ser simétrico
    respecto de su propio eje, y entonces el proximal volteado no sirve para
    el otro lado.
    """
    if not 0.0 < chaveta < radio:
        raise ValueError("la cara plana se come el agujero o no lo toca")
    t = math.acos(chaveta / radio)
    x = centro[0] + chaveta
    return [
        Arco(centro, radio, t, 2 * math.pi - t),
        Segmento((x, centro[1] - radio * math.sin(t)), (x, centro[1] + radio * math.sin(t))),
    ]


def circulo(centro: Punto, radio: float) -> Perfil:
    return [Arco(centro, radio, 0.0, 2 * math.pi)]


BRAZOS = {
    "brazo_proximal": ("brazo_proximal", True),
    "brazo_distal": ("brazo_distal", False),
    "palanca_lapiz": ("brazo_palanca", True),
}


def brazo(cual: str, c: dict[str, float] | None = None) -> Perfil:
    """Una de las tres barras del cinco barras, en su marco y en el datum."""
    if cual not in BRAZOS:
        raise KeyError(f"no sé dibujar «{cual}». Hay: {', '.join(BRAZOS)}")
    c = contrato_mm() if c is None else c
    entre_centros, calado = BRAZOS[cual]
    largo = c[entre_centros]
    extremo, perno = c["brazo_extremo_diametro"] / 2, c["brazo_perno_diametro"] / 2
    if not calado:
        # Biela: los dos extremos iguales porque no cala nada.
        return barra(largo, extremo, extremo) + circulo((0.0, 0.0), perno) + circulo(
            (largo, 0.0), perno
        )
    cubo, eje = c["brazo_cubo_diametro"] / 2, c["brazo_eje_diametro"] / 2
    return (
        barra(largo, cubo, extremo)
        + agujero_en_d((0.0, 0.0), eje, c["brazo_chaveta"])
        + circulo((largo, 0.0), perno)
    )


def escribir_dxf(perfil: Perfil, destino: Path, capa: str = "VISIBLE") -> Path:
    """El perfil a DXF, **sin rótulos**.

    Un `TEXT` de DXF no es una entidad de boceto y Onshape suelta un «no se ha
    podido importar la entidad desconocida» al verlo. Estos archivos se
    importan a un croquis, así que no llevan ninguno: lo que hay que leer va
    en la hoja, no en el archivo.
    """
    doc = nuevo_dxf("R2010", setup=False)
    doc.header["$INSUNITS"] = 4  # milímetros, para que el CAD no pregunte
    doc.layers.add(capa)
    msp = doc.modelspace()
    for e in perfil:
        if isinstance(e, Segmento):
            msp.add_line(e.a, e.b, dxfattribs={"layer": capa})
        elif abs(e.hasta - e.desde - 2 * math.pi) < 1e-12:
            msp.add_circle(e.centro, e.radio, dxfattribs={"layer": capa})
        else:
            msp.add_arc(
                e.centro,
                e.radio,
                math.degrees(e.desde),
                math.degrees(e.hasta),
                dxfattribs={"layer": capa},
            )
    destino.parent.mkdir(parents=True, exist_ok=True)
    doc.saveas(destino)
    return destino
