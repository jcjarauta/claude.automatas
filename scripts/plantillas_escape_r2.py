"""Plantillas 1:1 del banco de escape R2, para probar tolerancias.

    uv run python scripts/plantillas_escape_r2.py                 # x2 en A3
    uv run python scripts/plantillas_escape_r2.py --escala 1 --formato A4

Un solo PDF, todo a 1:1, cuatro clases de hoja:

1. **Hoja de banco.** Se pega en el tablero: las dos cruces de taladro a la
   distancia exacta entre centros, el perfil de la rueda con su banda de
   tolerancia para verificar la rueda cortada poniendola encima, y una escala
   de angulos centrada en el eje del ancora para leer con una aguja a que
   angulo del pendulo salta cada diente.
2. **Plantillas de corte.** Rueda (maciza: los radios son de la definitiva),
   yugo y un juego de paletas de varios anchos.
3. **Protocolo y tabla de resultados**, para apuntar diente a diente.

**Nada se emite sin pasar la envolvente** (regla 5): antes de escribir se
juzga el escape con cada ancho de paleta, sin error y con error de sierra, y
el resultado va impreso en el protocolo.
"""

from __future__ import annotations

import argparse
import dataclasses
import math
import sys
from pathlib import Path

from shapely import affinity
from shapely.geometry import LineString, Polygon

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from compile.escape_r2 import amplitud, geometria
from core.reloj.graham import (
    AncoraGraham,
    RuedaGraham,
    centro_ranura,
    contorno_rueda,
    juzgar,
    nariz,
    paleta,
    yugo,
)
from core.units import Metros, a_grados, a_mm, mm
from emit.layout import (
    LADO_CALIBRACION,
    MARGEN,
    Circulo,
    Formato,
    Lamina,
    Texto,
    Trazo,
    cuadro_de_calibracion,
    maquetar_juego,
)
from emit.pieza import Pieza, Polilinea, Taladro, Veta
from emit.template import escribir_pdf

ESPESOR = mm(4.0)
RANURA_LARGO = 8.0  # mm a escala 1, como el contrato
RANURA_ANCHO = 4.2  # mm: paso del M4, no escala
TOLERANCIA_SIERRA = mm(0.3)


def _f(valor: float, decimales: int = 2) -> str:
    return f"{valor:.{decimales}f}".replace(".", ",")


SIMPLIFICAR = mm(0.01)


def _puntos(g: Polygon, simplificar: Metros = SIMPLIFICAR) -> list[tuple[Metros, Metros]]:
    anillo = g.simplify(simplificar).exterior.coords
    return [(Metros(x), Metros(y)) for x, y in list(anillo)[:-1]]


# ---------------------------------------------------------------------------
# Piezas
# ---------------------------------------------------------------------------


def pieza_rueda(rueda: RuedaGraham, ancora: AncoraGraham, conjunto: str) -> Pieza:
    return Pieza(
        nombre=f"rueda Ø{_f(2 * a_mm(rueda.radio_punta), 0)} · papel hacia la esfera",
        numero="2.1-R2",
        conjunto=conjunto,
        material="contrachapado de abedul",
        espesor=ESPESOR,
        cantidad=1,
        veta=Veta.INDIFERENTE,
        contorno=_puntos(contorno_rueda(rueda)),
        taladros=[Taladro(centro=(Metros(0.0), Metros(0.0)), diametro=ancora.eje)],
    )


def pieza_yugo(ancora: AncoraGraham, conjunto: str) -> Pieza:
    p = ancora.eje_ancora
    taladros = [Taladro(centro=(Metros(p[0]), Metros(p[1])), diametro=ancora.eje)]
    for lado in ("entrada", "salida"):
        c = centro_ranura(ancora, lado)  # type: ignore[arg-type]
        taladros.append(Taladro(centro=(Metros(c[0]), Metros(c[1])), diametro=mm(RANURA_ANCHO)))
    return Pieza(
        nombre="yugo · papel hacia la esfera",
        numero="2.2-R2",
        conjunto=conjunto,
        material="contrachapado de abedul",
        espesor=ESPESOR,
        cantidad=1,
        veta=Veta.LARGO,
        contorno=_puntos(yugo(ancora)),
        taladros=taladros,
    )


def piezas_paleta(ancora: AncoraGraham, ancho: Metros, escala: float, conjunto: str) -> list[Pieza]:
    """Las dos paletas de un ancho, giradas con el dedo hacia arriba y la nariz
    abajo. La ranura va como dos taladros en sus extremos mas su contorno: se
    taladra y se sierra entre ellos."""
    a = dataclasses.replace(ancora, ancho_trabajo=ancho)
    salida = []
    for lado, giro in (("entrada", -45.0), ("salida", 45.0)):
        g = paleta(a, lado)  # type: ignore[arg-type]
        n = nariz(a, lado)  # type: ignore[arg-type]
        c = centro_ranura(a, lado)  # type: ignore[arg-type]
        origen = (0.0, 0.0)
        g = affinity.rotate(g, giro, origin=origen)
        reposo = affinity.rotate(Polygon([n.reposo, n.caida, c]), giro, origin=origen)
        cx, cy = affinity.rotate(LineString([c, c]), giro, origin=origen).coords[0]
        semi = mm((RANURA_LARGO * escala - RANURA_ANCHO) / 2)
        extremos = [(cx, cy - semi), (cx, cy + semi)]
        ranura = LineString(extremos).buffer(mm(RANURA_ANCHO) / 2, 16)
        x_reposo = reposo.exterior.coords[0][0]
        x_caida = reposo.exterior.coords[1][0]
        cara = "izquierda" if x_reposo < x_caida else "derecha"
        letra = "E" if lado == "entrada" else "S"
        salida.append(
            Pieza(
                nombre=f"{lado} {_f(a_mm(ancho), 1)} · reposo {cara[:3]}.",
                numero=f"2.3-{letra}-{_f(a_mm(ancho), 1)}",
                conjunto=conjunto,
                material="laton o haya",
                espesor=ESPESOR,
                cantidad=1,
                veta=Veta.INDIFERENTE,
                contorno=_puntos(g, mm(0.002)),
                taladros=[
                    Taladro(centro=(Metros(x), Metros(y)), diametro=mm(RANURA_ANCHO))
                    for x, y in extremos
                ],
                referencias=[Polilinea(puntos=_puntos(ranura), cerrada=True)],
            )
        )
    return salida


# ---------------------------------------------------------------------------
# Hoja de banco
# ---------------------------------------------------------------------------


def _anillo_mm(g: Polygon, dx: float, dy: float) -> tuple[tuple[float, float], ...]:
    return tuple((a_mm(Metros(x)) + dx, a_mm(Metros(y)) + dy) for x, y in g.exterior.coords)


def hoja_de_banco(
    rueda: RuedaGraham, ancora: AncoraGraham, formato: Formato, conjunto: str
) -> Lamina:
    ancho, alto = formato.medidas
    entre = a_mm(ancora.entre_centros)
    r = a_mm(rueda.radio_punta)
    x0 = MARGEN + r + 8.0
    y0 = MARGEN + r + 6.0
    px, py = x0, y0 + entre
    trazos: list[Trazo] = []
    circulos: list[Circulo] = []
    textos: list[Texto] = []

    # perfil ideal y banda de tolerancia
    ideal = contorno_rueda(rueda)
    trazos.append(Trazo("marca", _anillo_mm(ideal, x0, y0), cerrado=True))
    for d in (TOLERANCIA_SIERRA, -TOLERANCIA_SIERRA):
        trazos.append(Trazo("oculta", _anillo_mm(ideal.buffer(d, 64), x0, y0), cerrado=True))
    # las paletas nominales, donde van con el pendulo vertical
    for lado in ("entrada", "salida"):
        trazos.append(
            Trazo("referencia", _anillo_mm(paleta(ancora, lado), x0, y0), cerrado=True)  # type: ignore[arg-type]
        )
    # los dos ejes
    for cx, cy, etiqueta in ((x0, y0, "eje de la rueda"), (px, py, "eje del ancora")):
        radio = a_mm(ancora.eje) / 2
        circulos.append(Circulo("taladro", (cx, cy), radio))
        brazo = radio + 6.0
        trazos.append(Trazo("taladro", ((cx - brazo, cy), (cx + brazo, cy))))
        trazos.append(Trazo("taladro", ((cx, cy - brazo), (cx, cy + brazo))))
        textos.append(
            Texto(cx + brazo + 1.5, cy + 1.2, f"Ø{_f(a_mm(ancora.eje), 0)} · {etiqueta}", 3.0, True)
        )
    trazos.append(Trazo("referencia", ((x0, y0), (px, py))))
    textos.append(Texto(x0 + 4.0, y0 + r + (entre - r) * 0.55, f"{_f(entre)} mm", 3.6, True))
    textos.append(
        Texto(x0 + 4.0, y0 + r + (entre - r) * 0.55 - 5.0, "entre centros: la cota critica", 3.0)
    )

    # escala de angulos centrada en el eje del ancora, para una aguja hacia arriba
    radio_escala = min(70.0 * max(1.0, entre / 63.64), alto - MARGEN - py - 14.0)
    for decimas in range(-40, 41, 5):
        grados = decimas / 10
        largo = 6.0 if decimas % 10 == 0 else 3.0
        a = math.radians(90 + grados)
        x1, y1 = px + radio_escala * math.cos(a), py + radio_escala * math.sin(a)
        x2, y2 = (
            px + (radio_escala + largo) * math.cos(a),
            py + (radio_escala + largo) * math.sin(a),
        )
        trazos.append(Trazo("marca", ((x1, y1), (x2, y2))))
        if decimas % 20 == 0:
            xt = px + (radio_escala + 10.0) * math.cos(a)
            yt = py + (radio_escala + 10.0) * math.sin(a)
            signo = "+" if grados > 0 else ""
            textos.append(Texto(xt, yt, f"{signo}{grados:.0f}", 2.8, anclaje="centro"))
    for grados_marca in (1.75, -1.75):
        a = math.radians(90 + grados_marca)
        x1 = px + (radio_escala - 6.0) * math.cos(a)
        y1 = py + (radio_escala - 6.0) * math.sin(a)
        x2 = px + radio_escala * math.cos(a)
        y2 = py + radio_escala * math.sin(a)
        trazos.append(Trazo("marca", ((x1, y1), (x2, y2))))
    puntas = [
        (
            px + radio_escala * math.cos(math.radians(90 + g / 10)),
            py + radio_escala * math.sin(math.radians(90 + g / 10)),
        )
        for g in range(-40, 41)
    ]
    trazos.append(Trazo("marca", tuple(puntas)))
    textos.append(
        Texto(
            px,
            py + radio_escala + 16.0,
            "angulo del pendulo (aguja en el eje del ancora)",
            3.0,
            anclaje="centro",
        )
    )
    textos.append(
        Texto(
            px,
            py + radio_escala - 9.0,
            "+ a la izquierda · marcas largas: cae a ±1,75",
            2.8,
            anclaje="centro",
        )
    )

    # calibracion y cabecera, arriba a la derecha
    cx0 = ancho - MARGEN - LADO_CALIBRACION
    cy0 = alto - MARGEN - LADO_CALIBRACION
    cal = cuadro_de_calibracion(cx0, cy0)
    trazos += cal.trazos
    textos += cal.textos
    xt, yt = cx0, cy0 - 8.0
    for linea, tam, negrita in (
        (f"{conjunto} · HOJA DE BANCO", 4.2, True),
        ("IMPRIMIR AL 100 %, SIN AJUSTAR", 3.6, True),
        ("Se pega en el tablero. Taladrar Ø10 en las cruces.", 3.0, False),
        ("Linea continua: la rueda ideal.", 3.0, False),
        (f"Punteadas: ±{_f(a_mm(TOLERANCIA_SIERRA), 1)} mm. Cada punta cortada", 3.0, False),
        ("tiene que caer entre las dos.", 3.0, False),
        ("A trazos: las paletas con el pendulo vertical.", 3.0, False),
    ):
        textos.append(Texto(xt, yt, linea, tam, negrita))
        yt -= tam + 2.2
    return Lamina(
        ancho=ancho, alto=alto, trazos=tuple(trazos), circulos=tuple(circulos), textos=tuple(textos)
    )


# ---------------------------------------------------------------------------
# Protocolo
# ---------------------------------------------------------------------------


def hoja_de_protocolo(
    rueda: RuedaGraham,
    ancora: AncoraGraham,
    anchos: list[Metros],
    resultados: list[str],
    formato: Formato,
    conjunto: str,
) -> Lamina:
    ancho, alto = formato.medidas
    trazos: list[Trazo] = []
    textos: list[Texto] = []
    cal = cuadro_de_calibracion(ancho - MARGEN - LADO_CALIBRACION, alto - MARGEN - LADO_CALIBRACION)
    trazos += cal.trazos
    textos += cal.textos
    r = a_mm(rueda.radio_punta)
    x, y = MARGEN, alto - MARGEN - 6.0
    textos.append(Texto(x, y, f"{conjunto} · PROTOCOLO", 5.0, True))
    y -= 8.0
    pasos = [
        "1. Medir el cuadro de 100 mm en los dos lados. Si no mide 100, no seguir.",
        "2. Pegar la hoja de banco en un tablero de 18 mm. Taladrar Ø10 en las",
        f"   dos cruces, a columna. Comprobar {_f(a_mm(ancora.entre_centros))} mm entre "
        "centros (±0,2).",
        "3. Rueda: cortar por fuera de la linea y lijar hasta ella. Montarla en su",
        "   eje sobre la hoja: cada punta debe caer entre las dos punteadas.",
        f"   Cuerda saltando cinco dientes: {_f(r)} mm (±0,2). Es el radio de punta.",
        "4. Paletas: taladrar Ø4,2 los dos extremos de la ranura y serrar entre",
        "   ellos. Limar la nariz a la linea: su ancho es lo que se prueba.",
        f"5. Montar las de {_f(a_mm(anchos[0]), 1)} mm. Fijar una aguja al eje del ancora,",
        "   hacia arriba, sobre la escala. Ajustar la ranura hasta que la rueda",
        "   caiga con la aguja en ±1,75.",
        "6. Empujar la rueda con el dedo y mover la aguja despacio de un lado a",
        "   otro, 31 veces: una vuelta de rueda. Apuntar a que angulo salta cada",
        "   diente en cada paleta. Marcar X si un diente se dispara o se atasca.",
        "7. Repetir con los otros anchos de paleta.",
    ]
    for linea in pasos:
        textos.append(Texto(x, y, linea, 3.3))
        y -= 5.0
    y -= 2.0
    textos.append(Texto(x, y, "Simulado antes de imprimir (core/reloj/graham.py):", 3.3, True))
    for linea in resultados:
        y -= 5.0
        textos.append(Texto(x, y, linea, 3.1))

    # tabla de resultados
    y_tabla = min(y - 10.0, alto - MARGEN - LADO_CALIBRACION - 10.0)
    columnas = (
        ["diente"] + [f"{_f(a_mm(w), 1)} {lado}" for w in anchos for lado in ("E", "S")] + ["notas"]
    )
    ancho_util = ancho - 2 * MARGEN
    anchos_col = [18.0] + [24.0] * (len(columnas) - 2)
    anchos_col.append(ancho_util - sum(anchos_col))
    filas = rueda.dientes
    alto_fila = min(6.5, (y_tabla - MARGEN - 8.0) / (filas + 1))
    xs = [MARGEN]
    for w in anchos_col:
        xs.append(xs[-1] + w)
    y_cab = y_tabla
    for i, titulo in enumerate(columnas):
        textos.append(Texto(xs[i] + 1.5, y_cab - alto_fila + 1.8, titulo, 2.9, True))
    for f in range(filas + 2):
        yy = y_cab - f * alto_fila
        trazos.append(Trazo("cajetin", ((xs[0], yy), (xs[-1], yy))))
    y_fin = y_cab - (filas + 1) * alto_fila
    for xx in xs:
        trazos.append(Trazo("cajetin", ((xx, y_cab), (xx, y_fin))))
    for f in range(filas):
        textos.append(Texto(xs[0] + 1.5, y_cab - (f + 2) * alto_fila + 1.8, f"{f + 1}", 2.9))
    textos.append(
        Texto(
            MARGEN,
            y_fin - 5.0,
            "Se espera ±1,75 en todas. Una desviacion de mas de 0,3 es un diente fuera "
            "de tolerancia.",
            3.0,
        )
    )
    return Lamina(ancho=ancho, alto=alto, trazos=tuple(trazos), textos=tuple(textos))


# ---------------------------------------------------------------------------


def main() -> int:
    partes = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    partes.add_argument("--escala", type=float, default=2.0)
    partes.add_argument("--formato", default="A3", choices=[f.value for f in Formato])
    partes.add_argument(
        "--anchos", default="2.2,2.5,2.75", help="anchos de paleta a escala 1, en mm"
    )
    partes.add_argument("--out", default="build")
    opciones = partes.parse_args()

    escala = opciones.escala
    formato = Formato(opciones.formato)
    rueda, ancora = geometria(escala)
    amp = amplitud()
    anchos = [mm(float(a) * escala) for a in opciones.anchos.split(",")]
    conjunto = f"Escape R2 x{_f(escala, 1).rstrip('0').rstrip(',')}"

    # La envolvente, antes de emitir nada.
    resultados = []
    for w in anchos:
        a = dataclasses.replace(ancora, ancho_trabajo=w)
        nominal = juzgar(rueda, a, amp)
        if not nominal.apto:
            print(f"paleta {a_mm(w):.2f} mm: NO pasa la envolvente sin error de sierra")
            for i in nominal.incidencias:
                print(f"  [{i.codigo}] {i.mensaje}")
            return 1
        con_sierra = sum(
            juzgar(rueda.con_error_de_sierra(TOLERANCIA_SIERRA, s), a, amp).apto for s in (1, 2, 3)
        )
        caida = a_grados(nominal.metricas["caida_min"]) - a_grados(rueda.espesor_punta)
        impulso = a_grados(nominal.metricas["impulso_rueda"])
        linea = (
            f"paleta {_f(a_mm(w), 1)} mm: impulso {_f(impulso, 1)}° de rueda, caida libre "
            f"{_f(caida, 1)}° · con sierra ±{_f(a_mm(TOLERANCIA_SIERRA), 1)}: "
            f"{con_sierra} de 3 ruedas funcionan"
        )
        print(linea)
        resultados.append(linea)

    piezas = [pieza_rueda(rueda, ancora, conjunto), pieza_yugo(ancora, conjunto)]
    for w in anchos:
        piezas += piezas_paleta(ancora, w, escala, conjunto)

    laminas = [hoja_de_banco(rueda, ancora, formato, conjunto)]
    laminas += maquetar_juego(piezas, formato)
    laminas.append(hoja_de_protocolo(rueda, ancora, anchos, resultados, formato, conjunto))

    destino = Path(opciones.out) / f"escape_r2_x{escala:g}_{formato.value}.pdf"
    escribir_pdf(laminas, destino)
    print(f"escrito {destino} · {len(laminas)} hojas {formato.value}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
