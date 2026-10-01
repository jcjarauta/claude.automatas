"""Contrasta un DXF contra `docs/contratos.json`, venga de donde venga.

    uv run python scripts/comparar_dxf.py pieza.dxf

Mide el archivo —radios, distancias entre centros, longitudes, tangencias— y
lo cruza contra la **ficha** de la pieza, que declara qué rasgos tiene que
tener y de qué cota sale cada uno.

**La ficha no es burocracia, es lo que hace que la comparación signifique
algo.** Buscar «alguna cota del contrato que valga 6» no comprueba nada: el
contrato tiene ochenta cotas y cualquier número redondo encuentra una. La
primera versión de este script daba por bueno un radio de 6 citando el ancho
del tambor del cabestrante, que no pinta nada en un brazo. Con ficha, un
rasgo sobrante y uno que falta son dos fallos distintos y los dos se ven.

**Funciona en los dos sentidos, y por eso existe.** El DXF puede ser el que
emita el compilador o el que exporte Onshape después de que alguien lo
dibuje; la comparación es la misma y es la única que detecta una deriva vaya
la geometría en la dirección que vaya. Sin esto, mandar la geometría por
archivo cambia un error de transcripción, que se ve, por uno silencioso.

**Lo que NO ve: las restricciones.** Un croquis puede tener la forma exacta y
estar completamente suelto, que es el peor estado porque se ve bien y se
mueve luego. Eso no viaja en un DXF. Quien dibuje tiene que comprobar en el
CAD que la pieza sale «totalmente definida»; aquí no hay manera.

Los gemelos cuentan: una cota de radio explica un diámetro y al revés, que es
como se tecleó.
"""

from __future__ import annotations

import argparse
import itertools
import json
import math
import sys
from dataclasses import dataclass, field
from pathlib import Path

import ezdxf

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.acotar import CONTRATOS, MM

TOLERANCIA = 1e-3
"""En milímetros. Una micra: por debajo de eso es ruido del formato, por
encima es una cota distinta. El DXF guarda bastantes más decimales."""

CAPAS_DE_ADORNO = frozenset(
    {
        "TEXT",
        "CENTERLINES",
        "CENTERMARKS",
        "VIRTUAL_SHARPS",
        "ANNOTATION_LINES",
        "ANNOTATION_TEXT",
        "TABLES",
        "IMAGES",
        "DETAIL_VIEW_BORDER",
        "DETAIL_VIEW_PARENT_BORDER",
        "SECTION_CUTTING_LINE",
        "ROTULO",
    }
)
"""Lo que Onshape y nuestro emisor ponen que no es la pieza. Un eje de
simetría mide lo que le dé la gana y no hay cota que lo explique."""


@dataclass(frozen=True)
class Ficha:
    """Qué rasgos tiene que tener la pieza, y de qué cota sale cada uno.

    `radios` es {cota: cuántos arcos o círculos de ese radio}. Contarlos
    importa: el distal tiene DOS cubos de 6 porque sus dos extremos son
    iguales, y uno solo sería otra pieza.
    """

    que_es: str
    radios: dict[str, int]
    entre_centros: tuple[str, ...] = ()
    segmentos: dict[str, int] = field(default_factory=dict)
    tangentes: int = 0
    ranura: tuple[str, str] = ()
    """(cota del recorrido, cota del radio) de una ranura recta.

    Una ranura tiene **dos** centros de arco que no son dos rasgos: son los
    extremos de un rasgo. Sin declararla, el barrido de distancias entre
    centros saca tres huérfanas de una pieza que solo tiene dos agujeros.
    """
    desde_datum: tuple[str, ...] = ()
    """Cotas del datum al centro de un rasgo, sobre +X.

    Son **derivadas** y existen porque la herramienta que dibuja el rasgo pide
    esos puntos y no el par (centro, recorrido): restar la mitad de cabeza se
    falla. Mismo caso que la cuerda de la cara plana.
    """
    voladizo: str = ""
    """Del datum al borde más cercano del contorno, hacia -X.

    Sitúa el contorno respecto del datum, que es lo que ninguna otra cota
    hace: largo y ancho dicen cuánto mide el bloque y no dónde está. Sin
    ella el bloque se puede dibujar centrado entre los tornillos —que es lo
    natural y lo que estaba mal— y la ranura se sale por el extremo.
    """
    simetrico: bool = False
    """El contorno es simétrico respecto del eje X.

    Es lo que sitúa la pieza a lo alto, y no hay cota que lo diga: una
    simetría no es un número. Declararla deja que el comparador la mire y
    que la hoja la dibuje, en vez de que el que acota tenga que deducirla.
    """
    cara_plana: str = ""
    """La cota del desplazamiento del eje al plano de la cara, **con signo**.

    La cuerda sola no la sitúa: en un agujero de Ø10 una cuerda de 6 cae a 4
    del centro, pero puede caer a +4 o a -4, y la cara mirando al lado
    contrario cala el brazo media vuelta girado. Es la misma pieza vista en
    el croquis y otra distinta montada.
    """
    datum: str = ""
    """La cota del rasgo que va en el ORIGEN, y de ahí a +X el siguiente.

    Un croquis importado llega con la forma y **sin una sola restricción**:
    exacto y suelto, que es el peor estado porque se ve bien y se mueve en
    cuanto alguien lo roza. La geometría no puede traer restricciones —ningún
    DXF las lleva— pero sí puede traer el sitio, y con el sitio bien elegido
    quedan solo dos clics que matan los tres grados de libertad del plano:

      1. coincidente: centro del rasgo datum  ·  origen        (quita x e y)
      2. coincidente: el centro siguiente     ·  eje X         (quita el giro)

    Por eso el datum es un agujero y no el centro de la pieza: un agujero ya
    está en el dibujo y se engancha solo. Un punto medio habría que
    construirlo, y lo que hay que construir se olvida.

    No hay un tercer grado de libertad escondido en el volteo: la D del
    agujero es simétrica respecto de X —`brazo_chaveta_angulo` vale cero— así
    que la pieza espejada es la misma. La propiedad que ahorra el brazo
    derecho ahorra también un constraint.
    """


FICHAS: dict[str, Ficha] = {
    "brazo_proximal": Ficha(
        "barra de dos cubos, con el agujero del eje en D",
        {
            "brazo_cubo_diametro_radio": 1,
            "brazo_extremo_diametro_radio": 1,
            "brazo_eje_diametro_radio": 1,
            "brazo_perno_diametro_radio": 1,
        },
        entre_centros=("brazo_proximal",),
        segmentos={"brazo_chaveta_cuerda": 1},
        tangentes=4,
        cara_plana="brazo_chaveta",
        datum="brazo_eje_diametro_radio",
    ),
    "brazo_distal": Ficha(
        "biela: los dos extremos iguales, sin cara plana",
        {"brazo_extremo_diametro_radio": 2, "brazo_perno_diametro_radio": 2},
        entre_centros=("brazo_distal",),
        tangentes=4,
        datum="brazo_perno_diametro_radio",
    ),
    "palanca_lapiz": Ficha(
        "como el proximal pero más corta",
        {
            "brazo_cubo_diametro_radio": 1,
            "brazo_extremo_diametro_radio": 1,
            "brazo_eje_diametro_radio": 1,
            "brazo_perno_diametro_radio": 1,
        },
        entre_centros=("brazo_palanca",),
        segmentos={"brazo_chaveta_cuerda": 1},
        tangentes=4,
        cara_plana="brazo_chaveta",
        datum="brazo_eje_diametro_radio",
    ),
    "mordaza": Ficha(
        "bloque, tornillo de apriete y ranura: el calaje vive aquí",
        {
            "mordaza_tornillo_diametro_radio": 1,
            "mordaza_fijacion_diametro_radio": 2,
        },
        segmentos={"mordaza_largo": 2, "mordaza_ancho": 2},
        desde_datum=("mordaza_ranura_cerca", "mordaza_ranura_lejos"),
        voladizo="mordaza_voladizo",
        simetrico=True,
        ranura=("mordaza_recorrido", "mordaza_fijacion_diametro_radio"),
        entre_centros=("mordaza_entre_tornillos",),
        datum="mordaza_tornillo_diametro_radio",
    ),
    "eje_pivote": Ficha(
        "sección del eje: Ø10 con una cara plana, sin ningún ángulo mecanizado",
        {"brazo_eje_diametro_radio": 1},
        segmentos={"brazo_chaveta_cuerda": 1},
        cara_plana="brazo_chaveta",
        datum="brazo_eje_diametro_radio",
    ),
    "sector": Ficha(
        "disco entero con agujero de paso: la cinta no necesita muesca",
        {
            "amplificador_sector_radio_mecanizado": 1,
            "amplificador_sector_agujero_diametro_radio": 1,
        },
        datum="amplificador_sector_agujero_diametro_radio",
    ),
    "tambor": Ficha(
        "cilindro liso, sin pestañas: la cinta va anclada por los dos extremos",
        {
            "amplificador_tambor_radio_mecanizado": 1,
            "brazo_eje_diametro_radio": 1,
        },
        datum="brazo_eje_diametro_radio",
    ),
}
"""Las piezas prismáticas de la plataforma. No hay marco genérico a propósito:
la regla del proyecto es concreto ahora, marco en la máquina 2."""


@dataclass(frozen=True)
class Hallazgo:
    """Un rasgo que falta, que sobra o que no mide lo que debería."""

    gravedad: str
    texto: str


@dataclass
class Informe:
    archivo: str
    pieza: str
    entidades: dict[str, int] = field(default_factory=dict)
    bien: list[str] = field(default_factory=list)
    hallazgos: list[Hallazgo] = field(default_factory=list)
    datum: str = ""
    """Cómo está situada la pieza. **No es un incumplimiento del contrato**:
    el contrato dice formas y distancias, no en qué punto del plano se
    dibujan. Es una convención de trabajo, y se informa aparte para que no
    se confunda un croquis colocado de otra manera con una pieza mal hecha."""

    @property
    def cuadra(self) -> bool:
        return not self.hallazgos


def cotas_en_mm() -> dict[str, float]:
    """El contrato en milímetros, **con los gemelos**.

    El exportador saca de cada cota circular su otra forma porque el CAD
    acota el diámetro por defecto; si el gemelo es lo que se teclea, el
    gemelo es lo que tiene que explicar lo que se mide. Los ángulos se
    quedan fuera: un DXF no los lleva como dato.
    """
    datos = json.loads(CONTRATOS.read_text(encoding="utf-8"))
    salida: dict[str, float] = {}
    for grupo in datos["contratos"]:
        for v in grupo["valores"]:
            if v["unidad"] != "m":
                continue
            nombre, valor = v["nombre"], float(v["valor"]) * MM
            salida[nombre] = valor
            if "radio" in nombre:
                salida[f"{nombre}_diametro"] = valor * 2.0
            elif "diametro" in nombre:
                salida[f"{nombre}_radio"] = valor / 2.0
    return salida


def _circulares(msp) -> list[tuple[tuple[float, float], float]]:
    salida = []
    for e in msp:
        if e.dxf.layer in CAPAS_DE_ADORNO:
            continue
        if e.dxftype() in ("CIRCLE", "ARC"):
            c = e.dxf.center
            salida.append(((round(c.x, 9), round(c.y, 9)), e.dxf.radius))
    return salida


def _segmentos(msp) -> list[tuple[tuple[float, float], tuple[float, float]]]:
    salida = []
    for e in msp:
        if e.dxf.layer in CAPAS_DE_ADORNO:
            continue
        if e.dxftype() == "LINE":
            a, b = e.dxf.start, e.dxf.end
            salida.append(((a.x, a.y), (b.x, b.y)))
        elif e.dxftype() == "LWPOLYLINE":
            puntos = [(p[0], p[1]) for p in e.get_points("xy")]
            if e.closed:
                puntos.append(puntos[0])
            salida += list(itertools.pairwise(puntos))
    return salida


def _tangente(a, b, circulares, tol) -> list[float]:
    """Si los dos extremos del segmento se apoyan en sendos círculos y es
    perpendicular al radio en los dos, es una tangente exterior.

    La perpendicularidad se impone, no se mira a ojo: es el error que este
    repo ya cometió dos veces seguidas con la cinta del cabestrante. Devuelve
    el coseno en cada contacto, que debería ser cero.
    """
    cosenos = []
    for p in (a, b):
        for centro, radio in circulares:
            if abs(math.dist(p, centro) - radio) > tol:
                continue
            v = (p[0] - centro[0], p[1] - centro[1])
            u = (b[0] - a[0], b[1] - a[1])
            cos = abs(v[0] * u[0] + v[1] * u[1]) / (radio * math.hypot(*u))
            if cos < 1e-6:
                cosenos.append(cos)
                break
    return cosenos if len(cosenos) == 2 else []


def comparar(ruta: Path, pieza: str, tol: float = TOLERANCIA) -> Informe:
    if pieza not in FICHAS:
        raise KeyError(f"no hay ficha de «{pieza}». Hay: {', '.join(sorted(FICHAS))}")
    ficha, cotas = FICHAS[pieza], cotas_en_mm()
    doc = ezdxf.readfile(str(ruta))
    msp = doc.modelspace()
    inf = Informe(archivo=ruta.name, pieza=pieza)
    for e in msp:
        inf.entidades[e.dxftype()] = inf.entidades.get(e.dxftype(), 0) + 1

    circulares, segmentos = _circulares(msp), _segmentos(msp)

    # --- radios: cada rasgo declarado, con su recuento ---
    pendientes = list(circulares)
    for nombre, cuantos in ficha.radios.items():
        if nombre not in cotas:
            inf.hallazgos.append(Hallazgo("contrato", f"la ficha cita «{nombre}», que no está"))
            continue
        esperado = cotas[nombre]
        casan = [c for c in pendientes if abs(c[1] - esperado) <= tol]
        for c in casan:
            pendientes.remove(c)
        if len(casan) == cuantos:
            inf.bien.append(f"R{esperado:g} ×{cuantos}   #cota.{nombre}")
        else:
            inf.hallazgos.append(
                Hallazgo(
                    "falta" if len(casan) < cuantos else "sobra",
                    f"#cota.{nombre} pide {cuantos} arco(s) de R{esperado:g} y hay {len(casan)}",
                )
            )
    for centro, radio in pendientes:
        inf.hallazgos.append(
            Hallazgo(
                "huerfano",
                f"R{radio:.4f} en ({centro[0]:g},{centro[1]:g}) no lo explica "
                "ninguna cota de esta pieza",
            )
        )

    # --- del datum al centro de un rasgo ---
    for nombre in ficha.desde_datum:
        esperado = cotas[nombre]
        if any(abs(c[0] - esperado) <= tol and abs(c[1]) <= tol for c, _ in circulares):
            inf.bien.append(f"centro a {esperado:g} del datum   #cota.{nombre}")
        else:
            inf.hallazgos.append(
                Hallazgo("falta", f"#cota.{nombre} pide un centro a {esperado:g} del datum")
            )

    # --- dónde empieza el contorno respecto del datum ---
    if ficha.voladizo:
        esperado = cotas[ficha.voladizo]
        bordes = [min(a[0], b[0]) for a, b in segmentos if abs(a[0] - b[0]) <= tol]
        if not bordes:
            inf.hallazgos.append(
                Hallazgo("falta", f"#cota.{ficha.voladizo}: no hay ningún borde vertical")
            )
        elif abs(min(bordes) + esperado) <= tol:
            inf.bien.append(f"borde a {esperado:g} del datum   #cota.{ficha.voladizo}")
        else:
            inf.hallazgos.append(
                Hallazgo(
                    "falta",
                    f"#cota.{ficha.voladizo} pide el borde a {-esperado:+g} del datum "
                    f"y está a {min(bordes):+g}: el contorno no está donde dice el contrato",
                )
            )

    # --- simetría respecto del eje X ---
    if ficha.simetrico:
        altos = [p[1] for a, b in segmentos for p in (a, b)]
        altos += [c[1] + s * r for c, r in circulares for s in (-1, 1)]
        if altos and abs(max(altos) + min(altos)) <= tol:
            inf.bien.append("contorno simétrico respecto del eje X")
        else:
            inf.hallazgos.append(
                Hallazgo(
                    "falta",
                    f"la pieza debería ser simétrica respecto del eje X y va de "
                    f"{min(altos):+g} a {max(altos):+g}",
                )
            )

    # --- la ranura: dos arcos que son UN rasgo ---
    circulares_sueltos = list(circulares)
    if ficha.ranura:
        recorrido, radio_cota = cotas[ficha.ranura[0]], cotas[ficha.ranura[1]]
        extremos = [c for c in circulares_sueltos if abs(c[1] - radio_cota) <= tol]
        par = [
            (a, b)
            for i, a in enumerate(extremos)
            for b in extremos[i + 1 :]
            if abs(math.dist(a[0], b[0]) - recorrido) <= tol
        ]
        if par:
            a, b = par[0]
            circulares_sueltos.remove(a)
            circulares_sueltos.remove(b)
            medio = ((a[0][0] + b[0][0]) / 2, (a[0][1] + b[0][1]) / 2)
            circulares_sueltos.append((medio, radio_cota))
            inf.bien.append(f"ranura de {recorrido:g} de recorrido   #cota.{ficha.ranura[0]}")
        else:
            inf.hallazgos.append(
                Hallazgo(
                    "falta",
                    f"#cota.{ficha.ranura[0]}: no hay dos arcos de R{radio_cota:g} "
                    f"separados {recorrido:g}",
                )
            )

    # --- distancias entre centros ---
    centros = sorted({c for c, _ in circulares_sueltos})
    distancias = [
        math.dist(a, b)
        for i, a in enumerate(centros)
        for b in centros[i + 1 :]
        if math.dist(a, b) > tol
    ]
    for nombre in ficha.entre_centros:
        esperado = cotas[nombre]
        casan = [d for d in distancias if abs(d - esperado) <= tol]
        for d in casan:
            distancias.remove(d)
        if casan:
            inf.bien.append(f"entre centros {esperado:g}   #cota.{nombre}")
        else:
            cerca = f", la más próxima {min(distancias, default=0.0):.4f}" if distancias else ""
            inf.hallazgos.append(
                Hallazgo("falta", f"#cota.{nombre} pide {esperado:g} entre centros{cerca}")
            )
    for d in distancias:
        inf.hallazgos.append(Hallazgo("huerfano", f"{d:.4f} entre dos centros, sin cota"))

    # --- segmentos: la cuerda de la cara plana y poco más. Una tangente no
    # es una cota, la coloca la propia tangencia, así que se aparta antes.
    cosenos: list[float] = []
    sueltos = []
    for a, b in segmentos:
        if math.dist(a, b) <= tol:
            continue
        toca = _tangente(a, b, circulares, tol)
        if toca:
            cosenos += toca
        else:
            sueltos.append(math.dist(a, b))
    for nombre, cuantos in ficha.segmentos.items():
        esperado = cotas[nombre]
        casan = [x for x in sueltos if abs(x - esperado) <= tol]
        for x in casan:
            sueltos.remove(x)
        if len(casan) == cuantos:
            inf.bien.append(f"segmento {esperado:g} ×{cuantos}   #cota.{nombre}")
        else:
            inf.hallazgos.append(
                Hallazgo(
                    "falta" if len(casan) < cuantos else "sobra",
                    f"#cota.{nombre} pide {cuantos} segmento(s) de {esperado:g} y hay {len(casan)}",
                )
            )
    for x in sueltos:
        inf.hallazgos.append(Hallazgo("huerfano", f"segmento de {x:.4f} sin cota ni tangencia"))

    # --- la cara plana, con signo ---
    if ficha.cara_plana:
        esperado = cotas[ficha.cara_plana]
        cuerda = cotas[next(iter(ficha.segmentos))] if ficha.segmentos else 0.0
        datum = min(
            (c for c, r in circulares if abs(r - cotas[ficha.datum]) <= tol),
            key=lambda c: math.hypot(*c),
            default=None,
        )
        planas = [
            ((a[0] + b[0]) / 2 - (datum[0] if datum else 0.0))
            for a, b in segmentos
            if abs(math.dist(a, b) - cuerda) <= tol and abs(a[0] - b[0]) <= tol
        ]
        if not planas:
            inf.hallazgos.append(
                Hallazgo("falta", f"#cota.{ficha.cara_plana}: no hay ninguna cara plana vertical")
            )
        elif any(abs(x - esperado) <= tol for x in planas):
            inf.bien.append(f"cara plana a {esperado:g} del eje   #cota.{ficha.cara_plana}")
        else:
            inf.hallazgos.append(
                Hallazgo(
                    "falta",
                    f"#cota.{ficha.cara_plana} pide la cara a {esperado:+g} del eje y está a "
                    f"{planas[0]:+g}: mirando al otro lado cala el brazo media vuelta girado",
                )
            )

    # --- dónde está puesta: ni cota ni incumplimiento, convención ---
    if ficha.datum:
        esperado = cotas[ficha.datum]
        en_origen = [c for c, r in circulares if abs(r - esperado) <= tol and math.hypot(*c) <= tol]
        otros = [c for c, _ in circulares if math.hypot(*c) > tol]
        if not en_origen:
            inf.datum = (
                f"el rasgo datum (#cota.{ficha.datum}) NO está en el origen: "
                "hay que anclarla a mano, y lo que se ancla a mano se ancla mal"
            )
        elif otros and any(abs(c[1]) <= tol and c[0] > tol for c in otros):
            inf.datum = (
                "datum en el origen y el siguiente centro sobre +X: "
                "dos coincidentes y queda totalmente definida"
            )
        elif not otros and ficha.cara_plana:
            # Una pieza de un solo centro —la sección de un eje— no tiene un
            # «centro siguiente». Lo que la orienta es la cara plana, y con
            # su normal en +X el anclaje sigue siendo dos coincidentes.
            inf.datum = (
                "datum en el origen y la cara plana sobre +X: "
                "dos coincidentes y queda totalmente definida"
            )
        else:
            inf.datum = (
                "datum en el origen, pero el segundo centro no cae sobre +X: "
                "el giro hay que quitarlo con una cota angular"
            )

    # --- tangencias ---
    if ficha.tangentes:
        if len(cosenos) == ficha.tangentes:
            inf.bien.append(
                f"{len(cosenos)} contactos tangentes, perpendicularidad peor {max(cosenos):.1e}"
            )
        else:
            inf.hallazgos.append(
                Hallazgo(
                    "falta" if len(cosenos) < ficha.tangentes else "sobra",
                    f"la ficha pide {ficha.tangentes} contactos tangentes y hay "
                    f"{len(cosenos)}: el contorno no son tangentes de verdad",
                )
            )
    return inf


def adivinar(ruta: Path, tol: float = TOLERANCIA) -> str:
    """Qué ficha cuadra, cuando nadie lo dice. La que menos fallos deje."""
    return min(FICHAS, key=lambda p: len(comparar(ruta, p, tol).hallazgos))


def informe(inf: Informe) -> str:
    marca = {
        "falta": "FALTA   ",
        "sobra": "SOBRA   ",
        "huerfano": "HUÉRFANO",
        "contrato": "FICHA   ",
    }
    lineas = [
        f"{inf.archivo}  ·  {inf.pieza}",
        f"  {FICHAS[inf.pieza].que_es}",
        "  " + " · ".join(f"{n} {t}" for t, n in sorted(inf.entidades.items())),
        "",
    ]
    lineas += [f"  = {b}" for b in inf.bien]
    if inf.datum:
        lineas += ["", f"  · situación      {inf.datum}"]
    if inf.hallazgos:
        lineas.append("")
        lineas += [f"  ! {marca[h.gravedad]}  {h.texto}" for h in inf.hallazgos]
    lineas += [
        "",
        "  cuadra con el contrato"
        if inf.cuadra
        else f"  {len(inf.hallazgos)} cosa(s) que no cuadran",
        "",
        "  El DXF no lleva las restricciones: comprueba en el CAD que la pieza",
        "  sale «totalmente definida». Un croquis exacto y suelto se ve bien y",
        "  se mueve luego.",
    ]
    return "\n".join(lineas) + "\n"


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("dxf", type=Path, nargs="+")
    p.add_argument("--pieza", choices=sorted(FICHAS), help="por defecto, la que mejor cuadre")
    p.add_argument("--tol", type=float, default=TOLERANCIA, help="en mm")
    op = p.parse_args(argv)
    malos = 0
    for ruta in op.dxf:
        inf = comparar(ruta, op.pieza or adivinar(ruta, op.tol), op.tol)
        print(informe(inf))
        malos += not inf.cuadra
    return 1 if malos else 0


if __name__ == "__main__":
    raise SystemExit(main())
