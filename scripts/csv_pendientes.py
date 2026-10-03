"""Qué CSV hay que reimportar al Variable Studio, y qué ha cambiado en cada uno.

    uv run python scripts/csv_pendientes.py build/cad

`docs/importado.json` guarda el sha256 de lo que está **ahora mismo** en
Onshape. Esto compara el paquete recién generado contra eso y dice qué
archivos difieren y, fila a fila, qué entra, qué sale y qué cambia de valor.

**Hace falta porque reimportar de más también cuesta.** Un mapa del Variable
Studio no se actualiza: se borra y se vuelve a crear, y mientras tanto todo lo
que lo referencia se pone en rojo. Decir «reimporta los cinco» por si acaso es
pedir cinco veces ese susto cuando normalmente ha cambiado uno.

Y hace falta porque la alternativa es que alguien se acuerde. El bucle de
`docs/metodologia.md` §2d lo pide por pieza, y una lista que se escribe a mano
se queda atrás la segunda vez.

Después de importar se marca con `scripts/marcar_importado.py`.
"""

from __future__ import annotations

import argparse
import csv as _csv
import hashlib
import json
import os
import sys
from dataclasses import dataclass, field
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

RAIZ = Path(__file__).resolve().parent.parent
IMPORTADO = RAIZ / "docs" / "importado.json"


@dataclass
class Cambio:
    archivo: str
    altas: list[str] = field(default_factory=list)
    bajas: list[str] = field(default_factory=list)
    distintas: list[tuple[str, str, str]] = field(default_factory=list)
    renombradas: list[tuple[str, str]] = field(default_factory=list)
    """Una que se va y otra que llega con el MISMO valor.

    Se separa de las altas y las bajas porque no cuesta lo mismo. Una alta no
    rompe nada: la cota nueva se teclea cuando toque. Un renombrado **rompe en
    silencio todo croquis que ya usara el nombre viejo**, y el croquis se ve
    bien hasta que se abre.
    """

    @property
    def hay(self) -> bool:
        return bool(self.altas or self.bajas or self.distintas or self.renombradas)


def _filas(texto: str) -> dict[str, str]:
    """Nombre -> valor. Los CSV que se importan no llevan cabecera."""
    return {f[0]: f[1] for f in _csv.reader(texto.splitlines()) if len(f) >= 2}


def estado() -> dict[str, dict[str, object]]:
    return dict(json.loads(IMPORTADO.read_text(encoding="utf-8"))["archivos"])


def _la_mas_parecida(viejo: str, candidatas: list[str]) -> str | None:
    """De los nombres que valen lo mismo, el que de verdad es el renombrado.

    Con UNA candidata no hay nada que decidir: el valor la empareja y ya
    está, que es como funcionaba y funcionaba bien.

    Con varias manda el nombre: gana la que comparte más palabras con la
    vieja y, a igualdad, más prefijo. Un renombrado conserva de qué habla la
    cota —`platina_radio` pasó a `platina_diametro`, `seguidor_sector_lejos`
    a `union_sector_seguidor_lejos`—. Si ninguna comparte una palabra, no se
    elige: dos nombres sin nada en común que coinciden en el número son dos
    cotas distintas, y mandar a reteclear una cota que está bien es peor que
    callarse.
    """
    if len(candidatas) <= 1:
        return candidatas[0] if candidatas else None

    def parecido(n: str) -> tuple[int, int]:
        comunes = len(set(viejo.split("_")) & set(n.split("_")))
        return comunes, len(os.path.commonprefix([viejo, n]))

    mejor = max(candidatas, key=parecido)
    return mejor if parecido(mejor)[0] else None


def pendientes(paquete: Path) -> list[Cambio]:
    """Los archivos que difieren de lo que hay en Onshape, con el detalle."""
    dentro, salida = estado(), []
    for nombre, guardado in sorted(dentro.items()):
        ruta = paquete / f"{nombre}.csv"
        if not ruta.exists():
            continue
        crudo = ruta.read_bytes()
        if hashlib.sha256(crudo).hexdigest() == guardado["sha256"]:
            continue
        cambio = Cambio(nombre)
        ahora = _filas(crudo.decode("utf-8"))
        antes = _filas((guardado.get("contenido") or "") or "")
        if not antes:
            # Sin copia del contenido solo se puede decir que cambió. Es el
            # caso de la primera vez; a partir de ahí se guarda y hay detalle.
            cambio.altas = sorted(ahora)
        else:
            altas = sorted(ahora.keys() - antes.keys())
            bajas = sorted(antes.keys() - ahora.keys())
            # Emparejar por VALOR lo que se va con lo que llega: eso es un
            # renombrado, y es el único cambio que rompe un croquis ya hecho.
            #
            # **Por valor no basta cuando hay varios candidatos**, y los hay
            # en cuanto el contrato crece: el día que `poste_diametro` (15)
            # se renombró a `poste_obstaculo_diametro`, entró a la vez
            # `base_poste_empotrado`, que también vale 15, y el informe
            # emparejó el alfabéticamente primero. Decir «RENOMBRADA» de dos
            # cotas que no tienen nada que ver manda a reteclear cotas que
            # están bien, que es peor que no decir nada.
            #
            # Así que entre los que valen lo mismo manda el NOMBRE, y si
            # ninguno comparte una palabra con el que se va, no es un
            # renombrado: es una baja y un alta que coinciden en el número.
            for ida in list(bajas):
                gemela = _la_mas_parecida(ida, [n for n in altas if ahora[n] == antes[ida]])
                if gemela is not None:
                    cambio.renombradas.append((ida, gemela))
                    bajas.remove(ida)
                    altas.remove(gemela)
            cambio.altas, cambio.bajas = altas, bajas
            cambio.distintas = [
                (n, antes[n], ahora[n])
                for n in sorted(ahora.keys() & antes.keys())
                if antes[n] != ahora[n]
            ]
        salida.append(cambio)
    return salida


def informe(cambios: list[Cambio], mapas: dict[str, tuple[str, str]]) -> str:
    if not cambios:
        return "# Reimportar\n\nNada. Lo que hay en Onshape coincide con el paquete.\n"
    lineas = [
        "# Reimportar",
        "",
        "Lo que ha cambiado desde la última importación. **Lo que no está aquí no",
        "se toca**: un mapa del Variable Studio no se actualiza, se borra y se",
        "vuelve a crear, y mientras tanto todo lo que lo referencia se pone en rojo.",
        "",
        "| Archivo | Variable | Factor |",
        "| --- | --- | --- |",
    ]
    for c in cambios:
        mapa, factor = mapas.get(c.archivo, ("?", "?"))
        lineas.append(f"| `{c.archivo}.csv` | `#{mapa}` | `{factor}` |")
    for c in cambios:
        lineas += ["", f"## `{c.archivo}.csv`", ""]
        for viejo_n, nuevo_n in c.renombradas:
            lineas.append(
                f"- **RENOMBRADA** `{viejo_n}` → `{nuevo_n}` — reteclea a mano toda "
                "cota que usara la vieja: el croquis no avisa hasta que se abre"
            )
        for n in c.altas:
            lineas.append(f"- **nueva** `{n}`")
        for n in c.bajas:
            lineas.append(
                f"- **se va** `{n}` — la clave vieja se queda en el mapa si no borras la tabla"
            )
        for n, a, b in c.distintas:
            lineas.append(f"- **cambia** `{n}`: {a} → {b}")
    lineas += [
        "",
        "Al terminar: `uv run python scripts/marcar_importado.py`",
        "",
    ]
    return "\n".join(lineas)


def main(argv: list[str] | None = None) -> int:
    from scripts.exportar_para_cad import MAPAS

    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("paquete", type=Path, nargs="?", default=Path("build/cad"))
    op = p.parse_args(argv)
    cambios = pendientes(op.paquete)
    # La consola de Windows es cp1252 y no tiene la flecha de los cambios.
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    print(informe(cambios, MAPAS), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
