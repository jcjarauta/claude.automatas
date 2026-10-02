"""Convierte un fichero de contratos en la tabla de variables de Onshape.

    uv run python scripts/exportar_variables.py                    # escribiente, a la pantalla
    uv run python scripts/exportar_variables.py --out build/
    uv run python scripts/exportar_variables.py --csv --por-tipo \
        --contratos docs/reloj/contratos.json --out build/

**Una tabla por maquina, y por tanto un documento de Onshape por maquina.**
El Variable Studio tiene un solo espacio de nombres, asi que mezclar las cotas
del escribiente con las del reloj es pedir que alguien dibuje una platina con
el radio base de una leva. Cada maquina tiene su fichero de contratos, su
tabla y su documento.

Lo que las dos comparten -el contrato de eje- esta escrito en los dos ficheros
a proposito, y hay un test que comprueba que dicen lo mismo. Es la unica forma
de que el arbol del reloj entre en el agujero del escribiente el dia que se
acoplen.

**Para qué.** La plataforma se dibuja a mano en Onshape y tiene que usar los
mismos números que el compilador. Copiarlos a ojo es cómo la valona del
casquillo acabó siendo Ø12 en tres sitios cuando el fabricante dice Ø15. Esto
los escribe una vez, en el formato que Onshape entiende, y se pegan en el
**Variable Studio** del documento. Todas las Part Studios de la plataforma
los referencian desde ahí con `#nombre`.

**El flujo es de un solo sentido.** Se toca el JSON, se regenera, se pega. No
se editan las variables dentro de Onshape: lo que se edite allí se pierde en
la siguiente regeneración y, peor, deja de coincidir con lo que calcula el
compilador sin que nadie se entere.

**Unidades y tipos.** El compilador trabaja en SI; Onshape en milímetros y
grados. La conversión ocurre aquí, que es la frontera, y no a medias por el
camino. Cada unidad declara su factor y **de qué tipo es la variable en
Onshape**, porque no todas valen para lo mismo:

| Tipo | Qué es | Qué se puede hacer con ella |
| --- | --- | --- |
| `LENGTH` | m -> mm | Acotar un boceto |
| `ANGLE` | rad -> grados | Acotar un ángulo, un patrón circular |
| `NUMBER` | adimensional | Contar dientes, pernos, repeticiones |
| `REFERENCIA` | s, kg, N | **Nada.** No dimensiona geometría |

Las de `REFERENCIA` existen porque el reloj trae magnitudes que el escribiente
no tenía -un periodo, una masa, una tensión- y son decisiones de producto que
hay que tener delante al dibujar. Pero **no son cotas**, y si entran en el
Variable Studio como números pelados, antes o después alguien acota con
`#masa_pesa` y nadie se entera hasta que la pieza está cortada. Por eso salen
como comentario en el FeatureScript y en su propio fichero en el CSV.

**Una unidad que esta tabla no conozca revienta en vez de pasar por
adimensional.** Era el fallo de antes: el reloj metió `s`, `kg` y `N`, y los
tres salían como un número sin unidad, indistinguibles de un número de
dientes.

Dos formatos:

- **FeatureScript**, para pegar en una Feature Studio y llamarla desde el
  Variable Studio. Es el que conserva los comentarios.
- **CSV**, por si se prefiere la tabla de variables importada. Con `--por-tipo`
  sale un fichero por tipo, que es lo cómodo cuando el Variable Studio pide
  elegir el tipo en un desplegable.
"""

from __future__ import annotations

import argparse
import csv as modulo_csv
import io
import math
import sys
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path

from compile.contratos import RUTA, Contratos, Estado, Valor, cargar

CABECERA = """// Variables de {maquina}, generadas desde {fuente}
// NO EDITAR AQUI: se regenera con  uv run python scripts/exportar_variables.py
// Version del contrato: {version}   Fecha: {fecha}
"""

HORA = 3600.0
"""Segundos. Una autonomía de 108.000 s es correcta y no la lee nadie."""


class Tipo(StrEnum):
    """Qué puede hacer Onshape con la variable."""

    LENGTH = "LENGTH"
    ANGLE = "ANGLE"
    NUMBER = "NUMBER"
    REFERENCIA = "REFERENCIA"

    @property
    def dimensiona(self) -> bool:
        """Si vale para acotar algo. `REFERENCIA` no."""
        return self is not Tipo.REFERENCIA


@dataclass(frozen=True)
class Conversion:
    """Cómo pasa una magnitud del contrato a la frontera con el CAD."""

    factor: float
    simbolo: str
    tipo: Tipo
    sufijo: str
    """Lo que se escribe detrás del número en FeatureScript."""
    decimales: int


UNIDADES: dict[str, Conversion] = {
    "m": Conversion(1000.0, "mm", Tipo.LENGTH, " * millimeter", 4),
    "rad": Conversion(180.0 / math.pi, "deg", Tipo.ANGLE, " * degree", 4),
    "adimensional": Conversion(1.0, "", Tipo.NUMBER, "", 6),
    "s": Conversion(1.0, "s", Tipo.REFERENCIA, "", 6),
    "kg": Conversion(1.0, "kg", Tipo.REFERENCIA, "", 6),
    "N": Conversion(1.0, "N", Tipo.REFERENCIA, "", 6),
}


def conversion_de(valor: Valor) -> Conversion:
    """La conversión que le toca, o se rompe.

    Un `KeyError` silencioso aquí sería una variable con unidad desconocida
    saliendo como número pelado, que es exactamente como `masa_pesa` acabó
    pareciéndose a un número de dientes.

    El tiempo es el único caso con dos presentaciones: los periodos cortos se
    leen en segundos y las autonomías en horas. La decisión es de presentación
    y por eso vive aquí, en la frontera, y no en el contrato, que guarda SI.
    """
    if valor.unidad not in UNIDADES:
        conocidas = ", ".join(sorted(UNIDADES))
        raise ValueError(
            f"'{valor.nombre}' usa la unidad '{valor.unidad}', que esta tabla no sabe "
            f"convertir. Conocidas: {conocidas}. Añádela antes de exportar: sin esto "
            "saldría como un número sin unidad y nadie podría distinguirla de una cuenta."
        )
    base = UNIDADES[valor.unidad]
    if valor.unidad == "s" and abs(valor.valor) >= 2.0 * HORA:
        return Conversion(1.0 / HORA, "h", base.tipo, base.sufijo, base.decimales)
    return base


def convertir(valor: Valor) -> tuple[str, Conversion]:
    """El número ya en unidades de salida, y con qué se convirtió."""
    conversion = conversion_de(valor)
    cifra = f"{valor.valor * conversion.factor:.{conversion.decimales}f}"
    if conversion.decimales > 4:
        cifra = f"{valor.valor * conversion.factor:.6g}"
    return cifra, conversion


def featurescript(
    contratos: Contratos,
    maquina: str = "el escribiente",
    fuente: str = "docs/contratos.json",
) -> str:
    """El bloque para pegar en una Feature Studio de Onshape.

    Lo que dimensiona sale como `export const`. Lo que no -masas, tiempos,
    fuerzas- sale al final como comentario, para que esté delante de quien
    dibuja sin que pueda acotar con ello.
    """
    lineas = [
        CABECERA.format(
            maquina=maquina, fuente=fuente, version=contratos.version, fecha=contratos.fecha
        )
    ]
    referencia: list[str] = []
    for contrato in contratos.contratos:
        estado = contrato.estado.value.upper()
        cotas: list[str] = []
        for valor in contrato.valores:
            cifra, conversion = convertir(valor)
            tolerancia = f"  [{valor.tolerancia}]" if valor.tolerancia else ""
            if conversion.tipo.dimensiona:
                cotas.append(
                    f"export const {valor.nombre} = {cifra}{conversion.sufijo};"
                    f"  // {conversion.tipo.value} · {valor.descripcion}{tolerancia}"
                )
            else:
                referencia.append(
                    f"// {valor.nombre} = {cifra} {conversion.simbolo}"
                    f"  // {valor.descripcion}{tolerancia}"
                )
        if not cotas:
            continue
        lineas.append(f"// ---- {contrato.nombre.upper()} · {estado} ----")
        lineas.append(f"// {contrato.porque}")
        if contrato.estado is Estado.PENDIENTE:
            lineas.append("// OJO: pendiente de medir. Se puede dibujar, no se puede prometer.")
        lineas.extend(cotas)
        lineas.append("")
    if referencia:
        lineas.append("// ---- REFERENCIA · NO DIMENSIONA NADA ----")
        lineas.append("// Magnitudes de producto, no cotas. Van como comentario a proposito:")
        lineas.append("// acotar un boceto con una masa o con un periodo no da ningun error.")
        lineas.extend(referencia)
        lineas.append("")
    return "\n".join(lineas)


CABECERA_CSV = [
    "nombre",
    "valor",
    "unidad",
    "tipo",
    "factor",
    "unidad_contrato",
    "contrato",
    "estado",
    "tolerancia",
    "descripcion",
]


def filas(contratos: Contratos) -> list[list[str]]:
    """Una fila por variable, ya convertida, con el factor a la vista.

    El factor va en su columna para que la conversión sea auditable: la regla
    3 dice que nunca se convierte a medias, y la forma de comprobarlo es poder
    multiplicar el valor del contrato y que salga el de la tabla.
    """
    salida: list[list[str]] = []
    for contrato in contratos.contratos:
        for valor in contrato.valores:
            cifra, conversion = convertir(valor)
            salida.append(
                [
                    valor.nombre,
                    cifra,
                    conversion.simbolo,
                    conversion.tipo.value,
                    f"{conversion.factor:.10g}",
                    valor.unidad,
                    contrato.nombre,
                    contrato.estado.value,
                    valor.tolerancia,
                    valor.descripcion,
                ]
            )
    return salida


def _escribir_csv_sin_cabecera(cuerpo: list[list[str]]) -> str:
    buffer = io.StringIO()
    modulo_csv.writer(buffer, lineterminator="\n").writerows(cuerpo)
    return buffer.getvalue()


def _escribir_csv(cabecera: list[str], cuerpo: list[list[str]]) -> str:
    buffer = io.StringIO()
    escritor = modulo_csv.writer(buffer, lineterminator="\n")
    escritor.writerow(cabecera)
    escritor.writerows(cuerpo)
    return buffer.getvalue()


def csv(contratos: Contratos) -> str:
    """La tabla entera, por si se importa en vez de pegarse.

    Se escribe con el modulo `csv` y no a mano porque una tolerancia o una
    descripcion pueden llevar coma -`m6 en el plato metalico, deslizante en
    el POM` la lleva- y a mano eso parte la fila en dos columnas de mas sin
    que nada avise.
    """
    return _escribir_csv(CABECERA_CSV, filas(contratos))


def csv_por_tipo(contratos: Contratos) -> dict[Tipo, str]:
    """Una tabla por tipo de variable de Onshape.

    El Variable Studio pide el tipo en un desplegable al crear cada variable.
    Con un fichero por tipo no hay desplegable que equivocar, y las de
    `REFERENCIA` quedan en un fichero aparte que nadie va a importar.
    """
    reparto: dict[Tipo, list[list[str]]] = {}
    for fila in filas(contratos):
        reparto.setdefault(Tipo(fila[3]), []).append(fila)
    return {tipo: _escribir_csv(CABECERA_CSV, cuerpo) for tipo, cuerpo in reparto.items()}


COLUMNAS_COTA = ["nombre", "valor", "unidad", "contrato", "estado", "tolerancia", "descripcion"]
"""Las siete del formato que importa Onshape por indice de celda.

**No lleva cabecera.** La fila 0 es la primera variable, porque el dialogo de
importacion indexa desde 0 y una cabecera correria todas las filas una
posicion. El valor esta siempre en la columna 1.
"""

COLUMNA_VALOR = 1


def gemelo(nombre: str, valor: float) -> tuple[str, float] | None:
    """La misma cota expresada del otro modo: radio si es diametro, y al reves.

    El CAD acota unas veces por radio y otras por diametro, y la mitad o el
    doble se hacen de cabeza. Hacerlo de cabeza es donde se cuela el error, y
    ademas deja la cota fuera del contrato: si alguien teclea 5 porque el eje
    es de 10, ese 5 ya no se entera de que el eje cambie.

    La regla es por nombre y no por significado, a proposito: `taladro_eje`
    tambien es un diametro y no lleva gemelo, porque lo que decide no es lo
    que la cota ES sino como se llama. Asi se puede leer el fichero y saber
    cuales hay sin conocer la pieza.
    """
    if "diametro" in nombre:
        return f"{nombre}_radio", valor / 2.0
    if "radio" in nombre:
        return f"{nombre}_diametro", valor * 2.0
    return None


def tabla_cota(contratos: Contratos) -> str:
    """El fichero que se sube a Onshape y del que tiran las variables.

    Solo lo que dimensiona: una masa o un periodo no se acotan, y si estan en
    el fichero alguien acabara enlazando una variable a esa fila.
    """
    cuerpo: list[list[str]] = []
    for contrato in contratos.contratos:
        for valor in contrato.valores:
            cifra, conversion = convertir(valor)
            if not conversion.tipo.dimensiona:
                continue
            fila = [
                valor.nombre,
                cifra,
                conversion.simbolo,
                contrato.nombre,
                contrato.estado.value,
                valor.tolerancia,
                valor.descripcion,
            ]
            cuerpo.append(fila)
            par = gemelo(valor.nombre, valor.valor * conversion.factor)
            if par is not None and conversion.tipo is Tipo.LENGTH:
                nombre_gemelo, valor_gemelo = par
                cuerpo.append(
                    [
                        nombre_gemelo,
                        f"{valor_gemelo:.{conversion.decimales}f}",
                        conversion.simbolo,
                        contrato.nombre,
                        contrato.estado.value,
                        valor.tolerancia,
                        f"derivada de {valor.nombre} \u2014 {valor.descripcion}",
                    ]
                )
    return _escribir_csv_sin_cabecera(cuerpo)


def indice_de_filas(contratos: Contratos) -> list[tuple[int, str, str]]:
    """Que fila le toca a cada variable, para configurar la importacion."""
    filas = tabla_cota(contratos).strip().split("\n")
    import csv as lector

    return [
        (i, campos[0], f"{campos[1]} {campos[2]}".strip())
        for i, campos in enumerate(lector.reader(filas))
    ]


CABECERA_ONSHAPE = ["Nombre", "Tipo de variable", "Valor", "Descripcion"]

TIPO_EN_ONSHAPE = {
    Tipo.LENGTH: "Longitud",
    Tipo.ANGLE: "Angulo",
    Tipo.NUMBER: "Numero",
}


def descripcion_corta(texto: str, limite: int = 70) -> str:
    """La descripcion recortada a lo que cabe en una celda del CAD.

    El porque entero vive en el repositorio; en el Variable Studio solo hace
    falta reconocer la variable de un vistazo. Se corta por la primera frase,
    salvo que la primera frase sea tan corta que no diga nada -`Propuesta.`-,
    en cuyo caso se sigue y se recorta por palabra.
    """
    cabeza = texto.split(". ")[0]
    if len(cabeza) < 25:
        cabeza = texto
    if len(cabeza) <= limite:
        return cabeza.rstrip(".")
    recorte = cabeza[: limite - 1].rsplit(" ", 1)[0]
    return f"{recorte}\u2026"


def tabla_onshape(contratos: Contratos) -> dict[Tipo, str]:
    """La hoja con la forma exacta de la tabla del Variable Studio.

    Cuatro columnas y en su orden, el valor ya con su unidad escrita como la
    espera Onshape, y **sin las de REFERENCIA**: esas no entran en el Variable
    Studio y meterlas ahi es justo lo que el tipo existe para impedir.
    """
    reparto: dict[Tipo, list[list[str]]] = {}
    for contrato in contratos.contratos:
        for valor in contrato.valores:
            cifra, conversion = convertir(valor)
            if not conversion.tipo.dimensiona:
                continue
            # Sin ceros de cola: estas celdas se teclean a mano y `994 mm` se
            # lee y se escribe mejor que `994.0000 mm`.
            limpia = cifra.rstrip("0").rstrip(".") if "." in cifra else cifra
            celda = f"{limpia} {conversion.simbolo}".strip()
            reparto.setdefault(conversion.tipo, []).append(
                [
                    valor.nombre,
                    TIPO_EN_ONSHAPE[conversion.tipo],
                    celda,
                    descripcion_corta(valor.descripcion),
                ]
            )
    return {tipo: _escribir_csv(CABECERA_ONSHAPE, cuerpo) for tipo, cuerpo in reparto.items()}


def _maquina_de(fuente: Path) -> str:
    """El rotulo sale de la carpeta: `docs/reloj/contratos.json` -> reloj.

    El del escribiente vive en `docs/` a secas por razones historicas, asi
    que esa es la excepcion y no hay forma de deducirlo del nombre.
    """
    carpeta = fuente.parent.name
    return "escribiente" if carpeta in ("docs", "") else carpeta


def main(argv: list[str] | None = None) -> int:
    partes = argparse.ArgumentParser(prog="exportar_variables", description=__doc__)
    partes.add_argument("--out", type=Path, default=None, help="carpeta donde escribir")
    partes.add_argument("--csv", action="store_true", help="CSV en vez de FeatureScript")
    partes.add_argument(
        "--cota",
        action="store_true",
        help="el CSV que se sube a Onshape y del que tiran las variables importadas",
    )
    partes.add_argument(
        "--onshape",
        action="store_true",
        help="la hoja con la forma de la tabla del Variable Studio, un fichero por tipo",
    )
    partes.add_argument(
        "--por-tipo",
        action="store_true",
        help="un CSV por tipo de variable de Onshape, en vez de uno solo",
    )
    partes.add_argument(
        "--contratos",
        type=Path,
        default=None,
        help="fichero de contratos; por defecto el del escribiente",
    )
    partes.add_argument(
        "--maquina",
        default=None,
        help="rotulo de la maquina; por defecto sale de la carpeta del fichero",
    )
    opciones = partes.parse_args(argv)

    fuente = opciones.contratos if opciones.contratos is not None else RUTA
    maquina = opciones.maquina or _maquina_de(fuente)
    contratos = cargar(fuente)

    if opciones.por_tipo and not opciones.csv:
        print("--por-tipo solo tiene sentido con --csv", file=sys.stderr)
        return 2

    if opciones.cota:
        tablas = {f"{maquina}_cota.csv": tabla_cota(contratos)}
    elif opciones.onshape:
        tablas = {
            f"onshape-{maquina}-{tipo.value.lower()}.csv": texto
            for tipo, texto in tabla_onshape(contratos).items()
        }
    elif opciones.por_tipo:
        tablas = {
            f"variables-{maquina}-{tipo.value.lower()}.csv": texto
            for tipo, texto in csv_por_tipo(contratos).items()
        }
    else:
        nombre = f"variables-{maquina}.{'csv' if opciones.csv else 'fs'}"
        texto = (
            csv(contratos)
            if opciones.csv
            else featurescript(contratos, maquina=f"el {maquina}", fuente=str(fuente))
        )
        tablas = {nombre: texto}

    if opciones.out is None:
        for nombre, texto in tablas.items():
            if len(tablas) > 1:
                print(f"==== {nombre} ====")
            print(texto)
        return 0

    opciones.out.mkdir(parents=True, exist_ok=True)
    for nombre, texto in tablas.items():
        ruta = opciones.out / nombre
        ruta.write_text(texto, encoding="utf-8")
        print(f"escrito {ruta}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
