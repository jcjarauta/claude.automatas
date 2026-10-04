"""Mete las medidas del portaminas y cierra `base_al_plato`.

    uv run python scripts/medir_portaminas.py --longitud 150.2 --cuerpo 8.05 \\
        --agarre 38.5 --clip 52.0 --agarre-diametro 9.1
    uv run python scripts/medir_portaminas.py ... --escribir [--base 72]

Con pie de rey, sobre el ejemplar que se va a montar y con la mina asomando
lo que asoma al escribir:

- longitud: de la punta de la mina a lo alto del pulsador;
- cuerpo:   diámetro del cuerpo de plástico liso, en dos sitios a 90°, el mayor;
- agarre:   de la punta de la mina a donde ACABA el agarre metálico de delante;
- clip:     de lo alto del pulsador al pie del clip;
- agarre-diametro: el diámetro MAYOR del agarre metálico, en lo moleteado.

Sin `--escribir` solo dice la ventana y lo que recomienda. Con él escribe el
catálogo del portaminas, el agujero de la pinza y `base_al_plato`, y las dos
cotas que cuelgan de ella: el poste y el tirante. Después:

    uv run python scripts/listado_piezas.py --escribir
    uv run --group cad pytest
"""

from __future__ import annotations

import argparse
import datetime
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from compile.portaminas import Portaminas, agujero_de_la_pinza, recomendar, ventana

RAIZ = Path(__file__).resolve().parent.parent


def _contrato_mm(d: dict) -> dict[str, float]:
    return {
        v["nombre"]: v["valor"] * (1000.0 if v["unidad"] == "m" else 1.0)
        for c in d["contratos"]
        for v in c["valores"]
    }


def _poner(
    d: dict, nombre: str, mm: float, tolerancia: str | None = None, descripcion: str | None = None
) -> None:
    for c in d["contratos"]:
        for v in c["valores"]:
            if v["nombre"] == nombre:
                v["valor"] = mm / 1000.0
                if tolerancia is not None:
                    v["tolerancia"] = tolerancia
                if descripcion is not None:
                    v["descripcion"] = descripcion
                return
    raise KeyError(nombre)


def _escribir_json(ruta: Path, d: dict) -> None:
    ruta.write_text(
        json.dumps(d, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n"
    )


def aplicar(
    lapiz: Portaminas,
    contratos: Path,
    piezas: Path,
    base: float | None = None,
    hoy: str | None = None,
) -> float:
    """Escribe las medidas y lo que sale de ellas. Devuelve `base_al_plato`."""
    hoy = hoy or datetime.date.today().isoformat()
    d = json.loads(contratos.read_text(encoding="utf-8"))
    c = _contrato_mm(d)
    elegido = recomendar(lapiz, c, c["base_al_plato"]) if base is None else base
    if not ventana(lapiz, c).admite(elegido):
        v = ventana(lapiz, c)
        raise ValueError(
            f"base_al_plato {elegido:g} cae fuera de la ventana {v.minimo:g}..{v.maximo:g}"
        )

    # El catálogo: las cinco medidas, como medidas.
    ruta = piezas / "portaminas.json"
    ficha = json.loads(ruta.read_text(encoding="utf-8"))
    medidas = {
        "longitud": lapiz.longitud,
        "cuerpo": lapiz.cuerpo,
        "agarre": lapiz.agarre,
        "clip": lapiz.clip,
        "agarre_diametro": lapiz.agarre_diametro,
    }
    por_nombre = {k["nombre"]: k for k in ficha["cotas"]}
    for nombre, mm in medidas.items():
        cota = por_nombre.get(nombre)
        if cota is None:
            cota = {"nombre": nombre, "valor": 0.0, "tolerancia": "", "critica": True}
            ficha["cotas"].append(cota)
        cota["valor"] = mm / 1000.0
        cota["tolerancia"] = f"medido {hoy}"
    _escribir_json(ruta, ficha)

    # El contrato: la pinza, el plato 1 y lo que cuelga de él.
    _poner(
        d,
        "pinza_agujero_diametro",
        agujero_de_la_pinza(lapiz),
        tolerancia=f"cuerpo medido + {0.1:g}",
    )
    _poner(
        d,
        "base_al_plato",
        elegido,
        tolerancia="",
        descripcion=(
            "Hueco libre de la cara alta de la base a la cara baja del plato 1. Lo fija el "
            "portaminas (compile/portaminas.py): el portalapiz agarra una franja fija respecto "
            "del plato 1 y tiene que caer en el plastico liso, entre el agarre metalico y el "
            f"clip. Cerrado el {hoy} con el portaminas medido"
        ),
    )
    c = _contrato_mm(d)
    poste = (
        c["base_poste_empotrado"]
        + c["base_al_plato"]
        + 3 * c["platina_espesor"]
        + c["poste_vano"]
        + c["reductor_bahia"]
    )
    _poner(d, "poste_largo", poste, tolerancia="")
    _escribir_json(contratos, d)

    # El tirante cruza la pila entera: se recalcula con el contrato ya escrito.
    from compile.contratos import cargar
    from compile.levantamiento import tirante_largo

    _poner(d, "tirante_largo", tirante_largo(cargar(contratos)) * 1000.0, tolerancia="")
    _escribir_json(contratos, d)

    # Y el poste del catálogo, que es el mismo número.
    ruta = piezas / "poste_pivote.json"
    poste_ficha = json.loads(ruta.read_text(encoding="utf-8"))
    for cota in poste_ficha["cotas"]:
        if cota["nombre"] == "longitud":
            cota["valor"] = poste / 1000.0
    _escribir_json(ruta, poste_ficha)
    return elegido


def main(argv: list[str] | None = None) -> int:
    sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[union-attr]
    p = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    for nombre in ("longitud", "cuerpo", "agarre", "clip", "agarre-diametro"):
        p.add_argument(f"--{nombre}", type=float, required=True, help="mm")
    p.add_argument("--base", type=float, help="base_al_plato a mano; si no, el recomendado")
    p.add_argument("--escribir", action="store_true")
    op = p.parse_args(argv)
    lapiz = Portaminas(op.longitud, op.cuerpo, op.agarre, op.clip, op.agarre_diametro)
    contratos = RAIZ / "docs" / "contratos.json"
    c = _contrato_mm(json.loads(contratos.read_text(encoding="utf-8")))
    v = ventana(lapiz, c)
    print(f"base_al_plato admite de {v.minimo:g} a {v.maximo:g}; hoy vale {c['base_al_plato']:g}")
    elegido = op.base if op.base is not None else recomendar(lapiz, c, c["base_al_plato"])
    print(f"se queda en {elegido:g}; la pinza se taladra a {agujero_de_la_pinza(lapiz):g}")
    if op.escribir:
        aplicar(lapiz, contratos, RAIZ / "docs" / "piezas", base=op.base)
        print("escrito. Ahora: scripts/listado_piezas.py --escribir y los tests")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
