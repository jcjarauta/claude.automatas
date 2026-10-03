"""El catálogo de piezas comerciales, en STEP, generado desde las fichas.

**Qué problema resuelve.** Para montar el conjunto en un CAD hacen falta los
sólidos de las catorce referencias que se compran. La vía obvia es bajarlos
del fabricante, y tiene tres pegas que no se ven hasta que muerden:

1. **Puede que no coincidan con lo que calcula el compilador.** Un STEP de
   catálogo viene simplificado, a veces con el sólido equivocado, y cambia
   cuando al fabricante le parece. Ya pasó con la valona del casquillo: Ø12
   apuntado, Ø15 real, copiado en tres documentos.
2. **No todos existen.** El portaminas no tiene CAD, el eje rectificado
   tampoco, y los genéricos —MR63ZZ, separadores— no tienen fabricante que
   publique nada.
3. **Los de bibliotecas de terceros tienen licencia.** Los modelos de
   GrabCAD son «for private use only» y usarlos en un producto que se vende
   requiere permiso del autor.

Aquí el sólido **se genera desde la ficha**, así que por construcción dice lo
mismo que el compilador, existe siempre y es nuestro. Y como sale en STEP,
entra en cualquier CAD: no ata la decisión de qué herramienta usar.

**Qué NO es.** No son modelos bonitos. Son **envolventes**: exactas en las
cotas que la ficha marca como críticas —las que otra pieza toca— y toscas en
todo lo demás. Un engranaje sale como un disco sin dientes, porque para
comprobar que el conjunto cierra los dientes no aportan nada y para
fabricarlo se compra hecho. Un muelle sale como el cilindro que ocupa.

Para el render de venta se importa el STEP del fabricante encima. Para
acotar, montar y comprobar interferencias, esto es lo correcto: **lo que se
quiere saber es si la pieza cabe, y eso lo decide su envolvente.**
"""

from __future__ import annotations

import json
from collections.abc import Iterable
from pathlib import Path

from build123d import Align, Box, Cylinder, Mode, Part, Pos, export_step

from core.comercial import FamiliaComercial, PiezaComercial
from core.errors import FichaIncompleta
from core.units import a_mm

CATALOGO = Path("docs/piezas")

LARGO_POR_DEFECTO = 10.0
"""Cuando una ficha no declara longitud, el sólido se hace de 10 mm. Sirve
para colocarlo y no para acotar: si la longitud importa, va en la ficha."""

# La ficha guarda metros, como todo el núcleo; el STEP se escribe en
# milímetros, que es lo que declara su cabecera y lo que lee un CAD. La
# frontera de unidades se cruza en `_mm` y en ningún otro sitio del módulo,
# con el mismo `a_mm` que usa `emit/step.py`: regla 3, SI dentro y mm fuera.


def _mm(pieza: PiezaComercial, nombre: str, por_defecto: float | None = None) -> float:
    """Una cota en MILÍMETROS, o el valor por defecto si la ficha no la trae.

    El valor por defecto llega ya en milímetros: es un número escrito aquí,
    no una cota de la ficha, y mezclar las dos unidades en el mismo
    argumento es justo como se cuela un error de factor mil.
    """
    try:
        return a_mm(pieza.cota(nombre).valor)
    except KeyError:
        if por_defecto is None:
            raise FichaIncompleta(
                f"{pieza.nombre} ({pieza.familia.value}) necesita la cota '{nombre}'"
            ) from None
        return por_defecto


def _tubo(exterior: float, agujero: float, alto: float) -> Part:
    """Un cilindro hueco, que es la forma de medio catálogo."""
    solido = Cylinder(exterior / 2.0, alto, align=(Align.CENTER, Align.CENTER, Align.MIN))
    if agujero > 0.0:
        solido -= Cylinder(
            agujero / 2.0, alto, align=(Align.CENTER, Align.CENTER, Align.MIN), mode=Mode.SUBTRACT
        )
    return solido


def solido_de(pieza: PiezaComercial) -> Part:
    """La envolvente de una pieza comercial, en MILÍMETROS y apoyada en Z = 0.

    El eje Z es el de revolución en todo lo que gira, que es casi todo. Así
    una pieza importada se orienta sola sobre el eje donde va.
    """
    f = pieza.familia

    if f in (FamiliaComercial.RODAMIENTO, FamiliaComercial.SEPARADOR):
        alto = _mm(pieza, "ancho", _mm(pieza, "espesor", LARGO_POR_DEFECTO))
        return _tubo(_mm(pieza, "exterior"), _mm(pieza, "agujero"), alto)

    if f is FamiliaComercial.CASQUILLO:
        largo = _mm(pieza, "longitud", LARGO_POR_DEFECTO)
        espesor_valona = _mm(pieza, "espesor_valona", 1.0)
        cuerpo = _tubo(_mm(pieza, "exterior"), _mm(pieza, "agujero"), largo)
        valona = _tubo(_mm(pieza, "valona"), _mm(pieza, "agujero"), espesor_valona)
        # La valona va abajo: es la cara que apoya, y la que come el hueco.
        return (cuerpo + Pos(0, 0, 0) * valona).clean()

    if f in (FamiliaComercial.EJE, FamiliaComercial.PASADOR):
        return _tubo(_mm(pieza, "diametro"), 0.0, _mm(pieza, "longitud", LARGO_POR_DEFECTO))

    if f is FamiliaComercial.MUELLE:
        # La envolvente que ocupa, no la hélice: lo que importa es si cabe.
        return _tubo(_mm(pieza, "exterior"), 0.0, _mm(pieza, "longitud_libre", LARGO_POR_DEFECTO))

    if f is FamiliaComercial.ENGRANAJE:
        # Disco al diámetro exterior. Los dientes no ayudan a saber si cabe,
        # y la pieza se compra hecha: dibujarlos sería adorno con riesgo.
        return _tubo(_mm(pieza, "exterior"), _mm(pieza, "agujero"), _mm(pieza, "ancho", 4.0))

    if f is FamiliaComercial.INSTRUMENTO:
        return _tubo(_mm(pieza, "cuerpo"), 0.0, _mm(pieza, "longitud", LARGO_POR_DEFECTO))

    if f is FamiliaComercial.FIJACION:
        # La familia tiene dos formas muy distintas y se distinguen por las
        # cotas: lo que declara `metrica` es un tornillo, y lo que declara
        # `agujero` y `exterior` es un anillo. Meterlos en la misma rama sin
        # mirar daba un tornillo de cabeza Ø18 donde había un anillo.
        try:
            pieza.cota("metrica")
        except KeyError:
            return _tubo(_mm(pieza, "exterior"), _mm(pieza, "agujero"), _mm(pieza, "ancho"))
        metrica = _mm(pieza, "metrica")
        cabeza = _mm(pieza, "cabeza", metrica * 1.8)
        largo = _mm(pieza, "longitud", LARGO_POR_DEFECTO)
        vastago = _tubo(metrica, 0.0, largo)
        return (vastago + Pos(0, 0, largo) * _tubo(cabeza, 0.0, metrica)).clean()

    if f is FamiliaComercial.MATERIAL:
        return Box(
            _mm(pieza, "ancho", 100.0),
            _mm(pieza, "largo", 100.0),
            _mm(pieza, "espesor"),
            align=(Align.CENTER, Align.CENTER, Align.MIN),
        )

    raise FichaIncompleta(  # pragma: no cover - lo impide un test sobre el enum
        f"no sé qué forma dar a la familia '{getattr(f, 'value', f)}'"
    )


def cargar(ruta: Path | str = CATALOGO) -> list[PiezaComercial]:
    """Todas las fichas del catálogo, ordenadas por nombre."""
    return [
        PiezaComercial.model_validate(json.loads(f.read_text(encoding="utf-8")))
        for f in sorted(Path(ruta).glob("*.json"))
    ]


def escribir_catalogo(
    piezas: Iterable[PiezaComercial],
    destino: Path | str,
) -> list[Path]:
    """Un STEP por pieza, con su nombre. Devuelve lo que ha escrito."""
    carpeta = Path(destino)
    carpeta.mkdir(parents=True, exist_ok=True)
    escritos: list[Path] = []
    for pieza in piezas:
        ruta = carpeta / f"{pieza.nombre}.step"
        export_step(solido_de(pieza), str(ruta))
        escritos.append(ruta)
    return escritos


def caja_envolvente(pieza: PiezaComercial) -> tuple[float, float, float]:
    """Ancho, fondo y alto de la envolvente, en MILÍMETROS.

    Es lo que permite comprobar que el sólido generado coincide con la ficha
    sin abrir un CAD, y por eso hay tests que lo usan.
    """
    caja = solido_de(pieza).bounding_box()
    return (caja.size.X, caja.size.Y, caja.size.Z)


__all__ = [
    "CATALOGO",
    "LARGO_POR_DEFECTO",
    "caja_envolvente",
    "cargar",
    "escribir_catalogo",
    "solido_de",
]
