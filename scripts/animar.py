"""El escribiente moviéndose en el visor, y lo que escribe.

    uv run --group cad python scripts/animar.py                 # hola, 8 s por vuelta
    uv run --group cad python scripts/animar.py --fotogramas 120 --gif build/escribiente.gif
    uv run --group cad python scripts/animar.py --pedido demo/hola.json --velocidad 1
    uv run --group cad python scripts/animar.py --pedido demo/feliz_cumpleanos.json --reposo 2

Un pedido con renglones se anima con un cartucho por vuelta: escribe el
primero, sale por detrás entre los postes 1 y 2, entra el siguiente.

**La tinta sale a medida que la punta escribe**, letra a letra, y al
terminar la vuelta la máquina se para un momento con la frase entera y el
papel se borra para la vuelta siguiente.

Hace falta el visor abierto: en VS Code, «OCP CAD Viewer: Open viewer».

**Todo sale de recorrer las levas por su perfil cortado** (`estados(...,
camino="contacto")` y `compile.recorrido`): el giro de cada seguidor es el
de un rodillo apoyado en el polígono que va al DXF, y la tinta sobre la mesa
es lo que esa leva escribe. No se reproduce el programa en ningún paso.

**Cómo se anima sin tocar `colocar()`.** El visor gira cada nodo sobre su
origen. Así que cada parte que se mueve es un nodo puesto en su pivote, y sus
piezas van dentro **en el marco del nodo**: la colocación de θ = 0 deshecha
por la del nodo. Una rotación del nodo gira entonces las piezas alrededor de
su pivote de verdad. El distal va anidado bajo su proximal, en el codo: su
pista es un ángulo relativo y el lazo cerrado del cinco barras no hay que
resolverlo en el visor.

Lo que **no** se anima, porque no es un sólido rígido o su movimiento es
compuesto: las cintas, las patas de los muelles, la bieleta y las bielas de
la mesa. Se quedan en su posición de θ = 0.
"""

from __future__ import annotations

import argparse
import math
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

RAIZ = Path(__file__).resolve().parent.parent
RAIZ_DEL_ARBOL = "escribiente"

HUNDIDO = 2.0
"""mm que espera la tinta aún no escrita por debajo del papel: la mitad del
espesor de la mesa, que la tapa."""

LEVAS_SOCAVADAS: set[str] = set()
"""Las levas colocadas (leva_1…) que solo se pueden dibujar como silueta."""

QUIETAS = ("cinta_", "muelle_seguidor_", "bieleta", "biela_mesa_")
"""Lo que no se anima: deformable o con movimiento compuesto."""


@dataclass
class Nodo:
    """Un nodo del árbol del visor: dónde está, qué lleva y cómo se mueve."""

    nombre: str
    ubicacion: Any
    """`Location` del nodo en el marco de su padre."""
    piezas: list[tuple[str, Any]] = field(default_factory=list)
    """(nombre, sólido en el marco del nodo)."""
    hijos: list[Nodo] = field(default_factory=list)
    pista: tuple[str, list[Any]] | None = None
    """(acción del visor, valores por fotograma), relativos a θ = 0."""


def _miembros(nombre: str) -> str:
    """A qué nodo va cada pieza colocada; «fijo» si no se mueve o no se anima."""
    if nombre.startswith(QUIETAS):
        return "fijo"
    reglas = (
        (
            (
                "leva_",
                "eje_cartucho",
                "separador_",
                "pasador_indice",
                "garra",
                "pasador_garra",
                "eje_motriz",
                "munon",
                "rueda",
                "casquillo_rueda",
                "muelle_garra",
                "anillo_garra",
            ),
            "arbol",
        ),
        (("pinon", "eje_manivela", "volante", "manivela"), "manivela"),
        (("eje_balancin", "balancin", "palanca_lapiz", "bulon_tirante"), "balancin"),
        (("mesa", "orejeta_mesa_", "eje_mesa_movil_"), "mesa"),
        (("tirante",), "tirante"),
        (
            (
                "tubo_punta",
                "brazo_horquilla",
                "poste_horquilla",
                "pinza",
                "lamina_flexura_",
                "portaminas",
            ),
            "punta",
        ),
    )
    for prefijos, nodo in reglas:
        if nombre.startswith(prefijos) and not nombre.startswith("eje_mesa_fijo"):
            return nodo
    for i in (1, 2, 3):
        if nombre in {
            f"seguidor_{i}",
            f"rodillo_{i}",
            f"eje_rodillo_{i}",
            f"sector_{i}",
            f"calzo_sector_{i}",
            f"tornillos_sector_{i}",
            f"mordaza_{i}",
            f"tornillo_mordaza_{i}",
        } or (i == 3 and nombre == "casquillo_bieleta"):
            return f"seguidor_{i}"
    for n in (1, 2):
        if nombre in {f"proximal_{n}", f"eje_pivote_{n}", f"tambor_{n}", f"tornillo_tambor_{n}"}:
            return f"brazo_{n}"
        if nombre == f"distal_{n}":
            return f"distal_{n}"
    return "fijo"


SOCAVADA = " (socavada)"
"""Lo que se añade al nombre de una leva que solo se puede dibujar como
silueta: el visor la pinta en rojo."""


def _dibujable(pieza: Any) -> Any:
    """La leva tal cual si se puede construir su sólido; si su perfil se cruza
    consigo mismo, su silueta: el contorno exterior del polígono válido, que
    es lo que dejaría una fresa al recortarla.

    **Solo para mirarla.** `emit.step` no la arregla a propósito, porque es
    geometría de producción: una leva socavada no existe y el compilador ya
    la ha rechazado. Aquí se enseña para ver dónde y cuánto."""
    from shapely.geometry import Polygon

    from core.units import Metros
    from emit.step import solido_de_pieza

    try:
        solido_de_pieza(pieza)
        return pieza
    except Exception:
        valido = Polygon([(float(x), float(y)) for x, y in pieza.contorno]).buffer(0)
        mayor = max(getattr(valido, "geoms", [valido]), key=lambda g: g.area)
        contorno = [(Metros(x), Metros(y)) for x, y in list(mayor.exterior.coords)[:-1]]
        return pieza.model_copy(update={"contorno": contorno, "nombre": pieza.nombre + SOCAVADA})


def _centro(solido: Any) -> np.ndarray:
    caja = solido.bounding_box()
    return np.array(
        [
            (caja.min.X + caja.max.X) / 2,
            (caja.min.Y + caja.max.Y) / 2,
            (caja.min.Z + caja.max.Z) / 2,
        ]
    )


def _geometria_del_brazo(c: dict[str, float], estado: Any) -> dict[str, Any]:
    """Pivotes, giros y codos del cinco barras en un estado, como `colocar`."""
    from emit.montaje import _del_cinco_barras, _punta

    al = _del_cinco_barras(c)
    sep = c["brazo_separacion"] / 2.0
    lados = ((-sep, estado.psi_izquierdo), (sep, estado.psi_derecho))
    codos = [
        (x + c["brazo_proximal"] * math.cos(psi), c["brazo_proximal"] * math.sin(psi))
        for x, psi in lados
    ]
    punta = _punta(codos[0], codos[1], c["brazo_distal"])
    salida: dict[str, Any] = {"punta": al(punta)}
    for n, ((x, psi), codo) in enumerate(zip(lados, codos, strict=True), 1):
        salida[f"pivote_{n}"] = al((x, 0.0))
        salida[f"giro_{n}"] = psi + c["brazo_origen_giro"]
        salida[f"codo_{n}"] = al(codo)
        salida[f"distal_{n}"] = (
            math.atan2(punta[1] - codo[1], punta[0] - codo[0]) + c["brazo_origen_giro"]
        )
    return salida


PIEZAS_DEL_CARTUCHO = ("leva_", "eje_cartucho", "separador_", "pasador_indice")
"""Lo que sale con el cartucho: sus levas y su eje con separadores y pasador.
La garra, el muñón y el eje motriz son de la plataforma y se quedan."""

CAMBIO = 0.6
"""Segundos de animación en sacar un cartucho, y otros tantos en meter el
siguiente."""

APARTADO = 170.0
"""mm que se aparta, por su salida, el cartucho que no está escribiendo."""

ESTANTE = 30.0
"""mm entre un cartucho y el siguiente en la estantería de fuera: si
esperaran todos en el mismo sitio se dibujarían uno dentro de otro."""


@dataclass
class _Vuelta:
    """Lo que hace falta de un cartucho para animar su vuelta."""

    compilacion: Any
    levas: list[Any]
    todos: list[Any]
    recorrido: Any
    geos: list[dict[str, Any]] = field(default_factory=list)
    traslados: dict[str, list[list[float]]] = field(default_factory=dict)
    marcas: list[tuple[float, float]] = field(default_factory=list)


def construir(pedido: Path, fotogramas: int = 72, reposo: float = 0.0):
    """El árbol animable, sus tiempos y lo que escribe cada cartucho.
    Devuelve (raíz, tiempos, recorridos), un recorrido por vuelta.

    Un pedido con renglones (`compile.renglones`) se anima como se escribe:
    una vuelta por cartucho, y entre una y otra el cartucho sale por su sitio
    —entre los postes 1 y 2— y entra el siguiente. La tinta de cada vuelta
    se queda en el papel hasta el final. Con `reposo`, en segundos, la
    máquina se para con la tarjeta entera antes de borrarla y volver a
    empezar."""
    from build123d import Location, Plane, Polyline, Pos, Rot, Sphere, Vector

    from compile.conjunto import estados
    from compile.energia import rpm_del_arbol
    from compile.escribiente import SEGUIDORES, Escribiente, compilar
    from compile.recorrido import recorrer
    from compile.renglones import compilar_por_renglones, leer_pedido
    from emit.montaje import _del_cinco_barras, _levantamiento, alturas, colocar, taller
    from emit.plataforma import contrato_mm

    c = contrato_mm()
    maquina = Escribiente()
    datos = leer_pedido(pedido)
    if datos.renglones is None:
        compilaciones = [compilar(datos.escritura, maquina)]
    else:
        compilaciones = compilar_por_renglones(datos.escritura, datos.renglones, maquina)
    thetas = np.linspace(0.0, 2.0 * np.pi, max(fotogramas, 8), endpoint=False)
    seguidores = [maquina.seguidor(i) for i in range(len(SEGUIDORES))]
    hecho = taller(c)
    LEVAS_SOCAVADAS.clear()

    vueltas: list[_Vuelta] = []
    for numero, compilacion in enumerate(compilaciones, start=1):
        if not compilacion.perfiles:
            raise SystemExit(f"el cartucho {numero} no llegó a tener levas: no hay nada que animar")
        if not compilacion.veredicto.apto:
            print(
                f"AVISO: el cartucho {numero} NO es apto: "
                + ", ".join(sorted({i.codigo for i in compilacion.veredicto.errores}))
            )
        levas = [_dibujable(p) for p in compilacion.piezas]
        for i, (p, q) in enumerate(zip(compilacion.piezas, levas, strict=True)):
            if p is not q:
                print(
                    f"AVISO: la {p.nombre} del cartucho {numero} se cruza consigo misma y NO "
                    "es fabricable; se dibuja su silueta, en rojo"
                )
                LEVAS_SOCAVADAS.add(f"leva_{i + 1}")
        vueltas.append(
            _Vuelta(
                compilacion=compilacion,
                levas=levas,
                todos=estados(compilacion, maquina, thetas, camino="contacto"),
                recorrido=recorrer(compilacion, maquina, muestras=720),
            )
        )

    def colocadas(levas: list[Any], estado: Any) -> dict[str, Any]:
        return {p.nombre: p.solido for p in colocar(levas, seguidores, estado, c, hecho)}

    primera = vueltas[0]
    cero = colocadas(primera.levas, primera.todos[0])
    geo0 = _geometria_del_brazo(c, primera.todos[0])
    pivotes = [(s.pivote[0] * 1000.0, s.pivote[1] * 1000.0) for s in seguidores]
    t = c["platina_manivela_angulo"]
    manivela_en = (c["reductor_entre_ejes"] * math.cos(t), c["reductor_entre_ejes"] * math.sin(t))

    # El eje del balancín, en el marco de la leva: va a lo largo de +Y del
    # cinco barras, a la altura y la x del contrato.
    al = _del_cinco_barras(c)
    a = al((c["balancin_eje_x"], 0.0))
    b = al((c["balancin_eje_x"], 1.0))
    eje_bal = Vector(b[0] - a[0], b[1] - a[1], 0.0).normalized()
    z = alturas(c)
    z_bal = z["balancin"][0]

    ubicaciones = {
        "fijo": Location(),
        "arbol": Location(),
        "manivela": Pos(*manivela_en, 0.0),
        "balancin": Location(Plane(origin=(a[0], a[1], z_bal), z_dir=eje_bal)),
        "mesa": Location(),
        "tirante": Location(),
        "punta": Location(),
        **{f"seguidor_{i + 1}": Pos(*p, 0.0) for i, p in enumerate(pivotes)},
        **{f"brazo_{n}": Pos(*geo0[f"pivote_{n}"], 0.0) for n in (1, 2)},
    }
    nodos = {k: Nodo(k, v) for k, v in ubicaciones.items()}
    for n in (1, 2):
        # El distal, hijo de su brazo, puesto en el codo y en el marco del brazo.
        codo = Pos(*geo0[f"codo_{n}"], 0.0)
        nodos[f"distal_{n}"] = Nodo(f"distal_{n}", ubicaciones[f"brazo_{n}"].inverse() * codo)
        nodos[f"brazo_{n}"].hijos.append(nodos[f"distal_{n}"])
    # Cada cartucho: un nodo que se desliza por la salida y, dentro, otro que
    # gira con el árbol. Los dos en el origen, que es el eje del árbol.
    for k in range(1, len(vueltas) + 1):
        nodos[f"cartucho_{k}"] = Nodo(f"cartucho_{k}", Location())
        nodos[f"giro_{k}"] = Nodo(f"giro_{k}", Location())
        nodos[f"cartucho_{k}"].hijos.append(nodos[f"giro_{k}"])

    def absoluta(nodo: str) -> Any:
        if nodo.startswith("distal_"):
            return ubicaciones[f"brazo_{nodo[-1]}"] * nodos[nodo].ubicacion
        return ubicaciones.get(nodo, Location())

    for nombre, solido in cero.items():
        nodo = "giro_1" if nombre.startswith(PIEZAS_DEL_CARTUCHO) else _miembros(nombre)
        nodos[nodo].piezas.append((nombre, absoluta(nodo).inverse() * solido))
    for k, vuelta in enumerate(vueltas[1:], start=2):
        suyas = colocadas(vuelta.levas, vuelta.todos[0])
        for nombre, solido in suyas.items():
            if nombre.startswith(PIEZAS_DEL_CARTUCHO):
                nodos[f"giro_{k}"].piezas.append((nombre, solido))

    # --- lo que cambia en cada fotograma de cada vuelta ----------------------
    techo_mesa = cero["mesa"].bounding_box().max.Z + 0.05
    origen = {"mesa": _centro(cero["mesa"]), "tirante": _centro(cero["tirante"])}
    puntos_de = []
    for vuelta in vueltas:
        vuelta.geos = [_geometria_del_brazo(c, e) for e in vuelta.todos]
        # La mesa y el tirante, medidos donde los pone la cadena del
        # levantamiento de `colocar` —solo esa cadena: montar la máquina
        # entera por fotograma eran tres segundos—; el portalápiz, con la
        # punta del cinco barras.
        vuelta.traslados = {"mesa": [], "tirante": [], "punta": []}
        for e, g in zip(vuelta.todos, vuelta.geos, strict=True):
            cadena = {p.nombre: p.solido for p in _levantamiento(c, hecho, e, seguidores, z)}
            for k in ("mesa", "tirante"):
                vuelta.traslados[k].append([float(v) for v in _centro(cadena[k]) - origen[k]])
            vuelta.traslados["punta"].append(
                [
                    float(g["punta"][0] - geo0["punta"][0]),
                    float(g["punta"][1] - geo0["punta"][1]),
                    0.0,
                ]
            )
        puntos = [al((x * 1000.0, y * 1000.0)) for x, y in vuelta.recorrido.puntos]
        vuelta.marcas = [
            puntos[round(i * len(puntos) / len(thetas)) % len(puntos)] for i in range(len(thetas))
        ]
        puntos_de.append(puntos)

    # --- la línea de tiempo --------------------------------------------------
    # Cada marca es (tiempo, vuelta, clase, fotograma). «vuelta»: un fotograma
    # escribiendo. «fin»: la vuelta acabada, θ = 360°. «fuera»: el cartucho
    # que escribió ya ha salido y el siguiente aún no ha entrado. «reposo»:
    # la máquina quieta con la tarjeta entera.
    segundos = 60.0 / rpm_del_arbol()
    fotos = len(thetas)
    marcas: list[tuple[float, int, str, int]] = []
    ahora = 0.0
    for j in range(len(vueltas)):
        marcas += [(ahora + f * segundos / fotos, j, "vuelta", f) for f in range(fotos)]
        ahora += segundos
        if j < len(vueltas) - 1:
            marcas += [(ahora, j, "fin", 0), (ahora + CAMBIO, j, "fuera", 0)]
            ahora += 2.0 * CAMBIO
    if reposo > 0:
        # La máquina se queda quieta con la tarjeta entera —también el último
        # trozo de tinta— y luego vuelve a empezar.
        marcas.append((ahora - segundos / fotos + reposo, len(vueltas) - 1, "reposo", fotos - 1))
    indice_de = {(j, f): i for i, (_, j, clase, f) in enumerate(marcas) if clase == "vuelta"}

    def estado(marca: tuple[float, int, str, int]) -> tuple[int, int, float]:
        """(vuelta, fotograma, ángulo del árbol en grados) de una marca."""
        _, j, clase, f = marca
        if clase in ("fin", "fuera"):
            return j, 0, 360.0 * (j + 1)
        return j, f, 360.0 * j + float(np.degrees(thetas[f]))

    grados = np.degrees
    e0 = primera.todos[0]
    salida = c["cartucho_salida_angulo"]

    def afuera(k: int) -> list[float]:
        return [APARTADO * math.cos(salida), APARTADO * math.sin(salida), ESTANTE * k]

    pistas: dict[str, tuple[str, list[Any]]] = {}

    def pista(nombre: str, accion: str, valor: Any) -> None:
        pistas[nombre] = (accion, [valor(m, *estado(m)) for m in marcas])

    pista("arbol", "rz", lambda m, j, f, ang: ang)
    pista("manivela", "rz", lambda m, j, f, ang: -c["reductor_relacion"] * ang)
    pista(
        "balancin",
        "rz",
        lambda m, j, f, ang: float(grados(vueltas[j].todos[f].giro_balancin - e0.giro_balancin)),
    )
    for i in range(3):
        pista(
            f"seguidor_{i + 1}",
            "rz",
            lambda m, j, f, ang, i=i: float(
                grados(vueltas[j].todos[f].desviaciones[i] - e0.desviaciones[i])
            ),
        )
    for n in (1, 2):
        pista(
            f"brazo_{n}",
            "rz",
            lambda m, j, f, ang, n=n: float(
                grados(vueltas[j].geos[f][f"giro_{n}"] - geo0[f"giro_{n}"])
            ),
        )
        pista(
            f"distal_{n}",
            "rz",
            lambda m, j, f, ang, n=n: float(
                grados(
                    (vueltas[j].geos[f][f"distal_{n}"] - vueltas[j].geos[f][f"giro_{n}"])
                    - (geo0[f"distal_{n}"] - geo0[f"giro_{n}"])
                )
            ),
        )
    for k in ("mesa", "tirante", "punta"):
        pista(k, "t", lambda m, j, f, ang, k=k: vueltas[j].traslados[k][f])
    x0, y0 = puntos_de[0][0]
    pista(
        "punta_del_lapiz",
        "t",
        lambda m, j, f, ang: [
            float(vueltas[j].marcas[f][0] - x0),
            float(vueltas[j].marcas[f][1] - y0),
            0.0,
        ],
    )
    for k in range(len(vueltas)):
        # Dentro mientras es su vuelta; fuera en el cambio y antes y después.
        pista(
            f"cartucho_{k + 1}",
            "t",
            lambda m, j, f, ang, k=k: [0.0, 0.0, 0.0] if k == j and m[2] != "fuera" else afuera(k),
        )
        # Gira con el árbol en su vuelta; fuera se queda en fase cero, que es
        # como sale y como entra.
        pista(
            f"giro_{k + 1}",
            "rz",
            lambda m, j, f, ang, k=k: ang if k == j else 360.0 * (k + 1 if k < j else k),
        )

    # La tinta: lo que escriben las levas cortadas, sobre la mesa, **a medida
    # que se escribe**. El visor no sabe cambiar una geometría ni esconderla,
    # solo moverla; así que la tinta va partida en un trozo por fotograma, cada
    # trozo es un nodo hijo de la mesa, y espera hundido dentro de ella —la
    # mesa es opaca— hasta que la punta pasa por él: entonces sube al papel y
    # se queda hasta el final. Al volver a empezar todos bajan, y el papel
    # queda limpio.
    for j, vuelta in enumerate(vueltas):
        apoyado = vuelta.recorrido.apoyado
        puntos = puntos_de[j]
        m = len(puntos)
        bordes = [round(k * m / fotos) for k in range(fotos + 1)]
        for k in range(fotos):
            lineas = []
            tramo: list[tuple[float, float, float]] = []
            # Hasta el primer punto del trozo siguiente, incluido: así los
            # trozos se tocan y la línea sale seguida.
            for q in range(bordes[k], bordes[k + 1] + 1):
                if apoyado[q % m]:
                    tramo.append((*puntos[q % m], techo_mesa))
                else:
                    if len(tramo) > 1:
                        lineas.append(tramo)
                    tramo = []
            if len(tramo) > 1:
                lineas.append(tramo)
            if lineas:
                nombre = f"tinta_{j + 1}_{k:03d}"
                trozo = Nodo(nombre, Location())
                trozo.piezas += [(f"{nombre}_{q}", Polyline(*t)) for q, t in enumerate(lineas)]
                sube = indice_de[(j, k)]
                trozo.pista = ("tz", [0.0 if i > sube else -HUNDIDO for i in range(len(marcas))])
                nodos["mesa"].hijos.append(trozo)

    # La punta del lápiz, recorriendo la vuelta: una bolita en el plano del papel.
    nodos["punta_del_lapiz"] = Nodo("punta_del_lapiz", Pos(*puntos_de[0][0], techo_mesa))
    nodos["punta_del_lapiz"].piezas.append(("punta_del_lapiz", Sphere(0.8)))
    for k, valor in pistas.items():
        nodos[k].pista = valor

    tiempos = [m[0] for m in marcas]
    raiz = Nodo(
        RAIZ_DEL_ARBOL,
        Rot(Z=90.0 - math.degrees(c["cartucho_salida_angulo"])),
        hijos=[nodos[k] for k in nodos if not k.startswith(("distal_", "giro_"))],
    )
    return raiz, tiempos, [v.recorrido for v in vueltas]


def ubicacion_en(nodo: Nodo, fotograma: int, padre: Any = None) -> Any:
    """Dónde está un nodo en un fotograma, como lo pone el visor: su ubicación
    con la pista aplicada, encima de la de su padre. Un giro «rz» es sobre el
    origen del nodo; una traslación «t» se suma en el marco del padre."""
    from build123d import Location, Pos, Rot

    padre = Location() if padre is None else padre
    propia = nodo.ubicacion
    if nodo.pista is not None:
        accion, valores = nodo.pista
        if accion == "rz":
            propia = propia * Rot(Z=float(valores[fotograma]))
        elif accion == "t":
            propia = Pos(*valores[fotograma]) * propia
        elif accion == "tz":
            propia = Pos(0.0, 0.0, float(valores[fotograma])) * propia
        else:
            raise ValueError(f"pista {accion} sin traducir")
    return padre * propia


def nodos_en(raiz: Nodo, fotograma: int) -> dict[str, tuple[Nodo, Any]]:
    """Cada nodo con su ubicación absoluta en un fotograma, sin la raíz (que
    solo pone la máquina a escuadra)."""
    salida: dict[str, tuple[Nodo, Any]] = {}

    def bajar(nodo: Nodo, padre: Any) -> None:
        aqui = ubicacion_en(nodo, fotograma, padre)
        salida[nodo.nombre] = (nodo, aqui)
        for h in nodo.hijos:
            bajar(h, aqui)

    for h in raiz.hijos:
        bajar(h, None)
    return salida


def compuesto(nodo: Nodo, colores: dict[str, str]) -> Any:
    """El nodo como `Compound` de build123d, con su ubicación y sus hijos."""
    from build123d import Color, Compound

    from emit.montaje import grupo_de

    hijos = []
    for nombre, solido in nodo.piezas:
        solido.label = nombre
        try:
            grupo = grupo_de(nombre).nombre
            if nombre in LEVAS_SOCAVADAS:
                solido.color = Color("#d00000")
                hijos.append(solido)
                continue
            # El bastidor, translúcido: si no, los platos tapan las levas.
            alfa = 0.25 if grupo == "bastidor" else 1.0
            solido.color = Color(colores.get(grupo, "#9aa0a6"), alfa)
        except ValueError:
            solido.color = Color("#0b2a6f" if nombre.startswith("tinta") else "#d63384")
        hijos.append(solido)
    hijos += [compuesto(h, colores) for h in nodo.hijos]
    return Compound(children=hijos, label=nodo.nombre).locate(nodo.ubicacion)


def rutas(nodo: Nodo, prefijo: str = "") -> dict[str, tuple[str, list[Any]]]:
    """Ruta del visor de cada nodo con pista: /escribiente/brazo_1/distal_1."""
    ruta = f"{prefijo}/{nodo.nombre}"
    salida = {ruta: nodo.pista} if nodo.pista else {}
    for h in nodo.hijos:
        salida |= rutas(h, ruta)
    return salida


def guardar_gif(
    animacion: Any, destino: Path, fotogramas: int, pausa: float, duracion: float = 2.0
) -> Path:
    """La animación como GIF, una captura del visor por fotograma.

    No usa `Animation.save_as_gif`: en Windows abre su archivo temporal y lo
    deja abierto, el visor no puede escribir en él y la imagen sale vacía.
    Aquí cada fotograma va a su archivo y se espera a que el visor lo cierre.
    """
    import tempfile
    import time

    from ocp_vscode import save_screenshot
    from PIL import Image

    carpeta = Path(tempfile.mkdtemp(prefix="escribiente_gif_"))
    imagenes = []
    for k in range(fotogramas):
        animacion.set_relative_time(k / fotogramas)
        time.sleep(pausa)
        ruta = carpeta / f"{k:04d}.png"
        save_screenshot(str(ruta))
        for _ in range(100):
            if ruta.exists() and ruta.stat().st_size > 0:
                break
            time.sleep(0.1)
        time.sleep(0.2)
        with Image.open(ruta) as img:
            fondo = Image.new("RGB", img.size, "white")
            fondo.paste(img, mask=img.split()[3] if img.mode == "RGBA" else None)
            imagenes.append(fondo)
    destino.parent.mkdir(parents=True, exist_ok=True)
    imagenes[0].save(
        destino,
        save_all=True,
        append_images=imagenes[1:],
        duration=round(1000 * duracion / fotogramas),
        loop=0,
    )
    return destino


def main(argv: list[str] | None = None) -> int:
    sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[union-attr]
    p = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    p.add_argument("--pedido", type=Path, default=RAIZ / "demo" / "hola.json")
    p.add_argument("--fotogramas", type=int, default=120)
    p.add_argument(
        "--velocidad",
        type=float,
        default=0.25,
        help="1 = tiempo real, 2 s por vuelta; por defecto 0,25: 8 s por vuelta",
    )
    p.add_argument(
        "--reposo",
        type=float,
        default=0.5,
        help="segundos de máquina parada con la frase escrita, antes de borrar el papel",
    )
    p.add_argument("--gif", type=Path, help="guarda también la animación como GIF")
    p.add_argument(
        "--pausa",
        type=float,
        default=1.0,
        help="segundos entre capturas del GIF: el visor tarda en escribir cada una",
    )
    op = p.parse_args(argv)

    from ocp_vscode import Animation, Camera, show

    from emit.montaje import GRUPOS

    raiz, tiempos, recorridos = construir(op.pedido, op.fotogramas, op.reposo)
    for numero, recorrido in enumerate(recorridos, start=1):
        trazos, vuelos = recorrido.tramos()
        cartucho = f" cartucho {numero}" if len(recorridos) > 1 else ""
        print(
            f"{op.pedido.name}{cartucho}: {trazos} trazos y {vuelos} vuelos; error del trazo "
            f"por el perfil cortado {recorrido.error_maximo * 1e6:.1f} µm; escribe el "
            f"{100 * recorrido.fraccion_escribiendo:.0f} % de la vuelta"
        )
    colores = {g.nombre: g.color for g in GRUPOS}
    try:
        show(
            compuesto(raiz, colores),
            reset_camera=Camera.ISO,
            grid=(False, False, False),
            axes=False,
        )
    except Exception as fallo:
        print(
            f"\nNo hay visor OCP abierto ({type(fallo).__name__}). En VS Code: paleta de "
            "comandos (Ctrl+Shift+P) -> «OCP CAD Viewer: Open viewer», y vuelve a lanzarlo.",
            file=sys.stderr,
        )
        return 1
    animacion = Animation()
    for ruta, (accion, valores) in rutas(raiz).items():
        animacion.add_track(ruta, accion, tiempos, valores)
    animacion.animate(op.velocidad)
    if op.gif:
        op.gif.parent.mkdir(parents=True, exist_ok=True)
        guardar_gif(animacion, op.gif, len(tiempos), op.pausa, max(tiempos))
        print(f"GIF en {op.gif}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
