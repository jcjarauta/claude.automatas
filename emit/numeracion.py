"""La numeración única de la máquina: un registro, leído por todos.

Cada cosa que alguien tiene que encontrar encima de la mesa lleva una marca
de dos niveles —grupo y número dentro del grupo— y un código:

| Serie | Qué | Código |
| --- | --- | --- |
| piezas | lo que se fabrica (`emit.plataforma.LISTADO`) | P-AMP-03 |
| comerciales | lo que se compra entero (`docs/piezas/*.json`) | C-AMP-01 |
| tornilleria | cada línea de `emit.materiales.tornilleria()` | T-AMP-02 |

**De dónde sale.** De `docs/numeracion.json`, y de ningún otro sitio: la
explosión, las tablas del dossier, el índice y las fichas la leen; nadie la
calcula. Si se calculara en dos sitios, discreparían a los pocos días.

**Las marcas no se reutilizan ni se reordenan.** Una pieza nueva entra con la
siguiente marca libre de su grupo (`scripts/numeracion.py --alta`); una que
se va deja su número dado de baja, con `null`. Meter una pieza no renumera a
las demás: un dossier renumerado es un dossier reimpreso.

**El golden** (`tests/golden/numeracion.json`) es la copia congelada del
registro. Contra él, `comparar` dice qué es alta, qué es baja y qué número ha
cambiado de dueño, y lo dice con nombre.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
REGISTRO = RAIZ / "docs" / "numeracion.json"

SERIES = {"piezas": "P", "comerciales": "C", "tornilleria": "T"}
"""Las tres series y la letra de su código."""

Registro = dict[str, dict[str, object]]
"""grupo → {"sigla": "AMP", "piezas": {"1": "eje_pivote", …}, …}."""


@dataclass(frozen=True)
class Marca:
    grupo: str
    sigla: str
    serie: str
    numero: int
    nombre: str

    @property
    def codigo(self) -> str:
        return f"{SERIES[self.serie]}-{self.sigla}-{self.numero:02d}"

    @property
    def hoja(self) -> str:
        """Dónde se dibuja: su ficha si se fabrica, la hoja de su grupo si no."""
        return self.codigo if self.serie == "piezas" else f"G-{self.sigla}"


def cargar(ruta: Path = REGISTRO) -> Registro:
    datos: Registro = json.loads(Path(ruta).read_text(encoding="utf-8"))["grupos"]
    return datos


def guardar(registro: Registro, ruta: Path = REGISTRO) -> Path:
    """Siempre igual para el mismo registro: grupos y números ordenados."""
    ordenado = {
        g: {
            "sigla": registro[g]["sigla"],
            **{
                serie: dict(
                    sorted(
                        ((str(k), v) for k, v in dict(registro[g].get(serie, {})).items()),  # type: ignore[call-overload]
                        key=lambda kv: int(kv[0]),
                    )
                )
                for serie in SERIES
            },
        }
        for g in sorted(registro)
    }
    texto = json.dumps({"grupos": ordenado}, ensure_ascii=False, indent=2) + "\n"
    Path(ruta).write_text(texto, encoding="utf-8", newline="\n")
    return Path(ruta)


def marcas(registro: Registro) -> dict[tuple[str, str], Marca]:
    """(serie, nombre) → su marca. Los números dados de baja no salen."""
    salida: dict[tuple[str, str], Marca] = {}
    for grupo, datos in registro.items():
        for serie in SERIES:
            for numero, nombre in dict(datos.get(serie, {})).items():  # type: ignore[call-overload]
                if nombre is None:
                    continue
                clave = (serie, str(nombre))
                if clave in salida:
                    otra = salida[clave]
                    raise ValueError(
                        f"{nombre} tiene dos marcas: {otra.codigo} y "
                        f"{SERIES[serie]}-{datos['sigla']}-{int(numero):02d}"
                    )
                salida[clave] = Marca(grupo, str(datos["sigla"]), serie, int(numero), str(nombre))
    return salida


DOCUMENTO_DE_FICHAS = "fichas_{grupo}.pdf"

PRIMERA_HOJA_DE_PIEZA = 3
"""Hoja 1, la de grupo; hoja 2, el despiece explosionado; las fichas de
pieza, desde la 3."""
"""El PDF de fichas de cada grupo: hoja de grupo y una ficha por pieza."""


@dataclass(frozen=True)
class Pagina:
    documento: str
    hoja: int


def paginas(registro: Registro) -> dict[tuple[str, str], Pagina]:
    """(serie, nombre) → en qué documento y hoja está dibujado.

    Es el orden en que `emit.fichas.escribir_fichas` escribe: la hoja 1 es
    la de grupo, que lleva comerciales y tornillería; la 2, el despiece
    explosionado; después, una hoja por pieza, en el orden de su marca. Un
    número dado de baja no deja hoja vacía. No se cuentan hojas en ningún
    otro sitio: el test cruza esto con lo que de verdad lleva escrito cada
    hoja."""
    salida: dict[tuple[str, str], Pagina] = {}
    por_grupo: dict[str, list[Marca]] = {}
    for m in marcas(registro).values():
        por_grupo.setdefault(m.grupo, []).append(m)
    for grupo, suyas in por_grupo.items():
        documento = DOCUMENTO_DE_FICHAS.format(grupo=grupo)
        piezas = sorted((m for m in suyas if m.serie == "piezas"), key=lambda m: m.numero)
        for hoja, m in enumerate(piezas, start=PRIMERA_HOJA_DE_PIEZA):
            salida[(m.serie, m.nombre)] = Pagina(documento, hoja)
        for m in suyas:
            if m.serie != "piezas":
                salida[(m.serie, m.nombre)] = Pagina(documento, 1)
    return salida


Inventario = dict[str, dict[str, list[str]]]
"""grupo → serie → lo que existe hoy, en el orden en que se monta."""


def diferencias(registro: Registro, inventario: Inventario) -> list[str]:
    """Lo que existe y no tiene marca, lo que tiene marca y no existe, y lo
    que está marcado en un grupo que no es el suyo."""
    salida = []
    registradas = marcas(registro)
    existe = {(s, n): g for g, series in inventario.items() for s, ns in series.items() for n in ns}
    for (serie, nombre), grupo in sorted(existe.items()):
        marca = registradas.get((serie, nombre))
        if marca is None:
            salida.append(f"ALTA: {nombre} ({serie}, grupo {grupo}) no tiene marca")
        elif marca.grupo != grupo:
            salida.append(f"GRUPO: {nombre} es {marca.codigo} y está montado en {grupo}")
    for (serie, nombre), marca in sorted(registradas.items()):
        if (serie, nombre) not in existe:
            salida.append(f"BAJA: {marca.codigo} ({nombre}) ya no existe")
    return salida


def comparar(registro: Registro, golden: Registro) -> list[str]:
    """El registro contra su copia congelada: altas, bajas y cambios de
    dueño de un número, cada uno con su código."""
    salida = []
    for grupo in sorted(set(registro) | set(golden)):
        r, g = registro.get(grupo, {}), golden.get(grupo, {})
        if r.get("sigla") != g.get("sigla"):
            salida.append(f"SIGLA: el grupo {grupo} era {g.get('sigla')} y es {r.get('sigla')}")
        for serie, letra in SERIES.items():
            antes = dict(g.get(serie, {}))  # type: ignore[call-overload]
            ahora = dict(r.get(serie, {}))  # type: ignore[call-overload]
            sigla = r.get("sigla") or g.get("sigla")
            for numero in sorted(set(antes) | set(ahora), key=int):
                codigo = f"{letra}-{sigla}-{int(numero):02d}"
                if numero not in antes:
                    salida.append(f"ALTA: {codigo} es {ahora[numero]}")
                elif numero not in ahora:
                    salida.append(f"BORRADO: {codigo} era {antes[numero]} (se da de baja con null)")
                elif antes[numero] != ahora[numero]:
                    salida.append(f"CAMBIA: {codigo} era {antes[numero]} y es {ahora[numero]}")
    return salida


def dar_de_alta(registro: Registro, inventario: Inventario) -> tuple[Registro, list[str]]:
    """Las piezas que existen sin marca, con la siguiente libre de su grupo.
    No toca ningún número que ya esté puesto, tampoco los dados de baja."""
    nuevo: Registro = json.loads(json.dumps(registro))
    registradas = marcas(registro)
    altas = []
    for grupo in sorted(inventario):
        datos = nuevo.setdefault(grupo, {"sigla": "", **{s: {} for s in SERIES}})
        for serie in SERIES:
            usados = dict(datos.setdefault(serie, {}))  # type: ignore[call-overload]
            for nombre in inventario[grupo].get(serie, []):
                if (serie, nombre) in registradas:
                    continue
                numero = max((int(k) for k in usados), default=0) + 1
                usados[str(numero)] = nombre
                altas.append(f"ALTA: {SERIES[serie]}-{datos['sigla']}-{numero:02d} {nombre}")
            datos[serie] = usados
    return nuevo, altas


__all__ = [
    "DOCUMENTO_DE_FICHAS",
    "PRIMERA_HOJA_DE_PIEZA",
    "REGISTRO",
    "SERIES",
    "Inventario",
    "Marca",
    "Pagina",
    "Registro",
    "cargar",
    "comparar",
    "dar_de_alta",
    "diferencias",
    "guardar",
    "marcas",
    "paginas",
]
