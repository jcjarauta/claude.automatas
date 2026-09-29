"""Comprueba las reglas de arquitectura de CLAUDE.md.

Estos tests no prueban comportamiento: protegen decisiones. Existen desde el
primer día porque una regla que no se comprueba se rompe sola en tres semanas.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parent.parent

# Lo que el núcleo no puede importar nunca. Si algo de esto aparece en core/,
# es que una responsabilidad se ha colado donde no toca.
PROHIBIDO_EN_CORE = {
    # hermanos: la dependencia va en un solo sentido
    "compile",
    "emit",
    "api",
    # red
    "requests",
    "httpx",
    "urllib",
    "socket",
    "aiohttp",
    # disco
    "pathlib",
    "os",
    "shutil",
    "tempfile",
    "io",
    # frameworks
    "fastapi",
    "starlette",
    "uvicorn",
    # formatos de salida: el núcleo no sabe que existen los archivos
    "ezdxf",
    "build123d",
    "reportlab",
    "fitz",
    "matplotlib",
}


def _modulos_python(paquete: str) -> list[Path]:
    return sorted((RAIZ / paquete).rglob("*.py"))


def _importados(fichero: Path) -> set[str]:
    arbol = ast.parse(fichero.read_text(encoding="utf-8"), filename=str(fichero))
    nombres: set[str] = set()
    for nodo in ast.walk(arbol):
        if isinstance(nodo, ast.Import):
            for alias in nodo.names:
                nombres.add(alias.name.split(".")[0])
        elif isinstance(nodo, ast.ImportFrom):
            if nodo.level:  # import relativo dentro del propio paquete
                continue
            if nodo.module:
                nombres.add(nodo.module.split(".")[0])
    return nombres


@pytest.mark.core
@pytest.mark.parametrize("fichero", _modulos_python("core"), ids=lambda p: str(p.name))
def test_el_nucleo_no_importa_del_exterior(fichero: Path) -> None:
    """Regla 2 de CLAUDE.md: core/ es puro."""
    infractores = _importados(fichero) & PROHIBIDO_EN_CORE
    assert not infractores, (
        f"{fichero.relative_to(RAIZ)} importa {sorted(infractores)}. "
        "El núcleo no hace E/S, no habla por red y no conoce formatos de salida."
    )


@pytest.mark.core
@pytest.mark.parametrize("fichero", _modulos_python("core"), ids=lambda p: str(p.name))
def test_el_nucleo_no_imprime(fichero: Path) -> None:
    """El núcleo comunica devolviendo datos o lanzando errores, nunca por stdout."""
    arbol = ast.parse(fichero.read_text(encoding="utf-8"), filename=str(fichero))
    for nodo in ast.walk(arbol):
        if (
            isinstance(nodo, ast.Call)
            and isinstance(nodo.func, ast.Name)
            and nodo.func.id == "print"
        ):
            pytest.fail(
                f"{fichero.relative_to(RAIZ)}:{nodo.lineno} llama a print(). "
                "El núcleo devuelve datos; quien los muestra es otra capa."
            )


def test_existen_los_paquetes_declarados() -> None:
    """La estructura de CLAUDE.md existe de verdad."""
    esperados = [
        "core",
        "core/cam",
        "core/actors",
        "core/energy",
        "compile",
        "emit",
        "api",
        "bench",
        "docs",
        "tests",
    ]
    faltan = [d for d in esperados if not (RAIZ / d).is_dir()]
    assert not faltan, f"Faltan carpetas declaradas en CLAUDE.md: {faltan}"
