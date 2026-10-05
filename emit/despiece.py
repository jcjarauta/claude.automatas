"""El despiece pieza a pieza de un grupo, como el de un manual de motor.

Isométrica a línea, sin aristas ocultas; cada pieza sacada **por el eje en
que se monta**; una línea de montaje en trazo y punto del sitio de cada pieza
a donde ha salido, y un número suelto junto a cada pieza con una línea de
referencia fina que acaba en un punto sobre ella.

**Nada se declara a mano.** Las pilas —las piezas enhebradas en un mismo
eje— se derivan de las caras cilíndricas de los sólidos colocados: un eje,
un poste o un perno define una pila, y lo que tiene un agujero coaxial con
él se enhebra en ella; las piezas que comparten un agujero sin eje (el calzo
y el sector, por sus tornillos) forman la suya. La tornillería sale de su
agujero por su propio eje. Las distancias también se derivan: cada pieza a
`HUECO` de la anterior, y cada pila lo justo para que su caja en la
isométrica no pise la de otra.

La muestra a mano (`explosion_motor.py`) tenía tres defectos que esto
impide por construcción: pilas declaradas, un número señalando una pieza
tapada (aquí sale en `ocultas`, no señala nada) y dos pilas solapadas en la
proyección.

Todo en mm de la proyección isométrica (`emit.explosion.VISTA_ISOMETRICA`);
`encajar` lo lleva a un rectángulo de la hoja.
"""

from __future__ import annotations

import math
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field, replace
from typing import Any

from emit.explosion import EXPLOSIONES, VISTA_ISOMETRICA, Caja, _proyector, solapan
from emit.numeracion import Marca

Punto = tuple[float, float]
Vector = tuple[float, float, float]
Segmento = tuple[Punto, Punto]
Polilinea = list[Punto]

HUECO = 7.0
"""mm a lo largo del eje entre una pieza sacada y la anterior de su pila."""

PASO = 2.0
"""mm con que se busca cuánto apartar una pila para que no pise a otra."""

HOLGURA_PILAS = 3.0
"""mm, en la isométrica, entre las cajas de dos pilas."""

LETRA = 4.0
"""Alto de los números, en mm de la proyección."""

ANCHO_LETRA = 0.62
"""Ancho medio de un carácter de Helvetica negrita, en altos de letra: la
caja del texto se estima con él, sin medir la fuente."""

TOLERANCIA_ANCLA = 0.05
"""mm: un punto de una pieza está dibujado si cae a menos de esto de una
línea visible del conjunto."""

COS_PARALELO = math.cos(math.radians(1.0))
"""Dos ejes son paralelos si se apartan menos de 1°."""

COAXIAL = 0.2
"""mm entre las rectas de dos ejes paralelos para que sean el mismo."""

TOCA = 0.15
"""mm: un tornillo está en una pieza si sus sólidos están a menos de esto
(la caña lleva juego en su agujero, así que no se intersecan)."""

VISIBLE = 0.5
"""Fracción de su silueta que una pieza de una pila tiene que enseñar: si
la de delante la tapa más, se separan más. Siluetas convexas, en la
isométrica."""

PROPORCION = 170.0 / 175.0
"""Ancho / alto del hueco donde se dibuja el despiece en su hoja: la parte
izquierda de un A4 apaisado (la derecha lleva la leyenda y el cajetín)."""

EJES = ("eje_", "poste", "perno", "munon", "arbol", "varilla", "bulon")
"""Principio del nombre de las piezas que hacen de eje: definen una pila y
se quedan quietas en ella. Un pasador de tornillería no: sale por su eje."""


# ---------------------------------------------------------------------------
# Etiquetas: el número corto de cada pieza
# ---------------------------------------------------------------------------

_LETRA_DE_SERIE = {"piezas": "", "comerciales": "C", "tornilleria": "T"}


def texto_corto(marca: Marca, grupo: str) -> str:
    """El número que se escribe junto a la pieza en la hoja de su grupo.

    En la hoja del grupo el grupo se sobreentiende: `P-AMP-03` es «3»,
    `C-AMP-01` es «C1», `T-AMP-07` es «T7». Lo que tiene la marca en otro
    grupo lleva su sigla, «CBR-5», para que nadie lo busque en esta hoja."""
    corto = f"{_LETRA_DE_SERIE[marca.serie]}{marca.numero}"
    return corto if marca.grupo == grupo else f"{marca.sigla}-{corto}"


def marcas_de(
    nombre: str,
    marcas: Mapping[tuple[str, str], Marca],
    comerciales_colocados: Mapping[str, str],
) -> list[Marca]:
    """Las marcas del registro que dibuja una pieza colocada.

    Por orden: lo fabricado (por su clave del `LISTADO`), la tornillería
    (por el prefijo `en_3d` de su línea: un sólido puede dibujar dos
    líneas, el tornillo y su tuerca) y lo comprado (por el prefijo con que
    se coloca). Una pieza sin marca, como una leva, da la lista vacía."""
    from emit.fichas import base_de
    from emit.materiales import tornilleria

    clave = base_de(nombre)
    if clave and ("piezas", clave) in marcas:
        return [marcas[("piezas", clave)]]
    suyas = sorted(
        {
            marcas[("tornilleria", f.clave)]
            for f in tornilleria()
            if f.en_3d and nombre.startswith(f.en_3d) and ("tornilleria", f.clave) in marcas
        },
        key=lambda m: (m.grupo, m.numero),
    )
    if suyas:
        return suyas
    for comercial, prefijo in sorted(comerciales_colocados.items(), key=lambda kv: -len(kv[1])):
        if nombre.startswith(prefijo) and ("comerciales", comercial) in marcas:
            return [marcas[("comerciales", comercial)]]
    return []


def texto_de(
    nombre: str,
    grupo: str,
    marcas: Mapping[tuple[str, str], Marca],
    comerciales_colocados: Mapping[str, str],
) -> str:
    """El texto de la etiqueta de una pieza colocada; vacío si no lleva."""
    return ", ".join(
        texto_corto(m, grupo) for m in marcas_de(nombre, marcas, comerciales_colocados)
    )


# ---------------------------------------------------------------------------
# Geometría plana pura: cortes de segmento y caja
# ---------------------------------------------------------------------------


def _recorte(a: Punto, b: Punto, caja: Caja) -> tuple[float, float] | None:
    """Liang-Barsky: el tramo [t0, t1] de a→b dentro de la caja, o None."""
    x0, y0, x1, y1 = caja
    dx, dy = b[0] - a[0], b[1] - a[1]
    t0, t1 = 0.0, 1.0
    for p, q in ((-dx, a[0] - x0), (dx, x1 - a[0]), (-dy, a[1] - y0), (dy, y1 - a[1])):
        if p == 0:
            if q < 0:
                return None
            continue
        t = q / p
        if p < 0:
            t0 = max(t0, t)
        else:
            t1 = min(t1, t)
        if t0 > t1:
            return None
    return t0, t1


def corta(a: Punto, b: Punto, caja: Caja) -> bool:
    """Si el segmento a→b toca la caja (borde incluido)."""
    return _recorte(a, b, caja) is not None


def _segmentos_se_cruzan(p: Segmento, q: Segmento) -> bool:
    def lado(o: Punto, a: Punto, b: Punto) -> float:
        return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])

    (a, b), (c, d) = p, q
    return lado(a, b, c) * lado(a, b, d) < 0 and lado(c, d, a) * lado(c, d, b) < 0


def _segmentos(polilineas: Sequence[Sequence[Punto]]) -> list[Segmento]:
    return [(p[i], p[i + 1]) for p in polilineas for i in range(len(p) - 1) if p[i] != p[i + 1]]


class _Rejilla:
    """Segmentos repartidos en celdas, para no probar cada caja contra
    miles de ellos. Determinista: devuelve en orden de inserción."""

    def __init__(self, segmentos: Sequence[Segmento], celda: float) -> None:
        self.celda = celda
        self.segmentos: list[Segmento] = []
        self.celdas: dict[tuple[int, int], list[int]] = {}
        for s in segmentos:
            self.anadir(s)

    def _rango(self, caja: Caja) -> tuple[range, range]:
        c = self.celda
        return (
            range(math.floor(caja[0] / c), math.floor(caja[2] / c) + 1),
            range(math.floor(caja[1] / c), math.floor(caja[3] / c) + 1),
        )

    def anadir(self, s: Segmento) -> None:
        i = len(self.segmentos)
        self.segmentos.append(s)
        (a, b) = s
        xs, ys = self._rango((min(a[0], b[0]), min(a[1], b[1]), max(a[0], b[0]), max(a[1], b[1])))
        for x in xs:
            for y in ys:
                self.celdas.setdefault((x, y), []).append(i)

    def cerca(self, caja: Caja) -> list[Segmento]:
        xs, ys = self._rango(caja)
        indices = sorted({i for x in xs for y in ys for i in self.celdas.get((x, y), ())})
        return [self.segmentos[i] for i in indices]

    def corta_caja(self, caja: Caja) -> bool:
        return any(corta(a, b, caja) for a, b in self.cerca(caja))

    def cruces(self, s: Segmento) -> int:
        (a, b) = s
        caja = (min(a[0], b[0]), min(a[1], b[1]), max(a[0], b[0]), max(a[1], b[1]))
        return sum(1 for q in self.cerca(caja) if _segmentos_se_cruzan(s, q))

    def distancia_menor_que(self, p: Punto, d: float) -> bool:
        caja = (p[0] - d, p[1] - d, p[0] + d, p[1] + d)
        return any(_distancia_a_segmento(p, s) < d for s in self.cerca(caja))


def _distancia_a_segmento(p: Punto, s: Segmento) -> float:
    (a, b) = s
    dx, dy = b[0] - a[0], b[1] - a[1]
    n = dx * dx + dy * dy
    t = 0.0 if n == 0 else max(0.0, min(1.0, ((p[0] - a[0]) * dx + (p[1] - a[1]) * dy) / n))
    return math.hypot(p[0] - a[0] - t * dx, p[1] - a[1] - t * dy)


# ---------------------------------------------------------------------------
# Etiquetas: dónde va cada número
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Etiqueta:
    nombre: str
    """La pieza colocada que describe."""
    texto: str
    ancla: Punto
    """Dónde acaba la línea de referencia, con un punto: sobre una línea
    visible de la pieza."""
    posicion: Punto
    """Centro del texto."""
    caja: Caja
    """Lo que ocupa el texto, estimado por su número de caracteres."""
    extremo: Punto
    """Dónde la línea de referencia toca la caja del texto: se dibuja de
    `ancla` a aquí, para no tachar el número."""


def caja_de_texto(texto: str, centro: Punto, letra: float) -> Caja:
    ancho = (len(texto) * ANCHO_LETRA + 0.3) * letra
    alto = 1.2 * letra
    return (
        centro[0] - ancho / 2,
        centro[1] - alto / 2,
        centro[0] + ancho / 2,
        centro[1] + alto / 2,
    )


def _con_margen(c: Caja, m: float) -> Caja:
    return c[0] - m, c[1] - m, c[2] + m, c[3] + m


def colocar_etiquetas(
    anclas: Sequence[tuple[str, str, Punto]],
    obstaculos: Sequence[Segmento],
    letra: float = LETRA,
    centro: Punto | None = None,
) -> list[Etiqueta]:
    """Un número por (nombre, texto, ancla), cerca de su ancla y hacia fuera
    del dibujo, sin pisar otro número ni cortar ninguna línea.

    Los candidatos están en anillos alrededor del ancla, empezando por la
    dirección que sale del centro del dibujo y abriéndose a los dos lados;
    se queda el primero válido de los anillos más cercanos que menos líneas
    cruce con su línea de referencia. Las etiquetas se colocan por orden de
    ángulo alrededor del centro, y cada una es obstáculo para las
    siguientes: siempre el mismo resultado para la misma entrada."""
    if not anclas:
        return []
    if centro is None:
        xs = [a[2][0] for a in anclas]
        ys = [a[2][1] for a in anclas]
        centro = ((min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2)
    cx, cy = centro
    lineas = _Rejilla(obstaculos, max(4.0 * letra, 1.0))
    # Las cajas y las referencias ya puestas: otra rejilla, que crece.
    puestas = _Rejilla([], max(4.0 * letra, 1.0))
    cajas: list[Caja] = []
    salida: list[Etiqueta] = []

    def angulo(a: tuple[str, str, Punto]) -> tuple[float, str, str]:
        x, y = a[2]
        return (round(math.atan2(y - cy, x - cx), 9), a[1], a[0])

    hueco = 0.25 * letra
    for nombre, texto, ancla in sorted(anclas, key=angulo):
        fuera = math.atan2(ancla[1] - cy, ancla[0] - cx)
        mejor: tuple[float, Punto, Caja] | None = None
        primero_valido: int | None = None
        for anillo in range(200):
            if primero_valido is not None and anillo > primero_valido + 3:
                break
            radio = letra * (2.2 + 0.8 * anillo)
            for k in range(25):
                giro = (k + 1) // 2 * (1 if k % 2 else -1) * math.radians(15.0)
                if k == 0:
                    giro = 0.0
                a = fuera + giro
                p = (ancla[0] + radio * math.cos(a), ancla[1] + radio * math.sin(a))
                caja = caja_de_texto(texto, p, letra)
                holgada = _con_margen(caja, hueco)
                if any(solapan(holgada, c) for c in cajas):
                    continue
                if lineas.corta_caja(holgada) or puestas.corta_caja(holgada):
                    continue
                corte = _recorte(ancla, p, caja)
                t = corte[0] if corte else 1.0
                extremo = (ancla[0] + t * (p[0] - ancla[0]), ancla[1] + t * (p[1] - ancla[1]))
                if any(corta(ancla, extremo, _con_margen(c, -1e-6)) for c in cajas):
                    continue
                cruces = lineas.cruces((ancla, extremo)) + 3 * puestas.cruces((ancla, extremo))
                nota = anillo + 2.0 * cruces + abs(giro) / math.radians(60.0)
                if mejor is None or nota < mejor[0]:
                    mejor = (nota, p, caja)
                if primero_valido is None:
                    primero_valido = anillo
        if mejor is None:  # pragma: no cover - 200 anillos siempre salen del dibujo
            raise RuntimeError(f"no hay sitio para la etiqueta {texto} de {nombre}")
        _, p, caja = mejor
        corte = _recorte(ancla, p, caja)
        t = corte[0] if corte else 1.0
        extremo = (ancla[0] + t * (p[0] - ancla[0]), ancla[1] + t * (p[1] - ancla[1]))
        cajas.append(caja)
        x0, y0, x1, y1 = caja
        for s in (((x0, y0), (x1, y0)), ((x1, y0), (x1, y1)), ((x1, y1), (x0, y1))):
            puestas.anadir(s)
        puestas.anadir(((x0, y1), (x0, y0)))
        puestas.anadir((ancla, extremo))
        salida.append(Etiqueta(nombre, texto, ancla, p, caja, extremo))
    return sorted(salida, key=lambda e: (e.nombre, e.texto))


# ---------------------------------------------------------------------------
# Pilas: qué se enhebra en qué, y cuánto sale cada pieza
# ---------------------------------------------------------------------------


def ordenar_pila(
    tramos: Mapping[str, tuple[float, float]],
    eje: str | None,
    hueco: float = HUECO,
    despejado: Callable[[str, float, Mapping[str, float]], bool] | None = None,
    paso: float = PASO,
    tope: float = 600.0,
) -> dict[str, float]:
    """Cuánto sale cada pieza de una pila a lo largo de su eje.

    `tramos` es lo que ocupa cada pieza a lo largo del eje, montada. Con
    eje (la pieza más larga, que se queda), lo que está por encima de su
    mitad sale por arriba en orden y lo de debajo por abajo, cada pieza a
    `hueco` de la anterior. Sin eje, se queda la más baja y las demás
    suben en orden. Una pieza que ya está más allá no se mueve.

    `despejado(pieza, salida, colocadas)` dice si una pieza puede quedarse
    ahí: si no, sigue saliendo de `paso` en `paso` (hasta `tope` mm más). Es
    lo que impide que un disco grande tape al calzo que lleva debajo."""
    if not tramos:
        return {}
    if eje is None:
        eje = min(tramos, key=lambda n: (tramos[n][0], tramos[n][1], n))
        arriba = sorted((n for n in tramos if n != eje), key=lambda n: (*tramos[n], n))
        abajo: list[str] = []
    else:
        medio = sum(tramos[eje]) / 2
        resto = [n for n in tramos if n != eje]
        arriba = sorted(
            (n for n in resto if sum(tramos[n]) / 2 >= medio), key=lambda n: (*tramos[n], n)
        )
        abajo = sorted(
            (n for n in resto if sum(tramos[n]) / 2 < medio),
            key=lambda n: (-tramos[n][1], -tramos[n][0], n),
        )
    salida = {eje: 0.0}

    def despejar(n: str, d: float, sentido: float) -> float:
        if despejado is None:
            return d
        extra = 0.0
        while extra < tope and not despejado(n, d + sentido * extra, salida):
            extra += paso
        return d + sentido * extra

    techo = tramos[eje][1]
    for n in arriba:
        d = despejar(n, max(0.0, techo + hueco - tramos[n][0]), 1.0)
        salida[n] = d
        techo = tramos[n][1] + d
    suelo = tramos[eje][0]
    for n in abajo:
        d = despejar(n, min(0.0, suelo - hueco - tramos[n][1]), -1.0)
        salida[n] = d
        suelo = tramos[n][0] + d
    return salida


@dataclass(frozen=True)
class Cilindro:
    diametro: float
    punto: Vector
    """El pie del eje: el punto de su recta más cercano al origen."""
    direccion: Vector
    """Unitaria, con su mayor componente positiva."""
    desde: float
    hasta: float
    """El tramo de la cara, medido a lo largo de la dirección desde el origen."""


def _canonica(d: Vector) -> Vector:
    n = math.sqrt(sum(x * x for x in d))
    d = (d[0] / n, d[1] / n, d[2] / n)
    if max(d, key=abs) < 0:
        d = (-d[0], -d[1], -d[2])
    return (round(d[0], 9) + 0.0, round(d[1], 9) + 0.0, round(d[2], 9) + 0.0)


def _punto(a: Vector, d: Vector) -> float:
    return a[0] * d[0] + a[1] * d[1] + a[2] * d[2]


def _pie(p: Vector, d: Vector) -> Vector:
    t = _punto(p, d)
    return (p[0] - t * d[0], p[1] - t * d[1], p[2] - t * d[2])


def paralelos(a: Vector, b: Vector) -> bool:
    return abs(_punto(a, b)) >= COS_PARALELO


def coaxiales(a: Cilindro, b: Cilindro) -> bool:
    """El mismo eje: paralelos y sus rectas a menos de `COAXIAL`."""
    if not paralelos(a.direccion, b.direccion):
        return False
    w = tuple(q - p for p, q in zip(a.punto, b.punto, strict=True))
    t = _punto(w, a.direccion)  # type: ignore[arg-type]
    resto = [w[i] - t * a.direccion[i] for i in range(3)]
    return math.sqrt(sum(x * x for x in resto)) <= COAXIAL


def cilindros_de(solido: Any) -> list[Cilindro]:
    """Las caras cilíndricas de un sólido colocado, con su tramo, en orden
    fijo. Las dos medias caras de un mismo agujero salen una vez."""
    from OCP.BRepAdaptor import BRepAdaptor_Surface
    from OCP.GeomAbs import GeomAbs_Cylinder

    vistos: set[tuple[float, ...]] = set()
    salida = []
    for cara in solido.faces():
        superficie = BRepAdaptor_Surface(cara.wrapped)
        if superficie.GetType() != GeomAbs_Cylinder:
            continue
        cilindro = superficie.Cylinder()
        o, d = cilindro.Axis().Location(), cilindro.Axis().Direction()
        direccion = _canonica((d.X(), d.Y(), d.Z()))
        pie = _pie((o.X(), o.Y(), o.Z()), direccion)
        ts = [_punto((v.X, v.Y, v.Z), direccion) for v in cara.vertices()]
        if not ts:
            b = cara.bounding_box()
            ts = [_punto((b.min.X, b.min.Y, b.min.Z), direccion)]
            ts.append(_punto((b.max.X, b.max.Y, b.max.Z), direccion))
        c = Cilindro(
            round(2 * cilindro.Radius(), 4),
            (round(pie[0], 4) + 0.0, round(pie[1], 4) + 0.0, round(pie[2], 4) + 0.0),
            direccion,
            round(min(ts), 4),
            round(max(ts), 4),
        )
        clave = (c.diametro, *c.punto, *c.direccion, c.desde, c.hasta)
        if clave not in vistos:
            vistos.add(clave)
            salida.append(c)
    return sorted(salida, key=lambda c: (c.direccion, c.punto, c.diametro, c.desde, c.hasta))


def _principal(cs: Sequence[Cilindro]) -> Cilindro | None:
    """El cilindro más largo: la caña de un tornillo, el cuerpo de un eje."""
    if not cs:
        return None
    return min(cs, key=lambda c: (-(c.hasta - c.desde), c.diametro, c.punto, c.direccion))


def _esquinas(solido: Any) -> list[Vector]:
    b = solido.bounding_box()
    return [
        (x, y, z)
        for x in (b.min.X, b.max.X)
        for y in (b.min.Y, b.max.Y)
        for z in (b.min.Z, b.max.Z)
    ]


def _silueta(solido: Any) -> Any:
    """La envolvente convexa de la pieza en la isométrica, donde está."""
    from shapely.geometry import MultiPoint

    from emit.dossier import _polilinea

    vis, ocu = solido.project_to_viewport(*VISTA_ISOMETRICA)
    puntos = [q for a in [*vis, *ocu] for q in _polilinea(a)]
    return MultiPoint(sorted(set(puntos))).convex_hull


def lado_de_la_cabeza(solido: Any, c: Cilindro | None) -> float:
    """Hacia dónde tiene la cabeza un tornillo, a lo largo de c.direccion:
    el extremo de la circunferencia más grande centrada en su eje. +1, -1,
    o 0 si no tiene cabeza (una tuerca, un prisionero: todo del mismo
    diámetro en los dos extremos). Vale para la Allen y para la avellanada,
    cuya cabeza es un cono y no un cilindro."""
    from build123d import GeomType

    if c is None:
        return 0.0
    circulos = []
    for arista in solido.edges():
        if arista.geom_type != GeomType.CIRCLE:
            continue
        centro = arista.arc_center
        q = (centro.X, centro.Y, centro.Z)
        t = _punto(q, c.direccion)
        resto = [q[i] - c.punto[i] - t * c.direccion[i] for i in range(3)]
        if math.sqrt(sum(x * x for x in resto)) > COAXIAL:
            continue
        circulos.append((round(arista.radius, 4), round(t, 4)))
    if not circulos:
        return 0.0
    mayor = max(r for r, _ in circulos)
    ts = [t for _, t in circulos]
    medio = (min(ts) + max(ts)) / 2
    cabeza = [t for r, t in circulos if r == mayor]
    if mayor - min(r for r, _ in circulos) < 0.1 or max(ts) - min(ts) < 1e-6:
        return 0.0
    if all(t > medio for t in cabeza):
        return 1.0
    if all(t < medio for t in cabeza):
        return -1.0
    return 0.0


def _base_de_la_vista() -> tuple[Vector, Vector]:
    """(derecha, arriba) de la isométrica, en 3D."""
    proyectar = _proyector()
    cero = proyectar((0.0, 0.0, 0.0))
    imagenes = [proyectar(e) for e in ((1.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, 1.0))]
    derecha: Vector = (imagenes[0][0] - cero[0], imagenes[1][0] - cero[0], imagenes[2][0] - cero[0])
    arriba: Vector = (imagenes[0][1] - cero[1], imagenes[1][1] - cero[1], imagenes[2][1] - cero[1])
    return derecha, arriba


def _direcciones_de_apartar(general: Vector) -> list[Vector]:
    """Por dónde se puede apartar una pila: por el eje del grupo, en sus dos
    sentidos, y de lado en la vista (perpendicular a la imagen del eje del
    grupo, sin acercarse ni alejarse del ojo). En este orden, que es el que
    desempata."""
    derecha, arriba = _base_de_la_vista()
    gu, gv = _punto(general, derecha), _punto(general, arriba)
    n = math.hypot(gu, gv)
    pu, pv = (1.0, 0.0) if n < 1e-9 else (-gv / n, gu / n)
    lado = _unitario(_mas(_mas((0.0, 0.0, 0.0), derecha, pu), arriba, pv))
    if _punto(lado, derecha) < 0:
        lado = (-lado[0], -lado[1], -lado[2])
    menos = (-general[0], -general[1], -general[2])
    return [general, menos, lado, (-lado[0], -lado[1], -lado[2])]


def _nota_de_proporcion(cajas: Sequence[Caja], proporcion: float) -> float:
    """Lo grande que sale el conjunto metido en un hueco de esa proporción
    (ancho / alto): el lado que manda. Menos es mejor: dibuja más grande."""
    ancho = max(c[2] for c in cajas) - min(c[0] for c in cajas)
    alto = max(c[3] for c in cajas) - min(c[1] for c in cajas)
    return max(ancho / proporcion, alto)


def _sobre(c: Cilindro, p: Vector) -> Vector:
    """El punto del eje de c más cercano a p."""
    return _mas(c.punto, c.direccion, _punto(p, c.direccion))


def _tramo(solido: Any, d: Vector) -> tuple[float, float]:
    """Lo que ocupa a lo largo de d. Por las esquinas de su caja: exacto en
    un eje de la caja, y por exceso (más hueco, nunca menos) en otro."""
    ts = [_punto(p, d) for p in _esquinas(solido)]
    return round(min(ts), 6), round(max(ts), 6)


def _huella(solido: Any, d: Vector) -> Caja:
    """Lo que ocupa en el plano perpendicular a d."""
    u = _canonica((d[1], -d[0], 0.0) if abs(d[2]) < 0.9 else (1.0, 0.0, 0.0))
    u = _canonica(tuple(u[i] - _punto(u, d) * d[i] for i in range(3)))  # type: ignore[arg-type]
    v = (
        d[1] * u[2] - d[2] * u[1],
        d[2] * u[0] - d[0] * u[2],
        d[0] * u[1] - d[1] * u[0],
    )
    us = [_punto(p, u) for p in _esquinas(solido)]
    vs = [_punto(p, v) for p in _esquinas(solido)]
    return min(us), min(vs), max(us), max(vs)


@dataclass
class Pila:
    """Piezas enhebradas en un mismo eje, y la tornillería que entra en ellas."""

    direccion: Vector
    """Hacia dónde salen: con el sentido del eje de explosión del grupo."""
    punto: Vector
    eje: str | None
    """La pieza que hace de eje y se queda; None si la pila no tiene."""
    piezas: list[str] = field(default_factory=list)
    """Las enhebradas (con el eje, y con los circlips que van en él)."""
    tornillos: list[str] = field(default_factory=list)
    """La tornillería que sale de las piezas de la pila por su propio eje."""
    tramos: dict[str, tuple[float, float]] = field(default_factory=dict)
    """Lo que ocupa cada pieza a lo largo de `direccion`, ya explosionada."""
    orden: list[str] = field(default_factory=list)
    """Las piezas en el orden en que quedan a lo largo de `direccion`."""
    empuje: Vector = (0.0, 0.0, 0.0)
    """Cuánto se ha apartado la pila entera para no pisar a otra: lo que
    sale cada pieza de su sitio, dentro de la pila, es su desplazamiento
    menos esto."""

    @property
    def todas(self) -> list[str]:
        return [*self.piezas, *self.tornillos]


def es_tornilleria(nombre: str) -> bool:
    from emit.materiales import tornilleria

    return any(f.en_3d and nombre.startswith(f.en_3d) for f in tornilleria())


def es_eje(nombre: str) -> bool:
    return not es_tornilleria(nombre) and nombre.startswith(EJES)


def _orientar(d: Vector, hacia: Vector) -> Vector:
    """d con el sentido de `hacia`; si son perpendiculares, el canónico."""
    s = _punto(d, hacia)
    if abs(s) < 1e-9:
        return _canonica(d)
    return d if s > 0 else (-d[0] + 0.0, -d[1] + 0.0, -d[2] + 0.0)


def _unitario(v: Vector) -> Vector:
    n = math.sqrt(sum(x * x for x in v))
    return (v[0] / n, v[1] / n, v[2] / n)


def _mas(a: Vector, b: Vector, k: float = 1.0) -> Vector:
    return (a[0] + k * b[0], a[1] + k * b[1], a[2] + k * b[2])


def _centro(solido: Any) -> Vector:
    c = solido.bounding_box().center()
    return (c.X, c.Y, c.Z)


@dataclass
class Explosion:
    """Cómo sale cada pieza: el resultado de `explosionar`."""

    pilas: list[Pila]
    desplazamientos: dict[str, Vector]
    """Cuánto se mueve cada sólido, en total."""
    salidas: dict[str, tuple[Vector, Vector]]
    """De las piezas que salen de su sitio: el centro antes y después de
    salir, en 3D. Antes ya incluye lo que se ha movido su pila o la pieza
    que la lleva; la línea de montaje va de uno a otro, por su eje."""
    cabezas: dict[str, float] = field(default_factory=dict)
    """De cada pieza de tornillería, hacia dónde tiene la cabeza a lo largo
    de su eje principal (+1 o -1, en el sentido de `Cilindro.direccion`); 0
    si no tiene (tuerca, prisionero, circlip)."""


def explosionar(
    piezas: Sequence[tuple[str, Any]],
    grupo: str,
    hueco: float = HUECO,
    proporcion: float = PROPORCION,
) -> Explosion:
    """Las pilas del grupo, derivadas de sus ejes, y cuánto sale cada pieza.

    1. Cada pieza que hace de eje (`EJES`) abre una pila; lo que tiene un
       cilindro coaxial con él se enhebra (también un circlip).
    2. Las piezas que quedan y comparten un agujero coaxial abren otra, la
       del eje que más reúne.
    3. Lo que queda se suma a la pila de una pieza con la que comparte eje
       o tornillo, si ese eje es paralelo al de la pila.
    4. Lo que no entra en ninguna es su propia pila, por el eje del grupo.
    5. La tornillería sale por su eje hacia el lado de su cabeza: más allá
       de toda la pila si su eje es el de la pila, o de su pieza si no. Una
       tuerca va con su tornillo (el coaxial con cabeza), al lado contrario.
    6. Ninguna pila pisa a otra en la isométrica: la que pisa se aparta por
       el eje del grupo o de lado en la vista, por donde el conjunto quede
       más cerca de la `proporcion` (ancho / alto) del hueco de la hoja."""
    from build123d import Pos

    general = _unitario(EXPLOSIONES[grupo].eje)
    solidos = dict(sorted(piezas))
    nombres = list(solidos)
    cil = {n: cilindros_de(s) for n, s in solidos.items()}
    tornillos = [n for n in nombres if es_tornilleria(n)]
    pilas: list[Pila] = []
    de: dict[str, Pila] = {}

    def comparten(a: str, b: str, direccion: Vector | None = None) -> bool:
        return any(
            coaxiales(x, y) and (direccion is None or paralelos(x.direccion, direccion))
            for x in cil[a]
            for y in cil[b]
        )

    def abrir(c: Cilindro, eje: str | None, miembros: list[str]) -> None:
        p = Pila(_orientar(c.direccion, general), c.punto, eje, list(miembros))
        pilas.append(p)
        for m in miembros:
            de[m] = p

    # 1. Los ejes.
    for n in nombres:
        if not es_eje(n) or n in de:
            continue
        c = _principal(cil[n])
        if c is None:
            continue
        miembros = [n] + [
            m
            for m in nombres
            if m != n and m not in de and not es_eje(m) and any(coaxiales(c, x) for x in cil[m])
        ]
        abrir(c, n, miembros)

    # 2. Agujeros compartidos sin eje.
    while True:
        libres = [n for n in nombres if n not in de and n not in tornillos]
        mejor: tuple[int, tuple[Any, ...], Cilindro, list[str]] | None = None
        for n in libres:
            for c in cil[n]:
                juntos = [m for m in libres if any(coaxiales(c, x) for x in cil[m])]
                if len(juntos) < 2:
                    continue
                clave = (-len(juntos), (c.direccion, c.punto, c.diametro))
                if mejor is None or clave < (mejor[0], mejor[1]):
                    mejor = (clave[0], clave[1], c, juntos)
        if mejor is None:
            break
        abrir(mejor[2], None, mejor[3])

    # Dónde entra cada tornillo: las piezas que toca.
    def huesped(t: str) -> list[str]:
        bt = solidos[t].bounding_box()
        salida = []
        for m in nombres:
            if m == t or m in tornillos:
                continue
            bm = solidos[m].bounding_box()
            if (
                bm.min.X > bt.max.X + TOCA
                or bt.min.X > bm.max.X + TOCA
                or bm.min.Y > bt.max.Y + TOCA
                or bt.min.Y > bm.max.Y + TOCA
                or bm.min.Z > bt.max.Z + TOCA
                or bt.min.Z > bm.max.Z + TOCA
            ):
                continue
            if solidos[t].distance_to(solidos[m]) < TOCA:
                salida.append(m)
        # Primero la pieza con el agujero del tornillo; si no, la mayor: un
        # tornillo de la cinta al tambor es del tambor, no de la cinta.
        c = _principal(cil[t])
        return sorted(
            salida,
            key=lambda m: (
                not (c and any(coaxiales(c, x) for x in cil[m])),
                -round(solidos[m].volume, 3),
                m,
            ),
        )

    huespedes = {t: huesped(t) for t in tornillos if t not in de}

    # 3. Lo suelto, a la pila de una pieza con la que comparte eje o tornillo.
    cambio = True
    while cambio:
        cambio = False
        for n in nombres:
            if n in de or n in tornillos:
                continue
            for m in nombres:
                if m in de and m not in tornillos and comparten(n, m, de[m].direccion):
                    break
            else:
                m = next(
                    (
                        h
                        for t, hs in huespedes.items()
                        if n in hs and (c := _principal(cil[t])) is not None
                        for h in hs
                        if h in de and paralelos(c.direccion, de[h].direccion)
                    ),
                    "",
                )
                if not m:
                    continue
            de[m].piezas.append(n)
            de[n] = de[m]
            cambio = True

    # 4. Lo que queda, solo y por el eje del grupo.
    for n in nombres:
        if n not in de and n not in tornillos:
            pila = Pila(general, _centro(solidos[n]), None, [n])
            pilas.append(pila)
            de[n] = pila

    # Las pilas, ordenadas a lo largo de su eje.
    desplazamientos: dict[str, Vector] = {n: (0.0, 0.0, 0.0) for n in nombres}
    salidas: dict[str, tuple[Vector, Vector]] = {}
    proyectar = _proyector()
    cero = proyectar((0.0, 0.0, 0.0))
    siluetas = {n: _silueta(solidos[n]) for n in nombres}
    origen, _, mira = VISTA_ISOMETRICA
    hacia_mi = _unitario(tuple(o - m for o, m in zip(origen, mira, strict=True)))  # type: ignore[arg-type]

    def en_planta(n: str, a: Vector, d: float) -> Any:
        from shapely import affinity

        u, v = proyectar(_mas((0.0, 0.0, 0.0), a, d))
        return affinity.translate(siluetas[n], u - cero[0], v - cero[1])

    def visible(n: str, a: Vector, salidas_: Mapping[str, float]) -> float:
        """La parte de la silueta de n que no tapa nada de lo que tiene
        delante. En una pila, delante es más allá a lo largo del eje si el
        eje mira al ojo: el centro de cada pieza engaña, porque un calzo
        pequeño bajo un disco grande tiene el centro más cerca del ojo."""
        from shapely import unary_union

        mia = en_planta(n, a, salidas_[n])
        if mia.area <= 0:
            return 1.0
        hacia = 1.0 if _punto(a, hacia_mi) >= 0 else -1.0

        def altura(m: str, d: float) -> float:
            return hacia * (sum(_tramo(solidos[m], a)) / 2 + d)

        fondo = altura(n, salidas_[n])
        delante = [
            en_planta(m, a, d) for m, d in salidas_.items() if m != n and altura(m, d) > fondo
        ]
        if not delante:
            return 1.0
        return float(mia.difference(unary_union(delante)).area / mia.area)

    def en_su_eje(n: str, p: Pila) -> Vector:
        """Por dónde va la línea de montaje de n: por el eje del agujero con
        que se enhebra, como en un despiece de motor, y no por el centro de
        su caja, que en un brazo cae en medio de la nada. Prefiere el eje
        de la pila; si no, uno paralelo que comparta con otra pieza de la
        pila; si no, el suyo más largo paralelo; si no, su centro."""
        centro = _centro(solidos[n])
        paralelas = [x for x in cil[n] if paralelos(x.direccion, p.direccion)]
        eje_pila = Cilindro(0.0, p.punto, _canonica(p.direccion), 0.0, 0.0)
        for x in paralelas:
            if coaxiales(x, eje_pila):
                return _sobre(x, centro)
        for x in paralelas:
            if any(coaxiales(x, y) for m in p.todas if m != n for y in cil[m]):
                return _sobre(x, centro)
        c = _principal(paralelas)
        return centro if c is None else _sobre(c, centro)

    for p in pilas:
        tramos = {n: _tramo(solidos[n], p.direccion) for n in p.piezas}

        def despejado(n: str, d: float, colocadas: Mapping[str, float], p: Pila = p) -> bool:
            antes = dict(colocadas)
            con = {**antes, n: d}
            if visible(n, p.direccion, con) < VISIBLE:
                return False
            return all(
                visible(m, p.direccion, con) >= min(VISIBLE, visible(m, p.direccion, antes)) - 1e-9
                for m in antes
            )

        cuanto = ordenar_pila(tramos, p.eje, hueco, despejado)
        for n, d in cuanto.items():
            desplazamientos[n] = _mas((0.0, 0.0, 0.0), p.direccion, d)
            if d != 0.0:
                inicio = en_su_eje(n, p)
                salidas[n] = (inicio, _mas(inicio, p.direccion, d))

    # 5. La tornillería. Primero lo que tiene cabeza, para que una tuerca
    # sepa ya por dónde ha salido su tornillo y se vaya al otro lado.
    cabezas = {t: lado_de_la_cabeza(solidos[t], _principal(cil[t])) for t in tornillos}

    def sobre_la_pila(t: str, p: Pila, sentido: float) -> None:
        """Más allá de todo lo de la pila por el lado `sentido`, y de los
        tornillos ya puestos de ese lado si se pisan en planta."""
        a = p.direccion
        lejos = [_tramo(Pos(*desplazamientos[m]) * solidos[m], a) for m in p.piezas]
        huella = _huella(solidos[t], a)
        for otro in p.tornillos:
            if solapan(_con_margen(huella, 0.5), _huella(solidos[otro], a)):
                lejos.append(_tramo(Pos(*desplazamientos[otro]) * solidos[otro], a))
        lo, hi = _tramo(solidos[t], a)
        if sentido > 0:
            d = max(x[1] for x in lejos) + hueco - lo
        else:
            d = min(x[0] for x in lejos) - hueco - hi
        p.tornillos.append(t)
        de[t] = p
        desplazamientos[t] = _mas((0.0, 0.0, 0.0), a, d)
        cen = en_su_eje(t, p)
        salidas[t] = (cen, _mas(cen, a, d))

    def sentido_del_tornillo(s: str, a: Vector) -> float:
        """Hacia dónde ha salido un tornillo ya colocado, a lo largo de a:
        el lado de su cabeza; si no se le ve cabeza (un eje de rodillo
        cortado), hacia donde se ha movido. 0 si no se sabe."""
        c = _principal(cil[s])
        if c is not None and cabezas[s] != 0.0:
            return cabezas[s] * (1.0 if _punto(c.direccion, a) > 0 else -1.0)
        movido = _punto(desplazamientos[s], a)
        return 0.0 if abs(movido) < 1e-9 else math.copysign(1.0, movido)

    def su_tornillo(t: str) -> str:
        """El tornillo ya colocado en que va roscada una tuerca: coaxial, y
        con cabeza o ya sacado, para saber a qué lado no tiene que ir."""
        return next(
            (
                s
                for s in sorted(tornillos, key=lambda s: (cabezas[s] == 0.0, s))
                if s != t
                and s in de
                and (c := _principal(cil[s])) is not None
                and sentido_del_tornillo(s, c.direccion) != 0.0
                and any(coaxiales(c, x) for x in cil[t])
            ),
            "",
        )

    for t in sorted((t for t in tornillos if t not in de), key=lambda t: (cabezas[t] == 0, t)):
        c = _principal(cil[t])
        hs = huespedes[t]
        tornillo = su_tornillo(t) if c is not None and cabezas[t] == 0.0 else ""
        if c is not None and tornillo:
            # Una tuerca: con su tornillo, y hacia el lado contrario de su
            # cabeza. Aunque no toque nada del grupo (la del sector aprieta
            # contra el seguidor, que es de otro).
            paralelos_t = [h for h in hs if paralelos(c.direccion, de[h].direccion)]
            p = de[paralelos_t[0]] if paralelos_t else de[tornillo]
            cs = _principal(cil[tornillo])
            assert cs is not None
            if paralelos(cs.direccion, p.direccion):
                sobre_la_pila(t, p, -sentido_del_tornillo(tornillo, p.direccion))
                continue
        if c is None or not hs:
            pila = Pila(
                general if c is None else _orientar(c.direccion, general),
                _centro(solidos[t]),
                None,
                [t],
            )
            pilas.append(pila)
            de[t] = pila
            continue
        a = c.direccion
        paralelas_t = [h for h in hs if paralelos(a, de[h].direccion)]
        if paralelas_t:
            p = de[paralelas_t[0]]
            if cabezas[t] != 0.0:
                # Sale por donde tiene la cabeza: por ahí entró.
                sentido = cabezas[t] * (1.0 if _punto(a, p.direccion) > 0 else -1.0)
            elif p.eje is not None:
                centro = _punto(_centro(solidos[t]), p.direccion)
                medio = sum(_tramo(solidos[p.eje], p.direccion)) / 2
                sentido = 1.0 if centro >= medio else -1.0
            else:
                sentido = 1.0
            sobre_la_pila(t, p, sentido)
            continue
        # Fuera del eje de su pila: sale de su pieza, que ya se ha movido.
        h = hs[0]
        heredado = desplazamientos[h]
        if cabezas[t] != 0.0:
            sentido = cabezas[t]
        else:
            fuera = _punto(_centro(solidos[t]), a) >= _punto(_centro(solidos[h]), a)
            sentido = 1.0 if fuera else -1.0
        lo, hi = _tramo(solidos[t], a)
        hlo, hhi = _tramo(solidos[h], a)
        d = (hhi + hueco - lo) if sentido > 0 else (hlo - hueco - hi)
        de[h].tornillos.append(t)
        de[t] = de[h]
        desplazamientos[t] = _mas(heredado, a, d)
        cen = _mas(_sobre(c, _centro(solidos[t])), heredado)
        salidas[t] = (cen, _mas(cen, a, d))

    # 6. Que ninguna pila pise a otra en la isométrica. La que pisa se
    # aparta por el eje del grupo o de lado (en la vista), por donde el
    # conjunto quede más cerca de la proporción del hueco de la hoja.
    def caja_pila(p: Pila, extra: Vector) -> Caja:
        us, vs = [], []
        for n in p.todas:
            for q in _esquinas(solidos[n]):
                u, v = proyectar(_mas(_mas(q, desplazamientos[n]), extra))
                us.append(u)
                vs.append(v)
        return min(us), min(vs), max(us), max(vs)

    direcciones = _direcciones_de_apartar(general)
    colocadas: list[Caja] = []
    for p in pilas:
        elegida: tuple[tuple[float, int, int], Vector, float] | None = None
        for i, direccion in enumerate(direcciones):

            def pisa(distancia: float, p: Pila = p, direccion: Vector = direccion) -> bool:
                caja = _con_margen(
                    caja_pila(p, _mas((0.0, 0.0, 0.0), direccion, distancia)), HOLGURA_PILAS
                )
                return any(solapan(caja, o) for o in colocadas)

            k = 0
            while pisa(k * PASO):
                k += 1
            caja = caja_pila(p, _mas((0.0, 0.0, 0.0), direccion, k * PASO))
            orden = (round(_nota_de_proporcion([*colocadas, caja], proporcion), 6), k, i)
            if elegida is None or orden < elegida[0]:
                elegida = (orden, direccion, k * PASO)
            if k == 0:
                break
        assert elegida is not None
        extra = _mas((0.0, 0.0, 0.0), elegida[1], elegida[2])
        p.empuje = (round(extra[0], 6) + 0.0, round(extra[1], 6) + 0.0, round(extra[2], 6) + 0.0)
        for n in p.todas:
            desplazamientos[n] = _mas(desplazamientos[n], extra)
            if n in salidas:
                a, b = salidas[n]
                salidas[n] = (_mas(a, extra), _mas(b, extra))
        colocadas.append(caja_pila(p, (0.0, 0.0, 0.0)))
        p.tramos = {n: _tramo(Pos(*desplazamientos[n]) * solidos[n], p.direccion) for n in p.piezas}
        p.orden = sorted(p.piezas, key=lambda n: (p.tramos[n], n))
    redondo = {n: tuple(round(x, 6) + 0.0 for x in d) for n, d in desplazamientos.items()}
    return Explosion(pilas, redondo, salidas, cabezas)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# El despiece dibujado
# ---------------------------------------------------------------------------


@dataclass
class Despiece:
    """Lo que se dibuja del despiece de un grupo, en mm de la proyección."""

    grupo: str
    lineas: list[Polilinea]
    """Las aristas visibles del conjunto explosionado, proyectado de una vez:
    unas piezas tapan a otras."""
    montaje: list[tuple[str, Punto, Punto]]
    """(pieza, desde, hasta): una línea de trazo y punto por pieza movida."""
    etiquetas: list[Etiqueta]
    ocultas: list[str]
    """Piezas con número de las que no se ve ninguna línea: no se señalan."""
    cajas: dict[str, Caja]
    """La caja en la proyección de cada pieza, ya explosionada."""
    pilas: list[Pila]
    desplazamientos: dict[str, Vector]
    anclas: list[tuple[str, str, Punto]] = field(default_factory=list)
    """(pieza, texto, ancla) de lo que lleva número: con esto se recolocan
    las etiquetas a otro tamaño de letra (`encajar`)."""
    letra: float = LETRA
    """Alto de los números, en las mismas unidades que lo demás."""

    def obstaculos(self) -> list[Segmento]:
        return _segmentos(self.lineas) + [(a, b) for _, a, b in self.montaje]


def _densos(polilineas: Sequence[Sequence[Punto]], paso: float = 0.5) -> list[Punto]:
    """Puntos cada `paso` mm a lo largo de las polilíneas, no solo sus
    vértices: una recta larga solo tiene dos, y suelen ser esquinas que
    comparte con otra pieza."""
    salida: list[Punto] = []
    for a, b in _segmentos(polilineas):
        n = max(1, int(math.hypot(b[0] - a[0], b[1] - a[1]) / paso))
        salida += [
            (round(a[0] + (b[0] - a[0]) * i / n, 4), round(a[1] + (b[1] - a[1]) * i / n, 4))
            for i in range(n + 1)
        ]
    return salida


def despiece(
    piezas: Sequence[tuple[str, Any]],
    grupo: str,
    marcas: Mapping[tuple[str, str], Marca],
    comerciales_colocados: Mapping[str, str],
    letra: float = LETRA,
    hueco: float = HUECO,
    proporcion: float = PROPORCION,
) -> Despiece:
    """El despiece de un grupo.

    `piezas` es lo colocado de la máquina (`FichasDeGrupo.contexto`): se
    queda con lo que `emit.montaje.grupo_de` dice que es del grupo.
    `marcas` es `emit.numeracion.marcas(cargar())` y `comerciales_colocados`
    el nombre colocado de cada comercial (`scripts.numeracion`)."""
    from build123d import Compound, Pos

    from emit.dossier import _polilinea
    from emit.montaje import grupo_de

    suyas = sorted((n, s) for n, s in piezas if grupo_de(n).nombre == grupo)
    explosion = explosionar(suyas, grupo, hueco, proporcion)
    movidas = {n: Pos(*explosion.desplazamientos[n]) * s for n, s in suyas}
    origen, arriba, mira = VISTA_ISOMETRICA
    visibles, _ = Compound(children=list(movidas.values())).project_to_viewport(
        origen, arriba, mira
    )
    lineas = sorted(_polilinea(a) for a in visibles)
    proyectar = _proyector()

    montaje = [
        (n, _redondo(proyectar(a)), _redondo(proyectar(b)))
        for n, (a, b) in sorted(explosion.salidas.items())
    ]

    rejilla = _Rejilla(_segmentos(lineas), 5.0)
    cajas: dict[str, Caja] = {}
    anclas: list[tuple[str, str, Punto]] = []
    ocultas: list[str] = []
    for n, s in movidas.items():
        vis, ocu = s.project_to_viewport(origen, arriba, mira)
        propias = [_polilinea(a) for a in vis]
        todas = propias + [_polilinea(a) for a in ocu]
        if todas:
            xs = [x for p in todas for x, _ in p]
            ys = [y for p in todas for _, y in p]
            cajas[n] = (min(xs), min(ys), max(xs), max(ys))
        texto = texto_de(n, grupo, marcas, comerciales_colocados)
        if not texto:
            continue
        vistos = [q for q in _densos(propias) if rejilla.distancia_menor_que(q, TOLERANCIA_ANCLA)]
        if not vistos:
            ocultas.append(n)
            continue
        x0, y0, x1, y1 = cajas[n]
        cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
        ancla = min(vistos, key=lambda q: ((q[0] - cx) ** 2 + (q[1] - cy) ** 2, q))
        anclas.append((n, texto, ancla))

    d = Despiece(
        grupo=grupo,
        lineas=lineas,
        montaje=montaje,
        etiquetas=[],
        ocultas=sorted(ocultas),
        cajas=cajas,
        pilas=explosion.pilas,
        desplazamientos=explosion.desplazamientos,
        anclas=sorted(anclas),
        letra=letra,
    )
    d.etiquetas = colocar_etiquetas(d.anclas, d.obstaculos(), letra, _centro_de(d.lineas))
    return d


def _redondo(p: Punto) -> Punto:
    return (round(p[0], 3) + 0.0, round(p[1], 3) + 0.0)


def _extension(polilineas: Sequence[Sequence[Punto]]) -> Caja:
    xs = [x for p in polilineas for x, _ in p]
    ys = [y for p in polilineas for _, y in p]
    return min(xs), min(ys), max(xs), max(ys)


def _centro_de(polilineas: Sequence[Sequence[Punto]]) -> Punto:
    x0, y0, x1, y1 = _extension(polilineas)
    return (x0 + x1) / 2, (y0 + y1) / 2


def extension(d: Despiece) -> Caja:
    """Lo que ocupa todo: líneas, montaje y números."""
    trazos: list[Sequence[Punto]] = [*d.lineas, *([a, b] for _, a, b in d.montaje)]
    trazos += [[(e.caja[0], e.caja[1]), (e.caja[2], e.caja[3])] for e in d.etiquetas]
    return _extension(trazos)


def transformar(d: Despiece, f: Callable[[Punto], Punto], escala: float) -> Despiece:
    """Una copia con todo lo plano pasado por f (una semejanza de razón
    `escala`). Lo 3D —pilas y desplazamientos— queda igual."""

    def caja(c: Caja) -> Caja:
        a, b = f((c[0], c[1])), f((c[2], c[3]))
        return min(a[0], b[0]), min(a[1], b[1]), max(a[0], b[0]), max(a[1], b[1])

    return replace(
        d,
        lineas=[[f(q) for q in p] for p in d.lineas],
        montaje=[(n, f(a), f(b)) for n, a, b in d.montaje],
        etiquetas=[
            Etiqueta(e.nombre, e.texto, f(e.ancla), f(e.posicion), caja(e.caja), f(e.extremo))
            for e in d.etiquetas
        ],
        cajas={n: caja(c) for n, c in d.cajas.items()},
        anclas=[(n, t, f(a)) for n, t, a in d.anclas],
        letra=d.letra * escala,
    )


def encajar(
    d: Despiece, x: float, y: float, ancho: float, alto: float, letra: float = 3.0
) -> Despiece:
    """El despiece encajado y centrado en el rectángulo (x, y, ancho, alto)
    de la hoja, con los números de `letra` mm de alto en la hoja.

    La escala depende de dónde caen los números, y dónde caen depende de su
    tamaño en la proyección, que depende de la escala: se recolocan con la
    escala de las líneas solas y se ajusta un par de veces. Los números
    quedan de `letra` o algo menos, nunca fuera del rectángulo."""
    x0, y0, x1, y1 = _extension([*d.lineas, *([a, b] for _, a, b in d.montaje)])
    escala = min(ancho / max(x1 - x0, 1e-9), alto / max(y1 - y0, 1e-9))
    centro = _centro_de(d.lineas)
    obstaculos = d.obstaculos()
    actual = d
    for _ in range(4):
        actual = replace(
            d,
            etiquetas=colocar_etiquetas(d.anclas, obstaculos, letra / escala, centro),
            letra=letra / escala,
        )
        e = extension(actual)
        nueva = min(ancho / (e[2] - e[0]), alto / (e[3] - e[1]))
        if nueva >= escala * 0.999:
            break
        escala = nueva
    e = extension(actual)
    escala = min(escala, ancho / (e[2] - e[0]), alto / (e[3] - e[1]))
    ox = x + ancho / 2 - escala * (e[0] + e[2]) / 2
    oy = y + alto / 2 - escala * (e[1] + e[3]) / 2

    def f(p: Punto) -> Punto:
        return (round(ox + escala * p[0], 4), round(oy + escala * p[1], 4))

    return transformar(actual, f, escala)


__all__ = [
    "HUECO",
    "LETRA",
    "Cilindro",
    "Despiece",
    "Etiqueta",
    "Explosion",
    "Pila",
    "caja_de_texto",
    "cilindros_de",
    "coaxiales",
    "colocar_etiquetas",
    "corta",
    "despiece",
    "encajar",
    "es_eje",
    "es_tornilleria",
    "explosionar",
    "extension",
    "marcas_de",
    "ordenar_pila",
    "texto_corto",
    "texto_de",
    "transformar",
]
