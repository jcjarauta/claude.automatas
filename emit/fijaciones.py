"""La tornillería y la retención, dibujadas a su medida de norma.

Lo que compra `emit.materiales.tornilleria()` tiene que estar en el 3D: si
no, el despiece y la secuencia de montaje no lo enseñan, y nadie comprueba
que cabe. Aquí está **la forma** de cada elemento, en su marco: el eje en
+Z, la cara de apoyo en z = 0 y lo que entra en la pieza hacia -Z. Dónde va
cada uno lo dice `emit.montaje`, que es quien sabe dónde están las piezas.

Medidas de catálogo redondeadas a la décima: es un dibujo de montaje, no
un plano del tornillo. Ninguna rosca se dibuja; la caña va al diámetro
nominal menos el juego de giro, para que el barrido de choques sepa que
está en su agujero y no atravesando la pieza. **El agujero lo lleva la
pieza que lo recibe**: `taladro` da el sólido que se le resta.
"""

from __future__ import annotations

from typing import Any

JUEGO = 0.02
"""mm en diámetro entre una caña y su agujero: el de `emit.montaje`."""

CABEZA_DIN_912 = {2.0: (3.8, 2.0), 3.0: (5.5, 3.0), 4.0: (7.0, 4.0)}
"""Métrica → (Ø, alto) de la cabeza Allen."""

CABEZA_DIN_7991 = {3.0: (6.0, 1.7)}
"""Métrica → (Ø, alto) de la cabeza avellanada a 90°."""

TUERCA_DIN_439 = {3.0: (6.0, 1.8), 4.0: (7.7, 2.2)}
"""Métrica → (Ø entre aristas, alto) de la tuerca fina; se dibuja redonda."""

DIN_6799 = {1.5: (3.0, 0.3), 4.0: (7.3, 0.6), 6.0: (11.3, 0.7), 10.0: (16.3, 1.0)}
"""Ø del eje → (Ø exterior, espesor) del circlip de presión."""


def _cilindro(radio: float, alto: float, desde: float = 0.0) -> Any:
    from build123d import Align, Cylinder, Pos

    return Pos(0, 0, desde) * Cylinder(radio, alto, align=(Align.CENTER, Align.CENTER, Align.MIN))


def _anillo(exterior: float, interior: float, alto: float, desde: float = 0.0) -> Any:
    return _cilindro(exterior / 2, alto, desde) - _cilindro(interior / 2, alto + 2, desde - 1)


def allen(metrica: float, largo: float) -> Any:
    """DIN 912: la cabeza sobre z = 0, la caña de `largo` hacia -Z."""
    d, k = CABEZA_DIN_912[metrica]
    return _cilindro(d / 2, k) + _cilindro((metrica - JUEGO) / 2, largo, -largo)


def avellanado(metrica: float, largo: float) -> Any:
    """DIN 7991: enrasado, la cara de la cabeza en z = 0; el largo, total."""
    from build123d import Align, Cone, Pos

    d, k = CABEZA_DIN_7991[metrica]
    cabeza = Pos(0, 0, -k) * Cone(
        (metrica - JUEGO) / 2, d / 2, k, align=(Align.CENTER, Align.CENTER, Align.MIN)
    )
    return cabeza + _cilindro((metrica - JUEGO) / 2, largo - k, -largo)


def prisionero(metrica: float, largo: float) -> Any:
    """DIN 913: sin cabeza; la cara de la llave en z = 0, la punta en -largo."""
    return _cilindro((metrica - JUEGO) / 2, largo, -largo)


def tuerca(metrica: float) -> Any:
    """DIN 439, apoyada en z = 0 y hacia +Z."""
    d, m = TUERCA_DIN_439[metrica]
    return _anillo(d, metrica, m)


def circlip(eje: float) -> Any:
    """DIN 6799 sobre un eje de Ø `eje`, apoyado en z = 0 y hacia +Z. Se
    dibuja cerrado y sin la ranura del eje: lo que importa es lo que ocupa."""
    d, s = DIN_6799[eje]
    return _anillo(d, eje + JUEGO, s)


def arandela(interior: float, exterior: float, espesor: float) -> Any:
    """Apoyada en z = 0 y hacia +Z."""
    return _anillo(exterior, interior + JUEGO, espesor)


def taladro(metrica: float, profundo: float, cabeza: tuple[float, float] | None = None) -> Any:
    """Lo que se resta a la pieza que recibe una caña: el agujero al
    nominal, de z = 0 hacia -Z, y, si la cabeza va embutida, su
    alojamiento de z = 0 hacia +Z, donde `allen` pone la cabeza."""
    agujero = _cilindro(metrica / 2, profundo + 0.01, -profundo)
    if cabeza is not None:
        # La cabeza está del lado de +Z, como en `allen`: su alojamiento también.
        d, k = cabeza
        agujero += _cilindro(d / 2 + 0.05, k + 0.01, 0.0)
    return agujero


def taladro_avellanado(metrica: float, largo: float) -> Any:
    """El alojamiento de un DIN 7991: el cono a 90° y la caña al nominal."""
    from build123d import Align, Cone, Pos

    d, k = CABEZA_DIN_7991[metrica]
    cono = Pos(0, 0, -k) * Cone(
        metrica / 2, d / 2 + 0.05, k + 0.01, align=(Align.CENTER, Align.CENTER, Align.MIN)
    )
    return cono + _cilindro(metrica / 2, largo + 0.01, -largo)


Eje = tuple[tuple[float, float, float], tuple[float, float, float], float, float]
"""(punto del eje, dirección unitaria, desde, hasta): un agujero, con su
tramo medido a lo largo de la dirección desde el punto."""


def cilindros(
    solido: Any,
) -> list[tuple[float, tuple[float, float, float], tuple[float, float, float]]]:
    """(Ø, punto del eje, dirección) de cada cara cilíndrica: para saber por
    dónde pasa el eje de una arandela o un circlip ya colocado."""
    from OCP.BRepAdaptor import BRepAdaptor_Surface
    from OCP.GeomAbs import GeomAbs_Cylinder

    salida = []
    for cara in solido.faces():
        superficie = BRepAdaptor_Surface(cara.wrapped)
        if superficie.GetType() == GeomAbs_Cylinder:
            cilindro = superficie.Cylinder()
            o, d = cilindro.Axis().Location(), cilindro.Axis().Direction()
            salida.append((2 * cilindro.Radius(), (o.X(), o.Y(), o.Z()), (d.X(), d.Y(), d.Z())))
    return salida


def agujeros(solido: Any, diametro: float) -> list[Eje]:
    """Los agujeros cilíndricos de un diámetro en un sólido ya colocado: así
    la tornillería va donde la pieza tiene el agujero, y no donde alguien
    calculó que debería estar. Un cilindro que el kernel parte en dos caras
    sale una vez."""
    from OCP.BRepAdaptor import BRepAdaptor_Surface
    from OCP.GeomAbs import GeomAbs_Cylinder

    salida: list[Eje] = []
    for cara in solido.faces():
        superficie = BRepAdaptor_Surface(cara.wrapped)
        if superficie.GetType() != GeomAbs_Cylinder:
            continue
        cilindro = superficie.Cylinder()
        if abs(2 * cilindro.Radius() - diametro) > 1e-4:
            continue
        eje = cilindro.Axis()
        o, d = eje.Location(), eje.Direction()
        punto, direccion = (o.X(), o.Y(), o.Z()), (d.X(), d.Y(), d.Z())
        if max(direccion, key=abs) < 0:
            direccion = (-direccion[0], -direccion[1], -direccion[2])
        ts = [
            sum(
                (v_ - p_) * d_ for v_, p_, d_ in zip((v.X, v.Y, v.Z), punto, direccion, strict=True)
            )
            for v in cara.vertices()
        ]
        # El punto del eje, llevado al pie del tramo: dos medias caras del
        # mismo agujero dan el mismo punto.
        pie = min(ts)
        punto = tuple(p_ + pie * d_ for p_, d_ in zip(punto, direccion, strict=True))
        largo = max(ts) - pie
        repetido = any(
            sum((a - b) ** 2 for a, b in zip(punto, otro[0], strict=True)) < 1e-6
            and abs(largo - otro[3]) < 1e-6
            for otro in salida
        )
        if not repetido:
            salida.append((punto, direccion, 0.0, largo))  # type: ignore[arg-type]
    return salida


__all__ = [
    "CABEZA_DIN_912",
    "CABEZA_DIN_7991",
    "DIN_6799",
    "TUERCA_DIN_439",
    "Eje",
    "agujeros",
    "allen",
    "arandela",
    "avellanado",
    "cilindros",
    "circlip",
    "prisionero",
    "taladro",
    "taladro_avellanado",
    "tuerca",
]
