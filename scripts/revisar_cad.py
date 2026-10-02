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


def _caja_y_cilindros(
    ruta: Path,
) -> tuple[tuple[float, float, float], list[tuple[float, list[float]]]]:
    """La caja envolvente en mm y los cilindros, con su diametro y su centro.

    Lo comparte todo lo que es una plancha con agujeros pasantes, que es casi
    todo el reloj. La varilla no lo usa porque ademas tiene un taladro ciego
    y hay que medir su fondo."""
    ent = _entidades(ruta)
    puntos = [
        p for p in (_numeros(a) for t, a in ent.values() if t == "CARTESIAN_POINT") if len(p) == 3
    ]
    ejes = {
        n: _numeros(ent[a.split(",")[1].strip().lstrip("#")][1])
        for n, (t, a) in ent.items()
        if t == "AXIS2_PLACEMENT_3D" and a.split(",")[1].strip().lstrip("#") in ent
    }
    mm = 1000.0
    caja = tuple((max(p[i] for p in puntos) - min(p[i] for p in puntos)) * mm for i in range(3))
    cilindros: list[tuple[float, list[float]]] = []
    for t, a in ent.values():
        if t != "CYLINDRICAL_SURFACE":
            continue
        trozos = [x.strip() for x in a.split(",")]
        centro = ejes.get(trozos[-2].lstrip("#"), [0.0, 0.0, 0.0])
        cilindros.append((float(trozos[-1]) * 2.0 * mm, [x * mm for x in centro]))
    # El origen del solido no es el canto: lo que importa es la posicion
    # relativa a la caja, asi que se referencia al minimo de cada eje.
    base = [min(p[i] for p in puntos) * mm for i in range(3)]
    cilindros = [(d, [c0[i] - base[i] for i in range(3)]) for d, c0 in cilindros]
    return caja, cilindros  # type: ignore[return-value]


def _filas_de_taladros(
    cilindros: list[tuple[float, list[float]]], diametro: float
) -> list[tuple[float, list[list[float]]]]:
    """Agrupa los taladros en filas por su distancia al canto de apriete.

    El canto de apriete es el de abajo, y es el datum del pendulo. Agrupar
    por ahi es lo que permite comprobar las dos filas del bloque -la del
    muelle y la del anclaje- sin saber de antemano cuantas hay.
    """
    filas: dict[float, list[list[float]]] = {}
    for d, centro in cilindros:
        if abs(d - diametro) > HOLGURA:
            continue
        # `_caja_y_cilindros` ya devuelve el centro referido al minimo de
        # cada eje, es decir al canto de apriete. No hay que volver a sumarle
        # nada: hacerlo daba 30 donde habia 10 y pasaba por error del dibujo.
        al_canto = round(centro[1], 2)
        filas.setdefault(al_canto, []).append(centro)
    return sorted((y, sorted(cs, key=lambda c0: c0[0])) for y, cs in filas.items())


def _medidas_dos_taladros(
    c: Contratos,
    ruta: Path,
    rotulo: str,
    clave_ancho: str,
    clave_alto: str,
    clave_espesor: str,
    esperadas: list[tuple[str, str, str]],
) -> list[Medida]:
    """Una plancha rectangular con filas de dos tornillos.

    El bloque y la placa son la misma comprobacion con otras tres cotas: se
    taladran juntos, asi que si no dan lo mismo es que no se taladraron
    juntos. La diferencia es cuantas filas lleva cada uno.

    `esperadas` son las filas, de abajo arriba: rotulo, contrato y clave de
    la distancia al canto de apriete.
    """
    v = c.contrato("suspension")
    (ancho, alto, espesor), cilindros = _caja_y_cilindros(ruta)
    medidas = [
        Medida(f"ancho de {rotulo}", v.valor(clave_ancho).en_mm, ancho),
        Medida(f"alto de {rotulo}", v.valor(clave_alto).en_mm, alto),
        Medida(f"espesor de {rotulo}", v.valor(clave_espesor).en_mm, espesor),
    ]

    tornillo = v.valor("soporte_tornillo_diametro").en_mm
    filas = _filas_de_taladros(cilindros, tornillo)
    medidas.append(Medida("filas de taladros", float(len(esperadas)), float(len(filas))))
    medidas.append(
        Medida(
            "taladros, diametro",
            tornillo,
            tornillo if any(abs(d - tornillo) <= HOLGURA for d, _ in cilindros) else None,
        )
    )
    al_lado = v.valor("soporte_tornillo_al_lado").en_mm
    sep = v.valor("soporte_tornillo_separacion").en_mm

    for i, (titulo, contrato, clave) in enumerate(esperadas):
        esperado = c.valor(contrato, clave).en_mm
        if i >= len(filas):
            medidas.append(Medida(f"{titulo}, al canto de apriete", esperado, None))
            continue
        al_canto, agujeros = filas[i]
        medidas.append(Medida(f"{titulo}, al canto de apriete", esperado, al_canto))
        medidas.append(Medida(f"{titulo}, cuantos", 2.0, float(len(agujeros))))
        if len(agujeros) != 2:
            continue
        izq, der = agujeros
        medidas.append(Medida(f"{titulo}, separacion", sep, der[0] - izq[0]))
        # A los dos cantos y no a uno: con uno solo, un par bien separado
        # pero descentrado pasaria, y es el error que descoloca la placa.
        medidas.append(Medida(f"{titulo}, al canto izquierdo", al_lado, izq[0]))
        medidas.append(Medida(f"{titulo}, al canto derecho", al_lado, ancho - der[0]))
    return medidas


def _medidas_fleje_step(c: Contratos, ruta: Path) -> list[Medida]:
    """El fleje. Lo que se comprueba aqui y en ninguna otra pieza es que los
    dos agujeros caen en el tramo muerto: en el libre serian la entalla por
    la que rompe."""
    v = c.contrato("suspension")
    (ancho, largo, espesor), cilindros = _caja_y_cilindros(ruta)
    medidas = [
        Medida("ancho del fleje", v.valor("muelle_ancho").en_mm, ancho),
        Medida("largo del fleje", v.valor("muelle_largo").en_mm, largo),
        Medida("espesor del fleje", v.valor("muelle_espesor").en_mm, espesor),
    ]
    taladro = v.valor("muelle_taladro_diametro").en_mm
    agujeros = sorted(
        (c0 for d, c0 in cilindros if abs(d - taladro) <= HOLGURA), key=lambda c0: c0[1]
    )
    medidas.append(Medida("taladros, cuantos", 2.0, float(len(agujeros))))
    medidas.append(Medida("taladros, diametro", taladro, taladro if agujeros else None))
    if len(agujeros) != 2:
        return medidas

    # Una tira no dice cual es su extremo de arriba. Lo dice el contrato: las
    # dos cotas se miden desde el que entra en el soporte, y la pareja solo
    # encaja por un lado.
    cerca = v.valor("muelle_taladro_cerca").en_mm
    lejos = v.valor("muelle_taladro_lejos").en_mm
    desde_abajo = sorted(c0[1] for c0 in agujeros)
    desde_arriba = sorted(largo - y for y in desde_abajo)
    arriba = abs(desde_arriba[0] - cerca) + abs(desde_arriba[1] - lejos)
    abajo = abs(desde_abajo[0] - cerca) + abs(desde_abajo[1] - lejos)
    medido = desde_arriba if arriba <= abajo else desde_abajo
    medidas.append(Medida("taladro cerca, al extremo de arriba", cerca, medido[0]))
    medidas.append(Medida("taladro lejos, al extremo de arriba", lejos, medido[1]))
    for titulo, c0 in zip(("cerca", "lejos"), agujeros, strict=True):
        medidas.append(Medida(f"taladro {titulo}, al eje del ancho", ancho / 2.0, c0[0]))

    muerto = v.valor("muelle_empotrado").en_mm + v.valor("muelle_largo_libre").en_mm
    medidas.append(
        Medida(
            "el primer taladro empieza pasado el tramo libre",
            0.0,
            round(max(0.0, muerto - (medido[0] - taladro / 2.0)), 2),
        )
    )
    return medidas


def _medidas_escuadra_step(c: Contratos, ruta: Path) -> list[Medida]:
    """La tabla del banco R1.

    Es la unica pieza que se acota desde sus propios cantos y no desde el
    datum del pendulo, porque el datum -el canto de apriete del bloque- no es
    ningun borde de esta tabla. Aqui se comprueba exactamente eso.
    """
    b = c.contrato("banco_pendulo")
    (ancho, alto, espesor), cilindros = _caja_y_cilindros(ruta)
    medidas = [
        Medida("ancho de la tabla", b.valor("escuadra_ancho").en_mm, ancho),
        Medida("alto de la tabla", b.valor("escuadra_alto").en_mm, alto),
        Medida("espesor de la tabla", b.valor("escuadra_espesor").en_mm, espesor),
    ]
    guia = b.valor("escuadra_taladro_diametro").en_mm
    agujeros = sorted((c0 for d, c0 in cilindros if abs(d - guia) <= HOLGURA), key=lambda c0: c0[0])
    medidas.append(Medida("taladros, cuantos", 2.0, float(len(agujeros))))
    medidas.append(Medida("taladros, diametro", guia, guia if agujeros else None))
    # El taladro de guia es mas estrecho que el del bloque, y confundirlos es
    # el error que deja el tirafondo sin agarre.
    paso = c.valor("anclaje", "anclaje_tornillo_diametro").en_mm
    medidas.append(
        Medida(
            "no se taladro al paso del bloque",
            0.0,
            round(max(0.0, guia + HOLGURA - min((d for d, _ in cilindros), default=paso)), 2),
        )
    )
    if len(agujeros) != 2:
        return medidas
    izq, der = agujeros
    medidas.append(
        Medida(
            "separacion entre taladros",
            c.valor("anclaje", "anclaje_tornillo_separacion").en_mm,
            der[0] - izq[0],
        )
    )
    al_lado = b.valor("escuadra_taladro_al_lado").en_mm
    medidas.append(Medida("del canto izquierdo al taladro", al_lado, izq[0]))
    medidas.append(Medida("del canto derecho al taladro", al_lado, ancho - der[0]))
    # El canto de ARRIBA, que es el que se pone a nivel al montar.
    medidas.append(
        Medida(
            "del canto de arriba al taladro",
            b.valor("escuadra_taladro_al_canto").en_mm,
            alto - izq[1],
        )
    )
    return medidas


def _medidas_soporte_step(c: Contratos, ruta: Path) -> list[Medida]:
    return _medidas_dos_taladros(
        c,
        ruta,
        "el bloque",
        "soporte_ancho",
        "soporte_alto",
        "soporte_espesor",
        [
            ("taladros del muelle", "suspension", "soporte_tornillo_al_canto"),
            ("taladros del anclaje", "anclaje", "anclaje_al_datum"),
        ],
    )


def _medidas_placa_step(c: Contratos, ruta: Path) -> list[Medida]:
    return _medidas_dos_taladros(
        c,
        ruta,
        "la placa",
        "soporte_placa_ancho",
        "soporte_placa_alto",
        "soporte_placa_espesor",
        [("taladros del muelle", "suspension", "soporte_tornillo_al_canto")],
    )


REVISORES = {"varilla": _medidas_varilla}
REVISORES_STEP = {
    "varilla": _medidas_varilla_step,
    "soporte": _medidas_soporte_step,
    "placa": _medidas_placa_step,
    "fleje": _medidas_fleje_step,
    "escuadra": _medidas_escuadra_step,
}


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
    partes.add_argument(
        "--pieza", default="varilla", choices=sorted(set(REVISORES) | set(REVISORES_STEP))
    )
    partes.add_argument("--contratos", type=Path, default=RELOJ)
    opciones = partes.parse_args(argv)

    es_step = opciones.fichero.suffix.lower() in (".step", ".stp")
    tabla = REVISORES_STEP if es_step else REVISORES
    if opciones.pieza not in tabla:
        clase = "STEP" if es_step else "DXF"
        print(f"no se revisa el {clase} de '{opciones.pieza}' todavia", file=sys.stderr)
        return 2
    medidas = tabla[opciones.pieza](cargar(opciones.contratos), opciones.fichero)
    texto, todo = informe(medidas)
    print(texto)
    return 0 if todo else 1


if __name__ == "__main__":
    sys.exit(main())
