"""El material en bruto de la plataforma, y lo que sale de cada uno.

**Una pieza no se compra: se compra el material del que sale.** La lista de
compra, la hoja de corte y la de torno van por material, y cada material de
más es otro pedido, otro proveedor y otra preparación de máquina. Por eso
cada `Ficha.material` tiene que ser una entrada de `STOCK`, y un test lo
exige: dos nombres para la misma barra —pasó con la W10, «acero W10 h6
rectificado» y «barra W10 h6 rectificada»— salían en la lista como dos
compras.

Las cantidades salen del contrato y del perfil de cada pieza: los
milímetros de barra, sumando el largo y un corte por pieza, y la chapa por
la caja de cada perfil y un margen de corte alrededor. Es lo que hace falta
para pedir; el anidado fino lo hace el taller.
"""

from __future__ import annotations

from dataclasses import dataclass

from emit.plataforma import BRAZOS, LISTADO, PERFILES, Arco, Segmento, brazo, contrato_mm

CORTE = 2.0
"""Lo que se pierde por cada corte de sierra en barra o tubo, en mm."""

MARGEN_DE_CHAPA = 3.0
"""Lo que se deja alrededor de cada pieza de chapa al anidarla, en mm."""


@dataclass(frozen=True)
class Stock:
    forma: str
    """«chapa», «barra», «tubo», «alambre», «fleje» o «tabla»: decide si se
    pide por superficie o por largo."""
    compra: str
    """Cómo se pide, para la lista de compra."""


STOCK: dict[str, Stock] = {
    "POM-C negro, plancha de 5": Stock("chapa", "plancha 1000 × 1000 × 5; la misma que las levas"),
    "contrachapado de abedul de 9": Stock("chapa", "tablero de abedul de 9, calidad B/BB"),
    "nogal americano macizo de 25": Stock("tabla", "tabla cepillada de 25, 240 de ancho útil"),
    "aluminio 5083, chapa de 4": Stock("chapa", "chapa de 4"),
    "chapa de latón de 2": Stock("chapa", "chapa CuZn39Pb3 de 2"),
    "chapa de latón de 3": Stock("chapa", "chapa CuZn39Pb3 de 3"),
    "chapa de latón de 4": Stock("chapa", "chapa CuZn39Pb3 de 4"),
    "chapa de latón de 6": Stock("chapa", "chapa CuZn39Pb3 de 6"),
    "fleje 1.4310 de 0,15": Stock("fleje", "fleje inoxidable de muelle, 0,15"),
    "barra W10 h6 rectificada": Stock("barra", "eje de precisión Ø10 h6 CF53, cortado a medida"),
    "acero plata Ø1,5": Stock("barra", "acero plata Ø1,5 h9"),
    "acero plata Ø4 h6": Stock("barra", "acero plata Ø4 h6"),
    "acero plata Ø6": Stock("barra", "acero plata Ø6 h9"),
    "cuerda de piano Ø2": Stock("alambre", "cuerda de piano Ø2, recta"),
    "latón, barra de Ø4": Stock("barra", "barra de latón Ø4"),
    "latón, barra de Ø16": Stock("barra", "barra de latón CuZn39Pb3 Ø16"),
    "latón, barra de Ø25": Stock("barra", "barra de latón CuZn39Pb3 Ø25"),
    "latón, barra cuadrada de 16": Stock("barra", "barra cuadrada de latón de 16"),
    "latón, barra de 6 × 5": Stock("barra", "pletina de latón 6 × 5"),
    "latón, tubo 13/10,6": Stock("tubo", "tubo de latón 13 × 1,2"),
    "latón, tubo 4/3,1": Stock("tubo", "tubo de latón 4 × 0,45"),
    "latón, tubo 3,2/2": Stock("tubo", "tubo de latón 3,2 × 0,6"),
}
"""El material en bruto. Lo que no está aquí no se puede pedir."""


def _caja(nombre: str, c: dict[str, float]) -> tuple[float, float]:
    """Ancho y alto de la caja del perfil de una pieza, en mm."""
    perfil = brazo(nombre, c) if nombre in BRAZOS else PERFILES[nombre](c)
    xs: list[float] = []
    ys: list[float] = []
    for e in perfil:
        if isinstance(e, Segmento):
            xs += [e.a[0], e.b[0]]
            ys += [e.a[1], e.b[1]]
        elif isinstance(e, Arco):
            xs += [e.centro[0] - e.radio, e.centro[0] + e.radio]
            ys += [e.centro[1] - e.radio, e.centro[1] + e.radio]
    return max(xs) - min(xs), max(ys) - min(ys)


def _largos(nombre: str, cota: str, c: dict[str, float]) -> list[float]:
    """El largo de cada unidad. Una pieza de varios largos —el casquillo del
    rodillo, uno por canal— los lleva como variables `<cota>_1`, `_2`…, y el
    sólido se extruye al último; aquí cuenta cada uno."""
    ficha = LISTADO[nombre]
    # Lo que gasta de barra es la cota por la que se extruye, sea una barra
    # cortada a largo o un disco torneado a su espesor: nunca el diámetro.
    raiz, _, sufijo = cota.rpartition("_")
    if sufijo.isdigit():
        largos = [c[v.nombre] for v in ficha.variables if v.nombre.startswith(raiz + "_")]
        if len(largos) == ficha.cantidad:
            return largos
    return [c[cota]] * ficha.cantidad


@dataclass(frozen=True)
class Linea:
    material: str
    stock: Stock
    piezas: tuple[tuple[str, int], ...]
    cantidad: float
    """mm de barra, tubo o alambre, o mm² de chapa."""


def compra(c: dict[str, float] | None = None) -> list[Linea]:
    """Lo que hay que pedir de cada material para una plataforma."""
    c = contrato_mm() if c is None else c
    lineas = []
    for material, stock in STOCK.items():
        suyas = [(n, f) for n, f in LISTADO.items() if f.material == material]
        total = 0.0
        for nombre, ficha in suyas:
            _, cota = ficha.solido
            if stock.forma in ("barra", "tubo", "alambre"):
                total += sum(largo + CORTE for largo in _largos(nombre, cota, c))
            else:
                ancho, alto = _caja(nombre, c)
                total += (
                    (ancho + 2 * MARGEN_DE_CHAPA) * (alto + 2 * MARGEN_DE_CHAPA) * ficha.cantidad
                )
        lineas.append(
            Linea(material, stock, tuple((n, f.cantidad) for n, f in suyas), round(total, 1))
        )
    return lineas


def tabla_markdown(c: dict[str, float] | None = None) -> str:
    filas = [
        "| Material | Forma | Se pide | Cantidad | Piezas |",
        "| --- | --- | --- | ---: | --- |",
    ]
    for linea in compra(c):
        unidad = "mm²" if linea.stock.forma in ("chapa", "tabla", "fleje") else "mm"
        piezas = ", ".join(f"{n} ×{k}" for n, k in linea.piezas)
        cantidad = f"{linea.cantidad:,.0f}".replace(",", " ")
        filas.append(
            f"| {linea.material} | {linea.stock.forma} | {linea.stock.compra} | "
            f"{cantidad} {unidad} | {piezas} |"
        )
    return "\n".join(filas) + "\n"


__all__ = ["CORTE", "MARGEN_DE_CHAPA", "STOCK", "Linea", "Stock", "compra", "tabla_markdown"]
