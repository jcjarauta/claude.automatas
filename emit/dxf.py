"""DXF para corte digital: láser o CNC.

La compensación de **kerf** vive aquí y solo aquí. El núcleo no sabe con qué
se va a cortar la pieza, y el mismo perfil se corta a láser, con sierra o a
mano. El kerf es un dato medido por material y espesor, en `bench/kerf.json`;
mientras no esté medido se emite a la línea nominal y se dice en el archivo.

Qué se lleva la herramienta: el láser quema medio kerf a cada lado de la
línea, así que el contorno exterior se desplaza **hacia fuera** medio kerf y
los taladros **hacia dentro**. Compensar al revés es el error que deja la
pieza con un kerf entero de holgura.

Dos cosas que no son negociables en el archivo:

- **Nada de splines.** Mucho software de láser no los traga, o los aproxima a
  su manera y sin decirlo. Se exporta polilínea densa, que es lo que el
  núcleo ya tiene: el perfil son N muestras del ciclo.
- **Milímetros.** Se cruza la frontera de unidades aquí, como en `layout.py`.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from ezdxf._options import options as opciones_dxf
from ezdxf.document import Drawing
from ezdxf.filemanagement import new as nuevo_dxf
from shapely.geometry import LinearRing, Polygon

from core.units import Metros, a_mm
from emit.pieza import Pieza

CAPAS: dict[str, int] = {
    "CORTE": 1,
    "TALADRO": 3,
    "REFERENCIA": 5,
    "FASE": 6,
    "ROTULO": 7,
}
"""Capa -> color ACI. Separadas porque en el láser cada una lleva su
potencia: el corte atraviesa, el rótulo solo marca."""

# Regla 4 del proyecto: mismo input, mismo DXF, **byte a byte**. Por defecto
# un DXF lleva marca de tiempo y dos identificadores aleatorios que cambian en
# cada guardado, así que no habría golden que comparar ni forma de saber si un
# pedido repetido salió igual. La biblioteca trae este interruptor para fijar
# esos campos; el nombre dice «testing» porque es su uso habitual, pero aquí
# el determinismo es un requisito del producto y no una comodidad de los tests.
opciones_dxf.write_fixed_meta_data_for_testing = True


@dataclass(frozen=True)
class Kerf:
    """Lo que se lleva la herramienta, en metros."""

    anchura: float = 0.0
    medido: bool = False

    @classmethod
    def desde(cls, ruta: Path | str, material: str = "", espesor_mm: float = 0.0) -> Kerf:
        """Lee `bench/kerf.json`. Sin medida, devuelve kerf cero y lo dice."""
        datos = json.loads(Path(ruta).read_text(encoding="utf-8"))
        clave = f"{material}|{espesor_mm:.1f}"
        por_material = datos.get("materiales", {})
        if clave in por_material:
            return cls(anchura=float(por_material[clave]) / 1000.0, medido=True)
        return cls(
            anchura=float(datos.get("por_defecto_mm", 0.0)) / 1000.0,
            medido=bool(datos.get("medido", False)),
        )


def _compensar(
    puntos: list[tuple[Metros, Metros]], desplazamiento: float
) -> list[tuple[float, float]]:
    """Desplaza un contorno cerrado hacia fuera, en milímetros de salida.

    Con desplazamiento cero no se toca la geometría: así el archivo sin kerf
    medido es exactamente el perfil que calculó el núcleo.
    """
    if abs(desplazamiento) < 1e-12:
        return [(a_mm(x), a_mm(y)) for x, y in puntos]
    anillo = LinearRing([(float(x), float(y)) for x, y in puntos])
    if not anillo.is_ccw:
        anillo = LinearRing(list(anillo.coords)[::-1])
    ampliado = Polygon(anillo).buffer(desplazamiento, join_style="round", quad_segs=16)
    if ampliado.geom_type != "Polygon":
        raise ValueError(
            "compensar el kerf parte el contorno en trozos: el perfil tiene un "
            "detalle más fino que la herramienta y esta pieza no se puede cortar así."
        )
    return [(x * 1000.0, y * 1000.0) for x, y in ampliado.exterior.coords[:-1]]


def _documento() -> Drawing:
    doc = nuevo_dxf(dxfversion="R2010", setup=False)
    doc.header["$INSUNITS"] = 4  # milímetros
    doc.header["$MEASUREMENT"] = 1
    for nombre, color in CAPAS.items():
        doc.layers.add(name=nombre, color=color)
    return doc


def _fijar_orden_de_clases(doc: Drawing) -> None:
    """Registra las clases DXF en orden alfabético antes de guardar.

    Al guardar, la biblioteca recorre el conjunto de tipos de entidad usados
    para declarar sus clases, y un conjunto de Python no tiene orden estable
    entre procesos. El archivo salía idéntico dentro de una misma ejecución y
    distinto en la siguiente, que es la peor forma de no ser determinista:
    los tests pasaban y el golden fallaba. Registrándolas antes en orden, el
    recorrido posterior ya no añade nada.
    """
    for tipo in sorted(doc.entitydb.dxf_types_in_use()):
        doc.classes.add_class(tipo)


def escribir_dxf(pieza: Pieza, destino: Path | str, kerf: Kerf | None = None) -> Path:
    """Un DXF por pieza. Devuelve dónde quedó."""
    kerf = kerf or Kerf()
    doc = _documento()
    espacio = doc.modelspace()

    espacio.add_lwpolyline(
        _compensar(pieza.contorno, kerf.anchura / 2.0),
        close=True,
        dxfattribs={"layer": "CORTE"},
    )

    for taladro in pieza.taladros:
        # Hacia dentro: la herramienta se come medio kerf del borde del agujero.
        radio = a_mm(taladro.diametro) / 2.0 - a_mm(Metros(kerf.anchura)) / 2.0
        if radio <= 0.0:
            raise ValueError(
                f"'{pieza.nombre}': el taladro de {a_mm(taladro.diametro):.1f} mm no "
                f"sobrevive a un kerf de {a_mm(Metros(kerf.anchura)):.2f} mm."
            )
        espacio.add_circle(
            (a_mm(taladro.centro[0]), a_mm(taladro.centro[1])),
            radio,
            dxfattribs={"layer": "TALADRO"},
        )

    for referencia in pieza.referencias:
        espacio.add_lwpolyline(
            [(a_mm(x), a_mm(y)) for x, y in referencia.puntos],
            close=referencia.cerrada,
            dxfattribs={"layer": "REFERENCIA"},
        )

    if pieza.marca_fase is not None:
        espacio.add_circle(
            (a_mm(pieza.marca_fase[0]), a_mm(pieza.marca_fase[1])),
            2.0,
            dxfattribs={"layer": "FASE"},
        )

    nota = f"{pieza.numero} {pieza.nombre} | {pieza.material} | {a_mm(pieza.espesor):.1f} mm"
    nota += f" | x{pieza.cantidad} | veta {pieza.veta.value}"
    nota += " | kerf medido" if kerf.medido else " | KERF SIN MEDIR: linea nominal"
    espacio.add_text(
        nota,
        height=3.0,
        dxfattribs={"layer": "ROTULO"},
    ).set_placement((a_mm(pieza.limites[0]), a_mm(pieza.limites[1]) - 8.0))

    ruta = Path(destino)
    ruta.parent.mkdir(parents=True, exist_ok=True)
    _fijar_orden_de_clases(doc)
    doc.saveas(ruta, encoding="utf-8")
    return ruta


def escribir_dxfs(piezas: list[Pieza], carpeta: Path | str, kerf: Kerf | None = None) -> list[Path]:
    """Un archivo por pieza: en el láser cada una se corta por su cuenta."""
    if not piezas:
        raise ValueError("no hay piezas que exportar")
    destino = Path(carpeta)
    return [escribir_dxf(pieza, destino / f"{pieza.numero}.dxf", kerf) for pieza in piezas]


__all__ = ["CAPAS", "Kerf", "escribir_dxf", "escribir_dxfs"]
