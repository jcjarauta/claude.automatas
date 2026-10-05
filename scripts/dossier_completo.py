"""El dossier global, entero, en `dossier/` en la raíz del repositorio.

    uv run --group cad python scripts/dossier_completo.py

Escribe, con una sola versión para todo (la del commit en que se lanza):

- `dossier.pdf`, el dossier de montaje (`scripts/dossier.py`);
- `fichas_<grupo>.pdf` de los diez grupos (`scripts/fichas.py <grupo>`);
- `numeracion.txt`, el registro de marcas contra lo que existe
  (`scripts/numeracion.py`);
- `dibujable.txt`, lo que falta para dibujar cada pieza desde cero
  (`scripts/dibujable.py --todo`);
- `INDICE.md`: cada comando con lo que produce, y cada documento con sus
  hojas.

Se lanza con el árbol limpio, justo después de un commit, para que todas
las hojas digan de qué commit salen; si no, dirán «+cambios». Las
plantillas 1:1 y el patrón no entran aquí: son otra cosa
(`python -m compile.cli`), y no se mezclan con el dossier.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

RAIZ = Path(__file__).resolve().parent.parent
DESTINO = RAIZ / "dossier"

COMANDO = "uv run --group cad python"


def _hojas(pdf: Path) -> int:
    datos = pdf.read_bytes()
    return datos.count(b"/Type /Page") - datos.count(b"/Type /Pages")


def _cuantas(n: int, una: str, varias: str = "") -> str:
    return f"{n} {una if n == 1 else varias or una + 's'}"


def main(argv: list[str] | None = None) -> int:
    from emit.dibujable import faltas, perfil_de
    from emit.dossier import ORDEN_DE_MONTAJE, escribir_dossier
    from emit.fichas import escribir_fichas
    from emit.montaje import GRUPOS
    from emit.numeracion import cargar, diferencias, marcas, paginas
    from scripts.dossier import _version, datos
    from scripts.fichas import preparar
    from scripts.numeracion import inventario

    sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[union-attr]
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--destino", type=Path, default=DESTINO)
    op = p.parse_args(argv)
    destino: Path = op.destino
    destino.mkdir(parents=True, exist_ok=True)

    # Una versión para todo, leída antes de escribir nada: lo primero que se
    # escribe ensuciaría el árbol para lo demás.
    version = _version()
    print(f"versión: {version}")

    dossier = escribir_dossier(datos(version), destino / "dossier.pdf")
    print(f"{dossier.name}: {_hojas(dossier)} páginas")

    registro = cargar()
    donde = paginas(registro)
    por_grupo = {g.nombre: g for g in GRUPOS}
    fichas: list[tuple[str, Path, list[str]]] = []
    pendientes: list[str] = []
    for nombre in ORDEN_DE_MONTAJE:
        g = preparar(nombre)
        ruta = escribir_fichas(g, destino / f"fichas_{nombre}.pdf", version)
        suyas = [
            f
            for pieza in g.piezas
            for f in faltas(perfil_de(pieza.nombre, g.contrato), pieza.acotacion)
        ]
        pendientes.append(f"== {nombre}: {len(suyas)} faltas en {len(g.piezas)} piezas")
        pendientes += [f"   {f}" for f in suyas]
        fichas.append((nombre, ruta, list(g.sin_ficha)))
        print(f"{ruta.name}: {_cuantas(_hojas(ruta), 'hoja')}")
    total = sum(1 for linea in pendientes if linea.startswith("   "))
    pendientes.append(f"TOTAL {total}")
    (destino / "dibujable.txt").write_text("\n".join(pendientes) + "\n", encoding="utf-8")

    diferentes = diferencias(registro, inventario())
    (destino / "numeracion.txt").write_text(
        "\n".join(diferentes or ["el registro está al día"]) + "\n", encoding="utf-8"
    )

    # --- INDICE.md -----------------------------------------------------------
    todas = marcas(registro)
    lineas = [
        "# Dossier del escribiente",
        "",
        f"Generado por `{COMANDO} scripts/dossier_completo.py` · versión **{version}**.",
        "",
        "Todo lo que hay en esta carpeta sale de los comandos de abajo; nada se",
        "edita a mano. Las hojas dicen «No medir sobre esta hoja»: lo que se corta",
        "a escala 1:1 son las plantillas (`python -m compile.cli`), que van aparte.",
        "",
        "## Comandos y resultado",
        "",
        "| Comando | Resultado | Qué es |",
        "| --- | --- | --- |",
        f"| `{COMANDO} scripts/dossier.py` | [dossier.pdf](dossier.pdf) "
        f"({_cuantas(_hojas(dossier), 'pág.', 'págs.')}) | Dossier de montaje: portada, "
        "índice, explosión de conjunto, vistas, despiece, secuencia, procedimientos, "
        "comprobación final |",
    ]
    for nombre, ruta, _ in fichas:
        lineas.append(
            f"| `{COMANDO} scripts/fichas.py {nombre}` | [{ruta.name}]({ruta.name}) "
            f"({_cuantas(_hojas(ruta), 'hoja')}) | {por_grupo[nombre].objetivo} |"
        )
    lineas += [
        f"| `{COMANDO} scripts/numeracion.py` | [numeracion.txt](numeracion.txt) | "
        f"Registro de marcas contra lo que existe: {len(diferentes)} diferencias |",
        f"| `{COMANDO} scripts/dibujable.py --todo` | [dibujable.txt](dibujable.txt) | "
        f"Lo que falta para dibujar cada pieza desde cero: {total} faltas |",
        f"| `{COMANDO} scripts/ver.py --conjunto` | visor OCP CAD | La máquina montada, "
        "por grupos |",
        f"| `{COMANDO} scripts/ver.py --conjunto --explosion` | visor OCP CAD | La "
        "explosión de conjunto del dossier, en 3D |",
        "",
        "## Dónde está cada pieza",
        "",
        "En el orden de montaje. La hoja 1 de cada documento de fichas es la de",
        "grupo: comerciales, tornillería y despiece.",
        "",
    ]
    for paso, (nombre, ruta, sin_ficha) in enumerate(fichas, start=1):
        g = por_grupo[nombre]
        lineas += [
            f"### {paso}. {nombre} · G-{g.sigla} · [{ruta.name}]({ruta.name})",
            "",
            "| Marca | Qué | Hoja |",
            "| --- | --- | --- |",
        ]
        suyas = sorted(
            (m for m in todas.values() if m.grupo == nombre),
            key=lambda m: ("PCT".index(m.codigo[0]), m.numero),
        )
        for m in suyas:
            lineas.append(f"| {m.codigo} | {m.nombre} | {donde[(m.serie, m.nombre)].hoja} |")
        if sin_ficha:
            lineas.append(f"| — | sin ficha: {', '.join(sin_ficha)} | — |")
        lineas.append("")
    (destino / "INDICE.md").write_text("\n".join(lineas), encoding="utf-8", newline="\n")
    print(f"índice en {destino / 'INDICE.md'}")
    return 1 if total or diferentes else 0


if __name__ == "__main__":
    raise SystemExit(main())
