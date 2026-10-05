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
    "latón, tubo 12/9": Stock("tubo", "tubo de latón 12 × 1,5"),
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
        if largos and ficha.cantidad % len(largos) == 0:
            return largos * (ficha.cantidad // len(largos))
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


@dataclass(frozen=True)
class Fijacion:
    designacion: str
    cantidad: int
    para: str
    grupo: str
    """El grupo donde se monta, **declarado**: es el que le da su marca
    (`docs/numeracion.json`). Una línea que sirve a dos grupos se parte en
    dos, porque una marca vive en un grupo y nada más."""
    en_3d: str = ""
    """El prefijo de la pieza colocada que la dibuja (`emit.montaje.colocar`)."""
    por_pieza: int = 1
    """Cuántas de esta línea lleva cada pieza colocada: los dos M3 de un
    sector van en un mismo sólido, con sus tuercas."""

    @property
    def clave(self) -> str:
        """Lo que la distingue en la numeración: la designación sola se repite
        (dos DIN 912 M3 × 16 en sitios distintos)."""
        return f"{self.designacion} · {self.para}"


def tornilleria() -> list[Fijacion]:
    """La tornillería y la retención de una plataforma, por norma y medida.

    Las cantidades que dependen de una pieza salen de su `cantidad` en
    `LISTADO`: si cambia el número de sectores o de collares, cambia aquí. Los
    largos son los de catálogo que cubren el paquete que aprietan.
    """
    n = {k: f.cantidad for k, f in LISTADO.items()}
    union = 2 * n["sector"]  # dos M3 por sector, a través de calzo y seguidor
    rodillos = n["casquillo_rodillo"]
    return [
        Fijacion(
            "DIN 912 M3 × 16",
            union,
            "sector, calzo y seguidor",
            "amplificador",
            en_3d="tornillos_sector_",
            por_pieza=2,
        ),
        Fijacion(
            "DIN 912 M3 × 16",
            n["apoyo_balancin"],
            "apoyos del balancín, del plato 2",
            "levantamiento",
            en_3d="tornillo_apoyo_",
        ),
        Fijacion(
            "DIN 7991 M3 × 30, cortado a 12,5 / 19,5 / 26,5",
            rodillos,
            "ejes de rodillo",
            "seguidores",
            en_3d="eje_rodillo_",
        ),
        Fijacion(
            "DIN 7991 M3 × 10",
            3,
            "punta roscada de cada poste, sobre el plato 3",
            "bastidor",
            en_3d="tornillo_poste_",
        ),
        Fijacion(
            "DIN 439 M3 (tuerca fina)",
            union,
            "unión del sector",
            "amplificador",
            en_3d="tornillos_sector_",
            por_pieza=2,
        ),
        Fijacion(
            "DIN 439 M3 (tuerca fina)",
            rodillos,
            "ejes de rodillo",
            "seguidores",
            en_3d="eje_rodillo_",
        ),
        Fijacion(
            "DIN 912 M4 × 16",
            n["mordaza"],
            "mordaza al sector, por su ranura",
            "amplificador",
            en_3d="tornillo_mordaza_",
        ),
        Fijacion(
            "DIN 439 M4 (tuerca fina)",
            n["mordaza"],
            "bajo el sector",
            "amplificador",
            en_3d="tornillo_mordaza_",
        ),
        Fijacion(
            "DIN 913 M3 × 6, punta plana",
            n["mordaza"],
            "aprieta la cinta en la mordaza",
            "amplificador",
            en_3d="prisionero_mordaza_",
        ),
        Fijacion(
            "DIN 913 M3 × 4, punta plana",
            n["collar"],
            "collares",
            "bastidor",
            en_3d="prisionero_collar_",
        ),
        Fijacion(
            "DIN 913 M3 × 4, punta plana",
            n["casquillo_rueda"],
            "casquillo de la rueda",
            "accionamiento",
            en_3d="prisionero_rueda",
        ),
        Fijacion(
            "DIN 913 M3 × 4, punta plana",
            n["pinza"],
            "pinza del portaminas",
            "portalapiz",
            en_3d="prisionero_pinza",
        ),
        Fijacion(
            "DIN 912 M2 × 3",
            n["tambor"],
            "extremos de la cinta en el tambor",
            "amplificador",
            en_3d="tornillo_tambor_",
        ),
        Fijacion(
            "DIN 912 M2 × 4",
            2 * n["lamina_flexura"],
            "pestañas de las láminas",
            "portalapiz",
            en_3d="tornillo_lamina_",
        ),
        Fijacion(
            "DIN 912 M2 × 8",
            n["orejeta_mesa"],
            "mesa a sus orejetas",
            "levantamiento",
            en_3d="tornillo_orejeta_",
        ),
        Fijacion(
            "DIN 912 M2 × 25",
            n["soporte_mesa"],
            "soportes de la mesa, desde bajo la base",
            "levantamiento",
            en_3d="tornillo_soporte_",
        ),
        Fijacion(
            "DIN 705 Ø10, anillo de ajuste",
            n["eje_pivote"],
            "bajo cada brazo proximal",
            "cinco_barras",
            en_3d="anillo_proximal_",
        ),
        Fijacion(
            "DIN 6799 para eje Ø10",
            n["eje_pivote"],
            "sobre cada tambor",
            "amplificador",
            en_3d="circlip_tambor_",
        ),
        Fijacion(
            "DIN 6799 para eje Ø10",
            n["munon"] + n["garra"],
            "bajo el muñón y sobre el muelle de la garra",
            "entre_puntos",
            en_3d="circlip_garra_",
        ),
        Fijacion(
            "DIN 6799 para eje Ø6",
            n["bulon_tirante"],
            "bulón del tirante",
            "levantamiento",
            en_3d="circlip_bulon",
        ),
        Fijacion(
            "DIN 6799 para eje Ø4",
            2 * n["eje_balancin"],
            "eje del balancín, por fuera",
            "levantamiento",
            en_3d="circlip_balancin_",
        ),
        Fijacion(
            "DIN 6799 para eje Ø1,5",
            2 * n["eje_mesa_movil"] + n["eje_mesa_fijo"],
            "ejes de la mesa",
            "levantamiento",
            en_3d="circlip_mesa_",
        ),
        Fijacion(
            "DIN 7 Ø2 × 16",
            n["garra"],
            "pasador de la garra",
            "entre_puntos",
            en_3d="pasador_garra",
        ),
        Fijacion(
            "DIN 988 6 × 12 × 0,5",
            n["perno_codo"],
            "arandela de cada codo del cinco barras",
            "cinco_barras",
            en_3d="arandela_codo_",
        ),
        Fijacion(
            "DIN 7 Ø3 × 6",
            n["placa_tope"],
            "pasadores de tope, de pie en la placa",
            "seguidores",
            en_3d="pasador_tope_",
        ),
        Fijacion(
            "arandela de presión Ø2",
            n["bieleta"],
            "bieleta en el balancín",
            "levantamiento",
            en_3d="arandela_bieleta",
        ),
    ]


def tabla_tornilleria() -> str:
    filas = ["| Designación | Cantidad | Para |", "| --- | ---: | --- |"]
    filas += [f"| {f.designacion} | {f.cantidad} | {f.para} |" for f in tornilleria()]
    total = sum(f.cantidad for f in tornilleria())
    filas.append(f"| **total** | **{total}** | |")
    return "\n".join(filas) + "\n"


__all__ = [
    "CORTE",
    "MARGEN_DE_CHAPA",
    "STOCK",
    "Fijacion",
    "Linea",
    "Stock",
    "compra",
    "tabla_markdown",
    "tabla_tornilleria",
    "tornilleria",
]
